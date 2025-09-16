"""
MessageRouter Implementation Uniqueness Test

GitHub Issue: #1056 - Message router fragmentation blocking Golden Path
Business Impact: $500K+ ARR - Users cannot receive AI responses reliably

PURPOSE: Validate all MessageRouter imports return identical implementation
STATUS: SHOULD FAIL initially due to different implementations
EXPECTED: PASS after SSOT consolidation

This test compares method signatures and behavior across different
MessageRouter import paths to detect implementation fragmentation.
"""
import importlib
import inspect
from typing import Dict, Set, Any, List, Callable
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class MessageRouterImplementationUniquenessTests(SSotBaseTestCase):
    """Test MessageRouter implementation uniqueness across import paths."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.import_paths = ['netra_backend.app.websocket_core.handlers', 'netra_backend.app.agents.message_router', 'netra_backend.app.core.message_router']
        self.message_router_instances = {}
        self.implementation_signatures = {}

    def _load_message_router_implementations(self):
        """Load all available MessageRouter implementations."""
        for path in self.import_paths:
            try:
                module = importlib.import_module(path)
                if hasattr(module, 'MessageRouter'):
                    message_router_class = getattr(module, 'MessageRouter')
                    instance = message_router_class()
                    self.message_router_instances[path] = {'class': message_router_class, 'instance': instance, 'module_path': path}
                    methods = inspect.getmembers(message_router_class, predicate=inspect.isfunction)
                    self.implementation_signatures[path] = {name: inspect.signature(method) for name, method in methods}
                    self.logger.info(f'Loaded MessageRouter from {path}: {len(methods)} methods')
            except ImportError as e:
                self.logger.warning(f'Could not import MessageRouter from {path}: {e}')
            except Exception as e:
                self.logger.error(f'Error loading MessageRouter from {path}: {e}')

    def test_message_router_implementation_uniqueness(self):
        """
        Test all MessageRouter imports return identical implementation.

        CRITICAL: This test SHOULD FAIL initially with current fragmentation.
        EXPECTED: PASS after SSOT consolidation with identical implementations.
        """
        self._load_message_router_implementations()
        if len(self.message_router_instances) < 2:
            self.skipTest(f'Need at least 2 MessageRouter implementations to test uniqueness, found {len(self.message_router_instances)}')
        all_method_names = set()
        for path, signatures in self.implementation_signatures.items():
            all_method_names.update(signatures.keys())
        signature_mismatches = []
        missing_methods = []
        paths = list(self.implementation_signatures.keys())
        for method_name in all_method_names:
            implementations_with_method = [path for path in paths if method_name in self.implementation_signatures[path]]
            if len(implementations_with_method) != len(paths):
                missing_from = set(paths) - set(implementations_with_method)
                missing_methods.append({'method': method_name, 'missing_from': list(missing_from), 'present_in': implementations_with_method})
                continue
            base_signature = None
            base_path = None
            for path in implementations_with_method:
                current_signature = self.implementation_signatures[path][method_name]
                if base_signature is None:
                    base_signature = current_signature
                    base_path = path
                elif str(current_signature) != str(base_signature):
                    signature_mismatches.append({'method': method_name, 'base_path': base_path, 'base_signature': str(base_signature), 'mismatch_path': path, 'mismatch_signature': str(current_signature)})
        self.logger.info(f'Implementation uniqueness analysis: {len(self.message_router_instances)} implementations')
        self.logger.info(f'Total methods found: {len(all_method_names)}')
        self.logger.info(f'Signature mismatches: {len(signature_mismatches)}')
        self.logger.info(f'Missing methods: {len(missing_methods)}')
        if signature_mismatches:
            for mismatch in signature_mismatches:
                self.logger.error(f'  Method signature mismatch: {mismatch}')
        if missing_methods:
            for missing in missing_methods:
                self.logger.error(f'  Missing method: {missing}')
        total_violations = len(signature_mismatches) + len(missing_methods)
        if total_violations == 0:
            self.logger.info('✅ SSOT COMPLIANCE: All MessageRouter implementations have identical interfaces')
        else:
            violation_msg = f'SSOT VIOLATION: {total_violations} implementation differences detected'
            self.logger.error(f'❌ {violation_msg}')
            self.fail(f'SSOT VIOLATION: MessageRouter implementations must be identical. Found {len(signature_mismatches)} signature mismatches and {len(missing_methods)} missing methods. This proves fragmented implementations blocking Golden Path.')

    def test_message_router_initialization_consistency(self):
        """
        Test MessageRouter instances have consistent initialization behavior.

        CRITICAL: This test SHOULD FAIL initially with different initialization.
        EXPECTED: PASS after SSOT consolidation with consistent initialization.
        """
        self._load_message_router_implementations()
        if len(self.message_router_instances) < 2:
            self.skipTest(f'Need at least 2 MessageRouter implementations to test consistency')
        attribute_analysis = {}
        for path, info in self.message_router_instances.items():
            instance = info['instance']
            attributes = {}
            common_attributes = ['handlers', 'routing_stats', 'startup_time', 'custom_handlers', 'builtin_handlers']
            for attr in common_attributes:
                if hasattr(instance, attr):
                    attr_value = getattr(instance, attr)
                    attributes[attr] = {'exists': True, 'type': type(attr_value).__name__, 'value_repr': repr(attr_value)[:100] + '...' if len(repr(attr_value)) > 100 else repr(attr_value)}
                else:
                    attributes[attr] = {'exists': False}
            attribute_analysis[path] = attributes
        inconsistencies = []
        paths = list(attribute_analysis.keys())
        if len(paths) >= 2:
            base_path = paths[0]
            base_attributes = attribute_analysis[base_path]
            for compare_path in paths[1:]:
                compare_attributes = attribute_analysis[compare_path]
                for attr_name in set(base_attributes.keys()) | set(compare_attributes.keys()):
                    base_info = base_attributes.get(attr_name, {'exists': False})
                    compare_info = compare_attributes.get(attr_name, {'exists': False})
                    if base_info['exists'] != compare_info['exists']:
                        inconsistencies.append({'attribute': attr_name, 'base_path': base_path, 'base_exists': base_info['exists'], 'compare_path': compare_path, 'compare_exists': compare_info['exists']})
                    elif base_info['exists'] and compare_info['exists']:
                        if base_info['type'] != compare_info['type']:
                            inconsistencies.append({'attribute': attr_name, 'base_path': base_path, 'base_type': base_info['type'], 'compare_path': compare_path, 'compare_type': compare_info['type']})
        self.logger.info(f'Initialization consistency analysis: {len(self.message_router_instances)} implementations')
        for path, attributes in attribute_analysis.items():
            self.logger.info(f"  {path}: {len([a for a in attributes.values() if a['exists']])} attributes")
        if inconsistencies:
            for inconsistency in inconsistencies:
                self.logger.error(f'  Initialization inconsistency: {inconsistency}')
        if len(inconsistencies) == 0:
            self.logger.info('✅ SSOT COMPLIANCE: All MessageRouter implementations have consistent initialization')
        else:
            violation_msg = f'SSOT VIOLATION: {len(inconsistencies)} initialization inconsistencies detected'
            self.logger.error(f'❌ {violation_msg}')
            self.fail(f'SSOT VIOLATION: MessageRouter implementations must have consistent initialization. Found {len(inconsistencies)} inconsistencies proving fragmented implementations.')

    def test_message_router_behavioral_equivalence(self):
        """
        Test MessageRouter instances exhibit equivalent behavior for basic operations.

        CRITICAL: This test SHOULD FAIL initially with different behaviors.
        EXPECTED: PASS after SSOT consolidation with equivalent behavior.
        """
        self._load_message_router_implementations()
        if len(self.message_router_instances) < 2:
            self.skipTest(f'Need at least 2 MessageRouter implementations to test behavioral equivalence')
        behavior_results = {}
        for path, info in self.message_router_instances.items():
            instance = info['instance']
            results = {}
            try:
                if hasattr(instance, 'handlers'):
                    handlers = getattr(instance, 'handlers')
                    results['handlers_count'] = len(handlers) if hasattr(handlers, '__len__') else 'not_countable'
                    results['handlers_type'] = type(handlers).__name__
                else:
                    results['handlers_available'] = False
                if hasattr(instance, 'add_handler'):
                    results['add_handler_available'] = True
                    results['add_handler_callable'] = callable(getattr(instance, 'add_handler'))
                else:
                    results['add_handler_available'] = False
                if hasattr(instance, 'routing_stats'):
                    stats = getattr(instance, 'routing_stats')
                    results['routing_stats_type'] = type(stats).__name__
                    results['routing_stats_keys'] = list(stats.keys()) if hasattr(stats, 'keys') else 'no_keys'
                else:
                    results['routing_stats_available'] = False
            except Exception as e:
                results['error'] = str(e)
            behavior_results[path] = results
        behavioral_differences = []
        paths = list(behavior_results.keys())
        if len(paths) >= 2:
            base_path = paths[0]
            base_behavior = behavior_results[base_path]
            for compare_path in paths[1:]:
                compare_behavior = behavior_results[compare_path]
                for key in set(base_behavior.keys()) | set(compare_behavior.keys()):
                    base_value = base_behavior.get(key)
                    compare_value = compare_behavior.get(key)
                    if base_value != compare_value:
                        behavioral_differences.append({'behavior': key, 'base_path': base_path, 'base_value': base_value, 'compare_path': compare_path, 'compare_value': compare_value})
        self.logger.info(f'Behavioral equivalence analysis: {len(self.message_router_instances)} implementations')
        for path, results in behavior_results.items():
            self.logger.info(f'  {path}: {results}')
        if behavioral_differences:
            for difference in behavioral_differences:
                self.logger.error(f'  Behavioral difference: {difference}')
        if len(behavioral_differences) == 0:
            self.logger.info('✅ SSOT COMPLIANCE: All MessageRouter implementations exhibit equivalent behavior')
        else:
            violation_msg = f'SSOT VIOLATION: {len(behavioral_differences)} behavioral differences detected'
            self.logger.error(f'❌ {violation_msg}')
            self.fail(f'SSOT VIOLATION: MessageRouter implementations must exhibit equivalent behavior. Found {len(behavioral_differences)} behavioral differences proving fragmentation.')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')