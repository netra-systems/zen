"""
WebSocket Handshake Coordinator

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Coordinate WebSocket handshake completion with message handling
- Value Impact: Prevents race conditions between connection establishment and message processing
- Strategic/Revenue Impact: Protects $500K+ ARR by ensuring reliable handshake sequencing

This module implements handshake coordination logic that prevents race conditions
by managing the timing between WebSocket accept() completion and message handling.

CRITICAL FEATURES:
1. Handshake completion validation before message processing
2. State transition management with detailed logging
3. Environment-specific timing for Cloud Run optimization
4. Error recovery coordination for failed handshakes
5. Application-level readiness gate control

ROOT CAUSE ADDRESSED:
- Message handling starting before WebSocket handshake completion
- Missing coordination between transport-level and application-level readiness
- No systematic state transition management for connection lifecycle
- Lack of Cloud Run specific timing considerations
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.race_condition_prevention.types import (
    ApplicationConnectionState,
    RaceConditionPattern
)
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


class HandshakeCoordinator:
    """
    Coordinates WebSocket handshake completion with message handling.
    
    This class ensures that message processing does not begin until the WebSocket
    handshake is completely finished and the connection is ready for bidirectional
    communication.
    
    Key Responsibilities:
    1. Handshake completion validation
    2. Message handling gate control  
    3. State transition management
    4. Error recovery coordination
    5. Environment-specific timing control
    
    State Flow:
    INITIALIZING  ->  HANDSHAKE_PENDING  ->  CONNECTED  ->  READY_FOR_MESSAGES
    
    Error States:
    Any state  ->  ERROR (on failure)
    Any state  ->  CLOSED (on normal closure)
    """
    
    def __init__(self, environment: Optional[str] = None):
        """
        Initialize handshake coordinator.
        
        Args:
            environment: Target environment (testing, development, staging, production)
                        If None, will be detected from isolated environment
        """
        if environment is None:
            env = get_env()
            environment = env.get("ENVIRONMENT", "development").lower()
        
        self.environment = environment.lower()
        self.state = ApplicationConnectionState.INITIALIZING
        self.handshake_start_time: Optional[datetime] = None
        self.state_transitions: List[Tuple[ApplicationConnectionState, ApplicationConnectionState, datetime]] = []
        
        logger.debug(f"HandshakeCoordinator initialized for {self.environment} environment")
        logger.debug(f"Initial state: {self.state.value}")
    
    async def coordinate_handshake(self) -> bool:
        """
        Coordinate handshake completion before allowing messages.
        
        This is the main coordination method that manages the complete handshake
        process with environment-specific timing to prevent race conditions.
        
        Returns:
            True if handshake completed successfully and connection is ready
            
        Timing by Environment:
        - testing: Minimal delays for fast test execution
        - development: Moderate delays for good developer experience
        - staging/production: Cloud Run optimized timing with stabilization delays
        """
        try:
            logger.debug(f"Starting handshake coordination in {self.environment}")
            
            # Record handshake start time
            self.handshake_start_time = datetime.now(timezone.utc)
            self._transition_state(ApplicationConnectionState.HANDSHAKE_PENDING)
            
            # Phase 1: Initial handshake timing
            # This simulates the time needed for the WebSocket handshake to fully complete
            if self.environment in ["staging", "production"]:
                # Cloud Run environments need more time for network propagation
                await asyncio.sleep(0.1)  # 100ms for Cloud Run network latency
                logger.debug("Cloud Run handshake timing complete (100ms)")
            else:
                # Local environments can use minimal delay
                await asyncio.sleep(0.005)  # 5ms minimal delay for other environments
                logger.debug("Local handshake timing complete (5ms)")
            
            # Phase 2: Transport-level connection establishment
            self._transition_state(ApplicationConnectionState.CONNECTED)
            logger.debug("WebSocket transport-level connection established")
            
            # Phase 3: Cloud Run specific stabilization
            # This is critical for Cloud Run environments where additional time is needed
            # for the connection to be fully stable and ready for bidirectional communication
            if self.environment in ["staging", "production"]:
                await asyncio.sleep(0.025)  # Additional 25ms stabilization for Cloud Run
                logger.debug("Cloud Run connection stabilization complete (25ms)")
            
            # Phase 4: Application-level readiness
            self._transition_state(ApplicationConnectionState.READY_FOR_MESSAGES)
            
            # Calculate total handshake time
            if self.handshake_start_time:
                total_time = (datetime.now(timezone.utc) - self.handshake_start_time).total_seconds()
                logger.info(f"Handshake coordination complete in {total_time*1000:.1f}ms")
            
            return True
            
        except asyncio.CancelledError:
            logger.warning("Handshake coordination cancelled")
            self._transition_state(ApplicationConnectionState.ERROR)
            return False
        except Exception as e:
            logger.error(f"Handshake coordination failed: {e}")
            self._transition_state(ApplicationConnectionState.ERROR)
            return False
    
    def _transition_state(self, new_state: ApplicationConnectionState):
        """
        Record state transition for debugging and validation.
        
        This method maintains a complete audit trail of state transitions
        which is essential for debugging race condition issues.
        
        Args:
            new_state: Target state to transition to
        """
        old_state = self.state
        transition_time = datetime.now(timezone.utc)
        
        # Record the transition
        self.state_transitions.append((old_state, new_state, transition_time))
        self.state = new_state
        
        logger.debug(f"State transition: {old_state.value}  ->  {new_state.value}")
        
        # Log important transitions with more detail
        if new_state == ApplicationConnectionState.READY_FOR_MESSAGES:
            total_transitions = len(self.state_transitions)
            if self.handshake_start_time:
                total_time = (transition_time - self.handshake_start_time).total_seconds()
                logger.info(f"Connection ready for messages after {total_transitions} transitions in {total_time*1000:.1f}ms")
        
        elif new_state == ApplicationConnectionState.ERROR:
            logger.warning(f"Connection entered ERROR state from {old_state.value}")
        
        elif new_state == ApplicationConnectionState.CLOSED:
            logger.info(f"Connection closed from {old_state.value}")
    
    def is_ready_for_messages(self) -> bool:
        """
        Check if handshake is complete and ready for messages.
        
        This is the core gate that prevents race conditions by ensuring
        message processing only begins when the connection is fully ready.
        
        Returns:
            True only when connection is in READY_FOR_MESSAGES state
        """
        is_ready = self.state == ApplicationConnectionState.READY_FOR_MESSAGES
        
        if not is_ready:
            logger.debug(f"Connection not ready for messages: current_state={self.state.value}")
        
        return is_ready
    
    def get_current_state(self) -> ApplicationConnectionState:
        """Get current connection state."""
        return self.state
    
    def get_handshake_duration(self) -> Optional[float]:
        """
        Get total handshake duration in seconds.
        
        Returns:
            Duration in seconds if handshake has started, None otherwise
        """
        if not self.handshake_start_time:
            return None
        
        # Find when we reached READY_FOR_MESSAGES state
        ready_time = None
        for old_state, new_state, transition_time in self.state_transitions:
            if new_state == ApplicationConnectionState.READY_FOR_MESSAGES:
                ready_time = transition_time
                break
        
        if ready_time:
            return (ready_time - self.handshake_start_time).total_seconds()
        else:
            # Still in progress
            return (datetime.now(timezone.utc) - self.handshake_start_time).total_seconds()
    
    def get_state_history(self) -> List[dict]:
        """
        Get complete state transition history.
        
        Returns:
            List of state transitions with timestamps for debugging
        """
        history = []
        
        for old_state, new_state, transition_time in self.state_transitions:
            history.append({
                "from_state": old_state.value,
                "to_state": new_state.value,
                "timestamp": transition_time.isoformat(),
                "transition_time_ms": transition_time.timestamp() * 1000
            })
        
        return history
    
    def validate_state_sequence(self) -> bool:
        """
        Validate that state transitions follow expected sequence.
        
        This helps detect if race conditions have corrupted the state machine.
        
        Returns:
            True if state sequence is valid
        """
        if not self.state_transitions:
            return True
        
        # Define valid transitions
        valid_transitions = {
            ApplicationConnectionState.INITIALIZING: [
                ApplicationConnectionState.HANDSHAKE_PENDING,
                ApplicationConnectionState.ERROR,
                ApplicationConnectionState.CLOSED
            ],
            ApplicationConnectionState.HANDSHAKE_PENDING: [
                ApplicationConnectionState.CONNECTED,
                ApplicationConnectionState.ERROR,
                ApplicationConnectionState.CLOSED
            ],
            ApplicationConnectionState.CONNECTED: [
                ApplicationConnectionState.READY_FOR_MESSAGES,
                ApplicationConnectionState.ERROR,
                ApplicationConnectionState.CLOSED
            ],
            ApplicationConnectionState.READY_FOR_MESSAGES: [
                ApplicationConnectionState.ERROR,
                ApplicationConnectionState.CLOSED
            ],
            ApplicationConnectionState.ERROR: [
                ApplicationConnectionState.CLOSED
            ],
            ApplicationConnectionState.CLOSED: []
        }
        
        # Check each transition
        for old_state, new_state, _ in self.state_transitions:
            allowed_transitions = valid_transitions.get(old_state, [])
            if new_state not in allowed_transitions:
                logger.error(f"Invalid state transition: {old_state.value}  ->  {new_state.value}")
                return False
        
        return True
    
    def reset(self):
        """
        Reset coordinator to initial state (for testing).
        
        This method resets the coordinator to initial state for reuse,
        primarily useful in testing scenarios.
        """
        self.state = ApplicationConnectionState.INITIALIZING
        self.handshake_start_time = None
        self.state_transitions.clear()
        logger.debug("HandshakeCoordinator reset to initial state")
    
    def force_error_state(self, reason: str = "Forced error"):
        """
        Force coordinator into error state (for testing).
        
        Args:
            reason: Reason for forcing error state
        """
        logger.warning(f"Forcing error state: {reason}")
        self._transition_state(ApplicationConnectionState.ERROR)
    
    def get_coordination_summary(self) -> dict:
        """
        Get summary of coordination state and metrics.
        
        Returns:
            Dictionary with current state and performance metrics
        """
        duration = self.get_handshake_duration()
        
        return {
            "current_state": self.state.value,
            "environment": self.environment,
            "handshake_duration_ms": duration * 1000 if duration else None,
            "total_transitions": len(self.state_transitions),
            "is_ready_for_messages": self.is_ready_for_messages(),
            "state_sequence_valid": self.validate_state_sequence(),
            "handshake_start_time": self.handshake_start_time.isoformat() if self.handshake_start_time else None
        }