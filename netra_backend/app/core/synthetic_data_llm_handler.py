# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: CLAUDE.md compliance - Extract LLM interaction logic
# Git: 8-18-25-AM | new
# Change: Extract | Scope: Module | Risk: Low
# Session: llm-handler-extraction | Seq: 1
# Review: Pending | Score: 95
# ================================

"""
Synthetic Data LLM Handler Module

Handles all LLM interactions for synthetic data generation with proper logging,
heartbeat management, and error handling. Extracted from SyntheticDataSubAgent
to maintain single responsibility principle.

Module follows CLAUDE.md constraints:
- File  <= 300 lines
- Functions  <= 8 lines  
- Strong typing
- Single responsibility
"""

from typing import TYPE_CHECKING, Optional

from netra_backend.app.llm.observability import (
    generate_llm_correlation_id,
    log_agent_input,
    log_agent_output,
    start_llm_heartbeat,
    stop_llm_heartbeat,
)
from netra_backend.app.logging_config import central_logger

if TYPE_CHECKING:
    from netra_backend.app.llm.llm_manager import LLMManager

logger = central_logger.get_logger(__name__)


class SyntheticDataLLMHandler:
    """
    Handles LLM interactions for synthetic data generation.
    
    Provides centralized LLM communication with proper logging,
    heartbeat management, and error handling for synthetic data agents.
    """
    
    def __init__(self, llm_manager: "LLMManager", agent_name: str = "SyntheticDataSubAgent"):
        """
        Initialize LLM handler.
        
        Args:
            llm_manager: LLM manager instance for API calls
            agent_name: Name of the calling agent for logging
        """
        self.llm_manager = llm_manager
        self.agent_name = agent_name
    
    async def call_llm_with_logging(self, prompt: str) -> str:
        """
        Call LLM with proper logging and heartbeat management.
        
        Args:
            prompt: LLM prompt string
            
        Returns:
            LLM response string
            
        Raises:
            Exception: If LLM call fails
        """
        correlation_id = self._setup_llm_tracking()
        
        try:
            return await self._execute_llm_call(prompt, correlation_id)
        finally:
            stop_llm_heartbeat(correlation_id)
    
    def _setup_llm_tracking(self) -> str:
        """
        Setup LLM tracking and heartbeat.
        
        Returns:
            Correlation ID for tracking
        """
        correlation_id = generate_llm_correlation_id()
        start_llm_heartbeat(correlation_id, self.agent_name)
        return correlation_id
    
    async def _execute_llm_call(self, prompt: str, correlation_id: str) -> str:
        """
        Execute LLM call with error handling.
        
        Args:
            prompt: LLM prompt string
            correlation_id: Tracking correlation ID
            
        Returns:
            LLM response string
            
        Raises:
            Exception: If LLM call fails
        """
        try:
            return await self._execute_llm_with_logging(prompt, correlation_id)
        except Exception as e:
            self._log_llm_error(correlation_id)
            raise
    
    async def _execute_llm_with_logging(self, prompt: str, correlation_id: str) -> str:
        """
        Execute LLM call with input/output logging.
        
        Args:
            prompt: LLM prompt string
            correlation_id: Tracking correlation ID
            
        Returns:
            LLM response string
        """
        self._log_llm_input(prompt, correlation_id)
        response = await self._get_llm_response(prompt)
        self._log_llm_success(response, correlation_id)
        return response
    
    async def _get_llm_response(self, prompt: str) -> str:
        """
        Get response from LLM manager.
        
        Args:
            prompt: LLM prompt string
            
        Returns:
            LLM response string
        """
        return await self.llm_manager.ask_llm(prompt, llm_config_name='default')
    
    def _log_llm_input(self, prompt: str, correlation_id: str) -> None:
        """
        Log LLM input with correlation ID.
        
        Args:
            prompt: Input prompt string
            correlation_id: Tracking correlation ID
        """
        log_agent_input(
            self.agent_name, "LLM", len(prompt), correlation_id
        )
    
    def _log_llm_success(self, response: str, correlation_id: str) -> None:
        """
        Log successful LLM response.
        
        Args:
            response: LLM response string
            correlation_id: Tracking correlation ID
        """
        log_agent_output(
            "LLM", self.agent_name, 
            len(response), "success", correlation_id
        )
    
    def _log_llm_error(self, correlation_id: str) -> None:
        """
        Log LLM error response.
        
        Args:
            correlation_id: Tracking correlation ID
        """
        log_agent_output(
            "LLM", self.agent_name, 0, "error", correlation_id
        )


