"""
Golden Path Integration Tests - Issue #186 WebSocket Manager SSOT Consolidation

Tests that FAIL initially to prove manager fragmentation breaks end-to-end chat functionality.
After SSOT consolidation, these tests should PASS, proving Golden Path chat works correctly.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise)
- Business Goal: Restore $500K+ ARR chat functionality disrupted by manager fragmentation
- Value Impact: Ensure complete user login → AI response workflow works reliably
- Revenue Impact: Protect primary revenue stream from WebSocket manager inconsistencies

SSOT Violations This Module Proves:
1. Different managers break user flow continuity
2. WebSocket event delivery inconsistency between manager types
3. Multi-user isolation failures due to shared manager state
4. Error recovery inconsistency across different manager implementations

Golden Path Critical Requirements:
- User login and authentication works
- WebSocket connection established successfully  
- All 5 critical events sent (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- AI agent responses delivered to user
- Multi-user isolation maintained
"""

import asyncio
import time
import unittest
from typing import Any, Dict, List, Optional, Set
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
import json

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class MockWebSocketConnection:
    """Mock WebSocket for testing without real WebSocket infrastructure."""
    user_id: str
    connection_id: str
    messages_sent: List[Dict[str, Any]]
    is_closed: bool = False
    
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Mock send_json that records messages."""
        if not self.is_closed:
            self.messages_sent.append(data)
    
    def close(self) -> None:
        """Mock close that marks connection as closed."""
        self.is_closed = True


class TestWebSocketManagerGoldenPathIntegration(unittest.TestCase):
    """
    Integration tests to prove WebSocket manager consolidation violations break Golden Path.
    
    These tests are designed to FAIL initially, proving manager fragmentation breaks chat.
    After SSOT consolidation, they should PASS, proving Golden Path works end-to-end.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        import uuid
        self.test_user_id = str(uuid.uuid4())
        self.test_connection_id = str(uuid.uuid4())
        self.mock_websocket = MockWebSocketConnection(
            user_id=self.test_user_id,
            connection_id=self.test_connection_id,
            messages_sent=[]
        )

    def test_user_login_to_chat_response_flow(self):
        """
        Test complete golden path with consolidated manager.
        
        EXPECTED INITIAL STATE: FAIL - Different managers break user flow continuity
        EXPECTED POST-SSOT STATE: PASS - Single manager enables seamless user flow
        
        VIOLATION BEING PROVED: Manager fragmentation breaks complete user workflow
        """
        golden_path_violations = []
        
        try:
            # Step 1: Create WebSocket manager (this should work)
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            
            factory = WebSocketManagerFactory()
            
            # Step 2: Attempt to create isolated manager for user (this should fail)
            try:
                manager = factory.create_isolated_manager(
                    user_id=self.test_user_id,
                    connection_id=self.test_connection_id
                )
                golden_path_violations.append("Manager creation unexpectedly succeeded")
                
                # Step 3: Add WebSocket connection (if manager creation succeeded)
                try:
                    if hasattr(manager, 'add_connection'):
                        # Import WebSocketConnection for proper object creation
                        from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
                        from datetime import datetime
                        
                        # Create proper WebSocketConnection object
                        ws_connection = WebSocketConnection(
                            connection_id=self.test_connection_id,
                            user_id=self.test_user_id,
                            websocket=self.mock_websocket,
                            connected_at=datetime.now(),
                            metadata={}
                        )
                        
                        import asyncio
                        asyncio.run(manager.add_connection(ws_connection))
                        # Note: add_connection doesn't return bool, it returns None on success
                        golden_path_violations.append("Connection addition succeeded unexpectedly")
                    else:
                        golden_path_violations.append("Manager missing add_connection method")
                        
                except Exception as e:
                    golden_path_violations.append(f"Connection addition error: {e}")
                
                # Step 4: Test message sending
                try:
                    if hasattr(manager, 'send_message'):
                        test_message = {"type": "agent_request", "content": "test message"}
                        result = manager.send_message(self.test_user_id, test_message)
                        if not result:
                            golden_path_violations.append("Message sending failed")
                    else:
                        golden_path_violations.append("Manager missing send_message method")
                        
                except Exception as e:
                    golden_path_violations.append(f"Message sending error: {e}")
                    
            except Exception as e:
                if "create_isolated_manager failed" in str(e):
                    golden_path_violations.append(
                        f"EXPECTED FAILURE: Manager creation failed due to SSOT violations: {e}"
                    )
                else:
                    golden_path_violations.append(f"Unexpected manager creation error: {e}")

        except ImportError:
            golden_path_violations.append("WebSocketManagerFactory not available")
        except Exception as e:
            golden_path_violations.append(f"Golden path test setup failed: {e}")

        # Test with alternative manager if factory fails
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            
            # This should also fail due to constructor issues
            try:
                direct_manager = UnifiedWebSocketManager()
                
                # Try to use direct manager
                if hasattr(direct_manager, 'add_connection'):
                    # This may work differently than factory-created manager
                    pass
                else:
                    golden_path_violations.append("Direct manager missing required methods")
                    
            except Exception as e:
                golden_path_violations.append(f"Direct manager instantiation failed: {e}")
                
        except ImportError:
            golden_path_violations.append("UnifiedWebSocketManager not available")

        # ASSERTION THAT SHOULD FAIL INITIALLY: Complete Golden Path should work
        self.assertEqual(
            len(golden_path_violations), 0,
            f"SSOT VIOLATION: Golden Path workflow broken: {golden_path_violations}. "
            f"This proves manager fragmentation disrupts end-to-end user chat functionality."
        )

    def test_websocket_event_delivery_consistency(self):
        """
        Test all 5 critical events delivered with any manager.
        
        EXPECTED INITIAL STATE: FAIL - Different managers send different events
        EXPECTED POST-SSOT STATE: PASS - All managers send identical event sequences
        
        VIOLATION BEING PROVED: Event delivery inconsistency between manager types
        """
        event_violations = []
        required_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        # Test event delivery with different managers
        managers_to_test = []
        
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            factory = WebSocketManagerFactory()
            managers_to_test.append(('Factory-created', factory, True))  # Factory pattern
        except ImportError:
            pass
        except Exception as e:
            event_violations.append(f"Factory manager unavailable: {e}")
            
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            direct_manager = UnifiedWebSocketManager()
            managers_to_test.append(('Direct-created', direct_manager, False))  # Direct instantiation
        except Exception as e:
            event_violations.append(f"Direct manager unavailable: {e}")

        # Test each manager's event delivery capability
        manager_event_patterns = {}
        
        for manager_name, manager, is_factory in managers_to_test:
            try:
                events_sent = []
                
                if is_factory:
                    # Factory pattern - try to create manager first
                    try:
                        actual_manager = manager.create_isolated_manager(
                            user_id=self.test_user_id,
                            connection_id=self.test_connection_id
                        )
                        
                        # Test event sending methods
                        for event_type in required_events:
                            if hasattr(actual_manager, 'send_agent_event'):
                                try:
                                    result = actual_manager.send_agent_event(
                                        user_id=self.test_user_id,
                                        event_type=event_type,
                                        data={"test": "data"}
                                    )
                                    if result:
                                        events_sent.append(event_type)
                                except Exception as e:
                                    event_violations.append(f"{manager_name} event {event_type} failed: {e}")
                            else:
                                event_violations.append(f"{manager_name} missing send_agent_event method")
                                
                    except Exception as e:
                        event_violations.append(f"{manager_name} manager creation failed: {e}")
                        
                else:
                    # Direct manager - test event methods directly
                    for event_type in required_events:
                        if hasattr(manager, 'send_agent_event'):
                            try:
                                # Mock add connection first
                                if hasattr(manager, 'add_connection'):
                                    # Try proper WebSocketConnection object
                                    try:
                                        from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
                                        from datetime import datetime
                                        import asyncio
                                        
                                        ws_connection = WebSocketConnection(
                                            connection_id=self.test_connection_id,
                                            user_id=self.test_user_id,
                                            websocket=self.mock_websocket,
                                            connected_at=datetime.now(),
                                            metadata={}
                                        )
                                        asyncio.run(manager.add_connection(ws_connection))
                                    except Exception as e:
                                        event_violations.append(f"{manager_name} connection failed: {e}")
                                
                                # Now try sending event
                                result = manager.send_agent_event(
                                    user_id=self.test_user_id,
                                    event_type=event_type, 
                                    data={"test": "data"}
                                )
                                events_sent.append(event_type)
                                
                            except Exception as e:
                                event_violations.append(f"{manager_name} event {event_type} failed: {e}")
                        else:
                            event_violations.append(f"{manager_name} missing send_agent_event method")
                
                manager_event_patterns[manager_name] = events_sent
                
            except Exception as e:
                event_violations.append(f"{manager_name} event delivery test failed: {e}")

        # Compare event patterns between managers
        if len(manager_event_patterns) > 1:
            pattern_keys = list(manager_event_patterns.keys())
            base_pattern = manager_event_patterns[pattern_keys[0]]
            
            for other_manager in pattern_keys[1:]:
                other_pattern = manager_event_patterns[other_manager]
                
                if base_pattern != other_pattern:
                    event_violations.append(
                        f"Event pattern mismatch: {pattern_keys[0]} sends {base_pattern}, "
                        f"{other_manager} sends {other_pattern}"
                    )

        # Check if any manager sends all required events
        complete_event_managers = []
        for manager_name, events in manager_event_patterns.items():
            if len(events) == len(required_events):
                complete_event_managers.append(manager_name)
        
        if len(complete_event_managers) == 0:
            event_violations.append(
                f"No manager sends all required events. Patterns: {manager_event_patterns}"
            )

        # ASSERTION THAT SHOULD FAIL INITIALLY: Event delivery should be consistent
        self.assertEqual(
            len(event_violations), 0,
            f"SSOT VIOLATION: WebSocket event delivery inconsistencies: {event_violations}. "
            f"Event patterns: {manager_event_patterns}. "
            f"This proves managers do not consistently deliver critical WebSocket events."
        )

    def test_multi_user_manager_isolation(self):
        """
        Test multiple users get properly isolated managers.
        
        EXPECTED INITIAL STATE: FAIL - Shared state between different manager types
        EXPECTED POST-SSOT STATE: PASS - Perfect isolation between all user contexts
        
        VIOLATION BEING PROVED: Multi-user isolation failures causing data leakage
        """
        isolation_violations = []
        
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            
            factory = WebSocketManagerFactory()
            
            # Create managers for different users
            import uuid
            user_managers = {}
            test_users = [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]
            
            for user_id in test_users:
                try:
                    manager = factory.create_isolated_manager(
                        user_id=user_id,
                        connection_id=f"conn_{user_id}"
                    )
                    user_managers[user_id] = manager
                except Exception as e:
                    isolation_violations.append(f"Manager creation failed for {user_id}: {e}")

            # Test isolation between managers
            if len(user_managers) >= 2:
                user_ids = list(user_managers.keys())
                manager1 = user_managers[user_ids[0]]
                manager2 = user_managers[user_ids[1]]
                
                # Test if managers are different instances
                if manager1 is manager2:
                    isolation_violations.append("Managers are same instance - no isolation")
                
                # Test state isolation (if managers were created)
                try:
                    # Check if managers have isolated user contexts
                    if hasattr(manager1, '_user_id') and hasattr(manager2, '_user_id'):
                        if getattr(manager1, '_user_id') == getattr(manager2, '_user_id'):
                            isolation_violations.append("Managers share same user_id - state not isolated")
                    
                    # Test connection isolation
                    mock_ws1 = MockWebSocketConnection(user_ids[0], f"conn_{user_ids[0]}", [])
                    mock_ws2 = MockWebSocketConnection(user_ids[1], f"conn_{user_ids[1]}", [])
                    
                    if hasattr(manager1, 'add_connection'):
                        try:
                            from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
                            from datetime import datetime
                            import asyncio
                            
                            # Create proper WebSocketConnection objects
                            ws_connection1 = WebSocketConnection(
                                connection_id=f"conn_{user_ids[0]}",
                                user_id=user_ids[0],
                                websocket=mock_ws1,
                                connected_at=datetime.now(),
                                metadata={}
                            )
                            ws_connection2 = WebSocketConnection(
                                connection_id=f"conn_{user_ids[1]}",
                                user_id=user_ids[1],
                                websocket=mock_ws2,
                                connected_at=datetime.now(),
                                metadata={}
                            )
                            
                            asyncio.run(manager1.add_connection(ws_connection1))
                            asyncio.run(manager2.add_connection(ws_connection2))
                            
                            # Test that messages don't cross-contaminate
                            if hasattr(manager1, 'send_message'):
                                manager1.send_message(user_ids[0], {"type": "test", "user": user_ids[0]})
                                manager2.send_message(user_ids[1], {"type": "test", "user": user_ids[1]})
                                
                                # Check if messages went to correct connections
                                user1_messages = [msg for msg in mock_ws1.messages_sent if msg.get('user') == user_ids[0]]
                                user2_messages = [msg for msg in mock_ws2.messages_sent if msg.get('user') == user_ids[1]]
                                
                                if len(user1_messages) == 0:
                                    isolation_violations.append(f"User1 manager didn't send to user1 connection")
                                if len(user2_messages) == 0:
                                    isolation_violations.append(f"User2 manager didn't send to user2 connection")
                                
                                # Check for cross-contamination
                                user1_wrong_messages = [msg for msg in mock_ws1.messages_sent if msg.get('user') != user_ids[0]]
                                user2_wrong_messages = [msg for msg in mock_ws2.messages_sent if msg.get('user') != user_ids[1]]
                                
                                if user1_wrong_messages:
                                    isolation_violations.append(f"User1 connection received wrong messages: {user1_wrong_messages}")
                                if user2_wrong_messages:
                                    isolation_violations.append(f"User2 connection received wrong messages: {user2_wrong_messages}")
                                    
                        except Exception as e:
                            isolation_violations.append(f"Connection isolation test failed: {e}")
                            
                except Exception as e:
                    isolation_violations.append(f"State isolation test failed: {e}")
                    
            else:
                isolation_violations.append(f"Could not create multiple managers for isolation testing")

        except ImportError:
            isolation_violations.append("WebSocketManagerFactory not available for isolation testing")
        except Exception as e:
            isolation_violations.append(f"Multi-user isolation test setup failed: {e}")

        # ASSERTION THAT SHOULD FAIL INITIALLY: Multi-user isolation should work perfectly
        self.assertEqual(
            len(isolation_violations), 0,
            f"SSOT VIOLATION: Multi-user isolation failures: {isolation_violations}. "
            f"This proves manager fragmentation causes user state leakage and cross-contamination."
        )

    def test_manager_error_recovery_consistency(self):
        """
        Test error recovery works consistently across all managers.
        
        EXPECTED INITIAL STATE: FAIL - Different error handling patterns
        EXPECTED POST-SSOT STATE: PASS - Consistent error recovery across all managers
        
        VIOLATION BEING PROVED: Error recovery inconsistency causing unpredictable failures
        """
        error_recovery_violations = []
        
        # Test error scenarios across different managers
        managers_to_test = []
        
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            factory = WebSocketManagerFactory()
            managers_to_test.append(('Factory', factory, True))
        except ImportError:
            pass
        except Exception as e:
            error_recovery_violations.append(f"Factory manager unavailable: {e}")
            
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            direct_manager = UnifiedWebSocketManager()
            managers_to_test.append(('Direct', direct_manager, False))
        except Exception as e:
            error_recovery_violations.append(f"Direct manager unavailable: {e}")

        # Test error recovery patterns
        error_scenarios = [
            ("invalid_user_id", lambda mgr: mgr.send_message(None, {"test": "msg"}) if hasattr(mgr, 'send_message') else None),
            ("empty_message", lambda mgr: mgr.send_message("valid_user", {}) if hasattr(mgr, 'send_message') else None),
            ("connection_failure", lambda mgr: mgr.add_connection("user", None) if hasattr(mgr, 'add_connection') else None),
        ]
        
        error_handling_patterns = {}
        
        for manager_name, manager, is_factory in managers_to_test:
            pattern = {}
            
            try:
                # Get actual manager instance
                if is_factory:
                    try:
                        actual_manager = manager.create_isolated_manager(
                            user_id="error_test_user",
                            connection_id="error_test_conn"
                        )
                    except Exception as e:
                        error_recovery_violations.append(f"{manager_name} manager creation for error test failed: {e}")
                        continue
                else:
                    actual_manager = manager
                
                # Test each error scenario
                for scenario_name, error_func in error_scenarios:
                    try:
                        result = error_func(actual_manager)
                        pattern[scenario_name] = f"no_exception:{result}"
                    except ValueError as e:
                        pattern[scenario_name] = f"ValueError:{type(e).__name__}"
                    except TypeError as e:
                        pattern[scenario_name] = f"TypeError:{type(e).__name__}"
                    except AttributeError as e:
                        pattern[scenario_name] = f"AttributeError:method_missing"
                    except Exception as e:
                        pattern[scenario_name] = f"OtherException:{type(e).__name__}"
                
                error_handling_patterns[manager_name] = pattern
                
            except Exception as e:
                error_recovery_violations.append(f"{manager_name} error recovery test failed: {e}")

        # Compare error handling patterns
        if len(error_handling_patterns) > 1:
            pattern_keys = list(error_handling_patterns.keys())
            base_pattern = error_handling_patterns[pattern_keys[0]]
            
            for other_manager in pattern_keys[1:]:
                other_pattern = error_handling_patterns[other_manager]
                
                for scenario in error_scenarios:
                    scenario_name = scenario[0]
                    if scenario_name in base_pattern and scenario_name in other_pattern:
                        if base_pattern[scenario_name] != other_pattern[scenario_name]:
                            error_recovery_violations.append(
                                f"Error handling mismatch for {scenario_name}: "
                                f"{pattern_keys[0]} -> {base_pattern[scenario_name]}, "
                                f"{other_manager} -> {other_pattern[scenario_name]}"
                            )

        # ASSERTION THAT SHOULD FAIL INITIALLY: Error recovery should be consistent
        self.assertEqual(
            len(error_recovery_violations), 0,
            f"SSOT VIOLATION: Error recovery inconsistencies: {error_recovery_violations}. "
            f"Error patterns: {error_handling_patterns}. "
            f"This proves managers do not have consistent error handling and recovery patterns."
        )


if __name__ == '__main__':
    import unittest
    unittest.main()