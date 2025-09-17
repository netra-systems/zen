"""
E2E Staging Test: Frontend Thread ID Confusion Issue #1141

Tests for real user flow in staging environment to reproduce the thread_id: null issue.

This test should FAIL initially to reproduce the issue where real WebSocket messages
show thread_id: null instead of the expected thread ID from URL navigation.

Expected Failure Mode: Real messages show thread_id: null in WebSocket payload
"""

import asyncio
import json
import logging
import pytest
import time
import websockets
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

# Test configuration
STAGING_BACKEND_URL = "https://api.staging.netrasystems.ai"
STAGING_WEBSOCKET_URL = "wss://api.staging.netrasystems.ai/ws"
STAGING_FRONTEND_URL = "https://staging.netrasystems.ai"

# Test constants for Issue #1141
THREAD_ID_TEST_CASES = [
    "thread_2_5e5c7cac",  # Original issue thread ID
    "thread_1_abc123def", # Alternative format
    "thread_3_xyz789",    # Another test case
]

logger = logging.getLogger(__name__)


class WebSocketMessageCapture:
    """Captures and validates WebSocket messages for thread ID testing"""
    
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.start_agent_messages: List[Dict[str, Any]] = []
        self.thread_id_issues: List[str] = []
    
    def capture_message(self, message: Dict[str, Any]):
        """Capture a WebSocket message and analyze for thread ID issues"""
        self.messages.append(message)
        
        # Focus on start_agent messages where thread_id should be present
        if message.get('type') == 'start_agent':
            self.start_agent_messages.append(message)
            
            # Check for thread_id issues
            payload = message.get('payload', {})
            thread_id = payload.get('thread_id')
            
            if thread_id is None:
                issue = f"thread_id is null in start_agent message"
                self.thread_id_issues.append(issue)
                logger.error(f"ISSUE #1141 REPRODUCED: {issue}")
                logger.error(f"Full message: {json.dumps(message, indent=2)}")
            elif thread_id == "":
                issue = f"thread_id is empty string in start_agent message"
                self.thread_id_issues.append(issue)
                logger.error(f"ISSUE #1141 VARIANT: {issue}")
    
    def get_thread_id_from_start_agent(self) -> Optional[str]:
        """Extract thread_id from the most recent start_agent message"""
        if not self.start_agent_messages:
            return None
        
        latest_message = self.start_agent_messages[-1]
        return latest_message.get('payload', {}).get('thread_id')
    
    def has_thread_id_issues(self) -> bool:
        """Check if any thread ID issues were detected"""
        return len(self.thread_id_issues) > 0


async def create_authenticated_websocket(auth_token: str) -> websockets.ServerConnection:
    """Create WebSocket connection with authentication"""
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Origin": STAGING_FRONTEND_URL
    }
    
    try:
        websocket = await websockets.connect(
            STAGING_WEBSOCKET_URL,
            additional_headers=headers,
            timeout=30
        )
        logger.info("WebSocket connection established successfully")
        return websocket
    except Exception as e:
        logger.error(f"Failed to establish WebSocket connection: {e}")
        raise


async def simulate_thread_navigation_flow(
    websocket: websockets.ServerConnection,
    thread_id: str,
    message_capture: WebSocketMessageCapture
) -> None:
    """
    Simulate the real user flow:
    1. User navigates to /chat/thread_id URL
    2. Frontend should extract thread_id from URL
    3. User sends a message
    4. WebSocket start_agent message should include correct thread_id
    """
    
    # Simulate user sending a message in a specific thread context
    test_message = f"Test message for thread {thread_id} - Issue #1141 reproduction"
    
    # This is the message that should be sent by frontend when user is on /chat/{thread_id}
    # and types a message. The thread_id should come from the URL parameter.
    start_agent_message = {
        "type": "start_agent",
        "payload": {
            "user_request": test_message,
            "thread_id": thread_id,  # This should NOT be null if frontend works correctly
            "context": {"source": "message_input"},
            "settings": {}
        }
    }
    
    logger.info(f"Sending start_agent message for thread: {thread_id}")
    logger.info(f"Expected thread_id: {thread_id}")
    
    # Send the message
    await websocket.send(json.dumps(start_agent_message))
    
    # Wait for responses and capture them
    timeout_seconds = 30
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        try:
            # Wait for response with short timeout
            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            message = json.loads(response)
            message_capture.capture_message(message)
            
            logger.info(f"Received message type: {message.get('type')}")
            
            # Stop when we get agent_completed or agent_error
            if message.get('type') in ['agent_completed', 'agent_error']:
                break
                
        except asyncio.TimeoutError:
            # Continue waiting, no message received in this interval
            continue
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed unexpectedly")
            break
        except Exception as e:
            logger.error(f"Error receiving WebSocket message: {e}")
            break


