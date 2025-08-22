"""
Initialize database tables for Netra application.
Uses environment variables for database configuration.
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add the parent directory to sys.path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
load_dotenv('.env')
load_dotenv('.env.development')
load_dotenv('.env.development.local')

from sqlalchemy.ext.asyncio import create_async_engine

from netra_backend.app.db.base import Base
from netra_backend.app.db.models_postgres import *  # Import all models
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


async def create_tables():
    """Create all database tables."""
    # Get DATABASE_URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    logger.info(f"Connecting to database: {database_url}")
    
    # Create async engine
    engine = create_async_engine(database_url, echo=True)
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("All tables created successfully!")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_tables())