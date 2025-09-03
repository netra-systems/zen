"""DataSubAgent - UserExecutionContext Pattern Implementation

Modernized data analysis agent using UserExecutionContext pattern for complete request isolation.
Follows Phase 1 PARALLEL_AGENT_UPDATE_PLAN implementation.

New Pattern Features:
- Uses UserExecutionContext for complete request isolation
- DatabaseSessionManager for per-request session management
- No global state or shared sessions
- Complete removal of DeepAgentState legacy patterns
- Modern execute(context, stream_updates) interface

Business Value: Critical for identifying 15-30% cost savings opportunities.
BVJ: Enterprise | Performance Fee Capture | $10K+ monthly revenue per customer
"""

import time
from typing import Any, Dict, Optional

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.database.session_manager import DatabaseSessionManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger

# Consolidated data analysis core components (SSOT business logic)
from netra_backend.app.agents.data_sub_agent.core.data_analysis_core import DataAnalysisCore
from netra_backend.app.agents.data_sub_agent.core.data_processor import DataProcessor
from netra_backend.app.agents.data_sub_agent.core.anomaly_detector import AnomalyDetector

# Import data access capabilities for user-scoped ClickHouse and Redis access
from netra_backend.app.agents.supervisor.data_access_integration import DataAccessCapabilities

logger = central_logger.get_logger(__name__)


