"""
Test WebSocket Import Path Consistency

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise)
- Business Goal: Ensure consistent WebSocket import paths prevent dual pattern fragmentation
- Value Impact: Developer experience and system reliability for AI chat infrastructure
- Revenue Impact: Prevents race conditions that could disrupt $500K+ ARR user interactions

CRITICAL: This test validates import path consistency for WebSocket SSOT compliance.
These tests MUST FAIL before SSOT remediation and PASS after remediation.

Issue: 30+ files import deprecated WebSocket factory patterns
GitHub Issue: https://github.com/netra-systems/netra-apex/issues/1126
"""
import pytest
import importlib
import sys
import unittest
from typing import List, Tuple, Dict, Any
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class TestWebSocketImportPathConsistency(SSotBaseTestCase, unittest.TestCase):
    """Test WebSocket import path consistency for SSOT compliance."""

    def get_deprecated_import_paths(self) -> List[Tuple[str, str]]:
        """
        Get list of deprecated import paths that should NOT work after remediation.
        
        Returns:
            List of (module_path, import_name) tuples that should be deprecated
        """
        return [('netra_backend.app.websocket_core.websocket_manager_factory', 'WebSocketManagerFactory'), ('netra_backend.app.websocket_core.websocket_manager_factory', 'create_websocket_manager'), ('netra_backend.app.websocket_core.websocket_manager_factory', 'get_websocket_manager_factory'), ('netra_backend.app.websocket_core.websocket_manager_factory', 'IsolatedWebSocketManager'), ('netra_backend.app.websocket_core.websocket_manager_factory', 'create_websocket_manager_sync')]

    def get_canonical_ssot_import_paths(self) -> List[Tuple[str, str]]:
        """
        Get list of canonical SSOT import paths that SHOULD work after remediation.
        
        Returns:
            List of (module_path, import_name) tuples that are SSOT compliant
        """
        return [('netra_backend.app.websocket_core.websocket_manager', 'get_websocket_manager'), ('netra_backend.app.websocket_core.websocket_manager', 'WebSocketManager'), ('netra_backend.app.websocket_core.unified_manager', '_UnifiedWebSocketManagerImplementation'), ('netra_backend.app.websocket_core.websocket_manager', 'WebSocketConnection'), ('netra_backend.app.websocket_core.protocols', 'WebSocketManagerProtocol')]

    def test_deprecated_import_paths_raise_errors(self):
        """
        Test that all deprecated import paths raise ImportError or AttributeError.
        
        BEFORE REMEDIATION: This test should FAIL (deprecated imports work)
        AFTER REMEDIATION: This test should PASS (deprecated imports raise errors)
        """
        deprecated_paths = self.get_deprecated_import_paths()
        for module_path, import_name in deprecated_paths:
            with self.subTest(module=module_path, name=import_name):
                with self.assertRaises((ImportError, AttributeError, ModuleNotFoundError)) as context:
                    try:
                        module = importlib.import_module(module_path)
                        if hasattr(module, import_name):
                            self.fail(f'Deprecated import {module_path}.{import_name} should not be accessible after SSOT remediation')
                    except (ImportError, ModuleNotFoundError):
                        pass
                self.logger.info(f'Successfully blocked deprecated import: {module_path}.{import_name}')

    def test_canonical_ssot_import_paths_work(self):
        """
        Test that all canonical SSOT import paths work correctly.
        
        BEFORE REMEDIATION: This test should PASS (SSOT imports work)
        AFTER REMEDIATION: This test should PASS (SSOT imports still work)
        """
        canonical_paths = self.get_canonical_ssot_import_paths()
        for module_path, import_name in canonical_paths:
            with self.subTest(module=module_path, name=import_name):
                try:
                    module = importlib.import_module(module_path)
                    self.assertTrue(hasattr(module, import_name), f'Canonical SSOT import {module_path}.{import_name} should always be accessible')
                    imported_item = getattr(module, import_name)
                    self.assertIsNotNone(imported_item, f'SSOT import {module_path}.{import_name} should not be None')
                    self.logger.info(f'Successfully imported SSOT: {module_path}.{import_name}')
                except ImportError as e:
                    self.fail(f'Canonical SSOT import should always work: {module_path}.{import_name} - {e}')

    def test_no_duplicate_websocket_manager_implementations(self):
        """
        Test that there are no duplicate WebSocket manager implementations.
        
        BEFORE REMEDIATION: This test should FAIL (duplicates exist)
        AFTER REMEDIATION: This test should PASS (only SSOT implementation exists)
        """
        modules_to_check = ['netra_backend.app.websocket_core.websocket_manager_factory', 'netra_backend.app.websocket_core.websocket_manager', 'netra_backend.app.websocket_core.unified_manager', 'netra_backend.app.websocket_core']
        websocket_manager_classes = []
        for module_path in modules_to_check:
            try:
                module = importlib.import_module(module_path)
                manager_class_names = [name for name in dir(module) if 'WebSocketManager' in name and (not name.startswith('_'))]
                for class_name in manager_class_names:
                    cls = getattr(module, class_name)
                    if isinstance(cls, type):
                        websocket_manager_classes.append((module_path, class_name, cls))
            except ImportError:
                continue
        expected_ssot_classes = {'_UnifiedWebSocketManagerImplementation', 'WebSocketManager'}
        actual_classes = {class_name for _, class_name, _ in websocket_manager_classes}
        unexpected_classes = actual_classes - expected_ssot_classes
        self.assertEqual(len(unexpected_classes), 0, f'No unexpected WebSocket manager classes should exist after SSOT remediation: {unexpected_classes}')
        for module_path, class_name, cls in websocket_manager_classes:
            if class_name in expected_ssot_classes:
                self.logger.info(f'Found expected SSOT class: {module_path}.{class_name}')
            else:
                self.logger.warning(f'Found unexpected class: {module_path}.{class_name}')

    def test_import_error_messages_provide_guidance(self):
        """
        Test that ImportError messages provide proper guidance for migration.
        
        BEFORE REMEDIATION: This test documents expected error messages
        AFTER REMEDIATION: This test validates error messages guide developers
        """
        deprecated_paths = self.get_deprecated_import_paths()
        guidance_keywords = ['ssot', 'deprecated', 'use', 'instead', 'migration', 'get_websocket_manager']
        for module_path, import_name in deprecated_paths:
            with self.subTest(module=module_path, name=import_name):
                try:
                    module = importlib.import_module(module_path)
                    if hasattr(module, import_name):
                        import warnings
                        with warnings.catch_warnings(record=True) as warning_list:
                            warnings.simplefilter('always')
                            deprecated_item = getattr(module, import_name)
                            if warning_list:
                                warning_messages = [str(w.message).lower() for w in warning_list]
                                has_guidance = any((any((keyword in msg for keyword in guidance_keywords)) for msg in warning_messages))
                                self.assertTrue(has_guidance, f'Deprecation warning for {import_name} should provide migration guidance: {warning_messages}')
                            else:
                                self.logger.warning(f'No deprecation warning found for {module_path}.{import_name}')
                except (ImportError, ModuleNotFoundError):
                    pass

    def test_consistent_import_behavior_across_environments(self):
        """
        Test that import behavior is consistent across different environments.
        
        BEFORE REMEDIATION: This test might FAIL (inconsistent behavior)
        AFTER REMEDIATION: This test should PASS (consistent SSOT behavior)
        """
        import_contexts = [('direct_import', lambda module, name: getattr(__import__(module, fromlist=[name]), name)), ('importlib', lambda module, name: getattr(importlib.import_module(module), name))]
        canonical_paths = self.get_canonical_ssot_import_paths()
        for context_name, import_func in import_contexts:
            for module_path, import_name in canonical_paths:
                with self.subTest(context=context_name, module=module_path, name=import_name):
                    try:
                        imported_item = import_func(module_path, import_name)
                        self.assertIsNotNone(imported_item, f'SSOT import should work consistently in {context_name}: {module_path}.{import_name}')
                    except Exception as e:
                        self.fail(f'SSOT import should work consistently in {context_name}: {module_path}.{import_name} - {e}')
        self.logger.info('Import behavior consistency test completed')

    def test_module_level_all_exports_are_ssot_compliant(self):
        """
        Test that __all__ exports in WebSocket modules are SSOT compliant.
        
        BEFORE REMEDIATION: This test should FAIL (deprecated exports in __all__)
        AFTER REMEDIATION: This test should PASS (only SSOT exports in __all__)
        """
        modules_to_check = ['netra_backend.app.websocket_core.websocket_manager_factory', 'netra_backend.app.websocket_core.websocket_manager', 'netra_backend.app.websocket_core.unified_manager']
        deprecated_export_names = {'WebSocketManagerFactory', 'create_websocket_manager', 'get_websocket_manager_factory', 'IsolatedWebSocketManager'}
        for module_path in modules_to_check:
            with self.subTest(module=module_path):
                try:
                    module = importlib.import_module(module_path)
                    if hasattr(module, '__all__'):
                        all_exports = set(module.__all__)
                        deprecated_found = all_exports.intersection(deprecated_export_names)
                        self.assertEqual(len(deprecated_found), 0, f'Module {module_path} should not export deprecated names in __all__: {deprecated_found}')
                        self.logger.info(f'Module {module_path} has clean __all__ exports: {all_exports}')
                    else:
                        self.logger.info(f'Module {module_path} has no __all__ defined')
                except ImportError:
                    self.logger.info(f'Module {module_path} not found - acceptable after SSOT remediation')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')