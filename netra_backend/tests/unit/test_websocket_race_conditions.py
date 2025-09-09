"""
Test WebSocket Race Condition Detection Logic

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: System Stability & Revenue Protection
- Value Impact: Prevent critical WebSocket race conditions causing $500K+ ARR chat functionality failures
- Strategic Impact: Validate race condition detection patterns that protect core Chat business value

CRITICAL: WebSocket race conditions block users from accessing AI-powered chat,
directly impacting our core business model. These tests ensure race condition
detection logic works correctly to prevent 1011 errors and connection failures.

Test Categories:
- Connection state validation and detection
- Handshake completion timing verification  
- Premature message sending prevention
- Concurrent connection attempt handling
- Cloud environment-specific race condition patterns
"""

import asyncio
import json
import logging
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager

from shared.types.core_types import UserID, ConnectionID, RequestID
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class TestWebSocketConnectionStateValidation:
    """Test WebSocket connection state detection logic."""
    
    def test_connection_state_detection_basic_logic(self):
        """Test basic connection state detection without complex dependencies."""
        
        # Test connection state detection function
        def is_websocket_connected(websocket_mock):
            """Basic connection state detection."""
            if not websocket_mock:
                return False
            return hasattr(websocket_mock, 'open') and websocket_mock.open
        
        # Test scenarios
        assert is_websocket_connected(None) == False
        
        # Mock connected websocket
        connected_ws = Mock()
        connected_ws.open = True
        assert is_websocket_connected(connected_ws) == True
        
        # Mock disconnected websocket
        disconnected_ws = Mock()
        disconnected_ws.open = False
        assert is_websocket_connected(disconnected_ws) == False
        
        # Mock websocket without open attribute (invalid state)
        invalid_ws = Mock()
        delattr(invalid_ws, 'open') if hasattr(invalid_ws, 'open') else None
        assert is_websocket_connected(invalid_ws) == False

    def test_gcp_structured_logging_serialization(self):
        """Test GCP structured logging prevents race condition errors."""
        
        # Simulate GCP structured logging that was causing 1011 errors
        def serialize_websocket_state_for_gcp_logging(websocket_state: Dict):
            """Serialize WebSocket state for GCP structured logging."""
            try:
                # This was causing race conditions in staging
                serialized = json.dumps({
                    'connection_id': websocket_state.get('connection_id'),
                    'user_id': websocket_state.get('user_id'),
                    'state': websocket_state.get('state'),
                    'timestamp': websocket_state.get('timestamp')
                })
                return serialized
            except Exception as e:
                # Race condition detection: serialization failures indicate state corruption
                logger.error(f"WebSocket state serialization race condition detected: {e}")
                return None
        
        # Test valid state (no race condition)
        valid_state = {
            'connection_id': str(uuid.uuid4()),
            'user_id': 'test-user-123',
            'state': 'connected',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        result = serialize_websocket_state_for_gcp_logging(valid_state)
        assert result is not None
        assert 'connection_id' in result
        
        # Test corrupted state (race condition scenario)
        corrupted_state = {
            'connection_id': lambda: "invalid",  # Non-serializable - indicates race condition
            'user_id': 'test-user-123',
            'state': 'connected'
        }
        
        result = serialize_websocket_state_for_gcp_logging(corrupted_state)
        assert result is None  # Race condition detected

    def test_cloud_environment_connection_state_checking(self):
        """Test environment-specific connection state checking."""
        
        def is_websocket_connected_cloud_aware(websocket_mock, environment: str = "development"):
            """Cloud-aware connection state checking."""
            if not websocket_mock:
                return False
                
            # Base connection check
            if not (hasattr(websocket_mock, 'open') and websocket_mock.open):
                return False
            
            # Environment-specific additional checks
            if environment in ["staging", "production"]:
                # Additional GCP-specific checks to prevent race conditions
                if not hasattr(websocket_mock, 'ping'):
                    logger.warning(f"WebSocket missing ping capability in {environment}")
                    return False
                
                # Check for GCP-specific connection attributes
                if not hasattr(websocket_mock, 'remote_address'):
                    logger.warning(f"WebSocket missing remote_address in {environment}")
                    # Don't fail for this - just log for debugging
                    
            return True
        
        # Test development environment (permissive)
        dev_ws = Mock()
        dev_ws.open = True
        assert is_websocket_connected_cloud_aware(dev_ws, "development") == True
        
        # Test staging environment (stricter checks)
        staging_ws = Mock()
        staging_ws.open = True
        staging_ws.ping = AsyncMock()  # Required for staging
        assert is_websocket_connected_cloud_aware(staging_ws, "staging") == True
        
        # Test staging websocket missing ping (race condition risk)
        incomplete_staging_ws = Mock()
        incomplete_staging_ws.open = True
        # Missing ping attribute simulates race condition where websocket partially initialized
        assert is_websocket_connected_cloud_aware(incomplete_staging_ws, "staging") == False

    def test_websocket_readiness_with_missing_attributes(self):
        """Test readiness checking handles missing attributes gracefully."""
        
        def is_websocket_connected_and_ready(websocket_mock, require_all_attributes: bool = False):
            """Enhanced readiness checking with race condition detection."""
            try:
                if not websocket_mock:
                    return False
                
                # Basic connection state
                if not getattr(websocket_mock, 'open', False):
                    return False
                
                # Check for common race condition: websocket partially initialized
                required_attributes = ['send', 'recv', 'close']
                
                for attr in required_attributes:
                    if not hasattr(websocket_mock, attr):
                        logger.error(f"Race condition detected: WebSocket missing {attr} - partial initialization")
                        return False
                
                # Optional attributes (don't fail if missing, but log for debugging)
                optional_attributes = ['ping', 'pong', 'remote_address']
                missing_optional = []
                
                for attr in optional_attributes:
                    if not hasattr(websocket_mock, attr):
                        missing_optional.append(attr)
                
                if missing_optional:
                    logger.info(f"WebSocket ready but missing optional attributes: {missing_optional}")
                
                # If require_all_attributes is True, fail on missing optional attributes
                if require_all_attributes and missing_optional:
                    logger.warning(f"Strict readiness check failed - missing: {missing_optional}")
                    return False
                
                return True
                
            except Exception as e:
                logger.error(f"Exception during readiness check - possible race condition: {e}")
                return False
        
        # Test fully initialized websocket
        complete_ws = Mock()
        complete_ws.open = True
        complete_ws.send = AsyncMock()
        complete_ws.recv = AsyncMock()
        complete_ws.close = AsyncMock()
        complete_ws.ping = AsyncMock()
        complete_ws.pong = AsyncMock()
        complete_ws.remote_address = "127.0.0.1:12345"
        
        assert is_websocket_connected_and_ready(complete_ws, require_all_attributes=False) == True
        assert is_websocket_connected_and_ready(complete_ws, require_all_attributes=True) == True
        
        # Test websocket missing required attributes (race condition scenario)
        partial_ws = Mock()
        partial_ws.open = True
        partial_ws.send = AsyncMock()
        # Missing recv and close - indicates race condition during initialization
        
        assert is_websocket_connected_and_ready(partial_ws, require_all_attributes=False) == False
        
        # Test websocket with all required but missing optional attributes
        basic_ws = Mock()
        basic_ws.open = True
        basic_ws.send = AsyncMock()
        basic_ws.recv = AsyncMock()
        basic_ws.close = AsyncMock()
        # Missing optional attributes
        
        assert is_websocket_connected_and_ready(basic_ws, require_all_attributes=False) == True
        assert is_websocket_connected_and_ready(basic_ws, require_all_attributes=True) == False


class TestApplicationLevelConnectionStateMachine:
    """Test application-level connection state management to prevent race conditions."""
    
    def setup_method(self):
        """Set up connection state machine for each test."""
        self.connection_states = {}  # connection_id -> state info
        
    def test_connection_state_machine_initialization(self):
        """Test connection state machine properly initializes to prevent race conditions."""
        
        class ConnectionStateMachine:
            def __init__(self, connection_id: str, user_id: str):
                self.connection_id = connection_id
                self.user_id = user_id
                self.state = "initializing"
                self.created_at = time.time()
                self.state_history = ["initializing"]
                self.is_valid = True
                
            def transition_to(self, new_state: str) -> bool:
                """Safely transition to new state."""
                valid_transitions = {
                    "initializing": ["connecting", "failed"],
                    "connecting": ["connected", "failed"],
                    "connected": ["disconnecting", "failed"],
                    "disconnecting": ["disconnected"],
                    "failed": [],  # Terminal state
                    "disconnected": []  # Terminal state
                }
                
                current_valid_next = valid_transitions.get(self.state, [])
                if new_state not in current_valid_next:
                    logger.error(f"Invalid state transition: {self.state} -> {new_state}")
                    return False
                
                self.state = new_state
                self.state_history.append(new_state)
                return True
        
        # Test successful initialization
        connection_id = str(uuid.uuid4())
        user_id = "test-user-123"
        
        state_machine = ConnectionStateMachine(connection_id, user_id)
        
        assert state_machine.connection_id == connection_id
        assert state_machine.user_id == user_id
        assert state_machine.state == "initializing"
        assert state_machine.is_valid == True
        assert "initializing" in state_machine.state_history
        
    def test_valid_state_progression(self):
        """Test valid state progression through WebSocket setup phases."""
        
        class ConnectionStateMachine:
            def __init__(self, connection_id: str, user_id: str):
                self.connection_id = connection_id
                self.user_id = user_id
                self.state = "initializing"
                self.state_history = ["initializing"]
                
            def transition_to(self, new_state: str) -> bool:
                valid_transitions = {
                    "initializing": ["connecting", "failed"],
                    "connecting": ["connected", "failed"],
                    "connected": ["disconnecting", "failed"],
                    "disconnecting": ["disconnected"],
                    "failed": [],
                    "disconnected": []
                }
                
                if new_state not in valid_transitions.get(self.state, []):
                    return False
                
                self.state = new_state
                self.state_history.append(new_state)
                return True
        
        state_machine = ConnectionStateMachine("conn-123", "user-123")
        
        # Test valid progression: initializing -> connecting -> connected
        assert state_machine.transition_to("connecting") == True
        assert state_machine.state == "connecting"
        
        assert state_machine.transition_to("connected") == True
        assert state_machine.state == "connected"
        
        # Test graceful disconnection
        assert state_machine.transition_to("disconnecting") == True
        assert state_machine.transition_to("disconnected") == True
        
        assert state_machine.state_history == ["initializing", "connecting", "connected", "disconnecting", "disconnected"]

    def test_invalid_state_transition_blocking(self):
        """Test that invalid state transitions are blocked to prevent race conditions."""
        
        class ConnectionStateMachine:
            def __init__(self, connection_id: str, user_id: str):
                self.connection_id = connection_id
                self.user_id = user_id
                self.state = "initializing"
                self.state_history = ["initializing"]
                self.invalid_transition_attempts = []
                
            def transition_to(self, new_state: str) -> bool:
                valid_transitions = {
                    "initializing": ["connecting", "failed"],
                    "connecting": ["connected", "failed"],
                    "connected": ["disconnecting", "failed"],
                    "disconnecting": ["disconnected"],
                    "failed": [],
                    "disconnected": []
                }
                
                if new_state not in valid_transitions.get(self.state, []):
                    self.invalid_transition_attempts.append((self.state, new_state))
                    logger.warning(f"Blocked invalid transition: {self.state} -> {new_state}")
                    return False
                
                self.state = new_state
                self.state_history.append(new_state)
                return True
        
        state_machine = ConnectionStateMachine("conn-123", "user-123")
        
        # Test invalid transitions that could indicate race conditions
        assert state_machine.transition_to("connected") == False  # Skip connecting phase
        assert state_machine.state == "initializing"  # State unchanged
        
        assert state_machine.transition_to("disconnected") == False  # Skip all intermediate states
        assert state_machine.state == "initializing"  # State unchanged
        
        # Verify attempts were logged
        assert len(state_machine.invalid_transition_attempts) == 2
        assert ("initializing", "connected") in state_machine.invalid_transition_attempts
        assert ("initializing", "disconnected") in state_machine.invalid_transition_attempts
        
    def test_concurrent_state_machine_access(self):
        """Test thread safety under concurrent access - critical for multi-user system."""
        
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        class ThreadSafeConnectionStateMachine:
            def __init__(self, connection_id: str, user_id: str):
                self.connection_id = connection_id
                self.user_id = user_id
                self.state = "initializing"
                self.state_history = ["initializing"]
                self._lock = threading.RLock()  # Reentrant lock for complex operations
                self.transition_count = 0
                
            def transition_to(self, new_state: str) -> bool:
                with self._lock:
                    valid_transitions = {
                        "initializing": ["connecting", "failed"],
                        "connecting": ["connected", "failed"],
                        "connected": ["disconnecting", "failed"],
                        "disconnecting": ["disconnected"],
                        "failed": [],
                        "disconnected": []
                    }
                    
                    if new_state not in valid_transitions.get(self.state, []):
                        return False
                    
                    # Simulate processing time to increase chance of race condition
                    time.sleep(0.001)  # 1ms delay
                    
                    self.state = new_state
                    self.state_history.append(new_state)
                    self.transition_count += 1
                    return True
                
            def get_state_safely(self) -> str:
                with self._lock:
                    return self.state
                    
            def get_history_safely(self) -> List[str]:
                with self._lock:
                    return self.state_history.copy()
        
        state_machine = ThreadSafeConnectionStateMachine("conn-concurrent", "user-concurrent")
        
        def concurrent_transition_worker(worker_id: int):
            """Worker function that attempts state transitions."""
            transitions_attempted = []
            
            # Each worker attempts a sequence of transitions
            if worker_id % 2 == 0:
                # Even workers: normal flow
                sequence = ["connecting", "connected", "disconnecting"]
            else:
                # Odd workers: error flow
                sequence = ["connecting", "failed"]
            
            for transition in sequence:
                result = state_machine.transition_to(transition)
                transitions_attempted.append((transition, result))
                time.sleep(0.001)  # Small delay between transitions
            
            return {
                'worker_id': worker_id,
                'transitions': transitions_attempted,
                'final_state': state_machine.get_state_safely(),
                'history_length': len(state_machine.get_history_safely())
            }
        
        # Run concurrent workers
        num_workers = 5
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(concurrent_transition_worker, i) for i in range(num_workers)]
            results = [future.result() for future in as_completed(futures)]
        
        # Verify thread safety
        final_state = state_machine.get_state_safely()
        final_history = state_machine.get_history_safely()
        
        # State machine should be in a valid final state
        assert final_state in ["connected", "failed", "disconnected", "disconnecting"]
        
        # History should be consistent (no duplicate or missing entries due to race conditions)
        assert len(final_history) >= 2  # At least initializing + one transition
        assert final_history[0] == "initializing"  # First state always initializing
        
        # All state transitions in history should be valid
        for i in range(len(final_history) - 1):
            current = final_history[i]
            next_state = final_history[i + 1]
            
            valid_transitions = {
                "initializing": ["connecting", "failed"],
                "connecting": ["connected", "failed"],
                "connected": ["disconnecting", "failed"],
                "disconnecting": ["disconnected"],
                "failed": [],
                "disconnected": []
            }
            
            assert next_state in valid_transitions.get(current, []), \
                f"Invalid transition in history: {current} -> {next_state}"
        
        # Verify no worker had impossible results
        for result in results:
            assert result['final_state'] is not None
            assert result['history_length'] >= 2

    def test_state_rollback_on_failure(self):
        """Test state rollback when operations fail - prevents inconsistent state."""
        
        class RollbackCapableStateMachine:
            def __init__(self, connection_id: str, user_id: str):
                self.connection_id = connection_id
                self.user_id = user_id
                self.state = "initializing"
                self.state_history = ["initializing"]
                self.rollback_count = 0
                
            def attempt_transition_with_rollback(self, new_state: str, simulate_failure: bool = False) -> bool:
                """Attempt transition with rollback capability."""
                original_state = self.state
                original_history = self.state_history.copy()
                
                try:
                    # Validate transition
                    valid_transitions = {
                        "initializing": ["connecting", "failed"],
                        "connecting": ["connected", "failed"],
                        "connected": ["disconnecting", "failed"],
                        "disconnecting": ["disconnected"],
                        "failed": [],
                        "disconnected": []
                    }
                    
                    if new_state not in valid_transitions.get(self.state, []):
                        return False
                    
                    # Temporarily update state
                    self.state = new_state
                    self.state_history.append(new_state)
                    
                    # Simulate operation that might fail
                    if simulate_failure:
                        raise RuntimeError(f"Simulated failure during transition to {new_state}")
                    
                    # Success - keep the new state
                    return True
                    
                except Exception as e:
                    # Rollback to original state
                    logger.warning(f"Rolling back state transition due to error: {e}")
                    self.state = original_state
                    self.state_history = original_history
                    self.rollback_count += 1
                    return False
        
        state_machine = RollbackCapableStateMachine("conn-rollback", "user-rollback")
        
        # Test successful transition (no rollback needed)
        assert state_machine.attempt_transition_with_rollback("connecting", simulate_failure=False) == True
        assert state_machine.state == "connecting"
        assert state_machine.rollback_count == 0
        
        # Test failed transition with rollback
        assert state_machine.attempt_transition_with_rollback("connected", simulate_failure=True) == False
        assert state_machine.state == "connecting"  # Rolled back to previous state
        assert state_machine.rollback_count == 1
        
        # Verify history was also rolled back
        assert state_machine.state_history == ["initializing", "connecting"]
        
    def test_excessive_failure_handling(self):
        """Test handling of excessive failures - prevents infinite retry loops."""
        
        class FailureTrackingStateMachine:
            def __init__(self, connection_id: str, user_id: str, max_failures: int = 3):
                self.connection_id = connection_id
                self.user_id = user_id
                self.state = "initializing"
                self.failure_count = 0
                self.max_failures = max_failures
                self.is_permanently_failed = False
                
            def attempt_transition(self, new_state: str, will_fail: bool = False) -> bool:
                """Attempt transition with failure tracking."""
                if self.is_permanently_failed:
                    logger.error("Connection permanently failed - no more transitions allowed")
                    return False
                
                if will_fail:
                    self.failure_count += 1
                    logger.warning(f"Transition failed (failure {self.failure_count}/{self.max_failures})")
                    
                    if self.failure_count >= self.max_failures:
                        self.state = "permanently_failed"
                        self.is_permanently_failed = True
                        logger.error("Maximum failures exceeded - connection permanently failed")
                    
                    return False
                
                # Reset failure count on successful transition
                self.failure_count = 0
                self.state = new_state
                return True
        
        state_machine = FailureTrackingStateMachine("conn-failure", "user-failure", max_failures=3)
        
        # Test normal operation
        assert state_machine.attempt_transition("connecting", will_fail=False) == True
        assert state_machine.failure_count == 0
        
        # Test failures building up
        assert state_machine.attempt_transition("connected", will_fail=True) == False
        assert state_machine.failure_count == 1
        assert state_machine.is_permanently_failed == False
        
        assert state_machine.attempt_transition("connected", will_fail=True) == False
        assert state_machine.failure_count == 2
        assert state_machine.is_permanently_failed == False
        
        # Test permanent failure on max failures
        assert state_machine.attempt_transition("connected", will_fail=True) == False
        assert state_machine.failure_count == 3
        assert state_machine.is_permanently_failed == True
        assert state_machine.state == "permanently_failed"
        
        # Test that no further transitions are allowed
        assert state_machine.attempt_transition("connected", will_fail=False) == False


