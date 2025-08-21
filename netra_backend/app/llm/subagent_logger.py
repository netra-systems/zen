"""LLM subagent logging module.

Manages INFO level logging for subagent communication with support
for both JSON and text formats.
"""
import time
from typing import Optional, Dict, Any
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SubAgentLogger:
    """Manages INFO level logging for subagent communication."""
    
    def __init__(self, enabled: bool = True):
        """Initialize subagent logger with configuration."""
        self.enabled = enabled
        self.log_format = "json"  # json or text
    
    def log_agent_communication(self, from_agent: str, to_agent: str, 
                               correlation_id: str, message_type: str) -> None:
        """Log agent-to-agent communication event."""
        if not self.enabled:
            return
        self._log_communication_data(from_agent, to_agent, correlation_id, message_type)
    
    def log_agent_input(self, from_agent: str, to_agent: str, 
                       data_size: int, correlation_id: str = "") -> None:
        """Log agent input data transfer."""
        if not self.enabled:
            return
        self._log_input_data(from_agent, to_agent, data_size, correlation_id)
    
    def log_agent_output(self, to_agent: str, from_agent: str, 
                        data_size: int, status: str, correlation_id: str = "") -> None:
        """Log agent output data transfer."""
        if not self.enabled:
            return
        self._log_output_data(to_agent, from_agent, data_size, status, correlation_id)
    
    def _log_communication_data(self, from_agent: str, to_agent: str, 
                               correlation_id: str, message_type: str) -> None:
        """Log communication data using configured format."""
        if self.log_format == "json":
            self._log_communication_json(from_agent, to_agent, correlation_id, message_type)
        else:
            self._log_communication_text(from_agent, to_agent, correlation_id, message_type)
    
    def _log_input_data(self, from_agent: str, to_agent: str, 
                       data_size: int, correlation_id: str) -> None:
        """Log input data using configured format."""
        if self.log_format == "json":
            self._log_input_json(from_agent, to_agent, data_size, correlation_id)
        else:
            self._log_input_text(from_agent, to_agent, data_size, correlation_id)
    
    def _log_output_data(self, to_agent: str, from_agent: str, 
                        data_size: int, status: str, correlation_id: str) -> None:
        """Log output data using configured format."""
        if self.log_format == "json":
            self._log_output_json(to_agent, from_agent, data_size, status, correlation_id)
        else:
            self._log_output_text(to_agent, from_agent, data_size, status, correlation_id)
    
    def _log_communication_json(self, from_agent: str, to_agent: str, 
                               correlation_id: str, message_type: str) -> None:
        """Log communication in JSON format."""
        import json
        data = self._build_communication_data(from_agent, to_agent, correlation_id, message_type)
        logger.info(f"Agent communication: {json.dumps(data)}")
    
    def _build_communication_data(self, from_agent: str, to_agent: str, 
                                 correlation_id: str, message_type: str) -> Dict[str, Any]:
        """Build communication data dictionary."""
        return {
            "type": "agent_communication",
            "from_agent": from_agent,
            "to_agent": to_agent,
            "correlation_id": correlation_id,
            "message_type": message_type,
            "timestamp": time.time()
        }
    
    def _log_input_json(self, from_agent: str, to_agent: str, 
                       data_size: int, correlation_id: str) -> None:
        """Log input in JSON format."""
        import json
        data = self._build_input_data(from_agent, to_agent, data_size, correlation_id)
        logger.info(f"Agent input: {json.dumps(data)}")
    
    def _build_input_data(self, from_agent: str, to_agent: str, 
                         data_size: int, correlation_id: str) -> Dict[str, Any]:
        """Build input data dictionary."""
        return {
            "type": "agent_input",
            "from_agent": from_agent,
            "to_agent": to_agent,
            "data_size": data_size,
            "correlation_id": correlation_id,
            "timestamp": time.time()
        }
    
    def _log_output_json(self, to_agent: str, from_agent: str, 
                        data_size: int, status: str, correlation_id: str) -> None:
        """Log output in JSON format."""
        import json
        data = self._build_output_data(to_agent, from_agent, data_size, status, correlation_id)
        logger.info(f"Agent output: {json.dumps(data)}")
    
    def _build_agent_output_base(self, to_agent: str, from_agent: str, correlation_id: str) -> Dict[str, Any]:
        """Build base agent output structure."""
        return {
            "type": "agent_output",
            "to_agent": to_agent,
            "from_agent": from_agent,
            "correlation_id": correlation_id,
            "timestamp": time.time()
        }
    
    def _build_output_data(self, to_agent: str, from_agent: str, 
                          data_size: int, status: str, correlation_id: str) -> Dict[str, Any]:
        """Build output data dictionary."""
        data = self._build_agent_output_base(to_agent, from_agent, correlation_id)
        data.update({"data_size": data_size, "status": status})
        return data
    
    def _log_communication_text(self, from_agent: str, to_agent: str, 
                               correlation_id: str, message_type: str) -> None:
        """Log communication in text format."""
        msg = f"Agent communication: {from_agent} -> {to_agent} - {correlation_id} - type: {message_type}"
        logger.info(msg)
    
    def _log_input_text(self, from_agent: str, to_agent: str, 
                       data_size: int, correlation_id: str) -> None:
        """Log input in text format."""
        msg = f"Agent input: {from_agent} -> {to_agent} - data_size: {data_size}"
        if correlation_id:
            msg += f" - {correlation_id}"
        logger.info(msg)
    
    def _log_output_text(self, to_agent: str, from_agent: str, 
                        data_size: int, status: str, correlation_id: str) -> None:
        """Log output in text format."""
        msg = f"Agent output: {to_agent} -> {from_agent} - data_size: {data_size} - status: {status}"
        if correlation_id:
            msg += f" - {correlation_id}"
        logger.info(msg)


# Global subagent logger instance
_subagent_logger: Optional[SubAgentLogger] = None


def get_subagent_logger() -> SubAgentLogger:
    """Get the global subagent logger instance."""
    global _subagent_logger
    if _subagent_logger is None:
        _subagent_logger = SubAgentLogger()
    return _subagent_logger


def log_agent_communication(from_agent: str, to_agent: str, 
                           correlation_id: str, message_type: str) -> None:
    """Log agent-to-agent communication."""
    get_subagent_logger().log_agent_communication(from_agent, to_agent, correlation_id, message_type)


def log_agent_input(from_agent: str, to_agent: str, data_size: int, correlation_id: str = "") -> None:
    """Log agent input data."""
    get_subagent_logger().log_agent_input(from_agent, to_agent, data_size, correlation_id)


def log_agent_output(to_agent: str, from_agent: str, data_size: int, 
                    status: str, correlation_id: str = "") -> None:
    """Log agent output data."""
    get_subagent_logger().log_agent_output(to_agent, from_agent, data_size, status, correlation_id)