from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import Request
from contextlib import asynccontextmanager
import logging

from .config import get_settings
from .models import Base, engine
from .routers import analyze_router, github_router, health_router

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created")
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
    
    # CORS configuration
    allow_credentials = True
    if len(settings.allowed_origins) == 1 and settings.allowed_origins[0] == "*":
        allow_credentials = False

    logger.info(f"🔓 CORS Origins: {settings.allowed_origins}")
    logger.info(f"🔐 CORS Credentials: {allow_credentials}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_origin_regex=settings.allowed_origin_regex,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
    )
    
    # Exception handler for validation errors
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(f"❌ Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()}
        )
    
    
    # Include routers
    app.include_router(health_router)
    app.include_router(analyze_router)
    app.include_router(github_router)
    
    return app


app = create_app()
