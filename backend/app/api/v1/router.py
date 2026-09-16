"""FastAPI Router registration."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check():
    """System liveness health check."""
    return {
        "status": "healthy",
        "service": "skyguard-ai-backend",
        "version": "0.1.0"
    }
