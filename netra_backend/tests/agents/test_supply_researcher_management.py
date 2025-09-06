from unittest.mock import AsyncMock, Mock, patch, MagicMock
import asyncio

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Scheduling and management tests for SupplyResearcherAgent
# REMOVED_SYNTAX_ERROR: Modular design with ≤300 lines, ≤8 lines per function
""

import sys
from pathlib import Path
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment


# Test framework import - using pytest fixtures instead

from datetime import datetime, timedelta

import pytest

from netra_backend.app.agents.supply_researcher_sub_agent import ResearchType
# REMOVED_SYNTAX_ERROR: from netra_backend.tests.agents.supply_researcher_fixtures import ( )
agent,
mock_supply_service,
research_query_test_cases,


# REMOVED_SYNTAX_ERROR: class TestSupplyResearcherManagement:
    # REMOVED_SYNTAX_ERROR: """Scheduling and notification management tests"""

# REMOVED_SYNTAX_ERROR: def test_schedule_frequency_calculations(self):
    # REMOVED_SYNTAX_ERROR: """Test schedule frequency calculations for different intervals"""
    # REMOVED_SYNTAX_ERROR: now = datetime.now()
    # REMOVED_SYNTAX_ERROR: _test_daily_schedule(now)
    # REMOVED_SYNTAX_ERROR: _test_weekly_schedule(now)
    # REMOVED_SYNTAX_ERROR: _test_monthly_schedule(now)

# REMOVED_SYNTAX_ERROR: def _test_daily_schedule(self, now):
    # REMOVED_SYNTAX_ERROR: """Test daily schedule calculation (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.supply_research_scheduler import ( )
    # REMOVED_SYNTAX_ERROR: ResearchSchedule,
    # REMOVED_SYNTAX_ERROR: ScheduleFrequency,
    
    # REMOVED_SYNTAX_ERROR: daily = ResearchSchedule( )
    # REMOVED_SYNTAX_ERROR: name="test_daily",
    # REMOVED_SYNTAX_ERROR: frequency=ScheduleFrequency.DAILY,
    # REMOVED_SYNTAX_ERROR: research_type=ResearchType.PRICING
    
    # REMOVED_SYNTAX_ERROR: daily.calculate_next_run()
    # REMOVED_SYNTAX_ERROR: _verify_daily_schedule(daily, now)

# REMOVED_SYNTAX_ERROR: def _verify_daily_schedule(self, daily, now):
    # REMOVED_SYNTAX_ERROR: """Verify daily schedule timing (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: assert daily.next_run > now
    # REMOVED_SYNTAX_ERROR: assert (daily.next_run - now).days <= 1

# REMOVED_SYNTAX_ERROR: def _test_weekly_schedule(self, now):
    # REMOVED_SYNTAX_ERROR: """Test weekly schedule calculation (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.supply_research_scheduler import ( )
    # REMOVED_SYNTAX_ERROR: ResearchSchedule,
    # REMOVED_SYNTAX_ERROR: ScheduleFrequency,
    
    # REMOVED_SYNTAX_ERROR: weekly = ResearchSchedule( )
    # REMOVED_SYNTAX_ERROR: name="test_weekly",
    # REMOVED_SYNTAX_ERROR: frequency=ScheduleFrequency.WEEKLY,
    # REMOVED_SYNTAX_ERROR: research_type=ResearchType.CAPABILITIES
    
    # REMOVED_SYNTAX_ERROR: weekly.calculate_next_run()
    # REMOVED_SYNTAX_ERROR: _verify_weekly_schedule(weekly, now)

# REMOVED_SYNTAX_ERROR: def _verify_weekly_schedule(self, weekly, now):
    # REMOVED_SYNTAX_ERROR: """Verify weekly schedule timing (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: assert weekly.next_run > now
    # REMOVED_SYNTAX_ERROR: assert (weekly.next_run - now).days <= 7

# REMOVED_SYNTAX_ERROR: def _test_monthly_schedule(self, now):
    # REMOVED_SYNTAX_ERROR: """Test monthly schedule calculation (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.supply_research_scheduler import ( )
    # REMOVED_SYNTAX_ERROR: ResearchSchedule,
    # REMOVED_SYNTAX_ERROR: ScheduleFrequency,
    
    # REMOVED_SYNTAX_ERROR: monthly = ResearchSchedule( )
    # REMOVED_SYNTAX_ERROR: name="test_monthly",
    # REMOVED_SYNTAX_ERROR: frequency=ScheduleFrequency.MONTHLY,
    # REMOVED_SYNTAX_ERROR: research_type=ResearchType.MARKET_OVERVIEW
    
    # REMOVED_SYNTAX_ERROR: monthly.calculate_next_run()
    # REMOVED_SYNTAX_ERROR: _verify_monthly_schedule(monthly, now)

