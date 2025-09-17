"""Empty docstring."""
Integration tests for WebSocket factory pattern consistency validation.

This test file validates the consistency of WebSocket factory patterns
across the system and detects integration-level SSOT violations that
may not be apparent in unit tests.

Issue #1126 - WebSocket Factory Dual Pattern Fragmentation

Business Value Protection: $500K+ ARR Golden Path reliability
Priority: Critical infrastructure integration validation
"""Empty docstring."""

import pytest
import asyncio
import logging
import time
from typing import Dict, Any, List, Set
from unittest.mock import patch, MagicMock, AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase, CategoryType


logger = logging.getLogger(__name__)


@pytest.mark.integration
class WebSocketFactoryPatternConsistencyTests(SSotAsyncTestCase):
    "Integration tests for WebSocket factory pattern consistency."""
    
    def setup_method(self, method):
        "Set up test with integration-specific categories."
        super().setup_method(method)
        if self._test_context:
            self._test_context.test_category = CategoryType.INTEGRATION
            self._test_context.metadata.update({
                'business_impact': '$500K+ ARR',
                'issue': '#1126',
                'test_type': 'factory_pattern_integration'
            }
    
    async def test_websocket_manager_factory_creation_consistency(self):
        "Test consistency of WebSocket manager creation across different patterns."""
        
        EXPECTED FAILURE: Different factory patterns should create inconsistent manager instances.
"""Empty docstring."""
        logger.info(Testing WebSocket manager factory creation consistency)""
        
        created_managers = []
        creation_methods = []
        
        # Method 1: Direct import and instantiation
        try:
            from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
            from netra_backend.app.websocket_core.websocket_manager import create_test_user_context
            
            user_context = create_test_user_context()
            manager1 = UnifiedWebSocketManager(user_context=user_context)
            
            created_managers.append(('direct_unified', manager1, type(manager1)))
            creation_methods.append('direct_unified')
            
        except Exception as e:
            logger.warning(fDirect unified manager creation failed: {e}")"
        
        # Method 2: Legacy manager import
        try:
            from netra_backend.app.websocket_core.manager import WebSocketManager
            from netra_backend.app.websocket_core.manager import create_test_user_context
            
            user_context = create_test_user_context()
            manager2 = WebSocketManager(user_context=user_context)
            
            created_managers.append(('legacy_manager', manager2, type(manager2)))
            creation_methods.append('legacy_manager')
            
        except Exception as e:
            logger.warning(fLegacy manager creation failed: {e})
        
        # Method 3: Factory function (deprecated)
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            
            manager3 = await create_websocket_manager()
            created_managers.append(('factory_function', manager3, type(manager3)))
            creation_methods.append('factory_function')
            
        except Exception as e:
            logger.warning(fFactory function creation failed: {e})""
        
        # Method 4: Bridge factory
        try:
            from netra_backend.app.services.websocket_bridge_factory import create_websocket_bridge
            from netra_backend.app.websocket_core.websocket_manager import create_test_user_context
            
            user_context = create_test_user_context()
            bridge = await create_websocket_bridge(user_context)
            
            # Extract manager from bridge if possible
            if hasattr(bridge, 'websocket_manager'):
                manager4 = bridge.websocket_manager
                created_managers.append(('bridge_factory', manager4, type(manager4)))
                creation_methods.append('bridge_factory')
            
        except Exception as e:
            logger.warning(f"Bridge factory creation failed: {e})"
        
        self.record_metric('creation_methods_attempted', len(creation_methods))
        self.record_metric('managers_created', len(created_managers))
        self.record_metric('creation_methods', creation_methods)
        
        logger.info(fCreated managers via methods: {creation_methods})
        
        # CRITICAL TEST: All managers should be of the same type (SSOT compliance)
        if len(created_managers) > 1:
            reference_type = created_managers[0][2]
            type_inconsistencies = []
            
            for method, manager, manager_type in created_managers[1:]:
                if manager_type != reference_type:
                    type_inconsistencies.append({
                        'reference_method': created_managers[0][0],
                        'reference_type': reference_type.__name__,
                        'inconsistent_method': method,
                        'inconsistent_type': manager_type.__name__,
                        'same_type': manager_type is reference_type
                    }
            
            self.record_metric('type_inconsistencies', len(type_inconsistencies))
            self.record_metric('inconsistency_details', type_inconsistencies)
            
            # EXPECTED FAILURE: Should detect type inconsistencies (SSOT violation)
            assert len(type_inconsistencies) == 0, (
                fSSOT VIOLATION: Found {len(type_inconsistencies)} type inconsistencies 
                facross WebSocket manager creation methods. All should create same type. ""
                fInconsistencies: {type_inconsistencies}
            )
        
        logger.info(No type inconsistencies detected - SSOT compliance maintained)
    
    async def test_websocket_manager_user_isolation_consistency(self):
        "Test user isolation consistency across different manager creation patterns."
        
        EXPECTED FAILURE: Different patterns should create managers with inconsistent isolation.
"""Empty docstring."""
        logger.info(Testing WebSocket manager user isolation consistency")"
        
        isolation_results = {}
        
        # Create multiple user contexts for isolation testing
        try:
            from netra_backend.app.websocket_core.websocket_manager import create_test_user_context
            
            user_context1 = create_test_user_context()
            user_context2 = create_test_user_context()
            
            # Test isolation with different creation patterns
            creation_patterns = [
                ('direct_unified', 'netra_backend.app.websocket_core.websocket_manager'),
                ('legacy_manager', 'netra_backend.app.websocket_core.manager'),
            ]
            
            for pattern_name, module_path in creation_patterns:
                try:
                    import importlib
                    module = importlib.import_module(module_path)
                    
                    if hasattr(module, 'UnifiedWebSocketManager'):
                        manager_class = module.UnifiedWebSocketManager
                    elif hasattr(module, 'WebSocketManager'):
                        manager_class = module.WebSocketManager
                    else:
                        continue
                    
                    # Create managers for different users
                    manager1 = manager_class(user_context=user_context1)
                    manager2 = manager_class(user_context=user_context2)
                    
                    # Test isolation properties
                    isolation_results[pattern_name] = {
                        'manager1_user_id': getattr(manager1, 'user_context', {}.get('user_id', None),
                        'manager2_user_id': getattr(manager2, 'user_context', {}.get('user_id', None),
                        'managers_are_same_object': manager1 is manager2,
                        'user_contexts_are_same': user_context1 is user_context2,
                        'user_ids_are_different': (
                            getattr(manager1, 'user_context', {}.get('user_id') != 
                            getattr(manager2, 'user_context', {}.get('user_id')
                        )
                    }
                    
                except Exception as e:
                    isolation_results[pattern_name] = {'error': str(e)}
                    logger.warning(fIsolation test failed for {pattern_name}: {e})
        
        except Exception as e:
            logger.warning(fUser context creation failed: {e})""
            return
        
        self.record_metric('isolation_patterns_tested', len(isolation_results))
        self.record_metric('isolation_results', isolation_results)
        
        logger.info(f"Isolation test results: {isolation_results})"
        
        # Check for isolation consistency across patterns
        isolation_behaviors = set()
        for pattern_name, results in isolation_results.items():
            if 'error' not in results:
                # Create behavior signature
                behavior = (
                    results.get('managers_are_same_object', False),
                    results.get('user_ids_are_different', False)
                )
                isolation_behaviors.add(behavior)
        
        self.record_metric('unique_isolation_behaviors', len(isolation_behaviors))
        
        # EXPECTED FAILURE: Different patterns should have consistent isolation behavior
        assert len(isolation_behaviors) <= 1, (
            fSSOT VIOLATION: Found {len(isolation_behaviors)} different isolation behaviors 
            facross WebSocket manager creation patterns. All patterns should behave consistently. 
            fResults: {isolation_results}""
        )
        
        logger.info(Isolation behavior consistent across patterns - SSOT compliance maintained)
    
    async def test_websocket_event_delivery_pattern_consistency(self):
        "Test event delivery consistency across different WebSocket patterns."""
        
        EXPECTED FAILURE: Different patterns should have inconsistent event delivery.
"""Empty docstring."""
        logger.info(Testing WebSocket event delivery pattern consistency)""
        
        event_delivery_results = {}
        
        # Test event delivery with different manager patterns
        try:
            from netra_backend.app.websocket_core.websocket_manager import create_test_user_context
            
            user_context = create_test_user_context()
            
            # Mock WebSocket connection for testing
            mock_websocket = MagicMock()
            mock_websocket.send_text = AsyncMock()
            
            # Test different manager creation patterns
            manager_patterns = []
            
            # Pattern 1: Direct unified manager
            try:
                from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
                manager1 = UnifiedWebSocketManager(user_context=user_context)
                manager_patterns.append(('unified', manager1))
            except Exception as e:
                logger.warning(fUnified manager creation failed: {e}")"
            
            # Pattern 2: Legacy manager
            try:
                from netra_backend.app.websocket_core.manager import WebSocketManager
                manager2 = WebSocketManager(user_context=user_context)
                manager_patterns.append(('legacy', manager2))
            except Exception as e:
                logger.warning(fLegacy manager creation failed: {e})
            
            # Test event emission for each pattern
            for pattern_name, manager in manager_patterns:
                try:
                    # Add mock connection
                    connection_id = ftest_conn_{pattern_name}""
                    if hasattr(manager, 'add_connection'):
                        await manager.add_connection(connection_id, mock_websocket)
                    
                    # Test standard WebSocket events
                    test_events = [
                        ('agent_started', {'message': 'Agent started'},
                        ('agent_thinking', {'message': 'Agent thinking'},
                        ('tool_executing', {'tool': 'test_tool'},
                        ('tool_completed', {'tool': 'test_tool', 'result': 'success'},
                        ('agent_completed', {'message': 'Agent completed'}
                    ]
                    
                    event_results = []
                    for event_type, event_data in test_events:
                        try:
                            # Try to emit event
                            if hasattr(manager, 'emit_event'):
                                await manager.emit_event(event_type, event_data)
                                event_results.append((event_type, 'success', None))
                            elif hasattr(manager, 'send_message'):
                                await manager.send_message({'type': event_type, **event_data}
                                event_results.append((event_type, 'success', None))
                            else:
                                event_results.append((event_type, 'no_method', 'No event method found'))
                        except Exception as e:
                            event_results.append((event_type, 'error', str(e)))
                    
                    event_delivery_results[pattern_name] = {
                        'events_tested': len(test_events),
                        'events_successful': len([r for r in event_results if r[1] == 'success'],
                        'events_failed': len([r for r in event_results if r[1] == 'error'],
                        'events_no_method': len([r for r in event_results if r[1] == 'no_method'],
                        'event_details': event_results
                    }
                    
                except Exception as e:
                    event_delivery_results[pattern_name] = {'error': str(e)}
                    logger.warning(f"Event delivery test failed for {pattern_name}: {e})"
        
        except Exception as e:
            logger.warning(fEvent delivery setup failed: {e})
            return
        
        self.record_metric('event_delivery_patterns_tested', len(event_delivery_results))
        self.record_metric('event_delivery_results', event_delivery_results)
        
        logger.info(fEvent delivery results: {event_delivery_results})
        
        # Check for consistency in event delivery capabilities
        delivery_capabilities = set()
        for pattern_name, results in event_delivery_results.items():
            if 'error' not in results:
                # Create capability signature
                capability = (
                    results.get('events_successful', 0),
                    results.get('events_no_method', 0)
                )
                delivery_capabilities.add(capability)
        
        self.record_metric('unique_delivery_capabilities', len(delivery_capabilities))
        
        # EXPECTED FAILURE: Different patterns should have consistent event delivery capabilities
        assert len(delivery_capabilities) <= 1, (
            fSSOT VIOLATION: Found {len(delivery_capabilities)} different event delivery capabilities ""
            facross WebSocket manager patterns. All patterns should have same capabilities. 
            fResults: {event_delivery_results}
        )
        
        logger.info("Event delivery capabilities consistent across patterns - SSOT compliance maintained)"
    
    async def test_websocket_connection_lifecycle_pattern_consistency(self):
        Test connection lifecycle consistency across different WebSocket patterns.
        
        EXPECTED FAILURE: Different patterns should have inconsistent lifecycle management.
""
        logger.info(Testing WebSocket connection lifecycle pattern consistency)
        
        lifecycle_results = {}
        
        try:
            from netra_backend.app.websocket_core.websocket_manager import create_test_user_context
            
            user_context = create_test_user_context()
            
            # Test lifecycle with different manager patterns
            manager_patterns = []
            
            # Collect available manager patterns
            try:
                from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
                manager_patterns.append(('unified', UnifiedWebSocketManager))
            except ImportError:
                pass
            
            try:
                from netra_backend.app.websocket_core.manager import WebSocketManager
                manager_patterns.append(('legacy', WebSocketManager))
            except ImportError:
                pass
            
            # Test lifecycle operations for each pattern
            for pattern_name, manager_class in manager_patterns:
                try:
                    manager = manager_class(user_context=user_context)
                    
                    # Mock WebSocket for lifecycle testing
                    mock_websocket = MagicMock()
                    mock_websocket.send_text = AsyncMock()
                    
                    connection_id = ftest_conn_{pattern_name}""
                    
                    # Test lifecycle operations
                    lifecycle_ops = {}
                    
                    # Test add connection
                    if hasattr(manager, 'add_connection'):
                        try:
                            await manager.add_connection(connection_id, mock_websocket)
                            lifecycle_ops['add_connection'] = 'success'
                        except Exception as e:
                            lifecycle_ops['add_connection'] = f'error: {str(e)}'
                    else:
                        lifecycle_ops['add_connection'] = 'method_not_found'
                    
                    # Test get connection
                    if hasattr(manager, 'get_connection'):
                        try:
                            conn = manager.get_connection(connection_id)
                            lifecycle_ops['get_connection'] = 'success' if conn else 'none_found'
                        except Exception as e:
                            lifecycle_ops['get_connection'] = f'error: {str(e)}'
                    else:
                        lifecycle_ops['get_connection'] = 'method_not_found'
                    
                    # Test remove connection
                    if hasattr(manager, 'remove_connection'):
                        try:
                            await manager.remove_connection(connection_id)
                            lifecycle_ops['remove_connection'] = 'success'
                        except Exception as e:
                            lifecycle_ops['remove_connection'] = f'error: {str(e)}'
                    else:
                        lifecycle_ops['remove_connection'] = 'method_not_found'
                    
                    # Test cleanup
                    if hasattr(manager, 'cleanup'):
                        try:
                            await manager.cleanup()
                            lifecycle_ops['cleanup'] = 'success'
                        except Exception as e:
                            lifecycle_ops['cleanup'] = f'error: {str(e)}'
                    else:
                        lifecycle_ops['cleanup'] = 'method_not_found'
                    
                    lifecycle_results[pattern_name] = lifecycle_ops
                    
                except Exception as e:
                    lifecycle_results[pattern_name] = {'error': str(e)}
                    logger.warning(f"Lifecycle test failed for {pattern_name}: {e})"
        
        except Exception as e:
            logger.warning(fLifecycle setup failed: {e})
            return
        
        self.record_metric('lifecycle_patterns_tested', len(lifecycle_results))
        self.record_metric('lifecycle_results', lifecycle_results)
        
        logger.info(fLifecycle test results: {lifecycle_results})
        
        # Check for consistency in lifecycle method availability
        lifecycle_signatures = set()
        for pattern_name, results in lifecycle_results.items():
            if 'error' not in results:
                # Create method availability signature
                signature = tuple(sorted([
                    (method, status) for method, status in results.items()
                    if status != 'method_not_found'
                ])
                lifecycle_signatures.add(signature)
        
        self.record_metric('unique_lifecycle_signatures', len(lifecycle_signatures))
        
        # EXPECTED FAILURE: Different patterns should have consistent lifecycle methods
        assert len(lifecycle_signatures) <= 1, (
            fSSOT VIOLATION: Found {len(lifecycle_signatures)} different lifecycle method signatures ""
            facross WebSocket manager patterns. All patterns should have same lifecycle methods. 
            fResults: {lifecycle_results}
        )
        
        logger.info("Lifecycle method signatures consistent across patterns - SSOT compliance maintained")