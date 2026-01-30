"""
Diagram Analyzer Tool.

This tool analyzes architecture diagrams (images) to extract Azure services
and their relationships for Terraform code generation.
"""

import base64
import re
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field


class ArchitectureComponent(BaseModel):
    """Represents a component identified in an architecture diagram."""

    name: str = Field(description="The name/label of the component")
    service_type: str = Field(description="The Azure service type (e.g., 'Virtual Machine', 'Storage Account')")
    connections: list[str] = Field(default_factory=list, description="Names of connected components")
    properties: dict[str, str] = Field(default_factory=dict, description="Additional properties identified")


class DiagramAnalysisResult(BaseModel):
    """Result of analyzing an architecture diagram."""

    components: list[ArchitectureComponent] = Field(default_factory=list)
    description: str = Field(default="", description="Overall description of the architecture")
    regions: list[str] = Field(default_factory=list, description="Azure regions identified")
    resource_groups: list[str] = Field(default_factory=list, description="Resource groups identified")
    networking_topology: str = Field(default="", description="Description of the networking setup")
    security_components: list[str] = Field(default_factory=list, description="Security components identified")
    raw_analysis: str = Field(default="", description="Raw analysis text from the model")


def encode_image_to_base64(image_path: str) -> str:
    """Encode an image file to base64 string."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_media_type(image_path: str) -> str:
    """Get the media type based on file extension."""
    ext = Path(image_path).suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }
    return media_types.get(ext, "image/png")


def is_url(path: str) -> bool:
    """Check if a path is a URL."""
    try:
        result = urlparse(path)
        return result.scheme in ('http', 'https')
    except:
        return False


def download_image_from_url(url: str) -> tuple[bytes, str]:
    """
    Download an image from a URL.
    
    Args:
        url: The URL of the image
        
    Returns:
        Tuple of (image_bytes, media_type)
    """
    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        response = client.get(url)
        response.raise_for_status()
        
        # Get media type from Content-Type header or URL
        content_type = response.headers.get('content-type', '')
        if 'image/' in content_type:
            media_type = content_type.split(';')[0].strip()
        else:
            # Infer from URL
            media_type = get_image_media_type(url)
        
        return response.content, media_type


def encode_image_from_url(url: str) -> tuple[str, str]:
    """
    Download and encode an image from a URL to base64.
    
    Args:
        url: The URL of the image
        
    Returns:
        Tuple of (base64_encoded_data, media_type)
    """
    image_bytes, media_type = download_image_from_url(url)
    base64_data = base64.b64encode(image_bytes).decode('utf-8')
    return base64_data, media_type


def get_filename_from_url(url: str) -> str:
    """Extract filename from URL."""
    parsed = urlparse(url)
    path = parsed.path
    return Path(path).name if path else "diagram"


# Prompt for analyzing architecture diagrams
DIAGRAM_ANALYSIS_PROMPT = """Analyze this Azure architecture diagram and extract the following information:

1. **Components**: List all Azure services/resources shown in the diagram with their:
   - Name/label (as shown in the diagram)
   - Service type (e.g., "Virtual Machine", "App Service", "Storage Account", "Virtual Network", etc.)
   - Connections to other components

2. **Regions**: Any Azure regions shown or implied

3. **Resource Groups**: Any resource group boundaries shown

4. **Networking**: Describe the networking topology including:
   - Virtual Networks
   - Subnets
   - Load Balancers
   - Firewalls/NSGs
   - Connectivity patterns (hub-spoke, mesh, etc.)

5. **Security Components**: List any security-related components like:
   - Key Vault
   - Managed Identities
   - Private Endpoints
   - Firewalls

Please structure your response as JSON with the following format:
{
  "description": "Overall description of the architecture",
  "components": [
    {
      "name": "component name",
      "service_type": "Azure service type",
      "connections": ["connected component names"],
      "properties": {"key": "value"}
    }
  ],
  "regions": ["region names"],
  "resource_groups": ["resource group names"],
  "networking_topology": "description of networking",
  "security_components": ["security component names"]
}

