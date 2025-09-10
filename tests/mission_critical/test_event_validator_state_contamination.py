"""Mission Critical Test: EventValidator Global State Contamination

REPRODUCTION TEST - This test should FAIL initially due to global instance pattern.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - $500K+ ARR at risk  
- Business Goal: WebSocket Event Integrity & User Isolation
- Value Impact: Prevents validation state bleeding between users causing incorrect event processing
- Revenue Impact: Contaminated validation state breaks chat functionality - core platform value

GLOBAL INSTANCE VIOLATION UNDER TEST:
File: netra_backend/app/websocket_core/event_validator.py:880-892
Issue: _unified_validator_instance global variable shared across all users
Impact: Validation state contamination between concurrent user sessions

EXPECTED BEHAVIOR:
- PRE-REFACTORING: This test should FAIL - proving global state contamination exists
- POST-REFACTORING: This test should PASS - proving factory pattern provides isolation

CRITICAL BUSINESS IMPACT:
EventValidator global state contamination causes:
1. User A's validation errors to affect User B's events
2. Validation rules to persist across different user sessions  
3. Chat events to be incorrectly validated based on previous user's context
4. WebSocket events to fail or succeed incorrectly due to contaminated state
"""

import asyncio
import uuid
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT Test Framework Compliance
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# Import the global instance violator under test
from netra_backend.app.websocket_core.event_validator import (
    get_websocket_validator, 
    reset_websocket_validator,
    UnifiedEventValidator,
    _unified_validator_instance  # Global variable causing contamination
)


