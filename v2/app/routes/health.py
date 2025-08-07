from sqlalchemy import text
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgres import get_async_db as get_db
from app.logging_config import central_logger
import logging
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/live")
async def live():
    """
    Liveness probe to check if the application is running.
    """
    return {"status": "ok"}

@router.get("/ready")
async def ready(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe to check if the application is ready to serve requests.
    """
    try:
        # Check Postgres connection
        result = await db.execute(text("SELECT 1"))
        result.scalar_one_or_none()

        # Check ClickHouse connection
        clickhouse_client = central_logger.clickhouse_db
        if not await asyncio.to_thread(clickhouse_client.ping):
            raise Exception("ClickHouse connection failed")

        # If all checks pass, return a success response
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        raise HTTPException(status_code=503, detail="Service Unavailable")