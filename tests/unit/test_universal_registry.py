# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''Test suite for UniversalRegistry - SSOT registry pattern.

    # REMOVED_SYNTAX_ERROR: This test suite validates:
        # REMOVED_SYNTAX_ERROR: - Thread-safe registration and retrieval
        # REMOVED_SYNTAX_ERROR: - Factory pattern support
        # REMOVED_SYNTAX_ERROR: - Singleton pattern support
        # REMOVED_SYNTAX_ERROR: - Freeze/immutability
        # REMOVED_SYNTAX_ERROR: - Metrics and health checks
        # REMOVED_SYNTAX_ERROR: - Specialized registry implementations
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: import threading
        # REMOVED_SYNTAX_ERROR: import time
        # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
        # REMOVED_SYNTAX_ERROR: from concurrent.futures import ThreadPoolExecutor, as_completed
        # REMOVED_SYNTAX_ERROR: from typing import Any
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.agent_registry import AgentRegistry
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # REMOVED_SYNTAX_ERROR: import sys
        # REMOVED_SYNTAX_ERROR: from pathlib import Path
        # REMOVED_SYNTAX_ERROR: sys.path.append(str(Path(__file__).parent.parent.parent))

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.registry.universal_registry import ( )
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: UniversalRegistry,
        # REMOVED_SYNTAX_ERROR: AgentRegistry,
        # REMOVED_SYNTAX_ERROR: ToolRegistry,
        # REMOVED_SYNTAX_ERROR: ServiceRegistry,
        # REMOVED_SYNTAX_ERROR: StrategyRegistry,
        # REMOVED_SYNTAX_ERROR: get_global_registry,
        # REMOVED_SYNTAX_ERROR: create_scoped_registry,
        # REMOVED_SYNTAX_ERROR: RegistryItem
        


# REMOVED_SYNTAX_ERROR: class TestItem:
    # REMOVED_SYNTAX_ERROR: """Test item for registry."""
# REMOVED_SYNTAX_ERROR: def __init__(self, name: str):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.name = name


# REMOVED_SYNTAX_ERROR: class TestUniversalRegistry:
    # REMOVED_SYNTAX_ERROR: """Test UniversalRegistry base functionality."""

# REMOVED_SYNTAX_ERROR: def test_registry_creation(self):
    # REMOVED_SYNTAX_ERROR: """Test basic registry creation."""
    # REMOVED_SYNTAX_ERROR: registry = UniversalRegistry[TestItem]("TestRegistry")

    # REMOVED_SYNTAX_ERROR: assert registry.name == "TestRegistry"
    # REMOVED_SYNTAX_ERROR: assert not registry.is_frozen()
    # REMOVED_SYNTAX_ERROR: assert len(registry) == 0
    # REMOVED_SYNTAX_ERROR: assert registry.get_metrics()['total_items'] == 0

# REMOVED_SYNTAX_ERROR: def test_singleton_registration(self):
    # REMOVED_SYNTAX_ERROR: """Test singleton item registration."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: registry = UniversalRegistry[TestItem]("TestRegistry")
    # REMOVED_SYNTAX_ERROR: item = TestItem("test_item")

    # Register item
    # REMOVED_SYNTAX_ERROR: registry.register("test", item)

    # Verify registration
    # REMOVED_SYNTAX_ERROR: assert registry.has("test")
    # REMOVED_SYNTAX_ERROR: assert registry.get("test") is item
    # REMOVED_SYNTAX_ERROR: assert "test" in registry.list_keys()
    # REMOVED_SYNTAX_ERROR: assert len(registry) == 1

# REMOVED_SYNTAX_ERROR: def test_duplicate_registration_fails(self):
    # REMOVED_SYNTAX_ERROR: """Test that duplicate registration fails by default."""
    # REMOVED_SYNTAX_ERROR: registry = UniversalRegistry[TestItem]("TestRegistry")
    # REMOVED_SYNTAX_ERROR: item1 = TestItem("item1")
    # REMOVED_SYNTAX_ERROR: item2 = TestItem("item2")

    # REMOVED_SYNTAX_ERROR: registry.register("test", item1)

    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="already registered"):
        # REMOVED_SYNTAX_ERROR: registry.register("test", item2)