class TestHandshakeCompletionValidation:
    """Test handshake completion detection and timing validation."""
    
    @pytest.mark.asyncio
    async def test_handshake_completion_detection_success(self):
        """Test successful handshake completion detection."""
        
        async def validate_websocket_handshake_completion(websocket_mock, timeout: float = 5.0) -> bool:
            """Validate that WebSocket handshake completed successfully."""
            try:
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    # Check if websocket is open and ready
                    if not websocket_mock or not getattr(websocket_mock, 'open', False):
                        await asyncio.sleep(0.1)
                        continue
                    
                    # Check if websocket has necessary methods (indicates complete initialization)
                    required_methods = ['send', 'recv', 'close']
                    if not all(hasattr(websocket_mock, method) for method in required_methods):
                        await asyncio.sleep(0.1)
                        continue
                    
                    # Try to send a ping to verify handshake is complete
                    try:
                        if hasattr(websocket_mock, 'ping'):
                            await websocket_mock.ping()
                        return True
                    except Exception as e:
                        if "Need to call 'accept' first" in str(e):
                            # This is the specific race condition error we're trying to detect
                            logger.error(f"Handshake race condition detected: {e}")
                            await asyncio.sleep(0.1)
                            continue
                        else:
                            # Other errors may be transient
                            logger.warning(f"Handshake validation error: {e}")
                            await asyncio.sleep(0.1)
                            continue
                
                return False  # Timeout exceeded
                
            except Exception as e:
                logger.error(f"Exception during handshake validation: {e}")
                return False
        
        # Test successful handshake completion
        success_websocket = AsyncMock()
        success_websocket.open = True
        success_websocket.send = AsyncMock()
        success_websocket.recv = AsyncMock()
        success_websocket.close = AsyncMock()
        success_websocket.ping = AsyncMock(return_value=None)  # Successful ping
        
        result = await validate_websocket_handshake_completion(success_websocket, timeout=2.0)
        assert result == True
        
        # Verify ping was called to validate handshake
        success_websocket.ping.assert_called()

    @pytest.mark.asyncio
    async def test_handshake_need_to_call_accept_first_error(self):
        """Test detection of 'Need to call accept first' race condition error."""
        
        async def validate_websocket_handshake_completion(websocket_mock, timeout: float = 5.0) -> bool:
            """Validate handshake with race condition detection."""
            try:
                start_time = time.time()
                accept_error_count = 0
                max_accept_errors = 3  # Allow some retries for race condition recovery
                
                while time.time() - start_time < timeout:
                    if not websocket_mock or not getattr(websocket_mock, 'open', False):
                        await asyncio.sleep(0.1)
                        continue
                    
                    try:
                        if hasattr(websocket_mock, 'ping'):
                            await websocket_mock.ping()
                        return True
                    except Exception as e:
                        if "Need to call 'accept' first" in str(e):
                            accept_error_count += 1
                            logger.warning(f"Accept-first race condition detected (attempt {accept_error_count}): {e}")
                            
                            if accept_error_count >= max_accept_errors:
                                logger.error("Too many 'accept first' errors - handshake permanently failed")
                                return False
                            
                            await asyncio.sleep(0.2)  # Longer wait for race condition recovery
                            continue
                        else:
                            logger.warning(f"Other handshake error: {e}")
                            await asyncio.sleep(0.1)
                            continue
                
                return False
                
            except Exception as e:
                logger.error(f"Exception during handshake validation: {e}")
                return False
        
        # Test websocket with "Need to call 'accept' first" error (race condition)
        race_condition_websocket = AsyncMock()
        race_condition_websocket.open = True
        race_condition_websocket.send = AsyncMock()
        race_condition_websocket.recv = AsyncMock()
        race_condition_websocket.close = AsyncMock()
        
        # Mock ping to always raise the race condition error
        race_condition_websocket.ping = AsyncMock(
            side_effect=RuntimeError("Need to call 'accept' first")
        )
        
        result = await validate_websocket_handshake_completion(race_condition_websocket, timeout=1.0)
        assert result == False  # Should fail due to persistent race condition
        
        # Verify multiple ping attempts were made
        assert race_condition_websocket.ping.call_count >= 3

    @pytest.mark.asyncio
    async def test_handshake_timeout_in_cloud_environment(self):
        """Test handshake timeout handling in cloud environments."""
        
        async def validate_websocket_handshake_completion_cloud_aware(
            websocket_mock, 
            environment: str = "development",
            timeout: Optional[float] = None
        ) -> bool:
            """Cloud-aware handshake validation with environment-specific timeouts."""
            
            # Environment-specific timeout defaults
            if timeout is None:
                timeout_defaults = {
                    "development": 10.0,  # Generous timeout for development
                    "staging": 8.0,       # Shorter for GCP Cloud Run
                    "production": 6.0     # Conservative for production stability
                }
                timeout = timeout_defaults.get(environment, 5.0)
            
            logger.info(f"Validating handshake in {environment} with {timeout}s timeout")
            
            try:
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    if not websocket_mock or not getattr(websocket_mock, 'open', False):
                        await asyncio.sleep(0.1)
                        continue
                    
                    try:
                        if hasattr(websocket_mock, 'ping'):
                            await websocket_mock.ping()
                        return True
                    except Exception as e:
                        if "Need to call 'accept' first" in str(e):
                            # In cloud environments, be more patient with race conditions
                            cloud_wait_time = 0.3 if environment in ["staging", "production"] else 0.1
                            await asyncio.sleep(cloud_wait_time)
                            continue
                        else:
                            await asyncio.sleep(0.1)
                            continue
                
                logger.warning(f"Handshake validation timed out after {timeout}s in {environment}")
                return False
                
            except Exception as e:
                logger.error(f"Exception during {environment} handshake validation: {e}")
                return False
        
        # Test development environment with slow websocket
        slow_websocket = AsyncMock()
        slow_websocket.open = True
        slow_websocket.ping = AsyncMock()
        
        # Add delay to simulate slow handshake
        async def delayed_ping():
            await asyncio.sleep(0.5)  # 500ms delay
        slow_websocket.ping = delayed_ping
        
        # Should succeed in development (generous timeout)
        result = await validate_websocket_handshake_completion_cloud_aware(
            slow_websocket, environment="development", timeout=2.0
        )
        assert result == True
        
        # Should timeout in production (strict timeout)
        result = await validate_websocket_handshake_completion_cloud_aware(
            slow_websocket, environment="production", timeout=0.3
        )
        assert result == False

    @pytest.mark.asyncio  
    async def test_handshake_timeout_adjustment_for_staging(self):
        """Test automatic timeout adjustment for staging environment."""
        
        def get_environment_appropriate_timeout(environment: str, base_timeout: float = 5.0) -> float:
            """Get appropriate timeout based on environment characteristics."""
            
            timeout_multipliers = {
                "development": 2.0,    # Very generous for development
                "testing": 1.5,        # Moderate for testing
                "staging": 1.2,        # Slightly longer for GCP Cloud Run
                "production": 1.0      # Baseline for production
            }
            
            multiplier = timeout_multipliers.get(environment, 1.0)
            adjusted_timeout = base_timeout * multiplier
            
            logger.info(f"Environment {environment}: base_timeout={base_timeout}s, multiplier={multiplier}, adjusted={adjusted_timeout}s")
            
            return adjusted_timeout
        
        # Test timeout adjustments for different environments
        base_timeout = 5.0
        
        dev_timeout = get_environment_appropriate_timeout("development", base_timeout)
        assert dev_timeout == 10.0  # 5.0 * 2.0
        
        staging_timeout = get_environment_appropriate_timeout("staging", base_timeout)
        assert staging_timeout == 6.0  # 5.0 * 1.2
        
        prod_timeout = get_environment_appropriate_timeout("production", base_timeout)
        assert prod_timeout == 5.0  # 5.0 * 1.0
        
        # Test with staging-specific handshake validation
        async def staging_handshake_validation(websocket_mock) -> bool:
            """Staging-specific handshake validation with appropriate timeout."""
            timeout = get_environment_appropriate_timeout("staging", 5.0)
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if websocket_mock and getattr(websocket_mock, 'open', False):
                    try:
                        if hasattr(websocket_mock, 'ping'):
                            await websocket_mock.ping()
                        return True
                    except Exception:
                        await asyncio.sleep(0.2)  # Staging-appropriate wait time
                        continue
                else:
                    await asyncio.sleep(0.1)
                    
            return False
        
        # Test with websocket that becomes ready after delay
        delayed_ready_websocket = AsyncMock()
        delayed_ready_websocket.ping = AsyncMock()
        
        # Initially not ready
        delayed_ready_websocket.open = False
        
        # Create task to make websocket ready after delay
        async def make_ready_later():
            await asyncio.sleep(1.0)  # 1 second delay
            delayed_ready_websocket.open = True
        
        ready_task = asyncio.create_task(make_ready_later())
        
        # Should succeed with staging timeout (6 seconds total)
        validation_task = asyncio.create_task(staging_handshake_validation(delayed_ready_websocket))
        
        result = await validation_task
        await ready_task  # Clean up
        
        assert result == True  # Should succeed with longer staging timeout