Focus on identifying Azure services that can be deployed using Terraform Azure Verified Modules (AVM).
Common services to look for:
- Compute: Virtual Machines, VM Scale Sets, Container Apps, AKS, Functions, App Service
- Networking: Virtual Networks, Subnets, Load Balancers, Application Gateway, Front Door, VPN Gateway, Bastion
- Storage: Storage Accounts, Blob, Files, Data Lake
- Databases: SQL Database, PostgreSQL, MySQL, Cosmos DB, Redis
- Security: Key Vault, Managed Identity
- Messaging: Event Hub, Service Bus, Event Grid
- Monitoring: Log Analytics, Application Insights
- AI: Cognitive Services, Azure OpenAI, Machine Learning
"""


def analyze_architecture_diagram(
    image_path: Annotated[str, Field(description="Path to the architecture diagram image file")],
) -> DiagramAnalysisResult:
    """
    Analyze an architecture diagram to extract Azure services and their relationships.

    This is a tool function that will be called by the agent. The actual image analysis
    is performed by the LLM using vision capabilities. This function prepares the image
    and returns a structured result.

    Args:
        image_path: Path to the architecture diagram image file (PNG, JPG, etc.)

    Returns:
        DiagramAnalysisResult containing identified components and their relationships
    """
    # This function is a placeholder that structures the tool interface.
    # The actual implementation uses the LLM's vision capabilities through
    # the agent framework. The function signature and return type inform
    # the agent how to use this tool.

    # Validate the image exists
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Validate file type
    valid_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    if path.suffix.lower() not in valid_extensions:
        raise ValueError(f"Unsupported image format: {path.suffix}. Supported formats: {valid_extensions}")

    # Return a placeholder result - the actual analysis is done by the agent
    # using the LLM's vision capabilities
    return DiagramAnalysisResult(
        description="Image loaded successfully. Awaiting analysis.",
        raw_analysis=f"Image path: {image_path}, Size: {path.stat().st_size} bytes",
    )


def create_vision_message_content(image_path: str, prompt: str | None = None) -> list[dict]:
    """
    Create message content for vision analysis including the image.

    Args:
        image_path: Path to the image file
        prompt: Optional custom prompt (uses default if not provided)

    Returns:
        List of message content blocks for the LLM
    """
    image_data = encode_image_to_base64(image_path)
    media_type = get_image_media_type(image_path)
    analysis_prompt = prompt or DIAGRAM_ANALYSIS_PROMPT

    return [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": image_data,
            },
        },
        {
            "type": "text",
            "text": analysis_prompt,
        },
    ]


def parse_diagram_analysis_response(response_text: str) -> DiagramAnalysisResult:
    """
    Parse the LLM response into a structured DiagramAnalysisResult.

    Args:
        response_text: The raw text response from the LLM

    Returns:
        Structured DiagramAnalysisResult
    """
    import json
    import re

    # Try to extract JSON from the response
    json_match = re.search(r"\{[\s\S]*\}", response_text)
    if json_match:
        try:
            data = json.loads(json_match.group())

            components = []
            for comp in data.get("components", []):
                components.append(
                    ArchitectureComponent(
                        name=comp.get("name", "Unknown"),
                        service_type=comp.get("service_type", "Unknown"),
                        connections=comp.get("connections", []),
                        properties=comp.get("properties", {}),
                    )
                )

            return DiagramAnalysisResult(
                components=components,
                description=data.get("description", ""),
                regions=data.get("regions", []),
                resource_groups=data.get("resource_groups", []),
                networking_topology=data.get("networking_topology", ""),
                security_components=data.get("security_components", []),
                raw_analysis=response_text,
            )
        except json.JSONDecodeError:
            pass

    # If JSON parsing fails, return with raw analysis
    return DiagramAnalysisResult(
        description="Could not parse structured response",
        raw_analysis=response_text,
    )