# REMOVED_SYNTAX_ERROR: def test_override_allowed(self):
    # REMOVED_SYNTAX_ERROR: """Test override when explicitly allowed."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: registry = UniversalRegistry[TestItem]("TestRegistry", allow_override=True)
    # REMOVED_SYNTAX_ERROR: item1 = TestItem("item1")
    # REMOVED_SYNTAX_ERROR: item2 = TestItem("item2")

    # REMOVED_SYNTAX_ERROR: registry.register("test", item1)
    # REMOVED_SYNTAX_ERROR: registry.register("test", item2)  # Should succeed

    # REMOVED_SYNTAX_ERROR: assert registry.get("test") is item2

# REMOVED_SYNTAX_ERROR: def test_factory_registration(self):
    # REMOVED_SYNTAX_ERROR: """Test factory pattern registration."""
    # REMOVED_SYNTAX_ERROR: registry = UniversalRegistry[TestItem]("TestRegistry")

    # Mock UserExecutionContext
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
    # REMOVED_SYNTAX_ERROR: mock_context.user_id = "user123"
    # REMOVED_SYNTAX_ERROR: mock_context.run_id = "run456"

    # Register factory
# REMOVED_SYNTAX_ERROR: def create_item(context):
    # REMOVED_SYNTAX_ERROR: return TestItem("formatted_string")

    # REMOVED_SYNTAX_ERROR: registry.register_factory("test_factory", create_item)

    # Create instance via factory
    # REMOVED_SYNTAX_ERROR: item = registry.create_instance("test_factory", mock_context)

    # REMOVED_SYNTAX_ERROR: assert item is not None
    # REMOVED_SYNTAX_ERROR: assert item.name == "item_for_user123"

    # Verify factory creation metrics
    # REMOVED_SYNTAX_ERROR: metrics = registry.get_metrics()
    # REMOVED_SYNTAX_ERROR: assert metrics['metrics']['factory_creations'] == 1

# REMOVED_SYNTAX_ERROR: def test_get_with_context_prefers_factory(self):
    # REMOVED_SYNTAX_ERROR: """Test that get() uses factory when context provided."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: registry = UniversalRegistry[TestItem]("TestRegistry")
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation

    # Register both singleton and factory
    # REMOVED_SYNTAX_ERROR: singleton = TestItem("singleton")
    # REMOVED_SYNTAX_ERROR: registry.register("mixed", singleton)

    # First get without context returns singleton
    # REMOVED_SYNTAX_ERROR: assert registry.get("mixed") is singleton

    # Now register factory for same key (with override)
    # REMOVED_SYNTAX_ERROR: registry = UniversalRegistry[TestItem]("TestRegistry", allow_override=True)

# REMOVED_SYNTAX_ERROR: def create_item(context):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return TestItem("factory_created")

    # REMOVED_SYNTAX_ERROR: registry.register_factory("test", create_item)

    # Get with context uses factory
    # REMOVED_SYNTAX_ERROR: item = registry.get("test", mock_context)
    # REMOVED_SYNTAX_ERROR: assert item.name == "factory_created"

# REMOVED_SYNTAX_ERROR: def test_freeze_makes_immutable(self):
    # REMOVED_SYNTAX_ERROR: """Test registry freeze functionality."""
    # REMOVED_SYNTAX_ERROR: registry = UniversalRegistry[TestItem]("TestRegistry")
    # REMOVED_SYNTAX_ERROR: item = TestItem("test")

    # Register before freeze
    # REMOVED_SYNTAX_ERROR: registry.register("test", item)

    # Freeze registry
    # REMOVED_SYNTAX_ERROR: registry.freeze()
    # REMOVED_SYNTAX_ERROR: assert registry.is_frozen()

    # Attempt operations after freeze
    # REMOVED_SYNTAX_ERROR: with pytest.raises(RuntimeError, match="frozen"):
        # REMOVED_SYNTAX_ERROR: registry.register("new", TestItem("new"))

        # REMOVED_SYNTAX_ERROR: with pytest.raises(RuntimeError, match="frozen"):
            # REMOVED_SYNTAX_ERROR: registry.remove("test")

            # REMOVED_SYNTAX_ERROR: with pytest.raises(RuntimeError, match="frozen"):
                # REMOVED_SYNTAX_ERROR: registry.clear()

                # Read operations still work
                # REMOVED_SYNTAX_ERROR: assert registry.get("test") is item
                # REMOVED_SYNTAX_ERROR: assert registry.has("test")