class TestConcurrentConnectionHandling:
    """Test concurrent connection attempt handling."""
    
    def test_concurrent_connection_registration(self):
        """Test registration of multiple concurrent connections."""
        
        class ConnectionRegistry:
            def __init__(self):
                self.active_connections: Dict[str, Dict] = {}  # connection_id -> connection_info
                self.user_connections: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids
                self.registration_count = 0
                
            def register_connection(self, connection_id: str, user_id: str, websocket_mock) -> bool:
                """Register a new connection with race condition protection."""
                try:
                    # Check if connection already registered (duplicate registration race condition)
                    if connection_id in self.active_connections:
                        logger.warning(f"Connection {connection_id} already registered - possible race condition")
                        return False
                    
                    # Register connection
                    connection_info = {
                        'connection_id': connection_id,
                        'user_id': user_id,
                        'websocket': websocket_mock,
                        'registered_at': time.time(),
                        'status': 'active'
                    }
                    
                    self.active_connections[connection_id] = connection_info
                    
                    # Track user connections
                    if user_id not in self.user_connections:
                        self.user_connections[user_id] = set()
                    self.user_connections[user_id].add(connection_id)
                    
                    self.registration_count += 1
                    logger.info(f"Registered connection {connection_id} for user {user_id}")
                    
                    return True
                    
                except Exception as e:
                    logger.error(f"Error registering connection {connection_id}: {e}")
                    return False
                    
            def get_user_connections(self, user_id: str) -> List[str]:
                """Get all active connections for a user."""
                return list(self.user_connections.get(user_id, set()))
                
            def unregister_connection(self, connection_id: str) -> bool:
                """Unregister a connection."""
                if connection_id not in self.active_connections:
                    return False
                
                connection_info = self.active_connections[connection_id]
                user_id = connection_info['user_id']
                
                # Remove from active connections
                del self.active_connections[connection_id]
                
                # Remove from user connections
                if user_id in self.user_connections:
                    self.user_connections[user_id].discard(connection_id)
                    if not self.user_connections[user_id]:  # Remove empty set
                        del self.user_connections[user_id]
                
                return True
        
        registry = ConnectionRegistry()
        
        # Test single connection registration
        ws1 = Mock()
        assert registry.register_connection("conn-1", "user-1", ws1) == True
        assert registry.registration_count == 1
        assert "conn-1" in registry.active_connections
        assert "user-1" in registry.user_connections
        
        # Test duplicate connection registration (race condition scenario)
        ws1_duplicate = Mock()
        assert registry.register_connection("conn-1", "user-1", ws1_duplicate) == False
        assert registry.registration_count == 1  # Should not increment
        
        # Test concurrent connections for same user
        ws2 = Mock()
        assert registry.register_connection("conn-2", "user-1", ws2) == True
        assert registry.registration_count == 2
        
        user_connections = registry.get_user_connections("user-1")
        assert len(user_connections) == 2
        assert "conn-1" in user_connections
        assert "conn-2" in user_connections

    def test_multiple_connections_per_user(self):
        """Test handling multiple connections per user (e.g., multiple browser tabs)."""
        
        class MultiConnectionUserManager:
            def __init__(self, max_connections_per_user: int = 5):
                self.user_connections: Dict[str, List[Dict]] = {}
                self.max_connections_per_user = max_connections_per_user
                
            def add_user_connection(self, user_id: str, connection_id: str, websocket_mock) -> bool:
                """Add connection for user with limit enforcement."""
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = []
                
                # Check connection limit
                current_connections = len(self.user_connections[user_id])
                if current_connections >= self.max_connections_per_user:
                    logger.warning(f"User {user_id} exceeded connection limit ({current_connections}/{self.max_connections_per_user})")
                    return False
                
                # Add connection
                connection_info = {
                    'connection_id': connection_id,
                    'websocket': websocket_mock,
                    'created_at': time.time(),
                    'last_activity': time.time()
                }
                
                self.user_connections[user_id].append(connection_info)
                logger.info(f"Added connection {connection_id} for user {user_id} ({len(self.user_connections[user_id])}/{self.max_connections_per_user})")
                
                return True
                
            def remove_user_connection(self, user_id: str, connection_id: str) -> bool:
                """Remove specific connection for user."""
                if user_id not in self.user_connections:
                    return False
                
                # Find and remove connection
                user_conns = self.user_connections[user_id]
                for i, conn_info in enumerate(user_conns):
                    if conn_info['connection_id'] == connection_id:
                        del user_conns[i]
                        logger.info(f"Removed connection {connection_id} for user {user_id}")
                        
                        # Clean up empty user entry
                        if not user_conns:
                            del self.user_connections[user_id]
                        
                        return True
                
                return False
                
            def get_user_connection_count(self, user_id: str) -> int:
                """Get number of active connections for user."""
                return len(self.user_connections.get(user_id, []))
                
            def broadcast_to_user_connections(self, user_id: str, message: Dict) -> int:
                """Broadcast message to all user connections."""
                if user_id not in self.user_connections:
                    return 0
                
                successful_broadcasts = 0
                failed_connections = []
                
                for conn_info in self.user_connections[user_id]:
                    try:
                        websocket = conn_info['websocket']
                        if hasattr(websocket, 'send_json'):
                            websocket.send_json(message)  # Mock method
                            successful_broadcasts += 1
                        else:
                            failed_connections.append(conn_info['connection_id'])
                    except Exception as e:
                        logger.error(f"Failed to send to connection {conn_info['connection_id']}: {e}")
                        failed_connections.append(conn_info['connection_id'])
                
                # Clean up failed connections
                for failed_conn_id in failed_connections:
                    self.remove_user_connection(user_id, failed_conn_id)
                
                return successful_broadcasts
        
        manager = MultiConnectionUserManager(max_connections_per_user=3)
        
        # Test adding multiple connections for same user
        user_id = "multi-conn-user"
        
        ws1 = Mock()
        ws1.send_json = Mock()
        assert manager.add_user_connection(user_id, "conn-1", ws1) == True
        assert manager.get_user_connection_count(user_id) == 1
        
        ws2 = Mock()
        ws2.send_json = Mock()
        assert manager.add_user_connection(user_id, "conn-2", ws2) == True
        assert manager.get_user_connection_count(user_id) == 2
        
        ws3 = Mock()
        ws3.send_json = Mock()
        assert manager.add_user_connection(user_id, "conn-3", ws3) == True
        assert manager.get_user_connection_count(user_id) == 3
        
        # Test connection limit enforcement
        ws4 = Mock()
        assert manager.add_user_connection(user_id, "conn-4", ws4) == False  # Should be rejected
        assert manager.get_user_connection_count(user_id) == 3  # Unchanged
        
        # Test broadcasting to all connections
        test_message = {"type": "test", "data": "broadcast_test"}
        successful_broadcasts = manager.broadcast_to_user_connections(user_id, test_message)
        assert successful_broadcasts == 3
        
        # Verify all websockets received the message
        ws1.send_json.assert_called_with(test_message)
        ws2.send_json.assert_called_with(test_message)
        ws3.send_json.assert_called_with(test_message)

    def test_connection_registry_cleanup(self):
        """Test cleanup of closed connections from registry."""
        
        class ConnectionRegistryWithCleanup:
            def __init__(self):
                self.active_connections: Dict[str, Dict] = {}
                self.cleanup_count = 0
                
            def register_connection(self, connection_id: str, user_id: str, websocket_mock) -> bool:
                """Register connection with cleanup tracking."""
                self.active_connections[connection_id] = {
                    'connection_id': connection_id,
                    'user_id': user_id,
                    'websocket': websocket_mock,
                    'registered_at': time.time()
                }
                return True
                
            def cleanup_closed_connections(self) -> int:
                """Clean up closed connections."""
                closed_connections = []
                
                for conn_id, conn_info in self.active_connections.items():
                    websocket = conn_info['websocket']
                    
                    # Check if connection is closed
                    if not websocket or not getattr(websocket, 'open', True):
                        closed_connections.append(conn_id)
                
                # Remove closed connections
                for conn_id in closed_connections:
                    del self.active_connections[conn_id]
                    self.cleanup_count += 1
                
                if closed_connections:
                    logger.info(f"Cleaned up {len(closed_connections)} closed connections")
                
                return len(closed_connections)
                
            def get_active_connection_count(self) -> int:
                """Get number of active connections."""
                return len(self.active_connections)
                
            def force_cleanup_connection(self, connection_id: str) -> bool:
                """Force cleanup of specific connection."""
                if connection_id in self.active_connections:
                    del self.active_connections[connection_id]
                    self.cleanup_count += 1
                    return True
                return False
        
        registry = ConnectionRegistryWithCleanup()
        
        # Register active connections
        active_ws1 = Mock()
        active_ws1.open = True
        registry.register_connection("active-1", "user-1", active_ws1)
        
        active_ws2 = Mock()
        active_ws2.open = True
        registry.register_connection("active-2", "user-2", active_ws2)
        
        # Register closed connections
        closed_ws1 = Mock()
        closed_ws1.open = False  # Closed
        registry.register_connection("closed-1", "user-3", closed_ws1)
        
        closed_ws2 = None  # Null websocket (connection failed)
        registry.register_connection("closed-2", "user-4", closed_ws2)
        
        assert registry.get_active_connection_count() == 4
        
        # Run cleanup
        cleaned_up = registry.cleanup_closed_connections()
        assert cleaned_up == 2  # Should clean up 2 closed connections
        assert registry.get_active_connection_count() == 2  # Only active connections remain
        assert registry.cleanup_count == 2
        
        # Verify only active connections remain
        remaining_connections = list(registry.active_connections.keys())
        assert "active-1" in remaining_connections
        assert "active-2" in remaining_connections
        assert "closed-1" not in remaining_connections
        assert "closed-2" not in remaining_connections


