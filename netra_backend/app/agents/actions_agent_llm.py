"""LLM integration handler for ActionsToMeetGoalsSubAgent following SRP."""

from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.llm.observability import (
    generate_llm_correlation_id,
    log_agent_communication,
    log_agent_input,
    log_agent_output,
    start_llm_heartbeat,
    stop_llm_heartbeat,
)
from netra_backend.app.logging_config import central_logger as logger


class ActionsAgentLLMHandler:
    """Handles LLM requests and monitoring for the Actions agent."""

    def __init__(self, llm_manager: LLMManager):
        """Initialize with LLM manager."""
        self.llm_manager = llm_manager

    async def get_llm_response(self, prompt: str, run_id: str) -> str:
        """Get LLM response with monitoring."""
        correlation_id = self._prepare_llm_request(prompt, run_id)
        return await self._execute_monitored_llm_request(prompt, correlation_id)

    async def _execute_monitored_llm_request(
        self, prompt: str, correlation_id: str
    ) -> str:
        """Execute LLM request with monitoring cleanup."""
        try:
            response = await self._execute_llm_request(prompt, correlation_id)
            self._finalize_llm_request_success(response, correlation_id)
            return response
        finally:
            stop_llm_heartbeat(correlation_id)

    def _prepare_llm_request(self, prompt: str, run_id: str) -> str:
        """Prepare LLM request with logging and monitoring setup."""
        correlation_id = generate_llm_correlation_id()
        start_llm_heartbeat(correlation_id, "ActionsToMeetGoalsSubAgent")
        self._log_prompt_size(prompt, run_id)
        log_agent_input(
            "ActionsToMeetGoalsSubAgent", "LLM",
            len(prompt), correlation_id
        )
        return correlation_id

    async def _execute_llm_request(self, prompt: str, correlation_id: str) -> str:
        """Execute the actual LLM request."""
        return await self.llm_manager.ask_llm(
            prompt, llm_config_name='actions_to_meet_goals'
        )

    def _finalize_llm_request_success(
        self, response: str, correlation_id: str
    ) -> None:
        """Finalize successful LLM request with output logging."""
        log_agent_output(
            "LLM", "ActionsToMeetGoalsSubAgent",
            len(response) if response else 0,
            "success", correlation_id
        )

    def _log_prompt_size(self, prompt: str, run_id: str) -> None:
        """Log large prompt warning."""
        size_mb = len(prompt) / (1024 * 1024)
        if size_mb > 1:
            logger.info(f"Large prompt ({size_mb:.2f}MB) for {run_id}")

    def get_health_status(self) -> dict:
        """Get LLM handler health status."""
        return {
            "service": "llm_handler",
            "status": "healthy",
            "llm_manager": "connected" if self.llm_manager else "disconnected"
        }