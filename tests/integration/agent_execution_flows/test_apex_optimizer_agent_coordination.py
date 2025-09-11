"""
Test APEX Optimizer Agent Coordination Integration

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (Primary value delivery for paid tiers)
- Business Goal: Ensure APEX optimizer delivers high-value cost optimization insights
- Value Impact: Core value proposition - AI-powered cost optimization that saves customers money
- Strategic Impact: Differentiation feature that justifies premium pricing and drives customer retention

Tests the APEX optimizer agent's coordination with other agents including
data analysis, optimization recommendations, and integration with reporting agents.
"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)


class TestApexOptimizerAgentCoordination(BaseIntegrationTest):
    """Integration tests for APEX optimizer agent coordination."""

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_apex_optimizer_data_analysis_coordination(self, real_services_fixture):
        """Test APEX optimizer coordination with data analysis for cost optimization."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="enterprise_user_700",
            thread_id="thread_1000", 
            session_id="session_1300",
            workspace_id="enterprise_workspace_600"
        )
        
        # Mock data from previous data helper agent
        input_data = {
            "aws_costs": {
                "total_monthly": 15000,
                "services": {
                    "ec2": {"cost": 8000, "instances": 50, "avg_utilization": 35},
                    "rds": {"cost": 3000, "instances": 10, "avg_utilization": 65},
                    "s3": {"cost": 2000, "storage_tb": 100, "access_frequency": "low"},
                    "lambda": {"cost": 2000, "invocations": 1000000, "avg_duration": 500}
                }
            },
            "performance_metrics": {
                "cpu_utilization": 35,
                "memory_utilization": 60,
                "network_utilization": 20
            }
        }
        
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(return_value={
            "status": "success",
            "optimization_analysis": {
                "identified_waste": {
                    "underutilized_ec2": {"savings": 4800, "confidence": 0.9},
                    "oversized_rds": {"savings": 900, "confidence": 0.8},
                    "infrequent_access_s3": {"savings": 600, "confidence": 0.95},
                    "lambda_optimization": {"savings": 400, "confidence": 0.85}
                },
                "total_potential_savings": 6700,
                "roi_timeline": "3 months",
                "implementation_complexity": "medium"
            },
            "recommendations": [
                {
                    "type": "right_sizing",
                    "service": "ec2", 
                    "action": "downsize_underutilized_instances",
                    "impact": "high",
                    "savings": 4800
                },
                {
                    "type": "storage_optimization",
                    "service": "s3",
                    "action": "move_to_infrequent_access",
                    "impact": "medium", 
                    "savings": 600
                }
            ]
        })
        
        apex_optimizer = OptimizationsCoreSubAgent(
            user_context=user_context,
            llm_client=mock_llm
        )
        
        # Act - Execute optimization analysis
        result = await apex_optimizer.execute_cost_optimization_analysis(
            input_data=input_data,
            optimization_focus="cost_reduction",
            analysis_depth="comprehensive"
        )
        
        # Assert - Verify optimization coordination
        assert result is not None
        assert result.status == "success"
        
        optimization_analysis = result.result["optimization_analysis"]
        assert optimization_analysis["total_potential_savings"] > 6000
        assert len(result.result["recommendations"]) >= 2
        
        # Verify business value calculations
        total_savings = optimization_analysis["total_potential_savings"]
        monthly_cost = input_data["aws_costs"]["total_monthly"]
        savings_percentage = (total_savings / monthly_cost) * 100
        assert savings_percentage > 40  # Should identify significant savings

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_apex_optimizer_reporting_agent_coordination(self, real_services_fixture):
        """Test APEX optimizer coordination with reporting agent for executive summaries."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="enterprise_user_701",
            thread_id="thread_1001",
            session_id="session_1301", 
            workspace_id="enterprise_workspace_601"
        )
        
        # Mock optimization results to pass to reporting agent
        optimization_results = {
            "total_savings_identified": 12500,
            "implementation_timeline": "2-4 months",
            "priority_recommendations": [
                {"type": "ec2_rightsizing", "savings": 6000, "effort": "low"},
                {"type": "reserved_instances", "savings": 4000, "effort": "medium"}, 
                {"type": "storage_optimization", "savings": 2500, "effort": "high"}
            ],
            "risk_assessment": {"low": 2, "medium": 1, "high": 0},
            "confidence_score": 0.88
        }
        
        mock_reporting_agent = AsyncMock()
        mock_reporting_agent.generate_executive_summary = AsyncMock(return_value={
            "executive_summary": {
                "key_findings": [
                    "Identified $12,500 monthly cost savings opportunity (42% reduction)",
                    "Low-risk implementation possible within 2 months",
                    "EC2 rightsizing provides highest impact with minimal effort"
                ],
                "recommended_actions": [
                    "Implement EC2 rightsizing immediately for $6,000 monthly savings",
                    "Plan reserved instance strategy for additional $4,000 savings"
                ],
                "roi_projection": {
                    "monthly_savings": 12500,
                    "annual_impact": 150000,
                    "payback_period": "immediate"
                }
            }
        })
        
        mock_llm = AsyncMock() 
        mock_llm.generate_response = AsyncMock(return_value={
            "status": "success",
            "handoff_to_reporting": {
                "data_prepared": True,
                "summary_requested": True,
                "format": "executive_summary",
                "audience": "c_level"
            }
        })
        
        apex_optimizer = OptimizationsCoreSubAgent(
            user_context=user_context,
            llm_client=mock_llm,
            reporting_coordinator=mock_reporting_agent
        )
        
        # Act - Execute optimization and coordinate with reporting
        result = await apex_optimizer.execute_with_reporting_coordination(
            optimization_results=optimization_results,
            report_type="executive_summary",
            target_audience="executive"
        )
        
        # Assert - Verify reporting coordination
        assert result is not None
        assert result.status == "success"
        
        # Verify reporting agent was coordinated
        mock_reporting_agent.generate_executive_summary.assert_called()
        
        # Verify handoff preparation
        handoff = result.result["handoff_to_reporting"]
        assert handoff["data_prepared"] is True
        assert handoff["format"] == "executive_summary"

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_apex_optimizer_validation_coordination(self, real_services_fixture):
        """Test APEX optimizer coordination with validation agents for recommendation verification."""
        # Arrange  
        user_context = UserExecutionContext(
            user_id="enterprise_user_702",
            thread_id="thread_1002",
            session_id="session_1302",
            workspace_id="enterprise_workspace_602"
        )
        
        # Mock validation agent for recommendation verification
        mock_validator = AsyncMock()
        mock_validator.validate_recommendations = AsyncMock(return_value={
            "validation_results": [
                {
                    "recommendation_id": "rec_001",
                    "validation_status": "approved",
                    "risk_level": "low",
                    "feasibility_score": 0.95,
                    "estimated_impact_accuracy": 0.92
                },
                {
                    "recommendation_id": "rec_002", 
                    "validation_status": "approved_with_conditions",
                    "risk_level": "medium",
                    "conditions": ["require_staging_test"],
                    "feasibility_score": 0.78,
                    "estimated_impact_accuracy": 0.85
                }
            ],
            "overall_confidence": 0.89,
            "validation_passed": True
        })
        
        optimization_recommendations = [
            {
                "id": "rec_001",
                "type": "instance_rightsizing",
                "current_cost": 8000,
                "optimized_cost": 5000,
                "savings": 3000,
                "implementation": "immediate"
            },
            {
                "id": "rec_002",
                "type": "storage_tiering", 
                "current_cost": 2000,
                "optimized_cost": 1200,
                "savings": 800,
                "implementation": "requires_planning"
            }
        ]
        
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(return_value={
            "status": "success",
            "validated_recommendations": optimization_recommendations,
            "validation_coordination": {
                "validator_consulted": True,
                "recommendations_verified": True,
                "confidence_enhanced": True
            }
        })
        
        apex_optimizer = OptimizationsCoreSubAgent(
            user_context=user_context,
            llm_client=mock_llm,
            validation_coordinator=mock_validator
        )
        
        # Act - Execute optimization with validation coordination
        result = await apex_optimizer.execute_with_validation(
            recommendations=optimization_recommendations,
            validation_required=True,
            confidence_threshold=0.8
        )
        
        # Assert - Verify validation coordination
        assert result is not None
        assert result.status == "success"
        
        # Verify validator was consulted
        mock_validator.validate_recommendations.assert_called()
        
        # Verify coordination results
        validation_coord = result.result["validation_coordination"]
        assert validation_coord["validator_consulted"] is True
        assert validation_coord["recommendations_verified"] is True

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_apex_optimizer_iterative_refinement_coordination(self, real_services_future):
        """Test APEX optimizer coordination for iterative refinement of recommendations."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="enterprise_user_703", 
            thread_id="thread_1003",
            session_id="session_1303",
            workspace_id="enterprise_workspace_603"
        )
        
        # Mock feedback coordinator for iterative improvement
        mock_feedback_coordinator = AsyncMock()
        
        # First iteration feedback
        mock_feedback_coordinator.get_implementation_feedback = AsyncMock(return_value={
            "feedback_data": {
                "rec_001": {"actual_savings": 2800, "expected_savings": 3000, "accuracy": 0.93},
                "rec_002": {"implementation_blocked": True, "reason": "compliance_requirements"}
            },
            "refinement_suggestions": [
                "Adjust savings estimates by 5-10% for conservative projections",
                "Add compliance pre-check for storage recommendations"
            ]
        })
        
        mock_llm = AsyncMock()
        iteration_count = 0
        
        async def iterative_response(*args, **kwargs):
            nonlocal iteration_count
            iteration_count += 1
            
            if iteration_count == 1:
                # Initial recommendations
                return {
                    "status": "success",
                    "iteration": 1,
                    "recommendations": [
                        {"id": "rec_001", "savings": 3000, "confidence": 0.85},
                        {"id": "rec_002", "savings": 800, "confidence": 0.80}
                    ]
                }
            else:
                # Refined recommendations
                return {
                    "status": "success",
                    "iteration": 2,
                    "refined_recommendations": [
                        {"id": "rec_001", "savings": 2750, "confidence": 0.93, "refined": True},
                        {"id": "rec_003", "savings": 600, "confidence": 0.88, "compliance_verified": True}
                    ],
                    "refinement_applied": True
                }
        
        mock_llm.generate_response = iterative_response
        
        apex_optimizer = OptimizationsCoreSubAgent(
            user_context=user_context,
            llm_client=mock_llm,
            feedback_coordinator=mock_feedback_coordinator
        )
        
        # Act - Execute iterative refinement
        result = await apex_optimizer.execute_iterative_optimization(
            initial_request="Optimize cloud costs with high accuracy",
            max_iterations=2,
            refinement_enabled=True
        )
        
        # Assert - Verify iterative coordination
        assert result is not None
        assert result.status == "success"
        assert result.result.get("refinement_applied") is True
        
        # Verify feedback coordinator was used
        mock_feedback_coordinator.get_implementation_feedback.assert_called()
        
        # Verify refinement improved accuracy
        refined_recs = result.result.get("refined_recommendations", [])
        assert any(rec.get("confidence", 0) > 0.9 for rec in refined_recs)

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_apex_optimizer_cross_platform_coordination(self, real_services_fixture):
        """Test APEX optimizer coordination across multiple cloud platforms."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="enterprise_user_704",
            thread_id="thread_1004",
            session_id="session_1304",
            workspace_id="enterprise_workspace_604"
        )
        
        # Mock platform-specific coordinators
        mock_aws_coordinator = AsyncMock()
        mock_azure_coordinator = AsyncMock()
        mock_gcp_coordinator = AsyncMock()
        
        mock_aws_coordinator.analyze_aws_costs = AsyncMock(return_value={
            "aws_analysis": {"total_savings": 8000, "top_opportunity": "ec2_rightsizing"}
        })
        
        mock_azure_coordinator.analyze_azure_costs = AsyncMock(return_value={
            "azure_analysis": {"total_savings": 5000, "top_opportunity": "vm_scaling"}
        })
        
        mock_gcp_coordinator.analyze_gcp_costs = AsyncMock(return_value={
            "gcp_analysis": {"total_savings": 3000, "top_opportunity": "compute_optimization"}
        })
        
        multi_cloud_data = {
            "aws": {"monthly_cost": 20000, "services": ["ec2", "rds", "s3"]},
            "azure": {"monthly_cost": 15000, "services": ["vm", "sql", "storage"]},
            "gcp": {"monthly_cost": 10000, "services": ["compute", "cloud_sql", "storage"]}
        }
        
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(return_value={
            "status": "success",
            "cross_platform_optimization": {
                "total_cross_platform_savings": 16000,
                "platform_breakdown": {
                    "aws": 8000,
                    "azure": 5000, 
                    "gcp": 3000
                },
                "cross_platform_opportunities": [
                    {"type": "workload_migration", "savings": 2000, "complexity": "high"},
                    {"type": "unified_monitoring", "savings": 500, "complexity": "medium"}
                ],
                "coordination_successful": True
            }
        })
        
        apex_optimizer = OptimizationsCoreSubAgent(
            user_context=user_context,
            llm_client=mock_llm,
            aws_coordinator=mock_aws_coordinator,
            azure_coordinator=mock_azure_coordinator,
            gcp_coordinator=mock_gcp_coordinator
        )
        
        # Act - Execute cross-platform optimization
        result = await apex_optimizer.execute_cross_platform_optimization(
            multi_cloud_data=multi_cloud_data,
            platforms=["aws", "azure", "gcp"],
            cross_platform_analysis=True
        )
        
        # Assert - Verify cross-platform coordination
        assert result is not None
        assert result.status == "success"
        
        cross_platform = result.result["cross_platform_optimization"]
        assert cross_platform["coordination_successful"] is True
        assert cross_platform["total_cross_platform_savings"] > 15000
        
        # Verify all platform coordinators were used
        mock_aws_coordinator.analyze_aws_costs.assert_called()
        mock_azure_coordinator.analyze_azure_costs.assert_called() 
        mock_gcp_coordinator.analyze_gcp_costs.assert_called()
        
        # Verify cross-platform opportunities identified
        assert len(cross_platform["cross_platform_opportunities"]) > 0