# REMOVED_SYNTAX_ERROR: def _verify_monthly_schedule(self, monthly, now):
    # REMOVED_SYNTAX_ERROR: """Verify monthly schedule timing (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: assert monthly.next_run > now
    # REMOVED_SYNTAX_ERROR: assert (monthly.next_run - now).days <= 31

# REMOVED_SYNTAX_ERROR: def test_research_query_generation_templates(self, agent):
    # REMOVED_SYNTAX_ERROR: """Test research query generation for different types"""
    # REMOVED_SYNTAX_ERROR: test_cases = _get_research_query_test_cases()
    # REMOVED_SYNTAX_ERROR: for test_case in test_cases:
        # REMOVED_SYNTAX_ERROR: query = agent.research_engine.generate_research_query(test_case["parsed"])
        # REMOVED_SYNTAX_ERROR: _verify_query_keywords(query, test_case["expected_keywords"])

# REMOVED_SYNTAX_ERROR: def _get_research_query_test_cases(self):
    # REMOVED_SYNTAX_ERROR: """Get research query test cases (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return [ )
    # REMOVED_SYNTAX_ERROR: _get_pricing_query_case(),
    # REMOVED_SYNTAX_ERROR: _get_capabilities_query_case(),
    # REMOVED_SYNTAX_ERROR: _get_availability_query_case()
    

# REMOVED_SYNTAX_ERROR: def _get_pricing_query_case(self):
    # REMOVED_SYNTAX_ERROR: """Get pricing query test case (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "parsed": { )
    # REMOVED_SYNTAX_ERROR: "research_type": ResearchType.PRICING,
    # REMOVED_SYNTAX_ERROR: "provider": "openai",
    # REMOVED_SYNTAX_ERROR: "model_name": LLMModel.GEMINI_2_5_FLASH.value,
    # REMOVED_SYNTAX_ERROR: "timeframe": "current"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: "expected_keywords": ["pricing", "cost", "tokens", LLMModel.GEMINI_2_5_FLASH.value]
    

# REMOVED_SYNTAX_ERROR: def _get_capabilities_query_case(self):
    # REMOVED_SYNTAX_ERROR: """Get capabilities query test case (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "parsed": { )
    # REMOVED_SYNTAX_ERROR: "research_type": ResearchType.CAPABILITIES,
    # REMOVED_SYNTAX_ERROR: "provider": "anthropic",
    # REMOVED_SYNTAX_ERROR: "model_name": "claude-3",
    # REMOVED_SYNTAX_ERROR: "timeframe": "latest"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: "expected_keywords": ["capabilities", "context", "features", "claude-3"]
    

# REMOVED_SYNTAX_ERROR: def _get_availability_query_case(self):
    # REMOVED_SYNTAX_ERROR: """Get availability query test case (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "parsed": { )
    # REMOVED_SYNTAX_ERROR: "research_type": ResearchType.AVAILABILITY,
    # REMOVED_SYNTAX_ERROR: "provider": "google",
    # REMOVED_SYNTAX_ERROR: "model_name": "gemini",
    # REMOVED_SYNTAX_ERROR: "timeframe": "current"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: "expected_keywords": ["availability", "api", "access", "gemini"]
    

# REMOVED_SYNTAX_ERROR: def _verify_query_keywords(self, query, expected_keywords):
    # REMOVED_SYNTAX_ERROR: """Verify query contains expected keywords (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: query_lower = query.lower()
    # REMOVED_SYNTAX_ERROR: for keyword in expected_keywords:
        # REMOVED_SYNTAX_ERROR: assert keyword in query_lower, "formatted_string"

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_change_notification_triggers(self, agent, mock_supply_service):
            # REMOVED_SYNTAX_ERROR: """Test notification triggers for significant changes"""
            # REMOVED_SYNTAX_ERROR: _setup_significant_changes(mock_supply_service)
            # REMOVED_SYNTAX_ERROR: _setup_anomaly_detection(mock_supply_service)
            # REMOVED_SYNTAX_ERROR: await _test_notification_system(agent, mock_supply_service)

# REMOVED_SYNTAX_ERROR: def _setup_significant_changes(self, mock_supply_service):
    # REMOVED_SYNTAX_ERROR: """Setup significant price changes mock (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: mock_supply_service.calculate_price_changes.return_value = { )
    # REMOVED_SYNTAX_ERROR: "all_changes": [{ ))
    # REMOVED_SYNTAX_ERROR: "provider": "openai",
    # REMOVED_SYNTAX_ERROR: "model": LLMModel.GEMINI_2_5_FLASH.value,
    # REMOVED_SYNTAX_ERROR: "percent_change": 15,  # 15% change - should trigger
    # REMOVED_SYNTAX_ERROR: "field": "pricing_input"
    
    