# REMOVED_SYNTAX_ERROR: def test_tags_and_categories(self):
    # REMOVED_SYNTAX_ERROR: """Test tag-based categorization."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: registry = UniversalRegistry[TestItem]("TestRegistry")

    # Register items with tags
    # REMOVED_SYNTAX_ERROR: registry.register("item1", TestItem("1"), tags=["category_a", "shared"])
    # REMOVED_SYNTAX_ERROR: registry.register("item2", TestItem("2"), tags=["category_b", "shared"])
    # REMOVED_SYNTAX_ERROR: registry.register("item3", TestItem("3"), tags=["category_a"])

    # List by tag
    # REMOVED_SYNTAX_ERROR: assert set(registry.list_by_tag("category_a")) == {"item1", "item3"}
    # REMOVED_SYNTAX_ERROR: assert set(registry.list_by_tag("category_b")) == {"item2"}
    # REMOVED_SYNTAX_ERROR: assert set(registry.list_by_tag("shared")) == {"item1", "item2"}
    # REMOVED_SYNTAX_ERROR: assert registry.list_by_tag("nonexistent") == []

# REMOVED_SYNTAX_ERROR: def test_validation_handlers(self):
    # REMOVED_SYNTAX_ERROR: """Test custom validation handlers."""
    # REMOVED_SYNTAX_ERROR: registry = UniversalRegistry[TestItem]("TestRegistry")

    # Add validation that requires name to start with "valid_"
# REMOVED_SYNTAX_ERROR: def validate_name(key: str, item: Any) -> bool:
    # REMOVED_SYNTAX_ERROR: return key.startswith("valid_")

    # REMOVED_SYNTAX_ERROR: registry.add_validation_handler(validate_name)

    # Valid registration
    # REMOVED_SYNTAX_ERROR: registry.register("valid_item", TestItem("test"))

    # Invalid registration
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="Validation failed"):
        # REMOVED_SYNTAX_ERROR: registry.register("invalid_item", TestItem("test"))

        # Check validation failure metrics
        # REMOVED_SYNTAX_ERROR: metrics = registry.get_metrics()
        # REMOVED_SYNTAX_ERROR: assert metrics['metrics']['validation_failures'] == 1

# REMOVED_SYNTAX_ERROR: def test_remove_item(self):
    # REMOVED_SYNTAX_ERROR: """Test item removal."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: registry = UniversalRegistry[TestItem]("TestRegistry")

    # REMOVED_SYNTAX_ERROR: registry.register("test", TestItem("item"), tags=["category"])
    # REMOVED_SYNTAX_ERROR: assert registry.has("test")
    # REMOVED_SYNTAX_ERROR: assert "test" in registry.list_by_tag("category")

    # Remove item
    # REMOVED_SYNTAX_ERROR: assert registry.remove("test")
    # REMOVED_SYNTAX_ERROR: assert not registry.has("test")
    # REMOVED_SYNTAX_ERROR: assert "test" not in registry.list_by_tag("category")

    # Remove non-existent
    # REMOVED_SYNTAX_ERROR: assert not registry.remove("nonexistent")

# REMOVED_SYNTAX_ERROR: def test_clear_registry(self):
    # REMOVED_SYNTAX_ERROR: """Test clearing all items."""
    # REMOVED_SYNTAX_ERROR: registry = UniversalRegistry[TestItem]("TestRegistry")

    # Add multiple items
    # REMOVED_SYNTAX_ERROR: for i in range(5):
        # REMOVED_SYNTAX_ERROR: registry.register("formatted_string", TestItem("formatted_string"))

        # REMOVED_SYNTAX_ERROR: assert len(registry) == 5

        # Clear all
        # REMOVED_SYNTAX_ERROR: registry.clear()

        # REMOVED_SYNTAX_ERROR: assert len(registry) == 0
        # REMOVED_SYNTAX_ERROR: assert registry.list_keys() == []

