# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:48:31.173913+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to apex optimizer tools
# Git: v6 | be70ff77 | clean
# Change: Feature | Scope: Module | Risk: High
# Session: f4b153af-998e-4648-bfed-e03ac78b4b8f | Seq: 4
# Review: Pending | Score: 85
# ================================
from typing import Any, List

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.context import ToolContext

logger = central_logger.get_logger(__name__)

async def cost_analyzer(context: ToolContext) -> str:
    """Analyzes the current costs of the system."""
    logger.info(f"Starting cost analysis for {len(context.logs)} logs")
    
    try:
        total_cost = 0
        for log in context.logs:
            cost_result = await context.cost_estimator.execute(log.request.prompt_text, log.model_dump())
            total_cost += cost_result["estimated_cost_usd"]
        
        logger.info(f"Cost analysis complete. Total estimated cost: ${total_cost:.2f}")
        return f"Analyzed current costs. Total estimated cost: ${total_cost:.2f}"
    
    except Exception as e:
        logger.error(f"Cost analysis failed: {e}", exc_info=True)
        raise