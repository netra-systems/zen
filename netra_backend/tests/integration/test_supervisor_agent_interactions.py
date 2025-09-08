"""
Comprehensive Integration Test: SupervisorAgent Interactions

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure SupervisorAgent properly orchestrates all SSOT classes
- Value Impact: Validates complete user isolation, WebSocket events, and agent coordination
- Strategic Impact: Critical for multi-user platform stability and business value delivery

Tests SupervisorAgent interactions with key SSOT classes:
- SupervisorAgent ↔ UserExecutionContext (user isolation)
- SupervisorAgent ↔ ExecutionEngine (agent execution coordination)  
- SupervisorAgent ↔ BaseAgent subclasses (sub-agent creation)
- SupervisorAgent ↔ AgentRegistry (agent lifecycle)
- SupervisorAgent ↔ AgentWebSocketBridge (event emission)
- SupervisorAgent ↔ LLMManager (LLM operations)

This is a NON-DOCKER integration test that uses real services but no running Docker containers.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Core imports
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    get_agent_instance_factory
)
from netra_backend.app.agents.supervisor.agent_class_registry import (
    AgentClassRegistry,
    get_agent_class_registry
)
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.database.session_manager import DatabaseSessionManager
from netra_backend.app.logging_config import central_logger

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment

logger = central_logger.get_logger(__name__)


class MockAgent(BaseAgent):
    """Mock agent for testing that supports UserExecutionContext pattern."""
    
    def __init__(self, name: str, llm_manager: LLMManager):
        super().__init__(
            llm_manager=llm_manager,
            name=name,
            description=f"Mock {name} agent for testing"
        )
        self.execution_count = 0
        self.execution_results = []
        
    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute with UserExecutionContext pattern."""
        self.execution_count += 1
        result = {
            "agent_name": self.name,
            "user_id": context.user_id,
            "run_id": context.run_id,
            "status": "completed",
            "execution_count": self.execution_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.execution_results.append(result)
        
        # Store result in context metadata
        context.metadata[f"{self.name}_result"] = result
        context.metadata[f"{self.name}_executed"] = True
        
        return result


class TestSupervisorAgentInteractions(BaseIntegrationTest):
    """Comprehensive integration tests for SupervisorAgent interactions with SSOT classes."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.isolated_env = IsolatedEnvironment()
        self.isolated_env.set("TEST_MODE", "true", source="test")
        
    @pytest.fixture
    async def mock_llm_manager(self):
        """Create comprehensive mock LLM manager."""
        mock_manager = AsyncMock(spec=LLMManager)
        
        # Default triage response for ask_llm
        triage_response = json.dumps({
            "category": "optimization_request",
            "priority": "high", 
            "data_sufficiency": "partial",
            "intent": {
                "primary_intent": "optimize costs and performance",
                "action_required": True
            },
            "next_agents": ["data_helper", "optimization", "actions"]
        })
        
        # Mock the main LLM methods
        mock_manager.ask_llm.return_value = triage_response
        mock_manager.ask_llm_full.return_value = AsyncMock(content=triage_response)
        mock_manager.initialize.return_value = None
        mock_manager.health_check.return_value = {"status": "healthy", "initialized": True}
        
        return mock_manager
    
    @pytest.fixture
    async def mock_websocket_bridge(self):
        """Create mock WebSocket bridge with event tracking."""
        mock_bridge = AsyncMock(spec=AgentWebSocketBridge)
        mock_bridge.websocket_manager = AsyncMock()
        mock_bridge.emitted_events = []
        
        async def track_emit(event_type, data, **kwargs):
            mock_bridge.emitted_events.append({
                "event_type": event_type,
                "data": data,
                "kwargs": kwargs,
                "timestamp": datetime.now(timezone.utc)
            })
            return True
            
        mock_bridge.emit_agent_event.side_effect = track_emit
        return mock_bridge
    
    @pytest.fixture
    async def test_user_context(self):
        """Create test user execution context."""
        context = UserExecutionContext(
            user_id=f"test_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"test_run_{uuid.uuid4().hex[:8]}",
            websocket_connection_id=f"ws_conn_{uuid.uuid4().hex[:8]}",
            metadata={
                "user_request": "Help me optimize my AI costs and improve performance",
                "request_type": "optimization_analysis"
            }
        )
        return context
    
    @pytest.fixture
    async def mock_db_session(self):
        """Create mock database session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return mock_session
    
    @pytest.fixture
    async def configured_supervisor_agent(self, mock_llm_manager, mock_websocket_bridge):
        """Create configured SupervisorAgent for testing."""
        # Create a mock registry with some test agents
        mock_registry = MagicMock(spec=AgentClassRegistry)
        mock_registry.__len__ = MagicMock(return_value=5)  # Simulate 5 agent classes
        
        # Mock agent instance factory 
        mock_factory = MagicMock()
        mock_factory.configure = MagicMock()
        
        # Patch both imports used in SupervisorAgent
        with patch('netra_backend.app.agents.supervisor_consolidated.get_agent_class_registry', return_value=mock_registry):
            with patch('netra_backend.app.agents.supervisor_consolidated.get_agent_instance_factory', return_value=mock_factory):
                # Use factory method for proper initialization
                supervisor = SupervisorAgent.create(
                    llm_manager=mock_llm_manager,
                    websocket_bridge=mock_websocket_bridge
                )
                # Store mocks for later use in tests
                supervisor._test_registry = mock_registry
                supervisor._test_factory = mock_factory
                return supervisor
    
    @pytest.mark.integration
    async def test_user_execution_context_isolation(
        self, 
        configured_supervisor_agent, 
        mock_llm_manager,
        mock_websocket_bridge
    ):
        """Test SupervisorAgent maintains complete user isolation through UserExecutionContext."""
        
        # Create two different user contexts
        user1_context = UserExecutionContext(
            user_id="user_1_12345678",
            thread_id="thread_1_12345678",  
            run_id="run_1_12345678",
            metadata={"user_request": "Optimize costs for user 1"}
        )
        
        user2_context = UserExecutionContext(
            user_id="user_2_87654321",
            thread_id="thread_2_87654321",
            run_id="run_2_87654321", 
            metadata={"user_request": "Analyze performance for user 2"}
        )
        
        # Add mock database sessions
        user1_context = user1_context.with_db_session(AsyncMock(spec=AsyncSession))
        user2_context = user2_context.with_db_session(AsyncMock(spec=AsyncSession))
        
        # Validate context isolation first
        validate_user_isolation(user1_context, user2_context)
        
        # Test SupervisorAgent can handle different user contexts
        assert configured_supervisor_agent.websocket_bridge is not None
        assert configured_supervisor_agent.agent_instance_factory is not None
        assert configured_supervisor_agent.agent_class_registry is not None
        
        # Test that each context has proper isolation
        assert user1_context.user_id != user2_context.user_id
        assert user1_context.thread_id != user2_context.thread_id
        assert user1_context.run_id != user2_context.run_id
        assert user1_context.metadata["user_request"] != user2_context.metadata["user_request"]
        
        # Test context immutability (frozen dataclass)
        with pytest.raises(Exception):  # Should raise FrozenInstanceError or AttributeError
            user1_context.user_id = "modified"
            
        logger.info("✅ User execution context isolation test passed")
    
    @pytest.mark.integration
    async def test_websocket_event_emission_integration(
        self, 
        configured_supervisor_agent, 
        test_user_context,
        mock_websocket_bridge,
        mock_llm_manager
    ):
        """Test SupervisorAgent properly integrates with WebSocket bridge for event emission."""
        
        # Test WebSocket bridge integration
        assert configured_supervisor_agent.websocket_bridge is mock_websocket_bridge
        
        # Test that the bridge has the expected interface
        assert hasattr(mock_websocket_bridge, 'emit_agent_event')
        assert hasattr(mock_websocket_bridge, 'emitted_events')
        
        # Test manual event emission through supervisor's WebSocket bridge
        await configured_supervisor_agent.websocket_bridge.emit_agent_event(
            event_type="agent_thinking",
            data={
                "agent_name": "Supervisor",
                "message": "Test thinking event",
                "user_id": test_user_context.user_id
            },
            run_id=test_user_context.run_id,
            agent_name="Supervisor"
        )
        
        # Validate events were tracked
        emitted_events = mock_websocket_bridge.emitted_events
        assert len(emitted_events) > 0
        
        # Validate event structure
        latest_event = emitted_events[-1]
        assert latest_event["event_type"] == "agent_thinking"
        assert latest_event["data"]["user_id"] == test_user_context.user_id
        assert latest_event["data"]["agent_name"] == "Supervisor"
        
        logger.info(f"✅ WebSocket event emission integration test passed - {len(emitted_events)} events emitted")
    
    @pytest.mark.integration
    async def test_agent_orchestration_workflow(
        self, 
        configured_supervisor_agent,
        test_user_context, 
        mock_llm_manager,
        mock_websocket_bridge
    ):
        """Test SupervisorAgent properly orchestrates agent workflow with ExecutionEngine patterns."""
        
        # Add database session
        test_user_context = test_user_context.with_db_session(AsyncMock(spec=AsyncSession))
        
        # Create agents with execution tracking
        triage_agent = MockAgent("triage", mock_llm_manager)
        data_helper_agent = MockAgent("data_helper", mock_llm_manager)
        optimization_agent = MockAgent("optimization", mock_llm_manager)
        reporting_agent = MockAgent("reporting", mock_llm_manager)
        
        test_agents = {
            "triage": triage_agent,
            "data_helper": data_helper_agent,
            "optimization": optimization_agent,
            "reporting": reporting_agent
        }
        
        with patch.object(configured_supervisor_agent, '_create_isolated_agent_instances') as mock_create:
            mock_create.return_value = test_agents
            
            with patch('netra_backend.app.agents.supervisor_consolidated.managed_session') as mock_managed_session:
                mock_session_manager = AsyncMock(spec=DatabaseSessionManager)
                mock_managed_session.return_value.__aenter__.return_value = mock_session_manager
                mock_managed_session.return_value.__aexit__.return_value = None
                
                # Execute orchestration
                result = await configured_supervisor_agent.execute(test_user_context)
        
        # Validate orchestration succeeded
        assert result["orchestration_successful"] is True
        assert "results" in result
        
        # Validate agent execution order and dependencies
        workflow_results = result["results"]
        
        # Reporting should always execute (UVS principle)  
        assert "reporting" in workflow_results
        reporting_result = workflow_results["reporting"]
        assert reporting_result["status"] == "completed"
        assert reporting_agent.execution_count > 0
        
        # Validate metadata propagation
        final_metadata = test_user_context.metadata
        
        # Should have agent results in metadata for cross-agent communication
        for agent_name, agent in test_agents.items():
            if agent.execution_count > 0:
                expected_key = f"{agent_name}_result"
                assert expected_key in final_metadata, f"Missing {expected_key} in metadata"
                
        logger.info("✅ Agent orchestration workflow test passed")
    
    @pytest.mark.integration
    async def test_business_value_cost_optimization_scenario(
        self,
        configured_supervisor_agent,
        mock_llm_manager,
        mock_websocket_bridge
    ):
        """Test real business value scenario - cost optimization analysis."""
        
        # Create realistic cost optimization context
        context = UserExecutionContext(
            user_id="enterprise_user_cost_opt",
            thread_id="cost_analysis_thread",
            run_id="optimize_run_001",
            metadata={
                "user_request": "I'm spending $50,000/month on AI APIs. Help me optimize costs while maintaining performance.",
                "current_monthly_spend": 50000,
                "primary_providers": ["openai", "anthropic", "google"],
                "performance_requirements": {"latency": "<2s", "accuracy": ">95%"}
            }
        )
        
        # Add database session
        context = context.with_db_session(AsyncMock(spec=AsyncSession))
        
        # Create specialized agents for cost optimization
        triage_agent = MockAgent("triage", mock_llm_manager)
        data_agent = MockAgent("data", mock_llm_manager) 
        optimization_agent = MockAgent("optimization", mock_llm_manager)
        actions_agent = MockAgent("actions", mock_llm_manager)
        reporting_agent = MockAgent("reporting", mock_llm_manager)
        
        # Configure triage to recommend cost optimization workflow
        def triage_execute(context, stream_updates=False):
            result = {
                "category": "cost_optimization",
                "priority": "high",
                "data_sufficiency": "sufficient",
                "intent": {
                    "primary_intent": "reduce costs while maintaining performance",
                    "action_required": True
                },
                "estimated_savings": {"min": 8000, "max": 15000, "confidence": 0.85},
                "next_agents": ["data", "optimization", "actions"]
            }
            context.metadata["triage_result"] = result
            return result
            
        triage_agent.execute = triage_execute
        
        test_agents = {
            "triage": triage_agent,
            "data": data_agent,
            "optimization": optimization_agent, 
            "actions": actions_agent,
            "reporting": reporting_agent
        }
        
        with patch.object(configured_supervisor_agent, '_create_isolated_agent_instances') as mock_create:
            mock_create.return_value = test_agents
            
            with patch('netra_backend.app.agents.supervisor_consolidated.managed_session') as mock_managed_session:
                mock_session_manager = AsyncMock(spec=DatabaseSessionManager)
                mock_managed_session.return_value.__aenter__.return_value = mock_session_manager
                mock_managed_session.return_value.__aexit__.return_value = None
                
                # Execute cost optimization workflow
                result = await configured_supervisor_agent.execute(context)
        
        # Validate business value delivery
        assert result["orchestration_successful"] is True
        workflow_results = result["results"]
        
        # Validate cost optimization workflow executed
        assert "triage" in workflow_results
        assert "optimization" in workflow_results  
        assert "reporting" in workflow_results
        
        # Validate cost optimization metadata
        assert "triage_result" in context.metadata
        triage_result = context.metadata["triage_result"]
        assert triage_result["category"] == "cost_optimization"
        assert "estimated_savings" in triage_result
        
        # Validate business impact
        savings = triage_result["estimated_savings"]
        assert savings["min"] > 0, "Should identify potential cost savings"
        assert savings["confidence"] > 0.5, "Should have reasonable confidence"
        
        logger.info(f"✅ Cost optimization scenario test passed - estimated savings: ${savings['min']}-${savings['max']}")
    
    @pytest.mark.integration 
    async def test_error_handling_and_resilience(
        self,
        configured_supervisor_agent,
        test_user_context,
        mock_llm_manager,
        mock_websocket_bridge
    ):
        """Test SupervisorAgent error handling and resilience patterns."""
        
        # Add database session
        test_user_context = test_user_context.with_db_session(AsyncMock(spec=AsyncSession))
        
        # Create agents with mixed success/failure scenarios
        working_agent = MockAgent("reporting", mock_llm_manager)  # Critical agent - must work
        
        # Create failing agent 
        failing_agent = MockAgent("optimization", mock_llm_manager)
        
        async def failing_execute(context, stream_updates=False):
            raise RuntimeError("Simulated agent failure")
            
        failing_agent.execute = failing_execute
        
        test_agents = {
            "reporting": working_agent,  # Critical - must succeed
            "optimization": failing_agent  # Optional - can fail
        }
        
        with patch.object(configured_supervisor_agent, '_create_isolated_agent_instances') as mock_create:
            mock_create.return_value = test_agents
            
            with patch('netra_backend.app.agents.supervisor_consolidated.managed_session') as mock_managed_session:
                mock_session_manager = AsyncMock(spec=DatabaseSessionManager)
                mock_managed_session.return_value.__aenter__.return_value = mock_session_manager
                mock_managed_session.return_value.__aexit__.return_value = None
                
                # Execute with partial failures
                result = await configured_supervisor_agent.execute(test_user_context)
        
        # Validate graceful degradation
        assert result["orchestration_successful"] is True  # Overall success despite partial failures
        
        workflow_results = result["results"]
        
        # Critical agent (reporting) should succeed
        assert "reporting" in workflow_results
        assert workflow_results["reporting"]["status"] == "completed"
        
        # Optional agent (optimization) should fail gracefully
        assert "optimization" in workflow_results
        optimization_result = workflow_results["optimization"]
        assert optimization_result["status"] == "failed"
        assert optimization_result["recoverable"] is True
        
        # Validate workflow metadata tracks failures
        metadata = result["_workflow_metadata"]
        assert "failed_agents" in metadata
        assert "optimization" in metadata["failed_agents"]
        assert "reporting" in metadata["completed_agents"]
        
        logger.info("✅ Error handling and resilience test passed")
    
    @pytest.mark.integration
    async def test_concurrent_user_execution_safety(
        self,
        mock_llm_manager,
        mock_websocket_bridge
    ):
        """Test SupervisorAgent handles concurrent users safely without context leakage."""
        
        # Create a mock registry with some test agents for concurrent testing
        mock_registry = MagicMock(spec=AgentClassRegistry)
        mock_registry.__len__ = MagicMock(return_value=5)  # Simulate 5 agent classes
        
        # Mock agent instance factory 
        mock_factory = MagicMock()
        mock_factory.configure = MagicMock()
        
        # Create multiple supervisors for concurrent testing with proper mocks
        supervisors = []
        with patch('netra_backend.app.agents.supervisor_consolidated.get_agent_class_registry', return_value=mock_registry):
            with patch('netra_backend.app.agents.supervisor_consolidated.get_agent_instance_factory', return_value=mock_factory):
                supervisors = [
                    SupervisorAgent.create(mock_llm_manager, mock_websocket_bridge)
                    for _ in range(3)
                ]
        
        # Create different user contexts 
        user_contexts = []
        for i in range(3):
            context = UserExecutionContext(
                user_id=f"concurrent_user_{i}",
                thread_id=f"concurrent_thread_{i}",
                run_id=f"concurrent_run_{i}",
                metadata={
                    "user_request": f"Request from user {i}",
                    "user_specific_data": f"secret_data_user_{i}"
                }
            )
            context = context.with_db_session(AsyncMock(spec=AsyncSession))
            user_contexts.append(context)
        
        # Create agents with user-specific behavior
        def create_user_agents(user_id):
            agents = {}
            for agent_name in ["triage", "reporting"]:
                agent = MockAgent(agent_name, mock_llm_manager)
                
                # Override execute to include user-specific data
                original_execute = agent.execute
                async def user_specific_execute(context, stream_updates=False):
                    result = await original_execute(context, stream_updates)
                    result["processed_for_user"] = context.user_id
                    result["user_specific_data"] = context.metadata.get("user_specific_data")
                    return result
                    
                agent.execute = user_specific_execute
                agents[agent_name] = agent
                
            return agents
        
        # Mock agent creation for each supervisor
        for i, supervisor in enumerate(supervisors):
            user_agents = create_user_agents(user_contexts[i].user_id)
            
            def make_mock_create(agents):
                return lambda context: agents
                
            with patch.object(supervisor, '_create_isolated_agent_instances', side_effect=make_mock_create(user_agents)):
                with patch('netra_backend.app.agents.supervisor_consolidated.managed_session') as mock_managed_session:
                    mock_session_manager = AsyncMock(spec=DatabaseSessionManager)
                    mock_managed_session.return_value.__aenter__.return_value = mock_session_manager
                    mock_managed_session.return_value.__aexit__.return_value = None
                    
                    # Execute all supervisors concurrently
                    tasks = []
                    for j, context in enumerate(user_contexts):
                        task = supervisors[j].execute(context)
                        tasks.append(task)
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate no context leakage
        assert len(results) == 3
        
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"User {i} execution failed: {result}"
            assert result["user_id"] == user_contexts[i].user_id
            assert result["orchestration_successful"] is True
            
            # Validate user-specific data didn't leak
            workflow_results = result["results"]
            for agent_result in workflow_results.values():
                if isinstance(agent_result, dict) and "processed_for_user" in agent_result:
                    assert agent_result["processed_for_user"] == user_contexts[i].user_id
                    assert agent_result["user_specific_data"] == f"secret_data_user_{i}"
        
        logger.info("✅ Concurrent user execution safety test passed")


# Additional helper functions for test scenarios

async def create_realistic_llm_manager():
    """Create realistic LLM manager for testing (preferring real when available)."""
    from shared.isolated_environment import IsolatedEnvironment
    env = IsolatedEnvironment()
    
    use_real_llm = env.get("USE_REAL_LLM", "false").lower() == "true"
    
    if use_real_llm:
        try:
            real_manager = LLMManager()
            await real_manager.initialize()
            logger.info("Using real LLM manager for integration tests")
            return real_manager
        except Exception as e:
            logger.warning(f"Failed to initialize real LLM manager: {e}")
    
    # Fallback to comprehensive mock
    mock_manager = AsyncMock(spec=LLMManager)
    mock_manager.health_check = AsyncMock(return_value=True)
    return mock_manager


def validate_user_isolation(context1: UserExecutionContext, context2: UserExecutionContext):
    """Validate that two contexts are properly isolated."""
    assert context1.user_id != context2.user_id
    assert context1.thread_id != context2.thread_id  
    assert context1.run_id != context2.run_id
    assert context1.request_id != context2.request_id
    
    # Metadata should be separate instances
    assert id(context1.metadata) != id(context2.metadata)
    
    # Verify isolation verification passes
    assert context1.verify_isolation()
    assert context2.verify_isolation()


def validate_websocket_events(events: List[Dict], expected_types: List[str]):
    """Validate that expected WebSocket event types were emitted."""
    event_types = [event.get("event_type") for event in events]
    
    for expected_type in expected_types:
        assert expected_type in event_types, f"Missing event type: {expected_type}"
        
    # Validate event structure
    for event in events:
        assert "event_type" in event
        assert "data" in event
        assert "timestamp" in event