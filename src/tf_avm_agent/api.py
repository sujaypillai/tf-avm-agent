"""
FastAPI backend for the TF AVM Agent web interface.

Provides REST API and WebSocket endpoints for:
- Chat interactions with the agent
- Terraform code generation from services
- Architecture diagram analysis
- AVM module listing and search
"""

import asyncio
import json
import logging
import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from tf_avm_agent import __version__
from tf_avm_agent.agent import TerraformAVMAgent
from tf_avm_agent.registry.avm_modules import (
    AVM_MODULES,
    get_all_categories,
    get_module_by_service,
    get_modules_by_category,
    search_modules,
)
from tf_avm_agent.tools.terraform_generator import generate_terraform_project

logger = logging.getLogger(__name__)

# Session storage for chat agents
_sessions: dict[str, TerraformAVMAgent] = {}


def get_or_create_session(session_id: str) -> TerraformAVMAgent:
    """Get an existing session or create a new one."""
    if session_id not in _sessions:
        _sessions[session_id] = TerraformAVMAgent(
            use_azure_openai=bool(os.environ.get("AZURE_OPENAI_ENDPOINT")),
        )
    return _sessions[session_id]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting TF AVM Agent API")
    yield
    logger.info("Shutting down TF AVM Agent API")
    _sessions.clear()


app = FastAPI(
    title="TF AVM Agent API",
    description="API for generating Terraform code using Azure Verified Modules",
    version=__version__,
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Request/Response Models ==============


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., description="The user's message")
    session_id: str | None = Field(None, description="Session ID for conversation continuity")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    message: str = Field(..., description="The agent's response")
    session_id: str = Field(..., description="Session ID for conversation continuity")
    generated_files: list[dict] | None = Field(None, description="Generated Terraform files if any")


class GenerateRequest(BaseModel):
    """Request model for generate endpoint."""

    services: list[str] = Field(..., description="List of Azure services to include")
    project_name: str = Field(..., description="Name for the Terraform project")
    location: str = Field("eastus", description="Azure region for deployment")
    options: dict | None = Field(None, description="Additional generation options")


class GeneratedFile(BaseModel):
    """Model for a generated file."""

    path: str = Field(..., description="File path")
    content: str = Field(..., description="File content")
    type: str = Field(..., description="File type (terraform, tfvars, markdown, other)")


class GenerateResponse(BaseModel):
    """Response model for generate endpoint."""

    success: bool = Field(..., description="Whether generation was successful")
    files: list[GeneratedFile] = Field(default_factory=list, description="Generated files")
    message: str | None = Field(None, description="Status message")


class IdentifiedService(BaseModel):
    """Model for an identified service from diagram analysis."""

    name: str = Field(..., description="Service name")
    confidence: float = Field(..., description="Confidence score 0-1")
    category: str = Field(..., description="Service category")


class DiagramAnalysisResponse(BaseModel):
    """Response model for diagram analysis endpoint."""

    success: bool = Field(..., description="Whether analysis was successful")
    services: list[IdentifiedService] = Field(default_factory=list, description="Identified services")
    suggested_architecture: str | None = Field(None, description="Suggested architecture description")
    message: str | None = Field(None, description="Status message")


class ModuleInfo(BaseModel):
    """Model for AVM module information."""

    name: str
    description: str
    category: str
    version: str
    source: str
    aliases: list[str] = Field(default_factory=list)
    azure_service: str | None = None


class ModuleListResponse(BaseModel):
    """Response model for module listing."""

    modules: list[ModuleInfo]
    total: int
    categories: list[str] = Field(default_factory=list)


