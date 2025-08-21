"""LLM observability module.

This module provides backward compatibility imports for the refactored
modular observability components.
"""

# Import from the new modular structure for backward compatibility
from netra_backend.app.llm.data_logger import (
    DataLogger,
    get_data_logger,
    log_llm_input,
    log_llm_output,
)
from netra_backend.app.llm.heartbeat_logger import (
    HeartbeatLogger,
    generate_llm_correlation_id,
    get_heartbeat_logger,
    start_llm_heartbeat,
    stop_llm_heartbeat,
)
from netra_backend.app.llm.subagent_logger import (
    SubAgentLogger,
    get_subagent_logger,
    log_agent_communication,
    log_agent_input,
    log_agent_output,
)

# Re-export for backward compatibility
__all__ = [
    'HeartbeatLogger', 'get_heartbeat_logger', 'start_llm_heartbeat',
    'stop_llm_heartbeat', 'generate_llm_correlation_id',
    'DataLogger', 'get_data_logger', 'log_llm_input', 'log_llm_output',
    'SubAgentLogger', 'get_subagent_logger', 'log_agent_communication',
    'log_agent_input', 'log_agent_output'
]