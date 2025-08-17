"""LLM data logging module.

Manages DEBUG level data logging for LLM input/output with JSON and text formats.
Supports data truncation and depth limiting for optimal log readability.
"""
import time
from typing import Optional, Dict, Any
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DataLogger:
    """Manages DEBUG level data logging for LLM input/output."""
    
    def __init__(self, truncate_length: int = 1000, json_depth: int = 3):
        """Initialize data logger with configuration."""
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

    def _build_input_metadata(self, agent_name: str, correlation_id: str) -> Dict[str, Any]:
        """Build basic input metadata structure."""
        return {
            "type": "llm_input",
            "agent_name": agent_name,
            "correlation_id": correlation_id,
            "timestamp": time.time()
        }
    
    def _build_input_json_data(self, agent_name: str, correlation_id: str,
                              prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build input JSON data structure."""
        data = self._build_input_metadata(agent_name, correlation_id)
        data.update({
            "prompt_size": len(prompt),
            "prompt_preview": self._truncate_text(prompt),
            "parameters": self._sanitize_params(params)
        })
        return data

    def _log_output_json(self, agent_name: str, correlation_id: str,
                        response: str, tokens: Optional[int]) -> None:
        """Log output data as JSON with depth control."""
        import json
        data = self._build_output_json_data(agent_name, correlation_id, response, tokens)
        logger.debug(f"LLM output: {json.dumps(data, indent=2)}")

    def _build_output_metadata(self, agent_name: str, correlation_id: str) -> Dict[str, Any]:
        """Build basic output metadata structure."""
        return {
            "type": "llm_output",
            "agent_name": agent_name,
            "correlation_id": correlation_id,
            "timestamp": time.time()
        }
    
    def _build_output_json_data(self, agent_name: str, correlation_id: str,
                               response: str, tokens: Optional[int]) -> Dict[str, Any]:
        """Build output JSON data structure."""
        data = self._build_output_metadata(agent_name, correlation_id)
        data.update({
            "response_size": len(response),
            "response_preview": self._truncate_text(response),
            "token_count": tokens
        })
        return data

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