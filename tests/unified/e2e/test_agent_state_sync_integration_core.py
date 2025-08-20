"""Core Tests - Split from test_agent_state_sync_integration.py

Business Value Justification (BVJ):
- Segment: Mid to Enterprise customers using multi-tab workflows
- Business Goal: Retention and user experience optimization
- Value Impact: Prevents session state loss that causes user frustration
- Strategic/Revenue Impact: Protects $22K MRR from multi-session use cases

Test Coverage:
- State persistence during WebSocket reconnections
- Session synchronization across multiple browser tabs
- Recovery mechanisms for interrupted agent workflows
- Cross-session data consistency validation
"""

import asyncio
import pytest
import time
import uuid
import json
import websockets
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, asdict
from tests.unified.jwt_token_helpers import JWTTestHelper
from app.schemas.shared_types import AgentStatus, ProcessingResult

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def __init__(self):
        """Initialize state sync tester."""
        self.jwt_helper = JWTTestHelper()
        self.backend_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000"
        self.test_sessions: List[str] = []