# ============== API Endpoints ==============


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "tf-avm-agent-api"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the agent and get a response.

    This endpoint maintains conversation history using session IDs.
    """
    session_id = request.session_id or str(uuid.uuid4())

    try:
        agent = get_or_create_session(session_id)

        # Run the agent asynchronously
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, agent.run, request.message)

        return ChatResponse(
            message=response,
            session_id=session_id,
            generated_files=None,  # Files are included in the response text
        )

    except Exception as e:
        logger.exception("Error in chat endpoint")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_terraform(request: GenerateRequest):
    """
    Generate Terraform code from a list of Azure services.

    Returns complete Terraform project files using Azure Verified Modules.
    """
    try:
        # Generate the Terraform project
        result = generate_terraform_project(
            project_name=request.project_name,
            services=request.services,
            location=request.location,
        )

        # Convert to response format
        files = []
        for file_info in result.files:
            file_type = "terraform"
            if file_info.filename.endswith(".tfvars"):
                file_type = "tfvars"
            elif file_info.filename.endswith(".md"):
                file_type = "markdown"
            elif not file_info.filename.endswith(".tf"):
                file_type = "other"

            files.append(
                GeneratedFile(
                    path=file_info.filename,
                    content=file_info.content,
                    type=file_type,
                )
            )

        return GenerateResponse(
            success=True,
            files=files,
            message=f"Generated {len(files)} files for project '{request.project_name}'",
        )

    except Exception as e:
        logger.exception("Error in generate endpoint")
        return GenerateResponse(
            success=False,
            files=[],
            message=str(e),
        )


@app.post("/api/analyze", response_model=DiagramAnalysisResponse)
async def analyze_diagram_endpoint(file: UploadFile = File(...)):
    """
    Analyze an uploaded architecture diagram to identify Azure services.

    Accepts image files (PNG, JPG, SVG) and returns identified services
    with confidence scores.
    """
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/svg+xml"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}",
        )

    try:
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename or "diagram").suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Create a new agent for analysis
            agent = TerraformAVMAgent(
                use_azure_openai=bool(os.environ.get("AZURE_OPENAI_ENDPOINT")),
            )

            # Use the run method with a prompt to analyze the diagram
            # This avoids the method signature issue with analyze_diagram
            filename = file.filename or "diagram"
            prompt = f"""Please analyze this architecture diagram located at: {tmp_path}
Filename: {filename}

Identify all Azure services visible in the diagram and list them.
For each service, suggest the appropriate Azure Verified Module (AVM).

