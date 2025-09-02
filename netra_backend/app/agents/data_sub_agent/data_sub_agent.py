"""DataSubAgent - Consolidated Data Analysis Agent

Single, clean implementation providing reliable data insights for AI cost optimization.
Replaces 62+ fragmented files with focused, maintainable architecture.

Business Value: Critical for identifying 15-30% cost savings opportunities.
BVJ: Enterprise | Performance Fee Capture | $10K+ monthly revenue per customer
"""

import asyncio
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Union

# Import specific types from shared_types for better type safety
from netra_backend.app.schemas.shared_types import DataAnalysisResponse
from netra_backend.app.schemas.monitoring import PerformanceMetric

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus

# Import focused helper modules
from netra_backend.app.db.clickhouse import get_clickhouse_service
from netra_backend.app.agents.data_sub_agent.data_validator import DataValidator
from netra_backend.app.agents.data_sub_agent.performance_analyzer import (
    PerformanceAnalyzer,
)
from netra_backend.app.agents.data_sub_agent.schema_cache import SchemaCache
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.llm.cost_optimizer import LLMCostOptimizer


class DataSubAgent(BaseAgent):
    """Consolidated data analysis agent with ClickHouse integration.
    
    WebSocket events are handled through BaseAgent's bridge adapter.
    Provides reliable data insights for AI cost optimization through:
    - ClickHouse query execution with proper schema handling
    - Performance metrics analysis and trend detection
    - Cost optimization recommendations
    - Data validation and quality assurance
    - Real-time WebSocket event emissions for user feedback
    """
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher,
                 websocket_manager: Optional[Any] = None):
        """Initialize consolidated DataSubAgent."""
        # Initialize base agent with proper parameters
        super().__init__(
            llm_manager=llm_manager,
            name="DataSubAgent", 
            description="Consolidated data analysis agent providing reliable AI cost optimization insights",
            enable_reliability=True,
            enable_execution_engine=True,
            tool_dispatcher=tool_dispatcher
        )
        
        # Store websocket manager reference
        self.websocket_manager = websocket_manager
        
        # Initialize focused helper modules
        self._init_helper_modules()
        
        self.logger.info("DataSubAgent initialized successfully")
    
    def _init_helper_modules(self) -> None:
        """Initialize focused helper modules."""
        self.clickhouse_client = get_clickhouse_service()
        self.schema_cache = SchemaCache()
        self.performance_analyzer = PerformanceAnalyzer(self.clickhouse_client)
        self.cost_optimizer = LLMCostOptimizer()
        self.data_validator = DataValidator()
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for data analysis."""
        if not context.state:
            return False
            
        # Check if agent_input exists and has required data
        if not hasattr(context.state, 'agent_input') or context.state.agent_input is None:
            return False
            
        # Validate that we have the necessary helper modules initialized
        if not hasattr(self, 'clickhouse_client') or not hasattr(self, 'performance_analyzer'):
            return False
            
        return True
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core data analysis logic with WebSocket notifications."""
        # Send agent thinking notification
        await self.emit_thinking("Starting data analysis for AI cost optimization")
        
        # Extract analysis request from state
        await self.emit_thinking("Extracting analysis parameters from request...")
        analysis_request = self._extract_analysis_request(context.state)
        
        # Execute analysis with progress updates
        await self.emit_progress(f"Executing {analysis_request.get('type', 'performance')} analysis...")
        analysis_result = await self._execute_analysis(analysis_request)
        
        # Generate insights with progress updates
        await self.emit_progress("Generating actionable insights and cost optimization recommendations...")
        insights = await self._generate_insights(analysis_result)
        
        # Prepare final result data
        result_data = {
            "analysis_type": analysis_request.get("type"),
            "data_points_analyzed": analysis_result.get("data_points", 0),
            "status": "completed"
        }
        
        # Add flattened insights directly to result
        result_data.update(insights)
        
        # Emit completion notification
        await self.emit_progress("Data analysis completed successfully", is_complete=True)
        
        return result_data
    
    
    def _extract_analysis_request(self, state: DeepAgentState) -> Dict[str, Union[str, List[str], Optional[str]]]:
        """Extract and parse analysis request from state."""
        agent_input = state.agent_input
        
        # Default analysis request structure
        return {
            "type": agent_input.get("analysis_type", "performance"),
            "timeframe": agent_input.get("timeframe", "24h"),
            "metrics": agent_input.get("metrics", ["latency_ms", "cost_cents", "throughput"]),
            "filters": agent_input.get("filters", {}),
            "user_id": getattr(state, 'user_id', None)
        }
    
    async def _execute_analysis(self, request: Dict[str, Union[str, List[str], Optional[str]]]) -> Dict[str, Union[str, List[str], int, float, Dict[str, Any]]]:
        """Execute data analysis based on request type."""
        analysis_type = request["type"]
        
        if analysis_type == "performance":
            return await self.performance_analyzer.analyze_performance(request)
        elif analysis_type == "cost_optimization":
            return await self.cost_optimizer.analyze_costs(request)
        elif analysis_type == "trend_analysis":
            return await self.performance_analyzer.analyze_trends(request)
        else:
            # Default to performance analysis
            return await self.performance_analyzer.analyze_performance(request)
    
    async def _generate_insights(self, analysis_result: Dict[str, Union[str, List[str], int, float, Dict[str, Any]]]) -> Dict[str, Union[str, float, int]]:
        """Generate actionable insights from analysis results."""
        # Flatten complex structures to comply with TypedAgentResult constraints
        insights = {
            "summary": analysis_result.get("summary", "Analysis completed"),
            "key_findings": ", ".join(analysis_result.get("findings", [])),
            "recommendations": ", ".join(analysis_result.get("recommendations", [])),
        }
        
        # Flatten cost savings data - handle both "cost_savings" and "savings_potential" keys
        cost_savings = analysis_result.get("cost_savings", analysis_result.get("savings_potential", {}))
        if cost_savings:
            insights["cost_savings_percentage"] = cost_savings.get("percentage", cost_savings.get("savings_percentage", 0.0))
            insights["cost_savings_amount_cents"] = cost_savings.get("amount_cents", cost_savings.get("total_savings_cents", 0.0))
        
        # Flatten performance metrics
        metrics = analysis_result.get("metrics", {})
        if metrics:
            # Extract latency metrics
            if "latency" in metrics:
                latency_data = metrics["latency"]
                insights["avg_latency_ms"] = latency_data.get("avg_latency_ms", 0.0)
                insights["p95_latency_ms"] = latency_data.get("p95_latency_ms", 0.0)
        
        # Add LLM-generated insights if available
        if self.llm_manager and analysis_result.get("raw_data"):
            llm_insights = await self._generate_llm_insights(analysis_result)
            insights["ai_insights"] = llm_insights
        
        return insights
    
    async def _generate_llm_insights(self, analysis_result: Dict[str, Union[str, List[str], int, float, Dict[str, Any]]]) -> str:
        """Generate AI-powered insights using LLM."""
        try:
            prompt = self._build_insights_prompt(analysis_result)
            response = await self.llm_manager.generate_response(prompt)
            return response.get("content", "No insights generated")
        except Exception as e:
            self.logger.warning(f"LLM insights generation failed: {e}")
            return "AI insights unavailable"
    
    def _build_insights_prompt(self, analysis_result: Dict[str, Union[str, List[str], int, float, Dict[str, Any]]]) -> str:
        """Build prompt for LLM insights generation."""
        return f"""Analyze this AI workload data and provide actionable cost optimization insights:
        
        Data Summary: {analysis_result.get('summary', 'N/A')}
        Key Metrics: {analysis_result.get('metrics', {})}
        
        Focus on:
        1. Cost reduction opportunities (target 15-30% savings)
        2. Performance bottlenecks
        3. Resource optimization recommendations
        4. ROI impact projections
        
        Provide specific, actionable recommendations."""
    
    
    
    # Health and status methods
    def get_health_status(self) -> Dict[str, Union[str, Dict[str, str]]]:
        """Get comprehensive health status."""
        return {
            "agent_name": "DataSubAgent",
            "status": "healthy",
            "clickhouse_health": self.clickhouse_client.get_health_status(),
            "schema_cache_health": self.schema_cache.get_health_status(),
            "components": {
                "performance_analyzer": "active",
                "cost_optimizer": "active",
                "data_validator": "active"
            },
            "timestamp": datetime.now(UTC).isoformat()
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up DataSubAgent resources")
        await self.clickhouse_client.close()
        await self.schema_cache.cleanup()