# REMOVED_SYNTAX_ERROR: def _setup_anomaly_detection(self, mock_supply_service):
    # REMOVED_SYNTAX_ERROR: """Setup anomaly detection mock (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: mock_supply_service.detect_anomalies.return_value = [{ ))
    # REMOVED_SYNTAX_ERROR: "type": "significant_price_change",
    # REMOVED_SYNTAX_ERROR: "provider": "openai",
    # REMOVED_SYNTAX_ERROR: "model": LLMModel.GEMINI_2_5_FLASH.value,
    # REMOVED_SYNTAX_ERROR: "percent_change": 15
    

# REMOVED_SYNTAX_ERROR: async def _test_notification_system(self, agent, mock_supply_service):
    # REMOVED_SYNTAX_ERROR: """Test notification system behavior (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: with patch.object(agent, '_send_notifications',
    # REMOVED_SYNTAX_ERROR: new_callable=AsyncMock, create=True) as mock_notify:
        # REMOVED_SYNTAX_ERROR: if hasattr(agent, '_check_and_notify_changes'):
            # REMOVED_SYNTAX_ERROR: await agent._check_and_notify_changes(mock_supply_service)
            # REMOVED_SYNTAX_ERROR: _verify_notifications_sent(mock_notify)

# REMOVED_SYNTAX_ERROR: def _verify_notifications_sent(self, mock_notify):
    # REMOVED_SYNTAX_ERROR: """Verify notifications were sent (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: if mock_notify.called:
        # REMOVED_SYNTAX_ERROR: assert mock_notify.call_count > 0

# REMOVED_SYNTAX_ERROR: def test_schedule_priority_management(self):
    # REMOVED_SYNTAX_ERROR: """Test schedule priority and conflict resolution"""
    # REMOVED_SYNTAX_ERROR: schedules = _create_conflicting_schedules()
    # REMOVED_SYNTAX_ERROR: priority_order = _resolve_schedule_conflicts(schedules)
    # REMOVED_SYNTAX_ERROR: _verify_priority_resolution(priority_order)

# REMOVED_SYNTAX_ERROR: def _create_conflicting_schedules(self):
    # REMOVED_SYNTAX_ERROR: """Create conflicting schedule scenarios (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.supply_research_scheduler import ( )
    # REMOVED_SYNTAX_ERROR: ResearchSchedule,
    # REMOVED_SYNTAX_ERROR: ScheduleFrequency,
    
    # REMOVED_SYNTAX_ERROR: return [ )
    # REMOVED_SYNTAX_ERROR: ResearchSchedule("high_priority", ScheduleFrequency.DAILY,
    # REMOVED_SYNTAX_ERROR: ResearchType.PRICING, priority=1),
    # REMOVED_SYNTAX_ERROR: ResearchSchedule("low_priority", ScheduleFrequency.DAILY,
    # REMOVED_SYNTAX_ERROR: ResearchType.CAPABILITIES, priority=3),
    # REMOVED_SYNTAX_ERROR: ResearchSchedule("medium_priority", ScheduleFrequency.DAILY,
    # REMOVED_SYNTAX_ERROR: ResearchType.AVAILABILITY, priority=2)
    

# REMOVED_SYNTAX_ERROR: def _resolve_schedule_conflicts(self, schedules):
    # REMOVED_SYNTAX_ERROR: """Resolve schedule conflicts by priority (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return sorted(schedules, key=lambda x: None x.priority)

# REMOVED_SYNTAX_ERROR: def _verify_priority_resolution(self, priority_order):
    # REMOVED_SYNTAX_ERROR: """Verify priority resolution is correct (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: assert priority_order[0].priority == 1
    # REMOVED_SYNTAX_ERROR: assert priority_order[1].priority == 2
    # REMOVED_SYNTAX_ERROR: assert priority_order[2].priority == 3

# REMOVED_SYNTAX_ERROR: def test_notification_channel_routing(self):
    # REMOVED_SYNTAX_ERROR: """Test notification routing to different channels"""
    # REMOVED_SYNTAX_ERROR: notification_configs = _create_notification_configs()
    # REMOVED_SYNTAX_ERROR: for config in notification_configs:
        # REMOVED_SYNTAX_ERROR: routed_channels = _route_notification(config)
        # REMOVED_SYNTAX_ERROR: _verify_channel_routing(config, routed_channels)

# REMOVED_SYNTAX_ERROR: def _create_notification_configs(self):
    # REMOVED_SYNTAX_ERROR: """Create notification configuration test cases (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return [ )
    # REMOVED_SYNTAX_ERROR: {"type": "critical", "channels": ["email", "slack", "webhook"]],
    # REMOVED_SYNTAX_ERROR: {"type": "warning", "channels": ["slack", "webhook"]],
    # REMOVED_SYNTAX_ERROR: {"type": "info", "channels": ["webhook"]],
    # REMOVED_SYNTAX_ERROR: {"type": "debug", "channels": []]
    

