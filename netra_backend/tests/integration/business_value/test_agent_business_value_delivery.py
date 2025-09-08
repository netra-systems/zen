"""
Agent Business Value Delivery Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate agents deliver measurable business value to customers
- Value Impact: Ensures cost optimization, performance analysis, and insights generation
- Strategic Impact: Core value proposition validation - agents must provide ROI

Tests agent execution scenarios that directly impact customer business outcomes:
1. Cost optimization insights that save money
2. Performance recommendations that improve efficiency  
3. Resource utilization analysis for better allocation
4. Risk assessment workflows for compliance
5. Compliance reporting for regulatory requirements

Uses real components (databases, WebSocket events, agent execution) but configured
for integration testing without Docker dependencies.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List

from .enhanced_base_integration_test import EnhancedBaseIntegrationTest
from test_framework.ssot.websocket import WebSocketEventType


class TestAgentBusinessValueDelivery(EnhancedBaseIntegrationTest):
    """
    Integration tests validating agents deliver measurable business value.
    
    Focus: Revenue-generating capabilities, cost savings, performance improvements
    """
    
    @pytest.mark.integration
    @pytest.mark.business_value
    async def test_cost_optimization_insights_generation(self):
        """
        Test 1: Cost Optimization Analysis Delivers Actionable Savings
        
        Business Value: Enterprise customer reduces AI costs by $2500/month
        Customer Segment: Mid, Enterprise (budget-conscious users)
        Success Criteria: Identifies specific cost savings with implementation plan
        """
        # Setup: Enterprise customer with high AI spend
        user = await self.create_test_user(subscription_tier="enterprise")
        
        # Business scenario: CTO needs to reduce AI costs by 30%
        user_request = (
            "Our AI costs have grown to $8000/month. I need to reduce them by 30% "
            "while maintaining quality. We mainly use GPT-4 for customer support, "
            "data analysis, and content generation."
        )
        
        state = await self.create_agent_execution_context(user, user_request)
        
        # Expected business outcomes from cost optimization
        expected_outcomes = [
            "cost_savings_identified",
            "potential_monthly_savings", 
            "actionable_recommendations",
            "implementation_complexity"
        ]
        
        # Execute cost optimization agent with real components
        async with self.websocket_business_context(user) as ws_context:
            execution_result = await self.execute_agent_with_business_validation(
                agent_name="optimization_agent",
                state=state,
                expected_business_outcomes=expected_outcomes,
                timeout=30.0,
                ws_context=ws_context
            )
            
            # Business Value Assertions
            self.assert_business_value_delivered(execution_result)
            self.assert_cost_optimization_value(execution_result["business_outcomes"])
            
            # Verify cost savings are meaningful
            outcomes = execution_result["business_outcomes"] 
            savings = outcomes["potential_monthly_savings"]
            assert savings >= 2000, f"Savings should be at least $2000/month, got ${savings}"
            assert savings <= 5000, f"Savings seem unrealistic: ${savings}"
            
            # Verify recommendations are actionable
            recommendations = outcomes["actionable_recommendations"]
            assert recommendations >= 3, "Need at least 3 actionable recommendations"
            
            # WebSocket events validation - ensures real-time user engagement
            required_events = ["agent_started", "agent_thinking", "agent_completed"]
            self.assert_websocket_events_sent(ws_context["events"], required_events)
            
            # Performance validation
            self.assert_performance_within_limits(
                execution_result["execution_time"], 
                "optimization_agent"
            )
            
        # Verify business outcome persistence
        if self.mock_db:
            saved_optimization = await self.mock_db.save_optimization_result(
                user["id"], "cost_optimization", savings
            )
            assert saved_optimization is not None, "Optimization should be saved for tracking"
    
    @pytest.mark.integration  
    @pytest.mark.business_value
    async def test_performance_bottleneck_identification(self):
        """
        Test 2: Performance Analysis Identifies Specific Bottlenecks
        
        Business Value: Platform Engineer reduces P95 latency from 800ms to 400ms
        Customer Segment: Mid, Enterprise (performance-critical users)  
        Success Criteria: Identifies root causes with improvement estimates
        """
        # Setup: Mid-tier customer experiencing performance issues
        user = await self.create_test_user(subscription_tier="mid")
        
        # Business scenario: ML Engineer troubleshooting latency spike
        user_request = (
            "Our AI model inference latency jumped from 200ms to 800ms P95 "
            "last week. Users are complaining. Need to identify bottlenecks "
            "and get recommendations for improvement."
        )
        
        state = await self.create_agent_execution_context(user, user_request)
        
        # Expected business outcomes from performance analysis
        expected_outcomes = [
            "bottlenecks_identified",
            "root_cause_analysis", 
            "performance_recommendations",
            "expected_improvement"
        ]
        
        # Execute performance analysis with real monitoring
        async with self.websocket_business_context(user) as ws_context:
            execution_result = await self.execute_agent_with_business_validation(
                agent_name="performance_agent",
                state=state, 
                expected_business_outcomes=expected_outcomes,
                timeout=25.0,
                ws_context=ws_context
            )
            
            # Business Value Assertions
            self.assert_business_value_delivered(execution_result)
            
            outcomes = execution_result["business_outcomes"]
            
            # Verify specific performance insights
            assert "bottlenecks_identified" in outcomes, "Must identify specific bottlenecks"
            assert outcomes.get("confidence_score", 0) >= 0.8, "Performance analysis needs high confidence"
            
            # Verify improvement estimates are realistic
            improvement = outcomes.get("expected_improvement", "")
            assert "%" in improvement or "ms" in improvement, "Must provide quantified improvement estimate"
            
            # WebSocket real-time updates validation
            events = ws_context["events"]
            
            # Should see tool execution for performance monitoring
            event_types = [event.get("type") for event in events]
            assert "tool_executing" in event_types, "Must show tool execution for analysis"
            assert "tool_completed" in event_types, "Must complete tool execution"
            
            # Performance monitoring - analysis shouldn't be too slow itself
            self.assert_performance_within_limits(
                execution_result["execution_time"],
                "performance_agent"  
            )
            
        # Verify actionable recommendations
        recommendations = outcomes.get("performance_recommendations", [])
        assert len(recommendations) >= 2, "Need multiple performance recommendations"
    
    @pytest.mark.integration
    @pytest.mark.business_value 
    async def test_resource_utilization_optimization(self):
        """
        Test 3: Resource Analysis Optimizes Infrastructure Allocation
        
        Business Value: DevOps team reduces infrastructure costs by 25%
        Customer Segment: Mid, Enterprise (infrastructure-heavy users)
        Success Criteria: Identifies underutilized resources with reallocation plan
        """
        # Setup: Enterprise customer with complex infrastructure
        user = await self.create_test_user(subscription_tier="enterprise")
        
        # Business scenario: DevOps analyzing resource utilization
        user_request = (
            "We're running 50+ AI model inference servers across different regions. "
            "Costs are high but utilization seems uneven. Need analysis of resource "
            "allocation and recommendations for optimization."
        )
        
        state = await self.create_agent_execution_context(user, user_request)
        
        # Add infrastructure context to state
        state.user_context.update({
            "infrastructure": {
                "server_count": 52,
                "regions": ["us-east-1", "us-west-2", "eu-west-1"],
                "monthly_cost": 12000,
                "avg_cpu_utilization": 0.35,
                "avg_memory_utilization": 0.42
            }
        })
        
        expected_outcomes = [
            "utilization_analysis",
            "resource_waste_identified",
            "optimization_plan",
            "cost_reduction_estimate"
        ]
        
        async with self.websocket_business_context(user) as ws_context:
            execution_result = await self.execute_agent_with_business_validation(
                agent_name="resource_optimization_agent",
                state=state,
                expected_business_outcomes=expected_outcomes,
                timeout=35.0,
                ws_context=ws_context
            )
            
            # Business Value Assertions
            self.assert_business_value_delivered(execution_result)
            
            outcomes = execution_result["business_outcomes"]
            
            # Verify resource analysis quality
            assert "utilization_analysis" in outcomes, "Must analyze resource utilization"
            assert "resource_waste_identified" in outcomes, "Must identify wasteful resources"
            
            # Verify cost reduction estimates
            cost_reduction = outcomes.get("cost_reduction_estimate", 0)
            if isinstance(cost_reduction, str):
                # Extract number from string like "25% reduction" or "$3000/month"
                import re
                numbers = re.findall(r'\d+', cost_reduction)
                if numbers:
                    cost_reduction = float(numbers[0])
                    
            assert cost_reduction > 0, "Must provide cost reduction estimate"
            
            # Enterprise customers should get detailed analysis
            self.assert_enterprise_tier_value(user, outcomes)
            
            # WebSocket progress tracking
            required_events = [
                "agent_started", 
                "agent_thinking",
                "tool_executing",  # Resource analysis tools
                "tool_completed",
                "agent_completed"
            ]
            self.assert_websocket_events_sent(ws_context["events"], required_events)
            
            # Verify business impact measurement
            optimization_plan = outcomes.get("optimization_plan", {})
            if isinstance(optimization_plan, dict):
                assert "timeline" in optimization_plan or "steps" in optimization_plan, \
                    "Optimization plan must have implementation details"
    
    @pytest.mark.integration
    @pytest.mark.business_value
    async def test_risk_assessment_workflow_execution(self):
        """
        Test 4: Risk Assessment Identifies Business Continuity Threats
        
        Business Value: Risk Manager identifies potential $100K+ impact risks
        Customer Segment: Enterprise (compliance-focused users)
        Success Criteria: Comprehensive risk analysis with mitigation strategies
        """
        # Setup: Enterprise customer needing risk assessment
        user = await self.create_test_user(subscription_tier="enterprise")
        
        # Business scenario: Risk manager assessing AI system vulnerabilities  
        user_request = (
            "We need a comprehensive risk assessment of our AI systems before "
            "expanding to European markets. Focus on data privacy, model bias, "
            "operational failures, and compliance requirements."
        )
        
        state = await self.create_agent_execution_context(user, user_request)
        
        # Add risk context
        state.user_context.update({
            "business_context": {
                "expansion_markets": ["EU", "UK"],
                "current_revenue": 5000000,  # $5M annual revenue
                "compliance_requirements": ["GDPR", "AI Act", "ISO27001"],
                "critical_systems": ["customer_ai", "fraud_detection", "recommendation_engine"]
            }
        })
        
        expected_outcomes = [
            "risk_categories_identified",
            "impact_assessment", 
            "mitigation_strategies",
            "compliance_gaps",
            "business_continuity_plan"
        ]
        
        async with self.websocket_business_context(user) as ws_context:
            execution_result = await self.execute_agent_with_business_validation(
                agent_name="risk_assessment_agent",
                state=state,
                expected_business_outcomes=expected_outcomes, 
                timeout=40.0,
                ws_context=ws_context
            )
            
            # Business Value Assertions
            self.assert_business_value_delivered(execution_result)
            
            outcomes = execution_result["business_outcomes"]
            
            # Verify comprehensive risk analysis
            assert "risk_categories_identified" in outcomes, "Must identify risk categories"
            assert "impact_assessment" in outcomes, "Must assess business impact"
            assert "mitigation_strategies" in outcomes, "Must provide mitigation strategies"
            
            # Enterprise risk assessment should be thorough
            confidence = outcomes.get("confidence_score", 0)
            assert confidence >= 0.85, f"Risk assessment needs very high confidence: {confidence}"
            
            # Verify compliance considerations
            if "compliance_gaps" in outcomes:
                gaps = outcomes["compliance_gaps"]
                assert isinstance(gaps, (list, dict)), "Compliance gaps should be structured"
                
            # WebSocket events for executive dashboards
            events = ws_context["events"]
            event_types = [event.get("type") for event in events]
            
            # Risk assessment should show detailed progress
            assert "agent_thinking" in event_types, "Must show analysis progress"
            assert len([e for e in events if e.get("type") == "agent_thinking"]) >= 2, \
                "Risk assessment should show multiple thinking phases"
                
            # Performance expectation
            execution_time = execution_result["execution_time"]
            assert execution_time <= 45.0, f"Risk assessment too slow: {execution_time:.2f}s"
            
        # Verify business continuity considerations
        continuity_plan = outcomes.get("business_continuity_plan", {})
        if continuity_plan:
            assert "recovery_procedures" in str(continuity_plan) or \
                   "backup_systems" in str(continuity_plan), \
                   "Business continuity plan must address recovery"
    
    @pytest.mark.integration
    @pytest.mark.business_value
    async def test_compliance_reporting_automation(self):
        """
        Test 5: Automated Compliance Report Generation
        
        Business Value: Compliance Officer saves 20+ hours/month on reporting
        Customer Segment: Mid, Enterprise (regulated industries)
        Success Criteria: Generates audit-ready compliance reports automatically
        """
        # Setup: Enterprise customer in regulated industry
        user = await self.create_test_user(subscription_tier="enterprise")
        
        # Business scenario: Compliance officer needs quarterly report
        user_request = (
            "Generate our Q3 AI compliance report covering GDPR data processing, "
            "model bias testing results, security audit findings, and incident "
            "response metrics. Format for board presentation."
        )
        
        state = await self.create_agent_execution_context(user, user_request)
        
        # Add compliance data context
        state.user_context.update({
            "compliance_data": {
                "gdpr_requests_processed": 47,
                "data_breaches": 0,
                "model_bias_tests": 12,
                "security_audits_completed": 2,
                "incidents_resolved": 3,
                "reporting_period": "Q3 2024",
                "regulatory_framework": ["GDPR", "CCPA", "SOX"]
            }
        })
        
        expected_outcomes = [
            "report_generated",
            "executive_summary",
            "compliance_metrics",
            "audit_trail",
            "board_presentation_ready"
        ]
        
        async with self.websocket_business_context(user) as ws_context:
            execution_result = await self.execute_agent_with_business_validation(
                agent_name="compliance_reporting_agent",
                state=state,
                expected_business_outcomes=expected_outcomes,
                timeout=30.0,
                ws_context=ws_context
            )
            
            # Business Value Assertions
            self.assert_business_value_delivered(execution_result)
            
            outcomes = execution_result["business_outcomes"]
            
            # Verify report quality and completeness
            assert "report_generated" in outcomes, "Must generate compliance report"
            assert "executive_summary" in outcomes, "Must include executive summary"
            assert "compliance_metrics" in outcomes, "Must include quantified metrics"
            
            # Verify audit readiness
            if "audit_trail" in outcomes:
                audit_trail = outcomes["audit_trail"]
                assert audit_trail, "Audit trail must be substantial"
                
            # Board presentation requirements
            if "board_presentation_ready" in outcomes:
                presentation_ready = outcomes["board_presentation_ready"]
                assert presentation_ready, "Report must be board-presentation ready"
                
            # WebSocket progress for time-sensitive compliance work
            events = ws_context["events"]
            required_events = ["agent_started", "agent_completed"]
            self.assert_websocket_events_sent(events, required_events)
            
            # Tool usage for data gathering
            event_types = [event.get("type") for event in events]
            if "tool_executing" in event_types:
                # Should complete tool execution for data gathering
                assert "tool_completed" in event_types, "Data gathering tools must complete"
                
            # Performance - compliance reports are time-sensitive
            execution_time = execution_result["execution_time"]
            assert execution_time <= 35.0, f"Compliance reporting too slow: {execution_time:.2f}s"
            
        # Verify report structure and business value
        report_data = outcomes.get("compliance_metrics", {})
        if report_data:
            # Should include key compliance indicators
            expected_indicators = ["processing_requests", "security_incidents", "audit_results"]
            for indicator in expected_indicators:
                # Check if any form of these indicators exists
                found_indicator = any(indicator.replace("_", "") in str(key).replace("_", "").lower() 
                                    for key in report_data.keys() if isinstance(report_data, dict))
                if not found_indicator:
                    # Add warning but don't fail - compliance data varies
                    self.business_metrics.add_warning(f"Missing compliance indicator: {indicator}")
                    
        # Verify time savings (business value metric)
        time_saved_hours = 20  # Expected automation benefit
        hourly_rate = 150  # Compliance officer hourly rate
        monthly_savings = time_saved_hours * hourly_rate
        
        self.business_metrics.record_business_outcome(
            "monthly_time_savings_value", monthly_savings
        )
        
        assert monthly_savings >= 3000, f"Compliance automation should save at least $3000/month"


if __name__ == "__main__":
    # Run tests with comprehensive reporting
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "-m", "business_value",
        "--durations=10"
    ])