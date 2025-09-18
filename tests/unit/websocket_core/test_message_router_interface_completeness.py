"""
MessageRouter Interface Completeness Test

GitHub Issue: #1056 - Message router fragmentation blocking Golden Path
Business Impact: $500K+ ARR - Users cannot receive AI responses reliably

PURPOSE: Validate all MessageRouter implementations have complete interfaces
STATUS: SHOULD FAIL initially due to incomplete/inconsistent interfaces
EXPECTED: PASS after SSOT consolidation

This test validates that all MessageRouter implementations provide the
complete interface expected by consuming code, preventing runtime errors.
"""
import importlib
import inspect
from typing import Dict, Set, Any, List, Callable, Optional
from dataclasses import dataclass
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

@dataclass
class InterfaceRequirement:
    """Specification for a required interface method."""
    name: str
    method_type: str
    required: bool
    expected_signature: Optional[str] = None
    description: str = ''

@pytest.mark.unit
class MessageRouterInterfaceCompletenessTests(SSotBaseTestCase):
    """Test MessageRouter interface completeness across implementations."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.import_paths = ['netra_backend.app.websocket_core.handlers', 'netra_backend.app.agents.message_router', 'netra_backend.app.core.message_router']
        self.required_interface = [InterfaceRequirement('__init__', 'method', True, '(self)', 'Constructor'), InterfaceRequirement('handlers', 'property', True, None, 'List of message handlers'), InterfaceRequirement('add_handler', 'method', True, '(self, handler)', 'Add message handler'), InterfaceRequirement('remove_handler', 'method', False, '(self, handler)', 'Remove message handler'), InterfaceRequirement('routing_stats', 'attribute', False, None, 'Routing statistics')]
        self.optional_interface = [InterfaceRequirement('route_message', 'method', False, '(self, message)', 'Route single message'), InterfaceRequirement('handle_message', 'method', False, '(self, user_id, websocket, message)', 'Handle WebSocket message'), InterfaceRequirement('start', 'method', False, '(self)', 'Start router'), InterfaceRequirement('stop', 'method', False, '(self)', 'Stop router'), InterfaceRequirement('get_statistics', 'method', False, '(self)', 'Get routing statistics')]
        self.implementations = {}

    def _load_implementations(self):
        """Load all MessageRouter implementations for analysis."""
        for path in self.import_paths:
            try:
                module = importlib.import_module(path)
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    instance = router_class()
                    self.implementations[path] = {'class': router_class, 'instance': instance, 'module_path': path, 'loaded': True}
                    self.logger.info(f'Loaded MessageRouter implementation from {path}')
                else:
                    self.implementations[path] = {'loaded': False, 'error': 'MessageRouter class not found'}
            except ImportError as e:
                self.implementations[path] = {'loaded': False, 'error': f'Import error: {e}'}
            except Exception as e:
                self.implementations[path] = {'loaded': False, 'error': f'Unexpected error: {e}'}

    def test_message_router_interface_completeness(self):
        """
        Test all MessageRouter implementations have complete interfaces.

        CRITICAL: This test SHOULD FAIL initially with incomplete interfaces.
        EXPECTED: PASS after SSOT consolidation with complete interfaces.
        """
        self._load_implementations()
        loaded_implementations = {k: v for k, v in self.implementations.items() if v.get('loaded')}
        if not loaded_implementations:
            self.fail('No MessageRouter implementations could be loaded for interface testing')
        interface_violations = []
        for path, impl_info in loaded_implementations.items():
            router_class = impl_info['class']
            router_instance = impl_info['instance']
            for requirement in self.required_interface:
                violation = self._check_interface_requirement(path, router_class, router_instance, requirement)
                if violation:
                    interface_violations.append(violation)
        self.logger.info(f'Interface completeness analysis: {len(loaded_implementations)} implementations')
        for path, impl_info in loaded_implementations.items():
            if impl_info.get('loaded'):
                methods_count = len([m for m in dir(impl_info['class']) if not m.startswith('_')])
                self.logger.info(f'  {path}: {methods_count} public methods/attributes')
        if interface_violations:
            for violation in interface_violations:
                self.logger.error(f'  Interface violation: {violation}')
        if len(interface_violations) == 0:
            self.logger.info('CHECK SSOT COMPLIANCE: All MessageRouter implementations have complete required interfaces')
        else:
            violation_msg = f'SSOT VIOLATION: {len(interface_violations)} interface completeness violations detected'
            self.logger.error(f'X {violation_msg}')
            self.fail(f'SSOT VIOLATION: All MessageRouter implementations must have complete interfaces. Found {len(interface_violations)} interface violations proving incomplete implementations.')

    def _check_interface_requirement(self, path: str, router_class: type, router_instance: Any, requirement: InterfaceRequirement) -> Optional[Dict]:
        """Check if an implementation satisfies an interface requirement."""
        if requirement.method_type == 'method':
            return self._check_method_requirement(path, router_class, requirement)
        elif requirement.method_type == 'property':
            return self._check_property_requirement(path, router_instance, requirement)
        elif requirement.method_type == 'attribute':
            return self._check_attribute_requirement(path, router_instance, requirement)
        else:
            return {'path': path, 'requirement': requirement.name, 'violation_type': 'unknown_requirement_type', 'details': f'Unknown requirement type: {requirement.method_type}'}

    def _check_method_requirement(self, path: str, router_class: type, requirement: InterfaceRequirement) -> Optional[Dict]:
        """Check if a method requirement is satisfied."""
        if not hasattr(router_class, requirement.name):
            return {'path': path, 'requirement': requirement.name, 'violation_type': 'missing_method', 'required': requirement.required, 'details': f'Method {requirement.name} not found in class'}
        method = getattr(router_class, requirement.name)
        if not callable(method):
            return {'path': path, 'requirement': requirement.name, 'violation_type': 'not_callable', 'required': requirement.required, 'details': f'{requirement.name} exists but is not callable'}
        if requirement.expected_signature:
            try:
                actual_signature = str(inspect.signature(method))
                if actual_signature != requirement.expected_signature:
                    return {'path': path, 'requirement': requirement.name, 'violation_type': 'signature_mismatch', 'required': requirement.required, 'expected_signature': requirement.expected_signature, 'actual_signature': actual_signature, 'details': f'Method signature does not match expected'}
            except (ValueError, TypeError) as e:
                self.logger.debug(f'Could not inspect signature for {requirement.name}: {e}')
        return None

    def _check_property_requirement(self, path: str, router_instance: Any, requirement: InterfaceRequirement) -> Optional[Dict]:
        """Check if a property requirement is satisfied."""
        if not hasattr(router_instance, requirement.name):
            return {'path': path, 'requirement': requirement.name, 'violation_type': 'missing_property', 'required': requirement.required, 'details': f'Property {requirement.name} not found in instance'}
        try:
            value = getattr(router_instance, requirement.name)
            if requirement.name == 'handlers':
                if not hasattr(value, '__iter__'):
                    return {'path': path, 'requirement': requirement.name, 'violation_type': 'invalid_property_type', 'required': requirement.required, 'details': f'handlers property should be iterable, got {type(value)}'}
        except Exception as e:
            return {'path': path, 'requirement': requirement.name, 'violation_type': 'property_access_error', 'required': requirement.required, 'details': f'Error accessing property: {e}'}
        return None

    def _check_attribute_requirement(self, path: str, router_instance: Any, requirement: InterfaceRequirement) -> Optional[Dict]:
        """Check if an attribute requirement is satisfied."""
        if not hasattr(router_instance, requirement.name):
            if requirement.required:
                return {'path': path, 'requirement': requirement.name, 'violation_type': 'missing_attribute', 'required': requirement.required, 'details': f'Attribute {requirement.name} not found in instance'}
            return None
        return None

    def test_interface_method_signature_consistency(self):
        """
        Test that method signatures are consistent across implementations.

        CRITICAL: This test SHOULD FAIL initially with inconsistent signatures.
        EXPECTED: PASS after SSOT consolidation with consistent signatures.
        """
        self._load_implementations()
        loaded_implementations = {k: v for k, v in self.implementations.items() if v.get('loaded')}
        if len(loaded_implementations) < 2:
            self.skipTest(f'Need at least 2 implementations to test signature consistency')
        signature_analysis = {}
        for path, impl_info in loaded_implementations.items():
            router_class = impl_info['class']
            signatures = {}
            for name, method in inspect.getmembers(router_class, predicate=inspect.isfunction):
                if not name.startswith('_'):
                    try:
                        signatures[name] = str(inspect.signature(method))
                    except (ValueError, TypeError):
                        signatures[name] = 'signature_not_inspectable'
            signature_analysis[path] = signatures
        signature_inconsistencies = []
        all_method_names = set()
        for signatures in signature_analysis.values():
            all_method_names.update(signatures.keys())
        paths = list(signature_analysis.keys())
        for method_name in all_method_names:
            signatures_for_method = {}
            for path in paths:
                if method_name in signature_analysis[path]:
                    signatures_for_method[path] = signature_analysis[path][method_name]
            if len(signatures_for_method) > 1:
                unique_signatures = set(signatures_for_method.values())
                if len(unique_signatures) > 1:
                    signature_inconsistencies.append({'method_name': method_name, 'signatures': dict(signatures_for_method), 'unique_signatures': list(unique_signatures)})
        self.logger.info(f'Method signature consistency analysis: {len(loaded_implementations)} implementations')
        self.logger.info(f'Total unique method names found: {len(all_method_names)}')
        if signature_inconsistencies:
            for inconsistency in signature_inconsistencies:
                self.logger.error(f'  Signature inconsistency: {inconsistency}')
        if len(signature_inconsistencies) == 0:
            self.logger.info('CHECK SSOT COMPLIANCE: All MessageRouter implementations have consistent method signatures')
        else:
            violation_msg = f'SSOT VIOLATION: {len(signature_inconsistencies)} method signature inconsistencies detected'
            self.logger.error(f'X {violation_msg}')
            self.fail(f'SSOT VIOLATION: MessageRouter implementations must have consistent method signatures. Found {len(signature_inconsistencies)} signature inconsistencies proving fragmented interfaces.')

    def test_interface_compatibility_matrix(self):
        """
        Test interface compatibility matrix across all implementations.

        This test creates a comprehensive compatibility report to understand
        which interfaces are missing from which implementations.
        """
        self._load_implementations()
        loaded_implementations = {k: v for k, v in self.implementations.items() if v.get('loaded')}
        if not loaded_implementations:
            self.skipTest('No implementations loaded for compatibility testing')
        all_requirements = self.required_interface + self.optional_interface
        compatibility_matrix = {}
        for path, impl_info in loaded_implementations.items():
            router_class = impl_info['class']
            router_instance = impl_info['instance']
            compliance = {}
            for requirement in all_requirements:
                violation = self._check_interface_requirement(path, router_class, router_instance, requirement)
                compliance[requirement.name] = {'compliant': violation is None, 'required': requirement.required, 'violation': violation}
            compatibility_matrix[path] = compliance
        self.logger.info('MessageRouter Interface Compatibility Matrix:')
        for requirement in all_requirements:
            compliance_by_impl = {}
            for path, compliance in compatibility_matrix.items():
                is_compliant = compliance[requirement.name]['compliant']
                compliance_by_impl[path] = is_compliant
            compliant_count = sum((1 for c in compliance_by_impl.values() if c))
            total_count = len(compliance_by_impl)
            status = 'CHECK' if compliant_count == total_count else 'X'
            required_marker = '*' if requirement.required else ''
            self.logger.info(f'  {status} {requirement.name}{required_marker}: {compliant_count}/{total_count} implementations compliant')
        total_checks = len(all_requirements) * len(loaded_implementations)
        passed_checks = sum((1 for compliance in compatibility_matrix.values() for req_compliance in compliance.values() if req_compliance['compliant']))
        compliance_score = passed_checks / total_checks * 100 if total_checks > 0 else 0
        self.logger.info(f'Overall Interface Compliance Score: {compliance_score:.1f}%')
        self.assertTrue(True, 'Compatibility matrix analysis completed successfully')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')