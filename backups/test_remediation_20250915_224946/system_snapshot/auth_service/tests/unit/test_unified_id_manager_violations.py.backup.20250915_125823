"""
Test for direct UnifiedIDManager violations in auth service.

This test file detects direct usage of uuid.uuid4() instead of UnifiedIDManager.generate_id().

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability and Compliance
- Value Impact: Ensures centralized ID generation across all services
- Strategic Impact: Eliminates ID generation inconsistencies that could cause system failures

CRITICAL: These tests MUST FAIL initially to prove violations exist.
Once violations are fixed, these tests should pass.
"""
import ast
import os
import uuid
from pathlib import Path
from typing import List, Tuple
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType, get_id_manager

class TestUnifiedIDManagerViolations(SSotBaseTestCase):
    """Test suite to detect direct UUID.uuid4() violations in auth service code."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.auth_service_root = Path('C:/GitHub/netra-apex/auth_service')
        self.violations_found = []

    def test_direct_uuid4_violations_in_core_files(self):
        """
        CRITICAL VIOLATION TEST: Detect uuid.uuid4() in core auth service files.
        
        This test MUST FAIL initially as it detects the exact violations found in audit:
        - auth_core/oauth/oauth_handler.py:65, 161, 162
        - services/*.py files with direct uuid.uuid4() calls
        
        Expected behavior: FAIL initially, PASS after remediation
        """
        core_violations = []
        oauth_handler_path = self.auth_service_root / 'auth_core/oauth/oauth_handler.py'
        if oauth_handler_path.exists():
            violations = self._scan_file_for_uuid4_violations(oauth_handler_path)
            core_violations.extend(violations)
        services_dir = self.auth_service_root / 'services'
        if services_dir.exists():
            for py_file in services_dir.glob('*.py'):
                violations = self._scan_file_for_uuid4_violations(py_file)
                core_violations.extend(violations)
        self.assertEqual(len(core_violations), 0, f'Found {len(core_violations)} direct uuid.uuid4() violations in core files: {self._format_violations(core_violations)}')
        self.violations_found.extend(core_violations)

    def test_direct_uuid4_violations_in_test_factories(self):
        """
        CRITICAL VIOLATION TEST: Detect uuid.uuid4() in test factory files.
        
        This test MUST FAIL initially as it detects violations in:
        - tests/factories/audit_factory.py (multiple violations)
        - tests/factories/user_factory.py (multiple violations)
        - tests/factories/token_factory.py (multiple violations)
        - tests/factories/session_factory.py (multiple violations)
        
        Expected behavior: FAIL initially, PASS after remediation
        """
        factory_violations = []
        factories_dir = self.auth_service_root / 'tests/factories'
        if factories_dir.exists():
            for py_file in factories_dir.glob('*.py'):
                if py_file.name == '__init__.py':
                    continue
                violations = self._scan_file_for_uuid4_violations(py_file)
                factory_violations.extend(violations)
        self.assertEqual(len(factory_violations), 0, f'Found {len(factory_violations)} direct uuid.uuid4() violations in factory files: {self._format_violations(factory_violations)}')
        self.violations_found.extend(factory_violations)

    def test_direct_uuid4_violations_comprehensive_scan(self):
        """
        COMPREHENSIVE VIOLATION TEST: Full scan of auth_service for uuid.uuid4() usage.
        
        This test performs a comprehensive scan to find ALL direct uuid.uuid4() calls.
        Based on the audit, this should find approximately 100+ violations.
        
        Expected behavior: FAIL initially with high violation count, PASS after remediation
        """
        all_violations = []
        for py_file in self.auth_service_root.rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue
            violations = self._scan_file_for_uuid4_violations(py_file)
            all_violations.extend(violations)
        violation_count = len(all_violations)
        self.assertEqual(violation_count, 0, f'COMPREHENSIVE SCAN: Found {violation_count} total uuid.uuid4() violations across auth_service. This proves UnifiedIDManager is not being used consistently. First 10 violations: {self._format_violations(all_violations[:10])}')
        self.violations_found.extend(all_violations)

    def test_unified_id_manager_import_compliance(self):
        """
        COMPLIANCE TEST: Verify files that should use UnifiedIDManager actually import it.
        
        This test checks that core service files import UnifiedIDManager when they
        need to generate IDs, instead of importing uuid directly.
        
        Expected behavior: FAIL initially due to missing imports, PASS after remediation
        """
        import_violations = []
        critical_files = ['auth_core/oauth/oauth_handler.py', 'services/token_refresh_service.py', 'services/session_service.py', 'services/user_service.py']
        for file_path in critical_files:
            full_path = self.auth_service_root / file_path
            if full_path.exists():
                has_uuid_import = self._file_imports_uuid(full_path)
                has_unified_id_import = self._file_imports_unified_id_manager(full_path)
                if has_uuid_import and (not has_unified_id_import):
                    import_violations.append((str(full_path), 'imports uuid but not UnifiedIDManager'))
        self.assertEqual(len(import_violations), 0, f'Found {len(import_violations)} files importing uuid without UnifiedIDManager: {import_violations}')

    def test_specific_violation_locations_exact_match(self):
        """
        EXACT LOCATION TEST: Test specific violation locations found in audit.
        
        This test targets the exact file:line violations discovered:
        - oauth_handler.py line 65: state_token = str(uuid.uuid4())
        - oauth_handler.py line 161: "session_id": str(uuid.uuid4())
        - oauth_handler.py line 162: "user_id": str(uuid.uuid4())
        
        Expected behavior: FAIL initially at exact locations, PASS after specific fixes
        """
        specific_violations = []
        oauth_handler_path = self.auth_service_root / 'auth_core/oauth/oauth_handler.py'
        if oauth_handler_path.exists():
            with open(oauth_handler_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            violation_lines = [65, 161, 162]
            for line_num in violation_lines:
                if line_num <= len(lines):
                    line_content = lines[line_num - 1].strip()
                    if 'uuid.uuid4()' in line_content:
                        specific_violations.append(f'{oauth_handler_path}:{line_num} - {line_content}')
        self.assertEqual(len(specific_violations), 0, f'Found exact violations at known locations: {specific_violations}')

    def _scan_file_for_uuid4_violations(self, file_path: Path) -> List[Tuple[str, int, str]]:
        """
        Scan a Python file for direct uuid.uuid4() usage.
        
        Args:
            file_path: Path to Python file to scan
            
        Returns:
            List of tuples: (file_path, line_number, line_content)
        """
        violations = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if 'uuid.uuid4()' in line:
                        violations.append((str(file_path), line_num, line.strip()))
        except Exception as e:
            print(f'Warning: Could not scan {file_path}: {e}')
        return violations

    def _file_imports_uuid(self, file_path: Path) -> bool:
        """Check if file imports uuid module."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return 'import uuid' in content or 'from uuid import' in content
        except Exception:
            return False

    def _file_imports_unified_id_manager(self, file_path: Path) -> bool:
        """Check if file imports UnifiedIDManager."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return 'UnifiedIDManager' in content and 'import' in content
        except Exception:
            return False

    def _format_violations(self, violations: List[Tuple[str, int, str]]) -> str:
        """Format violation list for readable output."""
        if not violations:
            return 'None'
        formatted = []
        for file_path, line_num, line_content in violations:
            rel_path = str(Path(file_path).relative_to(Path('C:/GitHub/netra-apex')))
            formatted.append(f'{rel_path}:{line_num} - {line_content}')
        return '; '.join(formatted)

    def tearDown(self):
        """Clean up and report violations found."""
        super().tearDown()
        if self.violations_found:
            print(f'\nVIOLATION SUMMARY: Found {len(self.violations_found)} total violations:')
            for violation in self.violations_found[:20]:
                print(f'  {violation}')
            if len(self.violations_found) > 20:
                print(f'  ... and {len(self.violations_found) - 20} more')

class TestUnifiedIDManagerCorrectUsage(SSotBaseTestCase):
    """Test correct UnifiedIDManager usage patterns."""

    def test_unified_id_manager_basic_functionality(self):
        """Test that UnifiedIDManager works correctly for ID generation."""
        manager = get_id_manager()
        user_id = manager.generate_id(IDType.USER)
        session_id = manager.generate_id(IDType.SESSION)
        self.assertNotEqual(user_id, session_id)
        self.assertTrue(manager.is_valid_id(user_id, IDType.USER))
        self.assertTrue(manager.is_valid_id(session_id, IDType.SESSION))

    def test_unified_id_manager_vs_raw_uuid(self):
        """
        Demonstrate correct vs incorrect ID generation patterns.
        
        This test shows what code SHOULD look like after remediation.
        """
        manager = get_id_manager()
        correct_user_id = manager.generate_id(IDType.USER, prefix='auth')
        correct_session_id = manager.generate_id(IDType.SESSION, context={'service': 'auth'})
        incorrect_raw_uuid = str(uuid.uuid4())
        self.assertTrue(manager.is_valid_id(correct_user_id))
        self.assertTrue(manager.is_valid_id(correct_session_id))
        self.assertFalse(manager.is_valid_id(incorrect_raw_uuid))
        self.assertIn('user_', correct_user_id)
        self.assertIn('session_', correct_session_id)
        self.assertNotIn('user_', incorrect_raw_uuid)
        self.assertNotIn('session_', incorrect_raw_uuid)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')