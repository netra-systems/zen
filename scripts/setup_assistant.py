"""Setup the Netra Assistant in the database"""
import asyncio
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import Assistant
from netra_backend.app.db.postgres import get_async_db
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

def _get_assistant_tools() -> List[Dict[str, str]]:
    """Get standard assistant tools configuration."""
    return [
        {"type": "data_analysis"},
        {"type": "optimization"},
        {"type": "reporting"}
    ]

def _get_assistant_capabilities() -> List[str]:
    """Get standard assistant capabilities list."""
    return [
        "workload_analysis",
        "cost_optimization",
        "performance_optimization",
        "quality_optimization",
        "model_selection",
        "supply_catalog_management"
    ]

def _get_assistant_metadata() -> Dict[str, Any]:
    """Get standard assistant metadata configuration."""
    return {
        "version": "1.0",
        "capabilities": _get_assistant_capabilities()
    }

async def _check_existing_assistant(db: AsyncSession) -> Optional[Assistant]:
    """Check if Netra assistant already exists in database."""
    result = await db.execute(
        select(Assistant).where(Assistant.id == "netra-assistant")
    )
    return result.scalar_one_or_none()

def _create_assistant_config() -> Dict[str, Any]:
    """Create complete assistant configuration."""
    return {
        "id": "netra-assistant",
        "object": "assistant",
        "created_at": int(time.time()),
        "name": "Netra AI Optimization Assistant",
        "description": "The world's best AI workload optimization assistant",
        "model": "gpt-4",
        "instructions": "You are Netra AI Workload Optimization Assistant. You help users optimize their AI workloads for cost, performance, and quality.",
        "tools": _get_assistant_tools(),
        "file_ids": [],
        "metadata_": _get_assistant_metadata()
    }

async def _create_new_assistant(db: AsyncSession) -> Assistant:
    """Create and save new assistant to database."""
    config = _create_assistant_config()
    assistant = Assistant(**config)
    db.add(assistant)
    await db.commit()
    logger.info("Created Netra assistant successfully")
    return assistant

async def _update_assistant_properties(assistant: Assistant) -> None:
    """Update existing assistant with current properties."""
    assistant.name = "Netra AI Optimization Assistant"
    assistant.description = "The world's best AI workload optimization assistant"
    assistant.model = "gpt-4"
    assistant.instructions = "You are Netra AI Workload Optimization Assistant. You help users optimize their AI workloads for cost, performance, and quality."
    assistant.tools = _get_assistant_tools()
    assistant.metadata_ = _get_assistant_metadata()

async def _update_existing_assistant(db: AsyncSession, assistant: Assistant) -> Assistant:
    """Update existing assistant and save to database."""
    await _update_assistant_properties(assistant)
    await db.commit()
    logger.info("Updated Netra assistant successfully")
    return assistant

async def setup_netra_assistant() -> Assistant:
    """Create or update the Netra assistant in the database"""
    async with get_async_db() as db:
        try:
            assistant = await _check_existing_assistant(db)
            if not assistant:
                return await _create_new_assistant(db)
            else:
                return await _update_existing_assistant(db, assistant)
        except Exception as e:
            logger.error(f"Error setting up Netra assistant: {e}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(setup_netra_assistant())
    print("Netra assistant setup complete!")