class PromptBuilder:
    """
    Builder for creating structured prompts for synthetic data generation.
    
    Provides utilities to create well-formatted prompts with proper
    field specifications and instructions.
    """
    
    @staticmethod
    def create_parsing_prompt(user_request: str) -> str:
        """
        Create prompt for parsing user request into workload parameters.
        
        Args:
            user_request: User's synthetic data request
            
        Returns:
            Formatted parsing prompt
        """
        return PromptBuilder._build_complete_parsing_prompt(user_request)
    
    @staticmethod
    def _create_base_prompt(user_request: str) -> str:
        """
        Create base prompt for user request analysis.
        
        Args:
            user_request: User's request string
            
        Returns:
            Base prompt string
        """
        return f"Analyze this request for synthetic data parameters: {user_request}"
    
    @staticmethod
    def _build_complete_parsing_prompt(user_request: str) -> str:
        """
        Build complete parsing prompt with all components.
        
        Args:
            user_request: User's synthetic data request
            
        Returns:
            Complete formatted prompt
        """
        components = PromptBuilder._gather_prompt_components(user_request)
        return PromptBuilder._format_parsing_prompt(components)
    
    @staticmethod
    def _gather_prompt_components(user_request: str) -> dict:
        """
        Gather all components needed for parsing prompt.
        
        Args:
            user_request: User's request string
            
        Returns:
            Dictionary of prompt components
        """
        return {
            'base': PromptBuilder._create_base_prompt(user_request),
            'fields': PromptBuilder._get_prompt_fields_spec(),
            'instructions': "Default volume to 1000 if not specified."
        }
    
    @staticmethod
    def _format_parsing_prompt(components: dict) -> str:
        """
        Format complete parsing prompt with sections.
        
        Args:
            components: Dictionary with base, fields, instructions
            
        Returns:
            Complete formatted prompt
        """
        return f"""
{components['base']}

{components['fields']}

{components['instructions']}
"""
    
    @staticmethod
    def _get_prompt_fields_spec() -> str:
        """
        Get prompt fields specification string.
        
        Returns:
            Fields specification for JSON response
        """
        spec_parts = PromptBuilder._build_fields_spec_parts()
        return PromptBuilder._format_fields_spec(spec_parts)
    
    @staticmethod
    def _build_fields_spec_parts() -> dict:
        """
        Build individual parts of fields specification.
        
        Returns:
            Dictionary of specification parts
        """
        return {
            'types': "workload_type (inference_logs|training_data|performance_metrics|cost_data|custom)",
            'ranges': "volume (100-1000000), time_range_days (1-365)",
            'options': "distribution (normal|uniform|exponential), noise_level (0.0-0.5), custom_parameters"
        }
    
    @staticmethod
    def _format_fields_spec(spec_parts: dict) -> str:
        """
        Format fields specification from parts.
        
        Args:
            spec_parts: Dictionary with types, ranges, options
            
        Returns:
            Formatted fields specification
        """
        return f"Return JSON with fields: {spec_parts['types']}, {spec_parts['ranges']}, {spec_parts['options']}."


# Factory function for easy instantiation
def create_synthetic_data_llm_handler(
    llm_manager: "LLMManager", 
    agent_name: str = "SyntheticDataSubAgent"
) -> SyntheticDataLLMHandler:
    """
    Factory function to create SyntheticDataLLMHandler instance.
    
    Args:
        llm_manager: LLM manager instance
        agent_name: Name of calling agent (defaults to SyntheticDataSubAgent)
        
    Returns:
        Configured SyntheticDataLLMHandler instance
    """
    return SyntheticDataLLMHandler(llm_manager, agent_name)


# Utility functions for backward compatibility
async def call_llm_with_logging(
    llm_manager: "LLMManager", 
    prompt: str,
    agent_name: str = "SyntheticDataSubAgent"
) -> str:
    """
    Convenience function for one-off LLM calls with logging.
    
    Args:
        llm_manager: LLM manager instance
        prompt: LLM prompt string
        agent_name: Name of calling agent
        
    Returns:
        LLM response string
    """
    handler = create_synthetic_data_llm_handler(llm_manager, agent_name)
    return await handler.call_llm_with_logging(prompt)


def create_parsing_prompt(user_request: str) -> str:
    """
    Convenience function to create parsing prompt.
    
    Args:
        user_request: User's synthetic data request
        
    Returns:
        Formatted parsing prompt
    """
    return PromptBuilder.create_parsing_prompt(user_request)