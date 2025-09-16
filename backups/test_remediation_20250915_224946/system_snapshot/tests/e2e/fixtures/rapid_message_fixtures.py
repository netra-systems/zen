"""
Shared fixtures for rapid message succession E2E tests.

Business Value Justification (BVJ):
- Segment: All Segments
- Business Goal: Test Infrastructure 
- Value Impact: Shared test fixtures for consistent rapid message testing
- Strategic/Revenue Impact: Enables comprehensive testing of message handling
"""

import asyncio
import json
import logging
import os
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)

# Environment configuration
E2E_TEST_CONFIG = {
    "websocket_url": get_env().get("E2E_WEBSOCKET_URL", "ws://localhost:8765"),
    "backend_url": get_env().get("E2E_BACKEND_URL", "http://localhost:8000"),
    "auth_service_url": get_env().get("E2E_AUTH_SERVICE_URL", "http://localhost:8081"),
    "skip_real_services": get_env().get("SKIP_REAL_SERVICES", "true").lower() == "true",
    "test_mode": get_env().get("RAPID_MESSAGE_TEST_MODE", "mock")
}

@dataclass
class MessageSequenceEntry:
    """Entry in message sequence tracking."""
    message_id: str
    user_id: str
    sequence_num: int
    content: str
    timestamp: datetime
    status: str = "pending"
    response_id: Optional[str] = None
    processing_time: Optional[float] = None
    agent_assignments: List[str] = field(default_factory=list)
    state_updates: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class MessageBurstResult:
    """Result of a rapid message burst test."""
    burst_id: str
    total_messages: int
    successful_sends: int
    processing_times: List[float]
    sequence_violations: List[str]
    duplicate_responses: List[str]
    state_inconsistencies: List[Dict[str, Any]]
    burst_duration: float

class MessageSequenceValidator:
    """Validates message sequence ordering and idempotency."""
    
    def __init__(self):
        self.message_log: Dict[str, MessageSequenceEntry] = {}
        self.sequence_by_user: Dict[str, List[str]] = defaultdict(list)
        self.response_cache: Dict[str, str] = {}
        self.processing_times: List[float] = []
        
    def track_message(self, entry: MessageSequenceEntry):
        """Track a message in the sequence."""
        self.message_log[entry.message_id] = entry
        self.sequence_by_user[entry.user_id].append(entry.message_id)
        
    def validate_sequence_order(self, user_id: str) -> List[str]:
        """Validate message processing order for a user."""
        violations = []
        user_messages = self.sequence_by_user.get(user_id, [])
        
        for i in range(1, len(user_messages)):
            current_msg = self.message_log[user_messages[i]]
            prev_msg = self.message_log[user_messages[i-1]]
            
            if current_msg.sequence_num <= prev_msg.sequence_num:
                violations.append(
                    f"Sequence violation: {current_msg.message_id} "
                    f"({current_msg.sequence_num}) processed before "
                    f"{prev_msg.message_id} ({prev_msg.sequence_num})"
                )
        
        return violations
        
    def check_duplicate_responses(self, user_id: str) -> List[str]:
        """Check for duplicate responses."""
        duplicates = []
        user_messages = self.sequence_by_user.get(user_id, [])
        response_counts = defaultdict(int)
        
        for msg_id in user_messages:
            msg = self.message_log[msg_id]
            if msg.response_id:
                response_counts[msg.response_id] += 1
                
        for response_id, count in response_counts.items():
            if count > 1:
                duplicates.append(f"Duplicate response {response_id} (count: {count})")
                
        return duplicates

@pytest.fixture
async def user_token():
    """Generate a test user token."""
    if E2E_TEST_CONFIG["skip_real_services"]:
        return f"test_token_{uuid.uuid4().hex[:8]}"
    
    # Real token generation would go here
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.post(
            f"{E2E_TEST_CONFIG['auth_service_url']}/test/token",
            json={"user_type": "test", "permissions": ["message:send"]}
        )
        return response.json()["token"]

@pytest.fixture
def message_validator():
    """Create a message sequence validator."""
    return MessageSequenceValidator()

@pytest.fixture
def test_config():
    """Provide test configuration."""
    return E2E_TEST_CONFIG.copy()
