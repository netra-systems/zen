
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
Golden Path Failure Tests - Issue #186 WebSocket Manager Fragmentation

Tests that prove the Golden Path (user login → AI response) fails due to WebSocket manager
fragmentation and SSOT violations. These tests are designed to FAIL initially, proving
that the core business value delivery mechanism is broken.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise)
- Business Goal: Revenue Protection - Prove $500K+ ARR chat functionality is compromised
- Value Impact: Demonstrate that WebSocket fragmentation breaks end-to-end user experience
- Revenue Impact: Enable systematic fix to restore core platform value delivery

SSOT Violations This Module Proves:
1. Login → AI response flow failure without authentication bypass
2. WebSocket event delivery inconsistency between manager implementations  
3. Multi-user isolation failure causing cross-user contamination
4. Agent execution pipeline breaks due to manager interface mismatches
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import asyncio
import json
import uuid
import unittest
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
from datetime import datetime

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class MockWebSocketConnection:
    """Mock WebSocket connection for testing"""
    user_id: str
    connection_id: str
    is_active: bool = True
    messages_sent: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.messages_sent is None:
            self.messages_sent = []
    
    async def send_text(self, message: str):
        """Simulate sending text message"""
        try:
            data = json.loads(message)
            self.messages_sent.append(data)
        except json.JSONDecodeError:
            self.messages_sent.append({"raw_text": message})
    
    async def close(self):
        """Simulate connection close"""
        self.is_active = False


