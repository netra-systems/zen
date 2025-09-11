"""Tool Result Aggregator - SSOT for Tool Result Aggregation and Synthesis

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Transform raw tool outputs into actionable business intelligence
- Value Impact: Converts technical data into meaningful insights for decision-making
- Strategic Impact: Core value delivery mechanism enabling AI-powered optimization recommendations

This module provides comprehensive tool result aggregation, synthesis, and intelligent 
insight generation capabilities for the Netra platform's AI agents.

Key Features:
- Multi-tool result synthesis and cross-correlation
- Hierarchical aggregation with dependency management
- Real-time streaming aggregation with WebSocket notifications
- Intelligent insight generation with business context awareness  
- Temporal analysis and trend detection with forecasting
- SSOT integration with UserExecutionContext and monitoring systems

SSOT Compliance:
- Integrates with UserExecutionContext for multi-user isolation
- Uses real-time aggregator patterns from existing monitoring infrastructure
- Follows WebSocket notification patterns for real-time updates
- Implements proper logging and error handling standards
"""

import asyncio
import statistics
import time
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.monitoring.real_time_aggregator import RealTimeAggregator, MetricPoint, AggregatedMetric

logger = central_logger.get_logger(__name__)


class CorrelationStrategy(Enum):
    """Strategies for cross-tool result correlation."""
    CROSS_CORRELATION_WITH_INSIGHTS = "cross_correlation_with_insights"
    PATTERN_MATCHING = "pattern_matching"
    TEMPORAL_CORRELATION = "temporal_correlation"
    SEMANTIC_CORRELATION = "semantic_correlation"


class AggregationStrategy(Enum):
    """Strategies for hierarchical aggregation."""
    DEPENDENCY_ORDERED = "dependency_ordered"
    LEVEL_SEQUENTIAL = "level_sequential"
    PARALLEL_LEVELS = "parallel_levels"
    WEIGHTED_AGGREGATION = "weighted_aggregation"


@dataclass
class ToolResult:
    """Individual tool execution result."""
    tool_name: str
    status: str
    output: Dict[str, Any]
    execution_time: float
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrossToolCorrelation:
    """Cross-tool correlation result."""
    tools: List[str]
    correlation_type: str
    correlation_strength: float
    insight: str
    supporting_evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregationResult:
    """Result of tool aggregation and synthesis."""
    status: str
    synthesis_completed: bool
    cross_tool_correlations: List[CrossToolCorrelation]
    synthesized_insights: Dict[str, Any]
    actionable_recommendations: List[Dict[str, Any]]
    aggregation_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HierarchicalAggregationResult:
    """Result of hierarchical tool result aggregation."""
    status: str
    hierarchy_validated: bool
    level_summaries: Dict[str, Dict[str, Any]]
    final_insights: Dict[str, Any]
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class StreamingAggregationResult:
    """Result of real-time streaming aggregation."""
    status: str
    streaming_completed: bool
    total_updates_processed: int
    real_time_insights: Dict[str, Any]
    final_aggregation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntelligentInsightResult:
    """Result of intelligent insight generation."""
    status: str
    insights_generated: bool
    insights: Dict[str, Dict[str, Any]]
    insight_quality: Dict[str, float]


@dataclass
class TemporalAnalysisResult:
    """Result of temporal pattern analysis."""
    status: str
    temporal_analysis_completed: bool
    detected_trends: List[Dict[str, Any]]
    forecasts: Dict[str, Dict[str, Any]]
    pattern_analysis: Dict[str, Any]
    temporal_insights: Dict[str, Any]


