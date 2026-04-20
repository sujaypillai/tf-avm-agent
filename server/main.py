"""
MCP server for tf-avm-agent.

Wraps the existing Python API (TerraformAVMAgent, generate_terraform, etc.) and
exposes it over the Model Context Protocol using streamable HTTP transport so
AI clients (Claude, VS Code Copilot, Cursor, ...) can call the agent remotely.

Design notes:
  * FastMCP's streamable_http_app() serves "/mcp" internally. We mount it at "/"
    so the public endpoint is "/mcp" -- NOT "/mcp/mcp" (a common 404 trap).
  * Azure Container Apps default probes use GET, but /mcp is POST-only. We add
    a dedicated GET /health endpoint so probes don't cause restart loops.
  * Session manager must run inside an async lifespan; if you skip this the
    server returns 500s on every request with "Task group is not initialized".
  * API-key auth middleware is opt-in (set MCP_API_KEY). Off by default so local
    `mcp dev` / Inspector just works.

Env vars:
  MCP_API_KEY             - if set, every request to /mcp must send
                            `x-api-key: <value>` (or `Authorization: Bearer <value>`)
  PORT                    - listen port (default 8000)
  LOG_LEVEL               - uvicorn log level (default info)
  TF_AVM_DEFAULT_LOCATION - default Azure region for generate_terraform
                            (default eastus)
  OPENAI_API_KEY / AZURE_OPENAI_* - consumed by tf_avm_agent itself
"""

from __future__ import annotations

import base64
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from tf_avm_agent import TerraformAVMAgent

log = logging.getLogger("tf-avm-mcp")

# ---------------------------------------------------------------------------
# MCP server + tools
# ---------------------------------------------------------------------------

# stateless_http=False keeps MCP session state in-memory. Combined with ACA
# sticky sessions, a single client hits the same replica for the life of its
# session. If you ever need to run truly stateless (scale-out without sticky
# sessions), flip this to True -- but you lose progress notifications.
mcp = FastMCP("tf-avm-agent", stateless_http=False)
_agent = TerraformAVMAgent()
_DEFAULT_LOCATION = os.getenv("TF_AVM_DEFAULT_LOCATION", "eastus")


@mcp.tool()
def list_modules(category: str | None = None) -> str:
    """List Azure Verified Modules known to the agent.

    Args:
        category: Optional filter, e.g. "networking", "compute", "database".
                  When omitted, all modules are returned.
    """
    return _agent.list_modules(category=category) if category else _agent.list_modules()


@mcp.tool()
def search_modules(query: str) -> str:
    """Search AVM modules by free-text query (e.g. "kubernetes", "postgres")."""
    return _agent.search_modules(query)


@mcp.tool()
def module_info(name: str) -> str:
    """Return detailed information for a single AVM module (e.g. "virtual_machine")."""
    return _agent.get_module_info(name)


@mcp.tool()
def generate_terraform(
    services: list[str],
    project_name: str,
    location: str | None = None,
) -> dict[str, Any]:
    """Generate a complete Terraform project using Azure Verified Modules.

    Writes files to a temporary directory and returns their contents inline so
    the MCP client can render/save them. Nothing is persisted on the server.

    Args:
        services:     Service keys, e.g. ["virtual_machine", "storage_account", "key_vault"].
        project_name: Terraform project name (becomes the dir name).
        location:     Azure region. Defaults to $TF_AVM_DEFAULT_LOCATION or "eastus".
    """
    if not services:
        raise ValueError("services must be a non-empty list")

    loc = location or _DEFAULT_LOCATION
    with tempfile.TemporaryDirectory(prefix="tf-avm-") as tmp:
        result = _agent.generate_from_services(
            services=services,
            project_name=project_name,
            location=loc,
            output_dir=tmp,
        )
        project_dir = Path(tmp) / project_name
        files = {
            p.relative_to(project_dir).as_posix(): p.read_text(encoding="utf-8")
            for p in project_dir.rglob("*")
            if p.is_file()
        }

    return {
        "project_name": project_name,
        "location": loc,
        "services": services,
        "files": files,
        "summary": result.get("summary") if isinstance(result, dict) else None,
    }


@mcp.tool()
def analyze_diagram(
    image_base64: str,
    project_name: str,
    location: str | None = None,
) -> dict[str, Any]:
    """Analyse an architecture diagram and generate Terraform from it.

    Args:
        image_base64: Base64-encoded PNG/JPG of the architecture diagram.
        project_name: Terraform project name.
        location:     Azure region. Defaults to $TF_AVM_DEFAULT_LOCATION or "eastus".
    """
    try:
        raw = base64.b64decode(image_base64, validate=True)
    except Exception as exc:
        raise ValueError(f"image_base64 is not valid base64: {exc}") from exc

    loc = location or _DEFAULT_LOCATION
    with tempfile.TemporaryDirectory(prefix="tf-avm-diag-") as tmp:
        img_path = Path(tmp) / "diagram.png"
        img_path.write_bytes(raw)
        response = _agent.analyze_diagram(
            image_path=str(img_path),
            project_name=project_name,
            location=loc,
            output_dir=tmp,
        )
    return {"project_name": project_name, "location": loc, "response": response}


# ---------------------------------------------------------------------------
# FastAPI wrapper: health probe + optional auth + CORS
# ---------------------------------------------------------------------------

class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Guard the MCP endpoint with a shared secret.

    No-op when MCP_API_KEY is unset. /health is always public so ACA probes
    don't get 401s.
    """

    def __init__(self, app, api_key: str | None) -> None:
        super().__init__(app)
        self._api_key = api_key

    async def dispatch(self, request: Request, call_next):
        if not self._api_key or not request.url.path.startswith("/mcp"):
            return await call_next(request)

        header = request.headers.get("x-api-key")
        if not header:
            auth = request.headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                header = auth.split(" ", 1)[1]

        if header != self._api_key:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def _cors_origins() -> list[str]:
    raw = os.getenv(
        "MCP_CORS_ORIGINS",
        "https://vscode.dev,vscode-webview://*,https://claude.ai",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


def create_app() -> FastAPI:
    # Build the MCP ASGI app FIRST -- FastMCP creates its session manager
    # lazily inside streamable_http_app(), so referencing mcp.session_manager
    # before this call raises RuntimeError at startup.
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Start/stop FastMCP's session manager alongside FastAPI."""
        async with mcp.session_manager.run():
            yield

    app = FastAPI(
        title="tf-avm-agent MCP server",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
        # Mcp-Session-Id is required for streamable-HTTP session resumption
        allow_headers=["*", "Mcp-Session-Id", "x-api-key", "Authorization"],
        expose_headers=["Mcp-Session-Id"],
        allow_credentials=False,
    )
    app.add_middleware(ApiKeyMiddleware, api_key=os.getenv("MCP_API_KEY"))

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        """Liveness/readiness probe. Always 200 while the process is up."""
        return {"status": "ok"}

    # Mount FastMCP at root -> public endpoint is /mcp (not /mcp/mcp).
    app.mount("/", mcp_app)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "info").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",  # noqa: S104 -- container workload
        port=int(os.getenv("PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "info"),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )