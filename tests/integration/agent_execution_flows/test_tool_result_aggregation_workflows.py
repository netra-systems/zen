"""
Test Tool Result Aggregation Workflows Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure effective aggregation of tool results into actionable insights
- Value Impact: Transforms raw tool outputs into meaningful business intelligence
- Strategic Impact: Core value delivery mechanism that turns technical data into business decisions

Tests tool result aggregation including data synthesis, cross-tool correlation,
insight generation, and comprehensive result processing workflows.
"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import time

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.tools.result_aggregator import ToolResultAggregator
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestToolResultAggregationWorkflows(BaseIntegrationTest):
    """Integration tests for tool result aggregation workflows."""

    @pytest.mark.integration
    @pytest.mark.tool_execution_workflows
    async def test_multi_tool_result_synthesis_and_correlation(self, real_services_fixture):
        """Test synthesis and correlation of results from multiple tools."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="aggregation_user_1415",
            thread_id="thread_1715",
            session_id="session_2015",
            workspace_id="aggregation_workspace_1315"
        )
        
        result_aggregator = ToolResultAggregator(
            user_context=user_context,
            correlation_enabled=True,
            synthesis_mode="comprehensive"
        )
        
        # Multi-tool results to aggregate
        tool_results = {
            "cost_analyzer": {
                "status": "success",
                "output": {
                    "total_monthly_cost": 45000,
                    "cost_trend": "increasing",
                    "cost_breakdown": {"compute": 25000, "storage": 15000, "network": 5000},
                    "anomalies": ["unusual_spike_jan_15", "weekend_usage_increase"]
                },
                "execution_time": 5.2,
                "confidence": 0.92
            },
            "usage_analyzer": {
                "status": "success",
                "output": {
                    "cpu_utilization": 0.35,
                    "memory_utilization": 0.68,
                    "storage_efficiency": 0.71,
                    "peak_usage_times": ["09:00-11:00", "14:00-16:00"],
                    "underutilized_resources": ["instance_type_m5.large", "instance_type_c5.xlarge"]
                },
                "execution_time": 3.8,
                "confidence": 0.87
            },
            "optimization_engine": {
                "status": "success",
                "output": {
                    "optimization_opportunities": [
                        {"type": "rightsizing", "potential_savings": 12000, "confidence": 0.89},
                        {"type": "scheduling", "potential_savings": 3500, "confidence": 0.76},
                        {"type": "storage_optimization", "potential_savings": 5500, "confidence": 0.82}
                    ],
                    "total_potential_savings": 21000,
                    "implementation_complexity": "medium"
                },
                "execution_time": 8.7,
                "confidence": 0.85
            },
            "performance_monitor": {
                "status": "success",
                "output": {
                    "performance_score": 0.73,
                    "bottlenecks": ["memory_pressure", "storage_latency"],
                    "improvement_areas": ["caching_strategy", "data_locality"],
                    "sla_compliance": 0.94
                },
                "execution_time": 2.1,
                "confidence": 0.91
            }
        }
        
        # Act - Aggregate and synthesize results
        aggregation_result = await result_aggregator.aggregate_and_synthesize(
            tool_results=tool_results,
            synthesis_strategy="cross_correlation_with_insights",
            correlation_threshold=0.7
        )
        
        # Assert - Verify aggregation and synthesis
        assert aggregation_result["status"] == "success"
        assert aggregation_result["synthesis_completed"] is True
        
        # Verify cross-tool correlations were identified
        correlations = aggregation_result["cross_tool_correlations"]
        assert len(correlations) > 0
        
        # Should correlate high cost with low utilization
        cost_utilization_correlation = next(
            (c for c in correlations if "cost_analyzer" in c["tools"] and "usage_analyzer" in c["tools"]),
            None
        )
        assert cost_utilization_correlation is not None
        assert cost_utilization_correlation["correlation_strength"] > 0.7
        
        # Verify comprehensive insights generation
        insights = aggregation_result["synthesized_insights"]
        assert "cost_efficiency_analysis" in insights
        assert "optimization_roadmap" in insights
        assert "performance_impact_assessment" in insights
        
        # Verify actionable recommendations
        recommendations = aggregation_result["actionable_recommendations"]
        assert len(recommendations) >= 3
        assert all("priority" in rec and "impact" in rec for rec in recommendations)

    @pytest.mark.integration
    @pytest.mark.tool_execution_workflows
    async def test_hierarchical_result_aggregation_with_dependencies(self, real_services_fixture):
        """Test hierarchical aggregation of results with tool dependencies."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="hierarchical_user_1416",
            thread_id="thread_1716",
            session_id="session_2016",
            workspace_id="hierarchical_workspace_1316"
        )
        
        result_aggregator = ToolResultAggregator(
            user_context=user_context,
            hierarchical_aggregation=True,
            dependency_aware=True
        )
        
        # Hierarchical tool results with dependencies
        hierarchical_results = {
            "level_1": {
                "data_collectors": {
                    "aws_collector": {"data": {"ec2_instances": 50, "rds_instances": 10}},
                    "azure_collector": {"data": {"vms": 30, "sql_databases": 5}},
                    "gcp_collector": {"data": {"compute_instances": 25, "cloud_sql": 3}}
                }
            },
            "level_2": {
                "analyzers": {
                    "cost_analyzer": {
                        "depends_on": ["aws_collector", "azure_collector", "gcp_collector"],
                        "analysis": {"total_cost": 75000, "cost_per_provider": {"aws": 40000, "azure": 20000, "gcp": 15000}}
                    },
                    "usage_analyzer": {
                        "depends_on": ["aws_collector", "azure_collector", "gcp_collector"], 
                        "analysis": {"avg_utilization": 0.42, "peak_utilization": 0.78}
                    }
                }
            },
            "level_3": {
                "optimizers": {
                    "multi_cloud_optimizer": {
                        "depends_on": ["cost_analyzer", "usage_analyzer"],
                        "optimizations": {"cross_cloud_savings": 18000, "workload_distribution": "optimized"}
                    }
                }
            },
            "level_4": {
                "reporters": {
                    "executive_reporter": {
                        "depends_on": ["multi_cloud_optimizer"],
                        "report": {"executive_summary": "Multi-cloud optimization opportunity: $18k monthly savings"}
                    }
                }
            }
        }
        
        # Act - Perform hierarchical aggregation
        hierarchical_aggregation = await result_aggregator.aggregate_hierarchically(
            hierarchical_results=hierarchical_results,
            aggregation_strategy="dependency_ordered",
            level_validation=True
        )
        
        # Assert - Verify hierarchical aggregation
        assert hierarchical_aggregation["status"] == "success"
        assert hierarchical_aggregation["hierarchy_validated"] is True
        
        # Verify level-wise aggregation
        level_summaries = hierarchical_aggregation["level_summaries"]
        assert len(level_summaries) == 4
        
        # Level 1 should aggregate data collection
        level_1_summary = level_summaries["level_1"]
        assert level_1_summary["total_instances"] == 50 + 30 + 25  # All compute instances
        assert level_1_summary["total_databases"] == 10 + 5 + 3   # All database instances
        
        # Final level should have executive insights
        final_insights = hierarchical_aggregation["final_insights"]
        assert "$18k" in final_insights["executive_summary"]
        assert final_insights["aggregation_complete"] is True

    @pytest.mark.integration 
    @pytest.mark.tool_execution_workflows
    async def test_real_time_result_streaming_and_aggregation(self, real_services_fixture):
        """Test real-time streaming and aggregation of tool results."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="streaming_user_1417",
            thread_id="thread_1717",
            session_id="session_2017",
            workspace_id="streaming_workspace_1317"
        )
        
        mock_websocket_emitter = MagicMock()
        mock_websocket_emitter.emit = AsyncMock()
        
        result_aggregator = ToolResultAggregator(
            user_context=user_context,
            real_time_streaming=True,
            websocket_emitter=mock_websocket_emitter,
            streaming_aggregation=True
        )
        
        # Simulate streaming tool results
        streaming_tools = [
            {"name": "continuous_monitor", "streaming": True, "update_interval": 0.2},
            {"name": "real_time_analyzer", "streaming": True, "update_interval": 0.3},
            {"name": "live_optimizer", "streaming": True, "update_interval": 0.5}
        ]
        
        streaming_results = []
        
        async def simulate_streaming_tool(tool_name: str, update_interval: float):
            """Simulate a streaming tool that produces periodic results."""
            for i in range(5):  # 5 updates per tool
                await asyncio.sleep(update_interval)
                result = {
                    "tool": tool_name,
                    "timestamp": time.time(),
                    "update_sequence": i,
                    "data": {
                        f"{tool_name}_metric": 100 + i * 10,
                        "trend": "improving" if i > 2 else "stable",
                        "confidence": 0.8 + (i * 0.04)
                    }
                }
                streaming_results.append(result)
                
                # Send to aggregator
                await result_aggregator.process_streaming_result(result)
        
        # Act - Process streaming results
        streaming_tasks = []
        for tool in streaming_tools:
            task = asyncio.create_task(
                simulate_streaming_tool(tool["name"], tool["update_interval"])
            )
            streaming_tasks.append(task)
        
        # Start aggregation
        aggregation_task = asyncio.create_task(
            result_aggregator.start_streaming_aggregation(
                expected_tools=len(streaming_tools),
                aggregation_window=2.0,
                real_time_insights=True
            )
        )
        
        # Wait for streaming to complete
        await asyncio.gather(*streaming_tasks)
        
        # Complete aggregation
        final_aggregation = await result_aggregator.complete_streaming_aggregation()
        
        # Assert - Verify streaming aggregation
        assert final_aggregation["status"] == "success"
        assert final_aggregation["streaming_completed"] is True
        
        # Verify all streaming updates were processed
        processed_updates = final_aggregation["total_updates_processed"]
        assert processed_updates == len(streaming_tools) * 5  # 5 updates per tool
        
        # Verify real-time insights were generated
        real_time_insights = final_aggregation["real_time_insights"]
        assert len(real_time_insights) > 0
        assert "trend_analysis" in real_time_insights
        assert "continuous_optimization" in real_time_insights
        
        # Verify WebSocket streaming occurred
        assert mock_websocket_emitter.emit.call_count >= processed_updates

    @pytest.mark.integration
    @pytest.mark.tool_execution_workflows 
    async def test_intelligent_insight_generation_from_aggregated_results(self, real_services_fixture):
        """Test intelligent insight generation from aggregated tool results."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="insight_user_1418",
            thread_id="thread_1718", 
            session_id="session_2018",
            workspace_id="insight_workspace_1318"
        )
        
        result_aggregator = ToolResultAggregator(
            user_context=user_context,
            insight_generation=True,
            intelligence_level="advanced",
            business_context_aware=True
        )
        
        # Complex aggregated data for insight generation
        aggregated_data = {
            "financial_metrics": {
                "total_monthly_spend": 125000,
                "spend_growth_rate": 0.18,
                "cost_per_user": 45.50,
                "budget_variance": 0.15
            },
            "operational_metrics": {
                "system_availability": 0.9985,
                "performance_score": 0.82,
                "error_rate": 0.002,
                "response_time_p95": 245
            },
            "resource_metrics": {
                "cpu_utilization": 0.34,
                "memory_utilization": 0.67,
                "storage_utilization": 0.78,
                "network_utilization": 0.23
            },
            "optimization_opportunities": [
                {"category": "rightsizing", "impact": 25000, "effort": "low"},
                {"category": "scheduling", "impact": 8000, "effort": "medium"},
                {"category": "storage_tiering", "impact": 12000, "effort": "high"}
            ],
            "business_context": {
                "company_stage": "growth",
                "team_size": 150,
                "quarterly_targets": {"cost_reduction": 0.15, "performance_improvement": 0.10}
            }
        }
        
        # Act - Generate intelligent insights
        insight_result = await result_aggregator.generate_intelligent_insights(
            aggregated_data=aggregated_data,
            insight_categories=["cost_optimization", "performance_improvement", "strategic_recommendations"],
            business_context=aggregated_data["business_context"]
        )
        
        # Assert - Verify intelligent insight generation
        assert insight_result["status"] == "success"
        assert insight_result["insights_generated"] is True
        
        # Verify cost optimization insights
        cost_insights = insight_result["insights"]["cost_optimization"]
        assert "immediate_opportunities" in cost_insights
        assert "strategic_initiatives" in cost_insights
        
        immediate_savings = cost_insights["immediate_opportunities"]["total_savings"]
        assert immediate_savings >= 25000  # Should identify rightsizing opportunity
        
        # Verify performance improvement insights  
        performance_insights = insight_result["insights"]["performance_improvement"]
        assert "current_performance_assessment" in performance_insights
        assert "improvement_recommendations" in performance_insights
        
        # Should identify resource utilization issues
        assert "resource_optimization" in performance_insights["improvement_recommendations"]
        
        # Verify strategic recommendations
        strategic_insights = insight_result["insights"]["strategic_recommendations"]
        assert "quarterly_alignment" in strategic_insights
        assert "growth_stage_considerations" in strategic_insights
        
        # Should align with business targets
        cost_reduction_alignment = strategic_insights["quarterly_alignment"]["cost_reduction"]
        assert cost_reduction_alignment["feasibility"] > 0.8  # Should be highly feasible
        
        # Verify insight quality and actionability
        insight_quality = insight_result["insight_quality"]
        assert insight_quality["overall_score"] > 0.8
        assert insight_quality["actionability_score"] > 0.7
        assert insight_quality["business_relevance_score"] > 0.8

    @pytest.mark.integration
    @pytest.mark.tool_execution_workflows
    async def test_cross_temporal_result_analysis_and_trending(self, real_services_fixture):
        """Test cross-temporal analysis and trending of tool results over time."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="temporal_user_1419",
            thread_id="thread_1719",
            session_id="session_2019", 
            workspace_id="temporal_workspace_1319"
        )
        
        result_aggregator = ToolResultAggregator(
            user_context=user_context,
            temporal_analysis=True,
            trend_detection=True,
            forecasting_enabled=True
        )
        
        # Historical tool results over time
        temporal_results = []
        base_time = time.time() - (30 * 24 * 3600)  # 30 days ago
        
        for day in range(30):
            daily_timestamp = base_time + (day * 24 * 3600)
            
            # Simulate realistic trends
            cost_base = 40000
            cost_trend = cost_base + (day * 200) + (day * day * 5)  # Accelerating cost growth
            
            utilization_base = 0.4
            utilization_trend = utilization_base - (day * 0.005)  # Declining utilization
            
            daily_result = {
                "timestamp": daily_timestamp,
                "date": f"2024-01-{day+1:02d}",
                "metrics": {
                    "total_cost": cost_trend + (day % 7) * 500,  # Weekly variance
                    "cpu_utilization": max(0.2, utilization_trend + (day % 3) * 0.05),
                    "memory_utilization": 0.6 + (day % 5) * 0.02,
                    "performance_score": 0.85 - (day * 0.003) + (day % 4) * 0.02,
                    "error_count": max(0, 10 - day + (day % 7) * 3)
                },
                "events": [
                    f"daily_optimization_run_{day}",
                    f"performance_monitoring_{day}"
                ] + (["cost_alert"] if day > 20 and cost_trend > 45000 else [])
            }
            temporal_results.append(daily_result)
        
        # Act - Perform temporal analysis
        temporal_analysis = await result_aggregator.analyze_temporal_patterns(
            temporal_results=temporal_results,
            analysis_window="30_days",
            trend_detection_sensitivity=0.05,
            forecasting_horizon="7_days"
        )
        
        # Assert - Verify temporal analysis
        assert temporal_analysis["status"] == "success"
        assert temporal_analysis["temporal_analysis_completed"] is True
        
        # Verify trend detection
        detected_trends = temporal_analysis["detected_trends"]
        assert len(detected_trends) > 0
        
        # Should detect cost increase trend
        cost_trend = next(
            (t for t in detected_trends if t["metric"] == "total_cost"),
            None
        )
        assert cost_trend is not None
        assert cost_trend["direction"] == "increasing"
        assert cost_trend["significance"] > 0.8
        
        # Should detect utilization decline
        utilization_trend = next(
            (t for t in detected_trends if t["metric"] == "cpu_utilization"),
            None
        )
        assert utilization_trend is not None
        assert utilization_trend["direction"] == "decreasing"
        
        # Verify forecasting
        forecasts = temporal_analysis["forecasts"]
        assert "7_day_projection" in forecasts
        
        cost_forecast = forecasts["7_day_projection"]["total_cost"]
        assert cost_forecast["projected_value"] > temporal_results[-1]["metrics"]["total_cost"]
        assert cost_forecast["confidence_interval"] is not None
        
        # Verify pattern recognition
        patterns = temporal_analysis["pattern_analysis"]
        assert "weekly_patterns" in patterns
        assert "anomaly_detection" in patterns
        
        # Should identify weekly cost patterns
        weekly_pattern = patterns["weekly_patterns"]["total_cost"]
        assert weekly_pattern["pattern_strength"] > 0.3
        
        # Verify actionable insights from temporal analysis
        temporal_insights = temporal_analysis["temporal_insights"]
        assert "trend_based_recommendations" in temporal_insights
        assert "forecast_based_actions" in temporal_insights
        
        # Should recommend action based on cost trend
        cost_recommendations = temporal_insights["trend_based_recommendations"]["cost_management"]
        assert len(cost_recommendations) > 0
        assert any("optimization" in rec.lower() for rec in cost_recommendations)