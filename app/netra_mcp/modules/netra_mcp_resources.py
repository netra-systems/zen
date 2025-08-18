"""Netra MCP Server Resources Registration"""

import json
from datetime import datetime, timedelta, UTC
from typing import Dict, Any

from app.logging_config import CentralLogger

logger = CentralLogger()


class NetraMCPResources:
    """Resource registration for Netra MCP Server"""
    
    def __init__(self, mcp_instance):
        self.mcp = mcp_instance
        
    def register_all(self, server):
        """Register all resources with the MCP server"""
        self._register_optimization_history(server)
        self._register_model_configs(server)
        self._register_agent_catalog(server)
        self._register_current_metrics(server)
    
    def _register_optimization_history(self, server):
        """Register optimization history resource"""
        @self.mcp.resource("netra://optimization/history")
        async def get_optimization_history() -> str:
            """Get historical optimization results and recommendations"""
            try:
                result = await self._get_optimization_data(server)
                return self._format_optimization_response(result)
            except Exception as e:
                return self._handle_optimization_error(e)
    
    def _register_model_configs(self, server):
        """Register model configuration resource"""
        @self.mcp.resource("netra://config/models")
        async def get_model_configurations() -> str:
            """Get configured model parameters and settings"""
            configs = self._build_model_configs()
            return self._format_config_response(configs)
    
    def _register_agent_catalog(self, server):
        """Register agent catalog resource"""
        @self.mcp.resource("netra://agents/catalog")
        async def get_agent_catalog() -> str:
            """Get detailed catalog of available agents"""
            catalog = self._build_agent_catalog()
            return self._format_catalog_response(catalog)
    
    def _build_agent_catalog(self) -> Dict[str, Any]:
        """Build complete agent catalog structure"""
        return {
            "agents": {
                **self._create_supervisor_agent_spec(),
                **self._create_optimization_agent_spec()
            }
        }
    
    def _create_supervisor_agent_spec(self) -> Dict[str, Dict[str, Any]]:
        """Create SupervisorAgent specification"""
        return {
            "SupervisorAgent": {
                "description": "Main orchestrator for multi-agent workflows",
                "capabilities": self._get_supervisor_capabilities(),
                "input_schema": self._get_supervisor_schema(),
                "example_usage": self._get_supervisor_example()
            }
        }
    
    def _create_optimization_agent_spec(self) -> Dict[str, Dict[str, Any]]:
        """Create OptimizationsCoreSubAgent specification"""
        return {
            "OptimizationsCoreSubAgent": {
                "description": "Core optimization engine",
                "capabilities": self._get_optimization_capabilities(),
                "optimization_strategies": self._get_optimization_strategies()
            }
        }
    
    def _get_supervisor_capabilities(self) -> list:
        """Get SupervisorAgent capabilities list"""
        return [
            "Task decomposition",
            "Agent coordination",
            "Result aggregation",
            "Error recovery"
        ]
    
    def _get_supervisor_schema(self) -> Dict[str, Any]:
        """Get SupervisorAgent input schema"""
        return {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "context": {"type": "object"},
                "goals": {"type": "array"}
            }
        }
    
    def _get_supervisor_example(self) -> Dict[str, Any]:
        """Get SupervisorAgent example usage"""
        return {
            "task": "Optimize our LLM usage for cost",
            "context": {"current_spend": 50000},
            "goals": ["reduce_cost", "maintain_quality"]
        }
    
    def _get_optimization_capabilities(self) -> list:
        """Get optimization agent capabilities"""
        return [
            "Prompt optimization",
            "Model selection",
            "Batch processing strategies",
            "Caching recommendations"
        ]
    
    def _get_optimization_strategies(self) -> list:
        """Get optimization strategies list"""
        return [
            "prompt_compression",
            "model_downgrade",
            "response_caching",
            "batch_aggregation"
        ]
    
    def _register_current_metrics(self, server):
        """Register current metrics resource"""
        @self.mcp.resource("netra://metrics/current")
        async def get_current_metrics() -> str:
            """Get current system metrics and performance indicators"""
            try:
                metrics = await self._collect_system_metrics(server)
                return self._format_metrics_response(metrics)
            except Exception as e:
                return self._format_error_response(e)
    
    async def _collect_system_metrics(self, server) -> Dict[str, Any]:
        """Collect comprehensive system metrics"""
        metrics = self._create_base_metrics()
        await self._add_thread_metrics(server, metrics)
        await self._add_llm_metrics(server, metrics)
        self._ensure_fallback_metrics(metrics)
        return metrics
    
    def _create_base_metrics(self) -> Dict[str, Any]:
        """Create base metrics structure with timestamp"""
        return {"timestamp": datetime.now(UTC).isoformat()}
    
    async def _add_thread_metrics(self, server, metrics: Dict[str, Any]) -> None:
        """Add thread service metrics if available"""
        if not server.thread_service:
            return
        thread_metrics = await server.thread_service.get_metrics()
        if thread_metrics:
            self._update_thread_metrics(metrics, thread_metrics)
    
    def _update_thread_metrics(self, metrics: Dict[str, Any], thread_data: Dict[str, Any]) -> None:
        """Update metrics with thread data"""
        metrics.update({
            "active_threads": thread_data.get("active_threads", 0),
            "queue_depth": thread_data.get("queue_depth", 0)
        })
    
    async def _add_llm_metrics(self, server, metrics: Dict[str, Any]) -> None:
        """Add LLM manager metrics if available"""
        if not server.llm_manager:
            return
        llm_metrics = await server.llm_manager.get_metrics()
        if llm_metrics:
            self._update_llm_metrics(metrics, llm_metrics)
    
    def _update_llm_metrics(self, metrics: Dict[str, Any], llm_data: Dict[str, Any]) -> None:
        """Update metrics with LLM performance data"""
        metrics.update({
            "throughput": self._build_throughput_metrics(llm_data),
            "latency": self._build_latency_metrics(llm_data),
            "cost": self._build_cost_metrics(llm_data),
            "error_rate": llm_data.get("error_rate", 0)
        })
    
    def _build_throughput_metrics(self, llm_data: Dict[str, Any]) -> Dict[str, int]:
        """Build throughput metrics section"""
        return {
            "requests_per_minute": llm_data.get("rpm", 0),
            "tokens_per_minute": llm_data.get("tpm", 0)
        }
    
    def _build_latency_metrics(self, llm_data: Dict[str, Any]) -> Dict[str, int]:
        """Build latency metrics section"""
        return {
            "p50": llm_data.get("latency_p50", 0),
            "p95": llm_data.get("latency_p95", 0),
            "p99": llm_data.get("latency_p99", 0)
        }
    
    def _build_cost_metrics(self, llm_data: Dict[str, Any]) -> Dict[str, float]:
        """Build cost metrics section"""
        return {
            "last_hour": llm_data.get("cost_last_hour", 0),
            "today": llm_data.get("cost_today", 0),
            "this_month": llm_data.get("cost_month", 0)
        }
    
    def _ensure_fallback_metrics(self, metrics: Dict[str, Any]) -> None:
        """Add fallback metrics if real data unavailable"""
        if "throughput" not in metrics:
            self._add_sample_metrics(metrics)
    
    def _add_sample_metrics(self, metrics: Dict[str, Any]) -> None:
        """Add sample metrics as fallback"""
        sample_data = self._get_sample_metrics_data()
        metrics.update(sample_data)
    
    def _get_sample_metrics_data(self) -> Dict[str, Any]:
        """Get sample metrics data structure"""
        return {
            "throughput": {"requests_per_minute": 1250, "tokens_per_minute": 450000},
            "latency": {"p50": 120, "p95": 450, "p99": 890},
            "cost": {"last_hour": 125.50, "today": 2450.75, "this_month": 45600.00},
            "error_rate": 0.02, "active_threads": 45, "queue_depth": 12
        }
    
    def _format_error_response(self, error: Exception) -> str:
        """Format error response for metrics"""
        logger.error(f"Error retrieving current metrics: {error}")
        return json.dumps({"error": str(error)}, indent=2)
    
    async def _get_optimization_data(self, server) -> Dict[str, Any]:
        """Get optimization data from service or fallback"""
        if server.corpus_service:
            dates = self._get_date_range()
            return await self._fetch_service_history(server.corpus_service, dates)
        return self._get_fallback_optimization_data()
    
    def _get_date_range(self) -> Dict[str, str]:
        """Get start and end dates for history query"""
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=30)
        return {"start": start_date.isoformat(), "end": end_date.isoformat()}
    
    async def _fetch_service_history(self, service, dates: Dict[str, str]) -> Dict[str, Any]:
        """Fetch optimization history from service"""
        history_data = await service.get_optimization_history(
            start_date=dates["start"], end_date=dates["end"]
        )
        if history_data and "optimizations" in history_data:
            return history_data
        return self._get_fallback_optimization_data()
    
    def _get_fallback_optimization_data(self) -> Dict[str, Any]:
        """Get fallback optimization history data"""
        return {
            "optimizations": self._get_sample_optimizations(),
            "total_savings": "$12,450",
            "average_optimization": "52%"
        }
    
    def _get_sample_optimizations(self) -> list:
        """Get sample optimization records"""
        return [
            self._create_sample_optimization_1(),
            self._create_sample_optimization_2()
        ]
    
    def _create_sample_optimization_1(self) -> Dict[str, Any]:
        """Create first sample optimization record"""
        return {
            "id": "opt-001", "date": "2025-08-10",
            "type": "prompt_optimization", "model": "claude-3-opus",
            "cost_reduction": "45%", "performance_gain": "20%"
        }
    
    def _create_sample_optimization_2(self) -> Dict[str, Any]:
        """Create second sample optimization record"""
        return {
            "id": "opt-002", "date": "2025-08-11",
            "type": "model_selection", "original": "gpt-4",
            "recommended": "claude-3-sonnet", "cost_reduction": "60%",
            "quality_maintained": True
        }
    
    def _format_optimization_response(self, data: Dict[str, Any]) -> str:
        """Format optimization response as JSON"""
        return json.dumps(data, indent=2)
    
    def _handle_optimization_error(self, error: Exception) -> str:
        """Handle optimization history errors"""
        logger.error(f"Error retrieving optimization history: {error}")
        return json.dumps({"error": str(error)}, indent=2)
    
    def _build_model_configs(self) -> Dict[str, Any]:
        """Build complete model configurations"""
        return {
            "models": {
                **self._get_claude_config(),
                **self._get_gpt4_config(),
                **self._get_gemini_config()
            }
        }
    
    def _get_claude_config(self) -> Dict[str, Dict[str, Any]]:
        """Get Claude-3-Opus configuration"""
        return {
            "claude-3-opus": {
                "context_window": 200000, "max_output": 4096,
                "price_per_1k_input": 0.015, "price_per_1k_output": 0.075,
                "rate_limit": 100
            }
        }
    
    def _get_gpt4_config(self) -> Dict[str, Dict[str, Any]]:
        """Get GPT-4 configuration"""
        return {
            "gpt-4": {
                "context_window": 128000, "max_output": 4096,
                "price_per_1k_input": 0.03, "price_per_1k_output": 0.06,
                "rate_limit": 500
            }
        }
    
    def _get_gemini_config(self) -> Dict[str, Dict[str, Any]]:
        """Get Gemini Pro configuration"""
        return {
            "gemini-pro": {
                "context_window": 32000, "max_output": 2048,
                "price_per_1k_input": 0.00025, "price_per_1k_output": 0.0005,
                "rate_limit": 1000
            }
        }
    
    def _format_config_response(self, configs: Dict[str, Any]) -> str:
        """Format model configuration response as JSON"""
        return json.dumps(configs, indent=2)
    
    def _format_catalog_response(self, catalog: Dict[str, Any]) -> str:
        """Format agent catalog response as JSON"""
        return json.dumps(catalog, indent=2)
    
    def _format_metrics_response(self, metrics: Dict[str, Any]) -> str:
        """Format metrics response as JSON"""
        return json.dumps(metrics, indent=2)