from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "AI PR Code Reviewer"}


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI PR Code Reviewer API",
        "docs": "/docs",
        "health": "/health",
    }