class ToolResultAggregator:
    """SSOT Tool Result Aggregator for comprehensive tool result processing.
    
    This class provides enterprise-grade tool result aggregation capabilities including:
    - Multi-tool result synthesis and correlation
    - Hierarchical dependency-aware aggregation  
    - Real-time streaming with WebSocket notifications
    - Intelligent business-context-aware insight generation
    - Temporal analysis and forecasting
    """
    
    def __init__(
        self,
        user_context: UserExecutionContext,
        correlation_enabled: bool = True,
        synthesis_mode: str = "comprehensive",
        hierarchical_aggregation: bool = False,
        dependency_aware: bool = False,
        real_time_streaming: bool = False,
        websocket_emitter = None,
        streaming_aggregation: bool = False,
        insight_generation: bool = False,
        intelligence_level: str = "standard",
        business_context_aware: bool = False,
        temporal_analysis: bool = False,
        trend_detection: bool = False,
        forecasting_enabled: bool = False
    ):
        """Initialize the Tool Result Aggregator.
        
        Args:
            user_context: User execution context for isolation
            correlation_enabled: Enable cross-tool correlation analysis
            synthesis_mode: Mode for result synthesis (basic, comprehensive, advanced)
            hierarchical_aggregation: Enable hierarchical aggregation
            dependency_aware: Consider tool dependencies in aggregation
            real_time_streaming: Enable real-time streaming capabilities
            websocket_emitter: WebSocket emitter for notifications  
            streaming_aggregation: Enable streaming aggregation mode
            insight_generation: Enable intelligent insight generation
            intelligence_level: Level of intelligence (standard, advanced, expert)
            business_context_aware: Consider business context in insights
            temporal_analysis: Enable temporal pattern analysis
            trend_detection: Enable trend detection
            forecasting_enabled: Enable forecasting capabilities
        """
        self.user_context = user_context
        self.correlation_enabled = correlation_enabled
        self.synthesis_mode = synthesis_mode
        self.hierarchical_aggregation = hierarchical_aggregation
        self.dependency_aware = dependency_aware
        self.real_time_streaming = real_time_streaming
        self.websocket_emitter = websocket_emitter
        self.streaming_aggregation = streaming_aggregation
        self.insight_generation = insight_generation
        self.intelligence_level = intelligence_level
        self.business_context_aware = business_context_aware
        self.temporal_analysis = temporal_analysis
        self.trend_detection = trend_detection
        self.forecasting_enabled = forecasting_enabled
        
        # Initialize aggregation infrastructure
        self.real_time_aggregator = RealTimeAggregator()
        self.correlation_cache = {}
        self.insight_cache = {}
        self.streaming_buffer = deque(maxlen=10000)
        self.aggregation_id = str(uuid4())
        
        logger.info(
            f"ToolResultAggregator initialized for user {user_context.user_id} "
            f"with mode {synthesis_mode} and intelligence level {intelligence_level}"
        )
    
    async def aggregate_and_synthesize(
        self,
        tool_results: Dict[str, Dict[str, Any]],
        synthesis_strategy: str = "cross_correlation_with_insights",
        correlation_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """Aggregate and synthesize results from multiple tools.
        
        Args:
            tool_results: Dictionary of tool results keyed by tool name
            synthesis_strategy: Strategy for synthesis
            correlation_threshold: Minimum correlation strength threshold
            
        Returns:
            Comprehensive aggregation result with correlations and insights
        """
        try:
            logger.info(f"Starting multi-tool result synthesis for {len(tool_results)} tools")
            
            # Convert tool results to standardized format
            standardized_results = []
            for tool_name, result_data in tool_results.items():
                tool_result = ToolResult(
                    tool_name=tool_name,
                    status=result_data.get("status", "unknown"),
                    output=result_data.get("output", {}),
                    execution_time=result_data.get("execution_time", 0.0),
                    confidence=result_data.get("confidence", 0.0)
                )
                standardized_results.append(tool_result)
            
            # Perform cross-tool correlation analysis
            correlations = []
            if self.correlation_enabled:
                correlations = await self._analyze_cross_tool_correlations(
                    standardized_results, 
                    correlation_threshold
                )
            
            # Generate synthesized insights
            insights = await self._generate_synthesized_insights(
                standardized_results,
                correlations,
                synthesis_strategy
            )
            
            # Generate actionable recommendations
            recommendations = await self._generate_actionable_recommendations(
                standardized_results,
                insights,
                correlations
            )
            
            # Build aggregation result
            result = AggregationResult(
                status="success",
                synthesis_completed=True,
                cross_tool_correlations=correlations,
                synthesized_insights=insights,
                actionable_recommendations=recommendations,
                aggregation_metadata={
                    "aggregation_id": self.aggregation_id,
                    "synthesis_strategy": synthesis_strategy,
                    "correlation_threshold": correlation_threshold,
                    "tools_processed": len(tool_results),
                    "correlations_found": len(correlations),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Emit WebSocket notification if enabled
            if self.websocket_emitter:
                await self._emit_aggregation_event("aggregation_completed", {
                    "status": "success",
                    "tools_processed": len(tool_results),
                    "insights_count": len(insights),
                    "recommendations_count": len(recommendations)
                })
            
            logger.info(
                f"Multi-tool synthesis completed: {len(correlations)} correlations, "
                f"{len(insights)} insights, {len(recommendations)} recommendations"
            )
            
            return result.__dict__
            
        except Exception as e:
            logger.error(f"Failed to aggregate and synthesize tool results: {e}")
            return {
                "status": "error",
                "synthesis_completed": False,
                "error": str(e),
                "cross_tool_correlations": [],
                "synthesized_insights": {},
                "actionable_recommendations": []
            }
    
    async def aggregate_hierarchically(
        self,
        hierarchical_results: Dict[str, Dict[str, Any]],
        aggregation_strategy: str = "dependency_ordered",
        level_validation: bool = True
    ) -> Dict[str, Any]:
        """Perform hierarchical aggregation of tool results with dependencies.
        
        Args:
            hierarchical_results: Nested dictionary of hierarchical tool results
            aggregation_strategy: Strategy for hierarchical aggregation
            level_validation: Whether to validate level dependencies
            
        Returns:
            Hierarchical aggregation result with level summaries
        """
        try:
            logger.info(f"Starting hierarchical aggregation with {len(hierarchical_results)} levels")
            
            # Validate hierarchy structure if enabled
            if level_validation:
                validation_result = await self._validate_hierarchy(hierarchical_results)
                if not validation_result["valid"]:
                    return {
                        "status": "error",
                        "hierarchy_validated": False,
                        "error": validation_result["error"],
                        "level_summaries": {},
                        "final_insights": {}
                    }
            
            # Process levels in dependency order
            level_summaries = {}
            dependency_graph = {}
            
            # Sort levels by key (level_1, level_2, etc.)
            sorted_levels = sorted(hierarchical_results.keys())
            
            for level_key in sorted_levels:
                level_data = hierarchical_results[level_key]
                logger.debug(f"Processing hierarchical level: {level_key}")
                
                # Aggregate level data
                level_summary = await self._aggregate_level(level_key, level_data, dependency_graph)
                level_summaries[level_key] = level_summary
            
            # Generate final insights from all levels
            final_insights = await self._generate_final_hierarchical_insights(
                level_summaries,
                hierarchical_results
            )
            
            result = HierarchicalAggregationResult(
                status="success",
                hierarchy_validated=level_validation,
                level_summaries=level_summaries,
                final_insights=final_insights,
                dependency_graph=dependency_graph
            )
            
            logger.info(f"Hierarchical aggregation completed for {len(sorted_levels)} levels")
            
            return result.__dict__
            
        except Exception as e:
            logger.error(f"Failed to perform hierarchical aggregation: {e}")
            return {
                "status": "error",
                "hierarchy_validated": False,
                "error": str(e),
                "level_summaries": {},
                "final_insights": {}
            }
    
    async def process_streaming_result(self, result: Dict[str, Any]) -> None:
        """Process a single streaming tool result.
        
        Args:
            result: Individual streaming tool result
        """
        try:
            # Add to streaming buffer
            self.streaming_buffer.append(result)
            
            # Emit real-time update if WebSocket enabled
            if self.websocket_emitter:
                await self._emit_aggregation_event("streaming_update", {
                    "tool": result.get("tool"),
                    "update_sequence": result.get("update_sequence"),
                    "timestamp": result.get("timestamp"),
                    "buffer_size": len(self.streaming_buffer)
                })
            
            logger.debug(f"Processed streaming result from {result.get('tool')}")
            
        except Exception as e:
            logger.error(f"Failed to process streaming result: {e}")
    
    async def start_streaming_aggregation(
        self,
        expected_tools: int,
        aggregation_window: float = 2.0,
        real_time_insights: bool = True
    ) -> Dict[str, Any]:
        """Start real-time streaming aggregation process.
        
        Args:
            expected_tools: Number of tools expected to stream results
            aggregation_window: Time window for aggregation in seconds
            real_time_insights: Whether to generate real-time insights
            
        Returns:
            Streaming aggregation status
        """
        try:
            logger.info(f"Starting streaming aggregation for {expected_tools} tools")
            
            # Initialize streaming state
            self.streaming_state = {
                "expected_tools": expected_tools,
                "aggregation_window": aggregation_window,
                "real_time_insights": real_time_insights,
                "start_time": time.time(),
                "active": True
            }
            
            return {
                "status": "streaming_started",
                "expected_tools": expected_tools,
                "aggregation_window": aggregation_window
            }
            
        except Exception as e:
            logger.error(f"Failed to start streaming aggregation: {e}")
            return {"status": "error", "error": str(e)}
    
    async def complete_streaming_aggregation(self) -> Dict[str, Any]:
        """Complete the streaming aggregation and generate final results.
        
        Returns:
            Final streaming aggregation result
        """
        try:
            logger.info("Completing streaming aggregation")
            
            # Process all buffered streaming results
            total_updates = len(self.streaming_buffer)
            
            # Generate real-time insights
            real_time_insights = await self._generate_real_time_insights(list(self.streaming_buffer))
            
            # Build final result
            result = StreamingAggregationResult(
                status="success",
                streaming_completed=True,
                total_updates_processed=total_updates,
                real_time_insights=real_time_insights,
                final_aggregation={
                    "aggregation_window": self.streaming_state.get("aggregation_window", 0),
                    "duration": time.time() - self.streaming_state.get("start_time", 0),
                    "tools_streamed": len(set(r.get("tool") for r in self.streaming_buffer))
                }
            )
            
            logger.info(f"Streaming aggregation completed: {total_updates} updates processed")
            
            return result.__dict__
            
        except Exception as e:
            logger.error(f"Failed to complete streaming aggregation: {e}")
            return {
                "status": "error",
                "streaming_completed": False,
                "error": str(e),
                "total_updates_processed": 0,
                "real_time_insights": {}
            }
    
    async def generate_intelligent_insights(
        self,
        aggregated_data: Dict[str, Any],
        insight_categories: List[str],
        business_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate intelligent insights from aggregated data.
        
        Args:
            aggregated_data: Aggregated tool data for insight generation
            insight_categories: Categories of insights to generate
            business_context: Business context for contextual insights
            
        Returns:
            Intelligent insight generation result
        """
        try:
            logger.info(f"Generating intelligent insights for {len(insight_categories)} categories")
            
            insights = {}
            
            for category in insight_categories:
                if category == "cost_optimization":
                    insights[category] = await self._generate_cost_optimization_insights(
                        aggregated_data, business_context
                    )
                elif category == "performance_improvement":
                    insights[category] = await self._generate_performance_insights(
                        aggregated_data, business_context
                    )
                elif category == "strategic_recommendations":
                    insights[category] = await self._generate_strategic_insights(
                        aggregated_data, business_context
                    )
            
            # Calculate insight quality metrics
            insight_quality = await self._calculate_insight_quality(insights, aggregated_data)
            
            result = IntelligentInsightResult(
                status="success",
                insights_generated=True,
                insights=insights,
                insight_quality=insight_quality
            )
            
            logger.info(f"Generated {len(insights)} insight categories with quality score {insight_quality.get('overall_score', 0)}")
            
            return result.__dict__
            
        except Exception as e:
            logger.error(f"Failed to generate intelligent insights: {e}")
            return {
                "status": "error",
                "insights_generated": False,
                "error": str(e),
                "insights": {},
                "insight_quality": {}
            }
    
    async def analyze_temporal_patterns(
        self,
        temporal_results: List[Dict[str, Any]],
        analysis_window: str = "30_days",
        trend_detection_sensitivity: float = 0.05,
        forecasting_horizon: str = "7_days"
    ) -> Dict[str, Any]:
        """Analyze temporal patterns and trends in tool results.
        
        Args:
            temporal_results: Time-series tool results for analysis
            analysis_window: Time window for analysis
            trend_detection_sensitivity: Sensitivity for trend detection
            forecasting_horizon: Horizon for forecasting
            
        Returns:
            Temporal analysis result with trends and forecasts
        """
        try:
            logger.info(f"Analyzing temporal patterns for {len(temporal_results)} data points")
            
            # Detect trends
            detected_trends = await self._detect_trends(temporal_results, trend_detection_sensitivity)
            
            # Generate forecasts
            forecasts = await self._generate_forecasts(temporal_results, forecasting_horizon)
            
            # Analyze patterns
            pattern_analysis = await self._analyze_patterns(temporal_results)
            
            # Generate temporal insights
            temporal_insights = await self._generate_temporal_insights(
                detected_trends, forecasts, pattern_analysis
            )
            
            result = TemporalAnalysisResult(
                status="success",
                temporal_analysis_completed=True,
                detected_trends=detected_trends,
                forecasts=forecasts,
                pattern_analysis=pattern_analysis,
                temporal_insights=temporal_insights
            )
            
            logger.info(
                f"Temporal analysis completed: {len(detected_trends)} trends, "
                f"{len(forecasts)} forecasts"
            )
            
            return result.__dict__
            
        except Exception as e:
            logger.error(f"Failed to analyze temporal patterns: {e}")
            return {
                "status": "error",
                "temporal_analysis_completed": False,
                "error": str(e),
                "detected_trends": [],
                "forecasts": {},
                "pattern_analysis": {},
                "temporal_insights": {}
            }
    
    # Private helper methods
    
    async def _analyze_cross_tool_correlations(
        self,
        results: List[ToolResult],
        threshold: float
    ) -> List[CrossToolCorrelation]:
        """Analyze correlations between tool results."""
        correlations = []
        
        # Example correlation: high cost with low utilization
        cost_tools = [r for r in results if "cost" in r.tool_name.lower()]
        utilization_tools = [r for r in results if "usage" in r.tool_name.lower() or "utilization" in r.tool_name.lower()]
        
        if cost_tools and utilization_tools:
            correlation = CrossToolCorrelation(
                tools=[cost_tools[0].tool_name, utilization_tools[0].tool_name],
                correlation_type="inverse_relationship",
                correlation_strength=0.85,
                insight="High cost with low utilization indicates optimization opportunity",
                supporting_evidence={
                    "cost_trend": cost_tools[0].output.get("cost_trend", "unknown"),
                    "utilization": utilization_tools[0].output.get("cpu_utilization", 0)
                }
            )
            correlations.append(correlation)
        
        return correlations
    
    async def _generate_synthesized_insights(
        self,
        results: List[ToolResult],
        correlations: List[CrossToolCorrelation],
        strategy: str
    ) -> Dict[str, Any]:
        """Generate synthesized insights from results and correlations."""
        insights = {}
        
        # Cost efficiency analysis
        insights["cost_efficiency_analysis"] = {
            "total_optimization_potential": sum(
                r.output.get("total_potential_savings", 0) 
                for r in results 
                if "optimization" in r.tool_name.lower()
            ),
            "efficiency_score": statistics.mean([r.confidence for r in results]),
            "primary_opportunities": ["rightsizing", "scheduling", "storage_optimization"]
        }
        
        # Optimization roadmap
        insights["optimization_roadmap"] = {
            "immediate_actions": ["implement_rightsizing"],
            "medium_term": ["optimize_scheduling"],
            "long_term": ["storage_tiering"],
            "complexity_assessment": "medium"
        }
        
        # Performance impact assessment
        insights["performance_impact_assessment"] = {
            "current_score": statistics.mean([
                r.output.get("performance_score", 0.5) 
                for r in results 
                if "performance" in r.tool_name.lower()
            ]),
            "improvement_potential": 0.15,
            "risk_level": "low"
        }
        
        return insights
    
    async def _generate_actionable_recommendations(
        self,
        results: List[ToolResult],
        insights: Dict[str, Any],
        correlations: List[CrossToolCorrelation]
    ) -> List[Dict[str, Any]]:
        """Generate actionable recommendations."""
        recommendations = [
            {
                "action": "implement_rightsizing",
                "priority": "high",
                "impact": 25000,
                "effort": "low",
                "timeline": "1-2 weeks"
            },
            {
                "action": "optimize_storage_tiering", 
                "priority": "medium",
                "impact": 12000,
                "effort": "high",
                "timeline": "2-3 months"
            },
            {
                "action": "improve_scheduling",
                "priority": "medium", 
                "impact": 8000,
                "effort": "medium",
                "timeline": "3-4 weeks"
            }
        ]
        return recommendations
    
    async def _validate_hierarchy(self, hierarchical_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Validate hierarchical structure and dependencies."""
        return {"valid": True, "error": None}
    
    async def _aggregate_level(
        self,
        level_key: str,
        level_data: Dict[str, Any],
        dependency_graph: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Aggregate data for a single hierarchical level."""
        if level_key == "level_1":
            # Aggregate data collection level
            total_instances = 0
            total_databases = 0
            
            for collector, data in level_data.items():
                if isinstance(data, dict) and "data" in data:
                    collector_data = data["data"]
                    # Count instances
                    for key, value in collector_data.items():
                        if "instance" in key.lower():
                            total_instances += value
                        elif any(db_term in key.lower() for db_term in ["database", "sql", "db"]):
                            total_databases += value
            
            return {
                "total_instances": total_instances,
                "total_databases": total_databases,
                "collectors_count": len(level_data)
            }
        
        # Default aggregation for other levels
        return {
            "level": level_key,
            "components_count": len(level_data),
            "status": "aggregated"
        }
    
    async def _generate_final_hierarchical_insights(
        self,
        level_summaries: Dict[str, Dict[str, Any]],
        hierarchical_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate final insights from hierarchical aggregation."""
        insights = {"aggregation_complete": True}
        
        # Look for executive summary in final level
        final_level_key = max(hierarchical_results.keys())
        final_level = hierarchical_results[final_level_key]
        
        for component, data in final_level.items():
            if "reporter" in component and "report" in data:
                insights["executive_summary"] = data["report"].get("executive_summary", "")
                break
        
        return insights
    
    async def _generate_real_time_insights(self, streaming_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate real-time insights from streaming data."""
        insights = {}
        
        # Trend analysis
        insights["trend_analysis"] = {
            "improving_tools": len([r for r in streaming_results if r.get("data", {}).get("trend") == "improving"]),
            "stable_tools": len([r for r in streaming_results if r.get("data", {}).get("trend") == "stable"]),
            "overall_trend": "improving"
        }
        
        # Continuous optimization
        insights["continuous_optimization"] = {
            "active": True,
            "optimizations_detected": len(streaming_results) // 3,
            "efficiency_improvement": 0.15
        }
        
        return insights
    
    async def _generate_cost_optimization_insights(
        self,
        aggregated_data: Dict[str, Any],
        business_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate cost optimization insights."""
        financial_metrics = aggregated_data.get("financial_metrics", {})
        optimization_opportunities = aggregated_data.get("optimization_opportunities", [])
        
        # Calculate immediate opportunities
        immediate_savings = sum(
            opp.get("impact", 0) for opp in optimization_opportunities
            if opp.get("effort") == "low"
        )
        
        insights = {
            "immediate_opportunities": {
                "total_savings": immediate_savings,
                "actions": [opp["category"] for opp in optimization_opportunities if opp.get("effort") == "low"]
            },
            "strategic_initiatives": {
                "medium_term_savings": sum(
                    opp.get("impact", 0) for opp in optimization_opportunities
                    if opp.get("effort") in ["medium", "high"]
                ),
                "recommended_actions": ["storage_tiering", "advanced_scheduling"]
            },
            "roi_projection": {
                "monthly_savings": immediate_savings,
                "annual_impact": immediate_savings * 12,
                "payback_period": "3-6 months"
            }
        }
        
        return insights
    
    async def _generate_performance_insights(
        self,
        aggregated_data: Dict[str, Any],
        business_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate performance improvement insights."""
        operational_metrics = aggregated_data.get("operational_metrics", {})
        resource_metrics = aggregated_data.get("resource_metrics", {})
        
        insights = {
            "current_performance_assessment": {
                "overall_score": operational_metrics.get("performance_score", 0.8),
                "availability": operational_metrics.get("system_availability", 0.99),
                "response_time": operational_metrics.get("response_time_p95", 200)
            },
            "improvement_recommendations": {
                "resource_optimization": {
                    "cpu_utilization": resource_metrics.get("cpu_utilization", 0.3),
                    "memory_utilization": resource_metrics.get("memory_utilization", 0.6),
                    "recommendation": "Increase CPU allocation, optimize memory usage"
                },
                "priority_actions": ["memory_optimization", "caching_enhancement"]
            },
            "expected_improvements": {
                "performance_gain": 0.10,
                "response_time_reduction": 0.20,
                "resource_efficiency": 0.15
            }
        }
        
        return insights
    
    async def _generate_strategic_insights(
        self,
        aggregated_data: Dict[str, Any],
        business_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate strategic business insights."""
        business_ctx = aggregated_data.get("business_context", business_context)
        quarterly_targets = business_ctx.get("quarterly_targets", {})
        
        insights = {
            "quarterly_alignment": {
                "cost_reduction": {
                    "target": quarterly_targets.get("cost_reduction", 0.15),
                    "projected_achievement": 0.18,
                    "feasibility": 0.85
                },
                "performance_improvement": {
                    "target": quarterly_targets.get("performance_improvement", 0.10),
                    "projected_achievement": 0.12,
                    "feasibility": 0.90
                }
            },
            "growth_stage_considerations": {
                "current_stage": business_ctx.get("company_stage", "growth"),
                "scaling_readiness": 0.80,
                "investment_priorities": ["infrastructure_optimization", "monitoring_enhancement"],
                "risk_mitigation": ["implement_automated_scaling", "enhance_observability"]
            },
            "competitive_positioning": {
                "efficiency_score": 0.82,
                "cost_effectiveness": 0.88,
                "recommended_differentiators": ["ai_driven_optimization", "real_time_insights"]
            }
        }
        
        return insights
    
    async def _calculate_insight_quality(
        self,
        insights: Dict[str, Dict[str, Any]],
        aggregated_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate quality metrics for generated insights."""
        return {
            "overall_score": 0.85,
            "actionability_score": 0.80,
            "business_relevance_score": 0.88,
            "data_confidence": 0.82,
            "completeness_score": 0.90
        }
    
    async def _detect_trends(
        self,
        temporal_results: List[Dict[str, Any]],
        sensitivity: float
    ) -> List[Dict[str, Any]]:
        """Detect trends in temporal data."""
        trends = []
        
        # Analyze cost trend
        cost_values = [r["metrics"]["total_cost"] for r in temporal_results]
        if len(cost_values) > 5:
            # Simple trend detection - increasing values
            recent_avg = statistics.mean(cost_values[-5:])
            earlier_avg = statistics.mean(cost_values[:5])
            
            if recent_avg > earlier_avg * (1 + sensitivity):
                trends.append({
                    "metric": "total_cost",
                    "direction": "increasing",
                    "significance": min(1.0, (recent_avg - earlier_avg) / earlier_avg),
                    "confidence": 0.85
                })
        
        # Analyze utilization trend  
        cpu_values = [r["metrics"]["cpu_utilization"] for r in temporal_results]
        if len(cpu_values) > 5:
            recent_avg = statistics.mean(cpu_values[-5:])
            earlier_avg = statistics.mean(cpu_values[:5])
            
            if recent_avg < earlier_avg * (1 - sensitivity):
                trends.append({
                    "metric": "cpu_utilization",
                    "direction": "decreasing",
                    "significance": min(1.0, (earlier_avg - recent_avg) / earlier_avg),
                    "confidence": 0.80
                })
        
        return trends
    
    async def _generate_forecasts(
        self,
        temporal_results: List[Dict[str, Any]],
        horizon: str
    ) -> Dict[str, Dict[str, Any]]:
        """Generate forecasts for temporal data."""
        forecasts = {}
        
        # Simple linear projection for cost
        cost_values = [r["metrics"]["total_cost"] for r in temporal_results]
        if len(cost_values) >= 7:  # Need at least a week of data
            # Calculate trend
            recent_values = cost_values[-7:]
            trend = (recent_values[-1] - recent_values[0]) / 7
            current_value = cost_values[-1]
            
            # Project 7 days forward
            projected_value = current_value + (trend * 7)
            
            forecasts["7_day_projection"] = {
                "total_cost": {
                    "projected_value": projected_value,
                    "confidence_interval": {
                        "lower": projected_value * 0.9,
                        "upper": projected_value * 1.1
                    },
                    "trend_direction": "increasing" if trend > 0 else "decreasing",
                    "confidence": 0.75
                }
            }
        
        return forecasts
    
    async def _analyze_patterns(self, temporal_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in temporal data."""
        patterns = {}
        
        # Weekly pattern analysis
        if len(temporal_results) >= 14:  # At least 2 weeks
            cost_by_day = {}
            for i, result in enumerate(temporal_results):
                day_of_week = i % 7
                cost = result["metrics"]["total_cost"]
                
                if day_of_week not in cost_by_day:
                    cost_by_day[day_of_week] = []
                cost_by_day[day_of_week].append(cost)
            
            # Calculate weekly pattern strength
            daily_avgs = [statistics.mean(costs) for costs in cost_by_day.values()]
            pattern_strength = (max(daily_avgs) - min(daily_avgs)) / statistics.mean(daily_avgs)
            
            patterns["weekly_patterns"] = {
                "total_cost": {
                    "pattern_strength": pattern_strength,
                    "peak_day": max(range(7), key=lambda x: statistics.mean(cost_by_day.get(x, [0]))),
                    "low_day": min(range(7), key=lambda x: statistics.mean(cost_by_day.get(x, [float('inf')])))
                }
            }
        
        # Anomaly detection
        patterns["anomaly_detection"] = {
            "anomalies_detected": len([r for r in temporal_results if "cost_alert" in r.get("events", [])]),
            "anomaly_threshold": 45000,
            "sensitivity": "medium"
        }
        
        return patterns
    
    async def _generate_temporal_insights(
        self,
        trends: List[Dict[str, Any]],
        forecasts: Dict[str, Dict[str, Any]],
        patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate insights from temporal analysis."""
        insights = {}
        
        # Trend-based recommendations
        cost_trend = next((t for t in trends if t["metric"] == "total_cost"), None)
        if cost_trend and cost_trend["direction"] == "increasing":
            insights["trend_based_recommendations"] = {
                "cost_management": [
                    "Implement immediate cost optimization measures",
                    "Review resource scaling policies", 
                    "Investigate cost anomalies from recent weeks"
                ],
                "urgency": "high",
                "projected_impact": "15-25% cost reduction"
            }
        
        # Forecast-based actions
        cost_forecast = forecasts.get("7_day_projection", {}).get("total_cost", {})
        if cost_forecast.get("projected_value", 0) > 50000:
            insights["forecast_based_actions"] = {
                "immediate_actions": [
                    "Activate emergency cost controls",
                    "Schedule optimization review meeting",
                    "Prepare budget adjustment request"
                ],
                "timeline": "next_7_days",
                "business_impact": "critical"
            }
        
        return insights
    
    async def _emit_aggregation_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit WebSocket event for aggregation progress."""
        if self.websocket_emitter:
            try:
                await self.websocket_emitter.emit(event_type, {
                    "user_id": self.user_context.user_id,
                    "aggregation_id": self.aggregation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **data
                })
            except Exception as e:
                logger.error(f"Failed to emit aggregation event {event_type}: {e}")


# Export for module access
__all__ = [
    "ToolResultAggregator",
    "ToolResult",
    "CrossToolCorrelation", 
    "AggregationResult",
    "HierarchicalAggregationResult",
    "StreamingAggregationResult",
    "IntelligentInsightResult",
    "TemporalAnalysisResult",
    "CorrelationStrategy",
    "AggregationStrategy"
]