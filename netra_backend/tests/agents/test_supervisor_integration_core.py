"""Core Tests - Split from test_supervisor_integration.py"""

import sys
from pathlib import Path
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
from datetime import datetime, timezone

import pytest

from netra_backend.app.admin.tools.unified_admin_dispatcher import UnifiedAdminToolDispatcher as AdminToolDispatcher
from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager

# REMOVED_SYNTAX_ERROR: class StateMergeUtil:
    # REMOVED_SYNTAX_ERROR: """Utility class for state merging operations"""

    # REMOVED_SYNTAX_ERROR: @staticmethod
# REMOVED_SYNTAX_ERROR: def merge_states(state1, state2):
    # REMOVED_SYNTAX_ERROR: """Merge two DeepAgentState instances"""
    # Use the user_request from the first state
    # REMOVED_SYNTAX_ERROR: merged = DeepAgentState(user_request=state1.user_request)

    # Get valid fields from the Pydantic model
    # REMOVED_SYNTAX_ERROR: valid_fields = merged.model_fields.keys() if hasattr(merged, 'model_fields') else merged.__fields__.keys()

    # Merge all valid attributes
    # REMOVED_SYNTAX_ERROR: for attr in valid_fields:
        # REMOVED_SYNTAX_ERROR: if attr == "user_request":
            # REMOVED_SYNTAX_ERROR: continue  # Already set

            # REMOVED_SYNTAX_ERROR: val1 = getattr(state1, attr, None)
            # REMOVED_SYNTAX_ERROR: val2 = getattr(state2, attr, None)

            # REMOVED_SYNTAX_ERROR: if val1 is not None and val2 is not None:
                # REMOVED_SYNTAX_ERROR: if isinstance(val1, dict) and isinstance(val2, dict):
                    # Deep merge dictionaries
                    # REMOVED_SYNTAX_ERROR: merged_dict = val1.copy()
                    # REMOVED_SYNTAX_ERROR: for k, v in val2.items():
                        # REMOVED_SYNTAX_ERROR: if k in merged_dict and isinstance(merged_dict[k], dict) and isinstance(v, dict):
                            # REMOVED_SYNTAX_ERROR: merged_dict[k] = {**merged_dict[k], **v]
                            # REMOVED_SYNTAX_ERROR: else:
                                # REMOVED_SYNTAX_ERROR: merged_dict[k] = v
                                # REMOVED_SYNTAX_ERROR: setattr(merged, attr, merged_dict)
                                # REMOVED_SYNTAX_ERROR: elif isinstance(val1, list) and isinstance(val2, list):
                                    # REMOVED_SYNTAX_ERROR: setattr(merged, attr, val1 + val2)
                                    # REMOVED_SYNTAX_ERROR: else:
                                        # REMOVED_SYNTAX_ERROR: setattr(merged, attr, val1)
                                        # REMOVED_SYNTAX_ERROR: elif val1 is not None:
                                            # REMOVED_SYNTAX_ERROR: setattr(merged, attr, val1)
                                            # REMOVED_SYNTAX_ERROR: elif val2 is not None:
                                                # REMOVED_SYNTAX_ERROR: setattr(merged, attr, val2)

                                                # REMOVED_SYNTAX_ERROR: return merged