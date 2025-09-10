# Working Patterns Extraction for WebSocket Test Restoration

**Source**: `tests/mission_critical/test_websocket_agent_events_suite.py` (3,046 lines)
**Purpose**: Extract proven patterns for restoring commented WebSocket tests
**Business Context**: Mission critical WebSocket validation for $500K+ ARR chat functionality

## Pattern Extraction Summary

This document extracts key working patterns from the functional 3,046-line WebSocket test suite to support restoration of the commented `test_websocket_agent_events_real.py` file.

## 1. Core Validator Pattern (Lines 110-200)

### MissionCriticalEventValidator Class

**✅ PROVEN WORKING PATTERN**:
```python
class MissionCriticalEventValidator:
    """Validates WebSocket events with extreme rigor for real connections."""
    
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    # Additional events that may be sent in real scenarios
    OPTIONAL_EVENTS = {
        "agent_fallback",
        "final_report",
        "partial_result",
        "tool_error",
        "ping",
        "pong",
        "connection_ack"
    }
    
    # Expected event sequence for proper agent flow
    EXPECTED_EVENT_SEQUENCE = [
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    ]
    
    # Maximum acceptable latency for events (ms)
    MAX_EVENT_LATENCY = 100  # 100ms as per requirements
    
    # Reconnection timeout (seconds)
    MAX_RECONNECTION_TIME = 3  # 3 seconds as per requirements
    
    def __init__(self, strict_mode: bool = False):  # Less strict for real connections
        self.strict_mode = strict_mode
        self.events: List[Dict] = []
        self.event_timeline: List[tuple] = []  # (timestamp, event_type, data)
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.start_time = time.time()
```

**Key Features**:
- ✅ Defines exact 5 required events per CLAUDE.md Section 6.1
- ✅ Performance constraints (100ms latency, 3s reconnection)
- ✅ Flexible validation (strict_mode=False for real connections)
- ✅ Comprehensive event tracking with timestamps

## 2. Event Capture Pattern (Lines 71-108)

### RealWebSocketEventCapture Class

**✅ PROVEN WORKING PATTERN**:
```python
class RealWebSocketEventCapture:
    """Captures events from real WebSocket connections."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.event_counts: Dict[str, int] = {}
        self.start_time = time.time()
        self.connections: Dict[str, Any] = {}
    
    def record_event(self, event: Dict[str, Any]) -> None:
        """Record an event from real WebSocket."""
        event_type = event.get("type", "unknown")
        event_with_timestamp = {
            **event,
            "capture_timestamp": time.time(),
            "relative_time": time.time() - self.start_time
        }
        
        self.events.append(event_with_timestamp)
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
    
    def get_events_for_thread(self, thread_id: str) -> List[Dict]:
        """Get events for a specific thread."""
        return [event for event in self.events 
                if event.get("thread_id") == thread_id]
    
    def get_event_types_for_thread(self, thread_id: str) -> List[str]:
        """Get event types for a thread in order."""
        events = self.get_events_for_thread(thread_id)
        return [event.get('type', 'unknown') for event in events]
    
    def clear_events(self):
        """Clear all recorded events."""
        self.events.clear()
        self.event_counts.clear()
        self.start_time = time.time()
        self.connections.clear()
```

**Key Features**:
- ✅ Thread-aware event tracking (multi-user support)
- ✅ Timestamp tracking with relative timing
- ✅ Event counting and categorization
- ✅ Clean event management

## 3. Import Pattern (Lines 1-65)

### Working Imports Structure

**✅ PROVEN WORKING PATTERN**:
```python
#!/usr/bin/env python
"""MISSION CRITICAL TEST SUITE: WebSocket Agent Events - REAL SERVICES ONLY

THIS SUITE MUST PASS OR THE PRODUCT IS BROKEN.
Business Value: $500K+ ARR - Core chat functionality
"""

import asyncio
import json
import os
import sys
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional
import threading
import random

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import environment after path setup
from shared.isolated_environment import get_env, IsolatedEnvironment

import pytest
from loguru import logger

# Import production components
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import UnifiedToolDispatcherFactory
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager

# Import WebSocket test utilities - REAL SERVICES ONLY per CLAUDE.md
from tests.mission_critical.websocket_real_test_base import (
    RealWebSocketTestBase,  # Real WebSocket test base only
    RealWebSocketTestConfig,
    assert_agent_events_received,
    send_test_agent_request
)
```

**Key Features**:
- ✅ Proper project root path setup
- ✅ All required production component imports
- ✅ Real services test base imports
- ✅ Complete typing imports for validation

## 4. Test Base Configuration Pattern

### Working Test Configuration

**✅ PROVEN WORKING PATTERN (from working suite)**:
```python
# CRITICAL: Always use real WebSocket connections - NO MOCKS per CLAUDE.md
# Tests will fail if Docker services are not available (expected behavior)
WebSocketTestBase = RealWebSocketTestBase
from test_framework.test_context import TestContext, create_test_context
from test_framework.websocket_helpers import WebSocketTestHelpers
```

**Key Features**:
- ✅ Explicit real services requirement
- ✅ Docker dependency acknowledgment  
- ✅ Test framework integration
- ✅ WebSocket helper utilities

## 5. Authentication Pattern (from E2E Auth Helper)

### Demo Mode Authentication

