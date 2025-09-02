"""DataSubAgent - Golden Pattern Implementation

Consolidated data analysis agent following the golden pattern established by TriageSubAgent.
Replaces 66+ fragmented files with single SSOT implementation using BaseAgent infrastructure.

Follows Golden Pattern:
- Inherits from BaseAgent (single inheritance)
- Implements validate_preconditions() and execute_core_logic() only
- Uses inherited WebSocket events, reliability, and execution infrastructure
- Contains ONLY data analysis business logic
- NO infrastructure duplication

Business Value: Critical for identifying 15-30% cost savings opportunities.
BVJ: Enterprise | Performance Fee Capture | $10K+ monthly revenue per customer
"""

import time
from typing import Any, Dict, Optional

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.input_validation import validate_agent_input
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.type_validators import agent_type_safe
from netra_backend.app.schemas.strict_types import TypedAgentResult
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger

# Consolidated data analysis core components (SSOT business logic)
from netra_backend.app.agents.data_sub_agent.core.data_analysis_core import DataAnalysisCore
from netra_backend.app.agents.data_sub_agent.core.data_processor import DataProcessor
from netra_backend.app.agents.data_sub_agent.core.anomaly_detector import AnomalyDetector

logger = central_logger.get_logger(__name__)


class DataSubAgent(BaseAgent):
    """Golden Pattern DataSubAgent - SSOT Implementation
    
    Clean implementation following TriageSubAgent golden pattern:
    - Inherits ALL infrastructure from BaseAgent (WebSocket, reliability, execution)
    - Contains ONLY data analysis business logic
    - No infrastructure duplication (circuit breakers, retry, WebSocket handlers)
    - Single responsibility: data analysis for AI cost optimization
    
    Core Business Functions:
    - Performance metrics analysis and trend detection  
    - Cost optimization recommendations
    - Anomaly detection and correlation analysis
    - Data validation and quality assurance
    
    All infrastructure (WebSocket events, reliability, monitoring) inherited from BaseAgent.
    """
    
    def __init__(self, llm_manager: Optional[LLMManager] = None, 
                 tool_dispatcher: Optional[ToolDispatcher] = None):
        """Initialize DataSubAgent following golden pattern."""
        # Initialize BaseAgent with full infrastructure (following TriageSubAgent pattern)
        super().__init__(
            llm_manager=llm_manager,
            name="DataSubAgent", 
            description="Golden pattern data analysis agent using BaseAgent infrastructure",
            enable_reliability=True,      # Get circuit breaker + retry
            enable_execution_engine=True, # Get modern execution patterns
            enable_caching=True,          # Get caching infrastructure
            tool_dispatcher=tool_dispatcher
        )
        
        # Initialize ONLY business logic components (no infrastructure)
        self._init_data_analysis_core()
        
        self.logger.info("DataSubAgent initialized with golden pattern")
    
    def _init_data_analysis_core(self) -> None:
        """Initialize consolidated core business logic components (no infrastructure)."""
        # Core business logic components - consolidated from 66+ fragmented files
        self.data_analysis_core = DataAnalysisCore(self.redis_manager)  # Main analysis engine
        self.data_processor = DataProcessor()                           # Data validation & processing
        self.anomaly_detector = AnomalyDetector()                       # Anomaly detection algorithms
        
        # Legacy compatibility attributes (gradually migrate these)
        self.clickhouse_client = self.data_analysis_core.clickhouse_client
        self.cache_ttl = self.data_analysis_core.cache_ttl

    # Implement BaseAgent's abstract methods for data analysis business logic
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for data analysis."""
        if not context.state:
            self.logger.warning(f"No state provided for data analysis in run_id: {context.run_id}")
            return False
        
        # Check if agent_input exists and has required data
        if not hasattr(context.state, 'agent_input') or context.state.agent_input is None:
            self.logger.warning(f"No agent_input provided for data analysis in run_id: {context.run_id}")
            return False
        
        # Validate that we have the necessary core components initialized
        if not self.data_analysis_core:
            self.logger.error("DataAnalysisCore not initialized")
            return False
        
        return True
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core data analysis logic with WebSocket events (golden pattern)."""
        start_time = time.time()
        
        # Emit thinking event (agent_started handled by orchestrator)
        await self.emit_thinking("Starting data analysis for AI cost optimization")
        
        # Process and validate analysis request
        await self.emit_thinking("Extracting and validating analysis parameters...")
        analysis_request = await self._process_analysis_request(context.state)
        
        # Execute core analysis with progress updates
        await self.emit_progress("Executing data analysis with comprehensive metrics...")
        analysis_result = await self._execute_core_analysis(analysis_request)
        
        # Generate insights and recommendations
        await self.emit_progress("Generating actionable insights and optimization recommendations...")
        insights = await self._generate_business_insights(analysis_result, analysis_request)
        
        # Prepare final result
        result_data = self._prepare_final_result(analysis_request, analysis_result, insights, start_time)
        
        # Emit completion event
        await self.emit_progress("Data analysis completed successfully", is_complete=True)
        
        return result_data
    
    async def _process_analysis_request(self, state: DeepAgentState) -> Dict[str, Any]:
        """Process and validate analysis request using consolidated processor."""
        agent_input = state.agent_input or {}
        
        # Extract basic request structure
        raw_request = {
            "type": agent_input.get("analysis_type", "performance"),
            "timeframe": agent_input.get("timeframe", "24h"),
            "metrics": agent_input.get("metrics", ["latency_ms", "cost_cents", "throughput"]),
            "filters": agent_input.get("filters", {}),
            "user_id": getattr(state, 'user_id', None)
        }
        
        # Use consolidated processor for validation
        return await self.data_processor.process_analysis_request(raw_request)
    
    async def _execute_core_analysis(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute core analysis using consolidated analysis engine with WebSocket events."""
        analysis_type = request.get("type", "performance")
        
        try:
            if analysis_type == "performance":
                await self.emit_tool_executing("performance_analyzer", {
                    "analysis_type": "performance", 
                    "timeframe": request.get("timeframe")
                })
                result = await self.data_analysis_core.analyze_performance(request)
                await self.emit_tool_completed("performance_analyzer", {
                    "status": "success", 
                    "data_points": result.get("data_points", 0)
                })
                return result
                
            elif analysis_type == "cost_optimization":
                await self.emit_tool_executing("cost_optimizer", {
                    "analysis_type": "cost_optimization", 
                    "timeframe": request.get("timeframe")
                })
                result = await self.data_analysis_core.analyze_costs(request)
                await self.emit_tool_completed("cost_optimizer", {
                    "status": "success",
                    "savings_identified": result.get("savings_potential", {}).get("savings_percentage", 0)
                })
                return result
                
            elif analysis_type == "trend_analysis":
                await self.emit_tool_executing("trend_analyzer", {
                    "analysis_type": "trend_analysis",
                    "timeframe": request.get("timeframe")
                })
                result = await self.data_analysis_core.analyze_trends(request)
                await self.emit_tool_completed("trend_analyzer", {
                    "status": "success",
                    "trends_found": len(result.get("trends", {}))
                })
                return result
                
            elif analysis_type == "anomaly_detection":
                await self.emit_tool_executing("anomaly_detector", {
                    "analysis_type": "anomaly_detection",
                    "metric": request.get("metrics", ["latency_ms"])[0]
                })
                result = await self.data_analysis_core.detect_anomalies(request)
                await self.emit_tool_completed("anomaly_detector", {
                    "status": "success", 
                    "anomalies_found": result.get("anomalies_count", 0)
                })
                return result
                
            else:
                # Default to performance analysis
                await self.emit_tool_executing("performance_analyzer", {
                    "analysis_type": "performance", 
                    "timeframe": request.get("timeframe")
                })
                result = await self.data_analysis_core.analyze_performance(request)
                await self.emit_tool_completed("performance_analyzer", {
                    "status": "success", 
                    "data_points": result.get("data_points", 0)
                })
                return result
                
        except Exception as e:
            # Emit error event for tool execution failure
            tool_name = self._get_tool_name_for_analysis_type(analysis_type)
            await self.emit_error(f"{tool_name} execution failed: {str(e)}", 
                                "tool_execution_error", 
                                {"analysis_type": analysis_type})
            # Re-raise to be handled by base agent error handling
            raise
    
    def _get_tool_name_for_analysis_type(self, analysis_type: str) -> str:
        """Get tool name for analysis type for WebSocket events."""
        type_map = {
            "performance": "performance_analyzer",
            "cost_optimization": "cost_optimizer", 
            "trend_analysis": "trend_analyzer",
            "anomaly_detection": "anomaly_detector"
        }
        return type_map.get(analysis_type, "performance_analyzer")
    
    async def _generate_business_insights(self, analysis_result: Dict[str, Any], 
                                        original_request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate business insights and recommendations."""
        # Enrich result with business context
        enriched_result = await self.data_processor.enrich_analysis_result(
            analysis_result, original_request
        )
        
        # Extract key business metrics
        insights = {
            "summary": analysis_result.get("summary", "Analysis completed"),
            "status": analysis_result.get("status", "completed"),
            "analysis_type": original_request.get("type", "performance"),
            "timeframe": original_request.get("timeframe", "24h"),
            "data_points": analysis_result.get("data_points", 0)
        }
        
        # Add findings and recommendations as comma-separated strings
        findings = analysis_result.get("findings", [])
        recommendations = analysis_result.get("recommendations", [])
        
        if isinstance(findings, list):
            insights["key_findings"] = ", ".join(findings)
        else:
            insights["key_findings"] = str(findings)
        
        if isinstance(recommendations, list):
            insights["recommendations"] = ", ".join(recommendations) 
        else:
            insights["recommendations"] = str(recommendations)
        
        # Extract cost savings data (flatten for TypedAgentResult compatibility)
        savings_potential = analysis_result.get("savings_potential", {})
        if savings_potential:
            insights["cost_savings_percentage"] = savings_potential.get("savings_percentage", 0)
            insights["cost_savings_amount_cents"] = savings_potential.get("total_savings_cents", 0)
        
        # Extract performance metrics (flatten for compatibility)
        metrics = analysis_result.get("metrics", {})
        if metrics:
            latency_data = metrics.get("latency", {})
            if latency_data:
                insights["avg_latency_ms"] = latency_data.get("avg_latency_ms", 0)
                insights["p95_latency_ms"] = latency_data.get("p95_latency_ms", 0)
            
            throughput_data = metrics.get("throughput", {})
            if throughput_data:
                insights["avg_throughput"] = throughput_data.get("avg_throughput", 0)
        
        # Add anomaly information if present
        if "anomalies_count" in analysis_result:
            insights["anomalies_detected"] = analysis_result["anomalies_count"]
            insights["anomaly_percentage"] = analysis_result.get("anomaly_percentage", 0)
        
        # Add trend information if present
        trends = analysis_result.get("trends", {})
        if trends:
            # Flatten trend data
            for metric, trend_data in trends.items():
                if isinstance(trend_data, dict):
                    insights[f"{metric}_trend"] = trend_data.get("direction", "stable")
                    insights[f"{metric}_trend_confidence"] = trend_data.get("confidence", "medium")
        
        # Add LLM-generated insights if available
        if self.llm_manager:
            try:
                await self.emit_tool_executing("llm_insights_generator", {
                    "analysis_summary": insights.get("summary", "")
                })
                llm_insights = await self._generate_llm_insights(analysis_result)
                insights["ai_insights"] = llm_insights
                await self.emit_tool_completed("llm_insights_generator", {
                    "status": "success", 
                    "insights_length": len(llm_insights)
                })
            except Exception as e:
                await self.emit_error(f"LLM insights generation failed: {str(e)}", 
                                    "llm_execution_error")
                logger.warning(f"LLM insights generation failed: {e}")
                insights["ai_insights"] = "AI insights unavailable"
        
        return insights
    
    async def _generate_llm_insights(self, analysis_result: Dict[str, Any]) -> str:
        """Generate AI-powered insights using LLM."""
        prompt = self._build_insights_prompt(analysis_result)
        response = await self.llm_manager.generate_response(prompt)
        return response.get("content", "No insights generated")
    
    def _build_insights_prompt(self, analysis_result: Dict[str, Any]) -> str:
        """Build prompt for LLM insights generation."""
        return f"""Analyze this AI workload data and provide actionable cost optimization insights:
        
        Data Summary: {analysis_result.get('summary', 'N/A')}
        Key Metrics: {analysis_result.get('metrics', {})}
        
        Focus on:
        1. Cost reduction opportunities (target 15-30% savings)
        2. Performance bottlenecks and optimization paths
        3. Resource utilization improvements
        4. ROI impact projections
        
        Provide specific, actionable recommendations for immediate implementation."""
    
    def _prepare_final_result(self, request: Dict[str, Any], analysis_result: Dict[str, Any], 
                            insights: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Prepare final result data in expected format."""
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Base result structure
        result_data = {
            "analysis_type": request.get("type", "performance"),
            "timeframe": request.get("timeframe", "24h"),
            "data_points_analyzed": analysis_result.get("data_points", 0),
            "status": "completed",
            "execution_time_ms": round(execution_time_ms, 2)
        }
        
        # Add all insights directly to result (flattened structure)
        result_data.update(insights)
        
        return result_data

    # Legacy execute method for backward compatibility
    @validate_agent_input('DataSubAgent')
    @agent_type_safe
    async def execute(self, state: DeepAgentState, run_id: str, 
                     stream_updates: bool = False) -> TypedAgentResult:
        """Execute data analysis with backward compatibility."""
        await self.execute_with_reliability(
            lambda: self._execute_data_main(state, run_id, stream_updates),
            "execute_data_analysis",
            fallback=lambda: self._execute_data_fallback(state, run_id, stream_updates)
        )
        
        # Return the result stored in state
        return state.data_result if hasattr(state, 'data_result') else TypedAgentResult()
    
    async def _execute_data_main(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Main data execution logic - delegates to execute_core_logic."""
        from netra_backend.app.agents.utils import extract_thread_id
        from datetime import datetime, timezone
        
        context = ExecutionContext(
            run_id=run_id,
            agent_name=self.name,
            state=state,
            stream_updates=stream_updates,
            thread_id=extract_thread_id(state),
            user_id=getattr(state, 'user_id', None),
            start_time=datetime.now(timezone.utc),
            correlation_id=self.correlation_id
        )
        
        result = await self.execute_core_logic(context)
        
        # Store result in state for backward compatibility
        from netra_backend.app.schemas.strict_types import TypedAgentResult
        state.data_result = TypedAgentResult(**result) if result else TypedAgentResult()
        
        return result

    async def _execute_data_fallback(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Fallback execution for error recovery."""
        logger.warning(f"Using fallback data analysis for run_id: {run_id}")
        
        fallback_result = {
            "status": "completed_with_fallback",
            "analysis_type": "fallback",
            "summary": "Analysis completed with limited functionality",
            "data_points_analyzed": 0,
            "key_findings": "Fallback mode - limited analysis available",
            "recommendations": "Please retry analysis for full results"
        }
        
        # Store fallback result
        from netra_backend.app.schemas.strict_types import TypedAgentResult
        state.data_result = TypedAgentResult(**fallback_result)
        
        return fallback_result

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have the necessary data for analysis."""
        return (hasattr(state, 'agent_input') and 
                state.agent_input is not None and 
                bool(state.agent_input.get('analysis_type')))

    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Cleanup after execution - data analysis specific cleanup only."""
        if hasattr(state, 'data_result') and state.data_result:
            # Log analysis metrics for monitoring
            analysis_type = getattr(state.data_result, 'analysis_type', 'unknown')
            data_points = getattr(state.data_result, 'data_points_analyzed', 0)
            self.logger.debug(f"Data analysis completed for run_id {run_id}: "
                            f"type={analysis_type}, data_points={data_points}")

    # Health and status methods
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        base_health = super().get_health_status() if hasattr(super(), 'get_health_status') else {}
        
        # Add data analysis specific health checks
        data_health = {
            "agent_name": "DataSubAgent",
            "core_components": {
                "data_analysis_core": "healthy" if self.data_analysis_core else "unavailable",
                "data_processor": "healthy" if self.data_processor else "unavailable", 
                "anomaly_detector": "healthy" if self.anomaly_detector else "unavailable"
            },
            "business_logic_health": self.data_analysis_core.get_health_status() if self.data_analysis_core else {},
            "processing_stats": self.data_processor.get_processing_stats() if self.data_processor else {},
            "detection_stats": self.anomaly_detector.get_detection_stats() if self.anomaly_detector else {}
        }
        
        # Combine with base health
        return {**base_health, **data_health}

    # Data analysis specific helper methods (business logic only)
    def _validate_analysis_request(self, request: Dict[str, Any]) -> bool:
        """Validate analysis request structure."""
        required_fields = ["type", "timeframe"]
        return all(field in request for field in required_fields)
    
    def _get_analysis_cache_key(self, request: Dict[str, Any]) -> str:
        """Generate cache key for analysis request."""
        key_parts = [
            request.get("type", "performance"),
            request.get("timeframe", "24h"),
            str(request.get("user_id", "default")),
            "_".join(sorted(request.get("metrics", [])))
        ]
        return f"data_analysis:{'|'.join(key_parts)}"
    
    # All infrastructure methods (WebSocket, monitoring, reliability) inherited from BaseAgent