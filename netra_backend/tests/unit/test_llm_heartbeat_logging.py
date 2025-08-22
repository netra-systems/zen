"""Unit tests for LLM heartbeat logging functionality.

Tests the heartbeat logging integration for long-running LLM calls.
Each test must be concise and focused as per architecture requirements.
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
from app.llm.observability import (
    HeartbeatLogger,
    generate_llm_correlation_id,
    get_heartbeat_logger,
)
from app.schemas.Config import AppConfig

# Add project root to path


class TestHeartbeatLogger:
    """Test cases for HeartbeatLogger functionality."""
    
    def test_generate_correlation_id(self):
        """Test correlation ID generation."""
        logger = HeartbeatLogger()
        correlation_id = logger.generate_correlation_id()
        assert isinstance(correlation_id, str)
        assert len(correlation_id) > 0

    def test_heartbeat_logger_initialization(self):
        """Test HeartbeatLogger initialization with custom interval."""
        logger = HeartbeatLogger(interval_seconds=3.0)
        assert logger.interval_seconds == 3.0
        assert len(logger._active_tasks) == 0
    async def test_start_heartbeat_creates_task(self):
        """Test that starting heartbeat creates an async task."""
        logger = HeartbeatLogger()
        correlation_id = "test-correlation-id"
        logger.start_heartbeat(correlation_id, "test_agent")
        assert correlation_id in logger._active_tasks
        assert correlation_id in logger._start_times
        assert correlation_id in logger._agent_names
    async def test_stop_heartbeat_cleans_up(self):
        """Test that stopping heartbeat cleans up resources."""
        logger = HeartbeatLogger()
        correlation_id = "test-correlation-id"
        logger.start_heartbeat(correlation_id, "test_agent")
        logger.stop_heartbeat(correlation_id)
        assert correlation_id not in logger._active_tasks
        assert correlation_id not in logger._start_times
    async def test_heartbeat_logging_flow(self):
        """Test complete heartbeat logging flow."""
        with patch('app.llm.observability.logger') as mock_logger:
            logger = HeartbeatLogger(interval_seconds=0.1)
            correlation_id = generate_llm_correlation_id()
            
            logger.start_heartbeat(correlation_id, "test_agent")
            await asyncio.sleep(0.2)
            logger.stop_heartbeat(correlation_id)
            
            assert mock_logger.info.called
    async def test_get_active_operations(self):
        """Test getting active operations information."""
        logger = HeartbeatLogger()
        correlation_id = "test-correlation-id"
        logger.start_heartbeat(correlation_id, "test_agent")
        
        active_ops = logger.get_active_operations()
        assert correlation_id in active_ops
        assert active_ops[correlation_id]["agent_name"] == "test_agent"

    def test_global_heartbeat_logger_singleton(self):
        """Test that global heartbeat logger works as singleton."""
        logger1 = get_heartbeat_logger()
        logger2 = get_heartbeat_logger()
        assert logger1 is logger2

    def test_elapsed_time_calculation(self):
        """Test elapsed time calculation accuracy."""
        logger = HeartbeatLogger()
        correlation_id = "test-correlation-id"
        start_time = time.time()
        
        logger._start_times[correlation_id] = start_time
        time.sleep(0.1)
        elapsed = logger._calculate_elapsed_time(correlation_id)
        
        assert elapsed >= 0.1
        assert elapsed < 0.2

    def test_heartbeat_message_format(self):
        """Test heartbeat data formatting."""
        logger = HeartbeatLogger()
        data = logger._build_heartbeat_data("test_agent", "test-id", 2.5)
        
        assert data["type"] == "llm_heartbeat"
        assert data["agent_name"] == "test_agent"
        assert data["correlation_id"] == "test-id"
        assert data["elapsed_time_seconds"] == 2.5
        assert data["status"] == "processing"
        assert "timestamp" in data


class TestHeartbeatIntegration:
    """Test cases for heartbeat integration with LLM operations."""
    async def test_heartbeat_with_app_config(self):
        """Test heartbeat logger with app configuration."""
        from app.core.config import get_config
        config = get_config()
        
        # Verify configuration has heartbeat settings
        assert hasattr(config, 'llm_heartbeat_enabled')
        assert hasattr(config, 'llm_heartbeat_interval_seconds')
        assert config.llm_heartbeat_enabled is True
        assert config.llm_heartbeat_interval_seconds == 2.5

    def test_heartbeat_functions_work(self):
        """Test global heartbeat convenience functions."""
        correlation_id = generate_llm_correlation_id()
        assert isinstance(correlation_id, str)
        assert len(correlation_id) > 0
    async def test_heartbeat_task_cancellation(self):
        """Test that heartbeat tasks are properly cancelled."""
        logger = HeartbeatLogger(interval_seconds=0.1)
        correlation_id = generate_llm_correlation_id()
        
        logger.start_heartbeat(correlation_id, "test_agent")
        task = logger._active_tasks[correlation_id]
        assert not task.done()
        
        logger.stop_heartbeat(correlation_id)
        await asyncio.sleep(0.05)
        assert task.cancelled()

    def test_stop_heartbeat_non_existent_id(self):
        """Test stopping heartbeat with non-existent correlation ID."""
        logger = HeartbeatLogger()
        # Should not raise an exception
        logger.stop_heartbeat("non-existent-id")
        assert len(logger._active_tasks) == 0

    def test_heartbeat_configuration_integration(self):
        """Test heartbeat configuration is properly integrated."""
        from app.core.config import get_config
        from app.llm.llm_core_operations import LLMCoreOperations
        
        config = get_config()
        operations = LLMCoreOperations(config)
        
        # Verify the operations instance was created successfully
        assert operations.settings is config
        assert operations.settings.llm_heartbeat_enabled is True


class TestSupervisorHeartbeatScenarios:
    """Test heartbeat logging for supervisor-specific scenarios."""
    
    async def test_supervisor_agent_coordination_heartbeat(self):
        """Test heartbeat during supervisor agent coordination."""
        with patch('app.llm.observability.logger') as mock_logger:
            logger = HeartbeatLogger(interval_seconds=0.1)
            correlation_id = generate_llm_correlation_id()
            
            logger.start_heartbeat(correlation_id, "supervisor_coordinator")
            await asyncio.sleep(0.15)
            logger.stop_heartbeat(correlation_id)
            
            assert mock_logger.info.called
            logged_msg = mock_logger.info.call_args[0][0]
            assert "supervisor_coordinator" in logged_msg

    async def test_heartbeat_during_pipeline_execution(self):
        """Test heartbeat continues during long pipeline operations."""
        with patch('app.llm.observability.logger') as mock_logger:
            logger = HeartbeatLogger(interval_seconds=0.1)
            correlation_id = generate_llm_correlation_id()
            
            # Simulate long-running pipeline execution
            logger.start_heartbeat(correlation_id, "pipeline_executor")
            await asyncio.sleep(0.25)  # Multiple heartbeat intervals
            logger.stop_heartbeat(correlation_id)
            
            # Should have multiple heartbeat logs
            assert mock_logger.info.call_count >= 2

    async def test_concurrent_supervisor_agents_heartbeat(self):
        """Test heartbeat for multiple concurrent supervisor agents."""
        with patch('app.llm.observability.logger') as mock_logger:
            logger = HeartbeatLogger(interval_seconds=0.1)
            
            # Start multiple supervisor agents
            agents = ["supervisor_main", "supervisor_fallback", "supervisor_monitor"]
            correlation_ids = []
            
            for agent in agents:
                correlation_id = generate_llm_correlation_id()
                correlation_ids.append(correlation_id)
                logger.start_heartbeat(correlation_id, agent)
            
            await asyncio.sleep(0.15)
            
            # Stop all agents
            for correlation_id in correlation_ids:
                logger.stop_heartbeat(correlation_id)
            
            # Verify all agents were logged
            logged_messages = [call[0][0] for call in mock_logger.info.call_args_list]
            for agent in agents:
                assert any(agent in msg for msg in logged_messages)

    async def test_supervisor_error_recovery_heartbeat(self):
        """Test heartbeat continues during supervisor error recovery."""
        logger = HeartbeatLogger(interval_seconds=0.1)
        correlation_id = generate_llm_correlation_id()
        
        # Start heartbeat for error recovery scenario
        logger.start_heartbeat(correlation_id, "supervisor_error_recovery")
        
        # Verify heartbeat is active during recovery
        active_ops = logger.get_active_operations()
        assert correlation_id in active_ops
        assert active_ops[correlation_id]["agent_name"] == "supervisor_error_recovery"
        
        logger.stop_heartbeat(correlation_id)

    async def test_supervisor_state_checkpoint_heartbeat(self):
        """Test heartbeat during supervisor state checkpointing."""
        with patch('app.llm.observability.logger') as mock_logger:
            logger = HeartbeatLogger(interval_seconds=0.1)
            correlation_id = generate_llm_correlation_id()
            
            # Simulate state checkpoint operation
            logger.start_heartbeat(correlation_id, "supervisor_checkpoint_manager")
            await asyncio.sleep(0.12)
            logger.stop_heartbeat(correlation_id)
            
            # Verify checkpoint manager heartbeat was logged
            assert mock_logger.info.called
            logged_data = mock_logger.info.call_args[0][0]
            assert "supervisor_checkpoint_manager" in logged_data

    def test_supervisor_heartbeat_message_format(self):
        """Test heartbeat message format for supervisor agents."""
        logger = HeartbeatLogger()
        data = {
            "agent_name": "supervisor_main",
            "correlation_id": "test-id", 
            "elapsed_time_seconds": 3.7,
            "status": "processing"
        }
        message = logger._build_heartbeat_text_message(data)
        expected = "LLM heartbeat: supervisor_main - test-id - elapsed: 3.7s - status: processing"
        assert message == expected

    async def test_supervisor_long_operation_heartbeat_persistence(self):
        """Test heartbeat persists through long supervisor operations."""
        with patch('app.llm.observability.logger') as mock_logger:
            logger = HeartbeatLogger(interval_seconds=0.05)
            correlation_id = generate_llm_correlation_id()
            
            # Start long-running supervisor operation
            logger.start_heartbeat(correlation_id, "supervisor_long_operation")
            
            # Simulate long operation with multiple heartbeat cycles
            await asyncio.sleep(0.2)  # 4x heartbeat intervals
            
            logger.stop_heartbeat(correlation_id)
            
            # Should have multiple heartbeat entries
            assert mock_logger.info.call_count >= 3
            
            # Verify all logs are for the same correlation ID
            for call in mock_logger.info.call_args_list:
                logged_data = call[0][0]
                assert correlation_id in logged_data

    async def test_supervisor_agent_handoff_heartbeat_tracking(self):
        """Test heartbeat tracking during supervisor agent handoffs."""
        logger = HeartbeatLogger()
        
        # Simulate agent handoff scenario
        correlation_id_1 = generate_llm_correlation_id()
        correlation_id_2 = generate_llm_correlation_id()
        
        # First agent starts
        logger.start_heartbeat(correlation_id_1, "supervisor_agent_1")
        
        # Second agent starts (handoff)
        logger.start_heartbeat(correlation_id_2, "supervisor_agent_2")
        
        # Verify both agents are tracked
        active_ops = logger.get_active_operations()
        assert len(active_ops) == 2
        assert correlation_id_1 in active_ops
        assert correlation_id_2 in active_ops
        
        # Clean up
        logger.stop_heartbeat(correlation_id_1)
        logger.stop_heartbeat(correlation_id_2)