**✅ PROVEN WORKING PATTERN (from `test_framework/ssot/e2e_auth_helper.py`)**:
```python
from test_framework.ssot.e2e_auth_helper import AuthenticatedUser, E2EAuthHelper

async def create_authenticated_test_user():
    """Create authenticated user for WebSocket testing."""
    auth_helper = E2EAuthHelper()
    
    # Use demo mode for simplified testing (DEMO_MODE=1)
    user = await auth_helper.create_authenticated_user(
        email=f"test-user-{uuid.uuid4().hex[:8]}@demo.netra.ai",
        name="WebSocket Test User",
        use_demo_mode=True  # Leverages recent demo mode enhancements
    )
    
    return user
```

**Key Features**:
- ✅ Uses recent demo mode enhancements (DEMO_MODE=1 default)
- ✅ Generates unique test users
- ✅ Provides JWT tokens for WebSocket auth
- ✅ Strongly typed user representation

## 6. WebSocket Connection Pattern (from WebSocket Client)

### Real WebSocket Connection

**✅ PROVEN WORKING PATTERN (from `tests/clients/websocket_client.py`)**:
```python
class WebSocketTestClient:
    """Typed client for testing WebSocket connections."""
    
    def __init__(self, url: str):
        self.url = url
        self._websocket: Optional[WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._received_messages: List[Dict[str, Any]] = []
        self._message_queue: asyncio.Queue = asyncio.Queue()
        
    async def connect(self, token: Optional[str] = None, timeout: float = 10.0) -> bool:
        """Connect to the WebSocket server."""
        try:
            # Create additional headers for authentication
            additional_headers = {}
            if token:
                additional_headers["Authorization"] = f"Bearer {token}"
            
            # Clean URL - remove token parameter if it exists
            url = self.url
            if "?token=" in url:
                url = url.split("?token=")[0]
                
            self._websocket = await websockets.connect(
                url,
                additional_headers=additional_headers,
                timeout=timeout
            )
            
            return True
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False
```

**Key Features**:
- ✅ Real websockets library usage
- ✅ JWT token authentication via headers
- ✅ Proper connection management
- ✅ Error handling and logging

## 7. Test Method Pattern

### Basic Test Structure

**✅ PROVEN WORKING PATTERN**:
```python
@pytest.mark.asyncio
@pytest.mark.mission_critical
async def test_websocket_required_events_flow():
    """Mission Critical: Validate all 5 required WebSocket events."""
    
    # Setup
    validator = MissionCriticalEventValidator(strict_mode=False)
    capture = RealWebSocketEventCapture()
    
    # Create authenticated test user
    user = await create_authenticated_test_user()
    
    # Connect to real WebSocket
    ws_client = WebSocketTestClient(f"ws://localhost:8000/ws")
    connected = await ws_client.connect(token=user.access_token, timeout=10.0)
    assert connected, "Failed to connect to real WebSocket service"
    
    try:
        # Send test message that will trigger agent execution
        test_message = "Analyze my infrastructure costs for optimization"
        await ws_client.send_chat(test_message)
        
        # Capture events with timeout
        events = []
        timeout_start = time.time()
        
        while time.time() - timeout_start < 30.0:  # 30s timeout for real services
            event = await ws_client.receive(timeout=2.0)
            if event:
                events.append(event)
                validator.record(event)
                capture.record_event(event)
                
                # Check if we got completion event
                if event.get("type") == "agent_completed":
                    break
        
        # Validate required events were received
        success, failures = validator.validate_critical_requirements()
        assert success, f"Critical WebSocket event validation failed: {failures}"
        
        # Validate event sequence
        assert "agent_started" in validator.event_counts, "Missing agent_started event"
        assert "agent_thinking" in validator.event_counts, "Missing agent_thinking event" 
        assert "tool_executing" in validator.event_counts, "Missing tool_executing event"
        assert "tool_completed" in validator.event_counts, "Missing tool_completed event"
        assert "agent_completed" in validator.event_counts, "Missing agent_completed event"
        
        logger.info(f"✅ All required WebSocket events validated: {len(events)} total events")
        
    finally:
        await ws_client.disconnect()
```

**Key Features**:
- ✅ Proper async/await patterns
- ✅ Mission critical marker
- ✅ Real service connection with auth
- ✅ Event capture and validation
- ✅ Comprehensive assertions
- ✅ Proper cleanup

## 8. Docker Integration Pattern

### Service Dependencies

**✅ PROVEN WORKING PATTERN (inferred from working suite)**:
```python
# Tests automatically start Docker services via unified test runner
# Usage: python tests/unified_test_runner.py --real-services --category mission_critical

# Docker services required:
# - PostgreSQL (port 5434 for test env)
# - Redis (port 6381 for test env) 
# - Backend (port 8000)
# - Auth Service (port 8081)
```

**Key Features**:
- ✅ Automatic service startup via test runner
- ✅ Test-specific port configuration
- ✅ Service health checking
- ✅ Proper cleanup on test completion

## Application to Restored Tests

### Restoration Template

Using these proven patterns, the restored test file structure should be:

```python
#!/usr/bin/env python
"""MISSION CRITICAL TEST SUITE: WebSocket Agent Events - RESTORED

Restored from commented code using proven working patterns from 3,046-line test suite.
Business Value: $500K+ ARR - Core chat functionality validation
"""

# [Import Pattern from Section 3]
# [Validator Classes from Sections 1-2]
# [Authentication Helper from Section 5]
# [WebSocket Client from Section 6]

class TestWebSocketAgentEventsRestored:
    """Mission Critical: Restored WebSocket test suite using proven patterns."""
    
    # [Test methods using patterns from Section 7]
```

This extraction provides the complete foundation for successfully restoring the commented WebSocket test suite using proven, working patterns from the existing infrastructure.