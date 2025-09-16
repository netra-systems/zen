"""Integration tests for Agent Registry and Factory patterns.

These tests validate REAL component interactions between:
- UniversalRegistry[BaseAgent] 
- AgentRegistry specialized functionality
- Factory creation patterns
- WebSocket manager integration
- User context isolation

CRITICAL: These are INTEGRATION tests - they test REAL interactions between components
without mocks, but should work without Docker services.

Business Value: Platform/Internal - System Stability
Ensures agent registry and factory patterns work correctly for multi-user isolation.
"""

import asyncio
import pytest
import tempfile
import time
from typing import Any, Dict, Optional, List
from unittest.mock import AsyncMock, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.registry.universal_registry import (
    UniversalRegistry, 
    AgentRegistry, 
    create_scoped_registry,
    get_global_registry
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


class MockAgent:
    """Mock agent for testing - represents a real agent interface."""
    
    def __init__(self, name: str, capabilities: Optional[List[str]] = None):
        self.name = name
        self.capabilities = capabilities or []
        self.execution_count = 0
        self.websocket_bridge = None
        self.user_context = None
        
    def set_websocket_bridge(self, bridge):
        """Set WebSocket bridge for real integration."""
        self.websocket_bridge = bridge
        
    def set_user_context(self, context: UserExecutionContext):
        """Set user context for isolation."""
        self.user_context = context
        
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Mock execution for integration testing."""
        self.execution_count += 1
        await asyncio.sleep(0.001)  # Simulate async work
        return {
            "success": True,
            "result": f"Agent {self.name} executed successfully",
            "execution_count": self.execution_count,
            "context_isolated": self.user_context is not None
        }


class MockWebSocketManager:
    """Mock WebSocket manager for testing WebSocket integration."""
    
    def __init__(self):
        self.events_sent = []
        self.connections = {}
        
    async def notify_agent_started(self, run_id: str, agent_name: str, metadata: Dict[str, Any]):
        """Mock WebSocket notification."""
        event = {
            "type": "agent_started",
            "run_id": run_id,
            "agent_name": agent_name,
            "metadata": metadata,
            "timestamp": time.time()
        }
        self.events_sent.append(event)
        return True
        
    async def notify_agent_completed(self, run_id: str, agent_name: str, result: Dict[str, Any], **kwargs):
        """Mock WebSocket completion notification."""
        event = {
            "type": "agent_completed", 
            "run_id": run_id,
            "agent_name": agent_name,
            "result": result,
            "timestamp": time.time()
        }
        self.events_sent.append(event)
        return True
        
    def get_events_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Get events for specific run."""
        return [event for event in self.events_sent if event.get("run_id") == run_id]


class TestAgentRegistryFactory(SSotAsyncTestCase):
    """Integration tests for Agent Registry and Factory patterns.
    
    Tests REAL component interactions without Docker dependencies.
    """
    
    def setup_method(self, method=None):
        """Setup for each test with real components."""
        super().setup_method(method)
        
        # Create real UniversalRegistry instance (no mocks)
        self.registry = UniversalRegistry[MockAgent]("TestAgentRegistry")
        
        # Create real AgentRegistry with specializations
        self.agent_registry = AgentRegistry()
        
        # Create real WebSocket manager mock (represents real interface)
        self.websocket_manager = MockWebSocketManager()
        
        # Create real user contexts for isolation testing
        self.user1_context = UserExecutionContext(
            user_id="test_user_001",
            thread_id="thread_001", 
            run_id="run_001",
            agent_context={"test": "integration"}
        )
        
        self.user2_context = UserExecutionContext(
            user_id="test_user_002",
            thread_id="thread_002",
            run_id="run_002", 
            agent_context={"test": "integration"}
        )
        
        # Track metrics
        self.record_metric("test_setup_time", time.time())
        
    async def test_universal_registry_basic_operations(self):
        """Test UniversalRegistry basic registration and retrieval operations.
        
        Business Value: Ensures agent registry basic functionality works.
        Tests REAL registry operations without mocks.
        """
        # Test singleton registration
        triage_agent = MockAgent("triage", ["data_analysis", "workflow_routing"])
        self.registry.register("triage", triage_agent, 
                             description="Triage agent for request routing",
                             tags=["core", "routing"])
        
        # Test registration validation
        assert self.registry.has("triage")
        assert len(self.registry) == 1
        assert "triage" in self.registry
        
        # Test retrieval
        retrieved_agent = self.registry.get("triage")
        assert retrieved_agent is triage_agent
        assert retrieved_agent.name == "triage"
        assert "data_analysis" in retrieved_agent.capabilities
        
        # Test metrics and health
        metrics = self.registry.get_metrics()
        assert metrics["total_items"] == 1
        assert metrics["registry_name"] == "TestAgentRegistry"
        assert metrics["metrics"]["successful_registrations"] == 1
        
        health = self.registry.validate_health()
        assert health["status"] == "healthy"
        assert len(health["issues"]) == 0
        
        # Record integration metrics
        self.record_metric("agents_registered", 1)
        self.record_metric("registry_operations", 4)
        
    async def test_factory_pattern_user_isolation(self):
        """Test factory pattern for user isolation.
        
        Business Value: Ensures multi-user agent isolation works correctly.
        Tests REAL factory creation with user contexts.
        """
        # Register factory for user-isolated agents
        def create_data_agent(user_context: UserExecutionContext) -> MockAgent:
            agent = MockAgent(f"data_{user_context.user_id}", ["data_processing"])
            agent.set_user_context(user_context)
            return agent
        
        self.registry.register_factory("data", create_data_agent,
                                     description="Data processing agent factory",
                                     tags=["factory", "isolated"])
        
        # Test factory creation for different users
        user1_agent = self.registry.create_instance("data", self.user1_context)
        user2_agent = self.registry.create_instance("data", self.user2_context)
        
        # Verify isolation
        assert user1_agent is not user2_agent
        assert user1_agent.name == "data_test_user_001"
        assert user2_agent.name == "data_test_user_002"
        assert user1_agent.user_context.user_id == "test_user_001"
        assert user2_agent.user_context.user_id == "test_user_002"
        
        # Test execution isolation
        result1 = await user1_agent.execute({"task": "process_data"})
        result2 = await user2_agent.execute({"task": "process_data"})
        
        assert result1["context_isolated"] is True
        assert result2["context_isolated"] is True
        assert user1_agent.execution_count == 1
        assert user2_agent.execution_count == 1
        
        # Record isolation metrics
        self.record_metric("isolated_agents_created", 2)
        self.record_metric("context_isolation_verified", True)
        
    async def test_agent_registry_websocket_integration(self):
        """Test AgentRegistry WebSocket manager integration.
        
        Business Value: Ensures WebSocket events work with agent registry.
        Tests REAL WebSocket integration without mocking core functionality.
        """
        # Set WebSocket manager on registry
        self.agent_registry.set_websocket_manager(self.websocket_manager)
        
        # Verify WebSocket manager is set
        assert self.agent_registry.websocket_manager is self.websocket_manager
        
        # Register an agent 
        optimizer_agent = MockAgent("optimizer", ["cost_optimization"])
        self.agent_registry.register("optimizer", optimizer_agent,
                                   tags=["business", "optimization"])
        
        # Create agent with context (this should set up WebSocket bridge)
        created_agent = self.agent_registry.create_agent_with_context(
            "optimizer",
            self.user1_context,
            llm_manager=MagicMock(),  # OK for non-core dependencies
            tool_dispatcher=MagicMock()  # OK for non-core dependencies
        )
        
        # Verify WebSocket bridge integration
        assert created_agent.websocket_bridge is not None
        
        # Test tool dispatcher enhancement (mock is allowed for this dependency)
        tool_dispatcher = self.agent_registry.tool_dispatcher
        assert tool_dispatcher is not None
        
        # For mock tool dispatcher, verify it was enhanced
        if hasattr(tool_dispatcher, '_websocket_enhanced'):
            assert tool_dispatcher._websocket_enhanced is True
        
        # Record WebSocket metrics  
        self.record_metric("websocket_integrations", 1)
        self.record_metric("agents_with_websocket", 1)
        
    async def test_registry_categorization_and_tags(self):
        """Test registry categorization and tag-based operations.
        
        Business Value: Ensures agent categorization works for business workflows.
        Tests REAL tag-based filtering and categorization.
        """
        # Register agents with different categories
        agents_config = [
            ("triage", ["routing", "analysis"], ["core", "entry_point"]),
            ("data_processor", ["data_processing", "etl"], ["business", "data"]),
            ("optimizer", ["optimization", "cost_analysis"], ["business", "optimization"]),
            ("reporter", ["reporting", "visualization"], ["business", "output"]),
            ("validator", ["validation", "quality"], ["core", "quality"])
        ]
        
        for name, capabilities, tags in agents_config:
            agent = MockAgent(name, capabilities)
            self.registry.register(name, agent, tags=tags, category="business_agent")
        
        # Test tag-based retrieval
        core_agents = self.registry.list_by_tag("core")
        business_agents = self.registry.list_by_tag("business")
        
        assert len(core_agents) == 2
        assert "triage" in core_agents
        assert "validator" in core_agents
        
        assert len(business_agents) == 3
        assert "data_processor" in business_agents
        assert "optimizer" in business_agents
        assert "reporter" in business_agents
        
        # Test comprehensive metrics
        metrics = self.registry.get_metrics()
        assert metrics["total_items"] == 5
        assert "core" in metrics["category_distribution"]
        assert "business" in metrics["category_distribution"]
        assert metrics["category_distribution"]["core"] == 2
        assert metrics["category_distribution"]["business"] == 3
        
        # Test registry listing
        all_keys = self.registry.list_keys()
        assert len(all_keys) == 5
        assert set(all_keys) == {"triage", "data_processor", "optimizer", "reporter", "validator"}
        
        # Record categorization metrics
        self.record_metric("total_categories", len(set(tags for _, _, tags_list in agents_config for tags in tags_list)))
        self.record_metric("agents_by_category", len(agents_config))
        
    async def test_scoped_registry_creation_and_isolation(self):
        """Test scoped registry creation for request isolation.
        
        Business Value: Ensures request-scoped registries provide proper isolation.
        Tests REAL scoped registry creation and isolation.
        """
        # Create scoped registries for different requests
        request1_registry = create_scoped_registry("agent", "request_001") 
        request2_registry = create_scoped_registry("agent", "request_002")
        
        # Verify they are different instances
        assert request1_registry is not request2_registry
        assert request1_registry.name == "agent_request_001"
        assert request2_registry.name == "agent_request_002"
        
        # Register different agents in each scope
        agent1 = MockAgent("scoped_agent_1", ["task1"])
        agent2 = MockAgent("scoped_agent_2", ["task2"])
        
        request1_registry.register("task_agent", agent1)
        request2_registry.register("task_agent", agent2)  # Same key, different scope
        
        # Verify isolation
        retrieved1 = request1_registry.get("task_agent")
        retrieved2 = request2_registry.get("task_agent")
        
        assert retrieved1 is agent1
        assert retrieved2 is agent2 
        assert retrieved1 is not retrieved2
        assert retrieved1.name == "scoped_agent_1"
        assert retrieved2.name == "scoped_agent_2"
        
        # Test cross-registry isolation
        assert request1_registry.get("task_agent") is not None
        assert request2_registry.get("task_agent") is not None
        assert len(request1_registry) == 1
        assert len(request2_registry) == 1
        
        # Test global registry access (should be isolated)
        global_agent_registry = get_global_registry("agent")
        assert global_agent_registry is not request1_registry
        assert global_agent_registry is not request2_registry
        
        # Record scoped registry metrics
        self.record_metric("scoped_registries_created", 2)
        self.record_metric("scoped_isolation_verified", True)
        self.record_metric("global_registry_isolated", True)
        
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        # Record final metrics
        final_metrics = self.get_all_metrics()
        
        # Log key metrics for integration test monitoring
        if hasattr(self, 'registry') and self.registry:
            registry_metrics = self.registry.get_metrics()
            self.record_metric("final_registry_items", registry_metrics["total_items"])
            self.record_metric("final_success_rate", registry_metrics["success_rate"])
        
        # Cleanup registries to prevent state leakage
        if hasattr(self, 'registry'):
            self.registry.clear()
        if hasattr(self, 'agent_registry'):
            # AgentRegistry doesn't have clear method, just remove references
            self.agent_registry = None
            
        super().teardown_method(method)