"""Test enhanced LLM heartbeat and data logging with JSON depth."""
import asyncio
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.llm.observability import (
    HeartbeatLogger, DataLogger, get_heartbeat_logger, get_data_logger
)


class TestEnhancedHeartbeatLogging:
    """Test enhanced heartbeat logging with JSON output."""
    
    def test_heartbeat_json_format(self):
        """Test heartbeat logs JSON data."""
        logger = HeartbeatLogger(interval_seconds=1.0)
        logger.log_as_json = True
        
        data = logger._build_heartbeat_data("test_agent", "corr-123", 5.5)
        
        assert data["type"] == "llm_heartbeat"
        assert data["agent_name"] == "test_agent"
        assert data["correlation_id"] == "corr-123"
        assert data["elapsed_time_seconds"] == 5.5
        assert data["status"] == "processing"
        assert "timestamp" in data
    
    @patch('app.llm.observability.logger')
    def test_heartbeat_json_logging(self, mock_logger):
        """Test heartbeat logs as JSON when enabled."""
        logger = HeartbeatLogger()
        logger.log_as_json = True
        
        logger._log_heartbeat("test-corr-id")
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "LLM heartbeat:" in call_args
        assert "{" in call_args  # JSON object
    
    @patch('app.llm.observability.logger')
    def test_heartbeat_text_logging(self, mock_logger):
        """Test heartbeat logs as text when disabled."""
        logger = HeartbeatLogger()
        logger.log_as_json = False
        logger._agent_names["test-corr"] = "test_agent"
        logger._start_times["test-corr"] = 0
        
        data = {"agent_name": "test_agent", "correlation_id": "test-corr",
                "elapsed_time_seconds": 5.0, "status": "processing"}
        logger._log_heartbeat_text(data)
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "test_agent - test-corr" in call_args
        assert "elapsed: 5.0s" in call_args


class TestEnhancedDataLogging:
    """Test enhanced data logging with JSON depth control."""
    
    def test_data_logger_init(self):
        """Test data logger initialization with new params."""
        logger = DataLogger(truncate_length=500, json_depth=2)
        
        assert logger.truncate_length == 500
        assert logger.json_depth == 2
        assert logger.log_format == "json"
    
    def test_limit_depth_dict(self):
        """Test JSON depth limiting for dictionaries."""
        logger = DataLogger(json_depth=2)
        
        deep_dict = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": "value"
                    }
                }
            }
        }
        
        limited = logger._limit_depth(deep_dict, 2)
        
        assert isinstance(limited["level1"]["level2"], str)
        # At depth 2, level2 content becomes string representation
        assert len(str(limited["level1"]["level2"])) <= 100
    
    def test_limit_depth_list(self):
        """Test JSON depth limiting for lists."""
        logger = DataLogger(json_depth=1)
        
        deep_list = [
            {"item1": ["nested1", "nested2"]},
            {"item2": ["nested3", "nested4"]}
        ]
        
        limited = logger._limit_depth(deep_list, 1)
        
        assert isinstance(limited[0], str)
    
    def test_build_input_json_data(self):
        """Test building input JSON data structure."""
        logger = DataLogger()
        
        data = logger._build_input_json_data(
            "test_agent", "corr-123", "test prompt", 
            {"temperature": 0.7, "max_tokens": 100}
        )
        
        assert data["type"] == "llm_input"
        assert data["agent_name"] == "test_agent"
        assert data["correlation_id"] == "corr-123"
        assert data["prompt_size"] == 11
        assert "prompt_preview" in data
        assert "parameters" in data
        assert "timestamp" in data
    
    def test_build_output_json_data(self):
        """Test building output JSON data structure."""
        logger = DataLogger()
        
        data = logger._build_output_json_data(
            "test_agent", "corr-123", "test response", 50
        )
        
        assert data["type"] == "llm_output"
        assert data["agent_name"] == "test_agent"
        assert data["correlation_id"] == "corr-123"
        assert data["response_size"] == 13
        assert data["token_count"] == 50
        assert "response_preview" in data
        assert "timestamp" in data
    
    @patch('app.llm.observability.logger')
    def test_log_input_json(self, mock_logger):
        """Test JSON input logging."""
        logger = DataLogger()
        logger.log_format = "json"
        
        logger.log_input_data(
            "test_agent", "corr-123", "test prompt",
            {"temperature": 0.7}
        )
        
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0][0]
        assert "LLM input:" in call_args
        assert "{" in call_args  # JSON object
    
    @patch('app.llm.observability.logger')
    def test_log_output_json(self, mock_logger):
        """Test JSON output logging."""
        logger = DataLogger()
        logger.log_format = "json"
        
        logger.log_output_data(
            "test_agent", "corr-123", "test response", 50
        )
        
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0][0]
        assert "LLM output:" in call_args
        assert "{" in call_args  # JSON object
    
    def test_sanitize_params_depth(self):
        """Test parameter sanitization with depth control."""
        logger = DataLogger(json_depth=2)
        
        complex_params = {
            "model": "gpt-4",
            "config": {
                "temperature": 0.7,
                "nested": {
                    "deep": {
                        "value": "should be truncated"
                    }
                }
            }
        }
        
        sanitized = logger._sanitize_params(complex_params)
        
        assert sanitized["model"] == "gpt-4"
        assert sanitized["config"]["temperature"] == 0.7
        assert isinstance(sanitized["config"]["nested"], str)


class TestConfigurationIntegration:
    """Test configuration integration with logging."""
    
    def test_configure_from_settings(self):
        """Test configuration from app settings."""
        from app.llm.llm_core_operations import LLMCoreOperations
        from app.schemas.Config import AppConfig
        
        settings = AppConfig()
        settings.llm_heartbeat_interval_seconds = 3.0
        settings.llm_heartbeat_log_json = True
        settings.llm_data_truncate_length = 2000
        settings.llm_data_json_depth = 4
        settings.llm_data_log_format = "json"
        
        ops = LLMCoreOperations(settings)
        
        # Get the actual configured loggers
        from app.llm.observability import get_heartbeat_logger, get_data_logger
        heartbeat_logger = get_heartbeat_logger()
        data_logger = get_data_logger()
        
        # Check that configuration was applied
        assert heartbeat_logger.interval_seconds == 3.0
        assert heartbeat_logger.log_as_json == True
        assert data_logger.truncate_length == 2000
        assert data_logger.json_depth == 4
        assert data_logger.log_format == "json"