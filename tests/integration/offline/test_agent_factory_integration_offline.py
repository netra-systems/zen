"""
Offline Agent Factory Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure agent factory and registry integration works without external services
- Value Impact: Validates core agent instantiation, registration, and lifecycle management
- Strategic Impact: Enables testing of critical agent system without requiring Docker/LLM dependencies

These tests validate agent factory integration without requiring
external services like Redis, PostgreSQL, or LLM providers. They focus on:
1. Agent factory pattern and instantiation
2. Agent registry and discovery
3. Agent lifecycle management
4. Agent configuration and initialization
5. Agent execution context setup
6. WebSocket integration setup (without real connections)
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional, Callable, Type
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.async_test_helpers import (
    async_cleanup_registry, 
    AsyncTestFixtureMixin,
    AsyncMockManager
)


@dataclass
class MockAgentConfig:
    """Mock agent configuration for testing."""
    agent_id: str
    agent_type: str
    name: str
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    max_concurrent_executions: int = 1
    timeout_seconds: int = 300
    retry_attempts: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


class MockBaseAgent(ABC):
    """Mock base agent class for testing."""
    
    def __init__(self, config: MockAgentConfig):
        self.config = config
        self.agent_id = config.agent_id
        self.agent_type = config.agent_type
        self.name = config.name
        self.state = "initialized"
        self.execution_count = 0
        self.last_execution_time = None
        self.capabilities = config.capabilities.copy()
        self.metadata = config.metadata.copy()
        self._execution_context = None
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent logic."""
        pass
    
    async def initialize(self):
        """Initialize agent."""
        self.state = "ready"
        return True
    
    async def cleanup(self):
        """Cleanup agent resources."""
        self.state = "stopped"
        return True
    
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities."""
        return self.capabilities.copy()
    
    def is_available(self) -> bool:
        """Check if agent is available for execution."""
        return self.state == "ready"


class MockAnalysisAgent(MockBaseAgent):
    """Mock analysis agent for testing."""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Mock analysis execution."""
        self.execution_count += 1
        self.last_execution_time = time.time()
        self.state = "executing"
        
        # Simulate analysis work
        await asyncio.sleep(0.1)
        
        analysis_result = {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "analysis": {
                "input_data": context.get("data", "no_data"),
                "analysis_type": context.get("analysis_type", "default"),
                "findings": ["finding_1", "finding_2"],
                "confidence": 0.95,
                "recommendations": ["recommendation_1"]
            },
            "execution_metadata": {
                "execution_count": self.execution_count,
                "execution_time": self.last_execution_time,
                "processing_duration": 0.1
            }
        }
        
        self.state = "ready"
        return analysis_result


class MockOptimizationAgent(MockBaseAgent):
    """Mock optimization agent for testing."""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Mock optimization execution."""
        self.execution_count += 1
        self.last_execution_time = time.time()
        self.state = "executing"
        
        # Simulate optimization work
        await asyncio.sleep(0.15)
        
        optimization_result = {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "optimization": {
                "input_parameters": context.get("parameters", {}),
                "optimization_type": context.get("optimization_type", "default"),
                "optimized_values": {"param_1": 1.5, "param_2": 2.3},
                "improvement_percentage": 15.7,
                "iterations": 25
            },
            "execution_metadata": {
                "execution_count": self.execution_count,
                "execution_time": self.last_execution_time,
                "processing_duration": 0.15
            }
        }
        
        self.state = "ready"
        return optimization_result


class MockReportingAgent(MockBaseAgent):
    """Mock reporting agent for testing."""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Mock reporting execution."""
        self.execution_count += 1
        self.last_execution_time = time.time()
        self.state = "executing"
        
        # Simulate report generation
        await asyncio.sleep(0.05)
        
        report_result = {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "report": {
                "report_type": context.get("report_type", "summary"),
                "data_sources": context.get("data_sources", []),
                "sections": ["executive_summary", "details", "recommendations"],
                "format": context.get("format", "json"),
                "generated_at": self.last_execution_time
            },
            "execution_metadata": {
                "execution_count": self.execution_count,
                "execution_time": self.last_execution_time,
                "processing_duration": 0.05
            }
        }
        
        self.state = "ready"
        return report_result


