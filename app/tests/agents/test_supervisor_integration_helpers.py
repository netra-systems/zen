"""Utilities Tests - Split from test_supervisor_integration.py"""

import pytest
import asyncio
import json
import time
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.supervisor.execution_context import (
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher
from app.tests.helpers.supervisor_test_helpers import (
from app.agents.admin_tool_dispatcher import AdminToolDispatcher

    def __init__(self, llm_manager, websocket_manager):
        self.llm_manager = llm_manager
        self.websocket_manager = websocket_manager
        self.quality_threshold = 0.7

    def __init__(self, llm_manager, tool_dispatcher):
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.vector_store = None

    def __init__(self, llm_manager, tool_dispatcher):
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.data_sources = None
        self.enrichment_service = None

    def merge_states(self, state1, state2):
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