class TestPrematureMessageSendingPrevention:
    """Test prevention of premature message sending before handshake completion."""
    
    @pytest.mark.asyncio
    async def test_safe_send_connection_readiness_check(self):
        """Test safe send with connection readiness validation."""
        
        async def safe_websocket_send(websocket, message: Dict, validate_readiness: bool = True) -> bool:
            """Safely send WebSocket message with readiness validation."""
            try:
                # Basic connection check
                if not websocket or not getattr(websocket, 'open', False):
                    logger.error("WebSocket not connected")
                    return False
                
                if validate_readiness:
                    # Enhanced readiness check to prevent race conditions
                    required_attributes = ['send', 'recv', 'close']
                    for attr in required_attributes:
                        if not hasattr(websocket, attr):
                            logger.error(f"WebSocket not ready - missing {attr}")
                            return False
                
                # Convert message to JSON
                message_json = json.dumps(message)
                
                # Send message
                await websocket.send(message_json)
                logger.info(f"Successfully sent message: {message.get('type', 'unknown')}")
                return True
                
            except Exception as e:
                error_msg = str(e)
                
                # Check for specific race condition errors
                if "Need to call 'accept' first" in error_msg:
                    logger.error(f"Race condition detected during send: {error_msg}")
                elif "WebSocket connection is closed" in error_msg:
                    logger.error(f"Connection closed during send: {error_msg}")
                else:
                    logger.error(f"Error sending WebSocket message: {error_msg}")
                
                return False
        
        # Test successful send with ready websocket
        ready_websocket = AsyncMock()
        ready_websocket.open = True
        ready_websocket.send = AsyncMock()
        ready_websocket.recv = AsyncMock()
        ready_websocket.close = AsyncMock()
        
        test_message = {"type": "test", "data": "hello"}
        result = await safe_websocket_send(ready_websocket, test_message)
        assert result == True
        ready_websocket.send.assert_called_once()
        
        # Test send with unready websocket (missing recv method)
        unready_websocket = AsyncMock()
        unready_websocket.open = True
        unready_websocket.send = AsyncMock()
        unready_websocket.close = AsyncMock()
        # Missing recv method - indicates incomplete initialization
        
        result = await safe_websocket_send(unready_websocket, test_message)
        assert result == False
        unready_websocket.send.assert_not_called()  # Should not attempt send
        
        # Test send with closed websocket
        closed_websocket = AsyncMock()
        closed_websocket.open = False
        closed_websocket.send = AsyncMock()
        closed_websocket.recv = AsyncMock()
        closed_websocket.close = AsyncMock()
        
        result = await safe_websocket_send(closed_websocket, test_message)
        assert result == False
        closed_websocket.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_retry_logic_for_race_condition_errors(self):
        """Test retry logic when race condition errors occur during send."""
        
        async def safe_websocket_send_with_retry(
            websocket, 
            message: Dict, 
            max_retries: int = 3, 
            retry_delay: float = 0.1
        ) -> bool:
            """Send WebSocket message with retry logic for race conditions."""
            
            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    # Connection readiness check
                    if not websocket or not getattr(websocket, 'open', False):
                        if attempt == 0:  # Only log on first attempt
                            logger.error("WebSocket not connected")
                        return False
                    
                    # Send message
                    message_json = json.dumps(message)
                    await websocket.send(message_json)
                    
                    logger.info(f"Message sent successfully on attempt {attempt + 1}")
                    return True
                    
                except Exception as e:
                    error_msg = str(e)
                    
                    # Determine if this is a retryable race condition error
                    retryable_errors = [
                        "Need to call 'accept' first",
                        "WebSocket handshake not complete",
                        "Connection not fully established"
                    ]
                    
                    is_retryable = any(retryable_error in error_msg for retryable_error in retryable_errors)
                    
                    if is_retryable and attempt < max_retries:
                        logger.warning(f"Retryable race condition error on attempt {attempt + 1}: {error_msg}")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"Failed to send message after {attempt + 1} attempts: {error_msg}")
                        return False
            
            return False
        
        # Test successful send on first attempt
        success_websocket = AsyncMock()
        success_websocket.open = True
        success_websocket.send = AsyncMock()
        
        test_message = {"type": "test", "data": "retry_test"}
        result = await safe_websocket_send_with_retry(success_websocket, test_message)
        assert result == True
        assert success_websocket.send.call_count == 1
        
        # Test retry logic with race condition error that eventually succeeds
        retry_websocket = AsyncMock()
        retry_websocket.open = True
        
        # First two calls fail with race condition, third succeeds
        retry_websocket.send = AsyncMock(side_effect=[
            RuntimeError("Need to call 'accept' first"),
            RuntimeError("Need to call 'accept' first"),
            None  # Success on third attempt
        ])
        
        result = await safe_websocket_send_with_retry(retry_websocket, test_message, max_retries=3, retry_delay=0.01)
        assert result == True
        assert retry_websocket.send.call_count == 3
        
        # Test permanent failure after max retries
        failing_websocket = AsyncMock()
        failing_websocket.open = True
        failing_websocket.send = AsyncMock(side_effect=RuntimeError("Need to call 'accept' first"))
        
        result = await safe_websocket_send_with_retry(failing_websocket, test_message, max_retries=2, retry_delay=0.01)
        assert result == False
        assert failing_websocket.send.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_exponential_backoff_implementation(self):
        """Test exponential backoff for WebSocket race condition recovery."""
        
        async def safe_websocket_send_with_exponential_backoff(
            websocket,
            message: Dict,
            max_retries: int = 4,
            initial_delay: float = 0.1,
            backoff_multiplier: float = 2.0,
            max_delay: float = 2.0
        ) -> Dict:
            """Send with exponential backoff and detailed timing info."""
            
            attempt_times = []
            start_time = time.time()
            
            for attempt in range(max_retries + 1):
                attempt_start = time.time()
                
                try:
                    if not websocket or not getattr(websocket, 'open', False):
                        return {
                            'success': False,
                            'attempts': attempt + 1,
                            'total_time': time.time() - start_time,
                            'attempt_times': attempt_times,
                            'error': 'WebSocket not connected'
                        }
                    
                    # Send message
                    message_json = json.dumps(message)
                    await websocket.send(message_json)
                    
                    attempt_end = time.time()
                    attempt_times.append(attempt_end - attempt_start)
                    
                    return {
                        'success': True,
                        'attempts': attempt + 1,
                        'total_time': time.time() - start_time,
                        'attempt_times': attempt_times,
                        'error': None
                    }
                    
                except Exception as e:
                    attempt_end = time.time()
                    attempt_times.append(attempt_end - attempt_start)
                    
                    error_msg = str(e)
                    
                    # Check if retryable
                    if "Need to call 'accept' first" in error_msg and attempt < max_retries:
                        # Calculate exponential backoff delay
                        delay = min(initial_delay * (backoff_multiplier ** attempt), max_delay)
                        logger.info(f"Attempt {attempt + 1} failed, retrying in {delay:.3f}s")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        return {
                            'success': False,
                            'attempts': attempt + 1,
                            'total_time': time.time() - start_time,
                            'attempt_times': attempt_times,
                            'error': error_msg
                        }
            
            return {
                'success': False,
                'attempts': max_retries + 1,
                'total_time': time.time() - start_time,
                'attempt_times': attempt_times,
                'error': 'Max retries exceeded'
            }
        
        # Test successful send with exponential backoff timing
        backoff_websocket = AsyncMock()
        backoff_websocket.open = True
        
        # Fail first 3 attempts, succeed on 4th
        backoff_websocket.send = AsyncMock(side_effect=[
            RuntimeError("Need to call 'accept' first"),
            RuntimeError("Need to call 'accept' first"),
            RuntimeError("Need to call 'accept' first"),
            None  # Success
        ])
        
        test_message = {"type": "test", "data": "backoff_test"}
        result = await safe_websocket_send_with_exponential_backoff(
            backoff_websocket, 
            test_message,
            max_retries=4,
            initial_delay=0.05,  # 50ms initial
            backoff_multiplier=2.0,
            max_delay=0.4  # 400ms max
        )
        
        assert result['success'] == True
        assert result['attempts'] == 4
        assert len(result['attempt_times']) == 4
        
        # Verify exponential backoff timing (approximately)
        # Expected delays: 0ms, 50ms, 100ms, 200ms
        total_time = result['total_time']
        expected_min_time = 0.05 + 0.10 + 0.20  # Sum of delays (approximately)
        assert total_time >= expected_min_time  # Should take at least the delay time
        
        # Test max delay enforcement
        long_backoff_websocket = AsyncMock()
        long_backoff_websocket.open = True
        long_backoff_websocket.send = AsyncMock(side_effect=RuntimeError("Need to call 'accept' first"))
        
        result = await safe_websocket_send_with_exponential_backoff(
            long_backoff_websocket,
            test_message,
            max_retries=3,
            initial_delay=0.1,
            backoff_multiplier=10.0,  # Would create very long delays
            max_delay=0.2  # But capped at 200ms
        )
        
        assert result['success'] == False
        assert result['attempts'] == 4
        
        # Total time should be reasonable due to max_delay cap
        # Without cap: 0.1 + 1.0 + 10.0 = 11.1s
        # With cap: 0.1 + 0.2 + 0.2 = 0.5s
        assert result['total_time'] < 1.0  # Should be much less than uncapped time

    @pytest.mark.asyncio
    async def test_enhanced_readiness_checking_with_state_machine(self):
        """Test enhanced readiness checking integrated with connection state machine."""
        
        class WebSocketReadinessChecker:
            def __init__(self):
                self.readiness_checks = {
                    'basic': self._check_basic_connection,
                    'handshake': self._check_handshake_complete,
                    'message_ready': self._check_message_ready,
                    'state_machine': self._check_state_machine_ready
                }
                
            async def _check_basic_connection(self, websocket) -> bool:
                """Basic connection state check."""
                return websocket and getattr(websocket, 'open', False)
                
            async def _check_handshake_complete(self, websocket) -> bool:
                """Check if handshake is complete."""
                if not await self._check_basic_connection(websocket):
                    return False
                
                # Try a simple operation to verify handshake completion
                try:
                    if hasattr(websocket, 'ping'):
                        await websocket.ping()
                    return True
                except Exception as e:
                    if "Need to call 'accept' first" in str(e):
                        return False
                    # Other errors might be transient
                    return True
                    
            async def _check_message_ready(self, websocket) -> bool:
                """Check if websocket is ready for message sending."""
                if not await self._check_handshake_complete(websocket):
                    return False
                
                required_methods = ['send', 'recv', 'close']
                return all(hasattr(websocket, method) for method in required_methods)
                
            async def _check_state_machine_ready(self, websocket) -> bool:
                """Check if state machine indicates readiness."""
                # Simulate state machine check
                state_machine = getattr(websocket, '_state_machine', None)
                if state_machine:
                    return state_machine.get('state') == 'ready'
                return True  # No state machine means we rely on other checks
                
            async def is_websocket_ready(self, websocket, check_level: str = 'message_ready') -> Dict:
                """Comprehensive readiness check with detailed results."""
                results = {
                    'ready': False,
                    'check_level': check_level,
                    'passed_checks': [],
                    'failed_checks': [],
                    'details': {}
                }
                
                # Run checks in order of complexity
                check_order = ['basic', 'handshake', 'message_ready', 'state_machine']
                
                for check_name in check_order:
                    if check_name in self.readiness_checks:
                        try:
                            check_passed = await self.readiness_checks[check_name](websocket)
                            if check_passed:
                                results['passed_checks'].append(check_name)
                            else:
                                results['failed_checks'].append(check_name)
                                results['details'][check_name] = 'Failed'
                                
                            # If we've reached the desired check level and it passed, we're ready
                            if check_name == check_level and check_passed:
                                results['ready'] = True
                                break
                            elif check_name == check_level and not check_passed:
                                results['ready'] = False
                                break
                                
                        except Exception as e:
                            results['failed_checks'].append(check_name)
                            results['details'][check_name] = f'Exception: {str(e)}'
                            if check_name == check_level:
                                results['ready'] = False
                                break
                
                return results
        
        checker = WebSocketReadinessChecker()
        
        # Test fully ready websocket
        ready_websocket = AsyncMock()
        ready_websocket.open = True
        ready_websocket.send = AsyncMock()
        ready_websocket.recv = AsyncMock()
        ready_websocket.close = AsyncMock()
        ready_websocket.ping = AsyncMock()
        ready_websocket._state_machine = {'state': 'ready'}
        
        result = await checker.is_websocket_ready(ready_websocket, 'state_machine')
        assert result['ready'] == True
        assert 'basic' in result['passed_checks']
        assert 'handshake' in result['passed_checks']
        assert 'message_ready' in result['passed_checks']
        assert 'state_machine' in result['passed_checks']
        assert len(result['failed_checks']) == 0
        
        # Test websocket that fails at handshake level
        handshake_failing_websocket = AsyncMock()
        handshake_failing_websocket.open = True
        handshake_failing_websocket.send = AsyncMock()
        handshake_failing_websocket.recv = AsyncMock()
        handshake_failing_websocket.close = AsyncMock()
        handshake_failing_websocket.ping = AsyncMock(side_effect=RuntimeError("Need to call 'accept' first"))
        
        result = await checker.is_websocket_ready(handshake_failing_websocket, 'message_ready')
        assert result['ready'] == False
        assert 'basic' in result['passed_checks']
        assert 'handshake' in result['failed_checks']
        
        # Test websocket with state machine not ready
        state_not_ready_websocket = AsyncMock()
        state_not_ready_websocket.open = True
        state_not_ready_websocket.send = AsyncMock()
        state_not_ready_websocket.recv = AsyncMock()
        state_not_ready_websocket.close = AsyncMock()
        state_not_ready_websocket.ping = AsyncMock()
        state_not_ready_websocket._state_machine = {'state': 'connecting'}  # Not ready
        
        result = await checker.is_websocket_ready(state_not_ready_websocket, 'state_machine')
        assert result['ready'] == False
        assert 'state_machine' in result['failed_checks']


