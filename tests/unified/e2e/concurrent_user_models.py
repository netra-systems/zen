"""Concurrent User Testing Models and Data Structures

Business Value Justification (BVJ):
- Segment: Enterprise (concurrent user support required)
- Business Goal: Clean modular data structures for concurrent testing
- Value Impact: Enables comprehensive concurrent user validation
- Revenue Impact: Supports $100K+ ARR enterprise features

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- Modular design with focused responsibilities
"""

import uuid
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ConcurrentUserMetrics:
    """Metrics tracking for concurrent user testing"""
    total_users: int = 0
    successful_logins: int = 0
    successful_connections: int = 0
    successful_messages: int = 0
    response_times: List[float] = field(default_factory=list)
    isolation_violations: int = 0
    cross_contamination_detected: bool = False


@dataclass
class UserSession:
    """Individual user session data and state"""
    user_id: str
    email: str
    access_token: Optional[str] = None
    websocket_client: Optional[Any] = None  # Can be MockWebSocketClient or RealWebSocketClient
    sent_messages: List[Dict[str, Any]] = field(default_factory=list)
    received_responses: List[Dict[str, Any]] = field(default_factory=list)
    thread_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class MockServiceManager:
    """Mock service manager for testing without real services"""
    
    async def start_auth_service(self):
        """Mock auth service start"""
        await __import__('asyncio').sleep(0.1)
    
    async def start_backend_service(self):
        """Mock backend service start"""
        await __import__('asyncio').sleep(0.1)
    
    async def stop_all_services(self):
        """Mock service stop"""
        await __import__('asyncio').sleep(0.1)


class MockWebSocketClient:
    """Mock WebSocket client for testing concurrent behavior"""
    
    def __init__(self, ws_url: str, user_id: str):
        self.ws_url = ws_url
        self.user_id = user_id
        self.connected = False
        self.messages_sent = []
        self.responses = []
    
    async def connect(self, headers: Optional[Dict[str, str]] = None) -> bool:
        """Mock WebSocket connection"""
        await __import__('asyncio').sleep(0.05)  # Simulate connection time
        self.connected = True
        return True
    
    async def send(self, message: Dict[str, Any]) -> bool:
        """Mock message sending"""
        if not self.connected:
            return False
        await __import__('asyncio').sleep(0.02)  # Simulate send time
        self.messages_sent.append(message)
        return True
    
    async def receive(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Mock message receiving with unique user response"""
        if not self.connected:
            return None
        
        await __import__('asyncio').sleep(0.1)  # Simulate processing time
        
        # Generate unique response based on user_id to test isolation
        response = {
            "type": "chat_response",
            "content": f"AI response for {self.user_id}: Your AI costs have been analyzed.",
            "thread_id": str(uuid.uuid4()),
            "user_id": self.user_id,
            "timestamp": time.time()
        }
        self.responses.append(response)
        return response
    
    async def close(self):
        """Mock connection close"""
        self.connected = False


class IsolationValidator:
    """Validates user session isolation and prevents cross-contamination"""
    
    def __init__(self, metrics: ConcurrentUserMetrics):
        self.metrics = metrics
    
    def validate_user_isolation(self, users: List[UserSession]) -> Dict[str, Any]:
        """Validate that user sessions are properly isolated"""
        isolation_results = {
            "thread_id_conflicts": self._check_thread_conflicts(users),
            "response_contamination": self._check_response_contamination(users),
            "token_isolation": self._check_token_isolation(users),
            "content_isolation": self._check_content_isolation(users)
        }
        
        violations = sum(1 for v in isolation_results.values() if v > 0)
        self.metrics.isolation_violations = violations
        self.metrics.cross_contamination_detected = violations > 0
        
        return isolation_results
    
    def _check_thread_conflicts(self, users: List[UserSession]) -> int:
        """Check for thread ID conflicts between users"""
        thread_ids = [u.thread_id for u in users]
        unique_threads = set(thread_ids)
        return len(thread_ids) - len(unique_threads)
    
    def _check_response_contamination(self, users: List[UserSession]) -> int:
        """Check if users received responses for other users' messages"""
        contamination_count = 0
        for user in users:
            for response in user.received_responses:
                response_content = str(response.get("content", "")).lower()
                # Check if response contains other users' identifiers
                for other_user in users:
                    if other_user.user_id != user.user_id:
                        if other_user.user_id.lower() in response_content:
                            contamination_count += 1
        
        return contamination_count
    
    def _check_token_isolation(self, users: List[UserSession]) -> int:
        """Check that users have unique access tokens"""
        tokens = [u.access_token for u in users if u.access_token]
        unique_tokens = set(tokens)
        return len(tokens) - len(unique_tokens)
    
    def _check_content_isolation(self, users: List[UserSession]) -> int:
        """Check that message content remains isolated per user"""
        content_violations = 0
        for user in users:
            sent_content = [m.get("content", "") for m in user.sent_messages]
            
            for other_user in users:
                if other_user.user_id != user.user_id:
                    other_responses = [r.get("content", "") for r in other_user.received_responses]
                    # Check if this user's content appears in other user's responses
                    for content in sent_content:
                        for response in other_responses:
                            if content.lower() in response.lower():
                                content_violations += 1
        
        return content_violations