"""
Unit Tests for Agent State Management Business Logic - Comprehensive Coverage

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Data Integrity - Ensure business data is properly validated and structured
- Value Impact: State management ensures agent results are consistently formatted for business consumption
- Strategic Impact: Reliable data validation prevents business logic errors and enables automation

This test suite validates the business-critical path of agent state management including:
- Business result validation for cost savings and performance improvements
- Data structure consistency for business reporting and dashboards  
- Field parsing and conversion for robust business data handling
- Metadata preservation for business audit trails and traceability
- Typed models that prevent business logic errors
- Validation rules that protect business data integrity

CRITICAL: These tests focus on BUSINESS LOGIC that ensures AI agents produce
reliable, validated business data that can be safely consumed by business systems.
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import Mock

from netra_backend.app.agents.state import (
    OptimizationsResult,
    ActionPlanResult, 
    ReportResult,
    ReportSection,
    PlanStep,
    SyntheticDataResult
)
from netra_backend.app.schemas.agent_models import AgentMetadata
from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestMetrics
from test_framework.unified import TestCategory
from shared.isolated_environment import get_env


class TestAgentStateManagementBusiness(SSotBaseTestCase):
    """Comprehensive unit tests for agent state management business logic."""

    def setup_method(self, method):
        """Set up test environment with isolated configuration."""
        super().setup_method(method)
        self.env = get_env()
        self.env.set("LOG_LEVEL", "INFO", source="test")
        
        self.test_context = self.get_test_context()
        
        self.metrics = SsotTestMetrics()
        self.metrics.start_timing()

    def teardown_method(self, method):
        """Clean up after each test."""
        self.metrics.end_timing()
        super().teardown_method(method)

    @pytest.fixture
    def business_metadata(self):
        """Create realistic business metadata."""
        return AgentMetadata(
            agent_name="cost_optimization_agent",
            version="2.1.0",
            execution_id="cost-optimization-12345",
            created_at=datetime.now(timezone.utc),
            business_context={
                "department": "finance",
                "cost_center": "operations", 
                "budget_cycle": "FY2024-Q4",
                "stakeholders": ["CFO", "Operations_Director"]
            }
        )

    def test_optimizations_result_validates_business_cost_savings(self, business_metadata):
        """Test that OptimizationsResult validates business cost savings correctly."""
        # BUSINESS VALUE: Cost savings validation prevents unrealistic business projections
        
        # Test valid business cost savings
        valid_optimization = OptimizationsResult(
            optimization_type="aws_cost_optimization",
            recommendations=[
                "Rightsize EC2 instances to reduce overprovisioning",
                "Implement Reserved Instances for steady workloads",
                "Enable S3 lifecycle policies for old data"
            ],
            cost_savings=25000.0,  # $25k monthly savings - realistic
            performance_improvement=15.5,  # 15.5% improvement
            confidence_score=0.87,
            metadata=business_metadata
        )
        
        # Verify business validation passes
        assert valid_optimization.cost_savings == 25000.0
        assert valid_optimization.performance_improvement == 15.5
        assert valid_optimization.confidence_score == 0.87
        assert len(valid_optimization.recommendations) == 3
        
        # Test cost savings validation boundaries
        with pytest.raises(ValueError, match="Cost savings cannot be negative"):
            OptimizationsResult(
                optimization_type="invalid_optimization",
                cost_savings=-1000.0  # Negative savings - business error
            )
        
        with pytest.raises(ValueError, match="Cost savings exceeds reasonable limit"):
            OptimizationsResult(
                optimization_type="unrealistic_optimization", 
                cost_savings=2000000.0  # $2M - exceeds $1M limit
            )
        
        # Record business validation metrics
        self.metrics.record_custom("cost_savings_validation_working", True)
        self.metrics.record_custom("business_projections_protected", True)

    def test_optimizations_result_validates_performance_improvements(self):
        """Test that OptimizationsResult validates performance improvements correctly."""
        # BUSINESS VALUE: Performance validation prevents unrealistic business expectations
        
        # Test valid performance improvement
        valid_performance = OptimizationsResult(
            optimization_type="database_optimization",
            performance_improvement=45.0,  # 45% improvement - realistic
            confidence_score=0.92
        )
        
        assert valid_performance.performance_improvement == 45.0
        
        # Test performance improvement boundaries
        with pytest.raises(ValueError, match="Performance improvement cannot be less than -100%"):
            OptimizationsResult(
                optimization_type="degrading_optimization",
                performance_improvement=-150.0  # Impossible degradation
            )
        
        with pytest.raises(ValueError, match="Performance improvement exceeds reasonable limit"):
            OptimizationsResult(
                optimization_type="unrealistic_optimization",
                performance_improvement=50000.0  # 500x improvement - unrealistic
            )
        
        # Test maximum realistic improvement
        realistic_max = OptimizationsResult(
            optimization_type="high_impact_optimization",
            performance_improvement=500.0  # 5x improvement - high but possible
        )
        assert realistic_max.performance_improvement == 500.0
        
        # Record performance validation metrics
        self.metrics.record_custom("performance_validation_working", True)
        self.metrics.record_custom("realistic_expectations_enforced", True)

    def test_optimizations_result_parses_complex_business_recommendations(self):
        """Test that OptimizationsResult properly parses complex business recommendations."""
        # BUSINESS VALUE: Robust parsing ensures business recommendations are preserved correctly
        
        # Test with mixed data types (common in real agent outputs)
        complex_recommendations = [
            "Implement automated scaling for compute resources",
            {"recommendation": "Optimize data pipeline efficiency", "priority": "high"},
            "Consolidate redundant software licenses",
            {"action": "Renegotiate vendor contracts", "savings_estimate": 15000}
        ]
        
        optimization = OptimizationsResult(
            optimization_type="comprehensive_optimization",
            recommendations=complex_recommendations,
            cost_savings=45000.0
        )
        
        # Verify all recommendations are parsed to strings for business consumption
        parsed_recommendations = optimization.recommendations
        assert len(parsed_recommendations) == 4
        assert all(isinstance(rec, str) for rec in parsed_recommendations)
        
        # Verify business content is preserved in string form
        assert "automated scaling" in parsed_recommendations[0]
        assert "data pipeline" in parsed_recommendations[1] 
        assert "software licenses" in parsed_recommendations[2]
        assert "vendor contracts" in parsed_recommendations[3]
        
        # Record parsing metrics
        self.metrics.record_custom("complex_recommendations_parsed", 4)
        self.metrics.record_custom("business_content_preserved", True)

    def test_action_plan_result_structures_business_execution_plan(self, business_metadata):
        """Test that ActionPlanResult properly structures business execution plans."""
        # BUSINESS VALUE: Structured action plans enable business stakeholders to track implementation
        
        # Create comprehensive business action plan
        business_action_plan = ActionPlanResult(
            action_plan_summary="Comprehensive cost optimization implementation plan",
            total_estimated_time="8 weeks",
            required_approvals=["CFO", "IT_Director", "Procurement_Manager"],
            actions=[
                {
                    "action_id": "ACT-001",
                    "description": "Audit current cloud resource utilization",
                    "timeline": "Week 1-2",
                    "resources": ["Cloud_Engineer", "Data_Analyst"],
                    "cost": 15000
                },
                {
                    "action_id": "ACT-002", 
                    "description": "Implement rightsizing recommendations",
                    "timeline": "Week 3-5",
                    "resources": ["Cloud_Engineer", "DevOps_Team"],
                    "cost": 25000
                }
            ],
            execution_timeline=[
                {"phase": "Assessment", "duration": "2 weeks", "deliverables": ["Audit Report"]},
                {"phase": "Implementation", "duration": "4 weeks", "deliverables": ["Optimized Infrastructure"]},
                {"phase": "Validation", "duration": "2 weeks", "deliverables": ["Performance Report"]}
            ],
            cost_benefit_analysis={
                "total_investment": 65000,
                "annual_savings": 300000, 
                "payback_period_months": 2.6,
                "roi_percentage": 361.5
            },
            plan_steps=[
                PlanStep(
                    step_id="STEP-001",
                    description="Establish baseline performance metrics",
                    estimated_duration="3 days",
                    dependencies=[],
                    resources_needed=["Performance_Monitor", "Analytics_Access"]
                )
            ],
            priority="high",
            required_resources=["cloud_access", "budget_approval", "team_allocation"],
            success_metrics=["cost_reduction_achieved", "performance_maintained", "stakeholder_satisfaction"],
            metadata=business_metadata
        )
        
        # Verify business plan structure
        assert business_action_plan.action_plan_summary.startswith("Comprehensive")
        assert business_action_plan.total_estimated_time == "8 weeks"
        assert len(business_action_plan.required_approvals) == 3
        assert len(business_action_plan.actions) == 2
        assert len(business_action_plan.execution_timeline) == 3
        
        # Verify business cost-benefit analysis
        cba = business_action_plan.cost_benefit_analysis
        assert cba["total_investment"] == 65000
        assert cba["annual_savings"] == 300000
        assert cba["roi_percentage"] == 361.5
        
        # Verify business success metrics
        assert len(business_action_plan.success_metrics) == 3
        assert "cost_reduction_achieved" in business_action_plan.success_metrics
        
        # Record business planning metrics
        self.metrics.record_custom("business_action_plans_structured", True)
        self.metrics.record_custom("stakeholder_execution_enabled", True)

    def test_action_plan_result_parses_business_resources_and_metrics(self):
        """Test that ActionPlanResult properly parses business resources and metrics."""
        # BUSINESS VALUE: Robust parsing ensures business resource requirements are captured
        
        # Test with complex resource and metrics data
        complex_resources = [
            "cloud_infrastructure_access",
            {"resource_type": "human", "role": "senior_cloud_engineer", "hours": 160},
            "budget_allocation_50k",
            {"resource_type": "tool", "name": "cost_optimization_platform", "license_cost": 5000}
        ]
        
        complex_metrics = [
            "monthly_cost_reduction_target_15_percent",
            {"metric": "system_uptime", "target": 99.9, "measurement": "percentage"},
            "stakeholder_satisfaction_score",
            {"metric": "implementation_timeline_adherence", "target": 95, "unit": "percent"}
        ]
        
        action_plan = ActionPlanResult(
            action_plan_summary="Resource and metrics parsing test",
            required_resources=complex_resources,
            success_metrics=complex_metrics
        )
        
        # Verify resources are parsed for business consumption
        parsed_resources = action_plan.required_resources
        assert len(parsed_resources) == 4
        assert all(isinstance(res, str) for res in parsed_resources)
        assert "cloud_infrastructure_access" in parsed_resources[0]
        assert "senior_cloud_engineer" in parsed_resources[1]
        
        # Verify metrics are parsed for business tracking
        parsed_metrics = action_plan.success_metrics
        assert len(parsed_metrics) == 4
        assert all(isinstance(metric, str) for metric in parsed_metrics)
        assert "cost_reduction_target" in parsed_metrics[0]
        assert "stakeholder_satisfaction" in parsed_metrics[2]
        
        # Record parsing metrics
        self.metrics.record_custom("business_resources_parsed", 4)
        self.metrics.record_custom("success_metrics_structured", 4)

    def test_report_result_structures_business_reports(self, business_metadata):
        """Test that ReportResult properly structures business reports."""
        # BUSINESS VALUE: Structured reports enable business stakeholders to consume analysis results
        
        # Create comprehensive business report
        business_report = ReportResult(
            report_type="quarterly_cost_optimization_analysis",
            content="Executive Summary: This report analyzes Q4 2024 cost optimization opportunities...",
            sections=[
                ReportSection(
                    section_id="executive_summary",
                    title="Executive Summary",
                    content="Key findings: 23% cost reduction opportunity identified across cloud infrastructure...",
                    section_type="summary",
                    metadata=business_metadata
                ),
                ReportSection(
                    section_id="detailed_analysis", 
                    title="Detailed Cost Analysis",
                    content="Deep dive into cost drivers: EC2 instances account for 67% of monthly spend...",
                    section_type="analysis"
                ),
                ReportSection(
                    section_id="recommendations",
                    title="Implementation Recommendations", 
                    content="Priority actions: 1) Rightsize oversized instances, 2) Implement auto-scaling...",
                    section_type="recommendations"
                )
            ],
            attachments=["cost_analysis_dashboard.pdf", "implementation_timeline.xlsx"],
            metadata=business_metadata
        )
        
        # Verify business report structure
        assert business_report.report_type == "quarterly_cost_optimization_analysis"
        assert "Executive Summary" in business_report.content
        assert len(business_report.sections) == 3
        assert len(business_report.attachments) == 2
        
        # Verify business sections are properly structured
        exec_summary = business_report.sections[0]
        assert exec_summary.section_id == "executive_summary"
        assert exec_summary.title == "Executive Summary"
        assert "23% cost reduction" in exec_summary.content
        
        recommendations = business_report.sections[2]
        assert recommendations.section_type == "recommendations"
        assert "Priority actions" in recommendations.content
        
        # Verify timestamp for business audit trail
        assert isinstance(business_report.generated_at, datetime)
        assert business_report.generated_at.tzinfo is not None
        
        # Record business reporting metrics
        self.metrics.record_custom("business_reports_structured", True)
        self.metrics.record_custom("stakeholder_consumption_enabled", True)

    def test_report_result_parses_business_attachments(self):
        """Test that ReportResult properly parses business attachments."""
        # BUSINESS VALUE: Attachment parsing ensures business documents are properly referenced
        
        # Test with complex attachment data
        complex_attachments = [
            "executive_summary.pdf",
            {"file_name": "detailed_analysis.xlsx", "size_mb": 2.5, "type": "spreadsheet"},
            "cost_trends_chart.png",
            {"file_name": "implementation_plan.docx", "access_level": "confidential"}
        ]
        
        report = ReportResult(
            report_type="business_attachment_test",
            content="Test report with complex attachments",
            attachments=complex_attachments
        )
        
        # Verify attachments are parsed for business use
        parsed_attachments = report.attachments
        assert len(parsed_attachments) == 4
        assert all(isinstance(att, str) for att in parsed_attachments)
        
        # Verify business file references are preserved
        assert "executive_summary.pdf" in parsed_attachments[0]
        assert "detailed_analysis.xlsx" in parsed_attachments[1]
        assert "cost_trends_chart.png" in parsed_attachments[2]
        assert "implementation_plan.docx" in parsed_attachments[3]
        
        # Record attachment processing metrics
        self.metrics.record_custom("business_attachments_parsed", 4)
        self.metrics.record_custom("document_references_preserved", True)

    def test_synthetic_data_result_validates_business_data_quality(self):
        """Test that SyntheticDataResult validates business data quality parameters."""
        # BUSINESS VALUE: Data quality validation ensures synthetic data meets business standards
        
        # Test valid business synthetic data
        valid_synthetic_data = SyntheticDataResult(
            data_type="customer_transaction_data",
            generation_method="statistical_sampling",
            sample_count=50000,
            quality_score=0.91,  # High quality for business use
            file_path="/business_data/synthetic_transactions_2024.csv"
        )
        
        # Verify business data parameters
        assert valid_synthetic_data.data_type == "customer_transaction_data"
        assert valid_synthetic_data.sample_count == 50000
        assert valid_synthetic_data.quality_score == 0.91
        assert valid_synthetic_data.file_path.endswith(".csv")
        
        # Test quality score validation boundaries
        with pytest.raises(ValueError):
            SyntheticDataResult(
                data_type="invalid_quality_data",
                generation_method="test",
                quality_score=1.5  # Above 1.0 limit
            )
        
        with pytest.raises(ValueError):
            SyntheticDataResult(
                data_type="invalid_quality_data",
                generation_method="test", 
                quality_score=-0.1  # Below 0.0 limit
            )
        
        # Test business-appropriate quality thresholds
        high_quality_data = SyntheticDataResult(
            data_type="financial_projections",
            generation_method="monte_carlo_simulation",
            quality_score=0.95  # Very high quality for financial data
        )
        assert high_quality_data.quality_score >= 0.9  # Business standard
        
        # Record data quality metrics
        self.metrics.record_custom("synthetic_data_quality_validated", True)
        self.metrics.record_custom("business_data_standards_enforced", True)

    def test_plan_step_structures_business_workflow_steps(self):
        """Test that PlanStep properly structures business workflow steps."""
        # BUSINESS VALUE: Structured workflow steps enable business process tracking
        
        # Create comprehensive business workflow step
        business_step = PlanStep(
            step_id="COST-OPT-001",
            description="Conduct comprehensive cloud resource audit across all business units",
            estimated_duration="5 business days",
            dependencies=["budget_approval", "team_allocation"],
            resources_needed=[
                "cloud_infrastructure_access",
                "senior_cloud_engineer",
                "cost_analysis_tools",
                "business_unit_liaisons"
            ],
            status="in_progress"
        )
        
        # Verify business step structure
        assert business_step.step_id == "COST-OPT-001"
        assert "comprehensive cloud resource audit" in business_step.description
        assert business_step.estimated_duration == "5 business days"
        assert len(business_step.dependencies) == 2
        assert len(business_step.resources_needed) == 4
        assert business_step.status == "in_progress"
        
        # Verify business dependencies are tracked
        assert "budget_approval" in business_step.dependencies
        assert "team_allocation" in business_step.dependencies
        
        # Verify business resources are specified
        assert "senior_cloud_engineer" in business_step.resources_needed
        assert "business_unit_liaisons" in business_step.resources_needed
        
        # Record workflow metrics
        self.metrics.record_custom("business_workflow_steps_structured", True)
        self.metrics.record_custom("process_tracking_enabled", True)

    def test_business_metadata_preservation_across_models(self, business_metadata):
        """Test that business metadata is preserved across all state models."""
        # BUSINESS VALUE: Metadata preservation enables business audit trails and traceability
        
        # Test metadata preservation in OptimizationsResult
        optimization = OptimizationsResult(
            optimization_type="business_process_optimization",
            cost_savings=12000.0,
            metadata=business_metadata
        )
        
        # Test metadata preservation in ActionPlanResult  
        action_plan = ActionPlanResult(
            action_plan_summary="Business process improvement plan",
            metadata=business_metadata
        )
        
        # Test metadata preservation in ReportResult
        report = ReportResult(
            report_type="business_analysis_report",
            content="Business analysis content",
            metadata=business_metadata
        )
        
        # Verify business metadata is preserved across all models
        for model in [optimization, action_plan, report]:
            assert model.metadata.agent_name == "cost_optimization_agent"
            assert model.metadata.version == "2.1.0"
            assert model.metadata.execution_id == "cost-optimization-12345"
            assert "department" in model.metadata.business_context
            assert model.metadata.business_context["department"] == "finance"
            assert "stakeholders" in model.metadata.business_context
        
        # Record metadata preservation metrics
        self.metrics.record_custom("business_metadata_preserved", 3)
        self.metrics.record_custom("audit_trail_enabled", True)


class TestAgentStateManagementBusinessScenarios(SSotBaseTestCase):
    """Business scenario tests for agent state management edge cases."""

    def test_enterprise_scale_optimization_result_validation(self):
        """Test optimization result validation at enterprise scale."""
        # BUSINESS VALUE: Enterprise customers need validation for large-scale optimizations
        
        # Test large-scale enterprise optimization
        enterprise_optimization = OptimizationsResult(
            optimization_type="enterprise_wide_cloud_optimization",
            recommendations=[
                f"Optimize cost center {i}: Implement automated scaling and rightsizing"
                for i in range(50)  # 50 cost centers
            ],
            cost_savings=750000.0,  # $750k monthly - large but realistic for enterprise
            performance_improvement=180.0,  # 180% improvement - high but possible at scale
            confidence_score=0.89
        )
        
        # Verify enterprise-scale validation passes
        assert len(enterprise_optimization.recommendations) == 50
        assert enterprise_optimization.cost_savings == 750000.0
        assert enterprise_optimization.performance_improvement == 180.0
        
        # Record enterprise scale metrics
        metrics = SsotTestMetrics()
        metrics.record_custom("enterprise_scale_optimizations_validated", True)
        metrics.record_custom("large_scale_business_validation", 50)

    def test_multi_department_action_plan_complexity(self):
        """Test action plan handling for multi-department business initiatives."""
        # BUSINESS VALUE: Complex action plans enable coordination across business units
        
        # Create multi-department action plan
        departments = ["finance", "operations", "it", "procurement", "legal"]
        multi_dept_plan = ActionPlanResult(
            action_plan_summary="Multi-department cost optimization initiative",
            required_approvals=[f"{dept}_director" for dept in departments],
            actions=[
                {
                    "department": dept,
                    "action": f"Implement {dept}-specific optimization measures",
                    "timeline": f"Month {i+1}",
                    "budget": 50000 + (i * 10000)
                }
                for i, dept in enumerate(departments)
            ],
            required_resources=[
                f"{dept}_team_allocation" for dept in departments
            ] + [
                "cross_department_coordination",
                "executive_sponsorship", 
                "change_management_support"
            ],
            success_metrics=[
                f"{dept}_cost_reduction_achieved" for dept in departments
            ] + [
                "overall_efficiency_improvement",
                "stakeholder_satisfaction_maintained"
            ]
        )
        
        # Verify multi-department complexity is handled
        assert len(multi_dept_plan.required_approvals) == 5
        assert len(multi_dept_plan.actions) == 5
        assert len(multi_dept_plan.required_resources) == 8  # 5 departments + 3 coordination
        assert len(multi_dept_plan.success_metrics) == 7   # 5 departments + 2 overall
        
        # Record multi-department metrics
        metrics = SsotTestMetrics()
        metrics.record_custom("multi_department_plans_handled", 5)
        metrics.record_custom("business_coordination_enabled", True)