from app.logging_config import central_logger
from app.config import settings
from app.schemas import AppConfig
from app.redis_manager import RedisManager
from app.db.clickhouse_base import ClickHouseDatabase
from app.llm.llm_manager import LLMManager
import time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models_postgres import Assistant

logger = central_logger.get_logger(__name__)

async def check_config(settings: AppConfig):
    """Validates the application configuration."""
    if not settings.redis.host:
        raise ValueError("REDIS_HOST is not set.")
    # TBD thinking about how this integrated with existing pydantic auto validations
 

async def check_redis(redis_manager: RedisManager):
    """Checks the connection to Redis."""
    logger.info("Checking Redis connection...")
    try:
        await redis_manager.connect()
        logger.info("Redis connection successful.")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        # In development, Redis is optional
        if settings.environment == "development":
            logger.warning("Redis is not available in development mode - some features may be limited")
        else:
            raise

async def check_clickhouse():
    """Checks the connection to ClickHouse."""
    logger.info("Checking ClickHouse connection...")
    try:
        # The clickhouse_db is initialized in the central_logger, 
        # which is not ideal.
        # For now, we will create a new client to check the connection.
        # This should be refactored to use a single client instance.
        
        from app.db.clickhouse import get_clickhouse_client
        async with get_clickhouse_client() as client:
            client.ping()
        logger.info("ClickHouse connection successful.")
    except Exception as e:
        logger.error(f"ClickHouse connection failed: {e}")
        # In development, ClickHouse is optional
        if settings.environment == "development":
            logger.warning("ClickHouse is not available in development mode - logging features may be limited")
        else:
            raise

async def check_llm(llm_manager: LLMManager):
    """Checks the LLM configuration and API keys."""
    logger.info("Checking LLM configuration...")
    try:
        for llm_name in settings.llm_configs:
            logger.info(f"Checking LLM: {llm_name}")
            llm = llm_manager.get_llm(llm_name)
        logger.info("LLM configuration validation successful.")
    except Exception as e:
        logger.error(f"LLM configuration validation failed: {e}. Check Auth Refresh expires every 16 hours (e.g. gcloud auth application-default login)")
        # In development, LLM configuration is optional
        if settings.environment == "development":
            logger.warning("LLM configuration not available in development mode - AI features will be limited")
        else:
            raise

async def check_or_create_assistant(db_session_factory):
    """Checks if Netra assistant exists, creates it if not."""
    logger.info("Checking Netra assistant...")
    try:
        async with db_session_factory() as db:
            # Check if assistant already exists
            result = await db.execute(
                select(Assistant).where(Assistant.id == "netra-assistant")
            )
            assistant = result.scalar_one_or_none()
            
            if not assistant:
                # Create the assistant
                assistant = Assistant(
                    id="netra-assistant",
                    object="assistant",
                    created_at=int(time.time()),
                    name="Netra AI Optimization Assistant",
                    description="The world's best AI workload optimization assistant",
                    model="gpt-4",
                    instructions="You are Netra AI Workload Optimization Assistant. You help users optimize their AI workloads for cost, performance, and quality.",
                    tools=[
                        {"type": "data_analysis"},
                        {"type": "optimization"},
                        {"type": "reporting"}
                    ],
                    file_ids=[],
                    metadata_={
                        "version": "1.0",
                        "capabilities": [
                            "workload_analysis",
                            "cost_optimization",
                            "performance_optimization",
                            "quality_optimization",
                            "model_selection",
                            "supply_catalog_management"
                        ]
                    }
                )
                db.add(assistant)
                await db.commit()
                logger.info("Created Netra assistant successfully")
            else:
                logger.info("Netra assistant already exists")
    except Exception as e:
        logger.error(f"Failed to check/create Netra assistant: {e}")
        raise

async def run_startup_checks(app):
    """Runs all startup checks."""
    await check_config(settings)
    await check_redis(app.state.redis_manager)
    await check_clickhouse()
    await check_llm(app.state.llm_manager)
    await check_or_create_assistant(app.state.db_session_factory)
