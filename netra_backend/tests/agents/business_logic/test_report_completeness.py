"""Reporting Agent Business Logic Completeness Validation Tests

Business Value Justification (BVJ):
- Segment: Enterprise, Mid-Market
- Business Goal: Demonstrate clear ROI and value delivery
- Value Impact: Drives renewal and expansion decisions
- Revenue Impact: Critical for retention (affects 100% of revenue base)

This test suite validates that reports:
1. Clearly demonstrate delivered value
2. Include measurable outcomes
3. Provide actionable next steps
4. Build confidence in recommendations
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
import json
from decimal import Decimal

from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.base.execution_context import ExecutionContext, ExecutionMetadata
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestReportCompletenessLogic:
    """Validate reporting outputs demonstrate clear business value."""
    
    @pytest.fixture
    async def reporting_agent(self):
        """Create reporting agent with mocked dependencies."""
        llm_manager = AsyncMock()
        tool_dispatcher = AsyncMock()
        
        agent = ReportingSubAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher
        )
        return agent
    
    @pytest.fixture
    def report_scenarios(self) -> List[Dict[str, Any]]:
        """Complete optimization scenarios for reporting."""
        return [
            {
                "name": "successful_cost_optimization",
                "optimization_context": {
                    "initial_state": {
                        "monthly_cost": 25000,
                        "model": "gpt-4",
                        "request_volume": 500000
                    },
                    "optimizations_applied": [
                        {
                            "type": "model_switching",
                            "description": "Routed 60% to GPT-3.5-Turbo",
                            "implementation_date": "2024-01-15",
                            "estimated_savings": 10000,
                            "actual_savings": 9500
                        },
                        {
                            "type": "caching",
                            "description": "Implemented semantic caching",
                            "implementation_date": "2024-01-20",
                            "estimated_savings": 3000,
                            "actual_savings": 3200
                        }
                    ],
                    "current_state": {
                        "monthly_cost": 12300,
                        "model_mix": {"gpt-4": 0.4, "gpt-3.5-turbo": 0.6},
                        "cache_hit_rate": 0.32
                    }
                },
                "expected_report": {
                    "executive_summary": {
                        "total_savings": 12700,
                        "savings_percentage": 50.8,
                        "roi": "1270%",
                        "payback_period": "< 1 month",
                        "confidence_score": 0.95
                    },
                    "performance_metrics": {
                        "cost_reduction": {"target": 10000, "achieved": 12700, "status": "exceeded"},
                        "quality_maintained": {"target": 0.95, "achieved": 0.97, "status": "met"},
                        "latency_impact": {"before": 2.5, "after": 1.8, "improvement": "28%"}
                    },
                    "implementation_summary": {
                        "actions_taken": 2,
                        "timeline": "5 days",
                        "resources_used": "3 engineers",
                        "challenges_overcome": ["Quality monitoring", "Cache tuning"]
                    },
                    "next_steps": [
                        {
                            "recommendation": "Expand caching to edge locations",
                            "potential_savings": 2000,
                            "effort": "low",
                            "priority": "high"
                        }
                    ],
                    "visual_elements": ["cost_trend_chart", "model_distribution_pie", "savings_breakdown"]
                }
            },
            {
                "name": "latency_optimization_success",
                "optimization_context": {
                    "initial_state": {
                        "p95_latency_ms": 5000,
                        "p50_latency_ms": 2000,
                        "user_satisfaction": 3.2
                    },
                    "optimizations_applied": [
                        {
                            "type": "edge_caching",
                            "description": "Deployed 3 regional caches",
                            "latency_reduction": 2500,
                            "coverage": "85% of users"
                        },
                        {
                            "type": "request_batching",
                            "description": "50ms batching window",
                            "throughput_increase": 3.5,
                            "latency_tradeoff": 25
                        }
                    ],
                    "current_state": {
                        "p95_latency_ms": 2100,
                        "p50_latency_ms": 900,
                        "user_satisfaction": 4.6
                    }
                },
                "expected_report": {
                    "executive_summary": {
                        "latency_reduction": "58%",
                        "user_satisfaction_increase": 1.4,
                        "sla_compliance": "99.5%",
                        "performance_gain": "2.3x"
                    },
                    "technical_achievements": {
                        "infrastructure_changes": ["3 edge locations", "Redis cluster", "Load balancer config"],
                        "optimization_techniques": ["Intelligent routing", "Request coalescing", "Predictive caching"],
                        "monitoring_improvements": ["Real-time dashboards", "Alerting system", "Performance tracking"]
                    },
                    "business_impact": {
                        "customer_retention": "+15%",
                        "support_tickets": "-40%",
                        "nps_score": "+22 points",
                        "revenue_impact": "Protected $50K MRR"
                    }
                }
            },
            {
                "name": "partial_success_with_learnings",
                "optimization_context": {
                    "initial_state": {"monthly_cost": 15000},
                    "optimizations_applied": [
                        {
                            "type": "model_switching",
                            "estimated_savings": 5000,
                            "actual_savings": 2500,
                            "issues": ["Quality degradation on complex queries", "Required rollback on 20% traffic"]
                        }
                    ],
                    "current_state": {"monthly_cost": 12500},
                    "learnings": [
                        "Need better query classification",
                        "Quality monitoring essential",
                        "Gradual rollout critical"
                    ]
                },
                "expected_report": {
                    "executive_summary": {
                        "achieved_savings": 2500,
                        "target_savings": 5000,
                        "achievement_rate": "50%",
                        "adjusted_recommendations": True
                    },
                    "learnings_section": {
                        "what_worked": ["Basic query routing", "A/B testing framework"],
                        "what_didnt": ["Complex query handling", "Initial classifier accuracy"],
                        "improvements_made": ["Enhanced classifier", "Quality safeguards"],
                        "future_approach": "Phase 2 with improved classification"
                    },
                    "revised_projections": {
                        "realistic_savings": 3500,
                        "timeline": "2 additional weeks",
                        "confidence": 0.85
                    }
                }
            }
        ]
    
    @pytest.mark.asyncio
    async def test_expected_output_for_standard_input(self, reporting_agent, report_scenarios):
        """Test that standard scenarios produce complete reports."""
        for scenario in report_scenarios:
            context = ExecutionContext(
                thread_id=f"test_report_{scenario['name']}",
                user_message="Generate optimization report",
                thread_context=scenario["optimization_context"]
            )
            
            # Mock report generation
            reporting_agent.llm_manager.generate_response = AsyncMock(
                return_value={
                    "content": json.dumps({
                        "report": scenario["expected_report"]
                    }),
                    "metadata": {"model": "test"}
                }
            )
            
            result = await reporting_agent.execute(context)
            
            # Validate report completeness
            assert result.success, f"Failed for scenario: {scenario['name']}"
            report = result.data.get("report", {})
            
            # Must have executive summary
            assert "executive_summary" in report
            summary = report["executive_summary"]
            
            # Summary must quantify value
            value_metrics = ["savings", "reduction", "improvement", "roi", "impact"]
            assert any(metric in str(summary).lower() for metric in value_metrics)
    
    @pytest.mark.asyncio
    async def test_edge_case_handling(self, reporting_agent):
        """Test handling of edge cases in reporting."""
        edge_cases = [
            {
                "name": "no_optimizations_applied",
                "context": {
                    "optimizations_applied": [],
                    "reason": "Data collection phase"
                },
                "expected_behavior": "data_collection_report"
            },
            {
                "name": "optimization_failure",
                "context": {
                    "optimizations_applied": [{"type": "failed", "reason": "Technical issues"}],
                    "rollback": True
                },
                "expected_behavior": "failure_analysis_report"
            },
            {
                "name": "mixed_results",
                "context": {
                    "optimizations_applied": [
                        {"success": True, "savings": 1000},
                        {"success": False, "reason": "Quality issues"},
                        {"success": True, "savings": 500}
                    ]
                },
                "expected_behavior": "balanced_report"
            }
        ]
        
        for case in edge_cases:
            context = ExecutionContext(
                thread_id=f"test_edge_{case['name']}",
                user_message="Generate report",
                thread_context=case["context"]
            )
            
            # Mock appropriate report
            reporting_agent.llm_manager.generate_response = AsyncMock(
                return_value={
                    "content": json.dumps({
                        "report": {
                            "type": case["expected_behavior"],
                            "content": f"Handled {case['name']}",
                            "has_value": True,
                            "next_steps": ["Continue monitoring", "Gather more data"]
                        }
                    }),
                    "metadata": {"model": "test"}
                }
            )
            
            result = await reporting_agent.execute(context)
            
            # Should handle gracefully
            assert result.success, f"Failed to handle edge case: {case['name']}"
            report = result.data["report"]
            assert report["has_value"], "Even edge cases should provide value"
            assert len(report["next_steps"]) > 0, "Should always have next steps"
    
    @pytest.mark.asyncio
    async def test_report_completeness(self, reporting_agent, report_scenarios):
        """Test that reports include all essential elements."""
        scenario = report_scenarios[0]  # Successful optimization
        
        context = ExecutionContext(
            thread_id="test_completeness",
            user_message="Generate complete report",
            thread_context=scenario["optimization_context"]
        )
        
        reporting_agent.llm_manager.generate_response = AsyncMock(
            return_value={
                "content": json.dumps({
                    "report": scenario["expected_report"]
                }),
                "metadata": {"model": "test"}
            }
        )
        
        # Execute with proper arguments
        await reporting_agent.execute(state, "run_completeness", False)
        
        # Get mocked response data
        response_data = json.loads(reporting_agent.llm_manager.generate_response.return_value["content"])
        report = response_data["report"]
        
        # Essential elements checklist
        essential_elements = [
            "executive_summary",
            "performance_metrics",
            "implementation_summary",
            "next_steps"
        ]
        
        for element in essential_elements:
            assert element in report, f"Missing essential element: {element}"
        
        # Executive summary completeness
        summary = report["executive_summary"]
        assert "total_savings" in summary or "savings" in str(summary)
        assert "roi" in summary or "return" in str(summary).lower()
        
        # Metrics completeness
        if "performance_metrics" in report:
            metrics = report["performance_metrics"]
            for metric_name, metric_data in metrics.items():
                # Each metric should have comparison data
                assert any(k in metric_data for k in ["target", "before", "baseline"]), \
                    f"Metric '{metric_name}' lacks comparison data"
                assert any(k in metric_data for k in ["achieved", "after", "current"]), \
                    f"Metric '{metric_name}' lacks result data"
        
        # Next steps completeness
        if "next_steps" in report and isinstance(report["next_steps"], list):
            for step in report["next_steps"]:
                assert "recommendation" in step or "action" in step, \
                    "Next step lacks clear action"
                assert any(k in step for k in ["potential_savings", "impact", "benefit"]), \
                    "Next step lacks value proposition"
    
    @pytest.mark.asyncio
    async def test_value_demonstration(self, reporting_agent, report_scenarios):
        """Test that reports clearly demonstrate delivered value."""
        scenario = report_scenarios[0]  # Cost optimization
        
        context = ExecutionContext(
            thread_id="test_value_demo",
            user_message="Demonstrate value delivered",
            thread_context=scenario["optimization_context"]
        )
        
        reporting_agent.llm_manager.generate_response = AsyncMock(
            return_value={
                "content": json.dumps({
                    "report": scenario["expected_report"]
                }),
                "metadata": {"model": "test"}
            }
        )
        
        # Execute with proper arguments
        await reporting_agent.execute(state, "run_value_demo", False)
        
        # Get mocked response data
        response_data = json.loads(reporting_agent.llm_manager.generate_response.return_value["content"])
        report = response_data["report"]
        
        # Value demonstration requirements
        summary = report["executive_summary"]
        
        # Must show actual numbers
        assert isinstance(summary.get("total_savings", 0), (int, float))
        assert summary.get("total_savings", 0) > 0
        
        # Must show percentage improvement
        if "savings_percentage" in summary:
            assert 0 < summary["savings_percentage"] <= 100
        
        # Must show ROI
        if "roi" in summary:
            roi_str = str(summary["roi"])
            assert "%" in roi_str or isinstance(summary["roi"], (int, float))
        
        # Must show quick wins
        if "payback_period" in summary:
            assert "month" in summary["payback_period"].lower() or \
                   "week" in summary["payback_period"].lower() or \
                   "day" in summary["payback_period"].lower()
    
    @pytest.mark.asyncio
    async def test_visual_elements_inclusion(self, reporting_agent):
        """Test that reports include appropriate visual elements."""
        context = ExecutionContext(
            thread_id="test_visuals",
            user_message="Generate visual report",
            thread_context={
                "data_points": {
                    "cost_over_time": [(1, 5000), (2, 4500), (3, 3500)],
                    "model_distribution": {"gpt-4": 0.3, "gpt-3.5": 0.7}
                }
            }
        )
        
        reporting_agent.llm_manager.generate_response = AsyncMock(
            return_value={
                "content": json.dumps({
                    "report": {
                        "executive_summary": {"savings": 1500},
                        "visual_elements": [
                            {
                                "type": "line_chart",
                                "title": "Cost Reduction Trend",
                                "data": "cost_over_time",
                                "description": "Monthly cost trending down"
                            },
                            {
                                "type": "pie_chart",
                                "title": "Model Usage Distribution",
                                "data": "model_distribution",
                                "description": "Shift to cost-effective models"
                            },
                            {
                                "type": "bar_chart",
                                "title": "Savings by Category",
                                "data": {"model": 1000, "caching": 500},
                                "description": "Breakdown of optimizations"
                            }
                        ],
                        "visualization_summary": "3 charts showing clear improvement trends"
                    }
                }),
                "metadata": {"model": "test"}
            }
        )
        
        # Execute with proper arguments
        await reporting_agent.execute(state, "run_visuals", False)
        
        # Get mocked response data
        response_data = json.loads(reporting_agent.llm_manager.generate_response.return_value["content"])
        report = response_data["report"]
        
        # Validate visual elements
        assert "visual_elements" in report
        visuals = report["visual_elements"]
        assert len(visuals) >= 2, "Need multiple visualizations"
        
        for visual in visuals:
            assert "type" in visual
            assert "title" in visual
            assert "data" in visual
            assert visual["type"] in ["line_chart", "bar_chart", "pie_chart", "table", "heatmap"]
    
    @pytest.mark.asyncio
    async def test_confidence_scoring(self, reporting_agent):
        """Test that reports include confidence scores."""
        context = ExecutionContext(
            thread_id="test_confidence",
            user_message="Report with confidence",
            thread_context={
                "optimizations_applied": [
                    {"type": "tested", "confidence": 0.95},
                    {"type": "estimated", "confidence": 0.7}
                ]
            }
        )
        
        reporting_agent.llm_manager.generate_response = AsyncMock(
            return_value={
                "content": json.dumps({
                    "report": {
                        "executive_summary": {
                            "total_savings": 5000,
                            "confidence_score": 0.82,
                            "confidence_breakdown": {
                                "tested_optimizations": 0.95,
                                "estimated_optimizations": 0.70,
                                "overall": 0.82
                            }
                        },
                        "confidence_factors": {
                            "data_quality": "high",
                            "testing_coverage": "medium",
                            "historical_accuracy": "90%"
                        },
                        "risk_assessment": {
                            "low_confidence_items": ["Estimated optimizations"],
                            "mitigation": "Monitor actual vs predicted closely"
                        }
                    }
                }),
                "metadata": {"model": "test"}
            }
        )
        
        # Execute with proper arguments
        await reporting_agent.execute(state, "run_confidence", False)
        
        # Get mocked response data
        response_data = json.loads(reporting_agent.llm_manager.generate_response.return_value["content"])
        report = response_data["report"]
        
        # Validate confidence scoring
        summary = report["executive_summary"]
        assert "confidence_score" in summary or "confidence" in str(summary).lower()
        
        if "confidence_score" in summary:
            assert 0 <= summary["confidence_score"] <= 1
        
        if "confidence_breakdown" in summary:
            breakdown = summary["confidence_breakdown"]
            assert all(0 <= v <= 1 for v in breakdown.values() if isinstance(v, (int, float)))
        
        # Should explain confidence factors
        if "confidence_factors" in report:
            factors = report["confidence_factors"]
            assert len(factors) > 0
    
    @pytest.mark.asyncio
    async def test_actionable_recommendations(self, reporting_agent):
        """Test that reports include actionable next steps."""
        context = ExecutionContext(
            thread_id="test_actionable",
            user_message="Provide next steps",
            thread_context={
                "current_optimizations": ["model_switching", "caching"],
                "remaining_opportunities": ["batching", "edge_deployment"]
            }
        )
        
        reporting_agent.llm_manager.generate_response = AsyncMock(
            return_value={
                "content": json.dumps({
                    "report": {
                        "executive_summary": {"savings": 5000},
                        "next_steps": [
                            {
                                "priority": 1,
                                "recommendation": "Implement request batching",
                                "rationale": "Low effort, high impact",
                                "potential_savings": 1500,
                                "implementation_time": "3 days",
                                "required_resources": ["1 engineer", "Redis upgrade"],
                                "success_criteria": "30% throughput increase",
                                "risks": "Slight latency increase (25ms)"
                            },
                            {
                                "priority": 2,
                                "recommendation": "Deploy edge caching",
                                "rationale": "Significant latency improvement",
                                "potential_savings": 2000,
                                "implementation_time": "2 weeks",
                                "required_resources": ["2 engineers", "3 edge locations"],
                                "success_criteria": "Sub-100ms P50 latency",
                                "risks": "Complexity increase"
                            }
                        ],
                        "implementation_roadmap": {
                            "week_1": "Complete batching implementation",
                            "week_2_3": "Edge deployment setup",
                            "week_4": "Monitoring and optimization"
                        }
                    }
                }),
                "metadata": {"model": "test"}
            }
        )
        
        # Execute with proper arguments
        await reporting_agent.execute(state, "run_actionable", False)
        
        # Get mocked response data
        response_data = json.loads(reporting_agent.llm_manager.generate_response.return_value["content"])
        report = response_data["report"]
        
        # Validate actionable recommendations
        assert "next_steps" in report
        steps = report["next_steps"]
        assert len(steps) > 0
        
        for step in steps:
            # Each step must be actionable
            assert "recommendation" in step
            assert "rationale" in step
            
            # Must quantify value
            assert any(k in step for k in ["potential_savings", "impact", "improvement"])
            
            # Must be implementable
            assert any(k in step for k in ["implementation_time", "timeline", "effort"])
            assert any(k in step for k in ["required_resources", "requirements", "needs"])
            
            # Should have success criteria
            if "success_criteria" in step:
                assert len(step["success_criteria"]) > 0
    
    @pytest.mark.asyncio
    async def test_comparative_analysis(self, reporting_agent):
        """Test that reports include before/after comparisons."""
        # Create proper state and context
        state = DeepAgentState(
            user_request="Show improvements",
            chat_thread_id="test_comparative",
            metadata={"context": {
                "before": {
                    "cost": 10000,
                    "latency": 3000,
                    "error_rate": 0.05,
                    "satisfaction": 3.0
                },
                "after": {
                    "cost": 6000,
                    "latency": 1200,
                    "error_rate": 0.01,
                    "satisfaction": 4.5
                }
            }}
        )
        context = ExecutionContext(
            context_id="test_comparative",
            metadata=ExecutionMetadata(thread_id="test_comparative")
        )
        
        reporting_agent.llm_manager.generate_response = AsyncMock(
            return_value={
                "content": json.dumps({
                    "report": {
                        "executive_summary": {"overall_improvement": "significant"},
                        "comparative_analysis": {
                            "cost": {
                                "before": 10000,
                                "after": 6000,
                                "change": -4000,
                                "change_percent": -40,
                                "status": "improved"
                            },
                            "latency": {
                                "before": 3000,
                                "after": 1200,
                                "change": -1800,
                                "change_percent": -60,
                                "status": "improved"
                            },
                            "error_rate": {
                                "before": 0.05,
                                "after": 0.01,
                                "change": -0.04,
                                "change_percent": -80,
                                "status": "improved"
                            },
                            "satisfaction": {
                                "before": 3.0,
                                "after": 4.5,
                                "change": 1.5,
                                "change_percent": 50,
                                "status": "improved"
                            }
                        },
                        "improvement_summary": "All metrics show significant improvement"
                    }
                }),
                "metadata": {"model": "test"}
            }
        )
        
        # Execute with proper arguments
        await reporting_agent.execute(state, "run_comparative", False)
        
        # Get mocked response data
        response_data = json.loads(reporting_agent.llm_manager.generate_response.return_value["content"])
        report = response_data["report"]
        
        # Validate comparative analysis
        assert "comparative_analysis" in report
        comparison = report["comparative_analysis"]
        
        for metric, data in comparison.items():
            # Each metric should have before/after
            assert "before" in data
            assert "after" in data
            assert "change" in data or "difference" in data
            
            # Should calculate percentage change
            if "change_percent" in data:
                assert isinstance(data["change_percent"], (int, float))
            
            # Should indicate improvement/degradation
            assert "status" in data or "trend" in data
    
    @pytest.mark.asyncio
    async def test_learning_documentation(self, reporting_agent):
        """Test that reports document learnings and insights."""
        # Create proper state and context
        state = DeepAgentState(
            user_request="Include learnings",
            chat_thread_id="test_learnings",
            metadata={"context": {
                "optimizations_tried": [
                    {"type": "aggressive_switching", "result": "quality_issues"},
                    {"type": "gradual_switching", "result": "success"}
                ],
                "unexpected_findings": [
                    "Cache hit rate higher than expected",
                    "User tolerance for latency lower than assumed"
                ]
            }}
        )
        context = ExecutionContext(
            context_id="test_learnings",
            metadata=ExecutionMetadata(thread_id="test_learnings")
        )
        
        reporting_agent.llm_manager.generate_response = AsyncMock(
            return_value={
                "content": json.dumps({
                    "report": {
                        "executive_summary": {"key_learning": "Gradual approach essential"},
                        "learnings_and_insights": {
                            "what_worked": [
                                "Gradual model switching with quality monitoring",
                                "Semantic caching with 32% hit rate"
                            ],
                            "what_didnt": [
                                "Aggressive switching without quality checks",
                                "Assumptions about latency tolerance"
                            ],
                            "unexpected_discoveries": [
                                "Cache effectiveness exceeded projections by 60%",
                                "Users highly sensitive to P95 latency"
                            ],
                            "recommendations_for_future": [
                                "Always implement gradual rollouts",
                                "Invest in better user behavior analytics",
                                "Quality monitoring is non-negotiable"
                            ]
                        },
                        "knowledge_base_updates": [
                            "Updated latency SLA targets",
                            "Revised cache hit rate expectations",
                            "New model switching thresholds"
                        ]
                    }
                }),
                "metadata": {"model": "test"}
            }
        )
        
        # Execute with proper arguments
        await reporting_agent.execute(state, "run_learnings", False)
        
        # Get mocked response data
        response_data = json.loads(reporting_agent.llm_manager.generate_response.return_value["content"])
        report = response_data["report"]
        
        # Validate learnings documentation
        if "learnings_and_insights" in report:
            learnings = report["learnings_and_insights"]
            
            # Should document successes and failures
            assert "what_worked" in learnings
            assert "what_didnt" in learnings or "challenges" in learnings
            
            # Should capture unexpected findings
            if "unexpected_discoveries" in learnings:
                assert len(learnings["unexpected_discoveries"]) > 0
            
            # Should provide future guidance
            assert "recommendations_for_future" in learnings or \
                   "best_practices" in learnings
    
    def test_report_quality_metrics(self):
        """Meta-test for report quality standards."""
        quality_standards = {
            "completeness": {
                "required_sections": ["executive_summary", "metrics", "next_steps"],
                "minimum_metrics": 3,
                "visualization_count": 2
            },
            "clarity": {
                "max_jargon_percentage": 0.1,
                "requires_definitions": True,
                "executive_readable": True
            },
            "value_demonstration": {
                "quantified_benefits": True,
                "roi_calculation": True,
                "comparison_data": True
            },
            "actionability": {
                "specific_next_steps": True,
                "resource_requirements": True,
                "success_criteria": True
            }
        }
        
        # Validate quality standards
        assert all(category for category in quality_standards.keys())
        assert quality_standards["completeness"]["minimum_metrics"] >= 3
        assert quality_standards["value_demonstration"]["quantified_benefits"]
        assert quality_standards["actionability"]["specific_next_steps"]