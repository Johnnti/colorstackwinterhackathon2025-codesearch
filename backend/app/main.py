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
    
    # CORS middleware MUST be added first (will process last in request chain)
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
    
    # Request logging middleware
    @app.middleware("http")
    async def log_request(request: Request, call_next):
        # Log incoming request
        logger.info(f"📨 {request.method} {request.url.path}")
        
        # Skip body logging for OPTIONS and GET requests
        if request.method not in ["OPTIONS", "GET", "HEAD"]:
            try:
                body = await request.body()
                if body:
                    logger.debug(f"📤 Request body: {body[:500].decode() if isinstance(body, bytes) else body[:500]}")
                # Recreate the request with the body so it can be read again by the handlers
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
            except Exception as e:
                logger.debug(f"Could not log body: {e}")
        
        response = await call_next(request)
        logger.info(f"📫 {request.method} {request.url.path} -> {response.status_code}")
        return response
    
    # Exception handler for validation errors
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(f"❌ Validation error: {exc.errors()}")
        try:
            body = await request.body()
            logger.error(f"📦 Request body: {body.decode() if body else 'empty'}")
        except:
            logger.error("📦 Request body: unable to decode")
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
