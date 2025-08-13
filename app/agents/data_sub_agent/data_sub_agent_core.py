# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-13T00:00:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Core DataSubAgent implementation
# Git: v7 | Module-Refactor | dirty
# Change: Module Extract | Scope: Core | Risk: Low
# Session: module-refactor-session | Seq: 1
# Review: Pending | Score: 100
# ================================

from typing import Dict, Optional, Any
from datetime import datetime, timedelta, UTC

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.prompts import data_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.utils import extract_json_from_response
from app.redis_manager import RedisManager
from app.logging_config import central_logger as logger

from .data_sub_agent_analytics import DataAnalytics


class DataSubAgent(BaseSubAgent):
    """Core DataSubAgent implementation with modular architecture"""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="DataSubAgent", 
                        description="Advanced data gathering and analysis agent with ClickHouse integration.")
        self.tool_dispatcher = tool_dispatcher
        self.cache_ttl = 300  # 5 minutes cache TTL
        
        # Initialize Redis for caching if available
        redis_manager = None
        try:
            redis_manager = RedisManager()
        except Exception as e:
            logger.warning(f"Redis not available for DataSubAgent caching: {e}")
        
        # Initialize analytics module
        self.analytics = DataAnalytics(redis_manager=redis_manager, cache_ttl=self.cache_ttl)
        
        # Store redis manager for state management
        self.redis_manager = redis_manager
    
    async def _send_update(self, run_id: str, update: Dict[str, Any]):
        """Send real-time update via WebSocket"""
        try:
            if hasattr(self, 'ws_manager') and self.ws_manager:
                await self.ws_manager.send_agent_update(run_id, "DataSubAgent", update)
        except Exception as e:
            logger.debug(f"Failed to send WebSocket update: {e}")
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False) -> None:
        """Execute advanced data analysis with ClickHouse integration"""
        
        try:
            # Send initial update
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "started",
                    "message": "Starting advanced data analysis..."
                })
            
            # Extract parameters from triage result
            triage_result = state.triage_result or {}
            key_params = triage_result.get("key_parameters", {})
            
            # Determine analysis parameters
            user_id = key_params.get("user_id", 1)  # Default user for demo
            workload_id = key_params.get("workload_id")
            metric_names = key_params.get("metrics", ["latency_ms", "throughput", "cost_cents"])
            time_range_str = key_params.get("time_range", "last_24_hours")
            
            # Parse time range
            end_time = datetime.now(UTC)
            if time_range_str == "last_hour":
                start_time = end_time - timedelta(hours=1)
            elif time_range_str == "last_24_hours":
                start_time = end_time - timedelta(days=1)
            elif time_range_str == "last_week":
                start_time = end_time - timedelta(weeks=1)
            elif time_range_str == "last_month":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(days=1)  # Default to last 24 hours
            
            time_range = (start_time, end_time)
            
            # Perform analyses based on intent
            intent = triage_result.get("intent", {})
            primary_intent = intent.get("primary", "general")
            
            data_result = {
                "analysis_type": primary_intent,
                "parameters": {
                    "user_id": user_id,
                    "workload_id": workload_id,
                    "time_range": {
                        "start": start_time.isoformat(),
                        "end": end_time.isoformat()
                    },
                    "metrics": metric_names
                },
                "results": {}
            }
            
            # Execute appropriate analyses
            if primary_intent in ["optimize", "performance"]:
                if stream_updates:
                    await self._send_update(run_id, {
                        "status": "analyzing",
                        "message": "Analyzing performance metrics..."
                    })
                
                perf_analysis = await self.analytics.analyze_performance_metrics(
                    user_id, workload_id, time_range
                )
                data_result["results"]["performance"] = perf_analysis
                
                # Check for anomalies in key metrics
                for metric in ["latency_ms", "error_rate"]:
                    anomalies = await self.analytics.detect_anomalies(
                        user_id, metric, time_range
                    )
                    if anomalies.get("anomaly_count", 0) > 0:
                        data_result["results"][f"{metric}_anomalies"] = anomalies
            
            elif primary_intent == "analyze":
                if stream_updates:
                    await self._send_update(run_id, {
                        "status": "analyzing",
                        "message": "Performing correlation analysis..."
                    })
                
                # Correlation analysis
                correlations = await self.analytics.analyze_correlations(
                    user_id, metric_names, time_range
                )
                data_result["results"]["correlations"] = correlations
                
                # Usage patterns
                usage_patterns = await self.analytics.analyze_usage_patterns(user_id)
                data_result["results"]["usage_patterns"] = usage_patterns
            
            elif primary_intent == "monitor":
                if stream_updates:
                    await self._send_update(run_id, {
                        "status": "analyzing",
                        "message": "Checking for anomalies..."
                    })
                
                # Anomaly detection for all metrics
                for metric in metric_names:
                    anomalies = await self.analytics.detect_anomalies(
                        user_id, metric, time_range, z_score_threshold=2.5
                    )
                    data_result["results"][f"{metric}_monitoring"] = anomalies
            
            else:
                # Default: comprehensive analysis
                if stream_updates:
                    await self._send_update(run_id, {
                        "status": "analyzing",
                        "message": "Performing comprehensive analysis..."
                    })
                
                # Performance metrics
                perf_analysis = await self.analytics.analyze_performance_metrics(
                    user_id, workload_id, time_range
                )
                data_result["results"]["performance"] = perf_analysis
                
                # Usage patterns
                usage_patterns = await self.analytics.analyze_usage_patterns(user_id, 7)
                data_result["results"]["usage_patterns"] = usage_patterns
            
            # Store result in state
            state.data_result = data_result
            
            # Update with results
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "completed",
                    "message": "Advanced data analysis completed successfully",
                    "result": data_result
                })
            
            logger.info(f"DataSubAgent completed analysis for run_id: {run_id}")
            
        except Exception as e:
            logger.error(f"DataSubAgent execution failed: {e}")
            
            # Fallback to basic LLM-based data gathering
            prompt = data_prompt_template.format(
                triage_result=state.triage_result,
                user_request=state.user_request,
                thread_id=run_id
            )
            
            llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='data')
            data_result = extract_json_from_response(llm_response_str)
            
            if not data_result:
                data_result = {
                    "collection_status": "fallback",
                    "data": "Limited data available due to connection issues",
                    "error": str(e)
                }
            
            state.data_result = data_result
            
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "completed_with_fallback",
                    "message": "Data gathering completed with fallback method",
                    "result": data_result
                })