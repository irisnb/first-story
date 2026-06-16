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
    allow_origins=settings.cors_origins,
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


# Include API routes
app.include_router(router, prefix=settings.api_prefix)

# Mount demo UI at /demo
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/demo", StaticFiles(directory=static_dir, html=True), name="demo")


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
    )


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint - redirects to docs."""
    return {
        "message": "First Story Backend API",
        "docs": "/docs",
        "demo": "/demo",
        "health": "/health",
    }
