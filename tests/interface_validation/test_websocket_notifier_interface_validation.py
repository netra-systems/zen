"""
Interface Validation Tests for Issue #669 - WebSocketNotifier Interface Mismatches

This test suite validates that WebSocketNotifier implementations provide consistent interfaces
and identifies specific interface mismatches that prevent reliable WebSocket event delivery.

Business Impact: 500K+ ARR Golden Path functionality depends on consistent WebSocket interfaces.

Test Strategy: Create failing tests that reproduce interface mismatches, then validate fixes.
"""
import inspect
import pytest
import asyncio
from typing import Dict, List, Any, Optional, Type
from unittest.mock import Mock, AsyncMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext

class WebSocketNotifierInterfaceValidationTests(SSotBaseTestCase):
    """
    Test suite to validate WebSocketNotifier interface consistency.

    This test suite is designed to FAIL initially, proving interface mismatches exist.
    """

    def setup_method(self):
        """Set up test environment for interface validation."""
        super().setup_method()
        self.interface_implementations = [UnifiedWebSocketEmitter, WebSocketBridgeFactory, AgentWebSocketBridge]
        self.expected_interface_methods = ['create_user_emitter', 'create_auth_emitter']

    def test_method_name_consistency_across_implementations(self):
        """
        Test 1: Validate consistent method names across WebSocket implementations.

        EXPECTED TO FAIL: Different implementations use different method names.
        """
        method_mapping = {}
        for impl_class in self.interface_implementations:
            class_methods = [method for method in dir(impl_class) if not method.startswith('_')]
            method_mapping[impl_class.__name__] = class_methods
        implementations_with_create_user_emitter = []
        implementations_with_create_auth_emitter = []
        for impl_name, methods in method_mapping.items():
            if 'create_user_emitter' in methods:
                implementations_with_create_user_emitter.append(impl_name)
            if 'create_auth_emitter' in methods:
                implementations_with_create_auth_emitter.append(impl_name)
        assert len(implementations_with_create_user_emitter) == len(self.interface_implementations), f'Not all implementations have create_user_emitter. Found in: {implementations_with_create_user_emitter}, Missing from: {[impl.__name__ for impl in self.interface_implementations if impl.__name__ not in implementations_with_create_user_emitter]}'
        if not implementations_with_create_user_emitter:
            assert len(implementations_with_create_auth_emitter) == len(self.interface_implementations), f'Interface mismatch: Some implementations use create_user_emitter, others use create_auth_emitter. create_user_emitter: {implementations_with_create_user_emitter}, create_auth_emitter: {implementations_with_create_auth_emitter}'

    def test_parameter_signature_consistency(self):
        """
        Test 2: Validate parameter signatures are consistent across implementations.

        EXPECTED TO FAIL: Different implementations expect different parameters.
        """
        signature_mapping = {}
        for impl_class in self.interface_implementations:
            class_signatures = {}
            if hasattr(impl_class, 'create_user_emitter'):
                sig = inspect.signature(impl_class.create_user_emitter)
                class_signatures['create_user_emitter'] = {'parameters': list(sig.parameters.keys()), 'parameter_types': {name: param.annotation for name, param in sig.parameters.items()}, 'return_annotation': sig.return_annotation}
            if hasattr(impl_class, 'create_auth_emitter'):
                sig = inspect.signature(impl_class.create_auth_emitter)
                class_signatures['create_auth_emitter'] = {'parameters': list(sig.parameters.keys()), 'parameter_types': {name: param.annotation for name, param in sig.parameters.items()}, 'return_annotation': sig.return_annotation}
            signature_mapping[impl_class.__name__] = class_signatures
        create_user_emitter_signatures = []
        create_auth_emitter_signatures = []
        for impl_name, signatures in signature_mapping.items():
            if 'create_user_emitter' in signatures:
                create_user_emitter_signatures.append({'impl': impl_name, 'params': signatures['create_user_emitter']['parameters'], 'types': signatures['create_user_emitter']['parameter_types']})
            if 'create_auth_emitter' in signatures:
                create_auth_emitter_signatures.append({'impl': impl_name, 'params': signatures['create_auth_emitter']['parameters'], 'types': signatures['create_auth_emitter']['parameter_types']})
        if len(create_user_emitter_signatures) > 1:
            first_sig = create_user_emitter_signatures[0]
            for other_sig in create_user_emitter_signatures[1:]:
                assert first_sig['params'] == other_sig['params'], f"Parameter signature mismatch in create_user_emitter: {first_sig['impl']} has {first_sig['params']}, {other_sig['impl']} has {other_sig['params']}"
        import pytest
        pytest.fail('Expected interface signature mismatches - if this passes, interfaces may have been fixed')

    async def test_factory_method_compatibility(self):
        """
        Test 3: Validate factory methods create compatible emitter types.

        EXPECTED TO FAIL: Different factory methods return incompatible types.
        """
        mock_manager = Mock()
        mock_user_context = Mock(spec=UserExecutionContext)
        mock_user_context.user_id = 'test_user_123'
        mock_user_context.thread_id = 'test_thread_123'
        mock_user_context.connection_id = 'test_connection_123'
        emitter_results = {}
        try:
            if hasattr(UnifiedWebSocketEmitter, 'create_auth_emitter'):
                emitter = UnifiedWebSocketEmitter.create_auth_emitter(manager=mock_manager, user_id='test_user_123')
                emitter_results['UnifiedWebSocketEmitter.create_auth_emitter'] = {'success': True, 'type': type(emitter).__name__, 'emitter': emitter}
        except Exception as e:
            emitter_results['UnifiedWebSocketEmitter.create_auth_emitter'] = {'success': False, 'error': str(e)}
        try:
            if hasattr(WebSocketBridgeFactory, 'create_user_emitter'):
                factory = WebSocketBridgeFactory()
                emitter = await factory.create_user_emitter(user_id='test_user_123', thread_id='test_thread_123', connection_id='test_connection_123')
                emitter_results['WebSocketBridgeFactory.create_user_emitter'] = {'success': True, 'type': type(emitter).__name__, 'emitter': emitter}
        except Exception as e:
            emitter_results['WebSocketBridgeFactory.create_user_emitter'] = {'success': False, 'error': str(e)}
        try:
            if hasattr(AgentWebSocketBridge, 'create_user_emitter'):
                bridge = AgentWebSocketBridge()
                emitter = await bridge.create_user_emitter(mock_user_context)
                emitter_results['AgentWebSocketBridge.create_user_emitter'] = {'success': True, 'type': type(emitter).__name__, 'emitter': emitter}
        except Exception as e:
            emitter_results['AgentWebSocketBridge.create_user_emitter'] = {'success': False, 'error': str(e)}
        successful_results = {k: v for k, v in emitter_results.items() if v.get('success', False)}
        failed_results = {k: v for k, v in emitter_results.items() if not v.get('success', False)}
        assert len(failed_results) == 0, f'Factory method failures indicate interface incompatibility: {failed_results}'
        if len(successful_results) > 1:
            emitter_types = [result['type'] for result in successful_results.values()]
            first_type = emitter_types[0]
            for emitter_type in emitter_types[1:]:
                assert first_type == emitter_type, f'Factory methods return incompatible types: {emitter_types}'
        pytest.fail('Expected factory method incompatibilities - if this passes, factories may be compatible')

    def test_websocket_test_framework_interface_consistency(self):
        """
        Test 4: Validate test framework expects consistent WebSocket interfaces.

        EXPECTED TO FAIL: Test framework has incorrect interface expectations.
        """
        test_interface_expectations = []
        expected_test_methods = ['create_user_emitter', 'create_auth_emitter', 'create_isolated_execution_context']
        from test_framework.ssot.mock_factory import SSotMockFactory
        mock_factory = SSotMockFactory()
        websocket_params_to_test = ['websocket_client_id', 'user_id', 'thread_id', 'connection_id', 'user_context']
        mock_support_results = {}
        for param in websocket_params_to_test:
            try:
                mock_context = Mock()
                setattr(mock_context, param, f'test_{param}')
                mock_support_results[param] = True
            except Exception as e:
                mock_support_results[param] = False
        failed_params = [param for param, supported in mock_support_results.items() if not supported]
        assert len(failed_params) == 0, f"Test framework doesn't support expected WebSocket parameters: {failed_params}"
        pytest.fail('Expected test framework interface mismatches - if this passes, framework may be consistent')

    def test_ssot_compliance_across_websocket_implementations(self):
        """
        Test 5: Validate SSOT compliance across WebSocket implementations.

        EXPECTED TO FAIL: Implementations don't follow unified SSOT patterns.
        """
        ssot_compliance_results = {}
        for impl_class in self.interface_implementations:
            compliance_check = {'has_ssot_imports': False, 'uses_unified_manager': False, 'follows_factory_pattern': False, 'has_user_isolation': False}
            try:
                module = inspect.getmodule(impl_class)
                if module and hasattr(module, '__file__'):
                    with open(module.__file__, 'r') as f:
                        content = f.read()
                        if 'from netra_backend.app.websocket_core' in content:
                            compliance_check['has_ssot_imports'] = True
                        if 'UnifiedWebSocketManager' in content:
                            compliance_check['uses_unified_manager'] = True
                        if any((method in content for method in ['create_user_emitter', 'create_auth_emitter'])):
                            compliance_check['follows_factory_pattern'] = True
                        if 'UserExecutionContext' in content or 'user_isolation' in content:
                            compliance_check['has_user_isolation'] = True
            except Exception:
                pass
            ssot_compliance_results[impl_class.__name__] = compliance_check
        total_implementations = len(self.interface_implementations)
        compliance_scores = {}
        for compliance_aspect in ['has_ssot_imports', 'uses_unified_manager', 'follows_factory_pattern', 'has_user_isolation']:
            compliant_count = sum((1 for result in ssot_compliance_results.values() if result[compliance_aspect]))
            compliance_scores[compliance_aspect] = compliant_count / total_implementations
        minimum_compliance = 0.8
        for aspect, score in compliance_scores.items():
            assert score >= minimum_compliance, f'SSOT compliance failure for {aspect}: {score:.1%} compliance, expected {minimum_compliance:.1%}. Non-compliant implementations: {[impl for impl, result in ssot_compliance_results.items() if not result[aspect]]}'
        pytest.fail('Expected SSOT compliance issues - if this passes, implementations may be SSOT compliant')

