"""Unit tests for LLM heartbeat logging functionality.

Tests the heartbeat logging integration for long-running LLM calls.
Each test must be concise and focused as per architecture requirements.
"""
import asyncio
import pytest
import time
from unittest.mock import patch, MagicMock
from app.llm.observability import HeartbeatLogger, generate_llm_correlation_id, get_heartbeat_logger
from app.schemas.Config import AppConfig


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

    @pytest.mark.asyncio
    async def test_start_heartbeat_creates_task(self):
        """Test that starting heartbeat creates an async task."""
        logger = HeartbeatLogger()
        correlation_id = "test-correlation-id"
        logger.start_heartbeat(correlation_id, "test_agent")
        assert correlation_id in logger._active_tasks
        assert correlation_id in logger._start_times
        assert correlation_id in logger._agent_names

    @pytest.mark.asyncio
    async def test_stop_heartbeat_cleans_up(self):
        """Test that stopping heartbeat cleans up resources."""
        logger = HeartbeatLogger()
        correlation_id = "test-correlation-id"
        logger.start_heartbeat(correlation_id, "test_agent")
        logger.stop_heartbeat(correlation_id)
        assert correlation_id not in logger._active_tasks
        assert correlation_id not in logger._start_times

    @pytest.mark.asyncio
    async def test_heartbeat_logging_flow(self):
        """Test complete heartbeat logging flow."""
        with patch('app.llm.observability.logger') as mock_logger:
            logger = HeartbeatLogger(interval_seconds=0.1)
            correlation_id = generate_llm_correlation_id()
            
            logger.start_heartbeat(correlation_id, "test_agent")
            await asyncio.sleep(0.2)
            logger.stop_heartbeat(correlation_id)
            
            assert mock_logger.info.called

    @pytest.mark.asyncio
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
        """Test heartbeat message formatting."""
        logger = HeartbeatLogger()
        message = logger._format_heartbeat_message("test_agent", "test-id", 2.5)
        expected = "LLM heartbeat: test_agent - test-id - elapsed: 2.5s - status: processing"
        assert message == expected


class TestHeartbeatIntegration:
    """Test cases for heartbeat integration with LLM operations."""
    
    @pytest.mark.asyncio
    async def test_heartbeat_with_app_config(self):
        """Test heartbeat logger with app configuration."""
        from app.config import get_config
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

    @pytest.mark.asyncio 
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
        from app.llm.llm_core_operations import LLMCoreOperations
        from app.config import get_config
        
        config = get_config()
        operations = LLMCoreOperations(config)
        
        # Verify the operations instance was created successfully
        assert operations.settings is config
        assert operations.settings.llm_heartbeat_enabled is True