"""
MessageRouter SSOT Import Validation Test

GitHub Issue: #1056 - Message router fragmentation blocking Golden Path
Business Impact: $500K+ ARR - Users cannot receive AI responses reliably

PURPOSE: Validate only one canonical MessageRouter import path exists
STATUS: SHOULD FAIL initially due to current fragmentation
EXPECTED: PASS after SSOT consolidation

This test enforces SSOT compliance by validating that all MessageRouter
imports resolve to the same canonical implementation.
"""
import sys
import importlib
from pathlib import Path
from typing import Set, List, Tuple
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class MessageRouterSSOTImportValidationTests(SSotBaseTestCase):
    """Test MessageRouter SSOT import path validation."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.expected_canonical_path = 'netra_backend.app.websocket_core.handlers'
        self.known_import_paths = ['netra_backend.app.websocket_core.handlers', 'netra_backend.app.agents.message_router', 'netra_backend.app.core.message_router']

    def test_single_canonical_message_router_import_path(self):
        """
        Test that only one canonical MessageRouter import path exists.

        CRITICAL: This test SHOULD FAIL initially with current fragmentation.
        EXPECTED: PASS after SSOT consolidation.

        Business Value: Prevents routing ambiguity affecting $500K+ ARR
        """
        successful_imports = []
        import_results = []
        for import_path in self.known_import_paths:
            try:
                module = importlib.import_module(import_path)
                if hasattr(module, 'MessageRouter'):
                    message_router_class = getattr(module, 'MessageRouter')
                    successful_imports.append((import_path, message_router_class))
                    import_results.append({'path': import_path, 'success': True, 'class_name': message_router_class.__name__, 'module_location': message_router_class.__module__, 'class_id': id(message_router_class)})
                else:
                    import_results.append({'path': import_path, 'success': False, 'error': 'MessageRouter attribute not found'})
            except ImportError as e:
                import_results.append({'path': import_path, 'success': False, 'error': str(e)})
        self.logger.info(f'MessageRouter import validation results: {len(successful_imports)} successful imports')
        for result in import_results:
            self.logger.info(f'  {result}')
        if len(successful_imports) == 1:
            canonical_path, canonical_class = successful_imports[0]
            self.assertEqual(canonical_path, self.expected_canonical_path, f'Single MessageRouter import should be from canonical path {self.expected_canonical_path}, got {canonical_path}')
            self.logger.info(f'CHECK SSOT COMPLIANCE: Single MessageRouter import from {canonical_path}')
        else:
            violation_details = f'SSOT VIOLATION: Found {len(successful_imports)} MessageRouter implementations: '
            violation_details += ', '.join([f'{path} (id={hex(id(cls))})' for path, cls in successful_imports])
            self.logger.error(f'X {violation_details}')
            self.fail(f'SSOT VIOLATION: Expected exactly 1 MessageRouter implementation, found {len(successful_imports)}. This proves fragmentation blocking Golden Path. Details: {violation_details}')

    def test_message_router_class_identity_uniqueness(self):
        """
        Test that all MessageRouter imports return the same class object.

        CRITICAL: This test SHOULD FAIL initially with current fragmentation.
        EXPECTED: PASS after SSOT consolidation ensuring same class identity.
        """
        message_router_classes = set()
        class_locations = []
        for import_path in self.known_import_paths:
            try:
                module = importlib.import_module(import_path)
                if hasattr(module, 'MessageRouter'):
                    message_router_class = getattr(module, 'MessageRouter')
                    message_router_classes.add(id(message_router_class))
                    class_locations.append({'path': import_path, 'class_id': id(message_router_class), 'class_module': message_router_class.__module__, 'class_name': message_router_class.__qualname__})
            except ImportError:
                continue
        self.logger.info(f'MessageRouter class identity analysis: {len(message_router_classes)} unique class objects')
        for location in class_locations:
            self.logger.info(f'  {location}')
        if len(message_router_classes) == 1:
            self.logger.info('CHECK SSOT COMPLIANCE: All MessageRouter imports return same class identity')
        else:
            violation_msg = f'SSOT VIOLATION: {len(message_router_classes)} different MessageRouter class objects detected'
            self.logger.error(f'X {violation_msg}')
            self.fail(f'SSOT VIOLATION: All MessageRouter imports must return same class identity. Found {len(message_router_classes)} different class objects, proving fragmentation. Class locations: {class_locations}')

    def test_canonical_import_path_accessibility(self):
        """Test that the canonical MessageRouter path is accessible and functional."""
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            router = MessageRouter()
            self.assertIsNotNone(router)
            self.assertTrue(hasattr(router, 'handlers'))
            self.assertTrue(hasattr(router, 'add_handler'))
            self.logger.info('CHECK Canonical MessageRouter import path functional')
        except ImportError as e:
            self.fail(f'Canonical MessageRouter import path not accessible: {e}')
        except Exception as e:
            self.fail(f'Canonical MessageRouter not functional: {e}')

    def tearDown(self):
        """Clean up test fixtures."""
        super().tearDown()
        modules_to_clear = [path for path in self.known_import_paths if path in sys.modules]
        for module_path in modules_to_clear:
            if module_path.startswith('netra_backend.app'):
                try:
                    self.logger.debug(f'Test analyzed module: {module_path}')
                except:
                    pass
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')