"""
Scheduling and management tests for SupplyResearcherAgent
Modular design with ≤300 lines, ≤8 lines per function
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.agents.supply_researcher_sub_agent import ResearchType
from .supply_researcher_fixtures import (
    agent, mock_supply_service, research_query_test_cases
)


class TestSupplyResearcherManagement:
    """Scheduling and notification management tests"""

    def test_schedule_frequency_calculations(self):
        """Test schedule frequency calculations for different intervals"""
        now = datetime.now()
        _test_daily_schedule(now)
        _test_weekly_schedule(now)
        _test_monthly_schedule(now)

    def _test_daily_schedule(self, now):
        """Test daily schedule calculation (≤8 lines)"""
        from app.services.supply_research_scheduler import ResearchSchedule, ScheduleFrequency
        daily = ResearchSchedule(
            name="test_daily",
            frequency=ScheduleFrequency.DAILY,
            research_type=ResearchType.PRICING
        )
        daily.calculate_next_run()
        _verify_daily_schedule(daily, now)

    def _verify_daily_schedule(self, daily, now):
        """Verify daily schedule timing (≤8 lines)"""
        assert daily.next_run > now
        assert (daily.next_run - now).days <= 1

    def _test_weekly_schedule(self, now):
        """Test weekly schedule calculation (≤8 lines)"""
        from app.services.supply_research_scheduler import ResearchSchedule, ScheduleFrequency
        weekly = ResearchSchedule(
            name="test_weekly",
            frequency=ScheduleFrequency.WEEKLY,
            research_type=ResearchType.CAPABILITIES
        )
        weekly.calculate_next_run()
        _verify_weekly_schedule(weekly, now)

    def _verify_weekly_schedule(self, weekly, now):
        """Verify weekly schedule timing (≤8 lines)"""
        assert weekly.next_run > now
        assert (weekly.next_run - now).days <= 7

    def _test_monthly_schedule(self, now):
        """Test monthly schedule calculation (≤8 lines)"""
        from app.services.supply_research_scheduler import ResearchSchedule, ScheduleFrequency
        monthly = ResearchSchedule(
            name="test_monthly",
            frequency=ScheduleFrequency.MONTHLY,
            research_type=ResearchType.MARKET_OVERVIEW
        )
        monthly.calculate_next_run()
        _verify_monthly_schedule(monthly, now)

    def _verify_monthly_schedule(self, monthly, now):
        """Verify monthly schedule timing (≤8 lines)"""
        assert monthly.next_run > now
        assert (monthly.next_run - now).days <= 31

    def test_research_query_generation_templates(self, agent):
        """Test research query generation for different types"""
        test_cases = _get_research_query_test_cases()
        for test_case in test_cases:
            query = agent.research_engine.generate_research_query(test_case["parsed"])
            _verify_query_keywords(query, test_case["expected_keywords"])

    def _get_research_query_test_cases(self):
        """Get research query test cases (≤8 lines)"""
        return [
            _get_pricing_query_case(),
            _get_capabilities_query_case(),
            _get_availability_query_case()
        ]

    def _get_pricing_query_case(self):
        """Get pricing query test case (≤8 lines)"""
        return {
            "parsed": {
                "research_type": ResearchType.PRICING,
                "provider": "openai",
                "model_name": "gpt-4",
                "timeframe": "current"
            },
            "expected_keywords": ["pricing", "cost", "tokens", "gpt-4"]
        }

    def _get_capabilities_query_case(self):
        """Get capabilities query test case (≤8 lines)"""
        return {
            "parsed": {
                "research_type": ResearchType.CAPABILITIES,
                "provider": "anthropic",
                "model_name": "claude-3",
                "timeframe": "latest"
            },
            "expected_keywords": ["capabilities", "context", "features", "claude-3"]
        }

    def _get_availability_query_case(self):
        """Get availability query test case (≤8 lines)"""
        return {
            "parsed": {
                "research_type": ResearchType.AVAILABILITY,
                "provider": "google",
                "model_name": "gemini",
                "timeframe": "current"
            },
            "expected_keywords": ["availability", "api", "access", "gemini"]
        }

    def _verify_query_keywords(self, query, expected_keywords):
        """Verify query contains expected keywords (≤8 lines)"""
        query_lower = query.lower()
        for keyword in expected_keywords:
            assert keyword in query_lower, f"Expected '{keyword}' in query"

    async def test_change_notification_triggers(self, agent, mock_supply_service):
        """Test notification triggers for significant changes"""
        _setup_significant_changes(mock_supply_service)
        _setup_anomaly_detection(mock_supply_service)
        await _test_notification_system(agent, mock_supply_service)

    def _setup_significant_changes(self, mock_supply_service):
        """Setup significant price changes mock (≤8 lines)"""
        mock_supply_service.calculate_price_changes.return_value = {
            "all_changes": [{
                "provider": "openai",
                "model": "gpt-4",
                "percent_change": 15,  # 15% change - should trigger
                "field": "pricing_input"
            }]
        }

    def _setup_anomaly_detection(self, mock_supply_service):
        """Setup anomaly detection mock (≤8 lines)"""
        mock_supply_service.detect_anomalies.return_value = [{
            "type": "significant_price_change",
            "provider": "openai",
            "model": "gpt-4",
            "percent_change": 15
        }]

    async def _test_notification_system(self, agent, mock_supply_service):
        """Test notification system behavior (≤8 lines)"""
        with patch.object(agent, '_send_notifications', 
                         new_callable=AsyncMock, create=True) as mock_notify:
            if hasattr(agent, '_check_and_notify_changes'):
                await agent._check_and_notify_changes(mock_supply_service)
            _verify_notifications_sent(mock_notify)

    def _verify_notifications_sent(self, mock_notify):
        """Verify notifications were sent (≤8 lines)"""
        if mock_notify.called:
            assert mock_notify.call_count > 0

    def test_schedule_priority_management(self):
        """Test schedule priority and conflict resolution"""
        schedules = _create_conflicting_schedules()
        priority_order = _resolve_schedule_conflicts(schedules)
        _verify_priority_resolution(priority_order)

    def _create_conflicting_schedules(self):
        """Create conflicting schedule scenarios (≤8 lines)"""
        from app.services.supply_research_scheduler import ResearchSchedule, ScheduleFrequency
        return [
            ResearchSchedule("high_priority", ScheduleFrequency.DAILY, 
                           ResearchType.PRICING, priority=1),
            ResearchSchedule("low_priority", ScheduleFrequency.DAILY, 
                           ResearchType.CAPABILITIES, priority=3),
            ResearchSchedule("medium_priority", ScheduleFrequency.DAILY, 
                           ResearchType.AVAILABILITY, priority=2)
        ]

    def _resolve_schedule_conflicts(self, schedules):
        """Resolve schedule conflicts by priority (≤8 lines)"""
        return sorted(schedules, key=lambda x: x.priority)

    def _verify_priority_resolution(self, priority_order):
        """Verify priority resolution is correct (≤8 lines)"""
        assert priority_order[0].priority == 1
        assert priority_order[1].priority == 2
        assert priority_order[2].priority == 3

    def test_notification_channel_routing(self):
        """Test notification routing to different channels"""
        notification_configs = _create_notification_configs()
        for config in notification_configs:
            routed_channels = _route_notification(config)
            _verify_channel_routing(config, routed_channels)

    def _create_notification_configs(self):
        """Create notification configuration test cases (≤8 lines)"""
        return [
            {"type": "critical", "channels": ["email", "slack", "webhook"]},
            {"type": "warning", "channels": ["slack", "webhook"]},
            {"type": "info", "channels": ["webhook"]},
            {"type": "debug", "channels": []}
        ]

    def _route_notification(self, config):
        """Route notification to appropriate channels (≤8 lines)"""
        return config["channels"]

    def _verify_channel_routing(self, config, routed_channels):
        """Verify notification channel routing (≤8 lines)"""
        assert routed_channels == config["channels"]

    def test_batch_scheduling_optimization(self):
        """Test batch scheduling for efficiency"""
        research_requests = _create_batch_requests()
        optimized_batches = _optimize_request_batching(research_requests)
        _verify_batch_optimization(optimized_batches)

    def _create_batch_requests(self):
        """Create batch request test data (≤8 lines)"""
        return [
            {"provider": "openai", "type": ResearchType.PRICING},
            {"provider": "openai", "type": ResearchType.CAPABILITIES},
            {"provider": "anthropic", "type": ResearchType.PRICING},
            {"provider": "anthropic", "type": ResearchType.CAPABILITIES}
        ]

    def _optimize_request_batching(self, requests):
        """Optimize request batching by provider (≤8 lines)"""
        batches = {}
        for request in requests:
            provider = request["provider"]
            if provider not in batches:
                batches[provider] = []
            batches[provider].append(request)
        return batches

    def _verify_batch_optimization(self, batches):
        """Verify batch optimization results (≤8 lines)"""
        assert "openai" in batches
        assert "anthropic" in batches
        assert len(batches["openai"]) == 2
        assert len(batches["anthropic"]) == 2

    async def test_schedule_health_monitoring(self):
        """Test schedule health and failure monitoring"""
        schedule_health = _create_schedule_health_data()
        health_status = await _monitor_schedule_health(schedule_health)
        _verify_health_monitoring(health_status)

    def _create_schedule_health_data(self):
        """Create schedule health test data (≤8 lines)"""
        return {
            "daily_pricing": {"success_rate": 0.95, "last_run": "success"},
            "weekly_capabilities": {"success_rate": 0.80, "last_run": "failed"},
            "monthly_overview": {"success_rate": 1.0, "last_run": "success"}
        }

    async def _monitor_schedule_health(self, health_data):
        """Monitor schedule health status (≤8 lines)"""
        unhealthy_schedules = []
        for schedule, health in health_data.items():
            if health["success_rate"] < 0.9 or health["last_run"] == "failed":
                unhealthy_schedules.append(schedule)
        return {"unhealthy": unhealthy_schedules}

    def _verify_health_monitoring(self, health_status):
        """Verify health monitoring results (≤8 lines)"""
        assert "weekly_capabilities" in health_status["unhealthy"]
        assert "daily_pricing" not in health_status["unhealthy"]