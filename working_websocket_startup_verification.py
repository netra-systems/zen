"""
Test to reproduce WebSocket startup verification failure.
This test verifies the root cause identified in the Five Whys analysis.
"""
import pytest
import os
import time
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.smd import StartupOrchestrator
from fastapi import FastAPI


@pytest.mark.asyncio
async def test_websocket_startup_without_testing_flag():
    """
    Verify WebSocket manager rejects messages without TESTING=1 during startup.
    This reproduces the critical failure where startup fails because:
    1. No WebSocket connections exist at startup time
    2. TESTING flag is not set to "1"  
    3. Manager enters production path and returns False
    4. Startup verification fails with DeterministicStartupError
    """
    # Ensure TESTING is explicitly NOT set (simulating production/staging)
    original_testing = os.environ.pop("TESTING", None)
    original_env = os.environ.get("ENVIRONMENT", None)
    
    # Set environment to development (not testing)
    os.environ["ENVIRONMENT"] = "development"
    
    try:
        manager = WebSocketManager()
        
        # Create test message similar to startup verification
        test_thread = f"startup_test_{uuid.uuid4()}"
        test_message = {
            "type": "startup_test",
            "timestamp": time.time(),
            "validation": "critical_path"
        }
        
        # This should fail when TESTING != "1" and no connections exist
        # The manager will return False, causing startup to fail
        success = await manager.send_to_thread(test_thread, test_message)
        
        # In production/staging without connections, this returns False
        assert success is False, (
            "WebSocket manager should reject messages without TESTING=1 "
            "when no connections exist (root cause of startup failure)"
        )
        
    finally:
        # Restore original environment
        if original_testing:
            os.environ["TESTING"] = original_testing
        else:
            os.environ.pop("TESTING", None)
            
        if original_env:
            os.environ["ENVIRONMENT"] = original_env
        else:
            os.environ.pop("ENVIRONMENT", None)


@pytest.mark.asyncio
async def test_websocket_startup_with_testing_flag():
    """
    Verify WebSocket manager accepts messages WITH TESTING=1 during startup.
    This shows the working path where tests pass but production fails.
    """
    # Set TESTING=1 (simulating test environment)
    original_testing = os.environ.get("TESTING", None)
    os.environ["TESTING"] = "1"
    
    try:
        manager = WebSocketManager()
        
        # Create test message similar to startup verification
        test_thread = f"startup_test_{uuid.uuid4()}"
        test_message = {
            "type": "startup_test",
            "timestamp": time.time(),
            "validation": "critical_path"
        }
        
        # This should succeed when TESTING="1" even without connections
        success = await manager.send_to_thread(test_thread, test_message)
        
        # With TESTING=1, the manager accepts messages even without connections
        assert success is True, (
            "WebSocket manager should accept messages with TESTING=1 "
            "even when no connections exist (why tests pass)"
        )
        
    finally:
        # Restore original environment
        if original_testing:
            os.environ["TESTING"] = original_testing
        else:
            os.environ.pop("TESTING", None)


@pytest.mark.asyncio 
async def test_startup_verification_phase_fails_without_testing():
    """
    Test the actual startup verification phase that fails in production.
    This simulates the exact conditions that cause the startup failure.
    """
    # Setup environment without TESTING flag
    original_testing = os.environ.pop("TESTING", None)
    original_env = os.environ.get("ENVIRONMENT", None)
    os.environ["ENVIRONMENT"] = "development"
    
    try:
        # Create minimal FastAPI app for startup orchestrator
        app = FastAPI()
        app.state.agent_websocket_bridge = MagicMock()
        app.state.tool_dispatcher = MagicMock()
        app.state.tool_dispatcher.has_websocket_support = True
        
        orchestrator = StartupOrchestrator(app)
        
        # Try to verify WebSocket events (this is where it fails)
        with pytest.raises(Exception) as exc_info:
            await orchestrator._verify_websocket_events()
        
        # Should raise DeterministicStartupError
        assert "WebSocket test event failed to send" in str(exc_info.value) or \
               "manager rejected message" in str(exc_info.value), \
               "Should fail with WebSocket manager rejection error"
        
    finally:
        # Restore original environment
        if original_testing:
            os.environ["TESTING"] = original_testing
        else:
            os.environ.pop("TESTING", None)
            
        if original_env:
            os.environ["ENVIRONMENT"] = original_env
        else:
            os.environ.pop("ENVIRONMENT", None)


@pytest.mark.asyncio
async def test_production_environment_handling():
    """
    Test that production/staging environments handle startup verification correctly.
    The fix should allow startup to succeed even without connections in these environments.
    """
    # Test production environment
    original_testing = os.environ.pop("TESTING", None)
    original_env = os.environ.get("ENVIRONMENT", None)
    os.environ["ENVIRONMENT"] = "production"
    
    try:
        manager = WebSocketManager()
        
        # Create test message
        test_thread = f"startup_test_{uuid.uuid4()}"
        test_message = {
            "type": "startup_test",
            "timestamp": time.time(),
            "validation": "critical_path"
        }
        
        # In production without connections, current code returns False
        # The fix should make this acceptable for startup verification
        success = await manager.send_to_thread(test_thread, test_message)
        
        # Document current behavior (returns False)
        assert success is False, "Production currently rejects without connections"
        
    finally:
        # Restore original environment
        if original_testing:
            os.environ["TESTING"] = original_testing
        else:
            os.environ.pop("TESTING", None)
            
        if original_env:
            os.environ["ENVIRONMENT"] = original_env
        else:
            os.environ.pop("ENVIRONMENT", None)


@pytest.mark.asyncio
async def test_proposed_fix_with_startup_verification_flag():
    """
    Test the proposed fix: adding a startup_verification parameter.
    This shows how the fix would allow startup to succeed.
    """
    # This test documents the proposed solution
    # The actual implementation would modify WebSocketManager.send_to_thread
    # to accept a startup_verification parameter
    
    # Simulate the proposed fix behavior
    async def send_to_thread_with_fix(self, thread_id, message, startup_verification=False):
        """Modified send_to_thread with startup_verification parameter."""
        # If startup_verification is True, accept the message regardless
        if startup_verification:
            return True
        
        # Otherwise, use normal logic (which would fail without connections)
        # For testing, simulate the failure case
        return False
    
    # Test that the fix would work
    manager = WebSocketManager()
    
    # Patch the method to simulate the fix
    with patch.object(manager, 'send_to_thread', send_to_thread_with_fix.__get__(manager, WebSocketManager)):
        test_thread = f"startup_test_{uuid.uuid4()}"
        test_message = {
            "type": "startup_test",
            "timestamp": time.time()
        }
        
        # Without startup_verification flag, it fails
        success = await manager.send_to_thread(test_thread, test_message)
        assert success is False, "Should fail without startup_verification flag"
        
        # With startup_verification flag, it succeeds
        success = await manager.send_to_thread(test_thread, test_message, startup_verification=True)
        assert success is True, "Should succeed with startup_verification flag"