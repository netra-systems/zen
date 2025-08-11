from sqlalchemy import text
from fastapi import APIRouter, HTTPException
from app.db.postgres import get_async_db as get_db, async_engine
from app.logging_config import central_logger
from app.services.database_env_service import DatabaseEnvironmentValidator
from app.services.schema_validation_service import SchemaValidationService
from app.config import settings

import asyncio
from typing import Dict, Any

router = APIRouter()
logger = central_logger.get_logger(__name__)

@router.get("/live")
async def live() -> Dict[str, str]:
    """
    Liveness probe to check if the application is running.
    """
    return {"status": "ok"}

@router.get("/ready")
async def ready() -> Dict[str, str]:
    """
    Readiness probe to check if the application is ready to serve requests.
    """
    try:
        # Check Postgres connection
        async with get_db() as db:
            result = await db.execute(text("SELECT 1"))
            result.scalar_one_or_none()

        # Check ClickHouse connection
        from app.db.clickhouse import get_clickhouse_client
        async with get_clickhouse_client() as client:
            client.ping()

        # If all checks pass, return a success response
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        raise HTTPException(status_code=503, detail="Service Unavailable")
    
@router.get("/database-env")
async def database_environment() -> Dict[str, Any]:
    """
    Check database environment configuration and validation status.
    """
    env_info = DatabaseEnvironmentValidator.get_environment_info()
    validation_result = DatabaseEnvironmentValidator.validate_database_url(
        env_info["database_url"], 
        env_info["environment"]
    )
    
    return {
        "environment": env_info["environment"],
        "database_name": validation_result["database_name"],
        "validation": {
            "valid": validation_result["valid"],
            "errors": validation_result["errors"],
            "warnings": validation_result["warnings"]
        },
        "debug_mode": env_info["debug"],
        "safe_database_name": DatabaseEnvironmentValidator.get_safe_database_name(env_info["environment"])
    }
    
@router.get("/schema-validation")
async def schema_validation() -> Dict[str, Any]:
    """
    Run and return comprehensive schema validation results.
    """
    try:
        results = await SchemaValidationService.validate_schema(async_engine)
        return results
    except Exception as e:
        logger.error(f"Schema validation check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
