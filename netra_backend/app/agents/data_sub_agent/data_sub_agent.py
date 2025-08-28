"""DataSubAgent - Consolidated Data Analysis Agent

Single, clean implementation providing reliable data insights for AI cost optimization.
Replaces 62+ fragmented files with focused, maintainable architecture.

Business Value: Critical for identifying 15-30% cost savings opportunities.
BVJ: Enterprise | Performance Fee Capture | $10K+ monthly revenue per customer
"""

import asyncio
import time
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.base.interface import (
    BaseExecutionInterface,
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
    WebSocketManagerProtocol,
)

# Import focused helper modules
from netra_backend.app.db.clickhouse import get_clickhouse_service
from netra_backend.app.agents.data_sub_agent.data_validator import DataValidator
from netra_backend.app.agents.data_sub_agent.performance_analyzer import (
    PerformanceAnalyzer,
)
from netra_backend.app.agents.data_sub_agent.schema_cache import SchemaCache
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.core.type_validators import agent_type_safe
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.strict_types import TypedAgentResult
from netra_backend.app.services.llm.cost_optimizer import LLMCostOptimizer


class DataSubAgent(BaseSubAgent, BaseExecutionInterface):
    """Consolidated data analysis agent with ClickHouse integration.
    
    Provides reliable data insights for AI cost optimization through:
    - ClickHouse query execution with proper schema handling
    - Performance metrics analysis and trend detection
    - Cost optimization recommendations
    - Data validation and quality assurance
    """
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher,
                 websocket_manager: Optional[WebSocketManagerProtocol] = None):
        """Initialize consolidated DataSubAgent."""
        # Initialize base classes
        BaseSubAgent.__init__(self, llm_manager, name="DataSubAgent", 
                            description="Advanced data analysis for AI cost optimization")
        BaseExecutionInterface.__init__(self, "DataSubAgent", websocket_manager)
        
        # Initialize core components
        self.tool_dispatcher = tool_dispatcher
        self.logger = central_logger.get_logger("DataSubAgent")
        
        # Initialize focused helper modules
        self._init_helper_modules()
        
        self.logger.info("DataSubAgent initialized successfully")
    
    def _init_helper_modules(self) -> None:
        """Initialize focused helper modules."""
        self.clickhouse_client = get_clickhouse_service()
        self.schema_cache = SchemaCache()
        self.performance_analyzer = PerformanceAnalyzer(self.clickhouse_client)
        self.cost_optimizer = LLMCostOptimizer(self.clickhouse_client)
        self.data_validator = DataValidator()
    
    @agent_type_safe
    async def execute(self, state: Optional[DeepAgentState], run_id: str = "", stream_updates: bool = False) -> TypedAgentResult:
        """Execute data analysis workflow."""
        start_time = time.time()
        
        try:
            # Validate input
            if not self._validate_execution_state(state):
                return self._create_error_result("Invalid execution state", start_time)
            
            # Extract analysis request
            analysis_request = self._extract_analysis_request(state)
            
            # Execute analysis based on request type
            analysis_result = await self._execute_analysis(analysis_request)
            
            # Generate insights and recommendations
            insights = await self._generate_insights(analysis_result)
            
            # Prepare final result
            execution_time = (time.time() - start_time) * 1000
            
            # Flatten all result data to comply with TypedAgentResult constraints
            result_data = {
                "analysis_type": analysis_request.get("type"),
                "execution_time_ms": execution_time,
                "data_points_analyzed": analysis_result.get("data_points", 0)
            }
            
            # Add flattened insights directly to result
            result_data.update(insights)
            
            return TypedAgentResult(
                success=True,
                result=result_data,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self.logger.error(f"DataSubAgent execution failed: {str(e)}")
            return self._create_error_result(str(e), start_time)
    
    def _validate_execution_state(self, state: DeepAgentState) -> bool:
        """Validate execution state has required data analysis parameters."""
        return (
            state and 
            hasattr(state, 'agent_input') and 
            state.agent_input is not None
        )
    
    def _extract_analysis_request(self, state: DeepAgentState) -> Dict[str, Any]:
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
    
    async def _execute_analysis(self, request: Dict[str, Any]) -> Dict[str, Any]:
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
    
    async def _generate_insights(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
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
    
    async def _generate_llm_insights(self, analysis_result: Dict[str, Any]) -> str:
        """Generate AI-powered insights using LLM."""
        try:
            prompt = self._build_insights_prompt(analysis_result)
            response = await self.llm_manager.generate_response(prompt)
            return response.get("content", "No insights generated")
        except Exception as e:
            self.logger.warning(f"LLM insights generation failed: {e}")
            return "AI insights unavailable"
    
    def _build_insights_prompt(self, analysis_result: Dict[str, Any]) -> str:
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
    
    def _create_error_result(self, error_message: str, start_time: float) -> TypedAgentResult:
        """Create standardized error result."""
        execution_time = (time.time() - start_time) * 1000
        
        return TypedAgentResult(
            success=False,
            result={
                "error": error_message,
                "execution_time_ms": execution_time
            },
            execution_time_ms=execution_time
        )
    
    # BaseExecutionInterface implementation
    async def execute_core_logic(self, context: ExecutionContext) -> ExecutionResult:
        """Core execution logic for BaseExecutionInterface."""
        try:
            # Convert context to state for backward compatibility
            state = self._context_to_state(context)
            
            # Execute main logic
            result = await self.execute(state, context.run_id, context.stream_updates)
            
            return ExecutionResult(
                success=result.success,
                status=ExecutionStatus.COMPLETED if result.success else ExecutionStatus.FAILED,
                result=result.result,
                execution_time_ms=result.execution_time_ms
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.FAILED,
                error=str(e)
            )
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate preconditions for execution."""
        return (
            context.state is not None and
            self.clickhouse_client.is_healthy() and
            self.schema_cache.is_available()
        )
    
    def _context_to_state(self, context: ExecutionContext) -> DeepAgentState:
        """Convert ExecutionContext to DeepAgentState for backward compatibility."""
        return context.state
    
    # Health and status methods
    def get_health_status(self) -> Dict[str, Any]:
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