class TestWebSocketManagerGoldenPathFailures(SSotAsyncTestCase):
    """
    Tests to prove Golden Path failures due to WebSocket manager SSOT violations.
    
    These tests are designed to FAIL initially, proving business impact.
    After SSOT consolidation, they should PASS, proving value restoration.
    """

    async def test_user_login_to_chat_response_flow_failure(self):
        """
        Test complete golden path with consolidated manager fails due to fragmentation.
        
        EXPECTED INITIAL STATE: FAIL - Different managers break user flow continuity
        EXPECTED POST-SSOT STATE: PASS - Single manager enables seamless flow
        
        VIOLATION BEING PROVED: Manager fragmentation breaks end-to-end user experience
        """
        golden_path_violations = []
        
        # Simulate Golden Path flow
        test_user_id = str(uuid.uuid4())
        test_connection_id = str(uuid.uuid4())
        
        try:
            # Step 1: User Authentication (should create WebSocket context)
            try:
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                
                user_context = UserExecutionContext.from_websocket_request(
                    user_id=test_user_id,
                    websocket_client_id=test_connection_id,
                    operation="golden_path_test"
                )
                
                # Step 2: WebSocket Manager Setup (this is where fragmentation causes issues)
                managers_created = []
                
                # Test different manager creation patterns that should be equivalent
                try:
                    # Pattern 1: Factory creation
                    from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
                    factory = WebSocketManagerFactory()
                    
                    if hasattr(factory, 'create_isolated_manager'):
                        factory_manager = factory.create_isolated_manager(test_user_id, test_connection_id)
                        managers_created.append(('factory', factory_manager))
                        
                except Exception as e:
                    golden_path_violations.append(f"Factory manager creation failed: {e}")
                
                try:
                    # Pattern 2: Direct instantiation
                    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
                    direct_manager = UnifiedWebSocketManager()
                    managers_created.append(('direct', direct_manager))
                    
                except Exception as e:
                    golden_path_violations.append(f"Direct manager creation failed: {e}")
                
                # Step 3: Test Manager Equivalency (should be interchangeable)
                if len(managers_created) >= 2:
                    factory_manager = None
                    direct_manager = None
                    
                    for pattern, manager in managers_created:
                        if pattern == 'factory':
                            factory_manager = manager
                        elif pattern == 'direct':
                            direct_manager = manager
                    
                    if factory_manager is not None and direct_manager is not None:
                        # Test if both managers can handle same operations
                        mock_connection = MockWebSocketConnection(test_user_id, test_connection_id)
                        
                        # Test 1: Add connection capability
                        try:
                            if hasattr(factory_manager, 'add_connection'):
                                await factory_manager.add_connection(mock_connection)
                            else:
                                golden_path_violations.append(
                                    "Factory manager missing add_connection method"
                                )
                                
                            if hasattr(direct_manager, 'add_connection'):
                                await direct_manager.add_connection(mock_connection)
                            else:
                                golden_path_violations.append(
                                    "Direct manager missing add_connection method"
                                )
                                
                        except Exception as e:
                            golden_path_violations.append(f"Connection addition failed: {e}")
                        
                        # Test 2: Event sending capability (CRITICAL for Golden Path)
                        event_test_data = {
                            "event_type": "agent_started",
                            "data": {"agent_id": "test_agent", "user_id": test_user_id}
                        }
                        
                        factory_event_success = False
                        direct_event_success = False
                        
                        try:
                            if hasattr(factory_manager, 'send_event'):
                                result = await factory_manager.send_event(
                                    event_test_data["event_type"], 
                                    event_test_data["data"]
                                )
                                factory_event_success = bool(result)
                            else:
                                golden_path_violations.append(
                                    "Factory manager missing send_event method - breaks Golden Path"
                                )
                        except Exception as e:
                            golden_path_violations.append(f"Factory manager send_event failed: {e}")
                        
                        try:
                            if hasattr(direct_manager, 'send_event'):
                                result = await direct_manager.send_event(
                                    event_test_data["event_type"],
                                    event_test_data["data"] 
                                )
                                direct_event_success = bool(result)
                            else:
                                golden_path_violations.append(
                                    "Direct manager missing send_event method - breaks Golden Path"
                                )
                        except Exception as e:
                            golden_path_violations.append(f"Direct manager send_event failed: {e}")
                        
                        # Test 3: Event delivery consistency
                        if factory_event_success != direct_event_success:
                            golden_path_violations.append(
                                f"Event delivery inconsistency: factory={factory_event_success}, "
                                f"direct={direct_event_success}. This breaks Golden Path reliability."
                            )
                            
                # Step 4: Agent Execution Integration (requires working WebSocket events)
                try:
                    # Test if managers can integrate with agent execution
                    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
                    
                    if managers_created:
                        test_manager = managers_created[0][1]  # Use first available manager
                        
                        # Test agent registry integration
                        registry = AgentRegistry()
                        
                        # Try to set WebSocket manager (should work with any manager)
                        if hasattr(registry, 'set_websocket_manager'):
                            try:
                                registry.set_websocket_manager(test_manager)
                                
                                # Test if agent execution can send events through manager
                                if hasattr(registry, 'notify_agent_started'):
                                    try:
                                        await registry.notify_agent_started(
                                            user_id=test_user_id,
                                            agent_id="test_agent",
                                            thread_id=str(uuid.uuid4())
                                        )
                                    except Exception as e:
                                        golden_path_violations.append(
                                            f"Agent notification through manager failed: {e}"
                                        )
                                        
                            except Exception as e:
                                golden_path_violations.append(
                                    f"Agent registry manager integration failed: {e}"
                                )
                        else:
                            golden_path_violations.append(
                                "Agent registry missing WebSocket manager integration"
                            )
                            
                except ImportError:
                    golden_path_violations.append(
                        "Agent registry not available for Golden Path testing"
                    )
                except Exception as e:
                    golden_path_violations.append(f"Agent integration testing failed: {e}")
                
            except Exception as e:
                golden_path_violations.append(f"User context creation failed: {e}")
                
        except Exception as e:
            golden_path_violations.append(f"Golden Path test setup failed: {e}")
        
        # ASSERTION THAT SHOULD FAIL INITIALLY: Golden Path should work end-to-end
        self.assertEqual(
            len(golden_path_violations), 0,
            f"SSOT VIOLATION: Golden Path failures due to manager fragmentation: {golden_path_violations}. "
            f"This proves WebSocket manager SSOT violations break core business value delivery."
        )

    async def test_websocket_event_delivery_inconsistency(self):
        """
        Test that WebSocket event delivery is inconsistent between manager implementations.
        
        EXPECTED INITIAL STATE: FAIL - Different managers deliver events differently
        EXPECTED POST-SSOT STATE: PASS - All managers deliver events consistently
        
        VIOLATION BEING PROVED: Event delivery inconsistency breaks real-time user experience
        """
        event_delivery_violations = []
        
        # Test event delivery across different manager implementations
        test_user_id = str(uuid.uuid4())
        test_connection_id = str(uuid.uuid4())
        
        # Critical Golden Path events that must be delivered
        critical_events = [
            {"type": "agent_started", "data": {"agent_id": "test_agent"}},
            {"type": "agent_thinking", "data": {"thought": "Processing request"}},
            {"type": "tool_executing", "data": {"tool": "search", "query": "test"}},
            {"type": "tool_completed", "data": {"tool": "search", "results": []}},
            {"type": "agent_completed", "data": {"response": "Test response"}}
        ]
        
        managers_to_test = []
        
        # Get different manager implementations
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            factory = WebSocketManagerFactory()
            if hasattr(factory, 'create_isolated_manager'):
                try:
                    factory_manager = factory.create_isolated_manager(test_user_id, test_connection_id)
                    managers_to_test.append(('factory', factory_manager))
                except Exception as e:
                    event_delivery_violations.append(f"Factory manager creation failed: {e}")
        except ImportError:
            pass
        
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            direct_manager = UnifiedWebSocketManager()
            managers_to_test.append(('direct', direct_manager))
        except ImportError:
            pass
        
        # Test event delivery for each manager
        manager_event_results = {}
        
        for manager_name, manager in managers_to_test:
            mock_connection = MockWebSocketConnection(test_user_id, test_connection_id)
            event_results = []
            
            # Add connection if possible
            try:
                if hasattr(manager, 'add_connection'):
                    await manager.add_connection(mock_connection)
            except Exception as e:
                event_delivery_violations.append(
                    f"Manager {manager_name} connection addition failed: {e}"
                )
                continue
            
            # Test each critical event
            for event in critical_events:
                try:
                    if hasattr(manager, 'send_event'):
                        result = await manager.send_event(event["type"], event["data"])
                        event_results.append({
                            "event": event["type"],
                            "success": bool(result),
                            "messages_sent": len(mock_connection.messages_sent)
                        })
                    else:
                        event_results.append({
                            "event": event["type"],
                            "success": False,
                            "error": "send_event method not available"
                        })
                except Exception as e:
                    event_results.append({
                        "event": event["type"],
                        "success": False,
                        "error": str(e)
                    })
            
            manager_event_results[manager_name] = event_results
        
        # Compare event delivery across managers
        if len(manager_event_results) > 1:
            manager_names = list(manager_event_results.keys())
            
            for event in critical_events:
                event_type = event["type"]
                manager_results = {}
                
                for manager_name in manager_names:
                    for result in manager_event_results[manager_name]:
                        if result["event"] == event_type:
                            manager_results[manager_name] = result
                            break
                
                # Check for delivery consistency
                if len(manager_results) > 1:
                    success_values = [result["success"] for result in manager_results.values()]
                    unique_success = set(success_values)
                    
                    if len(unique_success) > 1:
                        event_delivery_violations.append(
                            f"Event {event_type} delivery inconsistency: {manager_results}. "
                            f"This breaks Golden Path event reliability."
                        )
                        
                    # Check message delivery consistency
                    message_counts = {}
                    for manager_name, result in manager_results.items():
                        if "messages_sent" in result:
                            message_counts[manager_name] = result["messages_sent"]
                    
                    if message_counts:
                        unique_counts = set(message_counts.values())
                        if len(unique_counts) > 1:
                            event_delivery_violations.append(
                                f"Event {event_type} message count inconsistency: {message_counts}"
                            )
        
        # ASSERTION THAT SHOULD FAIL INITIALLY: Event delivery should be consistent
        self.assertEqual(
            len(event_delivery_violations), 0,
            f"SSOT VIOLATION: WebSocket event delivery inconsistencies: {event_delivery_violations}. "
            f"Manager results: {manager_event_results}. "
            f"This proves manager fragmentation breaks real-time user experience."
        )

    async def test_multi_user_isolation_failure(self):
        """
        Test that multi-user isolation fails due to manager state sharing.
        
        EXPECTED INITIAL STATE: FAIL - Managers share state between users
        EXPECTED POST-SSOT STATE: PASS - Each user has isolated manager state
        
        VIOLATION BEING PROVED: Manager state sharing causes cross-user contamination
        """
        isolation_violations = []
        
        # Create two different users
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())
        connection1_id = str(uuid.uuid4())
        connection2_id = str(uuid.uuid4())
        
        try:
            # Test factory isolation
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            factory = WebSocketManagerFactory()
            
            if hasattr(factory, 'create_isolated_manager'):
                try:
                    # Create managers for two different users
                    manager1 = factory.create_isolated_manager(user1_id, connection1_id)
                    manager2 = factory.create_isolated_manager(user2_id, connection2_id)
                    
                    # Test isolation by checking if managers are truly separate
                    if manager1 is manager2:
                        isolation_violations.append(
                            "Factory returns same manager instance for different users"
                        )
                    
                    # Test state isolation
                    if hasattr(manager1, '_user_context') and hasattr(manager2, '_user_context'):
                        if (hasattr(manager1._user_context, 'user_id') and 
                            hasattr(manager2._user_context, 'user_id')):
                            
                            if manager1._user_context.user_id == manager2._user_context.user_id:
                                isolation_violations.append(
                                    f"Managers share same user context: {manager1._user_context.user_id}"
                                )
                    
                    # Test connection isolation
                    mock_conn1 = MockWebSocketConnection(user1_id, connection1_id)
                    mock_conn2 = MockWebSocketConnection(user2_id, connection2_id)
                    
                    # Add connections to respective managers
                    if hasattr(manager1, 'add_connection') and hasattr(manager2, 'add_connection'):
                        await manager1.add_connection(mock_conn1)
                        await manager2.add_connection(mock_conn2)
                        
                        # Send events to each user
                        if (hasattr(manager1, 'send_event') and hasattr(manager2, 'send_event')):
                            
                            await manager1.send_event("test_event", {"user": user1_id, "data": "user1_data"})
                            await manager2.send_event("test_event", {"user": user2_id, "data": "user2_data"})
                            
                            # Check if messages were delivered to correct users only
                            user1_messages = mock_conn1.messages_sent
                            user2_messages = mock_conn2.messages_sent
                            
                            # Check for cross-contamination
                            for msg in user1_messages:
                                if isinstance(msg, dict) and "user" in msg:
                                    if msg["user"] != user1_id:
                                        isolation_violations.append(
                                            f"User1 received message for different user: {msg}"
                                        )
                            
                            for msg in user2_messages:
                                if isinstance(msg, dict) and "user" in msg:
                                    if msg["user"] != user2_id:
                                        isolation_violations.append(
                                            f"User2 received message for different user: {msg}"
                                        )
                            
                            # Check if both users received their own messages
                            user1_got_message = any(
                                isinstance(msg, dict) and msg.get("user") == user1_id 
                                for msg in user1_messages
                            )
                            user2_got_message = any(
                                isinstance(msg, dict) and msg.get("user") == user2_id
                                for msg in user2_messages
                            )
                            
                            if not user1_got_message:
                                isolation_violations.append("User1 did not receive their own message")
                            if not user2_got_message:
                                isolation_violations.append("User2 did not receive their own message")
                                
                except Exception as e:
                    isolation_violations.append(f"Multi-user isolation testing failed: {e}")
                    
        except ImportError:
            isolation_violations.append("WebSocket factory not available for isolation testing")
        except Exception as e:
            isolation_violations.append(f"Isolation test setup failed: {e}")
        
        # ASSERTION THAT SHOULD FAIL INITIALLY: Users should be properly isolated
        self.assertEqual(
            len(isolation_violations), 0,
            f"SSOT VIOLATION: Multi-user isolation failures: {isolation_violations}. "
            f"This proves manager state sharing causes cross-user contamination security risk."
        )

    async def test_agent_execution_pipeline_breaks(self):
        """
        Test that agent execution pipeline breaks due to manager interface mismatches.
        
        EXPECTED INITIAL STATE: FAIL - Pipeline breaks due to interface incompatibility
        EXPECTED POST-SSOT STATE: PASS - Pipeline works with standardized interfaces
        
        VIOLATION BEING PROVED: Manager interface mismatches break agent-to-user communication
        """
        pipeline_violations = []
        
        test_user_id = str(uuid.uuid4())
        test_connection_id = str(uuid.uuid4())
        test_thread_id = str(uuid.uuid4())
        
        try:
            # Test agent execution component integration
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            
            # Create manager for testing
            manager = None
            try:
                from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
                factory = WebSocketManagerFactory()
                if hasattr(factory, 'create_isolated_manager'):
                    manager = factory.create_isolated_manager(test_user_id, test_connection_id)
            except Exception as e:
                pipeline_violations.append(f"Manager creation for pipeline testing failed: {e}")
            
            if manager is not None:
                # Test agent registry integration
                registry = AgentRegistry()
                
                # Test WebSocket manager setting
                if hasattr(registry, 'set_websocket_manager'):
                    try:
                        registry.set_websocket_manager(manager)
                    except Exception as e:
                        pipeline_violations.append(f"Agent registry manager integration failed: {e}")
                else:
                    pipeline_violations.append("Agent registry missing WebSocket manager integration")
                
                # Test agent execution notifications
                notification_methods = [
                    'notify_agent_started',
                    'notify_agent_thinking', 
                    'notify_tool_executing',
                    'notify_tool_completed',
                    'notify_agent_completed'
                ]
                
                for method_name in notification_methods:
                    if hasattr(registry, method_name):
                        try:
                            method = getattr(registry, method_name)
                            
                            # Test method signature compatibility
                            import inspect
                            sig = inspect.signature(method)
                            params = list(sig.parameters.keys())
                            
                            # Check if method expects user_id parameter (required for isolation)
                            if 'user_id' not in params:
                                pipeline_violations.append(
                                    f"Agent notification method {method_name} missing user_id parameter: {params}"
                                )
                            
                            # Test actual notification (with mock data)
                            try:
                                if method_name == 'notify_agent_started':
                                    await method(
                                        user_id=test_user_id,
                                        agent_id="test_agent",
                                        thread_id=test_thread_id
                                    )
                                elif method_name == 'notify_agent_thinking':
                                    await method(
                                        user_id=test_user_id,
                                        thought="Test thinking",
                                        thread_id=test_thread_id
                                    )
                                elif method_name == 'notify_tool_executing':
                                    await method(
                                        user_id=test_user_id,
                                        tool_name="test_tool",
                                        thread_id=test_thread_id
                                    )
                                elif method_name == 'notify_tool_completed':
                                    await method(
                                        user_id=test_user_id,
                                        tool_name="test_tool",
                                        result={},
                                        thread_id=test_thread_id
                                    )
                                elif method_name == 'notify_agent_completed':
                                    await method(
                                        user_id=test_user_id,
                                        response="Test response",
                                        thread_id=test_thread_id
                                    )
                                    
                            except Exception as e:
                                pipeline_violations.append(
                                    f"Agent notification {method_name} execution failed: {e}"
                                )
                                
                        except Exception as e:
                            pipeline_violations.append(
                                f"Agent notification method {method_name} analysis failed: {e}"
                            )
                    else:
                        pipeline_violations.append(
                            f"Agent registry missing {method_name} method for Golden Path"
                        )
                        
        except ImportError:
            pipeline_violations.append("Agent execution components not available for pipeline testing")
        except Exception as e:
            pipeline_violations.append(f"Agent pipeline testing failed: {e}")
        
        # ASSERTION THAT SHOULD FAIL INITIALLY: Agent execution pipeline should work
        self.assertEqual(
            len(pipeline_violations), 0,
            f"SSOT VIOLATION: Agent execution pipeline failures: {pipeline_violations}. "
            f"This proves manager interface mismatches break agent-to-user communication."
        )


# Helper function to run async tests
def run_async_test(test_method):
    """Helper to run async test methods"""
    async def wrapper(self):
        await test_method(self)
    return wrapper


# Apply async wrapper to async test methods
TestWebSocketManagerGoldenPathFailures.test_websocket_event_delivery_inconsistency = run_async_test(
    TestWebSocketManagerGoldenPathFailures.test_websocket_event_delivery_inconsistency
)

TestWebSocketManagerGoldenPathFailures.test_multi_user_isolation_failure = run_async_test(
    TestWebSocketManagerGoldenPathFailures.test_multi_user_isolation_failure
)

TestWebSocketManagerGoldenPathFailures.test_user_login_to_chat_response_flow_failure = run_async_test(
    TestWebSocketManagerGoldenPathFailures.test_user_login_to_chat_response_flow_failure
)

TestWebSocketManagerGoldenPathFailures.test_agent_execution_pipeline_breaks = run_async_test(
    TestWebSocketManagerGoldenPathFailures.test_agent_execution_pipeline_breaks
)


if __name__ == '__main__':
    unittest.main()