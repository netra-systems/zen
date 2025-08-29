"""Assistant Repository Implementation

Handles all assistant-related database operations.
"""

import time
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import Assistant
from netra_backend.app.llm.llm_defaults import LLMModel
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.database.base_repository import BaseRepository

logger = central_logger.get_logger(__name__)

class AssistantRepository(BaseRepository[Assistant]):
    """Repository for Assistant entities"""
    
    def __init__(self):
        super().__init__(Assistant)
    
    async def ensure_netra_assistant(self, db: AsyncSession) -> Assistant:
        """Ensure the Netra assistant exists, creating it if necessary."""
        try:
            # Check if assistant already exists
            result = await db.execute(
                select(Assistant).where(Assistant.id == "netra-assistant")
            )
            assistant = result.scalar_one_or_none()
            
            if assistant:
                logger.debug("Netra assistant already exists")
                return assistant
            
            # Create the assistant if it doesn't exist
            logger.info("Creating Netra assistant")
            assistant = self._build_netra_assistant()
            db.add(assistant)
            await db.commit()
            await db.refresh(assistant)
            
            logger.info("Netra assistant created successfully")
            return assistant
            
        except Exception as e:
            logger.error(f"Error ensuring Netra assistant: {e}")
            await db.rollback()
            raise
    
    def _build_netra_assistant(self) -> Assistant:
        """Build the Netra assistant instance with all properties."""
        return Assistant(
            id="netra-assistant",
            object="assistant",
            created_at=int(time.time()),
            name="Netra AI Optimization Assistant",
            model=LLMModel.GEMINI_2_5_FLASH.value,
            description="The world's best AI workload optimization assistant",
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
    
    async def get_by_id(self, db: AsyncSession, assistant_id: str) -> Optional[Assistant]:
        """Get assistant by ID."""
        try:
            result = await db.execute(
                select(Assistant).where(Assistant.id == assistant_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting assistant {assistant_id}: {e}")
            return None
    
    async def find_by_user(self, db: AsyncSession, user_id: str) -> list[Assistant]:
        """Find assistants by user - currently returns the default assistant."""
        # For now, we just have one global assistant
        assistant = await self.ensure_netra_assistant(db)
        return [assistant] if assistant else []