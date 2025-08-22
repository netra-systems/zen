"""
Synthetic Data LLM Handler Module

Handles all LLM interactions for synthetic data operations,
including logging, tracking, and response management.
"""

from typing import Optional

from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.llm.observability import (
    generate_llm_correlation_id,
    log_agent_input,
    log_agent_output,
    start_llm_heartbeat,
    stop_llm_heartbeat,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class LLMCallTracker:
    """Tracks LLM call correlation and heartbeat"""
    
    @staticmethod
    def setup_llm_tracking() -> str:
        """Setup LLM tracking and heartbeat."""
        correlation_id = generate_llm_correlation_id()
        start_llm_heartbeat(correlation_id, "SyntheticDataSubAgent")
        return correlation_id
    
    @staticmethod
    def cleanup_tracking(correlation_id: str) -> None:
        """Clean up LLM tracking"""
        stop_llm_heartbeat(correlation_id)


class LLMLogger:
    """Handles LLM call logging"""
    
    @staticmethod
    def log_llm_input(prompt: str, correlation_id: str) -> None:
        """Log LLM input with correlation ID."""
        log_agent_input(
            "SyntheticDataSubAgent", "LLM", len(prompt), correlation_id
        )
    
    @staticmethod
    def log_llm_success(response: str, correlation_id: str) -> None:
        """Log successful LLM response."""
        log_agent_output(
            "LLM", "SyntheticDataSubAgent", 
            len(response), "success", correlation_id
        )
    
    @staticmethod
    def log_llm_error(correlation_id: str) -> None:
        """Log LLM error response."""
        log_agent_output(
            "LLM", "SyntheticDataSubAgent", 0, "error", correlation_id
        )


class SyntheticDataLLMExecutor:
    """Executes LLM calls with proper logging and error handling"""
    
    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager
        self.tracker = LLMCallTracker()
        self.logger = LLMLogger()
    
    async def call_llm_with_logging(self, prompt: str) -> str:
        """Call LLM with proper logging and heartbeat."""
        correlation_id = self.tracker.setup_llm_tracking()
        
        try:
            return await self._execute_llm_call(prompt, correlation_id)
        finally:
            self.tracker.cleanup_tracking(correlation_id)
    
    async def _execute_llm_call(self, prompt: str, correlation_id: str) -> str:
        """Execute LLM call with logging."""
        try:
            return await self._execute_llm_with_logging(prompt, correlation_id)
        except Exception as e:
            self.logger.log_llm_error(correlation_id)
            raise
    
    async def _execute_llm_with_logging(self, prompt: str, correlation_id: str) -> str:
        """Execute LLM call with input/output logging."""
        self.logger.log_llm_input(prompt, correlation_id)
        response = await self._get_llm_response(prompt)
        self.logger.log_llm_success(response, correlation_id)
        return response
    
    async def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM manager"""
        return await self.llm_manager.ask_llm(prompt, llm_config_name='default')