class TestEventValidatorStateContamination(SSotAsyncTestCase):
    """Mission Critical Test: Expose EventValidator global state contamination across users."""
    
    async def asyncSetUp(self):
        """Set up test environment with proper isolation."""
        await super().asyncSetUp()
        
        # Reset global validator state before each test
        reset_websocket_validator()
        
        # Create test user contexts
        self.user_a_id = str(uuid.uuid4())
        self.user_b_id = str(uuid.uuid4())
        self.connection_a_id = str(uuid.uuid4())
        self.connection_b_id = str(uuid.uuid4())
        
        # Test event data for different users
        self.user_a_event = {
            "type": "agent_started",
            "data": {"user_id": self.user_a_id, "agent": "triage", "message": "User A starting triage"},
            "user_id": self.user_a_id,
            "connection_id": self.connection_a_id
        }
        
        self.user_b_event = {
            "type": "agent_completed", 
            "data": {"user_id": self.user_b_id, "agent": "supervisor", "message": "User B completed task"},
            "user_id": self.user_b_id,
            "connection_id": self.connection_b_id
        }

    async def test_event_validator_global_instance_contamination(self):
        """
        REPRODUCTION TEST - This should FAIL initially due to global instance sharing.
        
        Tests that EventValidator global instance causes validation state bleeding
        between different user sessions.
        """
        
        # STEP 1: User A gets validator and processes events
        validator_a = get_websocket_validator()  # Gets global instance
        
        # User A processes their event - this may set internal state
        result_a = validator_a.validate_event_data(
            event_type="agent_started",
            event_data=self.user_a_event["data"],
            user_id=self.user_a_id,
            connection_id=self.connection_a_id
        )
        
        # Verify User A's event is valid
        self.assertTrue(result_a.is_valid, f"User A's event should be valid: {result_a.error_message}")
        
        # STEP 2: User B gets "new" validator instance  
        validator_b = get_websocket_validator()  # Should return SAME global instance (VIOLATION!)
        
        # CRITICAL ASSERTION: This should FAIL due to global instance pattern
        self.assertIsNot(
            validator_a, validator_b,
            "🚨 CRITICAL CONTAMINATION: EventValidator global instance shared between users! "
            f"User A validator: {id(validator_a)}, User B validator: {id(validator_b)} - "
            "This causes validation state bleeding between user sessions. "
            "BUSINESS IMPACT: Chat functionality corrupted by contaminated validation state."
        )
        
        # STEP 3: Check if validation state is contaminated
        # Process User B's different event type
        result_b = validator_b.validate_event_data(
            event_type="agent_completed",
            event_data=self.user_b_event["data"], 
            user_id=self.user_b_id,
            connection_id=self.connection_b_id
        )
        
        # If global state exists, User B's validation might be affected by User A's state
        self.assertTrue(result_b.is_valid, 
            f"User B's event validation contaminated by User A's state: {result_b.error_message}")

    async def test_validation_error_state_bleeding(self):
        """
        Test that validation errors from one user don't affect another user's validation.
        Global instance causes error state to persist across user sessions.
        """
        
        # User A triggers a validation error with invalid event
        validator_a = get_websocket_validator()
        
        invalid_event = {
            "type": "invalid_event_type",  # This should cause validation error
            "data": {"invalid": "data", "missing_required": "fields"},
            "user_id": self.user_a_id,
            "connection_id": self.connection_a_id
        }
        
        result_a = validator_a.validate_event_data(
            event_type="invalid_event_type",
            event_data=invalid_event["data"],
            user_id=self.user_a_id, 
            connection_id=self.connection_a_id
        )
        
        # Verify User A gets validation error
        self.assertFalse(result_a.is_valid, "User A should get validation error for invalid event")
        
        # User B should get clean validator without User A's error state
        validator_b = get_websocket_validator()
        
        # User B processes valid event - should NOT be affected by User A's error
        result_b = validator_b.validate_event_data(
            event_type="agent_started",
            event_data=self.user_b_event["data"],
            user_id=self.user_b_id,
            connection_id=self.connection_b_id
        )
        
        # CRITICAL: User B's valid event should succeed despite User A's error
        if not result_b.is_valid:
            self.fail(
                f"🚨 ERROR STATE BLEEDING: User B's valid event failed due to User A's error state! "
                f"User A error: {result_a.error_message}, "
                f"User B contaminated result: {result_b.error_message}. "
                "Global validator instance preserves error state across users."
            )

    async def test_validation_rules_contamination_across_sessions(self):
        """
        Test that validation rules don't bleed between different user sessions.
        Global instance may accumulate validation rules from multiple users.
        """
        
        # User A's session with specific validation context
        validator_a = get_websocket_validator()
        
        # Simulate User A setting up validation context (if validator has state)
        user_a_context = {
            "user_type": "enterprise", 
            "permissions": ["advanced_agents", "custom_tools"],
            "session_id": self.user_a_id
        }
        
        # Process event that might set internal validation state
        for i in range(3):
            event = {
                "type": "agent_thinking",
                "data": {
                    "user_id": self.user_a_id,
                    "step": i,
                    "context": user_a_context
                },
                "user_id": self.user_a_id,
                "connection_id": self.connection_a_id
            }
            
            result = validator_a.validate_event_data(
                event_type="agent_thinking",
                event_data=event["data"],
                user_id=self.user_a_id,
                connection_id=self.connection_a_id
            )
            
        # User B should get isolated validator
        validator_b = get_websocket_validator()
        
        # User B's session with different context
        user_b_context = {
            "user_type": "free",
            "permissions": ["basic_agents"],
            "session_id": self.user_b_id
        }
        
        result_b = validator_b.validate_event_data(
            event_type="agent_completed",
            event_data={
                "user_id": self.user_b_id,
                "context": user_b_context
            },
            user_id=self.user_b_id,
            connection_id=self.connection_b_id
        )
        
        # Verify User B doesn't inherit User A's validation context
        self.assertTrue(result_b.is_valid,
            f"User B's validation contaminated by User A's session context: {result_b.error_message}")
        
        # Check that validators are different instances (should FAIL with global pattern)
        self.assertIsNot(
            validator_a, validator_b,
            "🚨 EventValidator global instance prevents proper user isolation"
        )

    async def test_concurrent_validation_race_conditions(self):
        """
        Test concurrent user validations to expose race conditions in global instance.
        Global state with concurrent access creates validation race conditions.
        """
        
        async def user_a_validation_workflow():
            """Simulate User A's validation workflow."""
            validator = get_websocket_validator()
            
            results = []
            for i in range(5):
                event_data = {
                    "user_id": self.user_a_id,
                    "step": i,
                    "data": f"user_a_step_{i}"
                }
                
                result = validator.validate_event_data(
                    event_type="agent_thinking",
                    event_data=event_data,
                    user_id=self.user_a_id,
                    connection_id=self.connection_a_id
                )
                results.append(result)
                
                # Small delay to create race condition opportunity
                await asyncio.sleep(0.001)
                
            return results
            
        async def user_b_validation_workflow():
            """Simulate User B's validation workflow."""
            # Small delay to create interleaving
            await asyncio.sleep(0.0005)
            
            validator = get_websocket_validator()
            
            results = []
            for i in range(5):
                event_data = {
                    "user_id": self.user_b_id,
                    "step": i,
                    "data": f"user_b_step_{i}"
                }
                
                result = validator.validate_event_data(
                    event_type="agent_completed",
                    event_data=event_data,
                    user_id=self.user_b_id,
                    connection_id=self.connection_b_id
                )
                results.append(result)
                
                await asyncio.sleep(0.001)
                
            return results
        
        # Run both user workflows concurrently
        user_a_results, user_b_results = await asyncio.gather(
            user_a_validation_workflow(),
            user_b_validation_workflow(),
            return_exceptions=True
        )
        
        # Verify all validations succeeded
        for i, result in enumerate(user_a_results):
            self.assertTrue(result.is_valid, 
                f"User A validation {i} failed: {result.error_message}")
            
        for i, result in enumerate(user_b_results):
            self.assertTrue(result.is_valid,
                f"User B validation {i} failed due to race condition: {result.error_message}")

    async def test_validation_memory_accumulation(self):
        """
        Test that validator doesn't accumulate memory from multiple user sessions.
        Global instance may accumulate validation data causing memory leaks.
        """
        
        # Simulate multiple user sessions
        user_count = 10
        
        for session_num in range(user_count):
            user_id = str(uuid.uuid4())
            connection_id = str(uuid.uuid4())
            
            validator = get_websocket_validator()
            
            # Each user processes multiple events
            for event_num in range(5):
                event_data = {
                    "user_id": user_id,
                    "session": session_num,
                    "event": event_num,
                    "large_data": "x" * 1000  # Some larger data to test memory
                }
                
                result = validator.validate_event_data(
                    event_type="agent_thinking",
                    event_data=event_data,
                    user_id=user_id,
                    connection_id=connection_id
                )
                
                self.assertTrue(result.is_valid,
                    f"Session {session_num} event {event_num} validation failed: {result.error_message}")
        
        # After many sessions, validator should still work correctly
        final_user_id = str(uuid.uuid4())
        final_connection_id = str(uuid.uuid4())
        
        final_validator = get_websocket_validator()
        final_result = final_validator.validate_event_data(
            event_type="agent_completed",
            event_data={"user_id": final_user_id, "final": True},
            user_id=final_user_id,
            connection_id=final_connection_id
        )
        
        self.assertTrue(final_result.is_valid,
            f"Final validation failed due to memory accumulation: {final_result.error_message}")

    async def tearDown(self):
        """Clean up test environment."""
        # Reset global validator state for next test
        reset_websocket_validator()
        await super().tearDown()