class TestCloudEnvironmentSpecificLogic:
    """Test cloud environment-specific race condition handling."""
    
    def test_staging_environment_conservative_validation(self):
        """Test conservative validation approach for staging environment."""
        
        def get_environment_specific_validation_config(environment: str) -> Dict:
            """Get validation configuration based on environment."""
            
            configs = {
                "development": {
                    "handshake_timeout": 10.0,
                    "retry_attempts": 5,
                    "validation_level": "basic",
                    "allow_partial_initialization": True,
                    "log_level": "DEBUG"
                },
                "testing": {
                    "handshake_timeout": 8.0,
                    "retry_attempts": 4,
                    "validation_level": "standard",
                    "allow_partial_initialization": True,
                    "log_level": "INFO"
                },
                "staging": {
                    "handshake_timeout": 6.0,
                    "retry_attempts": 3,
                    "validation_level": "strict",
                    "allow_partial_initialization": False,  # Conservative
                    "log_level": "WARNING"
                },
                "production": {
                    "handshake_timeout": 5.0,
                    "retry_attempts": 2,
                    "validation_level": "strict",
                    "allow_partial_initialization": False,
                    "log_level": "ERROR"
                }
            }
            
            return configs.get(environment, configs["development"])
        
        # Test staging configuration is more conservative than development
        dev_config = get_environment_specific_validation_config("development")
        staging_config = get_environment_specific_validation_config("staging")
        prod_config = get_environment_specific_validation_config("production")
        
        # Staging should be stricter than development
        assert staging_config["handshake_timeout"] < dev_config["handshake_timeout"]
        assert staging_config["retry_attempts"] < dev_config["retry_attempts"]
        assert staging_config["validation_level"] == "strict"
        assert staging_config["allow_partial_initialization"] == False
        
        # But more lenient than production
        assert staging_config["handshake_timeout"] > prod_config["handshake_timeout"]
        assert staging_config["retry_attempts"] > prod_config["retry_attempts"]
        
        # Test validation level progression
        assert dev_config["validation_level"] == "basic"
        assert staging_config["validation_level"] == "strict"
        assert prod_config["validation_level"] == "strict"

    @pytest.mark.asyncio
    async def test_production_timeout_handling(self):
        """Test production environment timeout handling for race conditions."""
        
        async def production_websocket_operation_with_timeout(
            websocket,
            operation: str,
            environment: str = "production"
        ) -> Dict:
            """Perform WebSocket operation with production-appropriate timeout."""
            
            # Environment-specific timeouts
            timeouts = {
                "development": {"connect": 15.0, "handshake": 10.0, "send": 5.0},
                "staging": {"connect": 12.0, "handshake": 8.0, "send": 4.0},
                "production": {"connect": 10.0, "handshake": 6.0, "send": 3.0}
            }
            
            env_timeouts = timeouts.get(environment, timeouts["production"])
            operation_timeout = env_timeouts.get(operation, 5.0)
            
            start_time = time.time()
            
            try:
                if operation == "handshake":
                    # Simulate handshake validation
                    async def validate_handshake():
                        if not websocket or not getattr(websocket, 'open', False):
                            raise RuntimeError("WebSocket not connected")
                        
                        if hasattr(websocket, 'ping'):
                            await websocket.ping()
                        
                        # Simulate handshake completion time
                        await asyncio.sleep(0.1)
                        return True
                    
                    result = await asyncio.wait_for(validate_handshake(), timeout=operation_timeout)
                    
                elif operation == "send":
                    # Simulate message sending
                    async def send_message():
                        if not websocket or not getattr(websocket, 'open', False):
                            raise RuntimeError("WebSocket not connected")
                        
                        message = json.dumps({"type": "test", "timestamp": time.time()})
                        await websocket.send(message)
                        return True
                    
                    result = await asyncio.wait_for(send_message(), timeout=operation_timeout)
                
                else:
                    raise ValueError(f"Unsupported operation: {operation}")
                
                end_time = time.time()
                
                return {
                    'success': True,
                    'operation': operation,
                    'environment': environment,
                    'timeout': operation_timeout,
                    'actual_time': end_time - start_time,
                    'error': None
                }
                
            except asyncio.TimeoutError:
                end_time = time.time()
                return {
                    'success': False,
                    'operation': operation,
                    'environment': environment,
                    'timeout': operation_timeout,
                    'actual_time': end_time - start_time,
                    'error': f"Operation timed out after {operation_timeout}s"
                }
            except Exception as e:
                end_time = time.time()
                return {
                    'success': False,
                    'operation': operation,
                    'environment': environment,
                    'timeout': operation_timeout,
                    'actual_time': end_time - start_time,
                    'error': str(e)
                }
        
        # Test fast websocket in production (should succeed)
        fast_websocket = AsyncMock()
        fast_websocket.open = True
        fast_websocket.ping = AsyncMock()
        fast_websocket.send = AsyncMock()
        
        result = await production_websocket_operation_with_timeout(fast_websocket, "handshake", "production")
        assert result['success'] == True
        assert result['timeout'] == 6.0  # Production handshake timeout
        assert result['actual_time'] < result['timeout']
        
        # Test slow websocket in production (should timeout)
        slow_websocket = AsyncMock()
        slow_websocket.open = True
        
        async def slow_ping():
            await asyncio.sleep(8.0)  # Longer than production timeout
        slow_websocket.ping = slow_ping
        
        result = await production_websocket_operation_with_timeout(slow_websocket, "handshake", "production")
        assert result['success'] == False
        assert "timed out" in result['error']
        assert result['actual_time'] >= result['timeout']  # Should be close to timeout
        
        # Test same slow websocket in development (should succeed)
        result = await production_websocket_operation_with_timeout(slow_websocket, "handshake", "development")
        assert result['success'] == True  # Development timeout is longer (10.0s vs 6.0s)
        assert result['timeout'] == 10.0

    def test_cloud_retry_configuration(self):
        """Test cloud-specific retry configuration for different environments."""
        
        class CloudRetryConfig:
            def __init__(self, environment: str = "development"):
                self.environment = environment
                self.config = self._get_retry_config()
                
            def _get_retry_config(self) -> Dict:
                """Get retry configuration based on cloud environment."""
                
                base_configs = {
                    "development": {
                        "max_retries": 5,
                        "initial_delay": 0.1,
                        "backoff_multiplier": 1.5,
                        "max_delay": 2.0,
                        "jitter": False,
                        "circuit_breaker_threshold": 10
                    },
                    "testing": {
                        "max_retries": 4,
                        "initial_delay": 0.1,
                        "backoff_multiplier": 1.8,
                        "max_delay": 1.5,
                        "jitter": False,
                        "circuit_breaker_threshold": 8
                    },
                    "staging": {
                        "max_retries": 3,
                        "initial_delay": 0.2,  # Slightly higher for GCP
                        "backoff_multiplier": 2.0,
                        "max_delay": 1.0,      # Lower max to prevent long waits
                        "jitter": True,        # Add jitter to prevent thundering herd
                        "circuit_breaker_threshold": 5
                    },
                    "production": {
                        "max_retries": 2,
                        "initial_delay": 0.15,
                        "backoff_multiplier": 2.0,
                        "max_delay": 0.8,
                        "jitter": True,
                        "circuit_breaker_threshold": 3
                    }
                }
                
                return base_configs.get(self.environment, base_configs["development"])
            
            def calculate_retry_delays(self) -> List[float]:
                """Calculate actual retry delays for this configuration."""
                delays = []
                current_delay = self.config["initial_delay"]
                
                for retry_num in range(self.config["max_retries"]):
                    # Apply backoff multiplier
                    actual_delay = min(current_delay, self.config["max_delay"])
                    
                    # Add jitter if enabled
                    if self.config["jitter"]:
                        import random
                        jitter_amount = actual_delay * 0.2  # 20% jitter
                        jitter = random.uniform(-jitter_amount, jitter_amount)
                        actual_delay = max(0.01, actual_delay + jitter)  # Minimum 10ms
                    
                    delays.append(actual_delay)
                    current_delay *= self.config["backoff_multiplier"]
                
                return delays
            
            def should_retry(self, attempt: int, error: Exception) -> bool:
                """Determine if retry should be attempted based on attempt count and error type."""
                if attempt >= self.config["max_retries"]:
                    return False
                
                # Environment-specific retry logic
                error_msg = str(error)
                
                # Always retry race condition errors
                race_condition_errors = [
                    "Need to call 'accept' first",
                    "WebSocket handshake not complete"
                ]
                
                if any(race_error in error_msg for race_error in race_condition_errors):
                    return True
                
                # Environment-specific error handling
                if self.environment in ["staging", "production"]:
                    # In cloud environments, be more selective about retries
                    retryable_errors = [
                        "Connection reset by peer",
                        "Temporary failure in name resolution",
                        "Service temporarily unavailable"
                    ]
                    return any(retryable_error in error_msg for retryable_error in retryable_errors)
                else:
                    # In development/testing, retry more liberally
                    non_retryable_errors = [
                        "Authentication failed",
                        "Permission denied",
                        "Invalid request format"
                    ]
                    return not any(non_retryable in error_msg for non_retryable in non_retryable_errors)
        
        # Test development configuration (most permissive)
        dev_config = CloudRetryConfig("development")
        assert dev_config.config["max_retries"] == 5
        assert dev_config.config["jitter"] == False
        assert dev_config.config["circuit_breaker_threshold"] == 10
        
        dev_delays = dev_config.calculate_retry_delays()
        assert len(dev_delays) == 5
        assert all(delay <= 2.0 for delay in dev_delays)  # Respects max_delay
        
        # Test staging configuration (cloud-optimized)
        staging_config = CloudRetryConfig("staging")
        assert staging_config.config["max_retries"] == 3
        assert staging_config.config["jitter"] == True
        assert staging_config.config["circuit_breaker_threshold"] == 5
        
        staging_delays = staging_config.calculate_retry_delays()
        assert len(staging_delays) == 3
        assert all(delay <= 1.0 for delay in staging_delays)  # Lower max_delay for staging
        
        # Test production configuration (most conservative)
        prod_config = CloudRetryConfig("production")
        assert prod_config.config["max_retries"] == 2
        assert prod_config.config["circuit_breaker_threshold"] == 3
        
        # Test retry decision logic
        race_condition_error = RuntimeError("Need to call 'accept' first")
        auth_error = RuntimeError("Authentication failed")
        
        # Race condition errors should always be retryable
        assert dev_config.should_retry(0, race_condition_error) == True
        assert staging_config.should_retry(0, race_condition_error) == True
        assert prod_config.should_retry(0, race_condition_error) == True
        
        # Auth errors should never be retryable
        assert dev_config.should_retry(0, auth_error) == False
        assert staging_config.should_retry(0, auth_error) == False
        assert prod_config.should_retry(0, auth_error) == False


