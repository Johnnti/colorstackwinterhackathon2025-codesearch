from fastapi import APIRouter

from ..config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "AI PR Code Reviewer"}


@router.get("/health/cors")
async def health_cors():
    """Expose CORS config for debugging."""
    settings = get_settings()
    return {
        "allowed_origins": settings.allowed_origins,
        "allowed_origin_regex": settings.allowed_origin_regex,
    }


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI PR Code Reviewer API",
        "docs": "/docs",
        "health": "/health",
    }
