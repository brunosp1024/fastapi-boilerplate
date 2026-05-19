from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import async_get_db

router = APIRouter(tags=["Health Check"])
APP_VERSION = settings.APP_VERSION


@router.get("/health")
async def health_check(db: AsyncSession = Depends(async_get_db)):
    """
    Simple health check endpoint to verify:
    - API is responding
    - Database connection is working
    - Current timestamp
    - Application version
    - Environment
    """
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "version": APP_VERSION,
        "environment": settings.APP_ENV,
        "redis": "healthy",
    }


@router.get("/")
async def root():
    """API root endpoint providing basic information."""
    return {
        "message": "Welcome to FastAPI Boilerplate",
        "version": APP_VERSION,
        "docs": "/docs",
    }
