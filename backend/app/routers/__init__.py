from .analyze import router as analyze_router
from .github import router as github_router
from .health import router as health_router

__all__ = ["analyze_router", "github_router", "health_router"]