End your response with a clear list of services in this format:
**Identified Services:** service1, service2, service3, ..."""

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, agent.run, prompt)

            # Parse the response to extract services
            # The agent returns a text response with identified services
            services = _parse_identified_services(response)

            return DiagramAnalysisResponse(
                success=True,
                services=services,
                suggested_architecture=response,
                message=f"Identified {len(services)} Azure services",
            )

        finally:
            # Clean up temp file
            os.unlink(tmp_path)

    except Exception as e:
        logger.exception("Error in analyze endpoint")
        return DiagramAnalysisResponse(
            success=False,
            services=[],
            message=str(e),
        )


def _parse_identified_services(response: str) -> list[IdentifiedService]:
    """Parse agent response to extract identified services."""
    services = []

    # Look for common Azure service keywords in the response
    service_keywords = {
        "virtual machine": ("Virtual Machine", "compute"),
        "vm": ("Virtual Machine", "compute"),
        "aks": ("Azure Kubernetes Service", "containers"),
        "kubernetes": ("Azure Kubernetes Service", "containers"),
        "app service": ("App Service", "compute"),
        "function": ("Azure Functions", "compute"),
        "container app": ("Container Apps", "containers"),
        "storage account": ("Storage Account", "storage"),
        "blob storage": ("Storage Account", "storage"),
        "sql database": ("Azure SQL Database", "database"),
        "sql server": ("Azure SQL Server", "database"),
        "cosmos": ("Cosmos DB", "database"),
        "postgresql": ("PostgreSQL Flexible Server", "database"),
        "redis": ("Azure Cache for Redis", "database"),
        "key vault": ("Key Vault", "security"),
        "keyvault": ("Key Vault", "security"),
        "virtual network": ("Virtual Network", "networking"),
        "vnet": ("Virtual Network", "networking"),
        "load balancer": ("Load Balancer", "networking"),
        "application gateway": ("Application Gateway", "networking"),
        "front door": ("Front Door", "networking"),
        "private endpoint": ("Private Endpoint", "networking"),
        "event hub": ("Event Hubs", "messaging"),
        "service bus": ("Service Bus", "messaging"),
        "log analytics": ("Log Analytics Workspace", "monitoring"),
        "application insights": ("Application Insights", "monitoring"),
        "openai": ("Azure OpenAI", "ai"),
        "cognitive": ("Cognitive Services", "ai"),
        "machine learning": ("Machine Learning", "ai"),
        "container registry": ("Container Registry", "containers"),
        "acr": ("Container Registry", "containers"),
    }

    response_lower = response.lower()
    seen = set()

    for keyword, (name, category) in service_keywords.items():
        if keyword in response_lower and name not in seen:
            seen.add(name)
            # Higher confidence if explicitly mentioned
            confidence = 0.9 if keyword in response_lower else 0.7
            services.append(
                IdentifiedService(
                    name=name,
                    confidence=confidence,
                    category=category,
                )
            )

    return services


@app.get("/api/modules", response_model=ModuleListResponse)
async def list_modules(
    category: Annotated[str | None, Query(description="Filter by category")] = None,
    search: Annotated[str | None, Query(description="Search query")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """
    List or search available AVM modules.

    Supports filtering by category and searching by name/description.
    """
    try:
        # Get modules based on filters
        if search:
            modules = search_modules(search)
        elif category:
            modules = get_modules_by_category(category)
        else:
            modules = list(AVM_MODULES.values())

        # Get total before pagination
        total = len(modules)

        # Apply pagination
        modules = modules[offset : offset + limit]

        # Convert to response format
        module_list = [
            ModuleInfo(
                name=m.name,
                description=m.description,
                category=m.category,
                version=m.version,
                source=m.source,
                aliases=m.aliases,
                azure_service=m.azure_service,
            )
            for m in modules
        ]

        return ModuleListResponse(
            modules=module_list,
            total=total,
            categories=get_all_categories(),
        )

    except Exception as e:
        logger.exception("Error in modules endpoint")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/modules/{module_name}", response_model=ModuleInfo)
async def get_module(module_name: str):
    """Get detailed information about a specific module."""
    module = get_module_by_service(module_name)

    if not module:
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found")

    return ModuleInfo(
        name=module.name,
        description=module.description,
        category=module.category,
        version=module.version,
        source=module.source,
        aliases=module.aliases,
        azure_service=module.azure_service,
    )


# ============== WebSocket Endpoint ==============


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)


manager = ConnectionManager()


@app.websocket("/api/ws/chat")
async def websocket_chat(websocket: WebSocket, session: str | None = None):
    """
    WebSocket endpoint for streaming chat responses.

    Provides real-time streaming of agent responses for a better UX.
    """
    session_id = session or str(uuid.uuid4())
    await manager.connect(websocket, session_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
                user_message = message_data.get("message", data)
            except json.JSONDecodeError:
                user_message = data

            # Send status update
            await manager.send_message(
                session_id, {"type": "status", "content": "Processing your request..."}
            )

            try:
                # Get or create agent session
                agent = get_or_create_session(session_id)

                # Run the agent
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, agent.run, user_message)

                # Send the response in chunks to simulate streaming
                # In a real implementation, you'd hook into the agent's streaming output
                chunk_size = 100
                for i in range(0, len(response), chunk_size):
                    chunk = response[i : i + chunk_size]
                    await manager.send_message(
                        session_id, {"type": "chat", "content": chunk}
                    )
                    await asyncio.sleep(0.02)  # Small delay for streaming effect

                # Send completion message
                await manager.send_message(
                    session_id,
                    {
                        "type": "complete",
                        "content": "",
                        "metadata": {"session_id": session_id},
                    },
                )

            except Exception as e:
                logger.exception("Error processing WebSocket message")
                await manager.send_message(
                    session_id,
                    {"type": "error", "content": str(e)},
                )

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info(f"WebSocket disconnected: {session_id}")


# ============== Server Entry Point ==============


def main():
    """Run the API server."""
    import uvicorn

    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8000"))
    reload = os.environ.get("API_RELOAD", "false").lower() == "true"

    print(f"Starting TF AVM Agent API on http://{host}:{port}")
    print("API Documentation: http://{host}:{port}/docs")

    uvicorn.run(
        "tf_avm_agent.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
