"""Setup the Netra Assistant in the database"""
import asyncio
import time
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgres import get_async_db
from app.db.models_postgres import Assistant
from sqlalchemy import select
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

async def setup_netra_assistant():
    """Create or update the Netra assistant in the database"""
    async with get_async_db() as db:
        try:
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
                # Update existing assistant
                assistant.name = "Netra AI Optimization Assistant"
                assistant.description = "The world's best AI workload optimization assistant"
                assistant.model = "gpt-4"
                assistant.instructions = "You are Netra AI Workload Optimization Assistant. You help users optimize their AI workloads for cost, performance, and quality."
                assistant.tools = [
                    {"type": "data_analysis"},
                    {"type": "optimization"},
                    {"type": "reporting"}
                ]
                assistant.metadata_ = {
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
                await db.commit()
                logger.info("Updated Netra assistant successfully")
            
            return assistant
            
        except Exception as e:
            logger.error(f"Error setting up Netra assistant: {e}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(setup_netra_assistant())
    print("Netra assistant setup complete!")