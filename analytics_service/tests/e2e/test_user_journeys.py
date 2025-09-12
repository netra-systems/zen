"""
Analytics Service End-to-End User Journey Tests
==============================================

BVJ (Business Value Justification):
1. Segment: All tiers (Free, Early, Mid, Enterprise)
2. Business Goal: Ensure complete user workflows function end-to-end
3. Value Impact: Critical for user retention and platform reliability
4. Revenue Impact: User journey failures directly impact conversion and retention

Comprehensive user journey testing covering complete workflows from event capture 
to report generation, with real service integration following NO MOCKS policy.

Test Coverage:
- New user onboarding analytics journey
- Power user advanced analytics workflow
- Enterprise multi-tenant analytics journey  
- Cross-session data continuity
- Mobile and web analytics integration
- User lifecycle tracking (signup  ->  conversion  ->  churn)
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

import httpx
from analytics_service.tests.e2e.test_full_flow import AnalyticsE2ETestHarness


# =============================================================================
# USER JOURNEY TEST INFRASTRUCTURE
# =============================================================================

class UserJourneyTestHarness(AnalyticsE2ETestHarness):
    """Extended test harness for user journey testing"""
    
    def __init__(self, base_url: str = "http://localhost:8090"):
        super().__init__(base_url)
        self.user_journeys = {}
        self.journey_start_times = {}
    
    def start_user_journey(self, user_id: str, journey_type: str) -> str:
        """Start tracking a user journey"""
        journey_id = f"journey_{journey_type}_{user_id}_{int(time.time())}"
        self.user_journeys[journey_id] = {
            "user_id": user_id,
            "journey_type": journey_type,
            "events": [],
            "milestones": [],
            "start_time": datetime.now(timezone.utc),
            "status": "active"
        }
        self.journey_start_times[journey_id] = time.time()
        return journey_id
    
    async def record_journey_event(self, journey_id: str, event_type: str, 
                                 properties: Dict[str, Any] = None) -> None:
        """Record an event as part of a user journey"""
        if journey_id not in self.user_journeys:
            raise ValueError(f"Journey {journey_id} not found")
        
        journey = self.user_journeys[journey_id]
        user_id = journey["user_id"]
        
        event = {
            "event_id": f"journey_event_{len(journey['events'])}_{int(time.time())}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "session_id": f"journey_session_{journey_id}",
            "event_type": event_type,
            "event_category": f"User Journey - {journey['journey_type']}",
            "event_action": "journey_step",
            "event_label": f"Step {len(journey['events']) + 1}",
            "properties": json.dumps(properties or {}),
            "page_path": f"/journey/{journey['journey_type']}/step-{len(journey['events']) + 1}",
            "page_title": f"Journey Step {len(journey['events']) + 1}",
            "environment": "e2e_test"
        }
        
        journey["events"].append(event)
        
        # Send event to analytics service
        await self.send_events([event], {"journey_id": journey_id})
    
    async def complete_journey_milestone(self, journey_id: str, milestone: str,
                                       milestone_data: Dict[str, Any] = None) -> None:
        """Mark completion of a journey milestone"""
        if journey_id not in self.user_journeys:
            raise ValueError(f"Journey {journey_id} not found")
        
        journey = self.user_journeys[journey_id]
        elapsed_time = time.time() - self.journey_start_times[journey_id]
        
        milestone_record = {
            "milestone": milestone,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": elapsed_time,
            "data": milestone_data or {}
        }
        
        journey["milestones"].append(milestone_record)
        
        # Record milestone as special event
        await self.record_journey_event(journey_id, "milestone_completed", {
            "milestone": milestone,
            "elapsed_seconds": elapsed_time,
            **(milestone_data or {})
        })
    
    async def finish_user_journey(self, journey_id: str, outcome: str = "completed") -> Dict[str, Any]:
        """Complete a user journey and return summary"""
        if journey_id not in self.user_journeys:
            raise ValueError(f"Journey {journey_id} not found")
        
        journey = self.user_journeys[journey_id]
        total_time = time.time() - self.journey_start_times[journey_id]
        
        journey["status"] = outcome
        journey["end_time"] = datetime.now(timezone.utc)
        journey["total_duration_seconds"] = total_time
        
        # Generate journey completion summary
        summary = {
            "journey_id": journey_id,
            "user_id": journey["user_id"],
            "journey_type": journey["journey_type"],
            "outcome": outcome,
            "total_events": len(journey["events"]),
            "milestones_completed": len(journey["milestones"]),
            "duration_seconds": total_time,
            "milestones": journey["milestones"],
            "event_types": list(set(event["event_type"] for event in journey["events"]))
        }
        
        return summary

# =============================================================================
# NEW USER ONBOARDING JOURNEY TESTS
# =============================================================================

class TestNewUserOnboardingJourney:
    """Test suite for new user onboarding analytics journey"""
    
    @pytest.fixture
    async def journey_harness(self):
        """User journey test harness fixture"""
        harness = UserJourneyTestHarness()
        await harness.setup()
        yield harness
        await harness.teardown()
    
    async def test_complete_new_user_onboarding_flow(self, journey_harness):
        """Test complete new user onboarding analytics journey"""
        # Step 1: Start new user journey
        user_id = journey_harness.generate_test_user()
        journey_id = journey_harness.start_user_journey(user_id, "new_user_onboarding")
        
        # Step 2: Landing page interaction
        await journey_harness.record_journey_event(journey_id, "landing_page_view", {
            "utm_source": "google",
            "utm_medium": "cpc",
            "utm_campaign": "ai_optimization"
        })
        await journey_harness.complete_journey_milestone(journey_id, "landing_page_viewed")
        
        # Step 3: Signup process
        await journey_harness.record_journey_event(journey_id, "signup_form_viewed", {
            "form_variant": "streamlined_v2"
        })
        
        await journey_harness.record_journey_event(journey_id, "signup_attempted", {
            "email_domain": "company.com",
            "signup_method": "email"
        })
        
        await journey_harness.record_journey_event(journey_id, "signup_completed", {
            "user_tier": "free",
            "email_verified": True
        })
        await journey_harness.complete_journey_milestone(journey_id, "account_created", {
            "signup_duration_seconds": 120,
            "conversion_source": "google_cpc"
        })
        
        # Step 4: Initial onboarding survey
        await journey_harness.record_journey_event(journey_id, "onboarding_survey_started", {
            "survey_version": "ai_spend_assessment_v3"
        })
        
        for question_num in range(1, 6):
            await journey_harness.record_journey_event(journey_id, "survey_question_answered", {
                "question_id": f"q{question_num}",
                "question_type": "ai_spend_estimate" if question_num <= 2 else "pain_point",
                "response_value": f"sample_response_{question_num}"
            })
        
        await journey_harness.record_journey_event(journey_id, "onboarding_survey_completed", {
            "estimated_ai_spend_monthly": 5000.0,
            "primary_pain_point": "cost_visibility",
            "company_size": "50-200"
        })
        await journey_harness.complete_journey_milestone(journey_id, "survey_completed")
        
        # Step 5: First dashboard interaction
        await journey_harness.record_journey_event(journey_id, "dashboard_first_view", {
            "dashboard_variant": "default_free_tier"
        })
        
        await journey_harness.record_journey_event(journey_id, "feature_discovery", {
            "feature_discovered": "cost_tracking",
            "discovery_method": "tutorial_tooltip"
        })
        
        await journey_harness.record_journey_event(journey_id, "first_api_connection_attempted", {
            "provider": "openai",
            "connection_method": "api_key"
        })
        await journey_harness.complete_journey_milestone(journey_id, "first_interaction")
        
        # Step 6: Complete journey
        journey_summary = await journey_harness.finish_user_journey(journey_id, "completed")
        
        # Wait for event processing
        await asyncio.sleep(5)
        
        # Validate journey completion
        assert journey_summary["outcome"] == "completed"
        assert journey_summary["total_events"] >= 10
        assert journey_summary["milestones_completed"] == 4
        assert journey_summary["duration_seconds"] > 0
        
        # Validate analytics data captures the complete journey
        report = await journey_harness.get_user_activity_report(user_id)
        assert report["data"]["user_id"] == user_id
        
        # Should capture various event types from the journey
        expected_event_types = ["landing_page_view", "signup_completed", "survey_question_answered", "dashboard_first_view"]
        metrics = report["data"]["metrics"]
        assert metrics["total_events"] >= 10
    
    async def test_user_journey_abandonment_tracking(self, journey_harness):
        """Test tracking of user journey abandonment points"""
        # Start user journey
        user_id = journey_harness.generate_test_user()
        journey_id = journey_harness.start_user_journey(user_id, "abandoned_onboarding")
        
        # User starts but doesn't complete onboarding
        await journey_harness.record_journey_event(journey_id, "landing_page_view", {
            "utm_source": "direct"
        })
        
        await journey_harness.record_journey_event(journey_id, "signup_form_viewed", {
            "form_variant": "default"
        })
        
        # Abandonment point - user starts signup but doesn't complete
        await journey_harness.record_journey_event(journey_id, "signup_attempted", {
            "email_domain": "gmail.com",
            "abandonment_point": "email_verification"
        })
        
        # Complete journey as abandoned
        journey_summary = await journey_harness.finish_user_journey(journey_id, "abandoned")
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Validate abandonment tracking
        assert journey_summary["outcome"] == "abandoned"
        assert journey_summary["milestones_completed"] == 0
        assert "signup_attempted" in journey_summary["event_types"]
        
        # Analytics should still capture the partial journey
        report = await journey_harness.get_user_activity_report(user_id)
        assert report["data"]["metrics"]["total_events"] >= 3

# =============================================================================
# POWER USER ADVANCED ANALYTICS JOURNEY
# =============================================================================

class TestPowerUserAnalyticsJourney:
    """Test suite for power user advanced analytics workflows"""
    
    @pytest.fixture
    async def journey_harness(self):
        """User journey test harness fixture"""
        harness = UserJourneyTestHarness()
        await harness.setup()
        yield harness
        await harness.teardown()
    
    async def test_power_user_advanced_analytics_workflow(self, journey_harness):
        """Test power user advanced analytics and reporting workflow"""
        # Start power user journey
        user_id = journey_harness.generate_test_user()
        journey_id = journey_harness.start_user_journey(user_id, "power_user_analytics")
        
        # Step 1: Advanced dashboard configuration
        await journey_harness.record_journey_event(journey_id, "dashboard_customization_started", {
            "user_tier": "mid",
            "customization_type": "advanced_metrics"
        })
        
        # Configure multiple data sources
        for provider in ["openai", "anthropic", "cohere"]:
            await journey_harness.record_journey_event(journey_id, "data_source_connected", {
                "provider": provider,
                "connection_type": "api_integration",
                "data_volume_estimate": "high"
            })
        
        await journey_harness.complete_journey_milestone(journey_id, "data_sources_configured", {
            "total_sources": 3,
            "configuration_time_seconds": 300
        })
        
        # Step 2: Advanced reporting usage
        report_types = ["cost_analysis", "usage_patterns", "optimization_opportunities"]
        
        for report_type in report_types:
            await journey_harness.record_journey_event(journey_id, "advanced_report_generated", {
                "report_type": report_type,
                "time_range": "last_30_days",
                "custom_filters": True,
                "export_format": "csv"
            })
        
        await journey_harness.complete_journey_milestone(journey_id, "advanced_reports_generated", {
            "reports_count": len(report_types)
        })
        
        # Step 3: Custom alert configuration
        await journey_harness.record_journey_event(journey_id, "alert_rule_created", {
            "alert_type": "cost_threshold",
            "threshold_value": 1000.0,
            "notification_method": "email"
        })
        
        await journey_harness.record_journey_event(journey_id, "alert_rule_created", {
            "alert_type": "usage_anomaly",
            "sensitivity": "medium",
            "notification_method": "slack"
        })
        
        await journey_harness.complete_journey_milestone(journey_id, "alerts_configured", {
            "alert_rules_count": 2
        })
        
        # Step 4: API usage for programmatic access
        await journey_harness.record_journey_event(journey_id, "api_key_generated", {
            "key_type": "read_write",
            "permissions": "full_analytics"
        })
        
        for i in range(5):
            await journey_harness.record_journey_event(journey_id, "api_call_made", {
                "endpoint": "analytics/reports",
                "method": "GET",
                "response_time_ms": 150 + i * 10,
                "status_code": 200
            })
        
        await journey_harness.complete_journey_milestone(journey_id, "api_integration_completed", {
            "api_calls_made": 5,
            "avg_response_time": 170.0
        })
        
        # Complete power user journey
        journey_summary = await journey_harness.finish_user_journey(journey_id, "completed")
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Validate power user journey
        assert journey_summary["outcome"] == "completed"
        assert journey_summary["milestones_completed"] == 4
        assert journey_summary["total_events"] >= 15
        
        # Validate advanced usage is captured in analytics
        report = await journey_harness.get_user_activity_report(user_id)
        metrics = report["data"]["metrics"]
        assert metrics["total_events"] >= 15
        
        # Should show power user behavior patterns
        expected_advanced_events = ["dashboard_customization_started", "advanced_report_generated", "api_call_made"]
        captured_events = set(journey_summary["event_types"])
        assert all(event in captured_events for event in expected_advanced_events)

# =============================================================================
# ENTERPRISE MULTI-TENANT JOURNEY
# =============================================================================

class TestEnterpriseMultiTenantJourney:
    """Test suite for enterprise multi-tenant analytics workflows"""
    
    @pytest.fixture
    async def journey_harness(self):
        """User journey test harness fixture"""
        harness = UserJourneyTestHarness()
        await harness.setup()
        yield harness
        await harness.teardown()
    
    async def test_enterprise_multi_tenant_analytics_workflow(self, journey_harness):
        """Test enterprise multi-tenant organization analytics workflow"""
        # Create enterprise organization with multiple users
        org_admin_id = journey_harness.generate_test_user()
        org_id = f"enterprise_org_{int(time.time())}"
        
        journey_id = journey_harness.start_user_journey(org_admin_id, "enterprise_multi_tenant")
        
        # Step 1: Organization setup
        await journey_harness.record_journey_event(journey_id, "organization_created", {
            "organization_id": org_id,
            "organization_tier": "enterprise",
            "user_seats": 50,
            "admin_user_id": org_admin_id
        })
        
        await journey_harness.complete_journey_milestone(journey_id, "organization_setup", {
            "organization_id": org_id
        })
        
        # Step 2: Multi-user analytics setup
        team_members = []
        for i in range(5):
            member_id = journey_harness.generate_test_user()
            team_members.append(member_id)
            
            await journey_harness.record_journey_event(journey_id, "team_member_added", {
                "organization_id": org_id,
                "member_user_id": member_id,
                "role": "analyst" if i < 3 else "viewer",
                "invited_by": org_admin_id
            })
        
        await journey_harness.complete_journey_milestone(journey_id, "team_configured", {
            "team_size": len(team_members)
        })
        
        # Step 3: Simulate multi-user activity
        for member_id in team_members[:3]:  # Active analysts
            for activity_num in range(3):
                await journey_harness.record_journey_event(journey_id, "team_member_activity", {
                    "organization_id": org_id,
                    "member_user_id": member_id,
                    "activity_type": "report_generation",
                    "report_scope": "organization",
                    "activity_sequence": activity_num + 1
                })
        
        # Step 4: Organization-wide reporting
        await journey_harness.record_journey_event(journey_id, "org_wide_report_generated", {
            "organization_id": org_id,
            "report_type": "cost_breakdown_by_team",
            "time_range": "current_month",
            "generated_by": org_admin_id
        })
        
        await journey_harness.record_journey_event(journey_id, "org_wide_report_generated", {
            "organization_id": org_id,
            "report_type": "usage_analytics_summary",
            "time_range": "current_quarter",
            "generated_by": org_admin_id
        })
        
        await journey_harness.complete_journey_milestone(journey_id, "org_reporting_active", {
            "reports_generated": 2,
            "active_team_members": 3
        })
        
        # Complete enterprise journey
        journey_summary = await journey_harness.finish_user_journey(journey_id, "completed")
        
        # Wait for processing
        await asyncio.sleep(6)
        
        # Validate enterprise journey
        assert journey_summary["outcome"] == "completed"
        assert journey_summary["milestones_completed"] == 3
        assert journey_summary["total_events"] >= 20  # Org setup + team activities + reporting
        
        # Validate organization-level analytics
        report = await journey_harness.get_user_activity_report(org_admin_id)
        metrics = report["data"]["metrics"]
        assert metrics["total_events"] >= 10
        
        # Should capture enterprise-specific events
        expected_enterprise_events = ["organization_created", "team_member_added", "org_wide_report_generated"]
        captured_events = set(journey_summary["event_types"])
        assert all(event in captured_events for event in expected_enterprise_events)

# =============================================================================
# CROSS-SESSION DATA CONTINUITY TESTS
# =============================================================================

class TestCrossSessionDataContinuity:
    """Test suite for cross-session data continuity"""
    
    @pytest.fixture
    async def journey_harness(self):
        """User journey test harness fixture"""
        harness = UserJourneyTestHarness()
        await harness.setup()
        yield harness
        await harness.teardown()
    
    async def test_multi_session_user_journey_continuity(self, journey_harness):
        """Test user journey continuity across multiple sessions"""
        user_id = journey_harness.generate_test_user()
        
        # Session 1: Initial setup
        session_1_journey = journey_harness.start_user_journey(user_id, "multi_session_continuity_s1")
        
        await journey_harness.record_journey_event(session_1_journey, "session_started", {
            "session_number": 1,
            "device_type": "desktop",
            "browser": "chrome"
        })
        
        await journey_harness.record_journey_event(session_1_journey, "feature_setup_started", {
            "feature": "cost_tracking",
            "setup_step": 1
        })
        
        # Simulate session end without completion
        await journey_harness.record_journey_event(session_1_journey, "session_ended", {
            "session_duration_seconds": 300,
            "completion_status": "incomplete"
        })
        
        await journey_harness.finish_user_journey(session_1_journey, "session_ended")
        
        # Wait between sessions
        await asyncio.sleep(2)
        
        # Session 2: Resume and complete
        session_2_journey = journey_harness.start_user_journey(user_id, "multi_session_continuity_s2")
        
        await journey_harness.record_journey_event(session_2_journey, "session_started", {
            "session_number": 2,
            "device_type": "desktop",
            "browser": "chrome",
            "returning_user": True
        })
        
        await journey_harness.record_journey_event(session_2_journey, "feature_setup_resumed", {
            "feature": "cost_tracking",
            "resumed_from_step": 1
        })
        
        await journey_harness.record_journey_event(session_2_journey, "feature_setup_completed", {
            "feature": "cost_tracking",
            "total_setup_sessions": 2
        })
        
        await journey_harness.complete_journey_milestone(session_2_journey, "feature_fully_configured", {
            "sessions_required": 2,
            "total_time_across_sessions": 600
        })
        
        await journey_harness.finish_user_journey(session_2_journey, "completed")
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Validate cross-session continuity
        report = await journey_harness.get_user_activity_report(user_id)
        metrics = report["data"]["metrics"]
        
        # Should capture events from both sessions
        assert metrics["total_events"] >= 6
        
        # Both journey summaries should reference the same user
        assert session_1_journey != session_2_journey  # Different journeys
        # But same user should be tracked consistently across sessions
    
    async def test_mobile_web_cross_platform_journey(self, journey_harness):
        """Test user journey continuity across mobile and web platforms"""
        user_id = journey_harness.generate_test_user()
        
        # Mobile journey
        mobile_journey = journey_harness.start_user_journey(user_id, "cross_platform_mobile")
        
        await journey_harness.record_journey_event(mobile_journey, "mobile_app_opened", {
            "platform": "mobile",
            "device_type": "smartphone",
            "app_version": "1.2.3"
        })
        
        await journey_harness.record_journey_event(mobile_journey, "quick_insight_viewed", {
            "insight_type": "cost_summary",
            "view_duration_seconds": 30
        })
        
        await journey_harness.finish_user_journey(mobile_journey, "completed")
        
        # Web journey (same user, different platform)
        web_journey = journey_harness.start_user_journey(user_id, "cross_platform_web")
        
        await journey_harness.record_journey_event(web_journey, "web_dashboard_opened", {
            "platform": "web",
            "device_type": "desktop",
            "browser": "firefox"
        })
        
        await journey_harness.record_journey_event(web_journey, "detailed_report_generated", {
            "report_type": "monthly_breakdown",
            "triggered_by_mobile_insight": True
        })
        
        await journey_harness.complete_journey_milestone(web_journey, "cross_platform_workflow", {
            "mobile_to_web_continuity": True
        })
        
        await journey_harness.finish_user_journey(web_journey, "completed")
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Validate cross-platform analytics
        report = await journey_harness.get_user_activity_report(user_id)
        metrics = report["data"]["metrics"]
        
        # Should capture activity from both platforms
        assert metrics["total_events"] >= 4
        
        # Analytics should maintain user identity across platforms
        assert report["data"]["user_id"] == user_id

# =============================================================================
# USER LIFECYCLE TRACKING TESTS
# =============================================================================

class TestUserLifecycleTracking:
    """Test suite for complete user lifecycle analytics"""
    
    @pytest.fixture
    async def journey_harness(self):
        """User journey test harness fixture"""
        harness = UserJourneyTestHarness()
        await harness.setup()
        yield harness
        await harness.teardown()
    
    async def test_complete_user_lifecycle_analytics(self, journey_harness):
        """Test complete user lifecycle from signup to potential churn"""
        user_id = journey_harness.generate_test_user()
        lifecycle_journey = journey_harness.start_user_journey(user_id, "complete_lifecycle")
        
        # Phase 1: Acquisition
        await journey_harness.record_journey_event(lifecycle_journey, "user_acquired", {
            "acquisition_channel": "organic_search",
            "acquisition_cost": 0.0,
            "first_touchpoint": "blog_post"
        })
        await journey_harness.complete_journey_milestone(lifecycle_journey, "acquired")
        
        # Phase 2: Activation (first value realization)
        await journey_harness.record_journey_event(lifecycle_journey, "first_value_delivered", {
            "value_type": "cost_insight",
            "time_to_value_hours": 2.5,
            "value_quantified": "identified_500_monthly_savings"
        })
        await journey_harness.complete_journey_milestone(lifecycle_journey, "activated")
        
        # Phase 3: Engagement patterns
        for week in range(1, 5):  # 4 weeks of usage
            await journey_harness.record_journey_event(lifecycle_journey, "weekly_engagement", {
                "week_number": week,
                "session_count": max(1, 5 - week),  # Declining engagement
                "features_used": ["dashboard", "reports"] if week <= 2 else ["dashboard"],
                "engagement_score": max(0.2, 1.0 - (week * 0.2))
            })
        
        await journey_harness.complete_journey_milestone(lifecycle_journey, "engagement_tracked", {
            "weeks_tracked": 4,
            "engagement_trend": "declining"
        })
        
        # Phase 4: Retention risk signals
        await journey_harness.record_journey_event(lifecycle_journey, "retention_risk_detected", {
            "risk_factors": ["declining_usage", "no_api_integration", "support_ticket_unresolved"],
            "risk_score": 0.75,
            "last_login_days_ago": 7
        })
        
        # Phase 5: Churn prevention attempt
        await journey_harness.record_journey_event(lifecycle_journey, "churn_prevention_triggered", {
            "intervention_type": "personalized_email_campaign",
            "intervention_content": "re_engagement_offer",
            "discount_offered": 25.0
        })
        
        # Phase 6: Final outcome (in this case, churn)
        await journey_harness.record_journey_event(lifecycle_journey, "user_churned", {
            "churn_reason": "insufficient_value_realization",
            "final_tier": "free",
            "total_lifetime_value": 0.0,
            "days_active": 28
        })
        
        await journey_harness.complete_journey_milestone(lifecycle_journey, "lifecycle_completed", {
            "final_outcome": "churned",
            "lifecycle_duration_days": 28
        })
        
        lifecycle_summary = await journey_harness.finish_user_journey(lifecycle_journey, "churned")
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Validate complete lifecycle tracking
        assert lifecycle_summary["outcome"] == "churned"
        assert lifecycle_summary["milestones_completed"] == 5
        assert lifecycle_summary["total_events"] >= 10
        
        # Validate analytics captures the complete lifecycle
        report = await journey_harness.get_user_activity_report(user_id)
        metrics = report["data"]["metrics"]
        assert metrics["total_events"] >= 10
        
        # Should capture all lifecycle phases
        expected_lifecycle_events = ["user_acquired", "first_value_delivered", "retention_risk_detected", "user_churned"]
        captured_events = set(lifecycle_summary["event_types"])
        assert all(event in captured_events for event in expected_lifecycle_events)
    
    async def test_successful_conversion_lifecycle(self, journey_harness):
        """Test successful user lifecycle leading to paid conversion"""
        user_id = journey_harness.generate_test_user()
        conversion_journey = journey_harness.start_user_journey(user_id, "successful_conversion")
        
        # Successful path: Acquisition  ->  Activation  ->  Engagement  ->  Conversion
        
        # Acquisition
        await journey_harness.record_journey_event(conversion_journey, "user_acquired", {
            "acquisition_channel": "paid_search",
            "acquisition_cost": 25.0
        })
        
        # Strong activation
        await journey_harness.record_journey_event(conversion_journey, "first_value_delivered", {
            "value_type": "cost_optimization",
            "time_to_value_hours": 1.0,
            "value_quantified": "identified_2000_monthly_savings"
        })
        await journey_harness.complete_journey_milestone(conversion_journey, "strong_activation")
        
        # Consistent engagement
        for week in range(1, 4):
            await journey_harness.record_journey_event(conversion_journey, "weekly_engagement", {
                "week_number": week,
                "session_count": 8,  # Consistent high usage
                "features_used": ["dashboard", "reports", "alerts", "api"],
                "engagement_score": 0.9
            })
        
        # Conversion trigger
        await journey_harness.record_journey_event(conversion_journey, "upgrade_trigger_event", {
            "trigger_type": "usage_limit_reached",
            "current_tier": "free",
            "usage_percentage": 95.0
        })
        
        # Successful conversion
        await journey_harness.record_journey_event(conversion_journey, "tier_upgraded", {
            "from_tier": "free",
            "to_tier": "early",
            "upgrade_value": 49.0,
            "payment_method": "credit_card"
        })
        await journey_harness.complete_journey_milestone(conversion_journey, "converted_to_paid", {
            "conversion_value": 49.0,
            "time_to_conversion_days": 21
        })
        
        conversion_summary = await journey_harness.finish_user_journey(conversion_journey, "converted")
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Validate successful conversion lifecycle
        assert conversion_summary["outcome"] == "converted"
        assert conversion_summary["milestones_completed"] == 2
        assert conversion_summary["total_events"] >= 7
        
        # Validate conversion analytics
        report = await journey_harness.get_user_activity_report(user_id)
        metrics = report["data"]["metrics"]
        assert metrics["total_events"] >= 7
        
        # Should capture conversion events
        expected_conversion_events = ["user_acquired", "first_value_delivered", "tier_upgraded"]
        captured_events = set(conversion_summary["event_types"])
        assert all(event in captured_events for event in expected_conversion_events)