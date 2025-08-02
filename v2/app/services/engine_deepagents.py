
import asyncio
from typing import List, Dict, Any, Optional
from app.deepagents import create_deep_agent
import httpx
from app.services.engine import (
    AnalysisPipeline,
    AnalysisRequest,
    UnifiedLogEntry,
    update_run_status,
    analysis_runs,
)


async def run_analysis_with_deepagents(
    run_id: str, request: AnalysisRequest, db_session, preloaded_spans: Optional[List[UnifiedLogEntry]] = None
):
    """
    Runs the analysis pipeline using a deep agent.
    """
    update_run_status(run_id, "running", log_message="Starting analysis with deep agents...")

    # 1. Define the tools for the agent
    tools = [
        # Tool for enriching logs
        {
            "name": "enrich_logs",
            "description": "Enriches the raw log data with additional metrics.",
            "input_schema": {"spans": "List of raw log entries"},
            "output_schema": {"enriched_spans": "List of enriched log entries"},
            "model": AnalysisPipeline.log_enricher.enrich_spans,
        },
        # Tool for discovering patterns
        {
            "name": "discover_patterns",
            "description": "Discovers usage patterns in the enriched log data.",
            "input_schema": {"spans": "List of enriched log entries"},
            "output_schema": {"patterns": "List of discovered patterns"},
            "model": AnalysisPipeline.pattern_discoverer.discover_patterns_from_spans,
        },
        # Tool for simulating policies
        {
            "name": "simulate_policies",
            "description": "Simulates different supply options to find the most optimal policies.",
            "input_schema": {
                "patterns": "List of discovered patterns",
                "span_map": "Map of span IDs to spans",
            },
            "output_schema": {"policies": "List of learned policies"},
            "model": AnalysisPipeline.simulation_engine.generate_policies,
        },
        # Tool for calculating final costs
        {
            "name": "calculate_costs",
            "description": "Calculates the final cost comparison.",
            "input_schema": {
                "workloads": "List of workloads",
                "policies": "List of learned policies",
            },
            "output_schema": {"cost_comparison": "The final cost comparison"},
            "model": AnalysisPipeline.simulation_engine.calculate_final_costs,
        },
    ]

    # 2. Define the instructions for the agent
    instructions = """
    You are a powerful analysis agent. Your goal is to analyze the provided log data and generate a comprehensive report.

    Here's the plan:
    1.  Enrich the raw log data.
    2.  Discover usage patterns in the enriched data.
    3.  Simulate different supply options to find the most optimal policies.
    4.  Calculate the final cost comparison.
    """

    # 3. Create the deep agent
    agent = create_deep_agent(tools=tools, instructions=instructions)

    # 4. Run the agent
    try:
        result = await agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Analyze the following request: {request.model_dump_json()}",
                    }
                ],
                "files": {
                    "preloaded_spans.json": preloaded_spans,
                },
            }
        )
        update_run_status(run_id, "completed", "Analysis complete.", result=result)
    except Exception as e:
        update_run_status(run_id, "failed", f"An error occurred: {e}", error=str(e))