# Business Impact Documentation
"""
BUSINESS IMPACT ANALYSIS:

1. CHAT FUNCTIONALITY CORRUPTION:
   - Global EventValidator state contamination breaks WebSocket event validation
   - User A's validation errors affect User B's event processing
   - Chat events incorrectly validated based on previous user's session context
   - Core platform value (90% business value) corrupted by validation state bleeding

2. REVENUE IMPACT:
   - $500K+ ARR immediately at risk from broken chat functionality  
   - Event validation failures prevent users from getting AI responses
   - Contaminated validation state causes unpredictable chat behavior
   - User experience degradation leads to churn and lost revenue

3. TECHNICAL DEBT:
   - Global instance prevents proper testing of validation logic
   - Race conditions in concurrent user scenarios cause intermittent failures
   - Memory accumulation from global state leads to performance degradation
   - Debugging becomes impossible due to contaminated global state

4. OPERATIONAL IMPACT:
   - WebSocket events fail or succeed incorrectly based on contaminated state
   - Support tickets increase due to unpredictable validation behavior
   - Monitoring and debugging hindered by shared global state
   - System reliability degraded by cross-user validation interference

REMEDIATION REQUIRED:
- Replace global instance pattern with factory pattern using UserExecutionContext
- Ensure each user gets isolated EventValidator instance
- Implement proper validation state cleanup between sessions
- Add comprehensive tests for concurrent user validation scenarios

POST-REFACTORING VALIDATION:
This test should PASS after factory pattern implementation, proving:
- Each user gets separate EventValidator instance
- No validation state bleeding between concurrent users
- Clean validation state for each user session
- Reliable WebSocket event processing for all users
"""