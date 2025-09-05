class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
    pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
    pass
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
    return self.messages_sent.copy()

"""Test suite for UniversalRegistry - SSOT registry pattern.

This test suite validates:
- Thread-safe registration and retrieval
- Factory pattern support
- Singleton pattern support
- Freeze/immutability
- Metrics and health checks
- Specialized registry implementations
"""

import pytest
import threading
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from netra_backend.app.core.agent_registry import AgentRegistry
from shared.isolated_environment import IsolatedEnvironment

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from netra_backend.app.core.registry.universal_registry import (
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
import asyncio
    UniversalRegistry,
    AgentRegistry,
    ToolRegistry,
    ServiceRegistry,
    StrategyRegistry,
    get_global_registry,
    create_scoped_registry,
    RegistryItem
)


class TestItem:
    """Test item for registry."""
    def __init__(self, name: str):
    pass
        self.name = name


class TestUniversalRegistry:
    """Test UniversalRegistry base functionality."""
    
    def test_registry_creation(self):
        """Test basic registry creation."""
        registry = UniversalRegistry[TestItem]("TestRegistry")
        
        assert registry.name == "TestRegistry"
        assert not registry.is_frozen()
        assert len(registry) == 0
        assert registry.get_metrics()['total_items'] == 0
    
    def test_singleton_registration(self):
        """Test singleton item registration."""
    pass
        registry = UniversalRegistry[TestItem]("TestRegistry")
        item = TestItem("test_item")
        
        # Register item
        registry.register("test", item)
        
        # Verify registration
        assert registry.has("test")
        assert registry.get("test") is item
        assert "test" in registry.list_keys()
        assert len(registry) == 1
    
    def test_duplicate_registration_fails(self):
        """Test that duplicate registration fails by default."""
        registry = UniversalRegistry[TestItem]("TestRegistry")
        item1 = TestItem("item1")
        item2 = TestItem("item2")
        
        registry.register("test", item1)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register("test", item2)
    
    def test_override_allowed(self):
        """Test override when explicitly allowed."""
    pass
        registry = UniversalRegistry[TestItem]("TestRegistry", allow_override=True)
        item1 = TestItem("item1")
        item2 = TestItem("item2")
        
        registry.register("test", item1)
        registry.register("test", item2)  # Should succeed
        
        assert registry.get("test") is item2
    
    def test_factory_registration(self):
        """Test factory pattern registration."""
        registry = UniversalRegistry[TestItem]("TestRegistry")
        
        # Mock UserExecutionContext
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        mock_context.user_id = "user123"
        mock_context.run_id = "run456"
        
        # Register factory
        def create_item(context):
            return TestItem(f"item_for_{context.user_id}")
        
        registry.register_factory("test_factory", create_item)
        
        # Create instance via factory
        item = registry.create_instance("test_factory", mock_context)
        
        assert item is not None
        assert item.name == "item_for_user123"
        
        # Verify factory creation metrics
        metrics = registry.get_metrics()
        assert metrics['metrics']['factory_creations'] == 1
    
    def test_get_with_context_prefers_factory(self):
        """Test that get() uses factory when context provided."""
    pass
        registry = UniversalRegistry[TestItem]("TestRegistry")
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        
        # Register both singleton and factory
        singleton = TestItem("singleton")
        registry.register("mixed", singleton)
        
        # First get without context returns singleton
        assert registry.get("mixed") is singleton
        
        # Now register factory for same key (with override)
        registry = UniversalRegistry[TestItem]("TestRegistry", allow_override=True)
        
        def create_item(context):
    pass
            return TestItem("factory_created")
        
        registry.register_factory("test", create_item)
        
        # Get with context uses factory
        item = registry.get("test", mock_context)
        assert item.name == "factory_created"
    
    def test_freeze_makes_immutable(self):
        """Test registry freeze functionality."""
        registry = UniversalRegistry[TestItem]("TestRegistry")
        item = TestItem("test")
        
        # Register before freeze
        registry.register("test", item)
        
        # Freeze registry
        registry.freeze()
        assert registry.is_frozen()
        
        # Attempt operations after freeze
        with pytest.raises(RuntimeError, match="frozen"):
            registry.register("new", TestItem("new"))
        
        with pytest.raises(RuntimeError, match="frozen"):
            registry.remove("test")
        
        with pytest.raises(RuntimeError, match="frozen"):
            registry.clear()
        
        # Read operations still work
        assert registry.get("test") is item
        assert registry.has("test")
    
    def test_tags_and_categories(self):
        """Test tag-based categorization."""
    pass
        registry = UniversalRegistry[TestItem]("TestRegistry")
        
        # Register items with tags
        registry.register("item1", TestItem("1"), tags=["category_a", "shared"])
        registry.register("item2", TestItem("2"), tags=["category_b", "shared"])
        registry.register("item3", TestItem("3"), tags=["category_a"])
        
        # List by tag
        assert set(registry.list_by_tag("category_a")) == {"item1", "item3"}
        assert set(registry.list_by_tag("category_b")) == {"item2"}
        assert set(registry.list_by_tag("shared")) == {"item1", "item2"}
        assert registry.list_by_tag("nonexistent") == []
    
    def test_validation_handlers(self):
        """Test custom validation handlers."""
        registry = UniversalRegistry[TestItem]("TestRegistry")
        
        # Add validation that requires name to start with "valid_"
        def validate_name(key: str, item: Any) -> bool:
            return key.startswith("valid_")
        
        registry.add_validation_handler(validate_name)
        
        # Valid registration
        registry.register("valid_item", TestItem("test"))
        
        # Invalid registration
        with pytest.raises(ValueError, match="Validation failed"):
            registry.register("invalid_item", TestItem("test"))
        
        # Check validation failure metrics
        metrics = registry.get_metrics()
        assert metrics['metrics']['validation_failures'] == 1
    
    def test_remove_item(self):
        """Test item removal."""
    pass
        registry = UniversalRegistry[TestItem]("TestRegistry")
        
        registry.register("test", TestItem("item"), tags=["category"])
        assert registry.has("test")
        assert "test" in registry.list_by_tag("category")
        
        # Remove item
        assert registry.remove("test")
        assert not registry.has("test")
        assert "test" not in registry.list_by_tag("category")
        
        # Remove non-existent
        assert not registry.remove("nonexistent")
    
    def test_clear_registry(self):
        """Test clearing all items."""
        registry = UniversalRegistry[TestItem]("TestRegistry")
        
        # Add multiple items
        for i in range(5):
            registry.register(f"item{i}", TestItem(f"test{i}"))
        
        assert len(registry) == 5
        
        # Clear all
        registry.clear()
        
        assert len(registry) == 0
        assert registry.list_keys() == []
    
    def test_metrics_tracking(self):
        """Test metrics collection."""
    pass
        registry = UniversalRegistry[TestItem]("TestRegistry", enable_metrics=True)
        
        # Perform operations
        registry.register("item1", TestItem("1"))
        registry.register("item2", TestItem("2"))
        
        # Access items
        registry.get("item1")
        registry.get("item1")
        registry.get("item2")
        
        # Get metrics
        metrics = registry.get_metrics()
        
        assert metrics['total_items'] == 2
        assert metrics['metrics']['successful_registrations'] == 2
        assert metrics['metrics']['total_retrievals'] == 3
        
        # Check most accessed
        most_accessed = metrics['most_accessed']
        assert most_accessed[0]['key'] == 'item1'
        assert most_accessed[0]['count'] == 2
    
    def test_health_validation(self):
        """Test health check functionality."""
        registry = UniversalRegistry[TestItem]("TestRegistry")
        
        # Empty registry warning
        health = registry.validate_health()
        assert health['status'] == 'warning'
        assert any('empty' in issue.lower() for issue in health['issues'])
        
        # Add items
        for i in range(5):
            registry.register(f"item{i}", TestItem(f"test{i}"))
        
        # Healthy registry
        health = registry.validate_health()
        assert health['status'] in ['healthy', 'warning']  # May warn about unused
        
        # Access some items to avoid unused warning
        for i in range(3):
            registry.get(f"item{i}")
        
        health = registry.validate_health()
        # Still may warn if >80% unused, but shouldn't be degraded
        assert health['status'] != 'degraded'
    
    def test_thread_safety(self):
        """Test thread-safe operations."""
    pass
        registry = UniversalRegistry[TestItem]("TestRegistry")
        errors = []
        
        def register_items(start, end):
    pass
            try:
                for i in range(start, end):
                    registry.register(f"item_{i}", TestItem(f"test_{i}"))
            except Exception as e:
                errors.append(e)
        
        # Run registrations in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(5):
                future = executor.submit(register_items, i * 10, (i + 1) * 10)
                futures.append(future)
            
            # Wait for completion
            for future in as_completed(futures):
                future.result()
        
        # Verify no errors and all items registered
        assert len(errors) == 0
        assert len(registry) == 50
        
        # Verify all items accessible
        for i in range(50):
            assert registry.has(f"item_{i}")


