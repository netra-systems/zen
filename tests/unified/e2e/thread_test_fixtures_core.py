"""Core Thread Test Fixtures
Shared fixtures and utilities for thread management testing.
Extracted from large test files for better organization.

BVJ: Reduces test duplication and ensures consistent thread test infrastructure.
Segment: All tiers. Business Goal: Test infrastructure reliability.
Value Impact: Enables comprehensive thread testing across all customer segments.
Strategic Impact: Faster test development and more reliable thread operations.
"""

import asyncio
import json
import uuid
import time
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from contextlib import asynccontextmanager
import pytest
from datetime import datetime, timezone

from netra_backend.tests.unified.config import TEST_USERS, TEST_ENDPOINTS, TestDataFactory
from netra_backend.tests.unified.e2e.unified_e2e_harness import UnifiedE2ETestHarness
from netra_backend.tests.unified.test_harness import UnifiedTestHarness
from netra_backend.app.schemas.core_enums import WebSocketMessageType
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ThreadTestDataFactory:
    """Factory for creating consistent thread test data."""
    
    @staticmethod
    def create_thread_data(user_id: str, **kwargs) -> Dict[str, Any]:
        """Create thread data with defaults."""
        return {
            "id": f"thread_{user_id}_{int(time.time())}",
            "object": "thread",
            "created_at": int(time.time()),
            "title": kwargs.get("title", f"Test Thread {uuid.uuid4().hex[:8]}"),
            "metadata_": {"user_id": user_id, **kwargs.get("metadata", {})}
        }
    
    @staticmethod
    def create_message_data(thread_id: str, role: str, content: str, **kwargs) -> Dict[str, Any]:
        """Create message data with defaults."""
        return {
            "id": f"msg_{uuid.uuid4().hex[:8]}",
            "object": "thread.message",
            "created_at": int(time.time()),
            "thread_id": thread_id,
            "role": role,
            "content": [{"type": "text", "text": {"value": content}}],
            "assistant_id": kwargs.get("assistant_id"),
            "run_id": kwargs.get("run_id"),
            "file_ids": [],
            "metadata_": kwargs.get("metadata", {})
        }
    
    @staticmethod
    def create_agent_context_data(agent_id: str, status: str = "idle", **kwargs) -> Dict[str, Any]:
        """Create agent context data for thread testing."""
        return {
            "agent_id": agent_id,
            "status": status,
            "execution_state": kwargs.get("execution_state", {}),
            "preserved_at": time.time(),
            "metadata": kwargs.get("metadata", {})
        }


