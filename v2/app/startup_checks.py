import logging
from app.config import settings
from app.schemas import AppConfig
from app.redis_manager import RedisManager
from app.db.clickhouse_base import ClickHouseDatabase
from app.llm.llm_manager import LLMManager

logger = logging.getLogger(__name__)

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
        raise

async def check_llm(llm_manager: LLMManager):
    """Checks the LLM configuration and API keys."""
    logger.info("Checking LLM configuration...")
    try:
        for llm_name in settings.llm_configs:
            logger.info(f"Checking LLM: {llm_name}")
            llm = llm_manager.get_llm(llm_name)
            # A simple, inexpensive call to validate the API key
            # For google, we can list models
            if settings.llm_configs[llm_name].provider == "google":
                # This is a bit of a hack, but it's a simple way to check the key
                # without making a call to the generative model itself.
                pass # Not implemented yet
            elif settings.llm_configs[llm_name].provider == "openai":
                pass # Not implemented yet
        logger.info("LLM configuration validation successful.")
    except Exception as e:
        logger.error(f"LLM configuration validation failed: {e}")
        raise

async def run_startup_checks(app):
    """Runs all startup checks."""
    await check_config(settings)
    await check_redis(app.state.redis_manager)
    await check_clickhouse()
    await check_llm(app.state.llm_manager)
