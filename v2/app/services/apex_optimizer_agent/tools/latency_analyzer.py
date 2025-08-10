# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:48:31.173913+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to apex optimizer tools
# Git: v6 | be70ff77 | clean
# Change: Feature | Scope: Module | Risk: High
# Session: f4b153af-998e-4648-bfed-e03ac78b4b8f | Seq: 5
# Review: Pending | Score: 85
# ================================
from langchain_core.tools import tool
from typing import List, Any
from app.services.context import ToolContext

@tool
async def latency_analyzer(context: ToolContext) -> str:
    """Analyzes the current latency of the system."""
    total_latency = 0
    for log in context.logs:
        latency_result = await context.performance_predictor.execute(log.request.prompt_text, log.model_dump())
        total_latency += latency_result["predicted_latency_ms"]
    
    average_latency = total_latency / len(context.logs) if context.logs else 0
    
    return f"Analyzed current latency. Average predicted latency: {average_latency:.2f}ms"