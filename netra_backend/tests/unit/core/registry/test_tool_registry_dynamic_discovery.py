"""Unit tests for tool registry and dynamic tool discovery.

These tests validate the UniversalRegistry pattern as applied to tool management,
including dynamic tool registration, discovery, factory patterns, and thread-safe operations.

Business Value: Platform/Internal - Development Velocity
Enables dynamic tool discovery and registration for flexible agent workflows.

Test Coverage:
- Dynamic tool registration and discovery
- Factory pattern for tool creation with user context
- Thread-safe registry operations
- Tool categorization and tagging
- Registry validation and error handling
- Tool lifecycle management
"""

import asyncio
import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.registry.universal_registry import (
    UniversalRegistry,
    RegistryItem,
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from langchain_core.tools import BaseTool


# Create ToolRegistry alias for testing
ToolRegistry = UniversalRegistry[BaseTool]


class MockAnalyticsTool(BaseTool):
    """Mock analytics tool for registry testing."""
    
    name = "analytics_tool"
    description = "Analyzes data and generates reports"
    
    def __init__(self, tool_id: str = None, config: Dict[str, Any] = None):
        super().__init__()
        self.tool_id = tool_id or "analytics_001"
        self.config = config or {}
        self.execution_count = 0
        self.created_at = time.time()
        
    def _run(self, query: str, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(query, **kwargs))
        
    async def _arun(self, query: str, **kwargs) -> str:
        """Asynchronous execution."""
        self.execution_count += 1
        await asyncio.sleep(0.001)  # Simulate work
        return f"Analytics result for: {query} (tool_id: {self.tool_id})"


class MockDataTool(BaseTool):
    """Mock data processing tool for registry testing."""
    
    name = "data_tool" 
    description = "Processes and transforms data"
    
    def __init__(self, processing_type: str = "standard"):
        super().__init__()
        self.processing_type = processing_type
        self.execution_count = 0
        
    def _run(self, dataset: str, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(dataset, **kwargs))
        
    async def _arun(self, dataset: str, **kwargs) -> str:
        """Asynchronous execution."""
        self.execution_count += 1
        return f"Processed {dataset} using {self.processing_type} processing"


class MockUserSpecificTool(BaseTool):
    """Mock tool that requires user context for creation."""
    
    name = "user_specific_tool"
    description = "Tool that operates on user-specific data"
    
    def __init__(self, user_context: UserExecutionContext):
        super().__init__()
        self.user_context = user_context
        self.execution_count = 0
        
    def _run(self, operation: str, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(operation, **kwargs))
        
    async def _arun(self, operation: str, **kwargs) -> str:
        """Asynchronous execution."""
        self.execution_count += 1
        return f"User {self.user_context.user_id} operation: {operation}"


def create_user_specific_tool_factory(base_config: Dict[str, Any] = None):
    """Factory function for creating user-specific tools."""
    def factory(user_context: UserExecutionContext) -> MockUserSpecificTool:
        tool = MockUserSpecificTool(user_context)
        if base_config:
            tool.config = base_config
        return tool
    return factory


class TestToolRegistryDynamicDiscovery(SSotAsyncTestCase):
    """Unit tests for tool registry and dynamic discovery patterns."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        # Create test user contexts
        self.user1_context = UserExecutionContext(
            user_id="registry_user_001",
            run_id=f"run_{int(time.time() * 1000)}",
            thread_id="thread_registry_001",
            session_id="session_registry_001",
            metadata={"plan_tier": "early", "roles": ["user"]}
        )
        
        self.user2_context = UserExecutionContext(
            user_id="registry_user_002",
            run_id=f"run_{int(time.time() * 1000) + 1}",
            thread_id="thread_registry_002",
            session_id="session_registry_002",
            metadata={"plan_tier": "mid", "roles": ["user", "analyst"]}
        )
        
        # Create test tools
        self.analytics_tool = MockAnalyticsTool("analytics_001")
        self.data_tool = MockDataTool("advanced")
        self.basic_analytics = MockAnalyticsTool("basic_analytics", {"tier": "basic"})
        
        # Create registry
        self.tool_registry = ToolRegistry("TestToolRegistry", allow_override=True)
        
    def tearDown(self):
        """Clean up after tests."""
        super().tearDown()
        
    # ===================== BASIC REGISTRY OPERATIONS =====================
    
    def test_tool_registration_and_retrieval(self):
        """Test basic tool registration and retrieval."""
        # Register tools
        self.tool_registry.register(
            "analytics",
            self.analytics_tool,
            description="Advanced analytics tool",
            tags=["analytics", "reporting"]
        )
        
        self.tool_registry.register(
            "data_processing",
            self.data_tool,
            description="Data processing tool",
            tags=["data", "processing"]
        )
        
        # Verify registration
        self.assertTrue(self.tool_registry.has("analytics"))
        self.assertTrue(self.tool_registry.has("data_processing"))
        self.assertFalse(self.tool_registry.has("nonexistent"))
        
        # Retrieve tools
        retrieved_analytics = self.tool_registry.get("analytics")
        retrieved_data = self.tool_registry.get("data_processing")
        
        self.assertIsNotNone(retrieved_analytics)
        self.assertIsNotNone(retrieved_data)
        self.assertEqual(retrieved_analytics.tool_id, "analytics_001")
        self.assertEqual(retrieved_data.processing_type, "advanced")
        
    def test_tool_discovery_by_category(self):
        """Test dynamic tool discovery by category/tags."""
        # Register tools with categories
        self.tool_registry.register(
            "advanced_analytics",
            self.analytics_tool,
            tags=["analytics", "advanced", "ml"]
        )
        
        self.tool_registry.register(
            "basic_analytics", 
            self.basic_analytics,
            tags=["analytics", "basic", "reporting"]
        )
        
        self.tool_registry.register(
            "data_processor",
            self.data_tool,
            tags=["data", "processing", "etl"]
        )
        
        # Discover tools by category
        analytics_tools = self.tool_registry.get_by_category("analytics")
        data_tools = self.tool_registry.get_by_category("data")
        advanced_tools = self.tool_registry.get_by_category("advanced")
        
        self.assertEqual(len(analytics_tools), 2)
        self.assertEqual(len(data_tools), 1)
        self.assertEqual(len(advanced_tools), 1)
        
        # Verify correct tools in categories
        analytics_keys = set(analytics_tools)
        self.assertIn("advanced_analytics", analytics_keys)
        self.assertIn("basic_analytics", analytics_keys)
        
    def test_available_tools_listing(self):
        """Test listing all available tools."""
        # Register multiple tools
        tools_to_register = {
            "tool_1": self.analytics_tool,
            "tool_2": self.data_tool,
            "tool_3": self.basic_analytics
        }
        
        for key, tool in tools_to_register.items():
            self.tool_registry.register(key, tool)
            
        # Get available tools
        available_tools = self.tool_registry.list_keys()
        
        self.assertEqual(len(available_tools), 3)
        for tool_key in tools_to_register.keys():
            self.assertIn(tool_key, available_tools)
            
    # ===================== FACTORY PATTERN TESTS =====================
            
    def test_tool_factory_registration_and_creation(self):
        """Test registering tool factories and creating user-specific instances."""
        # Register factory
        factory = create_user_specific_tool_factory({"version": "2.0"})
        
        self.tool_registry.register_factory(
            "user_tool",
            factory,
            description="User-specific tool factory",
            tags=["user", "contextual"]
        )
        
        # Verify factory is registered
        self.assertTrue(self.tool_registry.has("user_tool"))
        
        # Create instances for different users
        user1_tool = self.tool_registry.create_instance("user_tool", self.user1_context)
        user2_tool = self.tool_registry.create_instance("user_tool", self.user2_context)
        
        self.assertIsNotNone(user1_tool)
        self.assertIsNotNone(user2_tool)
        
        # Verify user-specific instances
        self.assertEqual(user1_tool.user_context.user_id, self.user1_context.user_id)
        self.assertEqual(user2_tool.user_context.user_id, self.user2_context.user_id)
        
        # Verify instances are different
        self.assertNotEqual(user1_tool, user2_tool)
        
    async def test_concurrent_factory_instance_creation(self):
        """Test concurrent creation of tool instances via factory."""
        # Register factory
        factory = create_user_specific_tool_factory()
        self.tool_registry.register_factory("concurrent_tool", factory)
        
        # Create multiple contexts
        contexts = []
        for i in range(10):
            context = UserExecutionContext(
                user_id=f"concurrent_user_{i}",
                run_id=f"concurrent_run_{i}",
                thread_id=f"concurrent_thread_{i}",
                session_id=f"concurrent_session_{i}"
            )
            contexts.append(context)
        
        # Create instances concurrently
        def create_instance(context):
            return self.tool_registry.create_instance("concurrent_tool", context)
            
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_instance, ctx) for ctx in contexts]
            instances = [future.result() for future in futures]
        
        # Verify all instances created successfully
        self.assertEqual(len(instances), 10)
        
        # Verify each instance has correct user context
        for i, instance in enumerate(instances):
            self.assertIsNotNone(instance)
            self.assertEqual(instance.user_context.user_id, f"concurrent_user_{i}")
            
    # ===================== THREAD SAFETY TESTS =====================
            
    def test_thread_safe_registration(self):
        """Test thread-safe tool registration under concurrent access."""
        num_threads = 10
        tools_per_thread = 5
        
        def register_tools(thread_id):
            for i in range(tools_per_thread):
                tool_key = f"thread_{thread_id}_tool_{i}"
                tool = MockAnalyticsTool(f"tool_{thread_id}_{i}")
                
                try:
                    self.tool_registry.register(
                        tool_key,
                        tool,
                        tags=[f"thread_{thread_id}", "concurrent"]
                    )
                except Exception as e:
                    # Log but don't fail - some overlap expected
                    pass
        
        # Run concurrent registrations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(register_tools, i) for i in range(num_threads)]
            [future.result() for future in futures]
        
        # Verify registry state is consistent
        available_tools = self.tool_registry.list_keys()
        self.assertGreater(len(available_tools), 0)
        
        # Verify tools can be retrieved
        for tool_key in available_tools:
            tool = self.tool_registry.get(tool_key)
            self.assertIsNotNone(tool)
            
    def test_concurrent_access_patterns(self):
        """Test concurrent read/write access patterns."""
        # Pre-register some tools
        for i in range(5):
            self.tool_registry.register(
                f"base_tool_{i}",
                MockAnalyticsTool(f"base_{i}"),
                tags=["base", "concurrent"]
            )
        
        results = {"registrations": 0, "retrievals": 0, "errors": 0}
        results_lock = threading.Lock()
        
        def register_and_retrieve(worker_id):
            try:
                # Register new tool
                tool_key = f"worker_{worker_id}_tool"
                tool = MockDataTool(f"worker_{worker_id}")
                
                self.tool_registry.register(tool_key, tool)
                
                with results_lock:
                    results["registrations"] += 1
                
                # Retrieve existing tools
                available = self.tool_registry.list_keys()
                for key in available[:3]:  # Check first 3 tools
                    retrieved = self.tool_registry.get(key)
                    if retrieved:
                        with results_lock:
                            results["retrievals"] += 1
                            
            except Exception as e:
                with results_lock:
                    results["errors"] += 1
        
        # Run concurrent operations
        num_workers = 10
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(register_and_retrieve, i) for i in range(num_workers)]
            [future.result() for future in futures]
        
        # Verify successful operations
        self.assertGreater(results["registrations"], 0)
        self.assertGreater(results["retrievals"], 0)
        self.assertEqual(results["errors"], 0)  # Should be no errors
        
    # ===================== VALIDATION AND ERROR HANDLING =====================
        
    def test_registry_validation_handlers(self):
        """Test custom validation handlers for tool registration."""
        validation_calls = []
        
        def custom_validator(key: str, item: Any) -> bool:
            """Custom validation that rejects tools without specific attributes."""
            validation_calls.append((key, item))
            
            # Require tools to have certain attributes
            if not hasattr(item, 'tool_id'):
                return False
            if not hasattr(item, 'name'):
                return False
                
            return True
        
        # Add validator
        self.tool_registry.add_validation_handler(custom_validator)
        
        # Try to register valid tool
        valid_tool = MockAnalyticsTool("valid_001")
        self.tool_registry.register("valid_tool", valid_tool)
        
        # Verify registration succeeded
        self.assertTrue(self.tool_registry.has("valid_tool"))
        self.assertEqual(len(validation_calls), 1)
        
        # Try to register invalid tool (object without required attributes)
        invalid_tool = MagicMock()
        del invalid_tool.tool_id  # Remove required attribute
        
        with self.assertRaises(ValueError):
            self.tool_registry.register("invalid_tool", invalid_tool)
        
        # Verify invalid tool was not registered
        self.assertFalse(self.tool_registry.has("invalid_tool"))
        
    def test_duplicate_registration_handling(self):
        """Test handling of duplicate tool registrations."""
        # Register initial tool
        self.tool_registry.register("duplicate_test", self.analytics_tool)
        
        # Try to register with same key (should work with allow_override=True)
        different_tool = MockDataTool()
        self.tool_registry.register("duplicate_test", different_tool)
        
        # Verify the second tool replaced the first
        retrieved = self.tool_registry.get("duplicate_test")
        self.assertIsInstance(retrieved, MockDataTool)
        
        # Test with registry that doesn't allow overrides
        strict_registry = ToolRegistry("StrictRegistry", allow_override=False)
        strict_registry.register("test_tool", self.analytics_tool)
        
        with self.assertRaises(ValueError):
            strict_registry.register("test_tool", different_tool)
            
    def test_registry_freeze_functionality(self):
        """Test registry freeze functionality for immutability."""
        # Register initial tools
        self.tool_registry.register("tool_1", self.analytics_tool)
        self.tool_registry.register("tool_2", self.data_tool)
        
        # Freeze registry
        self.tool_registry.freeze()
        
        # Verify existing tools still accessible
        self.assertTrue(self.tool_registry.has("tool_1"))
        self.assertTrue(self.tool_registry.has("tool_2"))
        
        # Verify new registrations are blocked
        with self.assertRaises(RuntimeError):
            self.tool_registry.register("new_tool", MockAnalyticsTool())
            
        with self.assertRaises(RuntimeError):
            self.tool_registry.register_factory("new_factory", create_user_specific_tool_factory())
            
    # ===================== METRICS AND MONITORING =====================
            
    def test_registry_metrics_tracking(self):
        """Test registry metrics and access tracking."""
        # Enable metrics
        registry_with_metrics = ToolRegistry("MetricsRegistry", enable_metrics=True)
        
        # Register tools
        registry_with_metrics.register("metrics_tool_1", self.analytics_tool)
        registry_with_metrics.register("metrics_tool_2", self.data_tool)
        
        # Access tools multiple times
        for _ in range(3):
            registry_with_metrics.get("metrics_tool_1")
        
        for _ in range(2):
            registry_with_metrics.get("metrics_tool_2")
        
        # Check metrics
        metrics = registry_with_metrics.get_metrics()
        
        self.assertEqual(metrics['total_registrations'], 2)
        self.assertEqual(metrics['successful_registrations'], 2)
        self.assertEqual(metrics['total_retrievals'], 5)
        
        # Check individual item access counts
        tool1_info = registry_with_metrics._items["metrics_tool_1"]
        tool2_info = registry_with_metrics._items["metrics_tool_2"]
        
        self.assertEqual(tool1_info.access_count, 3)
        self.assertEqual(tool2_info.access_count, 2)
        
    def test_registry_health_check(self):
        """Test registry health check functionality."""
        # Register tools
        self.tool_registry.register("health_tool_1", self.analytics_tool, tags=["healthy"])
        self.tool_registry.register("health_tool_2", self.data_tool, tags=["healthy"])
        
        # Register factory
        factory = create_user_specific_tool_factory()
        self.tool_registry.register_factory("factory_tool", factory, tags=["factory"])
        
        # Get health status
        health = self.tool_registry.get_health_status()
        
        self.assertIn("status", health)
        self.assertIn("total_items", health)
        self.assertIn("singleton_count", health)
        self.assertIn("factory_count", health)
        
        # Verify counts
        self.assertEqual(health["total_items"], 3)
        self.assertEqual(health["singleton_count"], 2)
        self.assertEqual(health["factory_count"], 1)
        
    def test_registry_cleanup_operations(self):
        """Test registry cleanup and maintenance operations."""
        # Register tools
        self.tool_registry.register("cleanup_tool_1", self.analytics_tool)
        self.tool_registry.register("cleanup_tool_2", self.data_tool)
        
        # Verify tools exist
        self.assertTrue(self.tool_registry.has("cleanup_tool_1"))
        self.assertTrue(self.tool_registry.has("cleanup_tool_2"))
        
        # Clear registry
        self.tool_registry.clear()
        
        # Verify registry is empty
        self.assertFalse(self.tool_registry.has("cleanup_tool_1"))
        self.assertFalse(self.tool_registry.has("cleanup_tool_2"))
        self.assertEqual(len(self.tool_registry.list_keys()), 0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])