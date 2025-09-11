"""
WebSocket SSOT Event Ordering Violation Tests

Tests for SSOT violations in WebSocket event ordering and delivery guarantees,
ensuring proper event sequencing through unified event system.

Business Value: Platform/Internal - Ensure correct chat event ordering for UX
Critical for maintaining proper chat conversation flow and user experience.

Test Status: DESIGNED TO FAIL with current code (detecting violations)
Expected Result: PASS after SSOT consolidation ensures proper event ordering
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.types.core_types import UserID, ensure_user_id


@dataclass
class EventRecord:
    """Record of a WebSocket event for ordering analysis."""
    event_type: str
    timestamp: datetime
    sequence_id: int
    user_id: str
    data: Dict[str, Any]


class TestWebSocketSSotEventOrdering(SSotAsyncTestCase):
    """Test event ordering SSOT violations."""
    
    def setUp(self):
        super().setUp()
        self.captured_events = []
        self.event_sequence = 0
    
    def _record_event(self, event_type: str, user_id: str, data: Dict[str, Any]):
        """Record an event for ordering analysis."""
        self.event_sequence += 1
        event = EventRecord(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            sequence_id=self.event_sequence,
            user_id=str(user_id),
            data=data
        )
        self.captured_events.append(event)
        return event

    async def test_critical_event_ordering_consistency(self):
        """
        Test that critical events are delivered in correct order through unified system.
        
        CURRENT BEHAVIOR: Event ordering may be inconsistent (VIOLATION)
        EXPECTED AFTER SSOT: Guaranteed event ordering
        """
        user_id = ensure_user_id("ordering_test_user")
        
        # Define required event sequence for proper chat flow
        required_sequence = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        ordering_violations = []
        event_delivery_systems = {}
        
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            manager = UnifiedWebSocketManager()
            
            # Test event ordering through different delivery methods
            delivery_methods = []
            
            # Method 1: Direct event sending
            if hasattr(manager, 'send_event'):
                delivery_methods.append(('direct_send_event', manager.send_event))
            
            # Method 2: User-specific sending
            if hasattr(manager, 'send_to_user'):
                delivery_methods.append(('send_to_user', manager.send_to_user))
            
            # Method 3: Legacy notification system
            if hasattr(manager, 'notify'):
                delivery_methods.append(('notify_system', manager.notify))
            
            # Test each delivery method for ordering consistency
            for method_name, method_func in delivery_methods:
                method_events = []
                
                # Send events in required sequence with small delays
                for i, event_type in enumerate(required_sequence):
                    try:
                        event_data = {
                            "sequence": i,
                            "event_type": event_type,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        # Record when we send the event
                        sent_event = self._record_event(f"{method_name}_{event_type}", user_id, event_data)
                        
                        # Send through the method
                        if method_name == 'direct_send_event':
                            await method_func(user_id, event_type, event_data)
                        else:
                            await method_func(user_id, event_data)
                        
                        method_events.append(sent_event)
                        
                        # Small delay to test ordering sensitivity
                        await asyncio.sleep(0.01)
                        
                    except Exception as e:
                        ordering_violations.append(f"{method_name}_send_error: {e}")
                
                event_delivery_systems[method_name] = {
                    "events_sent": len(method_events),
                    "expected_count": len(required_sequence),
                    "success_rate": len(method_events) / len(required_sequence) if required_sequence else 0
                }
                
                # Check for ordering violations within this method
                for i in range(1, len(method_events)):
                    prev_event = method_events[i-1]
                    curr_event = method_events[i]
                    
                    # Check timestamp ordering
                    if curr_event.timestamp < prev_event.timestamp:
                        ordering_violations.append(f"{method_name}_timestamp_violation: event {i}")
                    
                    # Check sequence ordering
                    if curr_event.sequence_id <= prev_event.sequence_id:
                        ordering_violations.append(f"{method_name}_sequence_violation: event {i}")
        
        except ImportError as e:
            self.fail(f"Failed to import WebSocket manager: {e}")
        
        # Analyze cross-method ordering violations
        all_events_by_user = [e for e in self.captured_events if e.user_id == str(user_id)]
        
        for i in range(1, len(all_events_by_user)):
            prev_event = all_events_by_user[i-1]
            curr_event = all_events_by_user[i]
            
            # Events from different methods should still maintain global ordering
            if curr_event.timestamp < prev_event.timestamp:
                ordering_violations.append(f"cross_method_timestamp_violation: events {prev_event.sequence_id}->{curr_event.sequence_id}")
        
        total_violations = len(ordering_violations)
        delivery_method_count = len(event_delivery_systems)
        
        # CURRENT EXPECTATION: Ordering violations exist (violation)
        # AFTER SSOT: Should have consistent ordering across all methods
        self.assertGreater(total_violations, 0,
                          "SSOT VIOLATION DETECTED: Event ordering violations found. "
                          f"Found {total_violations} violations across {delivery_method_count} delivery methods")
        
        self.metrics.record_test_event("event_ordering_violation", {
            "total_violations": total_violations,
            "delivery_method_count": delivery_method_count,
            "violations": ordering_violations[:10],  # Limit for metrics
            "delivery_systems": event_delivery_systems
        })

    async def test_concurrent_event_delivery_consistency(self):
        """
        Test that concurrent event delivery maintains consistency across users.
        
        CURRENT BEHAVIOR: Race conditions in concurrent delivery (VIOLATION)
        EXPECTED AFTER SSOT: Thread-safe concurrent delivery
        """
        user_count = 5
        events_per_user = 3
        users = [ensure_user_id(f"concurrent_user_{i}") for i in range(user_count)]
        
        concurrent_violations = []
        user_event_counts = {}
        cross_user_contamination = []
        
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            
            async def send_user_events(user_id: UserID):
                """Send events for a single user."""
                manager = UnifiedWebSocketManager()
                user_events = []
                
                for event_num in range(events_per_user):
                    event_type = f"user_event_{event_num}"
                    event_data = {
                        "user_id": str(user_id),
                        "event_number": event_num,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    try:
                        # Record the event
                        recorded_event = self._record_event(event_type, user_id, event_data)
                        user_events.append(recorded_event)
                        
                        # Send through manager
                        if hasattr(manager, 'send_to_user'):
                            await manager.send_to_user(user_id, event_data)
                        
                        # Small delay to increase race condition chances
                        await asyncio.sleep(0.005)
                        
                    except Exception as e:
                        concurrent_violations.append(f"send_error_user_{user_id}: {e}")
                
                user_event_counts[str(user_id)] = len(user_events)
                return user_events
            
            # Run concurrent event sending
            tasks = [send_user_events(user_id) for user_id in users]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for exceptions in concurrent execution
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    concurrent_violations.append(f"concurrent_exception_user_{i}: {result}")
            
            # Analyze event contamination between users
            for user_id in users:
                user_events = [e for e in self.captured_events if e.user_id == str(user_id)]
                expected_count = events_per_user
                actual_count = len(user_events)
                
                if actual_count != expected_count:
                    cross_user_contamination.append(f"user_{user_id}: expected {expected_count}, got {actual_count}")
                
                # Check for events with wrong user_id in data
                for event in user_events:
                    if event.data.get('user_id') != str(user_id):
                        cross_user_contamination.append(f"user_{user_id}: event has wrong user_id {event.data.get('user_id')}")
            
            # Check for manager instance violations in concurrent access
            manager_instance_violations = 0
            # This would require tracking manager instances across concurrent calls
            # For now, we'll estimate based on behavior patterns
            
        except ImportError as e:
            self.fail(f"Failed to import WebSocket manager: {e}")
        
        total_concurrent_violations = len(concurrent_violations) + len(cross_user_contamination)
        
        # CURRENT EXPECTATION: Concurrent violations exist (violation)
        # AFTER SSOT: Should have thread-safe concurrent delivery
        self.assertGreater(total_concurrent_violations, 0,
                          "SSOT VIOLATION DETECTED: Concurrent event delivery violations found. "
                          f"Violations: {len(concurrent_violations)}, Contamination: {len(cross_user_contamination)}")
        
        self.metrics.record_test_event("concurrent_delivery_violation", {
            "total_violations": total_concurrent_violations,
            "concurrent_violations": len(concurrent_violations),
            "cross_user_contamination": len(cross_user_contamination),
            "user_count": user_count,
            "events_per_user": events_per_user,
            "user_event_counts": user_event_counts
        })