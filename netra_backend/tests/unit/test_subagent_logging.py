"""Test subagent logging functionality."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.observability import SubAgentLogger, get_subagent_logger

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



class MockSubAgent(BaseSubAgent):
    """Test implementation of BaseSubAgent."""
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Test execute method."""
        pass


class MockSubAgentLogger:
    """Test SubAgentLogger class functionality."""
    
    def test_init_enabled(self):
        """Test logger initialization with enabled flag."""
        logger = SubAgentLogger(enabled=True)
        assert logger.enabled is True
        assert logger.log_format == "json"
    
    def test_init_disabled(self):
        """Test logger initialization with disabled flag."""
        logger = SubAgentLogger(enabled=False)
        assert logger.enabled is False
    
    @patch('app.llm.observability.logger')
    def test_log_agent_communication_enabled(self, mock_logger):
        """Test agent communication logging when enabled."""
        logger = SubAgentLogger(enabled=True)
        logger.log_agent_communication("agent_a", "agent_b", "corr_123", "test_message")
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Agent communication:" in call_args
        assert "agent_a" in call_args
        assert "agent_b" in call_args
    
    @patch('app.llm.observability.logger')
    def test_log_agent_communication_disabled(self, mock_logger):
        """Test agent communication logging when disabled."""
        logger = SubAgentLogger(enabled=False)
        logger.log_agent_communication("agent_a", "agent_b", "corr_123", "test_message")
        
        mock_logger.info.assert_not_called()
    
    @patch('app.llm.observability.logger')
    def test_log_agent_input(self, mock_logger):
        """Test agent input logging."""
        logger = SubAgentLogger(enabled=True)
        logger.log_agent_input("agent_a", "agent_b", 1024, "corr_123")
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Agent input:" in call_args
        assert "1024" in call_args
    
    @patch('app.llm.observability.logger')
    def test_log_agent_output(self, mock_logger):
        """Test agent output logging."""
        logger = SubAgentLogger(enabled=True)
        logger.log_agent_output("agent_a", "agent_b", 2048, "success", "corr_123")
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Agent output:" in call_args
        assert "2048" in call_args
        assert "success" in call_args


class TestBaseSubAgentLogging:
    """Test BaseSubAgent logging integration."""
    
    @pytest.fixture
    def test_agent(self):
        """Create test agent instance."""
        return MockSubAgent(name="TestAgent")
    
    @pytest.fixture
    def mock_state(self):
        """Create mock state."""
        return DeepAgentState(user_request="test request")
    
    def test_agent_has_correlation_id(self, test_agent):
        """Test agent has correlation ID for tracing."""
        assert hasattr(test_agent, 'correlation_id')
        assert test_agent.correlation_id is not None
        assert len(test_agent.correlation_id) > 0
    
    def test_agent_has_logging_enabled_config(self, test_agent):
        """Test agent has logging enabled configuration."""
        assert hasattr(test_agent, '_subagent_logging_enabled')
        assert isinstance(test_agent._subagent_logging_enabled, bool)
    
    def test_calculate_data_size_string(self, test_agent):
        """Test data size calculation for string."""
        data = "test string"
        size = test_agent._calculate_data_size(data)
        assert size == len(data)
    
    def test_calculate_data_size_dict(self, test_agent):
        """Test data size calculation for dictionary."""
        data = {"key": "value", "number": 123}
        size = test_agent._calculate_data_size(data)
        assert size > 0
    
    def test_calculate_data_size_list(self, test_agent):
        """Test data size calculation for list."""
        data = ["item1", "item2", 123]
        size = test_agent._calculate_data_size(data)
        assert size > 0
    
    def test_calculate_data_size_exception(self, test_agent):
        """Test data size calculation handles exceptions."""
        # Create an object that will fail JSON serialization
        class UnserializableObject:
            def __str__(self):
                raise Exception("Cannot serialize")
        
        data = UnserializableObject()
        size = test_agent._calculate_data_size(data)
        assert size == 0
    
    @patch('app.llm.observability.SubAgentLogger._log_communication_json')
    def test_log_agent_start(self, mock_log_comm, test_agent):
        """Test agent start logging."""
        test_agent._subagent_logging_enabled = True
        test_agent._log_agent_start("run_123")
        
        mock_log_comm.assert_called_once_with(
            "system", test_agent.name, test_agent.correlation_id, "agent_start"
        )
    
    @patch('app.llm.observability.SubAgentLogger._log_communication_json')
    def test_log_agent_start_disabled(self, mock_log_comm, test_agent):
        """Test agent start logging when disabled."""
        test_agent._subagent_logging_enabled = False
        test_agent._log_agent_start("run_123")
        
        mock_log_comm.assert_not_called()
    
    @patch('app.llm.observability.SubAgentLogger._log_communication_json')
    def test_log_agent_completion(self, mock_log_comm, test_agent):
        """Test agent completion logging."""
        test_agent._subagent_logging_enabled = True
        test_agent._log_agent_completion("run_123", "completed")
        
        mock_log_comm.assert_called_once_with(
            test_agent.name, "system", test_agent.correlation_id, "agent_completed"
        )
    
    @patch('app.llm.observability.SubAgentLogger._log_input_json')
    def test_log_input_from_agent(self, mock_log_input, test_agent):
        """Test logging input from another agent."""
        test_agent._subagent_logging_enabled = True
        test_agent.log_input_from_agent("other_agent", "test data")
        
        mock_log_input.assert_called_once()
        args = mock_log_input.call_args[0]
        assert args[0] == "other_agent"
        assert args[1] == test_agent.name
        assert args[2] == len("test data")
        assert args[3] == test_agent.correlation_id
    
    @patch('app.llm.observability.SubAgentLogger._log_output_json')
    def test_log_output_to_agent(self, mock_log_output, test_agent):
        """Test logging output to another agent."""
        test_agent._subagent_logging_enabled = True
        test_agent.log_output_to_agent("target_agent", "response data", "success")
        
        mock_log_output.assert_called_once()
        args = mock_log_output.call_args[0]
        assert args[0] == "target_agent"
        assert args[1] == test_agent.name
        assert args[2] == len("response data")
        assert args[3] == "success"
        assert args[4] == test_agent.correlation_id
    
    @patch('app.llm.observability.SubAgentLogger._log_communication_json')
    @patch('app.config.get_config')
    async def test_pre_run_logging(self, mock_get_config, mock_log_comm, test_agent, mock_state):
        """Test logging during pre_run."""
        # Mock config to enable logging
        mock_config = MagicMock()
        mock_config.subagent_logging_enabled = True
        mock_get_config.return_value = mock_config
        
        test_agent._subagent_logging_enabled = True
        
        # Mock check_entry_conditions to return True
        test_agent.check_entry_conditions = AsyncMock(return_value=True)
        
        result = await test_agent._pre_run(mock_state, "run_123", False)
        
        assert result is True
        mock_log_comm.assert_called_once_with(
            "system", test_agent.name, test_agent.correlation_id, "agent_start"
        )


def test_get_subagent_logger_singleton():
    """Test that get_subagent_logger returns singleton instance."""
    logger1 = get_subagent_logger()
    logger2 = get_subagent_logger()
    
    assert logger1 is logger2
    assert isinstance(logger1, SubAgentLogger)