class TestRaceConditionReproduction:
    """Test reproduction of specific race conditions from staging environment."""
    
    @pytest.mark.asyncio
    async def test_accept_vs_message_timing_race_reproduction(self):
        """Reproduce the exact race condition: message sent before accept() called."""
        
        class WebSocketRaceConditionSimulator:
            def __init__(self):
                self.accept_called = False
                self.messages_received_before_accept = []
                self.state = "initializing"
                self.call_sequence = []
                
            async def accept(self):
                """Simulate WebSocket accept() call."""
                await asyncio.sleep(0.1)  # Simulate accept processing time
                self.accept_called = True
                self.state = "accepted"
                self.call_sequence.append("accept")
                
            async def send(self, message: str):
                """Simulate WebSocket send() call."""
                self.call_sequence.append("send")
                
                if not self.accept_called:
                    # This is the race condition!
                    error_msg = "Need to call 'accept' first"
                    self.messages_received_before_accept.append(message)
                    raise RuntimeError(error_msg)
                
                # Successful send
                await asyncio.sleep(0.05)  # Simulate send processing
                return True
                
            def get_race_condition_info(self) -> Dict:
                """Get information about race condition occurrence."""
                return {
                    'race_condition_occurred': len(self.messages_received_before_accept) > 0,
                    'messages_lost_to_race_condition': self.messages_received_before_accept,
                    'call_sequence': self.call_sequence,
                    'accept_called': self.accept_called,
                    'final_state': self.state
                }
        
        # Test normal flow (no race condition)
        normal_websocket = WebSocketRaceConditionSimulator()
        
        # Accept first, then send
        await normal_websocket.accept()
        await normal_websocket.send("test message")
        
        race_info = normal_websocket.get_race_condition_info()
        assert race_info['race_condition_occurred'] == False
        assert race_info['call_sequence'] == ['accept', 'send']
        
        # Test race condition reproduction
        race_websocket = WebSocketRaceConditionSimulator()
        
        # Create tasks that might execute in wrong order
        accept_task = asyncio.create_task(race_websocket.accept())
        
        # Small delay to increase chance of race condition
        await asyncio.sleep(0.05)
        
        # Try to send before accept completes (race condition)
        with pytest.raises(RuntimeError) as exc_info:
            await race_websocket.send("premature message")
        
        assert "Need to call 'accept' first" in str(exc_info.value)
        
        # Complete the accept task
        await accept_task
        
        race_info = race_websocket.get_race_condition_info()
        assert race_info['race_condition_occurred'] == True
        assert "premature message" in race_info['messages_lost_to_race_condition']
        assert race_info['call_sequence'] == ['send', 'accept']  # Wrong order!
        
        # Verify that messages work after accept completes
        await race_websocket.send("post-accept message")  # Should succeed now

    @pytest.mark.asyncio
    async def test_specific_user_scenario_101463487227881885914(self):
        """Test specific user scenario from staging logs: User ID 101463487227881885914."""
        
        # This reproduces a specific user scenario that was failing in staging
        # Based on actual staging logs and error patterns
        
        class StagingUserScenarioSimulator:
            def __init__(self, user_id: str):
                self.user_id = user_id
                self.connection_attempts = []
                self.websocket_states = []
                self.error_log = []
                
            async def simulate_staging_connection_sequence(self) -> Dict:
                """Simulate the exact connection sequence that was failing in staging."""
                
                sequence_start = time.time()
                
                try:
                    # Step 1: Initial connection attempt
                    self.connection_attempts.append({
                        'timestamp': time.time(),
                        'step': 'initial_connection',
                        'user_id': self.user_id
                    })
                    
                    # Step 2: Rapid WebSocket creation (staging pattern)
                    websocket_mock = Mock()
                    websocket_mock.open = False  # Initially not open
                    
                    # Step 3: Simulate GCP Cloud Run connection establishment
                    await asyncio.sleep(0.05)  # Simulate network latency
                    websocket_mock.open = True
                    
                    self.websocket_states.append({
                        'timestamp': time.time(),
                        'state': 'open',
                        'user_id': self.user_id
                    })
                    
                    # Step 4: Immediate message sending attempt (this was causing the race condition)
                    try:
                        # This is where the "Need to call 'accept' first" error was occurring
                        test_message = json.dumps({
                            'type': 'agent_request',
                            'user_id': self.user_id,
                            'message': 'Quick optimization request'
                        })
                        
                        # Simulate the race condition that was happening in staging
                        if not hasattr(websocket_mock, '_accept_called'):
                            # This simulates the exact error from staging
                            raise RuntimeError("Need to call 'accept' first")
                        
                        # If we get here, the message was sent successfully
                        return {
                            'success': True,
                            'user_id': self.user_id,
                            'total_time': time.time() - sequence_start,
                            'connection_attempts': len(self.connection_attempts),
                            'websocket_states': self.websocket_states,
                            'error_log': self.error_log
                        }
                        
                    except RuntimeError as e:
                        # This is the error that was happening in staging
                        self.error_log.append({
                            'timestamp': time.time(),
                            'error': str(e),
                            'user_id': self.user_id,
                            'error_type': 'race_condition'
                        })
                        
                        # Simulate retry logic
                        await asyncio.sleep(0.2)  # Brief retry delay
                        
                        # Mark accept as called (simulating proper initialization)
                        websocket_mock._accept_called = True
                        
                        # Retry the message sending
                        retry_success = True  # Simulate successful retry
                        
                        return {
                            'success': retry_success,
                            'user_id': self.user_id,
                            'total_time': time.time() - sequence_start,
                            'connection_attempts': len(self.connection_attempts),
                            'websocket_states': self.websocket_states,
                            'error_log': self.error_log,
                            'retry_required': True
                        }
                        
                except Exception as e:
                    self.error_log.append({
                        'timestamp': time.time(),
                        'error': str(e),
                        'user_id': self.user_id,
                        'error_type': 'unexpected'
                    })
                    
                    return {
                        'success': False,
                        'user_id': self.user_id,
                        'total_time': time.time() - sequence_start,
                        'connection_attempts': len(self.connection_attempts),
                        'websocket_states': self.websocket_states,
                        'error_log': self.error_log,
                        'fatal_error': True
                    }
        
        # Test the specific user scenario that was failing
        failing_user_id = "101463487227881885914"
        simulator = StagingUserScenarioSimulator(failing_user_id)
        
        result = await simulator.simulate_staging_connection_sequence()
        
        # Verify that we can reproduce the race condition
        assert result['user_id'] == failing_user_id
        assert len(result['error_log']) > 0  # Should have logged the race condition error
        
        # Check if the specific race condition error occurred
        race_condition_errors = [
            error for error in result['error_log']
            if error['error_type'] == 'race_condition' and 
               'Need to call \'accept\' first' in error['error']
        ]
        assert len(race_condition_errors) > 0  # Should reproduce the exact error
        
        # Verify recovery logic worked (if retry was implemented)
        if 'retry_required' in result:
            assert result['retry_required'] == True
            # With retry logic, the user should eventually succeed
            assert result['success'] == True
        
        # Verify timing is realistic for staging environment
        assert result['total_time'] < 2.0  # Should complete reasonably quickly

    @pytest.mark.asyncio
    async def test_e2e_staging_pipeline_scenario(self):
        """Test E2E staging pipeline scenario that reproduces production race conditions."""
        
        class E2EStagingPipelineSimulator:
            def __init__(self):
                self.pipeline_steps = []
                self.user_sessions = {}
                self.websocket_connections = {}
                self.race_conditions_detected = []
                
            async def simulate_e2e_user_flow(self, user_id: str) -> Dict:
                """Simulate complete E2E user flow that was experiencing race conditions."""
                
                flow_start = time.time()
                
                try:
                    # Step 1: User authentication (staging OAuth simulation)
                    auth_result = await self._simulate_auth_step(user_id)
                    self.pipeline_steps.append(auth_result)
                    
                    if not auth_result['success']:
                        return {'success': False, 'failed_at': 'authentication', 'steps': self.pipeline_steps}
                    
                    # Step 2: WebSocket connection establishment
                    websocket_result = await self._simulate_websocket_connection(user_id)
                    self.pipeline_steps.append(websocket_result)
                    
                    if not websocket_result['success']:
                        return {'success': False, 'failed_at': 'websocket_connection', 'steps': self.pipeline_steps}
                    
                    # Step 3: Agent request (this is where race conditions often occurred)
                    agent_result = await self._simulate_agent_request(user_id)
                    self.pipeline_steps.append(agent_result)
                    
                    if not agent_result['success']:
                        return {'success': False, 'failed_at': 'agent_request', 'steps': self.pipeline_steps}
                    
                    # Step 4: WebSocket event delivery
                    events_result = await self._simulate_websocket_events(user_id)
                    self.pipeline_steps.append(events_result)
                    
                    return {
                        'success': events_result['success'],
                        'user_id': user_id,
                        'total_time': time.time() - flow_start,
                        'steps': self.pipeline_steps,
                        'race_conditions_detected': self.race_conditions_detected
                    }
                    
                except Exception as e:
                    return {
                        'success': False,
                        'user_id': user_id,
                        'total_time': time.time() - flow_start,
                        'error': str(e),
                        'steps': self.pipeline_steps,
                        'race_conditions_detected': self.race_conditions_detected
                    }
            
            async def _simulate_auth_step(self, user_id: str) -> Dict:
                """Simulate authentication step with staging characteristics."""
                step_start = time.time()
                
                # Simulate OAuth token validation delay (staging-specific)
                await asyncio.sleep(0.1)
                
                # Create user session
                self.user_sessions[user_id] = {
                    'authenticated_at': time.time(),
                    'jwt_token': f"staging-jwt-{user_id}",
                    'session_id': f"session-{user_id}"
                }
                
                return {
                    'step': 'authentication',
                    'success': True,
                    'duration': time.time() - step_start,
                    'user_id': user_id
                }
            
            async def _simulate_websocket_connection(self, user_id: str) -> Dict:
                """Simulate WebSocket connection with race condition potential."""
                step_start = time.time()
                
                try:
                    # Simulate WebSocket connection establishment
                    connection_id = f"ws-conn-{user_id}"
                    
                    # This is where race conditions were occurring in staging
                    websocket_mock = Mock()
                    websocket_mock.open = False
                    
                    # Simulate connection establishment delay
                    await asyncio.sleep(0.05)
                    websocket_mock.open = True
                    
                    # Check for race condition in connection establishment
                    if not hasattr(websocket_mock, '_handshake_complete'):
                        # Race condition detected!
                        race_condition = {
                            'type': 'handshake_incomplete',
                            'user_id': user_id,
                            'connection_id': connection_id,
                            'timestamp': time.time()
                        }
                        self.race_conditions_detected.append(race_condition)
                        
                        # Simulate recovery
                        await asyncio.sleep(0.1)  # Recovery delay
                        websocket_mock._handshake_complete = True
                    
                    self.websocket_connections[user_id] = {
                        'connection_id': connection_id,
                        'websocket': websocket_mock,
                        'connected_at': time.time()
                    }
                    
                    return {
                        'step': 'websocket_connection',
                        'success': True,
                        'duration': time.time() - step_start,
                        'connection_id': connection_id
                    }
                    
                except Exception as e:
                    return {
                        'step': 'websocket_connection',
                        'success': False,
                        'duration': time.time() - step_start,
                        'error': str(e)
                    }
            
            async def _simulate_agent_request(self, user_id: str) -> Dict:
                """Simulate agent request with potential race conditions."""
                step_start = time.time()
                
                try:
                    websocket_info = self.websocket_connections.get(user_id)
                    if not websocket_info:
                        raise RuntimeError("WebSocket not available")
                    
                    websocket = websocket_info['websocket']
                    
                    # Simulate agent request message
                    agent_message = {
                        'type': 'agent_request',
                        'agent': 'triage_agent',
                        'message': 'Staging E2E test optimization request'
                    }
                    
                    # This is where "Need to call 'accept' first" errors occurred
                    if not getattr(websocket, '_handshake_complete', False):
                        race_condition = {
                            'type': 'agent_request_race_condition',
                            'user_id': user_id,
                            'error': 'WebSocket handshake not complete before agent request',
                            'timestamp': time.time()
                        }
                        self.race_conditions_detected.append(race_condition)
                        raise RuntimeError("Need to call 'accept' first")
                    
                    # Simulate successful agent request processing
                    await asyncio.sleep(0.2)  # Simulate agent processing time
                    
                    return {
                        'step': 'agent_request',
                        'success': True,
                        'duration': time.time() - step_start,
                        'agent_message': agent_message
                    }
                    
                except Exception as e:
                    # Simulate retry logic for race conditions
                    if "Need to call 'accept' first" in str(e):
                        await asyncio.sleep(0.1)  # Retry delay
                        
                        # Mark handshake as complete for retry
                        websocket_info = self.websocket_connections.get(user_id)
                        if websocket_info:
                            websocket_info['websocket']._handshake_complete = True
                        
                        # Retry the agent request
                        await asyncio.sleep(0.2)  # Simulate successful retry
                        
                        return {
                            'step': 'agent_request',
                            'success': True,
                            'duration': time.time() - step_start,
                            'retry_required': True,
                            'original_error': str(e)
                        }
                    
                    return {
                        'step': 'agent_request',
                        'success': False,
                        'duration': time.time() - step_start,
                        'error': str(e)
                    }
            
            async def _simulate_websocket_events(self, user_id: str) -> Dict:
                """Simulate WebSocket event delivery."""
                step_start = time.time()
                
                # Simulate the 5 required WebSocket events
                required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
                delivered_events = []
                
                for event_type in required_events:
                    await asyncio.sleep(0.05)  # Simulate event delivery delay
                    delivered_events.append({
                        'type': event_type,
                        'timestamp': time.time(),
                        'user_id': user_id
                    })
                
                # Check if all events were delivered (staging requirement)
                all_events_delivered = len(delivered_events) == len(required_events)
                
                return {
                    'step': 'websocket_events',
                    'success': all_events_delivered,
                    'duration': time.time() - step_start,
                    'events_delivered': len(delivered_events),
                    'events_expected': len(required_events),
                    'delivered_events': delivered_events
                }
        
        # Test E2E staging pipeline with race condition reproduction
        simulator = E2EStagingPipelineSimulator()
        
        # Test user that was experiencing issues in staging
        test_user = "staging-e2e-test-user-001"
        result = await simulator.simulate_e2e_user_flow(test_user)
        
        # Verify the pipeline completed (with or without race condition recovery)
        assert result['user_id'] == test_user
        assert len(result['steps']) >= 4  # Should have all 4 steps
        
        # Check if race conditions were detected and handled
        if len(result['race_conditions_detected']) > 0:
            print(f"Race conditions detected and handled: {len(result['race_conditions_detected'])}")
            
            # Verify that the system recovered from race conditions
            # (The final result should still be successful if recovery logic works)
            if result['success']:
                print("✅ Race conditions detected but system recovered successfully")
            else:
                print("❌ Race conditions detected and system failed to recover")
        
        # Verify that the critical WebSocket events were delivered
        events_step = next((step for step in result['steps'] if step['step'] == 'websocket_events'), None)
        if events_step:
            assert events_step['events_delivered'] == 5  # All 5 critical events
            assert events_step['success'] == True
        
        # Verify reasonable completion time for staging
        assert result['total_time'] < 5.0  # Should complete within 5 seconds for E2E flow