# REMOVED_SYNTAX_ERROR: def test_metrics_tracking(self):
    # REMOVED_SYNTAX_ERROR: """Test metrics collection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: registry = UniversalRegistry[TestItem]("TestRegistry", enable_metrics=True)

    # Perform operations
    # REMOVED_SYNTAX_ERROR: registry.register("item1", TestItem("1"))
    # REMOVED_SYNTAX_ERROR: registry.register("item2", TestItem("2"))

    # Access items
    # REMOVED_SYNTAX_ERROR: registry.get("item1")
    # REMOVED_SYNTAX_ERROR: registry.get("item1")
    # REMOVED_SYNTAX_ERROR: registry.get("item2")

    # Get metrics
    # REMOVED_SYNTAX_ERROR: metrics = registry.get_metrics()

    # REMOVED_SYNTAX_ERROR: assert metrics['total_items'] == 2
    # REMOVED_SYNTAX_ERROR: assert metrics['metrics']['successful_registrations'] == 2
    # REMOVED_SYNTAX_ERROR: assert metrics['metrics']['total_retrievals'] == 3

    # Check most accessed
    # REMOVED_SYNTAX_ERROR: most_accessed = metrics['most_accessed']
    # REMOVED_SYNTAX_ERROR: assert most_accessed[0]['key'] == 'item1'
    # REMOVED_SYNTAX_ERROR: assert most_accessed[0]['count'] == 2

# REMOVED_SYNTAX_ERROR: def test_health_validation(self):
    # REMOVED_SYNTAX_ERROR: """Test health check functionality."""
    # REMOVED_SYNTAX_ERROR: registry = UniversalRegistry[TestItem]("TestRegistry")

    # Empty registry warning
    # REMOVED_SYNTAX_ERROR: health = registry.validate_health()
    # REMOVED_SYNTAX_ERROR: assert health['status'] == 'warning'
    # REMOVED_SYNTAX_ERROR: assert any('empty' in issue.lower() for issue in health['issues'])

    # Add items
    # REMOVED_SYNTAX_ERROR: for i in range(5):
        # REMOVED_SYNTAX_ERROR: registry.register("formatted_string", TestItem("formatted_string"))

        # Healthy registry
        # REMOVED_SYNTAX_ERROR: health = registry.validate_health()
        # REMOVED_SYNTAX_ERROR: assert health['status'] in ['healthy', 'warning']  # May warn about unused

        # Access some items to avoid unused warning
        # REMOVED_SYNTAX_ERROR: for i in range(3):
            # REMOVED_SYNTAX_ERROR: registry.get("formatted_string")

            # REMOVED_SYNTAX_ERROR: health = registry.validate_health()
            # Still may warn if >80% unused, but shouldn't be degraded
            # REMOVED_SYNTAX_ERROR: assert health['status'] != 'degraded'

# REMOVED_SYNTAX_ERROR: def test_thread_safety(self):
    # REMOVED_SYNTAX_ERROR: """Test thread-safe operations."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: registry = UniversalRegistry[TestItem]("TestRegistry")
    # REMOVED_SYNTAX_ERROR: errors = []

