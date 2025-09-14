"""
Interface Inconsistency Tests for Issue #914 AgentRegistry SSOT Consolidation

CRITICAL P0 TESTS: These tests are DESIGNED TO FAIL initially to prove interface 
inconsistencies between BasicRegistry and AdvancedRegistry that block Golden Path.

Business Value: $500K+ ARR Golden Path protection - ensures interface consistency
prevents WebSocket integration failures and AttributeError crashes.

Test Focus:
- set_websocket_manager signature conflicts (sync vs async)
- Missing list_available_agents method causing AttributeError
- WebSocket integration interface incompatibilities
- Method signature mismatches preventing drop-in replacement

Created: 2025-01-14 - Issue #914 Test Creation Plan
Priority: CRITICAL P0 - Must prove interface inconsistency blocking Golden Path
"""

import pytest
import asyncio
import inspect
from typing import Dict, Any, List, Optional, Union
from unittest.mock import Mock, AsyncMock

# SSOT Base Test Case - Required for all tests
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Environment access through SSOT pattern only
from shared.isolated_environment import IsolatedEnvironment

# Test imports - both registries to validate interface consistency
from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry


class TestAgentRegistryInterfaceInconsistency(SSotAsyncTestCase):
    """
    CRITICAL P0 Tests: Prove interface inconsistencies block Golden Path
    
    These tests are DESIGNED TO FAIL initially to demonstrate interface
    conflicts that prevent reliable WebSocket integration and agent execution.
    """
    
    async def async_setup_method(self, method=None):
        """Set up test environment with SSOT patterns"""
        await super().async_setup_method(method)
        self.env = IsolatedEnvironment()
        
        # Initialize both registry implementations
        self.basic_registry = BasicRegistry()
        self.advanced_registry = AdvancedRegistry()
        
        # Mock WebSocket manager for interface testing
        self.mock_websocket_manager = Mock()
        self.mock_websocket_manager.emit_agent_event = AsyncMock()
        
        # Test user context
        self.test_user_id = "test-user-interface-check"
        self.test_session_id = "test-session-interface-validation"

    async def test_set_websocket_manager_signature_conflicts(self):
        """
        CRITICAL P0 TEST: Prove set_websocket_manager signature conflicts
        
        DESIGNED TO FAIL: Different registries have incompatible set_websocket_manager
        signatures (sync vs async) preventing reliable WebSocket integration.
        
        Business Impact: Golden Path breaks when WebSocket manager setup fails
        due to signature mismatches between registry implementations.
        """
        websocket_method_analysis = {}
        method_conflicts = []
        
        # Analyze set_websocket_manager method in both registries
        registries = {
            'basic': self.basic_registry,
            'advanced': self.advanced_registry
        }
        
        for registry_name, registry in registries.items():
            if hasattr(registry, 'set_websocket_manager'):
                method = getattr(registry, 'set_websocket_manager')
                signature = inspect.signature(method)
                
                websocket_method_analysis[registry_name] = {
                    'exists': True,
                    'signature': str(signature),
                    'parameters': list(signature.parameters.keys()),
                    'is_async': asyncio.iscoroutinefunction(method),
                    'is_sync': not asyncio.iscoroutinefunction(method)
                }
                
                self.logger.info(f"{registry_name} registry set_websocket_manager: {signature}")
            else:
                websocket_method_analysis[registry_name] = {
                    'exists': False,
                    'signature': None,
                    'parameters': [],
                    'is_async': False,
                    'is_sync': False
                }
                self.logger.error(f"{registry_name} registry MISSING set_websocket_manager method")
        
        # Check for signature inconsistencies
        if len(websocket_method_analysis) > 1:
            signatures = {name: info['signature'] for name, info in websocket_method_analysis.items() if info['exists']}
            async_status = {name: info['is_async'] for name, info in websocket_method_analysis.items() if info['exists']}
            
            # Check for different signatures
            if len(set(signatures.values())) > 1:
                method_conflicts.append({
                    'method': 'set_websocket_manager',
                    'conflict_type': 'signature_mismatch',
                    'details': signatures
                })
            
            # Check for sync/async inconsistency
            if len(set(async_status.values())) > 1:
                method_conflicts.append({
                    'method': 'set_websocket_manager', 
                    'conflict_type': 'async_sync_mismatch',
                    'details': async_status
                })
        
        # Check for missing methods
        missing_methods = [name for name, info in websocket_method_analysis.items() if not info['exists']]
        if missing_methods:
            method_conflicts.append({
                'method': 'set_websocket_manager',
                'conflict_type': 'missing_method',
                'details': f"Missing from registries: {missing_methods}"
            })
        
        # DESIGNED TO FAIL: Interface inconsistencies block WebSocket integration
        if method_conflicts:
            conflict_details = []
            for conflict in method_conflicts:
                if conflict['conflict_type'] == 'signature_mismatch':
                    details = f"Signature mismatch - {conflict['details']}"
                elif conflict['conflict_type'] == 'async_sync_mismatch':
                    details = f"Async/sync mismatch - {conflict['details']}"
                elif conflict['conflict_type'] == 'missing_method':
                    details = conflict['details']
                else:
                    details = str(conflict['details'])
                conflict_details.append(f"{conflict['conflict_type']}: {details}")
            
            pytest.fail(
                f"CRITICAL INTERFACE INCONSISTENCY: set_websocket_manager method conflicts detected. "
                f"This prevents reliable WebSocket bridge integration blocking Golden Path user flow. "
                f"Conflicts: {'; '.join(conflict_details)}. "
                f"IMPACT: Users cannot receive real-time AI agent progress updates."
            )
        
        # If interfaces are consistent, that indicates SSOT consolidation success
        self.logger.info("set_websocket_manager interfaces are consistent - SSOT consolidation successful")

    async def test_list_available_agents_method_missing_error(self):
        """
        CRITICAL P0 TEST: Prove list_available_agents AttributeError
        
        DESIGNED TO FAIL: One registry missing list_available_agents method
        causing AttributeError that crashes agent discovery and blocks Golden Path.
        
        Business Impact: Golden Path fails when agent listing fails, preventing
        users from getting AI responses through proper agent routing.
        """
        method_availability = {}
        missing_methods = []
        method_signature_conflicts = []
        
        # Test both registries for list_available_agents method
        registries = {
            'basic': self.basic_registry,
            'advanced': self.advanced_registry
        }
        
        for registry_name, registry in registries.items():
            if hasattr(registry, 'list_available_agents'):
                method = getattr(registry, 'list_available_agents')
                signature = inspect.signature(method)
                
                method_availability[registry_name] = {
                    'exists': True,
                    'callable': callable(method),
                    'signature': str(signature),
                    'is_async': asyncio.iscoroutinefunction(method),
                    'parameter_count': len(signature.parameters)
                }
                
                self.logger.info(f"{registry_name} registry has list_available_agents: {signature}")
            else:
                method_availability[registry_name] = {
                    'exists': False,
                    'callable': False,
                    'signature': None,
                    'is_async': False,
                    'parameter_count': 0
                }
                missing_methods.append(registry_name)
                self.logger.error(f"{registry_name} registry MISSING list_available_agents method")
        
        # Check for signature inconsistencies among existing methods
        existing_methods = {name: info for name, info in method_availability.items() if info['exists']}
        if len(existing_methods) > 1:
            signatures = [info['signature'] for info in existing_methods.values()]
            async_statuses = [info['is_async'] for info in existing_methods.values()]
            
            if len(set(signatures)) > 1:
                method_signature_conflicts.append({
                    'conflict_type': 'signature_mismatch',
                    'details': {name: info['signature'] for name, info in existing_methods.items()}
                })
            
            if len(set(async_statuses)) > 1:
                method_signature_conflicts.append({
                    'conflict_type': 'async_sync_mismatch', 
                    'details': {name: info['is_async'] for name, info in existing_methods.items()}
                })
        
        # Test actual method calls to reproduce AttributeError
        execution_failures = []
        for registry_name, registry in registries.items():
            try:
                if hasattr(registry, 'list_available_agents'):
                    method = getattr(registry, 'list_available_agents')
                    if asyncio.iscoroutinefunction(method):
                        result = await method()
                    else:
                        result = method()
                    
                    self.logger.info(f"{registry_name} registry list_available_agents executed successfully")
                else:
                    # Try to call missing method to reproduce AttributeError
                    try:
                        await registry.list_available_agents()
                        execution_failures.append(f"{registry_name}: Unexpected success on missing method")
                    except AttributeError as e:
                        execution_failures.append(f"{registry_name}: AttributeError - {e}")
                        self.logger.error(f"{registry_name} registry AttributeError: {e}")
                    
            except Exception as e:
                execution_failures.append(f"{registry_name}: Execution failed - {e}")
                self.logger.error(f"{registry_name} registry execution error: {e}")
        
        # DESIGNED TO FAIL: Missing methods or inconsistencies block Golden Path
        failure_reasons = []
        
        if missing_methods:
            failure_reasons.append(f"Missing list_available_agents from registries: {missing_methods}")
        
        if method_signature_conflicts:
            conflict_details = []
            for conflict in method_signature_conflicts:
                conflict_details.append(f"{conflict['conflict_type']}: {conflict['details']}")
            failure_reasons.append(f"Signature conflicts: {'; '.join(conflict_details)}")
        
        if execution_failures:
            failure_reasons.append(f"Execution failures: {'; '.join(execution_failures)}")
        
        if failure_reasons:
            pytest.fail(
                f"CRITICAL METHOD AVAILABILITY INCONSISTENCY: list_available_agents method conflicts detected. "
                f"This causes AttributeError crashes blocking Golden Path agent discovery. "
                f"Failures: {'; '.join(failure_reasons)}. "
                f"IMPACT: Users cannot get AI responses due to agent discovery failures."
            )
        
        # If all methods exist and are consistent, that indicates successful consolidation
        self.logger.info("list_available_agents methods are consistent across all registries")

    async def test_websocket_integration_interface_compatibility(self):
        """
        CRITICAL P0 TEST: Prove WebSocket integration interface incompatibility
        
        DESIGNED TO FAIL: Registry interfaces incompatible with WebSocket bridge
        causing integration failures that prevent real-time agent events.
        
        Business Impact: Golden Path breaks when WebSocket events fail, users
        don't see agent progress and chat experience degrades severely.
        """
        websocket_integration_methods = [
            'set_websocket_manager',
            'set_websocket_bridge', 
            '_notify_agent_event',
            'emit_agent_event'
        ]
        
        interface_compatibility_analysis = {}
        compatibility_failures = []
        
        # Analyze WebSocket integration interface for both registries
        registries = {
            'basic': self.basic_registry,
            'advanced': self.advanced_registry
        }
        
        for registry_name, registry in registries.items():
            interface_compatibility_analysis[registry_name] = {
                'websocket_methods_available': 0,
                'websocket_methods_missing': [],
                'method_signatures': {},
                'integration_score': 0
            }
            
            for method_name in websocket_integration_methods:
                if hasattr(registry, method_name):
                    method = getattr(registry, method_name)
                    signature = inspect.signature(method)
                    
                    interface_compatibility_analysis[registry_name]['websocket_methods_available'] += 1
                    interface_compatibility_analysis[registry_name]['method_signatures'][method_name] = {
                        'signature': str(signature),
                        'is_async': asyncio.iscoroutinefunction(method),
                        'parameter_count': len(signature.parameters)
                    }
                    
                    self.logger.info(f"{registry_name} registry has {method_name}: {signature}")
                else:
                    interface_compatibility_analysis[registry_name]['websocket_methods_missing'].append(method_name)
                    self.logger.error(f"{registry_name} registry MISSING {method_name}")
            
            # Calculate integration compatibility score
            total_methods = len(websocket_integration_methods)
            available_methods = interface_compatibility_analysis[registry_name]['websocket_methods_available']
            interface_compatibility_analysis[registry_name]['integration_score'] = (available_methods / total_methods) * 100
        
        # Test actual WebSocket manager integration
        integration_test_results = {}
        
        for registry_name, registry in registries.items():
            integration_test_results[registry_name] = {
                'set_websocket_manager_success': False,
                'websocket_manager_accessible': False,
                'integration_errors': []
            }
            
            # Test setting WebSocket manager
            try:
                if hasattr(registry, 'set_websocket_manager'):
                    method = getattr(registry, 'set_websocket_manager')
                    
                    if asyncio.iscoroutinefunction(method):
                        await method(self.mock_websocket_manager)
                    else:
                        method(self.mock_websocket_manager)
                    
                    integration_test_results[registry_name]['set_websocket_manager_success'] = True
                    self.logger.info(f"{registry_name} registry set_websocket_manager succeeded")
                else:
                    integration_test_results[registry_name]['integration_errors'].append(
                        "set_websocket_manager method not available"
                    )
            except Exception as e:
                integration_test_results[registry_name]['integration_errors'].append(
                    f"set_websocket_manager failed: {e}"
                )
                self.logger.error(f"{registry_name} registry set_websocket_manager error: {e}")
            
            # Test WebSocket manager accessibility
            try:
                if hasattr(registry, 'websocket_manager'):
                    websocket_manager = getattr(registry, 'websocket_manager')
                    if websocket_manager is not None:
                        integration_test_results[registry_name]['websocket_manager_accessible'] = True
                        self.logger.info(f"{registry_name} registry websocket_manager accessible")
            except Exception as e:
                integration_test_results[registry_name]['integration_errors'].append(
                    f"websocket_manager access failed: {e}"
                )
        
        # Analyze cross-registry compatibility
        cross_registry_compatibility_issues = []
        
        # Check for method availability differences
        for method_name in websocket_integration_methods:
            registries_with_method = []
            registries_without_method = []
            
            for registry_name in registries.keys():
                if method_name not in interface_compatibility_analysis[registry_name]['websocket_methods_missing']:
                    registries_with_method.append(registry_name)
                else:
                    registries_without_method.append(registry_name)
            
            if registries_without_method and registries_with_method:
                cross_registry_compatibility_issues.append({
                    'method': method_name,
                    'issue': 'availability_mismatch',
                    'has_method': registries_with_method,
                    'missing_method': registries_without_method
                })
        
        # Check for signature mismatches
        for method_name in websocket_integration_methods:
            method_signatures = {}
            for registry_name in registries.keys():
                if method_name in interface_compatibility_analysis[registry_name]['method_signatures']:
                    method_signatures[registry_name] = interface_compatibility_analysis[registry_name]['method_signatures'][method_name]['signature']
            
            if len(method_signatures) > 1 and len(set(method_signatures.values())) > 1:
                cross_registry_compatibility_issues.append({
                    'method': method_name,
                    'issue': 'signature_mismatch',
                    'signatures': method_signatures
                })
        
        # DESIGNED TO FAIL: WebSocket integration incompatibilities block Golden Path
        failure_reasons = []
        
        # Check for low integration scores
        for registry_name, analysis in interface_compatibility_analysis.items():
            if analysis['integration_score'] < 100:  # Expect 100% for complete integration
                missing_methods = analysis['websocket_methods_missing']
                failure_reasons.append(
                    f"{registry_name} registry incomplete WebSocket integration "
                    f"({analysis['integration_score']:.1f}% complete) - missing: {missing_methods}"
                )
        
        # Check for integration test failures
        for registry_name, results in integration_test_results.items():
            if results['integration_errors']:
                failure_reasons.append(
                    f"{registry_name} registry integration errors: {'; '.join(results['integration_errors'])}"
                )
        
        # Check for cross-registry compatibility issues
        if cross_registry_compatibility_issues:
            for issue in cross_registry_compatibility_issues:
                if issue['issue'] == 'availability_mismatch':
                    failure_reasons.append(
                        f"Method {issue['method']} availability mismatch - "
                        f"available in {issue['has_method']}, missing from {issue['missing_method']}"
                    )
                elif issue['issue'] == 'signature_mismatch':
                    failure_reasons.append(
                        f"Method {issue['method']} signature mismatch - {issue['signatures']}"
                    )
        
        if failure_reasons:
            pytest.fail(
                f"CRITICAL WEBSOCKET INTEGRATION INCOMPATIBILITY: Registry interfaces incompatible with WebSocket bridge. "
                f"This prevents real-time agent event delivery blocking Golden Path user experience. "
                f"Integration failures: {'; '.join(failure_reasons)}. "
                f"IMPACT: Users don't see agent progress, chat experience severely degraded."
            )
        
        # If all WebSocket integrations are compatible, consolidation is successful
        self.logger.info("WebSocket integration interfaces are fully compatible across all registries")

    async def test_core_method_signature_mismatches(self):
        """
        CRITICAL P0 TEST: Prove core method signature mismatches
        
        DESIGNED TO FAIL: Core methods like get_agent, create_user_session have
        incompatible signatures preventing drop-in registry replacement.
        
        Business Impact: Golden Path breaks during registry usage when method
        calls fail due to signature mismatches, preventing agent execution.
        """
        core_methods = [
            'get_agent',
            'create_user_session', 
            'register_agent',
            'unregister_agent',
            'get_agent_status',
            'list_available_agents'
        ]
        
        method_signature_analysis = {}
        signature_conflicts = []
        
        # Analyze core method signatures for both registries
        registries = {
            'basic': self.basic_registry,
            'advanced': self.advanced_registry
        }
        
        for registry_name, registry in registries.items():
            method_signature_analysis[registry_name] = {}
            
            for method_name in core_methods:
                if hasattr(registry, method_name):
                    method = getattr(registry, method_name)
                    signature = inspect.signature(method)
                    
                    method_signature_analysis[registry_name][method_name] = {
                        'exists': True,
                        'signature': str(signature),
                        'parameters': list(signature.parameters.keys()),
                        'parameter_count': len(signature.parameters),
                        'is_async': asyncio.iscoroutinefunction(method)
                    }
                    
                    self.logger.info(f"{registry_name} registry {method_name}: {signature}")
                else:
                    method_signature_analysis[registry_name][method_name] = {
                        'exists': False,
                        'signature': None,
                        'parameters': [],
                        'parameter_count': 0,
                        'is_async': False
                    }
                    self.logger.warning(f"{registry_name} registry MISSING {method_name}")
        
        # Check for signature conflicts
        for method_name in core_methods:
            method_info_by_registry = {}
            
            for registry_name in registries.keys():
                if method_signature_analysis[registry_name][method_name]['exists']:
                    method_info_by_registry[registry_name] = method_signature_analysis[registry_name][method_name]
            
            if len(method_info_by_registry) > 1:  # Multiple registries have this method
                # Check for signature differences
                signatures = [info['signature'] for info in method_info_by_registry.values()]
                if len(set(signatures)) > 1:
                    signature_conflicts.append({
                        'method': method_name,
                        'conflict_type': 'signature_difference',
                        'signatures': {name: info['signature'] for name, info in method_info_by_registry.items()}
                    })
                
                # Check for async/sync differences
                async_statuses = [info['is_async'] for info in method_info_by_registry.values()]
                if len(set(async_statuses)) > 1:
                    signature_conflicts.append({
                        'method': method_name,
                        'conflict_type': 'async_sync_difference',
                        'async_statuses': {name: info['is_async'] for name, info in method_info_by_registry.items()}
                    })
                
                # Check for parameter count differences
                param_counts = [info['parameter_count'] for info in method_info_by_registry.values()]
                if len(set(param_counts)) > 1:
                    signature_conflicts.append({
                        'method': method_name,
                        'conflict_type': 'parameter_count_difference',
                        'parameter_counts': {name: info['parameter_count'] for name, info in method_info_by_registry.items()}
                    })
        
        # Test method calls with same parameters to find runtime incompatibilities
        runtime_compatibility_issues = []
        
        # Test get_agent method with consistent parameters
        if (hasattr(self.basic_registry, 'get_agent') and 
            hasattr(self.advanced_registry, 'get_agent')):
            
            test_agent_id = "test-agent-compatibility"
            
            try:
                # Try basic registry get_agent
                basic_get_agent = getattr(self.basic_registry, 'get_agent')
                if asyncio.iscoroutinefunction(basic_get_agent):
                    basic_result = await basic_get_agent(test_agent_id)
                else:
                    basic_result = basic_get_agent(test_agent_id)
                    
                self.logger.info(f"Basic registry get_agent succeeded: {type(basic_result)}")
            except Exception as e:
                runtime_compatibility_issues.append(f"Basic registry get_agent failed: {e}")
            
            try:
                # Try advanced registry get_agent
                advanced_get_agent = getattr(self.advanced_registry, 'get_agent')
                if asyncio.iscoroutinefunction(advanced_get_agent):
                    advanced_result = await advanced_get_agent(test_agent_id)
                else:
                    advanced_result = advanced_get_agent(test_agent_id)
                    
                self.logger.info(f"Advanced registry get_agent succeeded: {type(advanced_result)}")
            except Exception as e:
                runtime_compatibility_issues.append(f"Advanced registry get_agent failed: {e}")
        
        # DESIGNED TO FAIL: Signature conflicts prevent drop-in replacement
        failure_reasons = []
        
        if signature_conflicts:
            for conflict in signature_conflicts:
                if conflict['conflict_type'] == 'signature_difference':
                    failure_reasons.append(
                        f"Method {conflict['method']} signature mismatch: {conflict['signatures']}"
                    )
                elif conflict['conflict_type'] == 'async_sync_difference':
                    failure_reasons.append(
                        f"Method {conflict['method']} async/sync mismatch: {conflict['async_statuses']}"
                    )
                elif conflict['conflict_type'] == 'parameter_count_difference':
                    failure_reasons.append(
                        f"Method {conflict['method']} parameter count mismatch: {conflict['parameter_counts']}"
                    )
        
        if runtime_compatibility_issues:
            failure_reasons.append(f"Runtime compatibility failures: {'; '.join(runtime_compatibility_issues)}")
        
        if failure_reasons:
            pytest.fail(
                f"CRITICAL CORE METHOD SIGNATURE MISMATCHES: Core registry methods have incompatible signatures. "
                f"This prevents drop-in registry replacement blocking SSOT consolidation. "
                f"Signature conflicts: {'; '.join(failure_reasons)}. "
                f"IMPACT: Golden Path fails due to method call incompatibilities."
            )
        
        # If all core method signatures are compatible, consolidation is feasible
        self.logger.info("Core method signatures are compatible across all registries")

    async def async_teardown_method(self, method=None):
        """Clean up test resources"""
        await super().async_teardown_method(method)


if __name__ == "__main__":
    # Run with pytest for proper async support
    pytest.main([__file__, "-v", "--tb=short", "-s"])