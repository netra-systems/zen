"""Utilities Tests - Split from test_supervisor_integration.py"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.agents.admin_tool_dispatcher import AdminToolDispatcher
from app.agents.state import DeepAgentState

# Add project root to path
from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.tool_dispatcher import ToolDispatcher
from app.llm.llm_manager import LLMManager

# Add project root to path


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