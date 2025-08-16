"""LLM observability module for heartbeat logging and monitoring.

Provides heartbeat logging for long-running LLM calls with correlation tracking.
Each function must be ≤8 lines as per architecture requirements.
"""
import asyncio
import time
import uuid
from typing import Optional, Dict, Any
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class HeartbeatLogger:
    """Manages heartbeat logging for long-running LLM operations."""
    
    def __init__(self, interval_seconds: float = 2.5):
        self.interval_seconds = interval_seconds
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._start_times: Dict[str, float] = {}
        self._agent_names: Dict[str, str] = {}
        self.log_as_json = True  # Default to JSON logging

    def generate_correlation_id(self) -> str:
        """Generate unique correlation ID for tracking."""
        return str(uuid.uuid4())

    def start_heartbeat(self, correlation_id: str, agent_name: str) -> None:
        """Start heartbeat logging for an LLM operation."""
        self._record_heartbeat_start(correlation_id, agent_name)
        self._create_heartbeat_task(correlation_id)

    def _record_heartbeat_start(self, correlation_id: str, agent_name: str) -> None:
        """Record the start of a heartbeat operation."""
        self._start_times[correlation_id] = time.time()
        self._agent_names[correlation_id] = agent_name

    def _create_heartbeat_task(self, correlation_id: str) -> None:
        """Create the async heartbeat task."""
        try:
            task = asyncio.create_task(self._heartbeat_loop(correlation_id))
            self._active_tasks[correlation_id] = task
        except RuntimeError:
            pass

    def stop_heartbeat(self, correlation_id: str) -> None:
        """Stop heartbeat logging for an LLM operation."""
        if correlation_id in self._active_tasks:
            self._cancel_task(correlation_id)
            self._cleanup_tracking_data(correlation_id)

    def _cancel_task(self, correlation_id: str) -> None:
        """Cancel the heartbeat task."""
        task = self._active_tasks[correlation_id]
        task.cancel()
        del self._active_tasks[correlation_id]

    def _cleanup_tracking_data(self, correlation_id: str) -> None:
        """Clean up tracking data for correlation ID."""
        self._start_times.pop(correlation_id, None)
        self._agent_names.pop(correlation_id, None)

    async def _heartbeat_loop(self, correlation_id: str) -> None:
        """Main heartbeat loop that logs status periodically."""
        try:
            while True:
                await asyncio.sleep(self.interval_seconds)
                self._log_heartbeat(correlation_id)
        except asyncio.CancelledError:
            pass

    def _log_heartbeat(self, correlation_id: str) -> None:
        """Log a single heartbeat message with JSON data."""
        elapsed_time = self._calculate_elapsed_time(correlation_id)
        agent_name = self._agent_names.get(correlation_id, "unknown")
        heartbeat_data = self._build_heartbeat_data(agent_name, correlation_id, elapsed_time)
        self._log_heartbeat_data(heartbeat_data)

    def _calculate_elapsed_time(self, correlation_id: str) -> float:
        """Calculate elapsed time since operation start."""
        start_time = self._start_times.get(correlation_id, time.time())
        return time.time() - start_time

    def _build_heartbeat_data(self, agent_name: str, correlation_id: str, elapsed_time: float) -> Dict[str, Any]:
        """Build heartbeat data dictionary for JSON logging."""
        return {
            "type": "llm_heartbeat",
            "agent_name": agent_name,
            "correlation_id": correlation_id,
            "elapsed_time_seconds": round(elapsed_time, 1),
            "status": "processing",
            "timestamp": time.time()
        }

    def _log_heartbeat_data(self, data: Dict[str, Any]) -> None:
        """Log heartbeat data as JSON or text."""
        if self.log_as_json:
            import json
            logger.info(f"LLM heartbeat: {json.dumps(data)}")
        else:
            self._log_heartbeat_text(data)

    def _log_heartbeat_text(self, data: Dict[str, Any]) -> None:
        """Log heartbeat in text format."""
        msg = self._build_heartbeat_text_message(data)
        logger.info(msg)
    
    def _build_heartbeat_text_message(self, data: Dict[str, Any]) -> str:
        """Build heartbeat text message from data."""
        return (f"LLM heartbeat: {data['agent_name']} - {data['correlation_id']} - "
                f"elapsed: {data['elapsed_time_seconds']}s - status: {data['status']}")

    def get_active_operations(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently active operations."""
        return {correlation_id: self._get_operation_info(correlation_id)
                for correlation_id in self._active_tasks}

    def _get_operation_info(self, correlation_id: str) -> Dict[str, Any]:
        """Get operation information for a correlation ID."""
        return {
            "agent_name": self._agent_names.get(correlation_id, "unknown"),
            "elapsed_time": self._calculate_elapsed_time(correlation_id),
            "start_time": self._start_times.get(correlation_id, 0)
        }


# Global heartbeat logger instance (will be configured on first use)
_heartbeat_logger: Optional[HeartbeatLogger] = None


def get_heartbeat_logger() -> HeartbeatLogger:
    """Get the global heartbeat logger instance."""
    global _heartbeat_logger
    if _heartbeat_logger is None:
        _heartbeat_logger = HeartbeatLogger()
    return _heartbeat_logger


def start_llm_heartbeat(correlation_id: str, agent_name: str) -> None:
    """Start heartbeat logging for an LLM operation."""
    get_heartbeat_logger().start_heartbeat(correlation_id, agent_name)


def stop_llm_heartbeat(correlation_id: str) -> None:
    """Stop heartbeat logging for an LLM operation."""
    get_heartbeat_logger().stop_heartbeat(correlation_id)


def generate_llm_correlation_id() -> str:
    """Generate a new correlation ID for LLM operations."""
    return get_heartbeat_logger().generate_correlation_id()


class DataLogger:
    """Manages DEBUG level data logging for LLM input/output."""
    
    def __init__(self, truncate_length: int = 1000, json_depth: int = 3):
        self.truncate_length = truncate_length
        self.json_depth = json_depth
        self.log_format = "json"  # json or text

    def log_input_data(self, agent_name: str, correlation_id: str, 
                      prompt: str, params: Dict[str, Any]) -> None:
        """Log LLM input data at DEBUG level."""
        if self.log_format == "json":
            self._log_input_json(agent_name, correlation_id, prompt, params)
        else:
            self._log_input_text(agent_name, correlation_id, prompt, params)

    def log_output_data(self, agent_name: str, correlation_id: str,
                       response: str, tokens: Optional[int] = None) -> None:
        """Log LLM output data at DEBUG level."""
        if self.log_format == "json":
            self._log_output_json(agent_name, correlation_id, response, tokens)
        else:
            self._log_output_text(agent_name, correlation_id, response, tokens)

    def _format_input_message(self, agent_name: str, correlation_id: str,
                            prompt_size: int, params: Dict[str, Any]) -> str:
        """Format LLM input message."""
        return f"LLM input: {agent_name} - {correlation_id} - prompt_size: {prompt_size} - params: {params}"

    def _format_input_prompt_message(self, prompt: str) -> str:
        """Format truncated input prompt message."""
        truncated_prompt = self._truncate_text(prompt)
        return f"LLM input prompt: {truncated_prompt}"

    def _format_output_message(self, agent_name: str, correlation_id: str,
                             response_size: int, tokens: Optional[int]) -> str:
        """Format LLM output message."""
        token_info = f"tokens: {tokens}" if tokens else "tokens: unknown"
        return f"LLM output: {agent_name} - {correlation_id} - response_size: {response_size} - {token_info}"

    def _format_output_response_message(self, response: str) -> str:
        """Format truncated output response message."""
        truncated_response = self._truncate_text(response)
        return f"LLM response: {truncated_response}"

    def _truncate_text(self, text: str) -> str:
        """Truncate text to configured length."""
        if len(text) <= self.truncate_length:
            return text
        return text[:self.truncate_length] + "..."

    def _log_input_json(self, agent_name: str, correlation_id: str,
                       prompt: str, params: Dict[str, Any]) -> None:
        """Log input data as JSON with depth control."""
        import json
        data = self._build_input_json_data(agent_name, correlation_id, prompt, params)
        logger.debug(f"LLM input: {json.dumps(data, indent=2)}")

    def _build_input_json_data(self, agent_name: str, correlation_id: str,
                              prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build input JSON data structure."""
        return {
            "type": "llm_input",
            "agent_name": agent_name,
            "correlation_id": correlation_id,
            "prompt_size": len(prompt),
            "prompt_preview": self._truncate_text(prompt),
            "parameters": self._sanitize_params(params),
            "timestamp": time.time()
        }

    def _log_output_json(self, agent_name: str, correlation_id: str,
                        response: str, tokens: Optional[int]) -> None:
        """Log output data as JSON with depth control."""
        import json
        data = self._build_output_json_data(agent_name, correlation_id, response, tokens)
        logger.debug(f"LLM output: {json.dumps(data, indent=2)}")

    def _build_output_json_data(self, agent_name: str, correlation_id: str,
                               response: str, tokens: Optional[int]) -> Dict[str, Any]:
        """Build output JSON data structure."""
        return {
            "type": "llm_output",
            "agent_name": agent_name,
            "correlation_id": correlation_id,
            "response_size": len(response),
            "response_preview": self._truncate_text(response),
            "token_count": tokens,
            "timestamp": time.time()
        }

    def _log_input_text(self, agent_name: str, correlation_id: str,
                       prompt: str, params: Dict[str, Any]) -> None:
        """Log input data in text format (legacy)."""
        prompt_size = len(prompt)
        logger.debug(self._format_input_message(agent_name, correlation_id, prompt_size, params))
        logger.debug(self._format_input_prompt_message(prompt))

    def _log_output_text(self, agent_name: str, correlation_id: str,
                        response: str, tokens: Optional[int]) -> None:
        """Log output data in text format (legacy)."""
        response_size = len(response)
        logger.debug(self._format_output_message(agent_name, correlation_id, response_size, tokens))
        logger.debug(self._format_output_response_message(response))

    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize parameters for logging with depth control."""
        return self._limit_depth(params, self.json_depth)

    def _limit_depth(self, obj: Any, max_depth: int, current_depth: int = 0) -> Any:
        """Limit JSON depth for logging."""
        if current_depth >= max_depth:
            return self._truncate_deep_object(obj)
        return self._process_object_by_type(obj, max_depth, current_depth)
    
    def _truncate_deep_object(self, obj: Any) -> Any:
        """Truncate objects that exceed max depth."""
        return str(obj)[:100] if isinstance(obj, (dict, list)) else obj
    
    def _process_object_by_type(self, obj: Any, max_depth: int, current_depth: int) -> Any:
        """Process object based on its type for depth limiting."""
        if isinstance(obj, dict):
            return {k: self._limit_depth(v, max_depth, current_depth + 1) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._limit_depth(item, max_depth, current_depth + 1) for item in obj[:10]]
        return obj

    def _extract_token_count(self, response: Any) -> Optional[int]:
        """Extract token count from LLM response."""
        if hasattr(response, 'response_metadata'):
            metadata = response.response_metadata
            if isinstance(metadata, dict):
                return metadata.get('token_usage', {}).get('total_tokens')
        return None


# Global data logger instance
_data_logger: Optional[DataLogger] = None


def get_data_logger() -> DataLogger:
    """Get the global data logger instance."""
    global _data_logger
    if _data_logger is None:
        _data_logger = DataLogger()
    return _data_logger


def log_llm_input(agent_name: str, correlation_id: str, prompt: str, params: Dict[str, Any]) -> None:
    """Log LLM input data."""
    get_data_logger().log_input_data(agent_name, correlation_id, prompt, params)


def log_llm_output(agent_name: str, correlation_id: str, response: str, tokens: Optional[int] = None) -> None:
    """Log LLM output data."""
    get_data_logger().log_output_data(agent_name, correlation_id, response, tokens)


class SubAgentLogger:
    """Manages INFO level logging for subagent communication."""
    
    def __init__(self, enabled: bool = True):
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
    
    def _build_output_data(self, to_agent: str, from_agent: str, 
                          data_size: int, status: str, correlation_id: str) -> Dict[str, Any]:
        """Build output data dictionary."""
        return {
            "type": "agent_output",
            "to_agent": to_agent,
            "from_agent": from_agent,
            "data_size": data_size,
            "status": status,
            "correlation_id": correlation_id,
            "timestamp": time.time()
        }
    
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