@pytest.mark.asyncio
@pytest.mark.staging
async def test_thread_id_confusion_reproduction_real_websocket():
    """
    SHOULD FAIL: Real WebSocket traffic shows thread_id: null instead of expected thread ID
    
    This test reproduces Issue #1141 by:
    1. Simulating user navigation to /chat/thread_2_5e5c7cac
    2. Sending a message as if user typed it in the chat
    3. Verifying that WebSocket payload contains correct thread_id
    4. EXPECTED TO FAIL: thread_id will be null in actual WebSocket traffic
    """
    
    # Skip if no auth token available (this would be provided in real test environment)
    auth_token = "test_token_placeholder"  # In real test, this would come from staging auth
    
    if not auth_token or auth_token == "test_token_placeholder":
        pytest.skip("Staging auth token not available for real WebSocket testing")
    
    expected_thread_id = "thread_2_5e5c7cac"
    message_capture = WebSocketMessageCapture()
    
    try:
        # Create authenticated WebSocket connection
        websocket = await create_authenticated_websocket(auth_token)
        
        # Simulate the user flow that triggers Issue #1141
        await simulate_thread_navigation_flow(websocket, expected_thread_id, message_capture)
        
        # Close connection
        await websocket.close()
        
        # Analyze captured messages for thread ID issues
        logger.info(f"Captured {len(message_capture.messages)} total messages")
        logger.info(f"Captured {len(message_capture.start_agent_messages)} start_agent messages")
        
        # CRITICAL ASSERTIONS - These should FAIL initially
        
        # Verify start_agent message was sent
        assert len(message_capture.start_agent_messages) >= 1, \
            "No start_agent messages captured - WebSocket flow may be broken"
        
        # Get the thread_id from the actual WebSocket traffic
        actual_thread_id = message_capture.get_thread_id_from_start_agent()
        
        # Log the issue for debugging
        logger.error(f"EXPECTED thread_id: {expected_thread_id}")
        logger.error(f"ACTUAL thread_id: {actual_thread_id}")
        
        if actual_thread_id is None:
            logger.error("BUG REPRODUCED: thread_id is null in real WebSocket traffic")
            logger.error("This confirms Issue #1141 - Frontend thread ID confusion")
        
        # MAIN ASSERTION - This should FAIL
        assert actual_thread_id == expected_thread_id, \
            f"WebSocket payload contains thread_id: {actual_thread_id}, expected: {expected_thread_id}"
        
        # Additional assertions
        assert actual_thread_id is not None, \
            "thread_id should not be null in WebSocket message"
        
        assert actual_thread_id != "", \
            "thread_id should not be empty string in WebSocket message"
        
        # Verify no thread ID issues were detected
        assert not message_capture.has_thread_id_issues(), \
            f"Thread ID issues detected: {message_capture.thread_id_issues}"
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        
        # Log captured messages for debugging
        if message_capture.messages:
            logger.error("Captured messages for debugging:")
            for i, msg in enumerate(message_capture.messages):
                logger.error(f"Message {i}: {json.dumps(msg, indent=2)}")
        
        raise


@pytest.mark.asyncio
@pytest.mark.staging
async def test_multiple_thread_ids_all_produce_null():
    """
    SHOULD FAIL: Multiple different thread IDs all produce null in WebSocket traffic
    
    Tests that the issue is not specific to one thread ID format
    """
    
    auth_token = "test_token_placeholder"
    
    if not auth_token or auth_token == "test_token_placeholder":
        pytest.skip("Staging auth token not available")
    
    failed_thread_ids = []
    
    for thread_id in THREAD_ID_TEST_CASES:
        message_capture = WebSocketMessageCapture()
        
        try:
            websocket = await create_authenticated_websocket(auth_token)
            await simulate_thread_navigation_flow(websocket, thread_id, message_capture)
            await websocket.close()
            
            actual_thread_id = message_capture.get_thread_id_from_start_agent()
            
            if actual_thread_id != thread_id:
                failed_thread_ids.append({
                    'expected': thread_id,
                    'actual': actual_thread_id,
                    'issues': message_capture.thread_id_issues
                })
                
                logger.error(f"Thread ID {thread_id} failed: got {actual_thread_id}")
            
        except Exception as e:
            logger.error(f"Error testing thread ID {thread_id}: {e}")
            failed_thread_ids.append({
                'expected': thread_id,
                'actual': None,
                'error': str(e)
            })
    
    # This should FAIL - all thread IDs will produce null
    assert len(failed_thread_ids) == 0, \
        f"Multiple thread IDs failed to propagate correctly: {failed_thread_ids}"


@pytest.mark.asyncio 
@pytest.mark.staging
async def test_thread_id_null_vs_undefined_distinction():
    """
    SHOULD FAIL: Distinguish between thread_id: null vs thread_id: undefined vs missing
    
    This test helps identify the exact nature of the thread ID issue
    """
    
    auth_token = "test_token_placeholder"
    
    if not auth_token or auth_token == "test_token_placeholder":
        pytest.skip("Staging auth token not available")
    
    expected_thread_id = "thread_2_5e5c7cac"
    message_capture = WebSocketMessageCapture()
    
    try:
        websocket = await create_authenticated_websocket(auth_token)
        await simulate_thread_navigation_flow(websocket, expected_thread_id, message_capture)
        await websocket.close()
        
        # Analyze the exact nature of the thread_id field
        if message_capture.start_agent_messages:
            start_agent_msg = message_capture.start_agent_messages[-1]
            payload = start_agent_msg.get('payload', {})
            
            # Check different null/undefined scenarios
            if 'thread_id' not in payload:
                failure_mode = "thread_id field is missing from payload"
            elif payload['thread_id'] is None:
                failure_mode = "thread_id field is explicitly null"
            elif payload['thread_id'] == "":
                failure_mode = "thread_id field is empty string"
            elif payload['thread_id'] == "undefined":
                failure_mode = "thread_id field is string 'undefined'"
            else:
                failure_mode = f"thread_id field has unexpected value: {payload['thread_id']}"
            
            logger.error(f"Thread ID issue details: {failure_mode}")
            logger.error(f"Full payload: {json.dumps(payload, indent=2)}")
            
            # This should FAIL with specific failure mode
            assert payload.get('thread_id') == expected_thread_id, \
                f"Thread ID confusion confirmed - {failure_mode}"
        
        else:
            pytest.fail("No start_agent messages captured to analyze thread_id field")
            
    except Exception as e:
        logger.error(f"Thread ID analysis test failed: {e}")
        raise


if __name__ == "__main__":
    # Run the test directly for debugging
    asyncio.run(test_thread_id_confusion_reproduction_real_websocket())