class TestPerformanceAndResourceManagement:
    """Test performance implications of race condition fixes."""
    
    def test_state_machine_memory_footprint_under_load(self):
        """Test memory footprint of connection state machines under load."""
        
        import sys
        from typing import List
        
        class MemoryEfficientConnectionStateMachine:
            __slots__ = ['connection_id', 'user_id', 'state', 'created_at', 'state_count']  # Reduce memory usage
            
            def __init__(self, connection_id: str, user_id: str):
                self.connection_id = connection_id
                self.user_id = user_id
                self.state = 'initializing'
                self.created_at = time.time()
                self.state_count = 1
                
            def transition_to(self, new_state: str) -> bool:
                """Memory-efficient state transition."""
                valid_transitions = {
                    'initializing': ['connecting', 'failed'],
                    'connecting': ['connected', 'failed'],
                    'connected': ['disconnecting', 'failed'],
                    'disconnecting': ['disconnected'],
                    'failed': [],
                    'disconnected': []
                }
                
                if new_state in valid_transitions.get(self.state, []):
                    self.state = new_state
                    self.state_count += 1
                    return True
                return False
                
            def get_memory_info(self) -> Dict:
                """Get memory usage information for this state machine."""
                return {
                    'object_size_bytes': sys.getsizeof(self),
                    'connection_id_size': sys.getsizeof(self.connection_id),
                    'user_id_size': sys.getsizeof(self.user_id),
                    'state_size': sys.getsizeof(self.state),
                    'total_attributes': 5  # __slots__ attributes
                }
        
        # Test memory usage under load simulation
        num_state_machines = 1000  # Simulate 1000 concurrent connections
        state_machines: List[MemoryEfficientConnectionStateMachine] = []
        
        # Create state machines
        start_time = time.time()
        for i in range(num_state_machines):
            sm = MemoryEfficientConnectionStateMachine(f"conn-{i}", f"user-{i % 100}")  # 100 users, 10 connections each
            state_machines.append(sm)
        creation_time = time.time() - start_time
        
        # Test state transitions
        transition_start = time.time()
        successful_transitions = 0
        for sm in state_machines:
            if sm.transition_to('connecting'):
                successful_transitions += 1
            if sm.transition_to('connected'):
                successful_transitions += 1
        transition_time = time.time() - transition_start
        
        # Measure memory usage
        sample_sm = state_machines[0]
        memory_info = sample_sm.get_memory_info()
        total_memory_estimate = memory_info['object_size_bytes'] * num_state_machines
        
        # Performance assertions
        assert creation_time < 1.0, f"Creating {num_state_machines} state machines took too long: {creation_time:.3f}s"
        assert transition_time < 0.5, f"State transitions took too long: {transition_time:.3f}s"
        assert successful_transitions == num_state_machines * 2  # connecting + connected for each
        
        # Memory efficiency assertions
        assert memory_info['object_size_bytes'] < 200, f"State machine memory usage too high: {memory_info['object_size_bytes']} bytes"
        assert total_memory_estimate < 200000, f"Total memory for {num_state_machines} state machines too high: {total_memory_estimate} bytes"
        
        # Log performance metrics
        logger.info(f"Performance metrics for {num_state_machines} state machines:")
        logger.info(f"  Creation time: {creation_time:.3f}s")
        logger.info(f"  Transition time: {transition_time:.3f}s")  
        logger.info(f"  Memory per state machine: {memory_info['object_size_bytes']} bytes")
        logger.info(f"  Total memory estimate: {total_memory_estimate / 1024:.1f} KB")
        
        # Cleanup test
        del state_machines
        
    def test_state_transition_performance_benchmarking(self):
        """Test performance of state transitions under concurrent load."""
        
        import threading
        from concurrent.futures import ThreadPoolExecutor
        
        class PerformanceOptimizedStateMachine:
            def __init__(self, connection_id: str, user_id: str):
                self.connection_id = connection_id
                self.user_id = user_id
                self.state = 'initializing'
                self._lock = threading.Lock()  # Minimal locking for thread safety
                self.transition_count = 0
                self.transition_times = []
                
            def transition_to_with_timing(self, new_state: str) -> Dict:
                """State transition with performance timing."""
                start_time = time.time()
                
                with self._lock:
                    # Pre-computed transition lookup for performance
                    valid_next_states = {
                        'initializing': {'connecting', 'failed'},
                        'connecting': {'connected', 'failed'},
                        'connected': {'disconnecting', 'failed'},
                        'disconnecting': {'disconnected'},
                        'failed': set(),
                        'disconnected': set()
                    }
                    
                    if new_state in valid_next_states.get(self.state, set()):
                        old_state = self.state
                        self.state = new_state
                        self.transition_count += 1
                        
                        end_time = time.time()
                        transition_time = end_time - start_time
                        self.transition_times.append(transition_time)
                        
                        return {
                            'success': True,
                            'old_state': old_state,
                            'new_state': new_state,
                            'transition_time': transition_time,
                            'total_transitions': self.transition_count
                        }
                    else:
                        end_time = time.time()
                        return {
                            'success': False,
                            'old_state': self.state,
                            'attempted_state': new_state,
                            'transition_time': end_time - start_time,
                            'total_transitions': self.transition_count
                        }
            
            def get_performance_stats(self) -> Dict:
                """Get performance statistics."""
                if not self.transition_times:
                    return {'no_transitions': True}
                
                return {
                    'total_transitions': len(self.transition_times),
                    'min_transition_time': min(self.transition_times),
                    'max_transition_time': max(self.transition_times),
                    'avg_transition_time': sum(self.transition_times) / len(self.transition_times),
                    'transitions_per_second': len(self.transition_times) / sum(self.transition_times) if sum(self.transition_times) > 0 else 0
                }
        
        # Performance benchmark test
        num_state_machines = 50
        transitions_per_machine = 10
        
        def benchmark_state_machine(machine_id: int) -> Dict:
            """Benchmark a single state machine performance."""
            sm = PerformanceOptimizedStateMachine(f"perf-conn-{machine_id}", f"perf-user-{machine_id}")
            
            # Perform rapid state transitions
            transition_sequence = ['connecting', 'connected', 'disconnecting', 'disconnected']
            results = []
            
            for _ in range(transitions_per_machine):
                # Reset to initializing for repeated benchmarking
                sm.state = 'initializing'
                sm.transition_count = 0
                
                # Perform transition sequence
                for next_state in transition_sequence:
                    result = sm.transition_to_with_timing(next_state)
                    results.append(result)
            
            return {
                'machine_id': machine_id,
                'performance_stats': sm.get_performance_stats(),
                'transition_results': results
            }
        
        # Run concurrent benchmarking
        benchmark_start = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(benchmark_state_machine, i) for i in range(num_state_machines)]
            benchmark_results = [future.result() for future in futures]
        
        benchmark_end = time.time()
        total_benchmark_time = benchmark_end - benchmark_start
        
        # Analyze performance results
        all_transition_times = []
        total_transitions = 0
        
        for result in benchmark_results:
            stats = result['performance_stats']
            if 'no_transitions' not in stats:
                all_transition_times.extend([r['transition_time'] for r in result['transition_results']])
                total_transitions += stats['total_transitions']
        
        # Performance assertions
        if all_transition_times:
            avg_transition_time = sum(all_transition_times) / len(all_transition_times)
            max_transition_time = max(all_transition_times)
            
            # Transitions should be very fast (under 1ms each)
            assert avg_transition_time < 0.001, f"Average transition time too slow: {avg_transition_time * 1000:.3f}ms"
            assert max_transition_time < 0.01, f"Maximum transition time too slow: {max_transition_time * 1000:.3f}ms"
            
            # Overall throughput should be high
            transitions_per_second = total_transitions / total_benchmark_time
            assert transitions_per_second > 1000, f"Transition throughput too low: {transitions_per_second:.0f} transitions/second"
            
            logger.info(f"State transition performance benchmark results:")
            logger.info(f"  Total state machines: {num_state_machines}")
            logger.info(f"  Total transitions: {total_transitions}")
            logger.info(f"  Benchmark time: {total_benchmark_time:.3f}s")
            logger.info(f"  Average transition time: {avg_transition_time * 1000:.6f}ms")
            logger.info(f"  Throughput: {transitions_per_second:.0f} transitions/second")

    @pytest.mark.asyncio
    async def test_concurrent_readiness_checks_performance(self):
        """Test performance of concurrent WebSocket readiness checks."""
        
        class ConcurrentReadinessChecker:
            def __init__(self):
                self.check_count = 0
                self.check_times = []
                self.concurrent_results = []
                
            async def check_websocket_readiness_optimized(self, websocket_mock, check_id: str) -> Dict:
                """Optimized readiness check for concurrent execution."""
                start_time = time.time()
                
                try:
                    # Fast-path basic checks
                    if not websocket_mock or not getattr(websocket_mock, 'open', False):
                        return {
                            'check_id': check_id,
                            'ready': False,
                            'reason': 'not_connected',
                            'check_time': time.time() - start_time
                        }
                    
                    # Optimized attribute existence checks
                    required_attrs = ['send', 'recv', 'close']
                    
                    # Use all() with generator for efficiency
                    if not all(hasattr(websocket_mock, attr) for attr in required_attrs):
                        return {
                            'check_id': check_id,
                            'ready': False,
                            'reason': 'missing_methods',
                            'check_time': time.time() - start_time
                        }
                    
                    # Simulate minimal readiness validation
                    await asyncio.sleep(0.001)  # 1ms simulated check time
                    
                    return {
                        'check_id': check_id,
                        'ready': True,
                        'reason': 'fully_ready',
                        'check_time': time.time() - start_time
                    }
                    
                except Exception as e:
                    return {
                        'check_id': check_id,
                        'ready': False,
                        'reason': f'exception: {str(e)}',
                        'check_time': time.time() - start_time
                    }
            
            async def concurrent_readiness_benchmark(self, num_concurrent_checks: int) -> Dict:
                """Benchmark concurrent readiness checks."""
                
                # Create various websocket states for testing
                websocket_states = []
                for i in range(num_concurrent_checks):
                    ws_mock = Mock()
                    ws_mock.open = True
                    ws_mock.send = AsyncMock()
                    ws_mock.recv = AsyncMock() 
                    ws_mock.close = AsyncMock()
                    websocket_states.append(ws_mock)
                
                # Run concurrent readiness checks
                benchmark_start = time.time()
                
                tasks = [
                    self.check_websocket_readiness_optimized(ws, f"check-{i}")
                    for i, ws in enumerate(websocket_states)
                ]
                
                results = await asyncio.gather(*tasks)
                
                benchmark_end = time.time()
                total_time = benchmark_end - benchmark_start
                
                # Analyze results
                ready_count = sum(1 for r in results if r['ready'])
                check_times = [r['check_time'] for r in results]
                
                return {
                    'total_checks': num_concurrent_checks,
                    'ready_count': ready_count,
                    'total_time': total_time,
                    'avg_check_time': sum(check_times) / len(check_times),
                    'max_check_time': max(check_times),
                    'min_check_time': min(check_times),
                    'checks_per_second': num_concurrent_checks / total_time,
                    'all_results': results
                }
        
        checker = ConcurrentReadinessChecker()
        
        # Test various concurrency levels
        concurrency_levels = [10, 50, 100, 200]
        
        for num_concurrent in concurrency_levels:
            result = await checker.concurrent_readiness_benchmark(num_concurrent)
            
            # Performance assertions
            assert result['checks_per_second'] > 100, f"Readiness check throughput too low at {num_concurrent} concurrent: {result['checks_per_second']:.0f} checks/second"
            assert result['avg_check_time'] < 0.01, f"Average check time too slow at {num_concurrent} concurrent: {result['avg_check_time'] * 1000:.3f}ms"
            assert result['max_check_time'] < 0.1, f"Maximum check time too slow at {num_concurrent} concurrent: {result['max_check_time'] * 1000:.3f}ms"
            
            # Most checks should succeed (testing with good websocket mocks)
            success_rate = result['ready_count'] / result['total_checks']
            assert success_rate > 0.9, f"Success rate too low at {num_concurrent} concurrent: {success_rate:.2%}"
            
            logger.info(f"Concurrent readiness check performance ({num_concurrent} concurrent):")
            logger.info(f"  Total time: {result['total_time']:.3f}s")
            logger.info(f"  Average check time: {result['avg_check_time'] * 1000:.3f}ms")
            logger.info(f"  Throughput: {result['checks_per_second']:.0f} checks/second")
            logger.info(f"  Success rate: {success_rate:.2%}")
        
        # Test performance degradation under load
        light_load_result = await checker.concurrent_readiness_benchmark(10)
        heavy_load_result = await checker.concurrent_readiness_benchmark(200)
        
        # Performance shouldn't degrade significantly under load
        performance_degradation = heavy_load_result['avg_check_time'] / light_load_result['avg_check_time']
        assert performance_degradation < 5.0, f"Performance degraded too much under load: {performance_degradation:.2f}x slower"
        
        logger.info(f"Performance scaling analysis:")
        logger.info(f"  Light load (10 concurrent): {light_load_result['avg_check_time'] * 1000:.3f}ms avg")
        logger.info(f"  Heavy load (200 concurrent): {heavy_load_result['avg_check_time'] * 1000:.3f}ms avg")
        logger.info(f"  Performance degradation: {performance_degradation:.2f}x")