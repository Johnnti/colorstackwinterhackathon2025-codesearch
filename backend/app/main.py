from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import get_settings
from .models import Base, engine
from .routers import analyze_router, github_router, health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: Create database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: cleanup if needed


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        description="AI-powered PR Code Reviewer API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS middleware
    # If using wildcard origins, credentials must be disabled per CORS spec
    allow_credentials = True
    if len(settings.allowed_origins) == 1 and settings.allowed_origins[0] == "*":
        allow_credentials = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health_router)
    app.include_router(analyze_router)
    app.include_router(github_router)
    
    return app


app = create_app()