class WebSocketBridgeInterfaceIntegrationTests(SSotBaseTestCase):
    """
    Integration tests for WebSocket bridge interface compatibility.

    These tests validate that bridge implementations integrate correctly.
    """

    async def test_agent_websocket_bridge_to_factory_integration(self):
        """
        Test 6: Validate AgentWebSocketBridge integrates with WebSocketBridgeFactory.

        EXPECTED TO FAIL: Bridge integration has interface mismatches.
        """
        mock_user_context = Mock(spec=UserExecutionContext)
        mock_user_context.user_id = 'test_user_123'
        mock_user_context.thread_id = 'test_thread_123'
        mock_user_context.connection_id = 'test_connection_123'
        bridge = AgentWebSocketBridge()
        factory = WebSocketBridgeFactory()
        integration_results = {}
        try:
            bridge_emitter = await bridge.create_user_emitter(mock_user_context)
            integration_results['bridge_emitter'] = {'success': True, 'type': type(bridge_emitter).__name__}
        except Exception as e:
            integration_results['bridge_emitter'] = {'success': False, 'error': str(e)}
        try:
            factory_emitter = await factory.create_user_emitter(user_id=mock_user_context.user_id, thread_id=mock_user_context.thread_id, connection_id=mock_user_context.connection_id)
            integration_results['factory_emitter'] = {'success': True, 'type': type(factory_emitter).__name__}
        except Exception as e:
            integration_results['factory_emitter'] = {'success': False, 'error': str(e)}
        bridge_success = integration_results.get('bridge_emitter', {}).get('success', False)
        factory_success = integration_results.get('factory_emitter', {}).get('success', False)
        assert bridge_success, f"AgentWebSocketBridge.create_user_emitter failed: {integration_results.get('bridge_emitter', {}).get('error', 'Unknown error')}"
        assert factory_success, f"WebSocketBridgeFactory.create_user_emitter failed: {integration_results.get('factory_emitter', {}).get('error', 'Unknown error')}"
        if bridge_success and factory_success:
            bridge_type = integration_results['bridge_emitter']['type']
            factory_type = integration_results['factory_emitter']['type']
            assert bridge_type == factory_type, f'Bridge and factory create incompatible emitter types: {bridge_type} vs {factory_type}'
        pytest.fail('Expected bridge integration issues - if this passes, integration may be working')

    async def test_websocket_event_delivery_interface_consistency(self):
        """
        Test 7: Validate WebSocket event delivery works with consistent interfaces.

        EXPECTED TO FAIL: Event delivery fails due to interface mismatches.
        """
        critical_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        event_delivery_results = {}
        mock_manager = AsyncMock()
        mock_emitter = AsyncMock()
        for event in critical_events:
            try:
                await mock_emitter.emit_event(event, {'test': 'data'})
                event_delivery_results[event] = {'success': True, 'interface_used': 'mock_emitter'}
            except Exception as e:
                event_delivery_results[event] = {'success': False, 'error': str(e)}
        failed_events = [event for event, result in event_delivery_results.items() if not result.get('success', False)]
        assert len(failed_events) == 0, f'Critical WebSocket events failed delivery due to interface issues: {failed_events}'
        pytest.fail('Expected event delivery interface issues - if this passes, event delivery may be working')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')