# REMOVED_SYNTAX_ERROR: def register_items(start, end):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: for i in range(start, end):
            # REMOVED_SYNTAX_ERROR: registry.register("formatted_string", TestItem("formatted_string"))
            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: errors.append(e)

                # Run registrations in parallel
                # REMOVED_SYNTAX_ERROR: with ThreadPoolExecutor(max_workers=5) as executor:
                    # REMOVED_SYNTAX_ERROR: futures = []
                    # REMOVED_SYNTAX_ERROR: for i in range(5):
                        # REMOVED_SYNTAX_ERROR: future = executor.submit(register_items, i * 10, (i + 1) * 10)
                        # REMOVED_SYNTAX_ERROR: futures.append(future)

                        # Wait for completion
                        # REMOVED_SYNTAX_ERROR: for future in as_completed(futures):
                            # REMOVED_SYNTAX_ERROR: future.result()

                            # Verify no errors and all items registered
                            # REMOVED_SYNTAX_ERROR: assert len(errors) == 0
                            # REMOVED_SYNTAX_ERROR: assert len(registry) == 50

                            # Verify all items accessible
                            # REMOVED_SYNTAX_ERROR: for i in range(50):
                                # REMOVED_SYNTAX_ERROR: assert registry.has("formatted_string")


# REMOVED_SYNTAX_ERROR: class TestSpecializedRegistries:
    # REMOVED_SYNTAX_ERROR: """Test specialized registry implementations."""

# REMOVED_SYNTAX_ERROR: def test_agent_registry(self):
    # REMOVED_SYNTAX_ERROR: """Test AgentRegistry with WebSocket integration."""
    # REMOVED_SYNTAX_ERROR: registry = AgentRegistry()

    # REMOVED_SYNTAX_ERROR: assert registry.name == "AgentRegistry"

    # Mock WebSocket manager
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
    # REMOVED_SYNTAX_ERROR: registry.set_websocket_manager(mock_ws_manager)
    # REMOVED_SYNTAX_ERROR: assert registry.websocket_manager is mock_ws_manager

    # Mock WebSocket bridge
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
    # REMOVED_SYNTAX_ERROR: registry.set_websocket_bridge(mock_ws_bridge)
    # REMOVED_SYNTAX_ERROR: assert registry.websocket_bridge is mock_ws_bridge

    # Test None bridge rejection
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="cannot be None"):
        # REMOVED_SYNTAX_ERROR: registry.set_websocket_bridge(None)

# REMOVED_SYNTAX_ERROR: def test_tool_registry(self):
    # REMOVED_SYNTAX_ERROR: """Test ToolRegistry initialization."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: registry = ToolRegistry()

    # REMOVED_SYNTAX_ERROR: assert registry.name == "ToolRegistry"
    # Default tools should be registered (mocked in implementation)

# REMOVED_SYNTAX_ERROR: def test_service_registry(self):
    # REMOVED_SYNTAX_ERROR: """Test ServiceRegistry with service registration."""
    # REMOVED_SYNTAX_ERROR: registry = ServiceRegistry()

    # REMOVED_SYNTAX_ERROR: assert registry.name == "ServiceRegistry"

    # Register a service
    # REMOVED_SYNTAX_ERROR: registry.register_service( )
    # REMOVED_SYNTAX_ERROR: "backend",
    # REMOVED_SYNTAX_ERROR: "http://localhost:8000",
    # REMOVED_SYNTAX_ERROR: health_endpoint="/health",
    # REMOVED_SYNTAX_ERROR: version="1.0.0"
    

    # Retrieve service
    # REMOVED_SYNTAX_ERROR: service = registry.get("backend")
    # REMOVED_SYNTAX_ERROR: assert service is not None
    # REMOVED_SYNTAX_ERROR: assert service['url'] == "http://localhost:8000"
    # REMOVED_SYNTAX_ERROR: assert service['health_endpoint'] == "/health"

# REMOVED_SYNTAX_ERROR: def test_strategy_registry(self):
    # REMOVED_SYNTAX_ERROR: """Test StrategyRegistry."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: registry = StrategyRegistry()

    # REMOVED_SYNTAX_ERROR: assert registry.name == "StrategyRegistry"

    # Register a strategy
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
    # REMOVED_SYNTAX_ERROR: registry.register("retry_strategy", mock_strategy)

    # REMOVED_SYNTAX_ERROR: assert registry.get("retry_strategy") is mock_strategy


# REMOVED_SYNTAX_ERROR: class TestGlobalRegistries:
    # REMOVED_SYNTAX_ERROR: """Test global registry management."""