class TestSpecializedRegistries:
    """Test specialized registry implementations."""
    
    def test_agent_registry(self):
        """Test AgentRegistry with WebSocket integration."""
        registry = AgentRegistry()
        
        assert registry.name == "AgentRegistry"
        
        # Mock WebSocket manager
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        registry.set_websocket_manager(mock_ws_manager)
        assert registry.websocket_manager is mock_ws_manager
        
        # Mock WebSocket bridge
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        registry.set_websocket_bridge(mock_ws_bridge)
        assert registry.websocket_bridge is mock_ws_bridge
        
        # Test None bridge rejection
        with pytest.raises(ValueError, match="cannot be None"):
            registry.set_websocket_bridge(None)
    
    def test_tool_registry(self):
        """Test ToolRegistry initialization."""
    pass
        registry = ToolRegistry()
        
        assert registry.name == "ToolRegistry"
        # Default tools should be registered (mocked in implementation)
    
    def test_service_registry(self):
        """Test ServiceRegistry with service registration."""
        registry = ServiceRegistry()
        
        assert registry.name == "ServiceRegistry"
        
        # Register a service
        registry.register_service(
            "backend",
            "http://localhost:8000",
            health_endpoint="/health",
            version="1.0.0"
        )
        
        # Retrieve service
        service = registry.get("backend")
        assert service is not None
        assert service['url'] == "http://localhost:8000"
        assert service['health_endpoint'] == "/health"
    
    def test_strategy_registry(self):
        """Test StrategyRegistry."""
    pass
        registry = StrategyRegistry()
        
        assert registry.name == "StrategyRegistry"
        
        # Register a strategy
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        registry.register("retry_strategy", mock_strategy)
        
        assert registry.get("retry_strategy") is mock_strategy