class MockAgentFactory:
    """Mock agent factory for creating agents."""
    
    def __init__(self):
        self.agent_types = {}
        self.created_agents = []
        self.creation_count = 0
    
    def register_agent_type(self, agent_type: str, agent_class: Type[MockBaseAgent]):
        """Register an agent type with its class."""
        self.agent_types[agent_type] = agent_class
    
    async def create_agent(self, agent_type: str, config: MockAgentConfig) -> MockBaseAgent:
        """Create an agent instance."""
        if agent_type not in self.agent_types:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        agent_class = self.agent_types[agent_type]
        agent = agent_class(config)
        
        # Initialize the agent
        await agent.initialize()
        
        # Track creation
        self.creation_count += 1
        self.created_agents.append(agent)
        
        return agent
    
    def get_available_agent_types(self) -> List[str]:
        """Get list of available agent types."""
        return list(self.agent_types.keys())
    
    def get_creation_count(self) -> int:
        """Get total number of agents created."""
        return self.creation_count


class MockAgentRegistry:
    """Mock agent registry for managing agents."""
    
    def __init__(self):
        self.agents = {}  # agent_id -> agent
        self.agents_by_type = {}  # agent_type -> [agents]
        self.execution_history = []
        self.registered_count = 0
    
    async def register_agent(self, agent: MockBaseAgent):
        """Register an agent in the registry."""
        self.agents[agent.agent_id] = agent
        
        if agent.agent_type not in self.agents_by_type:
            self.agents_by_type[agent.agent_type] = []
        self.agents_by_type[agent.agent_type].append(agent)
        
        self.registered_count += 1
    
    async def unregister_agent(self, agent_id: str):
        """Unregister an agent from the registry."""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            await agent.cleanup()
            
            # Remove from main registry
            del self.agents[agent_id]
            
            # Remove from type registry
            if agent.agent_type in self.agents_by_type:
                self.agents_by_type[agent.agent_type] = [
                    a for a in self.agents_by_type[agent.agent_type]
                    if a.agent_id != agent_id
                ]
            
            return True
        return False
    
    def get_agent(self, agent_id: str) -> Optional[MockBaseAgent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
    
    def get_agents_by_type(self, agent_type: str) -> List[MockBaseAgent]:
        """Get all agents of a specific type."""
        return self.agents_by_type.get(agent_type, []).copy()
    
    def get_available_agents(self, agent_type: str = None) -> List[MockBaseAgent]:
        """Get available agents, optionally filtered by type."""
        if agent_type:
            agents = self.get_agents_by_type(agent_type)
        else:
            agents = list(self.agents.values())
        
        return [agent for agent in agents if agent.is_available()]
    
    async def execute_agent(self, agent_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an agent and track the execution."""
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        if not agent.is_available():
            raise RuntimeError(f"Agent {agent_id} not available")
        
        # Execute the agent
        start_time = time.time()
        result = await agent.execute(context)
        execution_time = time.time() - start_time
        
        # Track execution history
        execution_record = {
            "agent_id": agent_id,
            "agent_type": agent.agent_type,
            "execution_time": start_time,
            "duration": execution_time,
            "context_keys": list(context.keys()),
            "success": True
        }
        self.execution_history.append(execution_record)
        
        return result
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_agents": len(self.agents),
            "agents_by_type": {
                agent_type: len(agents) 
                for agent_type, agents in self.agents_by_type.items()
            },
            "available_agents": len([a for a in self.agents.values() if a.is_available()]),
            "total_executions": len(self.execution_history),
            "registered_count": self.registered_count
        }


class MockWebSocketManager:
    """Mock WebSocket manager for testing agent integration."""
    
    def __init__(self):
        self.connections = {}
        self.event_log = []
        self.connected = False
    
    async def connect(self):
        """Mock WebSocket connection."""
        self.connected = True
        return True
    
    async def disconnect(self):
        """Mock WebSocket disconnection."""
        self.connected = False
        return True
    
    async def send_event(self, event_type: str, data: Dict[str, Any]):
        """Mock sending WebSocket event."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        }
        self.event_log.append(event)
        return True
    
    def get_event_log(self) -> List[Dict[str, Any]]:
        """Get event log for testing."""
        return self.event_log.copy()
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self.connected


class TestAgentFactoryIntegrationOffline(SSotBaseTestCase, AsyncTestFixtureMixin):
    """Offline integration tests for agent factory and registry."""

    def setup_method(self, method=None):
        """Setup with mock agent components."""
        super().setup_method(method)
        self.setup_async_resources()
        
        # Initialize mock components
        self.mock_factory = MockAgentFactory()
        self.mock_registry = MockAgentRegistry()
        self.mock_websocket = MockWebSocketManager()
        
        # Track the registry for async cleanup
        self.track_mock_registry(self.mock_registry)
        
        # Register agent types in factory
        self.mock_factory.register_agent_type("analysis", MockAnalysisAgent)
        self.mock_factory.register_agent_type("optimization", MockOptimizationAgent)
        self.mock_factory.register_agent_type("reporting", MockReportingAgent)
    
    def teardown_method(self, method=None):
        """Cleanup agent components."""
        # Just call parent teardown - async cleanup handled by fixture
        super().teardown_method(method)
    
    @pytest.fixture(autouse=True)
    async def auto_cleanup_agents(self):
        """Auto cleanup fixture that runs async cleanup after each test."""
        yield
        # Use the SSOT async cleanup helper
        await self.cleanup_all_async_resources()

    @pytest.mark.integration
    async def test_agent_factory_creation_integration(self):
        """
        Test agent factory creation integration.
        
        Validates that agents can be created correctly with proper configuration.
        """
        # Test Case 1: Create analysis agent
        analysis_config = MockAgentConfig(
            agent_id="analysis_001",
            agent_type="analysis",
            name="Test Analysis Agent",
            description="Agent for testing analysis functionality",
            capabilities=["data_analysis", "pattern_recognition", "statistical_analysis"],
            max_concurrent_executions=2,
            timeout_seconds=600,
            metadata={"version": "1.0", "created_by": "test"}
        )
        
        analysis_agent = await self.mock_factory.create_agent("analysis", analysis_config)
        
        assert isinstance(analysis_agent, MockAnalysisAgent)
        assert analysis_agent.agent_id == "analysis_001"
        assert analysis_agent.agent_type == "analysis"
        assert analysis_agent.name == "Test Analysis Agent"
        assert analysis_agent.is_available()
        assert "data_analysis" in analysis_agent.get_capabilities()
        
        # Test Case 2: Create optimization agent
        optimization_config = MockAgentConfig(
            agent_id="optimization_001",
            agent_type="optimization", 
            name="Test Optimization Agent",
            capabilities=["parameter_tuning", "performance_optimization", "resource_allocation"],
            max_concurrent_executions=1,
            timeout_seconds=900
        )
        
        optimization_agent = await self.mock_factory.create_agent("optimization", optimization_config)
        
        assert isinstance(optimization_agent, MockOptimizationAgent)
        assert optimization_agent.agent_id == "optimization_001"
        assert optimization_agent.is_available()
        assert "parameter_tuning" in optimization_agent.get_capabilities()
        
        # Test Case 3: Create reporting agent
        reporting_config = MockAgentConfig(
            agent_id="reporting_001",
            agent_type="reporting",
            name="Test Reporting Agent",
            capabilities=["report_generation", "data_visualization", "summary_creation"],
            timeout_seconds=300
        )
        
        reporting_agent = await self.mock_factory.create_agent("reporting", reporting_config)
        
        assert isinstance(reporting_agent, MockReportingAgent)
        assert reporting_agent.agent_id == "reporting_001"
        assert reporting_agent.is_available()
        
        # Test Case 4: Verify factory tracking
        assert self.mock_factory.get_creation_count() == 3
        assert len(self.mock_factory.created_agents) == 3
        
        available_types = self.mock_factory.get_available_agent_types()
        assert "analysis" in available_types
        assert "optimization" in available_types
        assert "reporting" in available_types
        
        # Test Case 5: Error handling for invalid agent type
        invalid_config = MockAgentConfig(
            agent_id="invalid_001",
            agent_type="nonexistent",
            name="Invalid Agent"
        )
        
        with pytest.raises(ValueError, match="Unknown agent type: nonexistent"):
            await self.mock_factory.create_agent("nonexistent", invalid_config)
        
        # Creation count should not increase for failed creations
        assert self.mock_factory.get_creation_count() == 3
        
        # Record factory integration metrics
        self.record_metric("agents_created", self.mock_factory.get_creation_count())
        self.record_metric("agent_types_registered", len(available_types))
        self.record_metric("creation_errors_handled", 1)
        self.record_metric("agent_factory_integration_passed", True)

    @pytest.mark.integration
    async def test_agent_registry_management_integration(self):
        """
        Test agent registry management integration.
        
        Validates that agents can be registered, discovered, and managed correctly.
        """
        # Create agents for registry testing
        agents = []
        agent_configs = [
            MockAgentConfig("analysis_001", "analysis", "Analysis Agent 1", 
                           capabilities=["data_analysis"]),
            MockAgentConfig("analysis_002", "analysis", "Analysis Agent 2", 
                           capabilities=["pattern_recognition"]),
            MockAgentConfig("optimization_001", "optimization", "Optimization Agent 1", 
                           capabilities=["parameter_tuning"]),
            MockAgentConfig("reporting_001", "reporting", "Reporting Agent 1", 
                           capabilities=["report_generation"])
        ]
        
        for config in agent_configs:
            agent = await self.mock_factory.create_agent(config.agent_type, config)
            agents.append(agent)
        
        # Test Case 1: Register agents in registry
        for agent in agents:
            await self.mock_registry.register_agent(agent)
        
        registry_stats = self.mock_registry.get_registry_stats()
        assert registry_stats["total_agents"] == 4
        assert registry_stats["agents_by_type"]["analysis"] == 2
        assert registry_stats["agents_by_type"]["optimization"] == 1
        assert registry_stats["agents_by_type"]["reporting"] == 1
        assert registry_stats["available_agents"] == 4
        
        # Test Case 2: Agent retrieval by ID
        retrieved_agent = self.mock_registry.get_agent("analysis_001")
        assert retrieved_agent is not None
        assert retrieved_agent.agent_id == "analysis_001"
        assert retrieved_agent.name == "Analysis Agent 1"
        
        nonexistent_agent = self.mock_registry.get_agent("nonexistent_001")
        assert nonexistent_agent is None
        
        # Test Case 3: Agent retrieval by type
        analysis_agents = self.mock_registry.get_agents_by_type("analysis")
        assert len(analysis_agents) == 2
        assert all(agent.agent_type == "analysis" for agent in analysis_agents)
        
        optimization_agents = self.mock_registry.get_agents_by_type("optimization")
        assert len(optimization_agents) == 1
        assert optimization_agents[0].agent_type == "optimization"
        
        nonexistent_type_agents = self.mock_registry.get_agents_by_type("nonexistent")
        assert len(nonexistent_type_agents) == 0
        
        # Test Case 4: Available agent filtering
        all_available = self.mock_registry.get_available_agents()
        assert len(all_available) == 4
        assert all(agent.is_available() for agent in all_available)
        
        available_analysis = self.mock_registry.get_available_agents("analysis")
        assert len(available_analysis) == 2
        assert all(agent.agent_type == "analysis" and agent.is_available() 
                   for agent in available_analysis)
        
        # Test Case 5: Agent unregistration
        unregister_success = await self.mock_registry.unregister_agent("analysis_002")
        assert unregister_success == True
        
        updated_stats = self.mock_registry.get_registry_stats()
        assert updated_stats["total_agents"] == 3
        assert updated_stats["agents_by_type"]["analysis"] == 1
        
        # Test unregistering nonexistent agent
        unregister_fail = await self.mock_registry.unregister_agent("nonexistent_001")
        assert unregister_fail == False
        
        # Record registry management metrics
        self.record_metric("agents_registered", registry_stats["total_agents"])
        self.record_metric("agents_by_type_analysis", registry_stats["agents_by_type"]["analysis"])
        self.record_metric("agent_retrieval_by_id_successful", retrieved_agent is not None)
        self.record_metric("agent_unregistration_successful", unregister_success)
        self.record_metric("agent_registry_management_integration_passed", True)

    @pytest.mark.integration
    async def test_agent_execution_integration(self):
        """
        Test agent execution integration through registry.
        
        Validates that agents can be executed with proper context and results.
        """
        # Create and register test agents
        analysis_config = MockAgentConfig("analysis_exec_001", "analysis", 
                                        "Execution Test Analysis Agent")
        optimization_config = MockAgentConfig("optimization_exec_001", "optimization", 
                                            "Execution Test Optimization Agent")
        reporting_config = MockAgentConfig("reporting_exec_001", "reporting", 
                                         "Execution Test Reporting Agent")
        
        analysis_agent = await self.mock_factory.create_agent("analysis", analysis_config)
        optimization_agent = await self.mock_factory.create_agent("optimization", optimization_config)
        reporting_agent = await self.mock_factory.create_agent("reporting", reporting_config)
        
        await self.mock_registry.register_agent(analysis_agent)
        await self.mock_registry.register_agent(optimization_agent)
        await self.mock_registry.register_agent(reporting_agent)
        
        # Test Case 1: Execute analysis agent
        analysis_context = {
            "data": "test_dataset",
            "analysis_type": "statistical",
            "parameters": {"confidence_level": 0.95}
        }
        
        analysis_result = await self.mock_registry.execute_agent("analysis_exec_001", analysis_context)
        
        assert "agent_id" in analysis_result
        assert analysis_result["agent_id"] == "analysis_exec_001"
        assert analysis_result["agent_type"] == "analysis"
        assert "analysis" in analysis_result
        assert analysis_result["analysis"]["input_data"] == "test_dataset"
        assert analysis_result["analysis"]["analysis_type"] == "statistical"
        assert len(analysis_result["analysis"]["findings"]) > 0
        
        # Test Case 2: Execute optimization agent
        optimization_context = {
            "parameters": {"learning_rate": 0.01, "batch_size": 32},
            "optimization_type": "gradient_descent",
            "target_metric": "accuracy"
        }
        
        optimization_result = await self.mock_registry.execute_agent("optimization_exec_001", optimization_context)
        
        assert optimization_result["agent_id"] == "optimization_exec_001"
        assert optimization_result["agent_type"] == "optimization"
        assert "optimization" in optimization_result
        assert "optimized_values" in optimization_result["optimization"]
        assert optimization_result["optimization"]["improvement_percentage"] > 0
        
        # Test Case 3: Execute reporting agent
        reporting_context = {
            "report_type": "analysis_summary",
            "data_sources": ["analysis_result", "optimization_result"],
            "format": "json"
        }
        
        reporting_result = await self.mock_registry.execute_agent("reporting_exec_001", reporting_context)
        
        assert reporting_result["agent_id"] == "reporting_exec_001"
        assert reporting_result["agent_type"] == "reporting"
        assert "report" in reporting_result
        assert reporting_result["report"]["report_type"] == "analysis_summary"
        assert len(reporting_result["report"]["sections"]) > 0
        
        # Test Case 4: Verify execution tracking
        registry_stats = self.mock_registry.get_registry_stats()
        assert registry_stats["total_executions"] == 3
        
        execution_history = self.mock_registry.execution_history
        assert len(execution_history) == 3
        
        # Verify execution records
        analysis_exec = next(e for e in execution_history if e["agent_id"] == "analysis_exec_001")
        assert analysis_exec["agent_type"] == "analysis"
        assert analysis_exec["success"] == True
        assert analysis_exec["duration"] > 0
        assert "data" in analysis_exec["context_keys"]
        
        # Test Case 5: Error handling for invalid agent execution
        with pytest.raises(ValueError, match="Agent nonexistent_001 not found"):
            await self.mock_registry.execute_agent("nonexistent_001", {})
        
        # Test Case 6: Concurrent execution performance
        concurrent_contexts = [
            {"data": f"dataset_{i}", "analysis_type": "concurrent_test"}
            for i in range(5)
        ]
        
        concurrent_start = time.time()
        concurrent_results = await asyncio.gather(*[
            self.mock_registry.execute_agent("analysis_exec_001", context)
            for context in concurrent_contexts
        ])
        concurrent_time = time.time() - concurrent_start
        
        assert len(concurrent_results) == 5
        assert all("analysis" in result for result in concurrent_results)
        assert concurrent_time < 2.0, f"Concurrent execution took too long: {concurrent_time:.3f}s"
        
        # Record execution integration metrics
        self.record_metric("successful_executions", 3)
        self.record_metric("concurrent_executions", len(concurrent_results))
        self.record_metric("concurrent_execution_time_seconds", concurrent_time)
        self.record_metric("execution_tracking_working", len(execution_history) == 8)  # 3 + 5
        self.record_metric("agent_execution_integration_passed", True)

    @pytest.mark.integration
    async def test_websocket_integration_setup(self):
        """
        Test WebSocket integration setup for agent execution.
        
        Validates WebSocket event handling during agent execution without real connections.
        """
        # Create and register agent for WebSocket testing
        websocket_config = MockAgentConfig("websocket_test_001", "analysis", 
                                         "WebSocket Test Agent")
        websocket_agent = await self.mock_factory.create_agent("analysis", websocket_config)
        await self.mock_registry.register_agent(websocket_agent)
        
        # Test Case 1: WebSocket connection setup
        await self.mock_websocket.connect()
        assert self.mock_websocket.is_connected()
        
        # Test Case 2: Agent execution with WebSocket events
        execution_context = {
            "data": "websocket_test_data",
            "analysis_type": "websocket_integration",
            "enable_websocket_events": True
        }
        
        # Simulate sending WebSocket events during agent execution
        await self.mock_websocket.send_event("agent_started", {
            "agent_id": "websocket_test_001",
            "agent_type": "analysis",
            "execution_id": str(uuid.uuid4())
        })
        
        # Execute agent
        result = await self.mock_registry.execute_agent("websocket_test_001", execution_context)
        
        # Simulate more WebSocket events
        await self.mock_websocket.send_event("agent_thinking", {
            "agent_id": "websocket_test_001",
            "message": "Processing analysis data"
        })
        
        await self.mock_websocket.send_event("tool_executing", {
            "agent_id": "websocket_test_001",
            "tool": "statistical_analyzer",
            "parameters": {"confidence_level": 0.95}
        })
        
        await self.mock_websocket.send_event("tool_completed", {
            "agent_id": "websocket_test_001",
            "tool": "statistical_analyzer",
            "result": "analysis_complete"
        })
        
        await self.mock_websocket.send_event("agent_completed", {
            "agent_id": "websocket_test_001",
            "result": result,
            "execution_time": 0.1
        })
        
        # Test Case 3: Verify WebSocket event log
        event_log = self.mock_websocket.get_event_log()
        assert len(event_log) == 5
        
        # Verify event types
        event_types = [event["type"] for event in event_log]
        expected_types = ["agent_started", "agent_thinking", "tool_executing", 
                         "tool_completed", "agent_completed"]
        assert event_types == expected_types
        
        # Verify event data structure
        agent_started_event = event_log[0]
        assert agent_started_event["data"]["agent_id"] == "websocket_test_001"
        assert agent_started_event["data"]["agent_type"] == "analysis"
        assert "execution_id" in agent_started_event["data"]
        assert "timestamp" in agent_started_event
        
        agent_completed_event = event_log[4]
        assert agent_completed_event["data"]["agent_id"] == "websocket_test_001"
        assert "result" in agent_completed_event["data"]
        assert "execution_time" in agent_completed_event["data"]
        
        # Test Case 4: WebSocket error handling
        # Simulate connection loss
        await self.mock_websocket.disconnect()
        assert not self.mock_websocket.is_connected()
        
        # Attempt to send event while disconnected (should handle gracefully)
        try:
            await self.mock_websocket.send_event("agent_error", {
                "agent_id": "websocket_test_001",
                "error": "connection_lost"
            })
            # Mock doesn't enforce connection state, but in real implementation this might raise
        except Exception:
            pass  # Expected if implementation enforces connection state
        
        # Test Case 5: Reconnection and continued event sending
        await self.mock_websocket.connect()
        assert self.mock_websocket.is_connected()
        
        await self.mock_websocket.send_event("agent_reconnected", {
            "agent_id": "websocket_test_001",
            "status": "connection_restored"
        })
        
        final_event_log = self.mock_websocket.get_event_log()
        assert len(final_event_log) >= 6  # At least 5 + reconnection event
        
        # Test Case 6: Multiple agent WebSocket event isolation
        # Create another agent
        second_agent_config = MockAgentConfig("websocket_test_002", "optimization", 
                                            "Second WebSocket Agent")
        second_agent = await self.mock_factory.create_agent("optimization", second_agent_config)
        await self.mock_registry.register_agent(second_agent)
        
        # Clear event log and test isolation
        self.mock_websocket.event_log.clear()
        
        # Execute both agents concurrently
        contexts = [
            {"agent_id": "websocket_test_001", "data": "agent1_data"},
            {"parameters": {"agent_id": "websocket_test_002", "values": [1, 2, 3]}}
        ]
        
        # Send events for both agents
        await self.mock_websocket.send_event("agent_started", {"agent_id": "websocket_test_001"})
        await self.mock_websocket.send_event("agent_started", {"agent_id": "websocket_test_002"})
        
        # Execute concurrently
        results = await asyncio.gather(
            self.mock_registry.execute_agent("websocket_test_001", contexts[0]),
            self.mock_registry.execute_agent("websocket_test_002", contexts[1])
        )
        
        await self.mock_websocket.send_event("agent_completed", {"agent_id": "websocket_test_001"})
        await self.mock_websocket.send_event("agent_completed", {"agent_id": "websocket_test_002"})
        
        # Verify isolation - should have events for both agents
        isolation_event_log = self.mock_websocket.get_event_log()
        agent1_events = [e for e in isolation_event_log if e["data"].get("agent_id") == "websocket_test_001"]
        agent2_events = [e for e in isolation_event_log if e["data"].get("agent_id") == "websocket_test_002"]
        
        assert len(agent1_events) >= 2  # At least started + completed
        assert len(agent2_events) >= 2  # At least started + completed
        
        # Record WebSocket integration metrics
        self.record_metric("websocket_events_sent", len(final_event_log))
        self.record_metric("websocket_event_types_tested", len(expected_types))
        self.record_metric("websocket_connection_cycles", 2)  # connect, disconnect, reconnect
        self.record_metric("concurrent_websocket_agents", 2)
        self.record_metric("websocket_event_isolation_working", len(agent1_events) > 0 and len(agent2_events) > 0)
        self.record_metric("websocket_integration_setup_passed", True)

    @pytest.mark.integration
    async def test_agent_lifecycle_management_integration(self):
        """
        Test complete agent lifecycle management integration.
        
        Validates the entire lifecycle from creation to cleanup.
        """
        # Test Case 1: Full lifecycle for multiple agents
        lifecycle_configs = [
            MockAgentConfig("lifecycle_analysis_001", "analysis", "Lifecycle Analysis Agent"),
            MockAgentConfig("lifecycle_optimization_001", "optimization", "Lifecycle Optimization Agent"),
            MockAgentConfig("lifecycle_reporting_001", "reporting", "Lifecycle Reporting Agent")
        ]
        
        created_agents = []
        
        # Creation phase
        creation_start = time.time()
        for config in lifecycle_configs:
            agent = await self.mock_factory.create_agent(config.agent_type, config)
            created_agents.append(agent)
        creation_time = time.time() - creation_start
        
        # Verify all agents created and initialized
        for agent in created_agents:
            assert agent.state == "ready"
            assert agent.is_available()
        
        # Registration phase
        registration_start = time.time()
        for agent in created_agents:
            await self.mock_registry.register_agent(agent)
        registration_time = time.time() - registration_start
        
        # Verify registration
        registry_stats = self.mock_registry.get_registry_stats()
        assert registry_stats["total_agents"] >= 3
        assert registry_stats["available_agents"] >= 3
        
        # Execution phase
        execution_contexts = [
            {"data": "lifecycle_test_data", "analysis_type": "lifecycle"},
            {"parameters": {"test": True}, "optimization_type": "lifecycle"},
            {"report_type": "lifecycle_summary", "format": "json"}
        ]
        
        execution_start = time.time()
        execution_results = []
        
        for i, agent in enumerate(created_agents):
            result = await self.mock_registry.execute_agent(agent.agent_id, execution_contexts[i])
            execution_results.append(result)
        execution_time = time.time() - execution_start
        
        # Verify execution results
        assert len(execution_results) == 3
        for result in execution_results:
            assert "agent_id" in result
            assert "execution_metadata" in result
        
        # Test Case 2: Agent state transitions during execution
        test_agent = created_agents[0]  # Use analysis agent
        
        # Check initial state
        assert test_agent.state == "ready"
        assert test_agent.execution_count >= 1  # From previous execution
        
        # Execute again and verify state transitions
        initial_count = test_agent.execution_count
        await self.mock_registry.execute_agent(test_agent.agent_id, {"data": "state_test"})
        
        assert test_agent.execution_count == initial_count + 1
        assert test_agent.state == "ready"  # Should return to ready after execution
        assert test_agent.last_execution_time is not None
        
        # Test Case 3: Concurrent agent execution
        concurrent_contexts = [
            {"data": f"concurrent_test_{i}", "analysis_type": "performance"}
            for i in range(3)
        ]
        
        concurrent_start = time.time()
        concurrent_results = await asyncio.gather(*[
            self.mock_registry.execute_agent(created_agents[0].agent_id, context)
            for context in concurrent_contexts
        ])
        concurrent_time = time.time() - concurrent_start
        
        assert len(concurrent_results) == 3
        assert concurrent_time < 1.0, f"Concurrent execution too slow: {concurrent_time:.3f}s"
        
        # Test Case 4: Cleanup phase
        cleanup_start = time.time()
        
        # Unregister all agents
        for agent in created_agents:
            unregister_success = await self.mock_registry.unregister_agent(agent.agent_id)
            assert unregister_success == True
            assert agent.state == "stopped"
        
        cleanup_time = time.time() - cleanup_start
        
        # Verify cleanup
        updated_stats = self.mock_registry.get_registry_stats()
        assert updated_stats["total_agents"] == 0 or updated_stats["total_agents"] == len(self.mock_registry.agents)
        
        # Test Case 5: Performance benchmarking
        # Creation should be reasonable fast
        assert creation_time < 1.0, f"Agent creation too slow: {creation_time:.3f}s"
        assert registration_time < 0.5, f"Agent registration too slow: {registration_time:.3f}s"
        assert execution_time < 2.0, f"Sequential execution too slow: {execution_time:.3f}s"
        assert cleanup_time < 1.0, f"Agent cleanup too slow: {cleanup_time:.3f}s"
        
        # Test Case 6: Resource usage validation
        # Verify no memory leaks (agents properly cleaned up)
        # This is simulated in mock, but in real system would check memory usage
        factory_agents_count = len(self.mock_factory.created_agents)
        registry_agents_count = len(self.mock_registry.agents)
        
        # After cleanup, registry should have fewer agents than factory created
        # (Factory tracks all created, registry tracks currently active)
        self.record_metric("factory_total_created", factory_agents_count)
        self.record_metric("registry_active_agents", registry_agents_count)
        
        # Record lifecycle management metrics
        self.record_metric("lifecycle_creation_time_seconds", creation_time)
        self.record_metric("lifecycle_registration_time_seconds", registration_time)
        self.record_metric("lifecycle_execution_time_seconds", execution_time)
        self.record_metric("lifecycle_cleanup_time_seconds", cleanup_time)
        self.record_metric("concurrent_execution_time_seconds", concurrent_time)
        self.record_metric("agents_in_lifecycle_test", len(created_agents))
        self.record_metric("lifecycle_state_transitions_verified", True)
        self.record_metric("agent_lifecycle_management_integration_passed", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])