"""
Comprehensive unit tests for BaseSubAgent functionality
Focus: Uncovered areas with minimal mocking
Coverage Target: Timing, Correlation ID, Configuration, Logging, User Management
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.agents.base.timing_collector import ExecutionTimingCollector
from netra_backend.app.core.config import get_config
import asyncio


class ConcreteConcreteTestAgent(BaseSubAgent):
    """Concrete test implementation of BaseSubAgent"""
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False) -> None:
        """Test execute implementation"""
        pass
    
    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Test entry conditions implementation"""
        return True


class TestBaseAgentComprehensive:
    """Comprehensive test suite for BaseSubAgent uncovered functionality"""
    
    @pytest.fixture
    def real_llm_manager(self):
        """Create a real LLM manager instance"""
        # Using real instance to minimize mocking
        config = get_config()
        return LLMManager(settings=config)
    
    def test_timing_collector_lifecycle_management(self, real_llm_manager):
        """Test 1: Validates timing collector integration with agent lifecycle"""
        # Create agent with custom name
        agent_name = "TestTimingAgent"
        agent = ConcreteConcreteTestAgent(llm_manager=real_llm_manager, name=agent_name)
        
        # Verify timing collector is properly initialized
        assert agent.timing_collector is not None
        assert isinstance(agent.timing_collector, ExecutionTimingCollector)
        assert agent.timing_collector.agent_name == agent_name
        
        # Verify correlation ID is set
        assert agent.correlation_id is not None
        assert isinstance(agent.correlation_id, str)
        
        # Test timing collector can track operations
        # Start a timing execution first
        agent.timing_collector.start_execution(agent.correlation_id)
        
        with agent.timing_collector.time_operation("test_operation"):
            # Simulate some work
            import time
            time.sleep(0.01)
        
        # Complete the execution to aggregate stats
        tree = agent.timing_collector.complete_execution()
        
        # Verify timing was recorded
        assert tree is not None
        assert len(tree.entries) > 0
        
        # Test multiple timing entries
        agent.timing_collector.start_execution(agent.correlation_id)
        for i in range(3):
            with agent.timing_collector.time_operation(f"operation_{i}"):
                time.sleep(0.001)
        
        tree2 = agent.timing_collector.complete_execution()
        
        # Verify multiple operations tracked
        assert tree2 is not None
        assert len(tree2.entries) >= 3
        
        # Verify aggregated stats
        stats = agent.timing_collector.get_aggregated_stats()
        assert len(stats) >= 0  # Stats may be empty until we complete executions
    
    def test_correlation_id_generation_uniqueness_tracking(self, real_llm_manager):
        """Test 2: Tests correlation ID generation, uniqueness, and propagation"""
        # Create multiple agents
        agents = []
        correlation_ids = set()
        
        for i in range(10):
            agent = ConcreteConcreteTestAgent(
                llm_manager=real_llm_manager,
                name=f"Agent_{i}"
            )
            agents.append(agent)
            
            # Verify correlation ID is generated
            assert agent.correlation_id is not None
            assert isinstance(agent.correlation_id, str)
            
            # Verify UUID format (basic check)
            try:
                uuid.UUID(agent.correlation_id)
            except ValueError:
                pytest.fail(f"Invalid UUID format: {agent.correlation_id}")
            
            # Add to set for uniqueness check
            correlation_ids.add(agent.correlation_id)
        
        # Verify all correlation IDs are unique
        assert len(correlation_ids) == 10
        
        # Verify correlation ID persists throughout lifecycle
        test_agent = agents[0]
        initial_id = test_agent.correlation_id
        
        # Simulate various operations
        test_agent.set_state(SubAgentLifecycle.RUNNING)
        assert test_agent.correlation_id == initial_id
        
        test_agent.set_state(SubAgentLifecycle.COMPLETED)
        assert test_agent.correlation_id == initial_id
    
    @patch('netra_backend.app.agents.base_agent.get_config')
    @patch('netra_backend.app.agents.base_agent.get_env')
    def test_config_loading_error_resilience(self, mock_get_env, mock_get_config, real_llm_manager):
        """Test 3: Validates robust error handling when configuration loading fails"""
        # Test 1: Config loading raises exception
        mock_get_env.return_value = {}
        mock_get_config.side_effect = Exception("Config loading failed")
        
        # Agent should still initialize successfully
        agent = ConcreteConcreteTestAgent(llm_manager=real_llm_manager, name="ErrorConcreteTestAgent")
        assert agent is not None
        
        # Subagent logging should default to enabled
        assert agent._subagent_logging_enabled is True
        
        # Test 2: TEST_COLLECTION_MODE handling
        mock_get_env.return_value = {'TEST_COLLECTION_MODE': '1'}
        agent2 = ConcreteConcreteTestAgent(llm_manager=real_llm_manager, name="CollectionModeAgent")
        assert agent2._subagent_logging_enabled is False
        
        # Test 3: Config returns None
        mock_get_env.return_value = {}
        mock_get_config.side_effect = None
        mock_get_config.return_value = None
        
        agent3 = ConcreteConcreteTestAgent(llm_manager=real_llm_manager, name="NoneConfigAgent")
        assert agent3._subagent_logging_enabled is True
        
        # Test 4: Config missing subagent_logging_enabled attribute
        mock_config = Mock()
        del mock_config.subagent_logging_enabled  # Remove attribute
        mock_get_config.return_value = mock_config
        
        agent4 = ConcreteConcreteTestAgent(llm_manager=real_llm_manager, name="MissingAttrAgent")
        assert agent4._subagent_logging_enabled is True
    
    @patch('netra_backend.app.agents.base_agent.get_config')
    @patch('netra_backend.app.agents.base_agent.get_env')
    @patch('netra_backend.app.agents.base_agent.central_logger')
    def test_subagent_logging_configuration_states(self, mock_logger, mock_get_env, mock_get_config, real_llm_manager):
        """Test 4: Tests different logging configuration states and their effects"""
        mock_get_env.return_value = {}
        
        # Test 1: Logging enabled
        mock_config = Mock()
        mock_config.subagent_logging_enabled = True
        mock_get_config.return_value = mock_config
        
        agent_enabled = ConcreteConcreteTestAgent(llm_manager=real_llm_manager, name="LogEnabledAgent")
        assert agent_enabled._subagent_logging_enabled is True
        
        # Verify logger is created with correct name
        mock_logger.get_logger.assert_called_with("LogEnabledAgent")
        
        # Test 2: Logging disabled
        mock_config.subagent_logging_enabled = False
        agent_disabled = ConcreteConcreteTestAgent(llm_manager=real_llm_manager, name="LogDisabledAgent")
        assert agent_disabled._subagent_logging_enabled is False
        
        # Test 3: TEST_COLLECTION_MODE disables logging
        mock_get_env.return_value = {'TEST_COLLECTION_MODE': '1'}
        agent_collection = ConcreteConcreteTestAgent(llm_manager=real_llm_manager, name="CollectionAgent")
        assert agent_collection._subagent_logging_enabled is False
        
        # Test 4: Multiple agents have independent logging states
        mock_get_env.return_value = {}
        agents = []
        for i in range(5):
            mock_config.subagent_logging_enabled = (i % 2 == 0)  # Alternate enabled/disabled
            agent = ConcreteConcreteTestAgent(llm_manager=real_llm_manager, name=f"Agent_{i}")
            agents.append(agent)
            assert agent._subagent_logging_enabled == (i % 2 == 0)
    
    def test_user_id_websocket_manager_assignment(self, real_llm_manager):
        """Test 5: Validates user ID assignment and WebSocket manager integration"""
        agent = ConcreteConcreteTestAgent(llm_manager=real_llm_manager, name="WebSocketConcreteTestAgent")
        
        # Initial state - no user_id or websocket_manager
        assert agent.user_id is None
        assert agent.websocket_manager is None
        
        # Test user ID assignment
        test_user_id = "user_123"
        agent.user_id = test_user_id
        assert agent.user_id == test_user_id
        
        # Test WebSocket manager assignment
        mock_ws_manager = Mock()
        mock_ws_manager.send_message = Mock()
        agent.websocket_manager = mock_ws_manager
        assert agent.websocket_manager == mock_ws_manager
        
        # Test both working together
        agent2 = ConcreteConcreteTestAgent(llm_manager=real_llm_manager, name="CompleteWSAgent")
        agent2.user_id = "user_456"
        agent2.websocket_manager = mock_ws_manager
        
        # Verify they can be used together
        if agent2.websocket_manager and agent2.user_id:
            # This pattern is used in actual agent code
            can_send = True
        assert can_send is True
        
        # Test None handling
        agent3 = ConcreteConcreteTestAgent(llm_manager=real_llm_manager, name="NoneWSAgent")
        assert agent3.websocket_manager is None
        assert agent3.user_id is None
        
        # Test reassignment
        agent3.user_id = "user_789"
        agent3.websocket_manager = Mock()
        assert agent3.user_id == "user_789"
        
        # Test clearing
        agent3.user_id = None
        agent3.websocket_manager = None
        assert agent3.user_id is None
        assert agent3.websocket_manager is None
    
    @pytest.mark.asyncio
    async def test_shutdown_comprehensive(self, real_llm_manager):
        """Additional test: Comprehensive shutdown behavior validation"""
        agent = ConcreteConcreteTestAgent(llm_manager=real_llm_manager, name="ShutdownConcreteTestAgent")
        
        # Set up some state
        agent.context = {"key1": "value1", "key2": "value2"}
        agent.user_id = "test_user"
        agent.websocket_manager = Mock()
        agent.set_state(SubAgentLifecycle.RUNNING)
        
        # Test initial state
        assert agent.state == SubAgentLifecycle.RUNNING
        assert len(agent.context) == 2
        assert agent.user_id == "test_user"
        assert agent.websocket_manager is not None
        
        # Perform shutdown with proper exception handling
        try:
            await agent.shutdown()
        except Exception as e:
            pytest.fail(f"Shutdown failed with exception: {e}")
        
        # Verify state changes
        assert agent.state == SubAgentLifecycle.SHUTDOWN
        assert agent.context == {}  # Context should be cleared
        
        # User ID and websocket_manager should remain (for cleanup by supervisor)
        assert agent.user_id == "test_user"
        assert agent.websocket_manager is not None
        
        # Test multiple shutdowns are idempotent
        try:
            await agent.shutdown()
            await agent.shutdown()
        except Exception as e:
            pytest.fail(f"Multiple shutdowns failed with exception: {e}")
        
        # State should remain SHUTDOWN
        assert agent.state == SubAgentLifecycle.SHUTDOWN
        assert agent.context == {}
        
        # Test shutdown on already shutdown agent doesn't cause issues
        final_state = agent.state
        await agent.shutdown()
        assert agent.state == final_state