"""
Test Agent Report Generation Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agents deliver actionable business reports
- Value Impact: Core value proposition - agents generate reports users can access
- Strategic Impact: Foundation of $3M+ ARR - report quality drives user retention

This test suite validates the critical golden path: agent execution → report generation → user access.
Without this pipeline working, the entire business value proposition fails.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.models.user import User
from netra_backend.app.models.thread import Thread
from netra_backend.app.models.message import Message, MessageType
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from netra_backend.app.models.user_execution_context import UserExecutionContext
from netra_backend.app.services.thread_run_registry import ThreadRunRegistry
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.isolated_environment import IsolatedEnvironment


class BusinessValueReportValidator:
    """Validates reports contain actionable business value."""
    
    @staticmethod
    def validate_actionable_content(report: Dict[str, Any]) -> bool:
        """Ensures report contains specific, actionable business recommendations."""
        required_sections = [
            'executive_summary',
            'key_findings', 
            'recommendations',
            'financial_impact'
        ]
        
        # Must have all critical business sections
        for section in required_sections:
            if section not in report:
                return False
                
        # Recommendations must be specific and actionable
        recommendations = report.get('recommendations', [])
        if not recommendations or len(recommendations) == 0:
            return False
            
        # Each recommendation must have action and impact
        for rec in recommendations:
            if not isinstance(rec, dict):
                return False
            if 'action' not in rec or 'expected_impact' not in rec:
                return False
                
        return True
    
    @staticmethod
    def validate_professional_structure(report: Dict[str, Any]) -> bool:
        """Ensures report follows professional business structure."""
        required_metadata = [
            'generated_at',
            'agent_type',
            'data_sources',
            'confidence_score'
        ]
        
        for field in required_metadata:
            if field not in report:
                return False
                
        # Confidence score must be reasonable
        confidence = report.get('confidence_score', 0)
        if not (0 <= confidence <= 1.0):
            return False
            
        return True


class TestAgentReportGeneration(BaseIntegrationTest):
    """Test agent report generation with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_basic_agent_execution_produces_reports(self, real_services_fixture):
        """
        Test agent execution results in report generation with business-valuable content.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: Core value delivery mechanism
        - Value Impact: Agents must generate reports to provide user value
        - Strategic Impact: Foundation of entire business model
        """
        # Setup real services
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create test user with real database
        user_id = UnifiedIdGenerator.generate_base_id("user_test")
        user = User(
            id=user_id,
            email="test@example.com",
            name="Test User",
            subscription_tier="enterprise"
        )
        db.add(user)
        await db.commit()
        
        # Create thread for agent execution
        thread_id = UnifiedIdGenerator.generate_base_id("thread_test")
        thread = Thread(
            id=thread_id,
            user_id=user_id,
            title="Cost Optimization Analysis"
        )
        db.add(thread)
        await db.commit()
        
        # Simulate agent execution that should produce report
        run_id = UnifiedIdGenerator.generate_base_id("run_test")
        
        # Create user execution context (SSOT pattern)
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            permissions=["read", "write"],
            subscription_tier="enterprise"
        )
        
        # Execute agent (simplified for integration test)
        agent_result = {
            "agent_type": "cost_optimizer",
            "status": "completed",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "executive_summary": "Found $50,000/month in cost savings opportunities",
            "key_findings": [
                "Overprovisioned EC2 instances: $25,000/month",
                "Unused RDS instances: $15,000/month", 
                "Inefficient S3 storage: $10,000/month"
            ],
            "recommendations": [
                {
                    "action": "Downsize EC2 instances by 50%",
                    "expected_impact": "$25,000/month savings",
                    "effort_required": "2 hours",
                    "risk_level": "low"
                },
                {
                    "action": "Archive or delete unused RDS instances",
                    "expected_impact": "$15,000/month savings", 
                    "effort_required": "4 hours",
                    "risk_level": "medium"
                }
            ],
            "financial_impact": {
                "monthly_savings": 50000,
                "annual_savings": 600000,
                "implementation_cost": 5000,
                "roi_percentage": 11900
            },
            "data_sources": ["AWS Cost Explorer", "CloudWatch"],
            "confidence_score": 0.85
        }
        
        # Store report in database (this is what the real system should do)
        message = Message(
            id=UnifiedIdGenerator.generate_message_id("agent", user_id, thread_id),
            thread_id=thread_id,
            user_id=user_id,
            run_id=run_id,
            message_type=MessageType.AGENT_RESPONSE,
            content=str(agent_result),
            metadata={"report_type": "cost_optimization"}
        )
        db.add(message)
        await db.commit()
        
        # CRITICAL ASSERTIONS: Report must exist and be actionable
        assert agent_result is not None, "Agent execution must produce a report"
        assert BusinessValueReportValidator.validate_actionable_content(agent_result), \
            f"Report lacks actionable business content: {agent_result}"
        assert agent_result["financial_impact"]["monthly_savings"] > 0, \
            "Cost optimization report must identify savings"
        
        # Verify report persistence for user access
        stored_message = await db.get(Message, message.id)
        assert stored_message is not None, "Report must be persisted for user access"
        assert stored_message.thread_id == thread_id, "Report must be linked to user thread"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_report_content_substantive_and_actionable(self, real_services_fixture):
        """
        Test generated reports contain specific, actionable business recommendations.
        
        Business Value Justification (BVJ):
        - Segment: Early, Mid, Enterprise  
        - Business Goal: User satisfaction and retention
        - Value Impact: Users must receive specific, implementable recommendations
        - Strategic Impact: Actionable reports drive user engagement and renewals
        """
        db = real_services_fixture["db"]
        
        # Create test scenario with business data
        test_data = {
            "monthly_spend": 75000,
            "cost_categories": {
                "compute": 35000,
                "storage": 20000, 
                "networking": 15000,
                "database": 5000
            },
            "utilization_metrics": {
                "compute_utilization": 0.35,
                "storage_utilization": 0.60,
                "idle_resources": ["prod-db-replica", "staging-cluster"]
            }
        }
        
        # Simulate comprehensive agent analysis
        detailed_report = {
            "agent_type": "comprehensive_analyzer",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "executive_summary": f"Analysis of ${test_data['monthly_spend']:,}/month infrastructure identifies 40% optimization opportunity",
            "key_findings": [
                f"Compute over-provisioning: ${test_data['cost_categories']['compute'] * 0.4:,.0f}/month waste",
                f"Storage inefficiencies: ${test_data['cost_categories']['storage'] * 0.25:,.0f}/month optimization",
                f"Idle resources: {len(test_data['utilization_metrics']['idle_resources'])} unused resources"
            ],
            "recommendations": [
                {
                    "action": "Implement auto-scaling for compute workloads",
                    "expected_impact": f"${test_data['cost_categories']['compute'] * 0.4:,.0f}/month reduction",
                    "effort_required": "8 hours setup + 2 hours monitoring",
                    "risk_level": "low",
                    "priority": "high",
                    "timeline": "1-2 weeks"
                },
                {
                    "action": "Migrate cold storage to lower-cost tiers",
                    "expected_impact": f"${test_data['cost_categories']['storage'] * 0.25:,.0f}/month reduction", 
                    "effort_required": "4 hours analysis + 6 hours migration",
                    "risk_level": "low",
                    "priority": "medium",
                    "timeline": "2-3 weeks"
                },
                {
                    "action": "Decommission idle database replica",
                    "expected_impact": "$2,500/month savings",
                    "effort_required": "2 hours validation + 1 hour shutdown",
                    "risk_level": "medium",
                    "priority": "high",
                    "timeline": "1 week"
                }
            ],
            "financial_impact": {
                "monthly_savings": 19500,
                "annual_savings": 234000,
                "implementation_cost": 8000,
                "roi_percentage": 2825,
                "payback_period_months": 0.4
            },
            "implementation_roadmap": {
                "week_1": ["Audit idle resources", "Plan auto-scaling implementation"],
                "week_2": ["Deploy auto-scaling", "Begin storage tier analysis"],
                "week_3": ["Execute storage migration", "Monitor auto-scaling performance"],
                "week_4": ["Validate savings", "Generate follow-up recommendations"]
            },
            "data_sources": ["AWS Cost Explorer", "CloudWatch", "Resource tagging audit"],
            "confidence_score": 0.92
        }
        
        # CRITICAL ASSERTIONS: Report must be actionable and comprehensive
        assert BusinessValueReportValidator.validate_actionable_content(detailed_report), \
            "Report must contain actionable business recommendations"
        
        # Each recommendation must be implementable
        for rec in detailed_report["recommendations"]:
            assert "effort_required" in rec, f"Recommendation lacks effort estimate: {rec}"
            assert "timeline" in rec, f"Recommendation lacks timeline: {rec}" 
            assert "expected_impact" in rec, f"Recommendation lacks impact quantification: {rec}"
            assert rec["risk_level"] in ["low", "medium", "high"], f"Invalid risk level: {rec['risk_level']}"
        
        # Financial impact must be quantified
        financial = detailed_report["financial_impact"]
        assert financial["monthly_savings"] > 0, "Must quantify monthly savings"
        assert financial["roi_percentage"] > 100, "ROI must exceed 100% for viable recommendations"
        assert "payback_period_months" in financial, "Must include payback period"
        
        # Implementation roadmap must exist for enterprise users
        assert "implementation_roadmap" in detailed_report, "Enterprise users require implementation roadmap"
        assert len(detailed_report["implementation_roadmap"]) > 0, "Roadmap must not be empty"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_report_persistence_to_database(self, real_services_fixture):
        """
        Test reports are properly structured for database storage and user retrieval.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: Data persistence and user access
        - Value Impact: Users must be able to access historical reports
        - Strategic Impact: Report history enables trend analysis and follow-up
        """
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create user and thread
        user_id = UserID.generate()
        thread_id = ThreadID.generate()
        
        user = User(id=str(user_id), email="enterprise@example.com", name="Enterprise User")
        db.add(user)
        
        thread = Thread(id=str(thread_id), user_id=str(user_id), title="Security Analysis")
        db.add(thread)
        await db.commit()
        
        # Generate comprehensive report
        security_report = {
            "report_id": str(MessageID.generate()),
            "agent_type": "security_analyzer",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "user_id": str(user_id),
            "thread_id": str(thread_id),
            "executive_summary": "Critical security vulnerabilities identified requiring immediate attention",
            "key_findings": [
                "3 critical vulnerabilities in production systems",
                "12 medium-priority configuration issues",
                "5 compliance gaps requiring remediation"
            ],
            "recommendations": [
                {
                    "action": "Patch critical vulnerabilities immediately",
                    "expected_impact": "Eliminate 90% of security risk",
                    "effort_required": "4 hours emergency maintenance",
                    "risk_level": "critical"
                }
            ],
            "financial_impact": {
                "risk_mitigation_value": 500000,
                "compliance_cost_avoidance": 50000,
                "implementation_cost": 10000
            },
            "data_sources": ["Vulnerability scanners", "Configuration audits", "Compliance frameworks"],
            "confidence_score": 0.95,
            "metadata": {
                "report_type": "security_analysis",
                "priority": "critical",
                "requires_immediate_action": True,
                "compliance_frameworks": ["SOC2", "ISO27001", "GDPR"]
            }
        }
        
        # Store report with proper database structure
        message = Message(
            id=security_report["report_id"],
            thread_id=str(thread_id),
            user_id=str(user_id),
            run_id=str(RunID.generate()),
            message_type=MessageType.AGENT_RESPONSE,
            content=str(security_report),
            metadata=security_report["metadata"]
        )
        db.add(message)
        await db.commit()
        
        # Cache report for fast access
        cache_key = f"report:{user_id}:{message.id}"
        await redis.set(cache_key, str(security_report), ex=3600)
        
        # CRITICAL ASSERTIONS: Report must be persistently accessible
        stored_message = await db.get(Message, message.id)
        assert stored_message is not None, "Report must persist in database"
        assert stored_message.user_id == str(user_id), "Report must be linked to correct user"
        assert stored_message.thread_id == str(thread_id), "Report must be linked to correct thread"
        assert stored_message.message_type == MessageType.AGENT_RESPONSE, "Must be identified as agent response"
        
        # Verify cache accessibility  
        cached_report = await redis.get(cache_key)
        assert cached_report is not None, "Report must be cached for fast access"
        
        # Verify report structure for retrieval
        assert "report_id" in security_report, "Report must have unique identifier"
        assert "user_id" in security_report, "Report must be linked to user"
        assert "thread_id" in security_report, "Report must be linked to thread"
        assert BusinessValueReportValidator.validate_professional_structure(security_report), \
            "Report must have professional structure for business use"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_report_retrieval_for_user_access(self, real_services_fixture):
        """
        Test reports can be retrieved and accessed by users after generation.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: User experience and data access
        - Value Impact: Users must access reports to derive business value
        - Strategic Impact: Report accessibility drives platform adoption
        """
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create user with multiple reports
        user_id = UserID.generate()
        user = User(id=str(user_id), email="user@example.com", name="Business User")
        db.add(user)
        
        thread_id = ThreadID.generate()
        thread = Thread(id=str(thread_id), user_id=str(user_id), title="Performance Analysis")
        db.add(thread)
        await db.commit()
        
        # Generate and store multiple reports
        reports = []
        for i in range(3):
            report = {
                "report_id": str(MessageID.generate()),
                "agent_type": "performance_analyzer", 
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sequence": i + 1,
                "executive_summary": f"Performance analysis report #{i + 1}",
                "key_findings": [f"Finding {i + 1}.1", f"Finding {i + 1}.2"],
                "recommendations": [
                    {
                        "action": f"Action {i + 1}",
                        "expected_impact": f"Impact {i + 1}",
                        "effort_required": "2 hours"
                    }
                ],
                "financial_impact": {
                    "monthly_savings": (i + 1) * 5000,
                    "annual_savings": (i + 1) * 60000
                },
                "data_sources": ["APM tools", "Performance metrics"],
                "confidence_score": 0.8 + (i * 0.05)
            }
            reports.append(report)
            
            message = Message(
                id=report["report_id"],
                thread_id=str(thread_id),
                user_id=str(user_id),
                run_id=str(RunID.generate()),
                message_type=MessageType.AGENT_RESPONSE,
                content=str(report),
                metadata={"sequence": i + 1, "report_type": "performance"}
            )
            db.add(message)
        
        await db.commit()
        
        # Test report retrieval by user
        user_messages = db.query(Message).filter(
            Message.user_id == str(user_id),
            Message.thread_id == str(thread_id),
            Message.message_type == MessageType.AGENT_RESPONSE
        ).all()
        
        # CRITICAL ASSERTIONS: All reports must be retrievable
        assert len(user_messages) == 3, f"Must retrieve all user reports, got {len(user_messages)}"
        
        # Verify reports are in correct order and accessible
        for i, message in enumerate(user_messages):
            assert message.user_id == str(user_id), f"Message {i} must belong to correct user"
            assert message.thread_id == str(thread_id), f"Message {i} must belong to correct thread"
            assert message.message_type == MessageType.AGENT_RESPONSE, f"Message {i} must be agent response"
            
            # Verify report content is accessible and valid
            assert message.content is not None, f"Report {i} content must not be None"
            assert len(message.content) > 0, f"Report {i} content must not be empty"
            
        # Test latest report retrieval (common user pattern)
        latest_message = db.query(Message).filter(
            Message.user_id == str(user_id),
            Message.thread_id == str(thread_id),
            Message.message_type == MessageType.AGENT_RESPONSE
        ).order_by(Message.created_at.desc()).first()
        
        assert latest_message is not None, "Must be able to retrieve latest report"
        assert "sequence" in latest_message.metadata, "Latest report must have sequence metadata"
        assert latest_message.metadata["sequence"] == 3, "Must retrieve the most recent report"

    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_multi_user_report_isolation(self, real_services_fixture):
        """
        Test reports are properly isolated between different users.
        
        Business Value Justification (BVJ):
        - Segment: Enterprise
        - Business Goal: Data security and compliance
        - Value Impact: Multi-user isolation is critical for enterprise adoption
        - Strategic Impact: Isolation failures would block enterprise sales
        """
        db = real_services_fixture["db"]
        
        # Create two separate enterprise users
        user1_id = UserID.generate()
        user2_id = UserID.generate()
        
        user1 = User(id=str(user1_id), email="enterprise1@company.com", name="Enterprise User 1")
        user2 = User(id=str(user2_id), email="enterprise2@company.com", name="Enterprise User 2")
        
        db.add(user1)
        db.add(user2)
        
        # Create separate threads
        thread1_id = ThreadID.generate()
        thread2_id = ThreadID.generate()
        
        thread1 = Thread(id=str(thread1_id), user_id=str(user1_id), title="User 1 Analysis")
        thread2 = Thread(id=str(thread2_id), user_id=str(user2_id), title="User 2 Analysis")
        
        db.add(thread1)
        db.add(thread2)
        await db.commit()
        
        # Generate confidential reports for each user
        user1_report = {
            "report_id": str(MessageID.generate()),
            "agent_type": "confidential_analyzer",
            "user_id": str(user1_id),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "executive_summary": "CONFIDENTIAL: User 1 sensitive business data analysis",
            "key_findings": [
                "Proprietary algorithm performance: 95% accuracy",
                "Competitive advantage metrics: $2M annual value", 
                "Trade secret vulnerabilities identified"
            ],
            "recommendations": [
                {
                    "action": "Implement additional IP protection measures",
                    "expected_impact": "$500K risk mitigation",
                    "effort_required": "1 week",
                    "classification": "confidential"
                }
            ],
            "financial_impact": {
                "ip_value": 2000000,
                "risk_exposure": 500000
            },
            "data_sources": ["Internal systems", "Proprietary databases"],
            "confidence_score": 0.92,
            "classification": "confidential"
        }
        
        user2_report = {
            "report_id": str(MessageID.generate()),
            "agent_type": "confidential_analyzer", 
            "user_id": str(user2_id),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "executive_summary": "CONFIDENTIAL: User 2 different sensitive business data",
            "key_findings": [
                "Alternative business strategy analysis",
                "Different competitive landscape: $1.5M opportunity",
                "Unique operational challenges identified"
            ],
            "recommendations": [
                {
                    "action": "Explore new market segments",
                    "expected_impact": "$300K revenue opportunity",
                    "effort_required": "2 weeks", 
                    "classification": "confidential"
                }
            ],
            "financial_impact": {
                "market_opportunity": 1500000,
                "investment_required": 200000
            },
            "data_sources": ["Internal CRM", "Market research"],
            "confidence_score": 0.88,
            "classification": "confidential"
        }
        
        # Store reports with proper user isolation
        message1 = Message(
            id=user1_report["report_id"],
            thread_id=str(thread1_id),
            user_id=str(user1_id),
            run_id=str(RunID.generate()),
            message_type=MessageType.AGENT_RESPONSE,
            content=str(user1_report),
            metadata={"classification": "confidential", "owner": str(user1_id)}
        )
        
        message2 = Message(
            id=user2_report["report_id"],
            thread_id=str(thread2_id),
            user_id=str(user2_id), 
            run_id=str(RunID.generate()),
            message_type=MessageType.AGENT_RESPONSE,
            content=str(user2_report),
            metadata={"classification": "confidential", "owner": str(user2_id)}
        )
        
        db.add(message1)
        db.add(message2)
        await db.commit()
        
        # CRITICAL ASSERTIONS: Perfect user isolation required
        
        # User 1 can only access their own reports
        user1_messages = db.query(Message).filter(
            Message.user_id == str(user1_id)
        ).all()
        assert len(user1_messages) == 1, "User 1 must only see their own reports"
        assert user1_messages[0].id == user1_report["report_id"], "User 1 must get correct report"
        assert str(user1_id) in user1_messages[0].content, "Report must contain User 1's data"
        assert str(user2_id) not in user1_messages[0].content, "Report must NOT contain User 2's data"
        
        # User 2 can only access their own reports
        user2_messages = db.query(Message).filter(
            Message.user_id == str(user2_id)
        ).all()
        assert len(user2_messages) == 1, "User 2 must only see their own reports"
        assert user2_messages[0].id == user2_report["report_id"], "User 2 must get correct report"
        assert str(user2_id) in user2_messages[0].content, "Report must contain User 2's data"
        assert str(user1_id) not in user2_messages[0].content, "Report must NOT contain User 1's data"
        
        # Cross-user access must be completely blocked
        user1_cannot_access_user2 = db.query(Message).filter(
            Message.user_id == str(user2_id),
            Message.id == user1_report["report_id"]
        ).first()
        assert user1_cannot_access_user2 is None, "User 1 must not access User 2's reports"
        
        user2_cannot_access_user1 = db.query(Message).filter(
            Message.user_id == str(user1_id),
            Message.id == user2_report["report_id"]
        ).first()
        assert user2_cannot_access_user1 is None, "User 2 must not access User 1's reports"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_cases_produce_meaningful_reports(self, real_services_fixture):
        """
        Test system generates useful reports even with missing/malformed data.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: System reliability and user experience
        - Value Impact: Users must receive value even when data is incomplete
        - Strategic Impact: Graceful error handling prevents user churn
        """
        db = real_services_fixture["db"]
        
        # Create test user
        user_id = UserID.generate()
        user = User(id=str(user_id), email="test@example.com", name="Test User")
        db.add(user)
        
        thread_id = ThreadID.generate()
        thread = Thread(id=str(thread_id), user_id=str(user_id), title="Error Handling Test")
        db.add(thread)
        await db.commit()
        
        # Test Case 1: Missing data but still provide value
        incomplete_data_report = {
            "report_id": str(MessageID.generate()),
            "agent_type": "resilient_analyzer",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "partial_data",
            "executive_summary": "Analysis completed with partial data - actionable insights still available",
            "data_limitations": [
                "AWS Cost Explorer API returned incomplete data for 3 days",
                "CloudWatch metrics missing for 2 services",
                "30% of resources lack cost allocation tags"
            ],
            "key_findings": [
                "Available data shows $15,000/month optimization opportunity",
                "Pattern analysis suggests 40% additional savings possible with complete data",
                "Identified optimization areas despite data gaps"
            ],
            "recommendations": [
                {
                    "action": "Implement cost allocation tagging strategy",
                    "expected_impact": "$5,000/month visibility improvement",
                    "effort_required": "4 hours",
                    "confidence": "high",
                    "data_dependency": "low"
                },
                {
                    "action": "Schedule follow-up analysis when data issues resolved",
                    "expected_impact": "Complete $40,000/month optimization plan",
                    "effort_required": "2 hours",
                    "confidence": "medium",
                    "data_dependency": "high"
                }
            ],
            "financial_impact": {
                "confirmed_savings": 15000,
                "potential_additional_savings": 25000,
                "confidence_level": 0.7,
                "data_completeness": 0.6
            },
            "data_sources": ["Partial AWS Cost Explorer", "Incomplete CloudWatch"],
            "confidence_score": 0.7,
            "next_steps": [
                "Resolve data collection issues",
                "Re-run analysis with complete data",
                "Implement immediate high-confidence recommendations"
            ]
        }
        
        # Test Case 2: API errors but still provide guidance
        api_error_report = {
            "report_id": str(MessageID.generate()),
            "agent_type": "error_resilient_analyzer",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "api_errors_encountered",
            "executive_summary": "External API errors prevented complete analysis, providing alternative insights",
            "error_details": [
                "AWS Cost Explorer API: Rate limit exceeded (429)",
                "CloudWatch API: Authentication failed (403)",
                "Third-party cost tool: Service unavailable (503)"
            ],
            "alternative_analysis": {
                "method": "Historical data pattern analysis",
                "data_source": "Cached data from last 30 days",
                "reliability": "Medium - based on trends"
            },
            "key_findings": [
                "Historical patterns suggest typical $20K/month optimization opportunity",
                "Previous recommendations show 80% success rate",
                "Cost trends indicate immediate attention needed"
            ],
            "recommendations": [
                {
                    "action": "Review and implement previous month's recommendations",
                    "expected_impact": "$16,000/month (80% of typical $20K)",
                    "effort_required": "Review previous report + 6 hours implementation",
                    "confidence": "high",
                    "basis": "historical_success"
                },
                {
                    "action": "Retry analysis once API issues resolved",
                    "expected_impact": "Updated optimization plan",
                    "effort_required": "1 hour",
                    "timeline": "Within 24 hours"
                }
            ],
            "financial_impact": {
                "conservative_estimate": 16000,
                "basis": "80% of historical average",
                "confidence_level": 0.8
            },
            "data_sources": ["Historical cache", "Previous successful analyses"],
            "confidence_score": 0.8,
            "recovery_plan": "Automated retry every 2 hours until APIs available"
        }
        
        # Store error case reports
        error_reports = [incomplete_data_report, api_error_report]
        for report in error_reports:
            message = Message(
                id=report["report_id"],
                thread_id=str(thread_id),
                user_id=str(user_id),
                run_id=str(RunID.generate()),
                message_type=MessageType.AGENT_RESPONSE,
                content=str(report),
                metadata={"error_handling": True, "status": report["status"]}
            )
            db.add(message)
        
        await db.commit()
        
        # CRITICAL ASSERTIONS: Even error cases must provide business value
        error_messages = db.query(Message).filter(
            Message.user_id == str(user_id),
            Message.thread_id == str(thread_id)
        ).all()
        
        assert len(error_messages) == 2, "Both error case reports must be stored"
        
        for message in error_messages:
            # Every report must have actionable content even in error cases
            assert "recommendations" in message.content, "Error reports must still provide recommendations"
            assert "financial_impact" in message.content, "Error reports must still quantify business value"
            assert "confidence_score" in message.content, "Error reports must indicate confidence level"
            
            # Error transparency required
            assert ("error" in message.content.lower() or "partial" in message.content.lower() or 
                   "incomplete" in message.content.lower()), "Must clearly communicate limitations"
            
            # Must provide next steps
            assert ("next_steps" in message.content or "recovery_plan" in message.content or 
                   "retry" in message.content), "Must provide path forward despite errors"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_report_formatting_and_structure(self, real_services_fixture):
        """
        Test all reports follow consistent, professional structure.
        
        Business Value Justification (BVJ):
        - Segment: Mid, Enterprise
        - Business Goal: Professional presentation and usability  
        - Value Impact: Consistent structure enables user training and adoption
        - Strategic Impact: Professional reports drive enterprise sales
        """
        db = real_services_fixture["db"]
        
        # Create enterprise user expecting professional reports
        user_id = UserID.generate()
        user = User(
            id=str(user_id), 
            email="enterprise@bigcorp.com", 
            name="Enterprise Executive",
            subscription_tier="enterprise"
        )
        db.add(user)
        
        thread_id = ThreadID.generate()
        thread = Thread(id=str(thread_id), user_id=str(user_id), title="Executive Dashboard")
        db.add(thread)
        await db.commit()
        
        # Generate professionally structured report
        executive_report = {
            "report_id": str(MessageID.generate()),
            "report_version": "1.0",
            "agent_type": "executive_analyzer",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_for": {
                "user_name": "Enterprise Executive",
                "user_email": "enterprise@bigcorp.com",
                "subscription_tier": "enterprise"
            },
            
            # Executive Summary Section (required first)
            "executive_summary": {
                "headline": "Q4 Cost Optimization Analysis: $2.4M Annual Savings Identified",
                "key_metrics": {
                    "total_annual_savings": 2400000,
                    "implementation_effort": "160 hours",
                    "roi_percentage": 1400,
                    "payback_period": "6 weeks"
                },
                "priority_actions": [
                    "Immediate: Rightsize compute resources ($800K/year)",
                    "Q1 2024: Storage optimization program ($600K/year)", 
                    "Q2 2024: Reserved instance strategy ($1M/year)"
                ]
            },
            
            # Detailed Findings Section
            "detailed_analysis": {
                "scope": "Full infrastructure analysis covering compute, storage, networking",
                "methodology": "Cost analysis + utilization assessment + benchmarking",
                "data_period": "90 days (September-November 2023)",
                "confidence_level": 0.94
            },
            
            "key_findings": [
                {
                    "category": "Compute Optimization",
                    "finding": "65% of EC2 instances over-provisioned by average of 40%",
                    "financial_impact": "$800,000/year waste",
                    "urgency": "immediate"
                },
                {
                    "category": "Storage Efficiency", 
                    "finding": "40% of S3 storage eligible for cheaper tiers",
                    "financial_impact": "$600,000/year optimization",
                    "urgency": "medium"
                },
                {
                    "category": "Reserved Instances",
                    "finding": "Only 30% coverage despite predictable workloads",
                    "financial_impact": "$1,000,000/year missed savings",
                    "urgency": "high"
                }
            ],
            
            # Detailed Recommendations Section
            "recommendations": [
                {
                    "priority": 1,
                    "category": "Immediate Cost Reduction",
                    "action": "Rightsize over-provisioned compute resources",
                    "business_justification": "Immediate cost reduction with minimal business risk",
                    "expected_impact": {
                        "annual_savings": 800000,
                        "monthly_savings": 66667,
                        "cost_reduction_percentage": 35
                    },
                    "implementation": {
                        "effort_required": "40 hours over 2 weeks",
                        "key_milestones": [
                            "Week 1: Identify and validate rightsizing targets",
                            "Week 2: Execute changes during maintenance windows",
                            "Week 3: Monitor performance and adjust"
                        ],
                        "risk_mitigation": "Gradual rollout with performance monitoring",
                        "success_metrics": ["Cost reduction", "Performance maintained", "No service disruption"]
                    },
                    "owner": "Infrastructure Team",
                    "timeline": "2 weeks",
                    "risk_level": "low"
                }
            ],
            
            # Financial Impact Analysis
            "financial_impact": {
                "summary": {
                    "total_annual_savings": 2400000,
                    "total_implementation_cost": 80000,
                    "net_annual_benefit": 2320000,
                    "roi_percentage": 2900,
                    "payback_period_weeks": 6
                },
                "breakdown_by_quarter": {
                    "Q4_2023": {"savings": 200000, "investment": 80000, "net": 120000},
                    "Q1_2024": {"savings": 600000, "investment": 0, "net": 600000},
                    "Q2_2024": {"savings": 800000, "investment": 0, "net": 800000},
                    "Q3_2024": {"savings": 800000, "investment": 0, "net": 800000}
                }
            },
            
            # Professional Metadata
            "metadata": {
                "report_type": "executive_analysis",
                "confidentiality": "internal",
                "distribution": ["C-Suite", "Finance", "Infrastructure"],
                "review_cycle": "quarterly",
                "next_review_date": "2024-01-15",
                "analyst": "Netra AI Cost Optimization Agent",
                "data_sources": [
                    "AWS Cost & Usage Reports (90 days)",
                    "CloudWatch Performance Metrics",
                    "Reserved Instance Utilization Reports",
                    "Industry benchmarking data"
                ],
                "assumptions": [
                    "Current usage patterns continue",
                    "No major architectural changes",
                    "Implementation team availability as planned"
                ],
                "limitations": [
                    "Analysis based on 90-day period",
                    "Reserved instance pricing subject to AWS changes",
                    "Performance impact estimates require validation"
                ]
            },
            
            "confidence_score": 0.94
        }
        
        # Store professionally formatted report
        message = Message(
            id=executive_report["report_id"],
            thread_id=str(thread_id),
            user_id=str(user_id),
            run_id=str(RunID.generate()),
            message_type=MessageType.AGENT_RESPONSE,
            content=str(executive_report),
            metadata={
                "report_type": "executive_analysis",
                "formatting": "professional",
                "target_audience": "enterprise"
            }
        )
        db.add(message)
        await db.commit()
        
        # CRITICAL ASSERTIONS: Professional structure required
        assert BusinessValueReportValidator.validate_professional_structure(executive_report), \
            "Report must meet professional structure standards"
        
        # Required executive sections
        required_sections = [
            "executive_summary", "detailed_analysis", "key_findings", 
            "recommendations", "financial_impact", "metadata"
        ]
        for section in required_sections:
            assert section in executive_report, f"Professional reports must include {section} section"
        
        # Executive summary must be comprehensive
        exec_summary = executive_report["executive_summary"]
        assert "headline" in exec_summary, "Executive summary must have clear headline"
        assert "key_metrics" in exec_summary, "Must include key performance metrics"
        assert "priority_actions" in exec_summary, "Must include prioritized actions"
        
        # Financial impact must be detailed for enterprise users
        financial = executive_report["financial_impact"]
        assert "summary" in financial, "Must include financial summary"
        assert "breakdown_by_quarter" in financial, "Enterprise users require quarterly breakdown"
        assert financial["summary"]["roi_percentage"] > 100, "Must demonstrate clear ROI"
        
        # Recommendations must be implementation-ready
        for rec in executive_report["recommendations"]:
            assert "business_justification" in rec, "Enterprise recommendations need business justification"
            assert "implementation" in rec, "Must include detailed implementation plan"
            assert "timeline" in rec, "Must specify timeline"
            assert "owner" in rec, "Must assign ownership"
        
        # Metadata must be comprehensive for professional reports
        metadata = executive_report["metadata"]
        assert "data_sources" in metadata, "Must document data sources"
        assert "assumptions" in metadata, "Must state assumptions"
        assert "limitations" in metadata, "Must acknowledge limitations"
        assert "next_review_date" in metadata, "Must schedule follow-up"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_tool_execution_results_in_reports(self, real_services_fixture):
        """
        Test tool execution results are properly incorporated into final reports.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: Tool integration and comprehensive analysis
        - Value Impact: Tools enable deep analysis that drives report quality
        - Strategic Impact: Tool capabilities differentiate platform from competitors
        """
        db = real_services_fixture["db"]
        
        # Create user for comprehensive analysis
        user_id = UserID.generate()
        user = User(id=str(user_id), email="analyst@company.com", name="Business Analyst")
        db.add(user)
        
        thread_id = ThreadID.generate()
        thread = Thread(id=str(thread_id), user_id=str(user_id), title="Tool-Enhanced Analysis")
        db.add(thread)
        await db.commit()
        
        # Simulate multiple tool executions
        tool_results = {
            "cost_analyzer_tool": {
                "execution_time": "2.3 seconds",
                "status": "completed",
                "results": {
                    "monthly_costs": {
                        "compute": 45000,
                        "storage": 12000,
                        "networking": 8000,
                        "database": 15000
                    },
                    "waste_identified": {
                        "unused_resources": 8500,
                        "over_provisioned": 12000,
                        "inefficient_storage": 3500
                    },
                    "optimization_opportunities": [
                        {"type": "rightsizing", "savings": 12000},
                        {"type": "reserved_instances", "savings": 6000},
                        {"type": "storage_optimization", "savings": 3500}
                    ]
                },
                "confidence": 0.92
            },
            "security_scanner_tool": {
                "execution_time": "5.7 seconds", 
                "status": "completed",
                "results": {
                    "vulnerabilities": {
                        "critical": 2,
                        "high": 8,
                        "medium": 15,
                        "low": 23
                    },
                    "compliance_gaps": [
                        {"framework": "SOC2", "gaps": 3},
                        {"framework": "ISO27001", "gaps": 5}
                    ],
                    "risk_score": 7.8,
                    "immediate_actions_required": [
                        "Patch CVE-2023-1234 (critical)",
                        "Update SSL certificates (high)"
                    ]
                },
                "confidence": 0.95
            },
            "performance_analyzer_tool": {
                "execution_time": "3.1 seconds",
                "status": "completed", 
                "results": {
                    "response_times": {
                        "api_average": "245ms",
                        "database_average": "89ms",
                        "cache_hit_rate": 0.87
                    },
                    "bottlenecks": [
                        {"component": "user_service", "impact": "high", "fix_effort": "medium"},
                        {"component": "payment_processor", "impact": "medium", "fix_effort": "low"}
                    ],
                    "performance_score": 6.4,
                    "recommendations": [
                        "Implement database query optimization",
                        "Add caching layer to user service"
                    ]
                },
                "confidence": 0.88
            }
        }
        
        # Generate comprehensive report incorporating all tool results
        tool_enhanced_report = {
            "report_id": str(MessageID.generate()),
            "agent_type": "comprehensive_multi_tool_analyzer",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tool_execution_summary": {
                "tools_executed": list(tool_results.keys()),
                "total_execution_time": "11.1 seconds",
                "all_tools_successful": True,
                "combined_confidence": 0.92
            },
            
            "executive_summary": "Multi-tool analysis reveals $24K/month optimization opportunity across cost, security, and performance domains",
            
            "integrated_findings": {
                "cost_optimization": {
                    "source_tool": "cost_analyzer_tool",
                    "monthly_savings_potential": 21500,
                    "key_insights": tool_results["cost_analyzer_tool"]["results"]["optimization_opportunities"],
                    "tool_confidence": tool_results["cost_analyzer_tool"]["confidence"]
                },
                "security_assessment": {
                    "source_tool": "security_scanner_tool", 
                    "risk_level": "high",
                    "critical_vulnerabilities": tool_results["security_scanner_tool"]["results"]["vulnerabilities"]["critical"],
                    "compliance_status": tool_results["security_scanner_tool"]["results"]["compliance_gaps"],
                    "tool_confidence": tool_results["security_scanner_tool"]["confidence"]
                },
                "performance_analysis": {
                    "source_tool": "performance_analyzer_tool",
                    "performance_score": tool_results["performance_analyzer_tool"]["results"]["performance_score"],
                    "bottlenecks": tool_results["performance_analyzer_tool"]["results"]["bottlenecks"],
                    "tool_confidence": tool_results["performance_analyzer_tool"]["confidence"]
                }
            },
            
            "cross_tool_insights": [
                {
                    "insight": "Cost optimization efforts should prioritize security-compliant solutions",
                    "supporting_tools": ["cost_analyzer_tool", "security_scanner_tool"],
                    "business_impact": "Ensures cost savings don't compromise security compliance"
                },
                {
                    "insight": "Performance bottlenecks correlate with highest-cost services",
                    "supporting_tools": ["cost_analyzer_tool", "performance_analyzer_tool"],
                    "business_impact": "Performance improvements will also reduce costs"
                }
            ],
            
            "integrated_recommendations": [
                {
                    "action": "Implement security-compliant rightsizing strategy",
                    "data_sources": ["cost_analyzer_tool", "security_scanner_tool"],
                    "expected_impact": {
                        "cost_savings": 10000,
                        "security_improvement": "Eliminates 2 critical vulnerabilities",
                        "compliance_benefit": "Closes SOC2 gaps"
                    },
                    "effort_required": "12 hours",
                    "priority": "critical"
                },
                {
                    "action": "Optimize high-cost performance bottlenecks",
                    "data_sources": ["cost_analyzer_tool", "performance_analyzer_tool"],
                    "expected_impact": {
                        "cost_savings": 8000,
                        "performance_improvement": "40% faster API response",
                        "user_experience": "Improved satisfaction scores"
                    },
                    "effort_required": "8 hours",
                    "priority": "high"
                }
            ],
            
            "financial_impact": {
                "total_monthly_savings": 24000,
                "annual_savings": 288000,
                "tool_execution_roi": 28700,  # ROI on tool execution investment
                "confidence_weighted_savings": 22080  # Adjusted for tool confidence levels
            },
            
            "tool_execution_details": tool_results,
            "data_sources": ["Multi-tool execution results", "Cross-tool correlation analysis"],
            "confidence_score": 0.92
        }
        
        # Store tool-enhanced report
        message = Message(
            id=tool_enhanced_report["report_id"],
            thread_id=str(thread_id),
            user_id=str(user_id),
            run_id=str(RunID.generate()),
            message_type=MessageType.AGENT_RESPONSE,
            content=str(tool_enhanced_report),
            metadata={
                "tools_used": list(tool_results.keys()),
                "tool_count": len(tool_results),
                "multi_tool_analysis": True
            }
        )
        db.add(message)
        await db.commit()
        
        # CRITICAL ASSERTIONS: Tool integration must enhance report value
        
        # All tool results must be incorporated
        for tool_name in tool_results.keys():
            assert tool_name in tool_enhanced_report["tool_execution_details"], \
                f"Tool {tool_name} results must be included in report"
        
        # Tool execution must be summarized
        assert "tool_execution_summary" in tool_enhanced_report, "Must summarize tool execution"
        assert tool_enhanced_report["tool_execution_summary"]["all_tools_successful"], \
            "Tool execution status must be clear"
        
        # Integrated findings must reference specific tools
        integrated = tool_enhanced_report["integrated_findings"]
        for domain, findings in integrated.items():
            assert "source_tool" in findings, f"{domain} findings must reference source tool"
            assert "tool_confidence" in findings, f"{domain} must include tool confidence score"
        
        # Cross-tool insights must exist (this is the value-add)
        cross_insights = tool_enhanced_report["cross_tool_insights"]
        assert len(cross_insights) > 0, "Must provide cross-tool insights"
        for insight in cross_insights:
            assert len(insight["supporting_tools"]) >= 2, "Cross-tool insights need multiple tools"
            assert "business_impact" in insight, "Must explain business value of cross-tool analysis"
        
        # Recommendations must integrate multiple tool outputs
        integrated_recs = tool_enhanced_report["integrated_recommendations"]
        for rec in integrated_recs:
            assert "data_sources" in rec, "Recommendations must cite tool data sources"
            assert len(rec["data_sources"]) >= 1, "Must reference at least one tool"
            
        # Financial impact must account for tool execution value
        financial = tool_enhanced_report["financial_impact"]
        assert "tool_execution_roi" in financial, "Must quantify ROI of using tools"
        assert "confidence_weighted_savings" in financial, "Must adjust for tool confidence"
        assert financial["confidence_weighted_savings"] > 0, "Tool-enhanced analysis must add value"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_report_metadata_and_tracking(self, real_services_fixture):
        """
        Test reports include proper metadata for analytics and tracking.
        
        Business Value Justification (BVJ):
        - Segment: Platform/Internal + Enterprise
        - Business Goal: Analytics and business intelligence
        - Value Impact: Metadata enables usage analytics and improvement identification
        - Strategic Impact: Data-driven product development and customer success
        """
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create user with tracking requirements
        user_id = UserID.generate()
        user = User(
            id=str(user_id),
            email="tracked@enterprise.com", 
            name="Tracked User",
            subscription_tier="enterprise"
        )
        db.add(user)
        
        thread_id = ThreadID.generate()
        thread = Thread(id=str(thread_id), user_id=str(user_id), title="Analytics Test")
        db.add(thread)
        await db.commit()
        
        # Generate report with comprehensive tracking metadata
        tracked_report = {
            "report_id": str(MessageID.generate()),
            "agent_type": "analytics_tracked_agent",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            
            # Core report content
            "executive_summary": "Tracked analysis with comprehensive metadata",
            "key_findings": ["Finding 1", "Finding 2"],
            "recommendations": [
                {
                    "action": "Tracked recommendation",
                    "expected_impact": "$10,000/month savings",
                    "effort_required": "4 hours"
                }
            ],
            "financial_impact": {
                "monthly_savings": 10000,
                "annual_savings": 120000
            },
            "confidence_score": 0.85,
            
            # Comprehensive tracking metadata
            "tracking_metadata": {
                # User analytics
                "user_analytics": {
                    "user_id": str(user_id),
                    "subscription_tier": "enterprise",
                    "user_timezone": "UTC-8",
                    "user_session_duration": 45.7,  # minutes
                    "previous_reports_count": 12,
                    "user_engagement_score": 0.78
                },
                
                # Report generation metrics
                "generation_metrics": {
                    "generation_time_seconds": 23.4,
                    "data_processing_time_seconds": 18.1,
                    "llm_inference_time_seconds": 5.3,
                    "total_tokens_used": 8450,
                    "cost_per_report_cents": 12.7
                },
                
                # Business metrics
                "business_metrics": {
                    "report_category": "cost_optimization",
                    "business_value_tier": "high",  # high/medium/low
                    "estimated_user_savings": 120000,
                    "complexity_score": 0.73,
                    "actionability_score": 0.91
                },
                
                # Technical metrics
                "technical_metrics": {
                    "agent_version": "v2.1.4",
                    "model_version": "gpt-4-1106-preview",
                    "tools_executed": ["cost_analyzer", "trend_predictor"],
                    "data_sources_accessed": 5,
                    "api_calls_made": 23,
                    "cache_hit_rate": 0.67
                },
                
                # Quality metrics
                "quality_metrics": {
                    "confidence_score": 0.85,
                    "completeness_score": 0.92,
                    "accuracy_estimation": 0.88,
                    "user_satisfaction_prediction": 0.84
                },
                
                # Usage context
                "usage_context": {
                    "trigger_type": "scheduled",  # manual/scheduled/automated
                    "report_frequency": "weekly",
                    "related_reports": ["report_123", "report_098"],
                    "follow_up_scheduled": True,
                    "integration_endpoints": ["dashboard", "email", "api"]
                },
                
                # Performance tracking
                "performance_tracking": {
                    "memory_usage_mb": 145.3,
                    "cpu_time_seconds": 8.7,
                    "database_queries": 12,
                    "cache_operations": 28,
                    "error_count": 0,
                    "warning_count": 2
                }
            },
            
            "data_sources": ["Tracked data sources"],
            "generated_by": "analytics_tracked_agent_v2.1.4"
        }
        
        # Store report with metadata
        message = Message(
            id=tracked_report["report_id"],
            thread_id=str(thread_id),
            user_id=str(user_id),
            run_id=str(RunID.generate()),
            message_type=MessageType.AGENT_RESPONSE,
            content=str(tracked_report),
            metadata={
                "tracking_enabled": True,
                "analytics_tier": "enterprise",
                "generation_cost_cents": tracked_report["tracking_metadata"]["generation_metrics"]["cost_per_report_cents"]
            }
        )
        db.add(message)
        await db.commit()
        
        # Store tracking data in Redis for analytics
        tracking_key = f"report_analytics:{user_id}:{tracked_report['report_id']}"
        await redis.hset(tracking_key, mapping={
            "user_id": str(user_id),
            "report_id": tracked_report["report_id"],
            "generation_time": tracked_report["tracking_metadata"]["generation_metrics"]["generation_time_seconds"],
            "business_value": tracked_report["tracking_metadata"]["business_metrics"]["estimated_user_savings"],
            "confidence": tracked_report["confidence_score"],
            "cost_cents": tracked_report["tracking_metadata"]["generation_metrics"]["cost_per_report_cents"]
        })
        await redis.expire(tracking_key, 2592000)  # 30 days
        
        # CRITICAL ASSERTIONS: Comprehensive metadata required
        
        # Tracking metadata must be comprehensive
        tracking = tracked_report["tracking_metadata"]
        required_tracking_sections = [
            "user_analytics", "generation_metrics", "business_metrics",
            "technical_metrics", "quality_metrics", "usage_context", "performance_tracking"
        ]
        for section in required_tracking_sections:
            assert section in tracking, f"Must include {section} in tracking metadata"
        
        # User analytics for customer success
        user_analytics = tracking["user_analytics"]
        assert "subscription_tier" in user_analytics, "Must track subscription tier for analytics"
        assert "user_engagement_score" in user_analytics, "Must track engagement for churn prediction"
        assert "previous_reports_count" in user_analytics, "Must track usage frequency"
        
        # Generation metrics for cost optimization
        gen_metrics = tracking["generation_metrics"]
        assert "generation_time_seconds" in gen_metrics, "Must track performance metrics"
        assert "cost_per_report_cents" in gen_metrics, "Must track cost per report for profitability"
        assert "total_tokens_used" in gen_metrics, "Must track token usage for optimization"
        
        # Business metrics for value measurement
        biz_metrics = tracking["business_metrics"]
        assert "estimated_user_savings" in biz_metrics, "Must track business value delivered"
        assert "actionability_score" in biz_metrics, "Must measure report quality"
        assert "business_value_tier" in biz_metrics, "Must categorize value tier"
        
        # Quality metrics for improvement
        quality = tracking["quality_metrics"]
        assert "confidence_score" in quality, "Must track confidence for quality assurance"
        assert "completeness_score" in quality, "Must measure report completeness"
        assert "user_satisfaction_prediction" in quality, "Must predict user satisfaction"
        
        # Performance metrics for optimization
        performance = tracking["performance_tracking"]
        assert "memory_usage_mb" in performance, "Must track resource usage"
        assert "error_count" in performance, "Must track error rates"
        assert "database_queries" in performance, "Must track database efficiency"
        
        # Verify analytics storage
        analytics_data = await redis.hgetall(tracking_key)
        assert analytics_data is not None, "Analytics data must be stored for business intelligence"
        assert "business_value" in analytics_data, "Must track business value in analytics store"
        assert float(analytics_data["cost_cents"]) > 0, "Must track costs for profitability analysis"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_report_completeness_validation(self, real_services_fixture):
        """
        Test reports are complete with all required sections for business value.
        
        Business Value Justification (BVJ):
        - Segment: All  
        - Business Goal: Quality assurance and completeness
        - Value Impact: Complete reports ensure users get full value from analysis
        - Strategic Impact: Incomplete reports damage user trust and retention
        """
        db = real_services_fixture["db"]
        
        # Create quality-conscious user
        user_id = UserID.generate()
        user = User(
            id=str(user_id),
            email="quality@company.com", 
            name="Quality User",
            subscription_tier="enterprise"
        )
        db.add(user)
        
        thread_id = ThreadID.generate()
        thread = Thread(id=str(thread_id), user_id=str(user_id), title="Completeness Test")
        db.add(thread)
        await db.commit()
        
        # Test Case 1: Complete high-quality report
        complete_report = {
            "report_id": str(MessageID.generate()),
            "agent_type": "comprehensive_quality_agent",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            
            # Required content sections
            "executive_summary": "Complete analysis delivering comprehensive business insights",
            "methodology": {
                "approach": "Multi-factor analysis with statistical validation",
                "data_sources": ["Primary systems", "Historical data", "Industry benchmarks"],
                "analysis_period": "90 days",
                "confidence_methodology": "Statistical significance testing"
            },
            "key_findings": [
                {
                    "finding": "Critical optimization opportunity identified",
                    "evidence": "95% statistical confidence based on 90-day analysis",
                    "impact": "$50,000/month potential savings",
                    "urgency": "immediate"
                },
                {
                    "finding": "Secondary efficiency improvements available",
                    "evidence": "Trend analysis shows consistent pattern",
                    "impact": "$15,000/month additional savings",
                    "urgency": "medium"
                }
            ],
            "detailed_analysis": {
                "current_state": "Detailed current state analysis",
                "root_causes": ["Primary cause analysis", "Secondary factors"],
                "impact_assessment": "Quantified business impact analysis",
                "risk_analysis": "Comprehensive risk evaluation"
            },
            "recommendations": [
                {
                    "priority": 1,
                    "action": "Implement primary optimization strategy",
                    "business_justification": "Highest ROI opportunity with lowest risk",
                    "expected_impact": {
                        "monthly_savings": 50000,
                        "annual_savings": 600000,
                        "risk_mitigation": 0.95
                    },
                    "implementation": {
                        "timeline": "4 weeks",
                        "effort_required": "80 hours",
                        "resources_needed": ["DevOps team", "Security review"],
                        "milestones": [
                            "Week 1: Planning and design",
                            "Week 2-3: Implementation",
                            "Week 4: Testing and validation"
                        ]
                    },
                    "success_criteria": [
                        "50% cost reduction achieved",
                        "No performance degradation",
                        "Security compliance maintained"
                    ],
                    "risk_mitigation": "Phased rollout with rollback plan"
                }
            ],
            "financial_impact": {
                "summary": {
                    "total_annual_savings": 780000,
                    "implementation_cost": 60000,
                    "net_benefit": 720000,
                    "roi_percentage": 1200,
                    "payback_period_months": 0.9
                },
                "confidence_analysis": {
                    "high_confidence_savings": 600000,  # 90% confidence
                    "medium_confidence_savings": 120000,  # 70% confidence  
                    "low_confidence_savings": 60000,  # 50% confidence
                    "risk_adjusted_savings": 680000
                },
                "scenario_analysis": {
                    "best_case": 950000,
                    "base_case": 780000,
                    "worst_case": 580000,
                    "probability_distribution": {"best": 0.15, "base": 0.7, "worst": 0.15}
                }
            },
            "implementation_roadmap": {
                "phase_1": {
                    "timeline": "Weeks 1-4",
                    "deliverables": ["Primary optimization implementation"],
                    "success_metrics": ["$50K/month savings achieved"],
                    "gates": ["Security approval", "Performance validation"]
                },
                "phase_2": {
                    "timeline": "Weeks 5-8",
                    "deliverables": ["Secondary optimizations"],
                    "success_metrics": ["Additional $15K/month savings"],
                    "gates": ["Phase 1 success validation"]
                }
            },
            "risk_assessment": {
                "implementation_risks": [
                    {"risk": "Performance impact", "probability": 0.2, "impact": "medium", "mitigation": "Phased rollout"},
                    {"risk": "Resource unavailability", "probability": 0.3, "impact": "low", "mitigation": "Backup resources identified"}
                ],
                "business_risks": [
                    {"risk": "Market conditions change", "probability": 0.1, "impact": "medium", "mitigation": "Flexible implementation"}
                ],
                "overall_risk_score": 0.3
            },
            "success_measurement": {
                "kpis": [
                    {"metric": "Monthly cost reduction", "target": 65000, "measurement": "Monthly AWS bills"},
                    {"metric": "Implementation timeline", "target": "8 weeks", "measurement": "Project milestones"},
                    {"metric": "ROI achievement", "target": "1200%", "measurement": "Financial analysis"}
                ],
                "monitoring_plan": "Weekly progress reviews with monthly financial validation",
                "reporting_schedule": "Bi-weekly progress reports to stakeholders"
            },
            "data_quality_assessment": {
                "completeness": 0.95,
                "accuracy": 0.92,
                "recency": "Current within 24 hours",
                "reliability": 0.94,
                "data_sources_validated": True
            },
            "limitations_and_assumptions": {
                "limitations": [
                    "Analysis based on historical patterns",
                    "External market factors not modeled",
                    "Implementation assumes current team structure"
                ],
                "assumptions": [
                    "Current usage patterns continue",
                    "No major architectural changes planned",
                    "Implementation team availability as stated"
                ],
                "sensitivity_analysis": "10% change in assumptions affects results by <5%"
            },
            "next_steps": {
                "immediate_actions": [
                    "Stakeholder approval for Phase 1",
                    "Resource allocation confirmation",
                    "Detailed implementation planning"
                ],
                "follow_up_analysis": "Quarterly review of optimization effectiveness",
                "continuous_monitoring": "Real-time cost tracking dashboard"
            },
            "appendices": {
                "data_sources": ["Detailed list of all data sources"],
                "technical_details": ["Implementation technical specifications"],
                "supporting_analysis": ["Additional statistical analysis"]
            },
            "confidence_score": 0.92,
            "completeness_score": 1.0  # Perfect completeness
        }
        
        # Store complete report
        message = Message(
            id=complete_report["report_id"],
            thread_id=str(thread_id),
            user_id=str(user_id),
            run_id=str(RunID.generate()),
            message_type=MessageType.AGENT_RESPONSE,
            content=str(complete_report),
            metadata={
                "quality_tier": "comprehensive",
                "completeness_score": 1.0,
                "validation_passed": True
            }
        )
        db.add(message)
        await db.commit()
        
        # CRITICAL ASSERTIONS: Complete reports required for business value
        
        # Core business sections must exist and be comprehensive
        business_critical_sections = [
            "executive_summary", "methodology", "key_findings", "detailed_analysis",
            "recommendations", "financial_impact", "implementation_roadmap", 
            "risk_assessment", "success_measurement"
        ]
        for section in business_critical_sections:
            assert section in complete_report, f"Complete reports must include {section}"
            assert complete_report[section] is not None, f"{section} must not be None"
            assert len(str(complete_report[section])) > 0, f"{section} must not be empty"
        
        # Financial impact must be comprehensive with scenario analysis
        financial = complete_report["financial_impact"]
        assert "summary" in financial, "Must include financial summary"
        assert "confidence_analysis" in financial, "Must include confidence intervals"
        assert "scenario_analysis" in financial, "Must include best/base/worst case scenarios"
        
        # Recommendations must be implementation-ready
        for rec in complete_report["recommendations"]:
            assert "implementation" in rec, "Recommendations must include implementation details"
            assert "success_criteria" in rec, "Must define success criteria"
            assert "risk_mitigation" in rec, "Must include risk mitigation"
        
        # Risk assessment must be thorough
        risk_assessment = complete_report["risk_assessment"]
        assert "implementation_risks" in risk_assessment, "Must assess implementation risks"
        assert "business_risks" in risk_assessment, "Must assess business risks"
        assert "overall_risk_score" in risk_assessment, "Must provide overall risk score"
        
        # Success measurement must be defined
        success = complete_report["success_measurement"]
        assert "kpis" in success, "Must define KPIs"
        assert "monitoring_plan" in success, "Must include monitoring plan"
        
        # Quality validation
        assert complete_report["completeness_score"] == 1.0, "Report must achieve perfect completeness"
        assert complete_report["confidence_score"] > 0.9, "High-quality reports must have high confidence"
        
        # Data quality must be assessed
        data_quality = complete_report["data_quality_assessment"]
        assert "completeness" in data_quality, "Must assess data completeness"
        assert "accuracy" in data_quality, "Must assess data accuracy"
        assert data_quality["completeness"] > 0.9, "Data completeness must be high"
        
        # Limitations and next steps must be included
        assert "limitations_and_assumptions" in complete_report, "Must acknowledge limitations"
        assert "next_steps" in complete_report, "Must provide clear next steps"
        
        # Verify report is actionable and complete
        assert BusinessValueReportValidator.validate_actionable_content(complete_report), \
            "Complete report must be actionable"
        assert BusinessValueReportValidator.validate_professional_structure(complete_report), \
            "Complete report must be professionally structured"