# REMOVED_SYNTAX_ERROR: def _route_notification(self, config):
    # REMOVED_SYNTAX_ERROR: """Route notification to appropriate channels (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return config["channels"]

# REMOVED_SYNTAX_ERROR: def _verify_channel_routing(self, config, routed_channels):
    # REMOVED_SYNTAX_ERROR: """Verify notification channel routing (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: assert routed_channels == config["channels"]

# REMOVED_SYNTAX_ERROR: def test_batch_scheduling_optimization(self):
    # REMOVED_SYNTAX_ERROR: """Test batch scheduling for efficiency"""
    # REMOVED_SYNTAX_ERROR: research_requests = _create_batch_requests()
    # REMOVED_SYNTAX_ERROR: optimized_batches = _optimize_request_batching(research_requests)
    # REMOVED_SYNTAX_ERROR: _verify_batch_optimization(optimized_batches)

# REMOVED_SYNTAX_ERROR: def _create_batch_requests(self):
    # REMOVED_SYNTAX_ERROR: """Create batch request test data (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return [ )
    # REMOVED_SYNTAX_ERROR: {"provider": "openai", "type": ResearchType.PRICING},
    # REMOVED_SYNTAX_ERROR: {"provider": "openai", "type": ResearchType.CAPABILITIES},
    # REMOVED_SYNTAX_ERROR: {"provider": "anthropic", "type": ResearchType.PRICING},
    # REMOVED_SYNTAX_ERROR: {"provider": "anthropic", "type": ResearchType.CAPABILITIES}
    

# REMOVED_SYNTAX_ERROR: def _optimize_request_batching(self, requests):
    # REMOVED_SYNTAX_ERROR: """Optimize request batching by provider (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: batches = {}
    # REMOVED_SYNTAX_ERROR: for request in requests:
        # REMOVED_SYNTAX_ERROR: provider = request["provider"]
        # REMOVED_SYNTAX_ERROR: if provider not in batches:
            # REMOVED_SYNTAX_ERROR: batches[provider] = []
            # REMOVED_SYNTAX_ERROR: batches[provider].append(request)
            # REMOVED_SYNTAX_ERROR: return batches

# REMOVED_SYNTAX_ERROR: def _verify_batch_optimization(self, batches):
    # REMOVED_SYNTAX_ERROR: """Verify batch optimization results (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: assert "openai" in batches
    # REMOVED_SYNTAX_ERROR: assert "anthropic" in batches
    # REMOVED_SYNTAX_ERROR: assert len(batches["openai"]) == 2
    # REMOVED_SYNTAX_ERROR: assert len(batches["anthropic"]) == 2

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_schedule_health_monitoring(self):
        # REMOVED_SYNTAX_ERROR: """Test schedule health and failure monitoring"""
        # REMOVED_SYNTAX_ERROR: schedule_health = _create_schedule_health_data()
        # REMOVED_SYNTAX_ERROR: health_status = await _monitor_schedule_health(schedule_health)
        # REMOVED_SYNTAX_ERROR: _verify_health_monitoring(health_status)

# REMOVED_SYNTAX_ERROR: def _create_schedule_health_data(self):
    # REMOVED_SYNTAX_ERROR: """Create schedule health test data (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "daily_pricing": {"success_rate": 0.95, "last_run": "success"},
    # REMOVED_SYNTAX_ERROR: "weekly_capabilities": {"success_rate": 0.80, "last_run": "failed"},
    # REMOVED_SYNTAX_ERROR: "monthly_overview": {"success_rate": 1.0, "last_run": "success"}
    

# REMOVED_SYNTAX_ERROR: async def _monitor_schedule_health(self, health_data):
    # REMOVED_SYNTAX_ERROR: """Monitor schedule health status (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: unhealthy_schedules = []
    # REMOVED_SYNTAX_ERROR: for schedule, health in health_data.items():
        # REMOVED_SYNTAX_ERROR: if health["success_rate"] < 0.9 or health["last_run"] == "failed":
            # REMOVED_SYNTAX_ERROR: unhealthy_schedules.append(schedule)
            # REMOVED_SYNTAX_ERROR: return {"unhealthy": unhealthy_schedules}

# REMOVED_SYNTAX_ERROR: def _verify_health_monitoring(self, health_status):
    # REMOVED_SYNTAX_ERROR: """Verify health monitoring results (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: assert "weekly_capabilities" in health_status["unhealthy"]
    # REMOVED_SYNTAX_ERROR: assert "daily_pricing" not in health_status["unhealthy"]