"""
Analytics Service Integration Test Utilities
===========================================

Utility functions and helper classes for Analytics Service integration testing.
Provides common functionality for test setup, data generation, and assertions.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity and Test Reliability
- Value Impact: Reduces test development time and improves test maintainability
- Strategic Impact: Enables comprehensive testing of analytics functionality
"""

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4
import random
import string
from shared.isolated_environment import IsolatedEnvironment

from test_framework import setup_test_path

# CRITICAL: setup_test_path() MUST be called before any project imports per CLAUDE.md
setup_test_path()

from analytics_service.analytics_core.models.events import (
    AnalyticsEvent,
    EventType,
    MessageType,
    EventContext,
    ChatInteractionProperties,
    ThreadLifecycleProperties,
    FeatureUsageProperties,
    EventIngestionRequest,
    EventIngestionResponse,
)
from shared.isolated_environment import get_env


class TestDataGenerator:
    """Generates realistic test data for analytics integration tests."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize test data generator with optional seed for reproducibility."""
        if seed is not None:
            random.seed(seed)
        
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        ]
        
        self.page_paths = [
            "/chat", "/dashboard", "/settings", "/profile", "/analytics",
            "/onboarding", "/tutorial", "/help", "/pricing", "/admin"
        ]
        
        self.event_actions = {
            EventType.CHAT_INTERACTION: ["send_message", "receive_response", "edit_message", "delete_message"],
            EventType.PERFORMANCE_METRIC: ["page_load", "api_call", "database_query", "cache_hit"],
            EventType.FEATURE_USAGE: ["feature_activated", "feature_configured", "feature_disabled"],
            EventType.THREAD_LIFECYCLE: ["thread_created", "thread_updated", "thread_archived"],
        }
        
        self.ai_models = [
            "claude-sonnet-4", "claude-opus-3", "gpt-4-turbo", "gpt-3.5-turbo", 
            "gemini-pro", "claude-haiku-3", "llama-2-70b"
        ]
        
    def generate_user_id(self, prefix: str = "test_user") -> str:
        """Generate a unique user ID for testing."""
        return f"{prefix}_{int(time.time())}_{random.randint(1000, 9999)}"
    
    def generate_session_id(self, prefix: str = "session") -> str:
        """Generate a unique session ID for testing."""
        return f"{prefix}_{int(time.time())}_{random.randint(100, 999)}"
    
    def generate_thread_id(self) -> str:
        """Generate a unique thread ID for testing."""
        return str(uuid4())
    
    def generate_chat_interaction_event(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **overrides
    ) -> ChatInteractionEvent:
        """Generate a realistic chat interaction event."""
        base_event = ChatInteractionEvent(
            event_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            user_id=user_id or self.generate_user_id(),
            session_id=session_id or self.generate_session_id(),
            thread_id=self.generate_thread_id(),
            message_id=str(uuid4()),
            message_type=random.choice(["user_prompt", "assistant_response", "system_message"]),
            prompt_text=self._generate_prompt_text(),
            prompt_length=random.randint(10, 500),
            response_time_ms=random.uniform(200, 5000),
            model_used=random.choice(self.ai_models),
            tokens_consumed=random.randint(50, 2000),
            estimated_cost_cents=random.uniform(0.01, 2.50),
            is_follow_up=random.choice([True, False]),
        )
        
        # Apply any overrides
        for key, value in overrides.items():
            if hasattr(base_event, key):
                setattr(base_event, key, value)
        
        return base_event
    
    def generate_frontend_event(
        self,
        event_type: EventType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **overrides
    ) -> FrontendEvent:
        """Generate a realistic frontend event of specified type."""
        base_event = FrontendEvent(
            event_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            user_id=user_id or self.generate_user_id(),
            session_id=session_id or self.generate_session_id(),
            event_type=event_type,
            event_category=self._get_category_for_type(event_type),
            event_action=random.choice(self.event_actions.get(event_type, ["default_action"])),
            event_label=self._generate_event_label(event_type),
            event_value=random.uniform(1.0, 1000.0),
            properties=json.dumps(self._generate_event_properties(event_type)),
            page_path=random.choice(self.page_paths),
            page_title=self._generate_page_title(),
            referrer=self._generate_referrer(),
            user_agent=random.choice(self.user_agents),
            ip_address=self._generate_ip_address(),
            country_code=random.choice(["US", "GB", "CA", "AU", "DE", "FR", "JP"]),
            gtm_container_id=f"GTM-{random.randint(100000, 999999)}",
            environment="test",
            app_version="1.0.0-test",
        )
        
        # Apply any overrides
        for key, value in overrides.items():
            if hasattr(base_event, key):
                setattr(base_event, key, value)
        
        return base_event
    
    def generate_event_batch(
        self,
        size: int = 10,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        event_types: Optional[List[EventType]] = None,
    ) -> EventBatch:
        """Generate a batch of events for testing."""
        if event_types is None:
            event_types = [EventType.CHAT_INTERACTION, EventType.PERFORMANCE_METRIC, EventType.FEATURE_USAGE]
        
        events = []
        for i in range(size):
            event_type = random.choice(event_types)
            
            if event_type == EventType.CHAT_INTERACTION:
                event = self.generate_chat_interaction_event(user_id=user_id, session_id=session_id)
            else:
                event = self.generate_frontend_event(event_type, user_id=user_id, session_id=session_id)
            
            events.append(event)
        
        return EventBatch(
            batch_id=str(uuid4()),
            events=events,
            created_at=datetime.now(timezone.utc),
        )
    
    def generate_high_volume_events(
        self,
        count: int = 1000,
        user_count: int = 100,
        time_span_minutes: int = 60,
    ) -> List[FrontendEvent]:
        """Generate high-volume event data for performance testing."""
        events = []
        users = [self.generate_user_id(f"perf_user_{i}") for i in range(user_count)]
        start_time = datetime.now(timezone.utc) - timedelta(minutes=time_span_minutes)
        
        for i in range(count):
            # Distribute events across time span
            event_time = start_time + timedelta(
                minutes=random.uniform(0, time_span_minutes)
            )
            
            user_id = random.choice(users)
            event_type = random.choice(list(EventType))
            
            event = self.generate_frontend_event(
                event_type=event_type,
                user_id=user_id,
                timestamp=event_time,
            )
            
            events.append(event)
        
        return events
    
    def _generate_prompt_text(self) -> str:
        """Generate realistic prompt text for chat interactions."""
        prompts = [
            "How can I optimize my AI spending?",
            "What are the best practices for prompt engineering?",
            "Can you help me analyze my application performance?",
            "How do I set up monitoring for my AI models?",
            "What's the difference between these two approaches?",
            "Can you explain this error message?",
            "How can I improve my system's efficiency?",
            "What are the latest trends in AI optimization?",
        ]
        return random.choice(prompts)
    
    def _get_category_for_type(self, event_type: EventType) -> EventCategory:
        """Get appropriate event category for event type."""
        category_mapping = {
            EventType.CHAT_INTERACTION: EventCategory.USER_INTERACTION,
            EventType.PERFORMANCE_METRIC: EventCategory.TECHNICAL,
            EventType.FEATURE_USAGE: EventCategory.USER_INTERACTION,
            EventType.THREAD_LIFECYCLE: EventCategory.USER_INTERACTION,
        }
        return category_mapping.get(event_type, EventCategory.USER_INTERACTION)
    
    def _generate_event_label(self, event_type: EventType) -> str:
        """Generate appropriate event label for event type."""
        labels = {
            EventType.CHAT_INTERACTION: ["message_sent", "response_received", "thread_started"],
            EventType.PERFORMANCE_METRIC: ["page_load_time", "api_response_time", "cache_performance"],
            EventType.FEATURE_USAGE: ["feature_enabled", "setting_changed", "integration_configured"],
        }
        return random.choice(labels.get(event_type, ["generic_label"]))
    
    def _generate_event_properties(self, event_type: EventType) -> Dict[str, Any]:
        """Generate realistic event properties based on event type."""
        base_properties = {
            "test_generated": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if event_type == EventType.CHAT_INTERACTION:
            base_properties.update({
                "model": random.choice(self.ai_models),
                "tokens": random.randint(50, 2000),
                "cost_cents": random.uniform(0.01, 2.50),
                "response_time_ms": random.uniform(200, 5000),
            })
        elif event_type == EventType.PERFORMANCE_METRIC:
            base_properties.update({
                "duration_ms": random.uniform(10, 5000),
                "success": random.choice([True, False]),
                "endpoint": random.choice(["/api/chat", "/api/analytics", "/api/users"]),
            })
        elif event_type == EventType.FEATURE_USAGE:
            base_properties.update({
                "feature_name": random.choice(["analytics", "monitoring", "alerts", "reporting"]),
                "usage_count": random.randint(1, 100),
                "enabled": random.choice([True, False]),
            })
        
        return base_properties
    
    def _generate_page_title(self) -> str:
        """Generate realistic page title."""
        titles = [
            "Netra AI Chat", "Analytics Dashboard", "User Settings", 
            "Performance Monitor", "Cost Analysis", "Help Center"
        ]
        return random.choice(titles)
    
    def _generate_referrer(self) -> str:
        """Generate realistic referrer URL."""
        referrers = [
            "https://google.com", "https://netra.ai", "https://docs.netra.ai",
            "", "https://github.com", "https://stackoverflow.com"
        ]
        return random.choice(referrers)
    
    def _generate_ip_address(self) -> str:
        """Generate realistic IP address for testing."""
        return f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"


class TestAssertions:
    """Helper class for common test assertions in analytics integration tests."""
    
    @staticmethod
    def assert_event_structure(event: Dict[str, Any]) -> None:
        """Assert that an event has the required structure."""
        required_fields = ["event_id", "timestamp", "user_id", "event_type"]
        for field in required_fields:
            assert field in event, f"Required field '{field}' missing from event"
            assert event[field] is not None, f"Required field '{field}' is None"
        
        # Validate timestamp format
        assert isinstance(event["timestamp"], str), "Timestamp must be string"
        try:
            datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
        except ValueError:
            assert False, f"Invalid timestamp format: {event['timestamp']}"
    
    @staticmethod
    def assert_processing_result(result: Any) -> None:
        """Assert that a processing result has the expected structure."""
        assert hasattr(result, 'success'), "Processing result must have 'success' attribute"
        assert hasattr(result, 'event_id'), "Processing result must have 'event_id' attribute"
        assert hasattr(result, 'processing_time_ms'), "Processing result must have 'processing_time_ms' attribute"
        
        if not result.success:
            assert hasattr(result, 'error_message'), "Failed result must have 'error_message' attribute"
            assert result.error_message is not None, "Error message cannot be None for failed result"
    
    @staticmethod
    def assert_api_response_structure(response_data: Dict[str, Any], expected_fields: List[str]) -> None:
        """Assert that an API response has the expected structure."""
        for field in expected_fields:
            assert field in response_data, f"Expected field '{field}' missing from API response"
    
    @staticmethod
    def assert_performance_requirements(
        processing_time_ms: float, 
        max_time_ms: float, 
        operation: str = "operation"
    ) -> None:
        """Assert that processing time meets performance requirements."""
        assert processing_time_ms > 0, f"{operation} processing time must be positive"
        assert processing_time_ms <= max_time_ms, f"{operation} took {processing_time_ms}ms (max: {max_time_ms}ms)"
    
    @staticmethod
    def assert_batch_processing_results(
        results: List[Any], 
        expected_count: int, 
        min_success_rate: float = 0.9
    ) -> None:
        """Assert that batch processing results meet expectations."""
        assert len(results) == expected_count, f"Expected {expected_count} results, got {len(results)}"
        
        successful_count = sum(1 for r in results if hasattr(r, 'success') and r.success)
        success_rate = successful_count / len(results)
        
        assert success_rate >= min_success_rate, f"Success rate {success_rate:.2%} below minimum {min_success_rate:.2%}"


class DatabaseTestUtils:
    """Utilities for database testing in integration tests."""
    
    @staticmethod
    async def wait_for_database_operation(
        operation_func,
        max_wait_seconds: float = 10.0,
        check_interval: float = 0.5
    ) -> Any:
        """Wait for a database operation to complete successfully."""
        start_time = time.time()
        last_exception = None
        
        while (time.time() - start_time) < max_wait_seconds:
            try:
                result = await operation_func()
                return result
            except Exception as e:
                last_exception = e
                await asyncio.sleep(check_interval)
        
        raise TimeoutError(
            f"Database operation timed out after {max_wait_seconds}s. Last error: {last_exception}"
        )
    
    @staticmethod
    async def cleanup_test_data(
        clickhouse_manager, 
        redis_manager, 
        test_identifiers: List[str]
    ) -> None:
        """Clean up test data from databases."""
        try:
            # Clean ClickHouse test data
            if clickhouse_manager and test_identifiers:
                for identifier in test_identifiers:
                    await clickhouse_manager.execute_command(
                        f"DELETE FROM frontend_events WHERE user_id LIKE '%{identifier}%'"
                    )
            
            # Clean Redis test data
            if redis_manager and test_identifiers:
                for identifier in test_identifiers:
                    keys = await redis_manager.keys(f"*{identifier}*")
                    if keys:
                        await redis_manager.delete(*keys)
                        
        except Exception as e:
            # Log cleanup errors but don't fail tests
            print(f"Warning: Test cleanup failed: {e}")


class ServiceTestUtils:
    """Utilities for service communication testing."""
    
    @staticmethod
    async def wait_for_service_ready(
        service_url: str, 
        max_wait_seconds: float = 30.0,
        check_interval: float = 1.0
    ) -> bool:
        """Wait for a service to be ready for testing."""
        import httpx
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            while (time.time() - start_time) < max_wait_seconds:
                try:
                    response = await client.get(f"{service_url}/health")
                    if response.status_code == 200:
                        return True
                except (httpx.ConnectError, httpx.TimeoutException):
                    pass
                
                await asyncio.sleep(check_interval)
        
        return False
    
    @staticmethod
    def create_test_headers(api_key: Optional[str] = None) -> Dict[str, str]:
        """Create standard test headers for service communication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Analytics-Service-Integration-Test/1.0",
        }
        
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        return headers


class PerformanceTestUtils:
    """Utilities for performance testing in integration tests."""
    
    def __init__(self):
        self.measurements = {}
    
    def start_measurement(self, operation_name: str) -> None:
        """Start measuring performance for an operation."""
        self.measurements[operation_name] = {"start_time": time.time()}
    
    def end_measurement(self, operation_name: str) -> float:
        """End measurement and return duration in milliseconds."""
        if operation_name not in self.measurements:
            raise ValueError(f"No measurement started for operation: {operation_name}")
        
        duration = time.time() - self.measurements[operation_name]["start_time"]
        duration_ms = duration * 1000
        
        self.measurements[operation_name].update({
            "end_time": time.time(),
            "duration_seconds": duration,
            "duration_ms": duration_ms,
        })
        
        return duration_ms
    
    def get_measurement_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of all measurements."""
        summary = {}
        for operation, data in self.measurements.items():
            if "duration_ms" in data:
                summary[operation] = {
                    "duration_ms": data["duration_ms"],
                    "duration_seconds": data["duration_seconds"],
                }
        return summary
    
    @staticmethod
    def calculate_throughput(
        operations_count: int, 
        total_duration_seconds: float
    ) -> float:
        """Calculate operations per second throughput."""
        if total_duration_seconds <= 0:
            return 0.0
        return operations_count / total_duration_seconds
    
    @staticmethod
    def assert_throughput_requirement(
        actual_throughput: float,
        minimum_throughput: float,
        operation_name: str = "operation"
    ) -> None:
        """Assert that throughput meets minimum requirements."""
        assert actual_throughput >= minimum_throughput, (
            f"{operation_name} throughput {actual_throughput:.2f} ops/sec "
            f"below minimum {minimum_throughput:.2f} ops/sec"
        )


# Export commonly used utilities for easy importing
__all__ = [
    "TestDataGenerator",
    "TestAssertions", 
    "DatabaseTestUtils",
    "ServiceTestUtils",
    "PerformanceTestUtils",
]