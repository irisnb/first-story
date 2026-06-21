"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .config import get_settings
from .models import ErrorResponse, HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup: ensure projects directory exists
    settings = get_settings()
    settings.projects_root.mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="First Story Backend",
    description="Backend API for First Story - a screenplay writing assistant",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Exception handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(
            ErrorResponse(detail=str(exc), status=500)
        ),
    )


# Include API routes FIRST (before frontend catch-all)
app.include_router(router, prefix=settings.api_prefix)

# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
    )


# Mount demo UI at /demo
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/demo", StaticFiles(directory=static_dir, html=True), name="demo")

# Mount frontend dist at root (for production)
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    # Mount assets first (more specific path)
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    # Mount index.html for SPA fallback - but NOT for /api or /health paths
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}", tags=["frontend"])
    async def serve_frontend(full_path: str):
        """Serve frontend SPA."""
        # Check if requesting a specific file
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for SPA routing
        return FileResponse(frontend_dist / "index.html")