# REMOVED_SYNTAX_ERROR: def test_get_global_registry(self):
    # REMOVED_SYNTAX_ERROR: """Test global registry singleton pattern."""
    # Get agent registry
    # REMOVED_SYNTAX_ERROR: registry1 = get_global_registry("agent")
    # REMOVED_SYNTAX_ERROR: registry2 = get_global_registry("agent")

    # Should be same instance
    # REMOVED_SYNTAX_ERROR: assert registry1 is registry2

    # Different types should be different instances
    # REMOVED_SYNTAX_ERROR: tool_registry = get_global_registry("tool")
    # REMOVED_SYNTAX_ERROR: assert tool_registry is not registry1

# REMOVED_SYNTAX_ERROR: def test_unknown_registry_type(self):
    # REMOVED_SYNTAX_ERROR: """Test error for unknown registry type."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="Unknown registry type"):
        # REMOVED_SYNTAX_ERROR: get_global_registry("invalid_type")

# REMOVED_SYNTAX_ERROR: def test_create_scoped_registry(self):
    # REMOVED_SYNTAX_ERROR: """Test creating request-scoped registries."""
    # Create scoped registries
    # REMOVED_SYNTAX_ERROR: registry1 = create_scoped_registry("agent", "request_123")
    # REMOVED_SYNTAX_ERROR: registry2 = create_scoped_registry("agent", "request_456")

    # Should be different instances
    # REMOVED_SYNTAX_ERROR: assert registry1 is not registry2

    # Should have different names
    # REMOVED_SYNTAX_ERROR: assert registry1.name == "agent_request_123"
    # REMOVED_SYNTAX_ERROR: assert registry2.name == "agent_request_456"

    # Operations should be isolated
    # REMOVED_SYNTAX_ERROR: registry1.register("test",         assert registry1.has("test") )
    # REMOVED_SYNTAX_ERROR: assert not registry2.has("test")


# REMOVED_SYNTAX_ERROR: class TestConcurrentFactoryCreation:
    # REMOVED_SYNTAX_ERROR: """Test concurrent factory usage for user isolation."""

# REMOVED_SYNTAX_ERROR: def test_concurrent_factory_creation(self):
    # REMOVED_SYNTAX_ERROR: """Test that factories create isolated instances concurrently."""
    # REMOVED_SYNTAX_ERROR: registry = UniversalRegistry[TestItem]("TestRegistry")
    # REMOVED_SYNTAX_ERROR: created_items = []

    # Register factory that creates unique items
# REMOVED_SYNTAX_ERROR: def create_unique_item(context):
    # REMOVED_SYNTAX_ERROR: item = TestItem("formatted_string")
    # REMOVED_SYNTAX_ERROR: created_items.append(item)
    # REMOVED_SYNTAX_ERROR: return item

    # REMOVED_SYNTAX_ERROR: registry.register_factory("user_item", create_unique_item)

    # Create items concurrently for different users
# REMOVED_SYNTAX_ERROR: def create_for_user(user_id):
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
    # REMOVED_SYNTAX_ERROR: context.user_id = user_id
    # REMOVED_SYNTAX_ERROR: return registry.create_instance("user_item", context)

    # REMOVED_SYNTAX_ERROR: with ThreadPoolExecutor(max_workers=10) as executor:
        # REMOVED_SYNTAX_ERROR: futures = [executor.submit(create_for_user, "formatted_string") for i in range(10)]
        # REMOVED_SYNTAX_ERROR: results = [f.result() for f in as_completed(futures)]

        # Verify all items are unique
        # REMOVED_SYNTAX_ERROR: assert len(results) == 10
        # REMOVED_SYNTAX_ERROR: assert len(created_items) == 10

        # Verify no items are the same instance
        # REMOVED_SYNTAX_ERROR: for i, item1 in enumerate(results):
            # REMOVED_SYNTAX_ERROR: for j, item2 in enumerate(results):
                # REMOVED_SYNTAX_ERROR: if i != j:
                    # REMOVED_SYNTAX_ERROR: assert item1 is not item2


                    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                        # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v"])
                        # REMOVED_SYNTAX_ERROR: pass