class ThreadWebSocketFixtures:
    """Shared WebSocket fixtures for thread testing."""
    
    def __init__(self, harness: UnifiedTestHarness):
        self.harness = harness
        self.active_connections: Dict[str, Any] = {}
        self.thread_events: List[Dict[str, Any]] = []
        self.websocket_messages: List[Dict[str, Any]] = []
        self.thread_contexts: Dict[str, Dict[str, Any]] = {}
    
    async def create_authenticated_connection(self, user_id: str) -> Dict[str, Any]:
        """Create authenticated WebSocket connection for user."""
        tokens = self.harness.create_test_tokens(user_id)
        headers = self.harness.create_auth_headers(tokens["access_token"])
        connection = await self._establish_websocket_connection(user_id, headers)
        self.active_connections[user_id] = connection
        return connection
    
    async def _establish_websocket_connection(self, user_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Establish WebSocket connection with authentication."""
        return {
            "user_id": user_id,
            "connection_id": str(uuid.uuid4()),
            "headers": headers,
            "connected": True,
            "last_ping": time.time(),
            "message_queue": [],
            "subscribed_threads": set()
        }
    
    def build_websocket_message(self, message_type: WebSocketMessageType, **payload) -> Dict[str, Any]:
        """Build standardized WebSocket message."""
        return {
            "type": message_type.value,
            "payload": {
                **payload,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    
    async def send_websocket_message(self, user_id: str, message: Dict[str, Any]) -> None:
        """Send WebSocket message and track it."""
        connection = self.active_connections.get(user_id)
        if connection:
            connection["message_queue"].append(message)
            self.websocket_messages.append({
                "user_id": user_id,
                "message": message,
                "timestamp": time.time()
            })
    
    def capture_thread_event(self, event_type: WebSocketMessageType, user_id: str, 
                           thread_id: str, **extra_data) -> None:
        """Capture thread WebSocket event."""
        event = {
            "type": event_type.value,
            "user_id": user_id,
            "thread_id": thread_id,
            "timestamp": time.time(),
            "payload": {"thread_id": thread_id, **extra_data}
        }
        self.thread_events.append(event)


class ThreadContextManager:
    """Manages thread contexts for testing."""
    
    def __init__(self, ws_fixtures: ThreadWebSocketFixtures):
        self.ws_fixtures = ws_fixtures
        self.context_snapshots: List[Dict[str, Any]] = []
    
    async def preserve_agent_context_in_thread(self, user_id: str, thread_id: str, 
                                               agent_data: Dict[str, Any]) -> None:
        """Preserve agent context within thread."""
        context_key = f"{user_id}:{thread_id}"
        if context_key not in self.ws_fixtures.thread_contexts:
            self.ws_fixtures.thread_contexts[context_key] = {}
        
        self.ws_fixtures.thread_contexts[context_key]["agent_context"] = {
            **ThreadTestDataFactory.create_agent_context_data(
                agent_data.get("agent_id"),
                agent_data.get("status", "idle")
            ),
            "execution_state": agent_data.get("execution_state", {})
        }
    
    def validate_context_isolation(self, user_id: str, thread_a_id: str, thread_b_id: str) -> bool:
        """Validate thread contexts remain isolated."""
        context_a_key = f"{user_id}:{thread_a_id}"
        context_b_key = f"{user_id}:{thread_b_id}"
        
        context_a = self.ws_fixtures.thread_contexts.get(context_a_key, {})
        context_b = self.ws_fixtures.thread_contexts.get(context_b_key, {})
        
        return (context_a != context_b and 
                context_a.get("thread_id") != context_b.get("thread_id"))
    
    def capture_context_snapshot(self, user_id: str, thread_id: str, operation: str) -> Dict[str, Any]:
        """Capture context snapshot for validation."""
        context_key = f"{user_id}:{thread_id}"
        snapshot = {
            "user_id": user_id,
            "thread_id": thread_id,
            "operation": operation,
            "context": self.ws_fixtures.thread_contexts.get(context_key, {}).copy(),
            "timestamp": time.time(),
            "active_connections": len(self.ws_fixtures.active_connections),
            "total_events": len(self.ws_fixtures.thread_events)
        }
        self.context_snapshots.append(snapshot)
        return snapshot
    
    def verify_context_preservation(self, before_snapshot: Dict[str, Any], 
                                    after_snapshot: Dict[str, Any]) -> bool:
        """Verify context was preserved across operations."""
        before_context = before_snapshot.get("context", {})
        after_context = after_snapshot.get("context", {})
        
        before_agent = before_context.get("agent_context", {})
        after_agent = after_context.get("agent_context", {})
        
        return (before_agent.get("agent_id") == after_agent.get("agent_id") and
                before_agent.get("execution_state") == after_agent.get("execution_state"))


class ThreadPerformanceUtils:
    """Performance testing utilities for threads."""
    
    @staticmethod
    def measure_operation_time(operation_name: str):
        """Decorator to measure operation execution time."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                result = await func(*args, **kwargs)
                end_time = time.perf_counter()
                
                execution_time = end_time - start_time
                logger.info(f"{operation_name} completed in {execution_time:.3f}s")
                
                if hasattr(result, 'update') and isinstance(result, dict):
                    result.update({"execution_time": execution_time})
                
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def calculate_performance_metrics(successful_results: List, errors: List,
                                      start_time: float, end_time: float) -> Dict[str, Any]:
        """Calculate performance metrics for batch operations."""
        total_time = end_time - start_time
        success_count = len(successful_results)
        error_count = len(errors)
        total_operations = success_count + error_count
        
        return {
            "total_time": total_time,
            "success_count": success_count,
            "error_count": error_count,
            "total_operations": total_operations,
            "throughput": success_count / total_time if total_time > 0 else 0,
            "error_rate": error_count / total_operations if total_operations > 0 else 0,
            "success_rate": success_count / total_operations if total_operations > 0 else 0
        }
    
    @staticmethod
    def validate_performance_requirements(metrics: Dict[str, Any], 
                                          min_throughput: float = 10.0,
                                          max_error_rate: float = 0.05) -> bool:
        """Validate performance meets requirements."""
        return (metrics["throughput"] >= min_throughput and 
                metrics["error_rate"] <= max_error_rate)


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture
def unified_harness():
    """Unified test harness fixture."""
    return UnifiedTestHarness()


@pytest.fixture
def thread_data_factory():
    """Thread test data factory fixture."""
    return ThreadTestDataFactory()


@pytest.fixture
def ws_thread_fixtures(unified_harness):
    """WebSocket thread fixtures."""
    return ThreadWebSocketFixtures(unified_harness)


@pytest.fixture
def thread_context_manager(ws_thread_fixtures):
    """Thread context manager fixture."""
    return ThreadContextManager(ws_thread_fixtures)


@pytest.fixture
def performance_utils():
    """Performance testing utilities fixture."""
    return ThreadPerformanceUtils()


@pytest.fixture
def test_users():
    """Standard test users for thread testing."""
    return {
        "free": TEST_USERS["free"],
        "early": TEST_USERS["early"],
        "mid": TEST_USERS["mid"],
        "enterprise": TEST_USERS["enterprise"]
    }


@pytest.fixture
async def sample_thread_scenario(ws_thread_fixtures, thread_data_factory):
    """Create a sample thread scenario for testing."""
    user = TEST_USERS["mid"]
    
    # Create connection
    connection = await ws_thread_fixtures.create_authenticated_connection(user.id)
    
    # Create thread data
    thread_data = thread_data_factory.create_thread_data(
        user.id, 
        title="Sample Test Thread",
        metadata={"scenario": "sample"}
    )
    
    # Create some messages
    messages = [
        thread_data_factory.create_message_data(
            thread_data["id"], 
            "user", 
            "Hello, I need help with optimization"
        ),
        thread_data_factory.create_message_data(
            thread_data["id"], 
            "assistant", 
            "I'd be happy to help with optimization"
        )
    ]
    
    return {
        "user": user,
        "connection": connection,
        "thread": thread_data,
        "messages": messages
    }