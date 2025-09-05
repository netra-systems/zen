"""Core Tests - Split from test_supervisor_integration.py"""

import sys
from pathlib import Path
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
from datetime import datetime, timezone

import pytest

from netra_backend.app.agents.admin_tool_dispatcher import AdminToolDispatcher
from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager

class StateMergeUtil:
    """Utility class for state merging operations"""
    
    @staticmethod
    def merge_states(state1, state2):
        """Merge two DeepAgentState instances"""
        # Use the user_request from the first state
        merged = DeepAgentState(user_request=state1.user_request)
        
        # Get valid fields from the Pydantic model
        valid_fields = merged.model_fields.keys() if hasattr(merged, 'model_fields') else merged.__fields__.keys()
        
        # Merge all valid attributes
        for attr in valid_fields:
            if attr == "user_request":
                continue  # Already set
                
            val1 = getattr(state1, attr, None)
            val2 = getattr(state2, attr, None)
            
            if val1 is not None and val2 is not None:
                if isinstance(val1, dict) and isinstance(val2, dict):
                    # Deep merge dictionaries
                    merged_dict = val1.copy()
                    for k, v in val2.items():
                        if k in merged_dict and isinstance(merged_dict[k], dict) and isinstance(v, dict):
                            merged_dict[k] = {**merged_dict[k], **v}
                        else:
                            merged_dict[k] = v
                    setattr(merged, attr, merged_dict)
                elif isinstance(val1, list) and isinstance(val2, list):
                    setattr(merged, attr, val1 + val2)
                else:
                    setattr(merged, attr, val1)
            elif val1 is not None:
                setattr(merged, attr, val1)
            elif val2 is not None:
                setattr(merged, attr, val2)
        
        return merged