class DataSubAgent(BaseAgent):
    """UserExecutionContext Pattern DataSubAgent - Phase 1 Implementation
    
    Modernized implementation using UserExecutionContext pattern:
    - Uses UserExecutionContext for complete request isolation
    - DatabaseSessionManager for per-request database operations
    - No global state or legacy DeepAgentState usage
    - Modern execute(context, stream_updates) interface
    - Complete session isolation and proper cleanup
    
    Core Business Functions:
    - Performance metrics analysis and trend detection  
    - Cost optimization recommendations
    - Anomaly detection and correlation analysis
    - Data validation and quality assurance
    
    All database operations go through DatabaseSessionManager(context) for proper isolation.
    """
    
    def __init__(self, llm_manager: Optional[LLMManager] = None, 
                 tool_dispatcher: Optional[ToolDispatcher] = None):
        """Initialize DataSubAgent with UserExecutionContext pattern."""
        # Initialize BaseAgent with modern infrastructure
        super().__init__(
            llm_manager=llm_manager,
            name="DataSubAgent", 
            description="UserExecutionContext pattern data analysis agent",
            enable_reliability=True,
            enable_execution_engine=True,
            enable_caching=True,
            tool_dispatcher=tool_dispatcher
        )
        
        # Initialize ONLY business logic components (no database sessions stored)
        self._init_data_analysis_core()
        
        self.logger.info("DataSubAgent initialized with UserExecutionContext pattern")
    
    def _init_data_analysis_core(self) -> None:
        """Initialize consolidated core business logic components (no stored sessions)."""
        # Core business logic components - NO database sessions stored
        # Sessions are passed through context only
        self.data_processor = DataProcessor()                           # Data validation & processing
        self.anomaly_detector = AnomalyDetector()                       # Anomaly detection algorithms
        
        # Note: DataAnalysisCore will be initialized per-request with context
        # to ensure proper session isolation

    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute data analysis with UserExecutionContext pattern.
        
        Args:
            context: User execution context with request isolation
            stream_updates: Whether to stream progress updates
            
        Returns:
            Dictionary containing analysis results
            
        Raises:
            ValueError: If context is invalid
            SessionManagerError: If database session issues occur
        """
        # Validate context at entry
        if not isinstance(context, UserExecutionContext):
            raise ValueError(f"Invalid context type: {type(context)}")
        
        if not context.db_session:
            raise ValueError("UserExecutionContext must contain a database session")
        
        self.logger.info(f"Starting data analysis for user {context.user_id}, run {context.run_id}")
        
        # CRITICAL: Emit agent_started for proper chat value delivery
        if stream_updates:
            await self.emit_agent_started("Starting comprehensive data analysis for AI cost optimization opportunities")
        
        # Create database session manager for this request
        session_manager = DatabaseSessionManager(context)
        
        try:
            return await self._execute_with_context(context, session_manager, stream_updates)
        finally:
            # Always cleanup session manager
            await session_manager.close()
    
    async def _execute_with_context(self, context: UserExecutionContext, 
                                   session_manager: DatabaseSessionManager, 
                                   stream_updates: bool) -> Dict[str, Any]:
        """Execute core data analysis logic with proper context isolation."""
        start_time = time.time()
        
        # Emit thinking event if streaming enabled
        if stream_updates:
            await self.emit_thinking("Starting data analysis for AI cost optimization")
        
        # Process and validate analysis request from context metadata
        if stream_updates:
            await self.emit_thinking("Extracting and validating analysis parameters...")
        analysis_request = await self._process_analysis_request_from_context(context)
        
        # Initialize data analysis core with session manager and user-scoped data access capabilities
        data_access_capabilities = DataAccessCapabilities(context)
        data_analysis_core = DataAnalysisCore(session_manager, data_access_capabilities)
        
        # Execute core analysis with progress updates
        if stream_updates:
            await self.emit_progress("Executing data analysis with comprehensive metrics...")
        analysis_result = await self._execute_core_analysis_with_context(
            analysis_request, data_analysis_core, context, stream_updates
        )
        
        # Generate insights and recommendations
        if stream_updates:
            await self.emit_progress("Generating actionable insights and optimization recommendations...")
        insights = await self._generate_business_insights_with_context(
            analysis_result, analysis_request, context
        )
        
        # Prepare final result
        result_data = self._prepare_final_result(analysis_request, analysis_result, insights, start_time)
        
        # CRITICAL: Emit agent_completed for proper chat value delivery
        if stream_updates:
            execution_time_ms = (time.time() - start_time) * 1000
            completion_data = {
                "success": True,
                "analysis_type": analysis_request.get("type", "performance"),
                "data_points_analyzed": analysis_result.get("data_points", 0),
                "execution_time_ms": execution_time_ms,
                "user_id": context.user_id,
                "run_id": context.run_id
            }
            await self.emit_agent_completed(completion_data)
        
        # CRITICAL: Store data result in context metadata for other agents
        context.metadata['data_result'] = result_data
        
        return result_data
    
    async def _process_analysis_request_from_context(self, context: UserExecutionContext) -> Dict[str, Any]:
        """Process and validate analysis request from context metadata."""
        # Extract analysis parameters from context metadata
        metadata = context.metadata or {}
        
        # Extract basic request structure
        raw_request = {
            "type": metadata.get("analysis_type", "performance"),
            "timeframe": metadata.get("timeframe", "24h"),
            "metrics": metadata.get("metrics", ["latency_ms", "cost_cents", "throughput"]),
            "filters": metadata.get("filters", {}),
            "user_id": context.user_id
        }
        
        # Use consolidated processor for validation
        return await self.data_processor.process_analysis_request(raw_request)
    
    async def _execute_core_analysis_with_context(self, request: Dict[str, Any], 
                                                 data_analysis_core: DataAnalysisCore,
                                                 context: UserExecutionContext,
                                                 stream_updates: bool) -> Dict[str, Any]:
        """Execute core analysis using context-aware analysis engine."""
        analysis_type = request.get("type", "performance")
        
        try:
            if analysis_type == "performance":
                if stream_updates:
                    await self.emit_tool_executing("performance_analyzer", {
                        "analysis_type": "performance", 
                        "timeframe": request.get("timeframe"),
                        "user_id": context.user_id
                    })
                result = await data_analysis_core.analyze_performance(request)
                if stream_updates:
                    await self.emit_tool_completed("performance_analyzer", {
                        "status": "success", 
                        "data_points": result.get("data_points", 0)
                    })
                return result
                
            elif analysis_type == "cost_optimization":
                if stream_updates:
                    await self.emit_tool_executing("cost_optimizer", {
                        "analysis_type": "cost_optimization", 
                        "timeframe": request.get("timeframe"),
                        "user_id": context.user_id
                    })
                result = await data_analysis_core.analyze_costs(request)
                if stream_updates:
                    await self.emit_tool_completed("cost_optimizer", {
                        "status": "success",
                        "savings_identified": result.get("savings_potential", {}).get("savings_percentage", 0)
                    })
                return result
                
            elif analysis_type == "trend_analysis":
                if stream_updates:
                    await self.emit_tool_executing("trend_analyzer", {
                        "analysis_type": "trend_analysis",
                        "timeframe": request.get("timeframe"),
                        "user_id": context.user_id
                    })
                result = await data_analysis_core.analyze_trends(request)
                if stream_updates:
                    await self.emit_tool_completed("trend_analyzer", {
                        "status": "success",
                        "trends_found": len(result.get("trends", {}))
                    })
                return result
                
            elif analysis_type == "anomaly_detection":
                if stream_updates:
                    await self.emit_tool_executing("anomaly_detector", {
                        "analysis_type": "anomaly_detection",
                        "metric": request.get("metrics", ["latency_ms"])[0],
                        "user_id": context.user_id
                    })
                result = await data_analysis_core.detect_anomalies(request)
                if stream_updates:
                    await self.emit_tool_completed("anomaly_detector", {
                        "status": "success", 
                        "anomalies_found": result.get("anomalies_count", 0)
                    })
                return result
                
            else:
                # Default to performance analysis
                if stream_updates:
                    await self.emit_tool_executing("performance_analyzer", {
                        "analysis_type": "performance", 
                        "timeframe": request.get("timeframe"),
                        "user_id": context.user_id
                    })
                result = await data_analysis_core.analyze_performance(request)
                if stream_updates:
                    await self.emit_tool_completed("performance_analyzer", {
                        "status": "success", 
                        "data_points": result.get("data_points", 0)
                    })
                return result
                
        except Exception as e:
            # Emit error event for tool execution failure if streaming
            tool_name = self._get_tool_name_for_analysis_type(analysis_type)
            if stream_updates:
                await self.emit_error(f"{tool_name} execution failed: {str(e)}", 
                                    "tool_execution_error", 
                                    {"analysis_type": analysis_type, "user_id": context.user_id})
            # Log error with context
            self.logger.error(f"Analysis failed for user {context.user_id}, run {context.run_id}: {e}")
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
    
    async def _generate_business_insights_with_context(self, analysis_result: Dict[str, Any], 
                                                      original_request: Dict[str, Any],
                                                      context: UserExecutionContext) -> Dict[str, Any]:
        """Generate business insights and recommendations with context isolation."""
        # Enrich result with business context
        enriched_result = await self.data_processor.enrich_analysis_result(
            analysis_result, original_request
        )
        
        # Extract key business metrics with user context
        insights = {
            "summary": analysis_result.get("summary", "Analysis completed"),
            "status": analysis_result.get("status", "completed"),
            "analysis_type": original_request.get("type", "performance"),
            "timeframe": original_request.get("timeframe", "24h"),
            "data_points": analysis_result.get("data_points", 0),
            "user_id": context.user_id,
            "run_id": context.run_id
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
        
        # Extract cost savings data (flatten for compatibility)
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
        
        # Add LLM-generated insights if available (with context)
        if self.llm_manager:
            try:
                llm_insights = await self._generate_llm_insights_with_context(analysis_result, context)
                insights["ai_insights"] = llm_insights
            except Exception as e:
                self.logger.warning(f"LLM insights generation failed for user {context.user_id}: {e}")
                insights["ai_insights"] = "AI insights unavailable"
        
        return insights
    
    async def _generate_llm_insights_with_context(self, analysis_result: Dict[str, Any], 
                                                 context: UserExecutionContext) -> str:
        """Generate AI-powered insights using LLM with context isolation."""
        prompt = self._build_insights_prompt(analysis_result, context)
        response = await self.llm_manager.generate_response(prompt)
        return response.get("content", "No insights generated")
    
    def _build_insights_prompt(self, analysis_result: Dict[str, Any], context: UserExecutionContext) -> str:
        """Build prompt for LLM insights generation with user context."""
        return f"""Analyze this AI workload data and provide actionable cost optimization insights:
        
        Data Summary: {analysis_result.get('summary', 'N/A')}
        Key Metrics: {analysis_result.get('metrics', {})}
        User Context: {context.user_id} (Run: {context.run_id})
        
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

    async def validate_context(self, context: UserExecutionContext) -> bool:
        """Validate context contains required data for analysis.
        
        Args:
            context: User execution context to validate
            
        Returns:
            True if context is valid for data analysis
        """
        if not context.metadata:
            self.logger.warning(f"No metadata in context for user {context.user_id}")
            return False
        
        # Check for required analysis parameters in metadata
        analysis_type = context.metadata.get('analysis_type')
        if not analysis_type:
            self.logger.warning(f"No analysis_type in context metadata for user {context.user_id}")
            return False
        
        return True
    
    async def cleanup_context(self, context: UserExecutionContext) -> None:
        """Cleanup after execution with context isolation.
        
        Args:
            context: User execution context for this request
        """
        self.logger.debug(f"Data analysis completed for user {context.user_id}, run {context.run_id}")
        # No cleanup needed - session manager handles database session cleanup

    # Health and status methods
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        base_health = super().get_health_status() if hasattr(super(), 'get_health_status') else {}
        
        # Add data analysis specific health checks
        data_health = {
            "agent_name": "DataSubAgent",
            "pattern": "UserExecutionContext",
            "core_components": {
                "data_processor": "healthy" if self.data_processor else "unavailable", 
                "anomaly_detector": "healthy" if self.anomaly_detector else "unavailable"
            },
            "processing_stats": self.data_processor.get_processing_stats() if self.data_processor else {},
            "detection_stats": self.anomaly_detector.get_detection_stats() if self.anomaly_detector else {},
            "session_isolation": "enforced",
            "legacy_compatibility": "removed"
        }
        
        # Combine with base health
        return {**base_health, **data_health}

    # Data analysis specific helper methods (business logic only)
    def _validate_analysis_request(self, request: Dict[str, Any]) -> bool:
        """Validate analysis request structure."""
        required_fields = ["type", "timeframe"]
        return all(field in request for field in required_fields)
    
    def _get_analysis_cache_key(self, request: Dict[str, Any]) -> str:
        """Generate cache key for analysis request with proper user isolation."""
        # CRITICAL: Ensure proper user isolation in cache keys  
        user_id = request.get("user_id", "default")
        analysis_type = request.get("type", "performance")
        timeframe = request.get("timeframe", "24h")
        metrics = sorted(request.get("metrics", []))
        
        # Build hash-friendly key components
        key_components = f"{analysis_type}:{timeframe}:{':'.join(metrics)}"
        import hashlib
        content_hash = hashlib.md5(key_components.encode()).hexdigest()[:8]
        
        # Pattern: data_analysis:{user_id}:{hash} for proper user isolation
        return f"data_analysis:{user_id}:{content_hash}"
    
    # All infrastructure methods (WebSocket, monitoring, reliability) inherited from BaseAgent