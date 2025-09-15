"""
CRITICAL SSOT Test 4: MessageRouter Handler Registry Validation - Issue #1101

PURPOSE: Validate message handler registration consistency across different MessageRouter
implementations. These tests SHOULD FAIL before remediation and PASS after consolidation.

VIOLATION: Multiple MessageRouter implementations have:
- Different handler registration mechanisms
- Inconsistent handler discovery patterns  
- Conflicting handler priorities and execution order
- Duplicate handler registrations across router instances

BUSINESS IMPACT: $500K+ ARR Golden Path failures due to:
- Messages routed to wrong handlers causing incorrect responses
- Handler conflicts causing agent execution failures
- Missing handlers causing silent message drops
- Duplicate handling causing duplicate agent responses

TEST STRATEGY: 20% of MessageRouter SSOT testing strategy focused on handler registry validation
"""

import pytest
import unittest
import importlib
import inspect
import asyncio
from typing import Dict, List, Any, Set, Tuple, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase


@pytest.mark.unit
class MessageRouterHandlerRegistryValidationTests(SSotAsyncTestCase):
    """Test message handler registry consistency across different router implementations."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.router_sources = [
            ('core', 'netra_backend.app.core.message_router'),
            ('websocket_core', 'netra_backend.app.websocket_core.handlers'),
            ('services', 'netra_backend.app.services.message_router')
        ]
        self.handler_registry_analysis = {}

    def test_handler_registration_mechanism_consistency(self):
        """
        CRITICAL: Test that all router implementations use consistent handler registration.
        
        SHOULD FAIL: Different routers have different registration mechanisms
        WILL PASS: After consolidation all use same SSOT registration mechanism
        
        Business Impact: Inconsistent registration causes handler discovery failures
        """
        registration_mechanisms = {}
        
        for source_name, module_path in self.router_sources:
            try:
                module = importlib.import_module(module_path)
                
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    router_instance = router_class()
                    
                    # Analyze registration mechanisms
                    mechanisms = {
                        'has_add_route': hasattr(router_instance, 'add_route'),
                        'has_add_handler': hasattr(router_instance, 'add_handler'),
                        'has_register_handler': hasattr(router_instance, 'register_handler'),
                        'has_add_middleware': hasattr(router_instance, 'add_middleware'),
                        'has_custom_handlers_list': hasattr(router_instance, 'custom_handlers'),
                        'has_builtin_handlers_list': hasattr(router_instance, 'builtin_handlers'),
                        'has_routes_dict': hasattr(router_instance, 'routes'),
                        'has_handlers_dict': hasattr(router_instance, 'handlers'),
                    }
                    
                    # Check method signatures for registration methods
                    registration_signatures = {}
                    for method_name in ['add_route', 'add_handler', 'register_handler', 'add_middleware']:
                        if hasattr(router_instance, method_name):
                            try:
                                method = getattr(router_instance, method_name)
                                sig = inspect.signature(method)
                                registration_signatures[method_name] = str(sig)
                            except (ValueError, TypeError):
                                registration_signatures[method_name] = 'signature_unavailable'
                    
                    registration_mechanisms[source_name] = {
                        'mechanisms': mechanisms,
                        'signatures': registration_signatures,
                        'router_class': router_class.__name__,
                        'router_module': router_class.__module__
                    }
                    
            except (ImportError, AttributeError) as e:
                registration_mechanisms[source_name] = {
                    'error': str(e),
                    'mechanisms': {},
                    'signatures': {}
                }
        
        # Analyze consistency across implementations
        if len(registration_mechanisms) > 1:
            # Check mechanism consistency
            all_mechanisms = [data.get('mechanisms', {}) for data in registration_mechanisms.values() if 'mechanisms' in data]
            
            if len(all_mechanisms) > 1:
                # Compare mechanism availability
                mechanism_keys = set()
                for mechanisms in all_mechanisms:
                    mechanism_keys.update(mechanisms.keys())
                
                inconsistencies = []
                for key in mechanism_keys:
                    values = [mechanisms.get(key, False) for mechanisms in all_mechanisms]
                    if len(set(values)) > 1:  # Not all implementations have same value
                        inconsistencies.append({
                            'mechanism': key,
                            'values': dict(zip([src for src, data in registration_mechanisms.items() if 'mechanisms' in data], values))
                        })
                
                # CRITICAL: All router implementations should have consistent registration mechanisms
                self.assertEqual(
                    len(inconsistencies), 0,
                    f"SSOT VIOLATION: Found {len(inconsistencies)} handler registration mechanism inconsistencies: "
                    f"{inconsistencies}. All routers should support same registration methods."
                )

    def test_builtin_handler_consistency_across_implementations(self):
        """
        CRITICAL: Test that builtin handlers are consistent across router implementations.
        
        SHOULD FAIL: Different router implementations have different builtin handlers
        WILL PASS: After consolidation all routers have same SSOT builtin handlers
        
        Business Impact: Missing builtin handlers cause message processing failures
        """
        builtin_handler_analysis = {}
        
        for source_name, module_path in self.router_sources:
            try:
                module = importlib.import_module(module_path)
                
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    router_instance = router_class()
                    
                    # Analyze builtin handlers
                    builtin_handlers = []
                    handler_types = []
                    
                    if hasattr(router_instance, 'builtin_handlers'):
                        handlers = getattr(router_instance, 'builtin_handlers')
                        builtin_handlers = [type(handler).__name__ for handler in handlers]
                        handler_types = [type(handler) for handler in handlers]
                    elif hasattr(router_instance, 'handlers'):
                        # Alternative handler storage
                        handlers = getattr(router_instance, 'handlers', {})
                        if isinstance(handlers, dict):
                            builtin_handlers = list(handlers.keys())
                        elif isinstance(handlers, list):
                            builtin_handlers = [type(handler).__name__ for handler in handlers]
                    
                    builtin_handler_analysis[source_name] = {
                        'handler_names': builtin_handlers,
                        'handler_count': len(builtin_handlers),
                        'handler_types': [t.__name__ for t in handler_types] if handler_types else [],
                        'has_builtin_handlers_attr': hasattr(router_instance, 'builtin_handlers'),
                        'router_class': router_class.__name__
                    }
                    
            except (ImportError, AttributeError) as e:
                builtin_handler_analysis[source_name] = {
                    'error': str(e),
                    'handler_names': [],
                    'handler_count': 0,
                    'handler_types': []
                }
        
        # Analyze builtin handler consistency
        successful_analyses = {k: v for k, v in builtin_handler_analysis.items() if 'error' not in v}
        
        if len(successful_analyses) > 1:
            # Compare handler sets
            handler_sets = {source: set(data['handler_names']) for source, data in successful_analyses.items()}
            handler_counts = {source: data['handler_count'] for source, data in successful_analyses.items()}
            
            # Check for handler set consistency
            unique_handler_sets = set()
            for handler_set in handler_sets.values():
                unique_handler_sets.add(frozenset(handler_set))
            
            # Check for handler count consistency
            unique_handler_counts = set(handler_counts.values())
            
            # CRITICAL: All implementations should have same builtin handlers after SSOT
            self.assertEqual(
                len(unique_handler_sets), 1,
                f"SSOT VIOLATION: Found {len(unique_handler_sets)} different builtin handler sets: "
                f"{dict(handler_sets)}. All router implementations should have same builtin handlers."
            )
            
            self.assertEqual(
                len(unique_handler_counts), 1,
                f"SSOT VIOLATION: Found {len(unique_handler_counts)} different builtin handler counts: "
                f"{handler_counts}. All router implementations should have same number of builtin handlers."
            )

    async def test_handler_execution_order_consistency(self):
        """
        CRITICAL: Test that handler execution order is consistent across implementations.
        
        SHOULD FAIL: Different routers execute handlers in different orders
        WILL PASS: After consolidation all routers use same SSOT execution order
        
        Business Impact: Wrong execution order causes incorrect message processing
        """
        execution_order_tests = {}
        
        # Create test message that would trigger multiple handlers
        test_message = {
            'id': 'test_execution_order',
            'type': 'user_message',
            'user_id': 'test_user',
            'content': 'Test handler execution order'
        }
        
        for source_name, module_path in self.router_sources:
            try:
                module = importlib.import_module(module_path)
                
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    router_instance = router_class()
                    
                    # Track handler execution order
                    execution_order = []
                    handler_info = []
                    
                    if hasattr(router_instance, 'builtin_handlers'):
                        handlers = getattr(router_instance, 'builtin_handlers')
                        for i, handler in enumerate(handlers):
                            handler_info.append({
                                'position': i,
                                'type': type(handler).__name__,
                                'priority': getattr(handler, 'priority', 0),
                                'can_handle': hasattr(handler, 'can_handle')
                            })
                        
                        execution_order = [h['type'] for h in handler_info]
                    
                    execution_order_tests[source_name] = {
                        'execution_order': execution_order,
                        'handler_info': handler_info,
                        'total_handlers': len(handler_info)
                    }
                    
            except (ImportError, AttributeError) as e:
                execution_order_tests[source_name] = {
                    'error': str(e),
                    'execution_order': [],
                    'handler_info': []
                }
        
        # Analyze execution order consistency
        successful_tests = {k: v for k, v in execution_order_tests.items() if 'error' not in v}
        
        if len(successful_tests) > 1:
            # Compare execution orders
            execution_orders = {source: data['execution_order'] for source, data in successful_tests.items()}
            
            # Check if all execution orders are the same
            unique_orders = set()
            for order in execution_orders.values():
                unique_orders.add(tuple(order))
            
            # CRITICAL: Handler execution order should be consistent after SSOT
            self.assertEqual(
                len(unique_orders), 1,
                f"SSOT VIOLATION: Found {len(unique_orders)} different handler execution orders: "
                f"{dict(execution_orders)}. All router implementations should execute handlers in same order."
            )

    def test_handler_priority_system_consistency(self):
        """
        CRITICAL: Test that handler priority systems are consistent across implementations.
        
        SHOULD FAIL: Different routers use different priority systems or ignore priorities
        WILL PASS: After consolidation all routers use same SSOT priority system
        
        Business Impact: Priority inconsistencies cause important handlers to be skipped
        """
        priority_system_analysis = {}
        
        for source_name, module_path in self.router_sources:
            try:
                module = importlib.import_module(module_path)
                
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    router_instance = router_class()
                    
                    # Analyze priority system
                    priority_info = {
                        'supports_priorities': False,
                        'priority_attribute_name': None,
                        'priority_values': [],
                        'priority_types': set(),
                        'custom_handlers_prioritized': False,
                        'builtin_handlers_prioritized': False
                    }
                    
                    # Check builtin handlers for priority support
                    if hasattr(router_instance, 'builtin_handlers'):
                        handlers = getattr(router_instance, 'builtin_handlers')
                        for handler in handlers:
                            # Check for priority attributes
                            for attr_name in ['priority', '_priority', 'handler_priority', 'execution_priority']:
                                if hasattr(handler, attr_name):
                                    priority_info['supports_priorities'] = True
                                    priority_info['priority_attribute_name'] = attr_name
                                    priority_value = getattr(handler, attr_name)
                                    priority_info['priority_values'].append(priority_value)
                                    priority_info['priority_types'].add(type(priority_value).__name__)
                                    priority_info['builtin_handlers_prioritized'] = True
                                    break
                    
                    # Check custom handlers support
                    if hasattr(router_instance, 'custom_handlers'):
                        priority_info['custom_handlers_prioritized'] = True
                    
                    # Convert set to list for JSON serialization
                    priority_info['priority_types'] = list(priority_info['priority_types'])
                    
                    priority_system_analysis[source_name] = priority_info
                    
            except (ImportError, AttributeError) as e:
                priority_system_analysis[source_name] = {
                    'error': str(e),
                    'supports_priorities': False
                }
        
        # Analyze priority system consistency
        successful_analyses = {k: v for k, v in priority_system_analysis.items() if 'error' not in v}
        
        if len(successful_analyses) > 1:
            # Check priority support consistency
            priority_support = {source: data['supports_priorities'] for source, data in successful_analyses.items()}
            attribute_names = {source: data['priority_attribute_name'] for source, data in successful_analyses.items() if data['supports_priorities']}
            priority_types = {source: set(data['priority_types']) for source, data in successful_analyses.items() if data['supports_priorities']}
            
            # Check consistency
            unique_priority_support = set(priority_support.values())
            unique_attribute_names = set(attr for attr in attribute_names.values() if attr is not None)
            
            # CRITICAL: Priority system should be consistent across all implementations
            self.assertEqual(
                len(unique_priority_support), 1,
                f"SSOT VIOLATION: Found inconsistent priority support: {priority_support}. "
                f"All router implementations should consistently support or not support priorities."
            )
            
            if len(unique_attribute_names) > 1:
                self.fail(
                    f"SSOT VIOLATION: Found {len(unique_attribute_names)} different priority attribute names: "
                    f"{unique_attribute_names}. All routers should use same priority attribute name."
                )

    async def test_handler_registration_conflicts_detection(self):
        """
        CRITICAL: Test detection of handler registration conflicts between router instances.
        
        SHOULD FAIL: Multiple router instances cause handler registration conflicts
        WILL PASS: After consolidation single router prevents registration conflicts
        
        Business Impact: Registration conflicts cause handlers to override each other
        """
        registration_conflicts = []
        handler_registrations = {}
        
        # Test handler registration across different router instances
        test_handler_name = 'test_conflict_handler'
        
        for source_name, module_path in self.router_sources:
            try:
                module = importlib.import_module(module_path)
                
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    
                    # Create multiple router instances from same source
                    for instance_id in range(2):
                        router_instance = router_class()
                        instance_key = f"{source_name}_instance_{instance_id}"
                        
                        # Try to register a test handler if possible
                        handler_registered = False
                        registration_method = None
                        
                        # Mock handler for testing
                        mock_handler = MagicMock()
                        mock_handler.name = f"{test_handler_name}_{instance_key}"
                        
                        # Try different registration methods
                        if hasattr(router_instance, 'add_route'):
                            try:
                                router_instance.add_route('test_pattern', mock_handler)
                                handler_registered = True
                                registration_method = 'add_route'
                            except Exception as e:
                                pass
                        elif hasattr(router_instance, 'custom_handlers') and isinstance(getattr(router_instance, 'custom_handlers'), list):
                            try:
                                getattr(router_instance, 'custom_handlers').append(mock_handler)
                                handler_registered = True
                                registration_method = 'custom_handlers_list'
                            except Exception:
                                pass
                        
                        handler_registrations[instance_key] = {
                            'source': source_name,
                            'instance_id': instance_id,
                            'router_id': id(router_instance),
                            'handler_registered': handler_registered,
                            'registration_method': registration_method,
                            'handler_name': mock_handler.name
                        }
                        
            except (ImportError, AttributeError) as e:
                registration_conflicts.append({
                    'source': source_name,
                    'error': str(e),
                    'conflict_type': 'import_failure'
                })
        
        # Analyze registration conflicts
        successful_registrations = {k: v for k, v in handler_registrations.items() if v['handler_registered']}
        
        # Check for registration method consistency
        registration_methods = set(data['registration_method'] for data in successful_registrations.values())
        
        # Check for router ID conflicts (same router instance used multiple times)
        router_ids = [data['router_id'] for data in successful_registrations.values()]
        duplicate_router_ids = set([router_id for router_id in router_ids if router_ids.count(router_id) > 1])
        
        if duplicate_router_ids:
            registration_conflicts.append({
                'conflict_type': 'duplicate_router_instances',
                'duplicate_ids': list(duplicate_router_ids),
                'details': 'Same router instance used for multiple registrations'
            })
        
        # Check for registration method inconsistencies
        if len(registration_methods) > 1:
            registration_conflicts.append({
                'conflict_type': 'inconsistent_registration_methods',
                'methods': list(registration_methods),
                'details': 'Different router implementations use different registration methods'
            })
        
        # CRITICAL: No registration conflicts should exist after SSOT consolidation
        self.assertEqual(
            len(registration_conflicts), 0,
            f"SSOT VIOLATION: Found {len(registration_conflicts)} handler registration conflicts: "
            f"{registration_conflicts}. Single SSOT router should prevent all registration conflicts."
        )

    def test_handler_discovery_mechanism_consistency(self):
        """
        CRITICAL: Test that handler discovery mechanisms are consistent across implementations.
        
        SHOULD FAIL: Different routers use different handler discovery mechanisms
        WILL PASS: After consolidation all routers use same SSOT discovery mechanism
        
        Business Impact: Discovery inconsistencies cause handlers to be missed or duplicated
        """
        discovery_analysis = {}
        
        for source_name, module_path in self.router_sources:
            try:
                module = importlib.import_module(module_path)
                
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    router_instance = router_class()
                    
                    # Analyze handler discovery mechanisms
                    discovery_info = {
                        'has_find_handler_method': hasattr(router_instance, 'find_handler'),
                        'has_get_handlers_method': hasattr(router_instance, 'get_handlers'),
                        'has_route_method': hasattr(router_instance, 'route'),
                        'has_handle_message_method': hasattr(router_instance, 'handle_message'),
                        'has_can_handle_check': False,
                        'discovery_strategy': 'unknown'
                    }
                    
                    # Check discovery strategy
                    if hasattr(router_instance, 'builtin_handlers'):
                        handlers = getattr(router_instance, 'builtin_handlers')
                        for handler in handlers:
                            if hasattr(handler, 'can_handle'):
                                discovery_info['has_can_handle_check'] = True
                                discovery_info['discovery_strategy'] = 'can_handle_method'
                                break
                    
                    if hasattr(router_instance, 'routes'):
                        discovery_info['discovery_strategy'] = 'pattern_matching'
                    
                    # Check for handler selection methods
                    handler_selection_methods = []
                    for method_name in ['find_handler', 'select_handler', 'get_handler_for_message', 'match_handler']:
                        if hasattr(router_instance, method_name):
                            handler_selection_methods.append(method_name)
                    
                    discovery_info['handler_selection_methods'] = handler_selection_methods
                    discovery_info['selection_method_count'] = len(handler_selection_methods)
                    
                    discovery_analysis[source_name] = discovery_info
                    
            except (ImportError, AttributeError) as e:
                discovery_analysis[source_name] = {
                    'error': str(e),
                    'discovery_strategy': 'error'
                }
        
        # Analyze discovery mechanism consistency
        successful_analyses = {k: v for k, v in discovery_analysis.items() if 'error' not in v}
        
        if len(successful_analyses) > 1:
            # Check discovery strategy consistency
            discovery_strategies = {source: data['discovery_strategy'] for source, data in successful_analyses.items()}
            can_handle_usage = {source: data['has_can_handle_check'] for source, data in successful_analyses.items()}
            selection_methods = {source: set(data['handler_selection_methods']) for source, data in successful_analyses.items()}
            
            # Check consistency
            unique_strategies = set(discovery_strategies.values())
            unique_can_handle_usage = set(can_handle_usage.values())
            
            # CRITICAL: Discovery mechanisms should be consistent after SSOT
            self.assertEqual(
                len(unique_strategies), 1,
                f"SSOT VIOLATION: Found {len(unique_strategies)} different handler discovery strategies: "
                f"{discovery_strategies}. All router implementations should use same discovery strategy."
            )
            
            self.assertEqual(
                len(unique_can_handle_usage), 1,
                f"SSOT VIOLATION: Found inconsistent can_handle usage: {can_handle_usage}. "
                f"All router implementations should consistently use or not use can_handle checks."
            )


if __name__ == '__main__':
    unittest.main()