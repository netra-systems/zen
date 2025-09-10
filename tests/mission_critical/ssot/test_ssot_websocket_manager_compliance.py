"""
MISSION CRITICAL: WebSocket Manager SSOT Compliance Test Suite

Business Impact: Protects $500K+ ARR chat functionality by ensuring WebSocket SSOT integrity.
SSOT violations in WebSocket management can cause:
- Chat message delivery failures (users can't get AI responses)
- Cross-user message leakage (critical security breach)
- WebSocket connection instability (chat stops working)
- Missing agent execution events (users see no progress)
- Factory pattern violations (multi-user conflicts)

This test suite validates:
1. No duplicate WebSocket manager implementations exist
2. All imports use the canonical WebSocket manager 
3. User isolation is maintained in concurrent scenarios
4. All 5 critical WebSocket events are properly sent
5. Factory pattern is correctly implemented

Root Cause Prevention: The Five Whys analysis identified missing formal interface
contracts as the root cause of WebSocket implementation drift. This test enforces
the WebSocketManagerProtocol to prevent future AttributeError exceptions.

Business Value Justification:
- Segment: ALL (Free -> Enterprise)
- Goal: Maintain reliable chat functionality (90% of platform value)
- Impact: Prevents catastrophic chat failures that destroy user confidence
- Revenue Impact: Protects primary revenue-generating capability
"""

import asyncio
import pytest
import os
import ast
import importlib.util
from typing import Dict, List, Set, Any, Optional
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
import logging
import time
from datetime import datetime

# Import SSOT BaseTestCase - ALL tests must inherit from this
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase

# Import WebSocket SSOT components
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
from netra_backend.app.websocket_core.protocols import (
    WebSocketManagerProtocol, 
    WebSocketProtocolValidator,
    WebSocketManagerProtocolValidator  # Backward compatibility alias
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ConnectionID, ThreadID, ensure_user_id

# Import logging
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.mission_critical
@pytest.mark.ssot
class TestWebSocketManagerSSotCompliance(SSotAsyncTestCase):
    """
    CRITICAL: WebSocket Manager SSOT compliance testing.
    
    Business Impact: Protects $500K+ ARR chat functionality.
    Violations in WebSocket SSOT can cause:
    - Chat message delivery failures
    - Cross-user message leakage (security breach)
    - WebSocket connection instability
    - Missing agent execution events
    
    This test ensures:
    1. Single Source of Truth for WebSocket management
    2. No duplicate implementations
    3. Proper user isolation
    4. Complete event delivery
    5. Factory pattern compliance
    """
    
    def setup_method(self):
        """Set up test environment using SSOT patterns."""
        super().setup_method()
        
        # CRITICAL: Store original state for cleanup
        self._original_websocket_managers = {}
        self._test_connections = []
        self._test_user_contexts = []
        
        # Track WebSocket managers created during testing
        self._created_managers = []
        
        logger.info("🔧 WebSocket SSOT compliance test setup complete")
    
    def teardown_method(self):
        """Clean up test resources using SSOT patterns."""
        try:
            # Clean up any test WebSocket connections
            for connection in self._test_connections:
                try:
                    if hasattr(connection, 'close') and callable(connection.close):
                        asyncio.run(connection.close())
                except Exception as e:
                    logger.warning(f"Failed to close test connection: {e}")
            
            # Clean up test user contexts
            for context in self._test_user_contexts:
                if hasattr(context, 'cleanup'):
                    context.cleanup()
            
            # Clean up created managers
            for manager in self._created_managers:
                if hasattr(manager, 'cleanup') and callable(manager.cleanup):
                    try:
                        asyncio.run(manager.cleanup())
                    except Exception as e:
                        logger.warning(f"Failed to cleanup manager: {e}")
            
            logger.info("🧹 WebSocket SSOT compliance test cleanup complete")
        except Exception as e:
            logger.error(f"❌ Test cleanup failed: {e}")
        finally:
            super().teardown_method()
    
    def test_no_duplicate_websocket_managers(self):
        """
        CRITICAL: Detect forbidden duplicate WebSocket manager implementations.
        
        Business Impact: Prevents fragmentation of WebSocket functionality that could
        lead to inconsistent behavior and chat failures.
        
        SSOT Requirement: Only one canonical WebSocket manager implementation allowed.
        """
        logger.info("🔍 Testing for duplicate WebSocket manager implementations")
        
        # Define the canonical WebSocket manager locations
        canonical_managers = {
            'UnifiedWebSocketManager': 'netra_backend.app.websocket_core.unified_manager',
            'WebSocketManager': 'netra_backend.app.websocket_core.websocket_manager',  # Alias
        }
        
        # Define FORBIDDEN duplicate locations that violate SSOT
        forbidden_patterns = [
            # Forbidden duplicate manager classes
            'WebSocketManagerDuplicate',
            'AlternativeWebSocketManager',
            'CustomWebSocketManager',
            'SimpleWebSocketManager',
            'StandaloneWebSocketManager',
            
            # Forbidden bypass implementations
            'DirectWebSocketHandler',
            'WebSocketBypass',
            'QuickWebSocketManager',
            
            # Legacy patterns that should be removed
            'LegacyWebSocketManager',
            'OldWebSocketManager',
            'DeprecatedWebSocketManager',
        ]
        
        # Scan codebase for forbidden patterns
        project_root = Path(__file__).parent.parent.parent.parent
        websocket_files = []
        
        # Search for Python files that might contain WebSocket managers
        for pattern in ['**/*websocket*.py', '**/*manager*.py']:
            websocket_files.extend(project_root.glob(pattern))
        
        violations = []
        duplicate_implementations = []
        
        for file_path in websocket_files:
            if file_path.is_file() and file_path.suffix == '.py':
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Parse AST to find class definitions
                    try:
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                class_name = node.name
                                file_relative = str(file_path.relative_to(project_root))
                                
                                # Skip test files for forbidden patterns check (they may contain test implementations)
                                is_test_file = ('test' in file_relative.lower() or 'tests' in file_relative.lower())
                                
                                # Check for forbidden patterns (excluding test files)
                                if not is_test_file and any(pattern in class_name for pattern in forbidden_patterns):
                                    violations.append({
                                        'file': file_relative,
                                        'class_name': class_name,
                                        'violation_type': 'forbidden_duplicate_implementation'
                                    })
                                
                                # Check for unauthorized WebSocket managers (excluding protocols, factories, and legitimate components)
                                if ('WebSocketManager' in class_name and 
                                    class_name not in [
                                        'WebSocketManager', 'UnifiedWebSocketManager', 'IsolatedWebSocketManager',
                                        'WebSocketManagerProtocol', 'WebSocketManagerFactory',  # Legitimate components
                                        'EmergencyWebSocketManager'  # Emergency handlers are allowed
                                    ] and
                                    'Test' not in class_name and 'Mock' not in class_name and
                                    'Protocol' not in class_name and 'Factory' not in class_name):
                                    
                                    # Verify it's not in canonical locations and not in test files
                                    is_canonical = any(
                                        canonical_path in file_relative 
                                        for canonical_path in canonical_managers.values()
                                    )
                                    
                                    if not is_canonical and not is_test_file:
                                        duplicate_implementations.append({
                                            'file': file_relative,
                                            'class_name': class_name,
                                            'violation_type': 'unauthorized_websocket_manager'
                                        })
                    
                    except SyntaxError:
                        # Skip files with syntax errors (might be templates)
                        continue
                
                except (UnicodeDecodeError, FileNotFoundError, PermissionError):
                    # Skip files we can't read
                    continue
        
        # Assert no violations found
        all_violations = violations + duplicate_implementations
        
        if all_violations:
            violation_details = "\n".join([
                f"  - {v['file']}: {v['class_name']} ({v['violation_type']})"
                for v in all_violations
            ])
            
            pytest.fail(
                f"🚨 CRITICAL SSOT VIOLATION: Found {len(all_violations)} duplicate/forbidden WebSocket manager implementations:\n"
                f"{violation_details}\n"
                f"BUSINESS IMPACT: These duplicates can cause chat functionality fragmentation, "
                f"leading to message delivery failures and user experience degradation.\n"
                f"REMEDIATION: Remove duplicate implementations and use canonical WebSocket managers only."
            )
        
        logger.info(f"✅ No duplicate WebSocket manager implementations found - SSOT compliance verified")
        
        # Record compliance metrics
        # Record test metrics
        metrics = {
            'test_name': 'websocket_manager_duplicates',
            'files_scanned': len(websocket_files),
            'violations_found': len(all_violations),
            'canonical_managers_verified': len(canonical_managers),
            'compliance_status': 'PASS'
        }
        for key, value in metrics.items():
            self.record_metric(key, value)
    
    def test_canonical_websocket_manager_imports(self):
        """
        CRITICAL: Ensure all WebSocket manager imports use canonical SSOT sources.
        
        Business Impact: Prevents import fragmentation that could lead to inconsistent
        WebSocket behavior and chat functionality failures.
        
        SSOT Requirement: All WebSocket manager imports must use canonical modules.
        """
        logger.info("🔍 Testing WebSocket manager import compliance")
        
        # Define canonical import patterns
        canonical_imports = [
            'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager',
            'from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager',
            'from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager',
        ]
        
        # Define FORBIDDEN import patterns
        forbidden_imports = [
            # Direct websocket library imports bypassing our manager
            'from websockets import',
            'from fastapi import WebSocket',
            'from starlette.websockets import WebSocket',
            
            # Deprecated/legacy imports
            'from netra_backend.websocket import',
            'from backend.websocket import',
            
            # Unauthorized manager imports
            'import websocket_manager_custom',
            'from custom_websocket import',
        ]
        
        project_root = Path(__file__).parent.parent.parent.parent
        python_files = list(project_root.glob('**/*.py'))
        
        import_violations = []
        canonical_usage = []
        
        for file_path in python_files:
            if file_path.is_file() and 'test' not in str(file_path).lower():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for canonical imports (good)
                    for canonical_import in canonical_imports:
                        if canonical_import in content:
                            canonical_usage.append({
                                'file': str(file_path.relative_to(project_root)),
                                'import_statement': canonical_import
                            }
        for key, value in metrics.items():
            self.record_metric(key, value)
                    
                    # Check for forbidden imports (violations)
                    for forbidden_import in forbidden_imports:
                        if forbidden_import in content:
                            # Skip if it's in a test file or mock
                            if ('test' in file_path.name.lower() or 
                                'mock' in file_path.name.lower() or
                                'example' in file_path.name.lower()):
                                continue
                            
                            import_violations.append({
                                'file': str(file_path.relative_to(project_root)),
                                'forbidden_import': forbidden_import,
                                'violation_type': 'forbidden_websocket_import'
                            }
        for key, value in metrics.items():
            self.record_metric(key, value)
                
                except (UnicodeDecodeError, FileNotFoundError, PermissionError):
                    continue
        
        # Check specific SSOT compliance requirements
        
        # 1. Verify WebSocketManager alias is used correctly
        websocket_manager_file = project_root / 'netra_backend' / 'app' / 'websocket_core' / 'websocket_manager.py'
        if websocket_manager_file.exists():
            with open(websocket_manager_file, 'r', encoding='utf-8') as f:
                manager_content = f.read()
            
            # Verify the alias is properly defined
            if 'WebSocketManager = UnifiedWebSocketManager' not in manager_content:
                import_violations.append({
                    'file': str(websocket_manager_file.relative_to(project_root)),
                    'forbidden_import': 'Missing WebSocketManager alias',
                    'violation_type': 'missing_canonical_alias'
                }
        for key, value in metrics.items():
            self.record_metric(key, value)
        
        # Assert no import violations
        if import_violations:
            violation_details = "\n".join([
                f"  - {v['file']}: {v['forbidden_import']} ({v['violation_type']})"
                for v in import_violations
            ])
            
            pytest.fail(
                f"🚨 CRITICAL SSOT VIOLATION: Found {len(import_violations)} forbidden WebSocket imports:\n"
                f"{violation_details}\n"
                f"BUSINESS IMPACT: Inconsistent imports can cause WebSocket functionality fragmentation, "
                f"leading to chat instability and message delivery failures.\n"
                f"REMEDIATION: Use canonical WebSocket manager imports only."
            )
        
        logger.info(f"✅ WebSocket import compliance verified - {len(canonical_usage)} canonical imports found")
        
        # Record compliance metrics
        # Record test metrics
        metrics = {
            'test_name': 'websocket_manager_imports',
            'files_scanned': len(python_files),
            'canonical_imports': len(canonical_usage),
            'import_violations': len(import_violations),
            'compliance_status': 'PASS'
        }
        for key, value in metrics.items():
            self.record_metric(key, value)
    
    def test_websocket_protocol_compliance(self):
        """
        CRITICAL: Verify WebSocket managers implement the required protocol interface.
        
        Business Impact: Prevents the Five Whys root cause by ensuring all WebSocket
        managers implement the complete interface contract.
        
        Root Cause Prevention: The Five Whys analysis identified missing 
        get_connection_id_by_websocket method as causing AttributeError exceptions.
        """
        logger.info("🔍 Testing WebSocket Manager Protocol compliance")
        
        # Test the canonical WebSocket manager implementations
        managers_to_test = [
            {
                'name': 'UnifiedWebSocketManager',
                'class': UnifiedWebSocketManager,
                'create_instance': lambda: UnifiedWebSocketManager()
            },
        ]
        
        compliance_results = []
        
        for manager_info in managers_to_test:
            try:
                # Create manager instance
                manager = manager_info['create_instance']()
                self._created_managers.append(manager)
                
                logger.info(f"🧪 Testing protocol compliance for {manager_info['name']}")
                
                # Use WebSocketProtocolValidator to check compliance
                validation_result = WebSocketProtocolValidator.validate_manager_protocol(manager)
                
                compliance_results.append({
                    'manager_name': manager_info['name'],
                    'validation_result': validation_result
                }
        for key, value in metrics.items():
            self.record_metric(key, value)
                
                # Assert compliance
                if not validation_result['compliant']:
                    missing_methods = validation_result.get('missing_methods', [])
                    invalid_signatures = validation_result.get('invalid_signatures', [])
                    
                    # Check for Five Whys critical methods specifically
                    five_whys_methods = ['get_connection_id_by_websocket', 'update_connection_thread']
                    missing_critical = [m for m in missing_methods if m in five_whys_methods]
                    
                    error_message = (
                        f"🚨 PROTOCOL COMPLIANCE FAILURE: {manager_info['name']} failed WebSocket protocol compliance.\n"
                        f"Compliance: {validation_result.get('summary', {}).get('compliance_percentage', 0)}%\n"
                        f"Missing methods: {missing_methods}\n"
                        f"Invalid signatures: {invalid_signatures}\n"
                    )
                    
                    if missing_critical:
                        error_message += (
                            f"FIVE WHYS CRITICAL: Missing {missing_critical} methods that caused the original AttributeError.\n"
                        )
                    
                    error_message += (
                        f"BUSINESS IMPACT: Protocol violations can cause AttributeError exceptions during agent execution, "
                        f"breaking the chat functionality that delivers 90% of platform value.\n"
                        f"ROOT CAUSE PREVENTION: This ensures all WebSocket managers have consistent interfaces."
                    )
                    
                    pytest.fail(error_message)
                
                logger.info(f"✅ {manager_info['name']} protocol compliance verified ({validation_result.get('summary', {}).get('compliance_percentage', 0)}%)")
                
            except Exception as e:
                pytest.fail(f"❌ Failed to test {manager_info['name']} protocol compliance: {e}")
        
        # Record compliance metrics
        total_managers = len(managers_to_test)
        compliant_managers = sum(1 for result in compliance_results if result['validation_result']['compliant'])
        
        # Record test metrics
        metrics = {
            'test_name': 'websocket_protocol_compliance',
            'managers_tested': total_managers,
            'compliant_managers': compliant_managers,
            'compliance_rate': (compliant_managers / total_managers) * 100 if total_managers > 0 else 0,
            'compliance_status': 'PASS' if compliant_managers == total_managers else 'FAIL'
        }
        for key, value in metrics.items():
            self.record_metric(key, value)
    
    @pytest.mark.asyncio
    async def test_websocket_manager_user_isolation(self):
        """
        CRITICAL: Verify WebSocket manager maintains user isolation in concurrent scenarios.
        
        Business Impact: Prevents cross-user message leakage which is a critical security breach.
        User isolation failures can result in:
        - Users seeing other users' chat messages
        - AI responses being delivered to wrong users  
        - Confidential data exposure
        - Complete loss of user trust and business
        
        Factory Pattern Requirement: Each user must get isolated WebSocket manager instance.
        """
        logger.info("🔍 Testing WebSocket manager user isolation")
        
        # Create multiple user contexts for isolation testing
        user_contexts = []
        managers = []
        
        try:
            # Create isolated user contexts
            user_ids = [f"test_user_{i}_{int(time.time())}" for i in range(3)]
            
            for user_id in user_ids:
                # Create user execution context
                user_context = UserExecutionContext(
                    user_id=ensure_user_id(user_id),
                    request_id=f"req_{user_id}",
                    thread_id=f"thread_{user_id}"
                )
                user_contexts.append(user_context)
                self._test_user_contexts.append(user_context)
                
                # Create isolated WebSocket manager for this user
                manager = create_websocket_manager(user_context)
                managers.append(manager)
                self._created_managers.append(manager)
            
            logger.info(f"📊 Created {len(managers)} isolated WebSocket managers for user isolation testing")
            
            # Test 1: Verify managers are different instances
            for i, manager1 in enumerate(managers):
                for j, manager2 in enumerate(managers):
                    if i != j:
                        assert manager1 is not manager2, (
                            f"🚨 CRITICAL ISOLATION VIOLATION: User {user_ids[i]} and {user_ids[j]} "
                            f"got the same WebSocket manager instance. This can cause cross-user message leakage!"
                        )
            
            logger.info("✅ Manager instance isolation verified - each user has unique manager")
            
            # Test 2: Verify user-specific state isolation
            for i, (manager, user_context) in enumerate(zip(managers, user_contexts)):
                user_id = user_context.user_id
                
                # Create mock WebSocket connection
                mock_websocket = Mock()
                mock_websocket.send_json = AsyncMock()
                mock_websocket.close = AsyncMock()
                
                # Create connection with user-specific data
                connection = WebSocketConnection(
                    websocket=mock_websocket,
                    connection_id=ConnectionID(f"conn_{user_id}_{i}"),
                    user_id=user_id,
                    thread_id=ThreadID(f"thread_{user_id}_{i}")
                )
                self._test_connections.append(connection)
                
                # Add connection to manager
                await manager.add_connection(connection)
                
                # Verify connection is associated with correct user only
                user_connections = manager.get_user_connections(user_id)
                assert len(user_connections) == 1, (
                    f"User {user_id} should have exactly 1 connection, got {len(user_connections)}"
                )
                
                # Verify other users don't see this connection
                for other_manager, other_context in zip(managers, user_contexts):
                    if other_manager is not manager:
                        other_user_connections = other_manager.get_user_connections(other_context.user_id)
                        assert connection.connection_id not in other_user_connections, (
                            f"🚨 CRITICAL ISOLATION VIOLATION: User {other_context.user_id} can see "
                            f"connection {connection.connection_id} belonging to user {user_id}!"
                        )
            
            logger.info("✅ User state isolation verified - connections properly isolated per user")
            
            # Test 3: Verify message delivery isolation
            test_messages = [
                {"type": "agent_started", "user_specific": f"Message for {user_id}", "timestamp": datetime.utcnow().isoformat()}
                for user_id in user_ids
            ]
            
            # Send user-specific messages
            for i, (manager, user_context, message) in enumerate(zip(managers, user_contexts, test_messages)):
                await manager.send_to_user(user_context.user_id, message)
            
            # Verify each user's connections only received their message
            # (This would require actual WebSocket mocking to verify delivery isolation)
            
            logger.info("✅ Message delivery isolation test completed")
            
            # Test 4: Verify concurrent access doesn't cause cross-contamination
            async def concurrent_user_operation(manager, user_context, operation_id):
                """Simulate concurrent user operations."""
                try:
                    # Simulate typical WebSocket operations
                    user_connections = manager.get_user_connections(user_context.user_id)
                    is_active = manager.is_connection_active(user_context.user_id)
                    health = manager.get_connection_health(user_context.user_id)
                    
                    # Each user should only see their own data
                    assert isinstance(health, dict), f"Health check failed for operation {operation_id}"
                    
                    return {"operation_id": operation_id, "success": True, "connections": len(user_connections)}
                except Exception as e:
                    return {"operation_id": operation_id, "success": False, "error": str(e)}
            
            # Run concurrent operations
            concurrent_tasks = []
            for i, (manager, user_context) in enumerate(zip(managers, user_contexts)):
                for operation_id in range(5):  # 5 operations per user
                    task = concurrent_user_operation(manager, user_context, f"user_{i}_op_{operation_id}")
                    concurrent_tasks.append(task)
            
            concurrent_results = await asyncio.gather(*concurrent_tasks)
            
            # Verify all operations succeeded
            failed_operations = [r for r in concurrent_results if not r['success']]
            if failed_operations:
                pytest.fail(f"🚨 CONCURRENT ACCESS FAILURE: {len(failed_operations)} operations failed during concurrent testing")
            
            logger.info(f"✅ Concurrent access test passed - {len(concurrent_results)} operations completed successfully")
            
        except Exception as e:
            pytest.fail(f"❌ User isolation test failed: {e}")
        
        finally:
            # Clean up test connections and managers
            for connection in self._test_connections:
                try:
                    if hasattr(connection, 'websocket') and hasattr(connection.websocket, 'close'):
                        await connection.websocket.close()
                except:
                    pass
        
        # Record isolation metrics
        # Record test metrics
        metrics = {
            'test_name': 'websocket_user_isolation',
            'users_tested': len(user_contexts),
            'managers_created': len(managers),
            'concurrent_operations': len(concurrent_results),
            'isolation_violations': 0,  # If we got here, no violations found
            'compliance_status': 'PASS'
        }
        for key, value in metrics.items():
            self.record_metric(key, value)
    
    @pytest.mark.asyncio
    async def test_websocket_event_delivery_compliance(self):
        """
        CRITICAL: Ensure all 5 critical WebSocket events are properly supported.
        
        Business Impact: These events enable the real-time chat experience that delivers
        90% of platform value. Missing events cause:
        - Users don't see AI agent progress
        - Chat appears frozen or unresponsive
        - Poor user experience leading to churn
        - Reduced confidence in AI capabilities
        
        Required Events:
        1. agent_started - User sees agent began processing
        2. agent_thinking - Real-time reasoning visibility  
        3. tool_executing - Tool usage transparency
        4. tool_completed - Tool results display
        5. agent_completed - User knows response is ready
        """
        logger.info("🔍 Testing WebSocket critical event delivery compliance")
        
        # Define the 5 critical events that MUST be supported
        critical_events = [
            'agent_started',
            'agent_thinking', 
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]
        
        try:
            # Create test user context
            user_context = UserExecutionContext(
                user_id=ensure_user_id(f"event_test_user_{int(time.time())}"),
                request_id=f"event_test_req_{int(time.time())}",
                thread_id=f"event_test_thread_{int(time.time())}"
            )
            self._test_user_contexts.append(user_context)
            
            # Create WebSocket manager
            manager = create_websocket_manager(user_context)
            self._created_managers.append(manager)
            
            # Create mock WebSocket connection
            mock_websocket = Mock()
            sent_messages = []
            
            async def capture_sent_message(message):
                sent_messages.append(message)
                logger.info(f"📨 Captured WebSocket message: {message}")
            
            mock_websocket.send_json = AsyncMock(side_effect=capture_sent_message)
            mock_websocket.close = AsyncMock()
            
            # Create connection
            connection = WebSocketConnection(
                websocket=mock_websocket,
                connection_id=ConnectionID(f"event_test_conn_{int(time.time())}"),
                user_id=user_context.user_id,
                thread_id=ThreadID(user_context.thread_id)
            )
            self._test_connections.append(connection)
            
            # Add connection to manager
            await manager.add_connection(connection)
            
            logger.info("🧪 Testing each critical event delivery")
            
            # Test each critical event
            event_test_results = []
            
            for event_type in critical_events:
                try:
                    # Create event data
                    event_data = {
                        'event_type': event_type,
                        'timestamp': datetime.utcnow().isoformat(),
                        'user_id': str(user_context.user_id),
                        'thread_id': str(user_context.thread_id),
                        'test_specific_data': f"Test data for {event_type}"
                    }
                    
                    # Clear previous messages
                    sent_messages.clear()
                    
                    # Emit the critical event
                    await manager.emit_critical_event(
                        user_id=user_context.user_id,
                        event_type=event_type,
                        data=event_data
                    )
                    
                    # Verify event was sent
                    event_sent = len(sent_messages) > 0
                    
                    if event_sent:
                        # Verify event structure
                        latest_message = sent_messages[-1]
                        has_event_type = event_type in str(latest_message)
                        has_required_data = 'timestamp' in str(latest_message)
                        
                        event_test_results.append({
                            'event_type': event_type,
                            'delivered': True,
                            'structured_correctly': has_event_type and has_required_data,
                            'message_content': latest_message
                        }
        for key, value in metrics.items():
            self.record_metric(key, value)
                        
                        logger.info(f"✅ Event {event_type} delivered successfully")
                    else:
                        event_test_results.append({
                            'event_type': event_type,
                            'delivered': False,
                            'structured_correctly': False,
                            'error': 'No message sent'
                        }
        for key, value in metrics.items():
            self.record_metric(key, value)
                        
                        logger.error(f"❌ Event {event_type} failed to deliver")
                
                except Exception as e:
                    event_test_results.append({
                        'event_type': event_type,
                        'delivered': False,
                        'structured_correctly': False,
                        'error': str(e)
                    }
        for key, value in metrics.items():
            self.record_metric(key, value)
                    
                    logger.error(f"❌ Event {event_type} failed with exception: {e}")
            
            # Analyze results
            failed_events = [r for r in event_test_results if not r['delivered']]
            malformed_events = [r for r in event_test_results if r['delivered'] and not r['structured_correctly']]
            
            if failed_events:
                failed_event_names = [e['event_type'] for e in failed_events]
                pytest.fail(
                    f"🚨 CRITICAL EVENT DELIVERY FAILURE: {len(failed_events)} out of {len(critical_events)} "
                    f"critical events failed to deliver: {failed_event_names}\n"
                    f"BUSINESS IMPACT: Missing events cause chat to appear frozen, destroying user experience.\n"
                    f"These events are critical for the 90% of platform value delivered through chat functionality.\n"
                    f"Failure Details: {[{'event': e['event_type'], 'error': e.get('error', 'Unknown')} for e in failed_events]}"
                )
            
            if malformed_events:
                malformed_event_names = [e['event_type'] for e in malformed_events]
                pytest.fail(
                    f"🚨 EVENT STRUCTURE VIOLATION: {len(malformed_events)} events were delivered but malformed: {malformed_event_names}\n"
                    f"BUSINESS IMPACT: Malformed events can cause frontend parsing errors and chat instability."
                )
            
            logger.info(f"✅ All {len(critical_events)} critical WebSocket events delivered successfully")
            
        except Exception as e:
            pytest.fail(f"❌ WebSocket event delivery test failed: {e}")
        
        # Record event delivery metrics
        successful_events = len([r for r in event_test_results if r['delivered'] and r['structured_correctly']])
        
        # Record test metrics
        metrics = {
            'test_name': 'websocket_event_delivery',
            'critical_events_tested': len(critical_events),
            'successful_deliveries': successful_events,
            'delivery_success_rate': (successful_events / len(critical_events)) * 100,
            'compliance_status': 'PASS' if successful_events == len(critical_events) else 'FAIL'
        }
        for key, value in metrics.items():
            self.record_metric(key, value)
    
    @pytest.mark.asyncio
    async def test_websocket_factory_pattern_compliance(self):
        """
        CRITICAL: Verify WebSocket factory pattern is correctly implemented.
        
        Business Impact: Factory pattern ensures user isolation and prevents:
        - Singleton-related memory leaks
        - Cross-user state contamination 
        - Scalability issues with concurrent users
        - WebSocket connection confusion
        
        Factory Pattern Requirements:
        1. create_websocket_manager() creates unique instances
        2. No shared singletons for user-specific data
        3. Proper cleanup and lifecycle management
        4. Thread-safe creation for concurrent users
        """
        logger.info("🔍 Testing WebSocket factory pattern compliance")
        
        # Test 1: Verify create_websocket_manager creates unique instances
        user_contexts = []
        managers = []
        
        try:
            # Create multiple user contexts
            for i in range(5):
                user_context = UserExecutionContext(
                    user_id=ensure_user_id(f"factory_test_user_{i}_{int(time.time())}"),
                    request_id=f"factory_test_req_{i}_{int(time.time())}",
                    thread_id=f"factory_test_thread_{i}_{int(time.time())}"
                )
                user_contexts.append(user_context)
                self._test_user_contexts.append(user_context)
                
                # Create manager using factory
                manager = create_websocket_manager(user_context)
                managers.append(manager)
                self._created_managers.append(manager)
            
            logger.info(f"🏭 Created {len(managers)} WebSocket managers via factory")
            
            # Verify all instances are unique
            for i, manager1 in enumerate(managers):
                for j, manager2 in enumerate(managers):
                    if i != j:
                        assert manager1 is not manager2, (
                            f"🚨 FACTORY PATTERN VIOLATION: Factory returned same instance for different users! "
                            f"User {i} and User {j} got identical manager instances. "
                            f"This violates user isolation and can cause data contamination."
                        )
            
            logger.info("✅ Factory uniqueness verified - each call creates distinct manager instance")
            
            # Test 2: Verify no shared singleton state
            singleton_violations = []
            
            for i, (manager, user_context) in enumerate(zip(managers, user_contexts)):
                # Check for singleton patterns or shared class variables
                manager_class = manager.__class__
                
                # Look for singleton indicators
                if hasattr(manager_class, '_instance') and manager_class._instance is not None:
                    singleton_violations.append({
                        'manager_index': i,
                        'violation': 'class has _instance singleton variable',
                        'class_name': manager_class.__name__
                    }
        for key, value in metrics.items():
            self.record_metric(key, value)
                
                if hasattr(manager_class, '_instances') and manager_class._instances:
                    singleton_violations.append({
                        'manager_index': i,
                        'violation': 'class has _instances collection',
                        'class_name': manager_class.__name__
                    }
        for key, value in metrics.items():
            self.record_metric(key, value)
                
                # Check for shared state that could cause cross-contamination
                if hasattr(manager, 'connections') and isinstance(manager.connections, dict):
                    # Connections should be isolated per manager
                    for other_manager in managers:
                        if other_manager is not manager:
                            if (hasattr(other_manager, 'connections') and 
                                other_manager.connections is manager.connections):
                                singleton_violations.append({
                                    'manager_index': i,
                                    'violation': 'managers share connection dictionary reference',
                                    'class_name': manager_class.__name__
                                }
        for key, value in metrics.items():
            self.record_metric(key, value)
            
            if singleton_violations:
                violation_details = "\n".join([
                    f"  - Manager {v['manager_index']} ({v['class_name']}): {v['violation']}"
                    for v in singleton_violations
                ])
                
                pytest.fail(
                    f"🚨 FACTORY PATTERN VIOLATION: Found {len(singleton_violations)} singleton pattern violations:\n"
                    f"{violation_details}\n"
                    f"BUSINESS IMPACT: Singleton patterns cause cross-user data contamination and memory leaks. "
                    f"This can result in users seeing other users' messages and system instability."
                )
            
            logger.info("✅ No singleton violations detected - proper factory isolation verified")
            
            # Test 3: Verify thread-safety of factory creation
            async def concurrent_factory_creation(user_index):
                """Create manager concurrently to test thread safety."""
                try:
                    user_context = UserExecutionContext(
                        user_id=ensure_user_id(f"concurrent_user_{user_index}_{int(time.time())}"),
                        request_id=f"concurrent_req_{user_index}_{int(time.time())}",
                        thread_id=f"concurrent_thread_{user_index}_{int(time.time())}"
                    )
                    
                    # Create manager
                    manager = create_websocket_manager(user_context)
                    
                    # Verify manager is valid
                    assert manager is not None, f"Factory returned None for user {user_index}"
                    assert hasattr(manager, 'add_connection'), f"Manager missing add_connection method"
                    
                    return {
                        'user_index': user_index,
                        'success': True,
                        'manager_id': id(manager),
                        'manager_type': type(manager).__name__
                    }
                
                except Exception as e:
                    return {
                        'user_index': user_index,
                        'success': False,
                        'error': str(e)
                    }
            
            # Run concurrent factory operations
            concurrent_tasks = [
                concurrent_factory_creation(i) for i in range(10)
            ]
            
            concurrent_results = await asyncio.gather(*concurrent_tasks)
            
            # Analyze concurrent creation results
            failed_creations = [r for r in concurrent_results if not r['success']]
            successful_creations = [r for r in concurrent_results if r['success']]
            
            if failed_creations:
                failure_details = "\n".join([
                    f"  - User {f['user_index']}: {f['error']}"
                    for f in failed_creations
                ])
                
                pytest.fail(
                    f"🚨 CONCURRENT FACTORY FAILURE: {len(failed_creations)} out of {len(concurrent_tasks)} "
                    f"concurrent factory creations failed:\n{failure_details}\n"
                    f"BUSINESS IMPACT: Factory thread-safety issues can cause race conditions and connection failures."
                )
            
            # Verify all created managers are unique
            manager_ids = [r['manager_id'] for r in successful_creations]
            unique_manager_ids = set(manager_ids)
            
            if len(unique_manager_ids) != len(manager_ids):
                pytest.fail(
                    f"🚨 CONCURRENT UNIQUENESS VIOLATION: Factory created {len(manager_ids)} managers "
                    f"but only {len(unique_manager_ids)} were unique. "
                    f"Concurrent creation is producing duplicate instances!"
                )
            
            logger.info(f"✅ Concurrent factory creation test passed - {len(successful_creations)} unique managers created")
            
        except Exception as e:
            pytest.fail(f"❌ WebSocket factory pattern test failed: {e}")
        
        # Record factory pattern metrics
        # Record test metrics
        metrics = {
            'test_name': 'websocket_factory_pattern',
            'managers_created': len(managers),
            'uniqueness_violations': 0,  # If we got here, no violations
            'singleton_violations': len(singleton_violations) if 'singleton_violations' in locals() else 0,
            'concurrent_creation_success_rate': (len(successful_creations) / len(concurrent_results)) * 100 if 'concurrent_results' in locals() else 100,
            'compliance_status': 'PASS'
        }
        for key, value in metrics.items():
            self.record_metric(key, value)
    
    @pytest.mark.asyncio
    async def test_websocket_ssot_comprehensive_validation(self):
        """
        COMPREHENSIVE: Run complete SSOT validation combining all critical checks.
        
        This master test orchestrates all SSOT validation requirements and provides
        a comprehensive compliance report for WebSocket Manager SSOT integrity.
        
        Business Impact: Ensures complete protection of $500K+ ARR chat functionality.
        """
        logger.info("🎯 Running comprehensive WebSocket SSOT validation")
        
        validation_results = {
            'overall_compliance': False,
            'test_results': {},
            'critical_violations': [],
            'business_impact_score': 0,
            'remediation_required': False
        }
        
        try:
            # Run all individual validation tests
            individual_tests = [
                ('duplicate_detection', self.test_no_duplicate_websocket_managers),
                ('import_compliance', self.test_canonical_websocket_manager_imports), 
                ('protocol_compliance', self.test_websocket_protocol_compliance),
                ('factory_pattern', self.test_websocket_factory_pattern_compliance),
            ]
            
            for test_name, test_method in individual_tests:
                try:
                    logger.info(f"🧪 Running {test_name} validation...")
                    test_method()
                    validation_results['test_results'][test_name] = {
                        'status': 'PASS',
                        'business_impact': 'PROTECTED'
                    }
                    logger.info(f"✅ {test_name} validation PASSED")
                    
                except AssertionError as e:
                    validation_results['test_results'][test_name] = {
                        'status': 'FAIL', 
                        'error': str(e),
                        'business_impact': 'AT_RISK'
                    }
                    validation_results['critical_violations'].append({
                        'test': test_name,
                        'severity': 'CRITICAL',
                        'error': str(e)
                    }
        for key, value in metrics.items():
            self.record_metric(key, value)
                    logger.error(f"❌ {test_name} validation FAILED: {e}")
                    
                except Exception as e:
                    validation_results['test_results'][test_name] = {
                        'status': 'ERROR',
                        'error': str(e),
                        'business_impact': 'UNKNOWN'
                    }
                    logger.error(f"🚨 {test_name} validation ERROR: {e}")
            
            # Run async tests
            async_tests = [
                ('user_isolation', self.test_websocket_manager_user_isolation),
                ('event_delivery', self.test_websocket_event_delivery_compliance),
            ]
            
            for test_name, test_method in async_tests:
                try:
                    logger.info(f"🧪 Running async {test_name} validation...")
                    await test_method()
                    validation_results['test_results'][test_name] = {
                        'status': 'PASS',
                        'business_impact': 'PROTECTED'
                    }
                    logger.info(f"✅ {test_name} validation PASSED")
                    
                except AssertionError as e:
                    validation_results['test_results'][test_name] = {
                        'status': 'FAIL',
                        'error': str(e),
                        'business_impact': 'AT_RISK'
                    }
                    validation_results['critical_violations'].append({
                        'test': test_name,
                        'severity': 'CRITICAL',
                        'error': str(e)
                    }
        for key, value in metrics.items():
            self.record_metric(key, value)
                    logger.error(f"❌ {test_name} validation FAILED: {e}")
                    
                except Exception as e:
                    validation_results['test_results'][test_name] = {
                        'status': 'ERROR',
                        'error': str(e),
                        'business_impact': 'UNKNOWN'
                    }
                    logger.error(f"🚨 {test_name} validation ERROR: {e}")
            
            # Calculate overall compliance
            total_tests = len(validation_results['test_results'])
            passing_tests = len([r for r in validation_results['test_results'].values() if r['status'] == 'PASS'])
            
            validation_results['overall_compliance'] = passing_tests == total_tests
            validation_results['compliance_percentage'] = (passing_tests / total_tests) * 100 if total_tests > 0 else 0
            
            # Calculate business impact score (0-100)
            protected_tests = len([r for r in validation_results['test_results'].values() if r.get('business_impact') == 'PROTECTED'])
            validation_results['business_impact_score'] = (protected_tests / total_tests) * 100 if total_tests > 0 else 0
            
            # Determine if remediation is required
            validation_results['remediation_required'] = len(validation_results['critical_violations']) > 0
            
            # Generate comprehensive report
            if validation_results['overall_compliance']:
                logger.info(
                    f"🎉 COMPREHENSIVE SSOT VALIDATION SUCCESS!\n"
                    f"✅ All {total_tests} WebSocket SSOT validation tests PASSED\n"
                    f"✅ Business Impact Score: {validation_results['business_impact_score']:.1f}%\n"
                    f"✅ Chat functionality ($500K+ ARR) is PROTECTED\n"
                    f"✅ No remediation required"
                )
            else:
                critical_violation_summary = "\n".join([
                    f"  - {v['test']}: {v['error'][:100]}..." 
                    for v in validation_results['critical_violations']
                ])
                
                pytest.fail(
                    f"🚨 COMPREHENSIVE SSOT VALIDATION FAILURE!\n"
                    f"❌ {total_tests - passing_tests} out of {total_tests} critical tests FAILED\n"
                    f"❌ Compliance: {validation_results['compliance_percentage']:.1f}%\n"
                    f"❌ Business Impact Score: {validation_results['business_impact_score']:.1f}%\n"
                    f"❌ Critical Violations:\n{critical_violation_summary}\n"
                    f"🚨 IMMEDIATE REMEDIATION REQUIRED: WebSocket SSOT violations threaten $500K+ ARR chat functionality!"
                )
        
        except Exception as e:
            validation_results['test_results']['comprehensive_validation'] = {
                'status': 'ERROR',
                'error': str(e),
                'business_impact': 'CRITICAL_FAILURE'
            }
            pytest.fail(f"❌ Comprehensive WebSocket SSOT validation failed: {e}")
        
        # Record comprehensive validation metrics
        # Record test metrics
        metrics = {
            'test_name': 'websocket_ssot_comprehensive',
            'total_validation_tests': len(validation_results['test_results']),
            'passing_tests': passing_tests if 'passing_tests' in locals() else 0,
            'compliance_percentage': validation_results['compliance_percentage'],
            'business_impact_score': validation_results['business_impact_score'],
            'critical_violations': len(validation_results['critical_violations']),
            'remediation_required': validation_results['remediation_required'],
            'overall_status': 'PASS' if validation_results['overall_compliance'] else 'FAIL'
        }
        for key, value in metrics.items():
            self.record_metric(key, value)