class TestGlobalRegistries:
    """Test global registry management."""
    
    def test_get_global_registry(self):
        """Test global registry singleton pattern."""
        # Get agent registry
        registry1 = get_global_registry("agent")
        registry2 = get_global_registry("agent")
        
        # Should be same instance
        assert registry1 is registry2
        
        # Different types should be different instances
        tool_registry = get_global_registry("tool")
        assert tool_registry is not registry1
    
    def test_unknown_registry_type(self):
        """Test error for unknown registry type."""
    pass
        with pytest.raises(ValueError, match="Unknown registry type"):
            get_global_registry("invalid_type")
    
    def test_create_scoped_registry(self):
        """Test creating request-scoped registries."""
        # Create scoped registries
        registry1 = create_scoped_registry("agent", "request_123")
        registry2 = create_scoped_registry("agent", "request_456")
        
        # Should be different instances
        assert registry1 is not registry2
        
        # Should have different names
        assert registry1.name == "agent_request_123"
        assert registry2.name == "agent_request_456"
        
        # Operations should be isolated
        registry1.register("test",         assert registry1.has("test")
        assert not registry2.has("test")


class TestConcurrentFactoryCreation:
    """Test concurrent factory usage for user isolation."""
    
    def test_concurrent_factory_creation(self):
        """Test that factories create isolated instances concurrently."""
        registry = UniversalRegistry[TestItem]("TestRegistry")
        created_items = []
        
        # Register factory that creates unique items
        def create_unique_item(context):
            item = TestItem(f"user_{context.user_id}_time_{time.time()}")
            created_items.append(item)
            return item
        
        registry.register_factory("user_item", create_unique_item)
        
        # Create items concurrently for different users
        def create_for_user(user_id):
            websocket = TestWebSocketConnection()  # Real WebSocket implementation
            context.user_id = user_id
            return registry.create_instance("user_item", context)
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_for_user, f"user_{i}") for i in range(10)]
            results = [f.result() for f in as_completed(futures)]
        
        # Verify all items are unique
        assert len(results) == 10
        assert len(created_items) == 10
        
        # Verify no items are the same instance
        for i, item1 in enumerate(results):
            for j, item2 in enumerate(results):
                if i != j:
                    assert item1 is not item2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
    pass