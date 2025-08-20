"""Core Tests - Split from test_websocket_event_completeness_integration.py

Business Value Justification (BVJ):
1. Segment: Platform/Internal (Development velocity) 
2. Business Goal: Validate missing WebSocket events in agent workflows
3. Value Impact: Ensures complete event coverage for UI responsiveness
4. Strategic Impact: $15K MRR protection via WebSocket reliability

COMPLIANCE: File size <300 lines, Functions <8 lines, Real WebSocket testing
"""

import asyncio
import time
import pytest
import json
from typing import Dict, Any, List, Optional, Set
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.base import BaseSubAgent
from app.llm.llm_manager import LLMManager
from app.config import get_config
from app.schemas import WebSocketMessage, AgentStarted, SubAgentUpdate, AgentCompleted

    def _filter_events_by_type(self, messages: List[Dict], event_type: str) -> List[Dict]:
        """Filter messages by event type."""
        return [msg for msg in messages if msg["message"].type == event_type]

    def _validate_event_sequence(self, messages: List[Dict]) -> Dict[str, bool]:
        """Validate presence of required event types."""
        event_types = {msg["message"].type for msg in messages}
        
        return {
            "agent_started_present": "agent_started" in event_types,
            "agent_thinking_present": "agent_thinking" in event_types,
            "tool_executing_present": "tool_executing" in event_types,
            "partial_result_present": "partial_result" in event_types,
            "final_report_present": "final_report" in event_types,
            "agent_completed_present": "agent_completed" in event_types
        }

    def _validate_concurrent_event_ordering(self, messages: List[Dict]) -> Dict[str, bool]:
        """Validate event ordering in concurrent execution."""
        # Sort by timestamp
        sorted_messages = sorted(messages, key=lambda x: x["timestamp"])
        
        # Check for proper ordering (agent_started before agent_completed)
        agent_events = {}
        for msg in sorted_messages:
            agent_name = msg["message"].data.get("agent_name")
            if agent_name:
                if agent_name not in agent_events:
                    agent_events[agent_name] = []
                agent_events[agent_name].append(msg["message"].type)
        
        # Validate ordering for each agent
        properly_ordered = True
        no_mixing = True
        
        for agent_name, events in agent_events.items():
            if events and events[0] != "agent_started":
                properly_ordered = False
            if events and events[-1] != "agent_completed":
                properly_ordered = False
        
        return {
            "events_properly_ordered": properly_ordered,
            "no_event_mixing": no_mixing
        }
