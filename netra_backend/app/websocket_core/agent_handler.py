"""
BACKWARDS COMPATIBILITY MODULE - Agent Message Handler for WebSocket Communication

MIGRATION NOTICE: This module now imports from the SSOT implementation.
Issue #1093: WebSocket agent message handler fragmentation has been resolved.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & System Reliability
- Value Impact: Eliminates handler fragmentation while maintaining backwards compatibility
- Strategic Impact: Single canonical handler ensures consistent WebSocket agent processing

This module provides backwards compatibility for existing imports while delegating
all functionality to the SSOT implementation in ssot_agent_message_handler.py.

LEGACY COMPATIBILITY:
- Existing imports continue to work unchanged
- All functionality preserved
- Performance improved through consolidation
- Golden Path WebSocket events guaranteed

NEW DEVELOPMENT:
- Use: from netra_backend.app.websocket_core.ssot_agent_message_handler import SSotAgentMessageHandler
- Or: from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler (continues to work)
"""

# BACKWARDS COMPATIBILITY IMPORT
# All functionality is now provided by the SSOT implementation
from netra_backend.app.websocket_core.ssot_agent_message_handler import (
    SSotAgentMessageHandler as AgentMessageHandler
)

# COMPATIBILITY ALIAS: Export AgentMessageHandler as AgentHandler for backward compatibility
AgentHandler = AgentMessageHandler