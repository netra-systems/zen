"""
"""
SSOT File Reference Migration Tests for Issue #1076

"""
"""
Test Plan: Detect files that still reference deprecated import paths or modules.
Should FAIL initially (detecting remaining references) and PASS after migration.

Key violations to detect:
1. Files still importing from deprecated logging_config
2. Files using legacy auth patterns instead of SSOT auth service
3. Files referencing non-SSOT configuration modules
4. Import path consistency across the codebase

Related Issues: #1076 - SSOT compliance verification
Priority: CRITICAL - These tests ensure complete migration to SSOT patterns
"
"

import pytest
from pathlib import Path
import sys
import re
from typing import Dict, List, Set, Tuple

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class SSotFileReferenceMigrationTests(SSotBaseTestCase):
    "Tests to detect file reference violations that need SSOT migration."

    @property
    def project_root(self):
        "Get project root path."
        return Path(__file__).parent.parent.parent

    def test_logging_config_migration_completion(self):
        """
        "
        CRITICAL: Ensure all files have migrated from deprecated logging_config.

        EXPECTED: Should FAIL initially - detects remaining logging_config references
        REMEDIATION: Replace with 'from shared.logging.unified_logging_ssot import get_logger'
"
"
        remaining_references = []

        # Search patterns for deprecated logging imports
        deprecated_patterns = [
            r'from netra_backend\.app\.logging_config import',
            r'import netra_backend\.app\.logging_config',
            r'netra_backend\.app\.logging_config\.',
            r'logging_config\.central_logger',
            r'central_logger'  # Often indicates legacy usage
        ]

        # Search in critical production files (exclude tests for now)
        search_paths = [
            self.project_root / netra_backend / app","
            self.project_root / "auth_service,"
            self.project_root / shared
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for py_file in search_path.rglob("*.py):"
                if py_file.name.startswith(__) or test in py_file.name.lower():
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    for pattern in deprecated_patterns:
                        matches = re.finditer(pattern, content, re.MULTILINE)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            line_content = content.split('\n')[line_num - 1].strip()

                            remaining_references.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': line_num,
                                'pattern': pattern,
                                'content': line_content,
                                'violation_type': 'deprecated_logging_import'
                            }

                except Exception as e:
                    continue

        # This test should FAIL initially if deprecated logging references exist
        if remaining_references:
            violation_details = \n.join(["
            violation_details = \n.join(["
                f"  - {ref['file']}:{ref['line']} - {ref['content']}"
                for ref in remaining_references[:20]  # Limit output
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(remaining_references)} deprecated logging_config references:\n
                f{violation_details}\n
                f{'... and more' if len(remaining_references) > 20 else ''}\n\n""
                fREMEDIATION REQUIRED:\n
                f1. Replace 'from netra_backend.app.logging_config import central_logger' with:\n
                f"   'from shared.logging.unified_logging_ssot import get_logger'\n"
                f2. Update logger usage: logger = get_logger(__name__)\n"
                f2. Update logger usage: logger = get_logger(__name__)\n"
                f3. Update all central_logger references to use the new logger
            )

    def test_auth_service_import_consistency(self):
        """
        "
        CRITICAL: Ensure consistent auth service import patterns across codebase.

        EXPECTED: Should FAIL initially - detects inconsistent auth imports
        REMEDIATION: Standardize on SSOT auth service patterns
"
"
        auth_import_violations = []
        auth_import_patterns = {}

        # Expected SSOT auth import patterns
        expected_patterns = [
            from auth_service.auth_core.core.jwt_handler import,"
            from auth_service.auth_core.core.jwt_handler import,"
            from auth_service.auth_core.core.session_manager import","
            from auth_service.auth_core.core.token_validator import
        ]

        # Deprecated auth import patterns to detect
        deprecated_patterns = [
            r'from netra_backend\.app\.auth_integration import validate_jwt',
            r'from netra_backend\.app\.auth_integration\.auth import',
            r'import netra_backend\.app\.auth_integration',
            r'from auth_service\.legacy import'
        ]

        # Search in key directories
        search_paths = [
            self.project_root / netra_backend" / app,"
            self.project_root / auth_service,
            self.project_root / shared"
            self.project_root / shared"
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for py_file in search_path.rglob(*.py"):"
                if py_file.name.startswith(__) or test in py_file.name.lower():
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check for deprecated auth patterns
                    for pattern in deprecated_patterns:
                        matches = re.finditer(pattern, content, re.MULTILINE)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            line_content = content.split('\n')[line_num - 1].strip()

                            auth_import_violations.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': line_num,
                                'pattern': pattern,
                                'content': line_content,
                                'violation_type': 'deprecated_auth_import'
                            }

                    # Track auth import patterns for consistency analysis
                    auth_imports = re.findall(r'from auth_service\.[^\s]+ import|import auth_service\.[^\s]+', content)
                    if auth_imports:
                        file_key = str(py_file.relative_to(self.project_root))
                        auth_import_patterns[file_key] = auth_imports

                except Exception as e:
                    continue

        # This test should FAIL initially if deprecated auth imports exist
        if auth_import_violations:
            violation_details = "\n.join(["
                f  - {viol['file']}:{viol['line']} - {viol['content']}
                for viol in auth_import_violations[:15]  # Limit output
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(auth_import_violations)} deprecated auth import patterns:\n
                f{violation_details}\n""
                f{'... and more' if len(auth_import_violations) > 15 else ''}\n\n
                fREMEDIATION REQUIRED:\n
                f"1. Replace deprecated auth imports with SSOT auth service imports\n"
                f2. Use direct auth_service imports instead of backend wrappers\n"
                f2. Use direct auth_service imports instead of backend wrappers\n"
                f3. Ensure auth_service is the single source of truth for auth operations
            )

    def test_configuration_import_migration(self):
        """
        "
        CRITICAL: Ensure all files use SSOT configuration patterns.

        EXPECTED: Should FAIL initially - detects non-SSOT config imports
        REMEDIATION: Migrate to unified configuration architecture
"
"
        config_violations = []

        # Deprecated configuration patterns
        deprecated_config_patterns = [
            r'from netra_backend\.app\.config import',
            r'import netra_backend\.app\.config',
            r'os\.environ\[',  # Direct environment access
            r'os\.getenv\(',   # Direct environment access
            r'from os import environ'
        ]

        # Expected SSOT configuration patterns
        expected_patterns = [
            from netra_backend.app.core.configuration,"
            from netra_backend.app.core.configuration,"
            from shared.logging.unified_logging_ssot","
            from dev_launcher.isolated_environment import IsolatedEnvironment
        ]

        search_paths = [
            self.project_root / netra_backend" / app,"
            self.project_root / auth_service,
            self.project_root / shared"
            self.project_root / shared"
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for py_file in search_path.rglob(*.py"):"
                if py_file.name.startswith(__) or test in py_file.name.lower():
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    for pattern in deprecated_config_patterns:
                        matches = re.finditer(pattern, content, re.MULTILINE)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            line_content = content.split('\n')[line_num - 1].strip()

                            # Skip if it's in a comment or string literal'
                            if line_content.strip().startswith('#'):
                                continue

                            config_violations.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': line_num,
                                'pattern': pattern,
                                'content': line_content,
                                'violation_type': 'deprecated_config_access'
                            }

                except Exception as e:
                    continue

        # This test should FAIL initially if deprecated config access exists
        if config_violations:
            violation_details = "\n.join(["
                f  - {viol['file']}:{viol['line']} - {viol['content']}
                for viol in config_violations[:20]  # Limit output
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(config_violations)} deprecated configuration access patterns:\n
                f{violation_details}\n""
                f{'... and more' if len(config_violations) > 20 else ''}\n\n
                fREMEDIATION REQUIRED:\n
                f"1. Replace direct os.environ access with IsolatedEnvironment\n"
                f2. Use SSOT configuration modules from netra_backend.app.core.configuration\n"
                f2. Use SSOT configuration modules from netra_backend.app.core.configuration\n"
                f3. Ensure environment access follows SSOT patterns
            )

    def test_websocket_import_consistency(self):
        """
        "
        CRITICAL: Ensure WebSocket imports use SSOT patterns consistently.

        EXPECTED: Should FAIL initially - detects inconsistent WebSocket imports
        REMEDIATION: Standardize WebSocket imports to SSOT patterns
"
"
        websocket_violations = []

        # Deprecated WebSocket import patterns
        deprecated_websocket_patterns = [
            r'from netra_backend\.app\.websocket import',  # Old direct import
            r'import netra_backend\.app\.websocket[^_]',   # Old module import
            r'from websocket_manager import',              # Non-SSOT import
            r'from .*websocket_legacy',                    # Legacy patterns
        ]

        # Expected SSOT WebSocket patterns
        expected_patterns = [
            from netra_backend.app.websocket_core.websocket_manager import,"
            from netra_backend.app.websocket_core.websocket_manager import,"
            from netra_backend.app.websocket_core.manager import","
            from netra_backend.app.routes.websocket import
        ]

        search_paths = [
            self.project_root / netra_backend" / app,"
            self.project_root / shared
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for py_file in search_path.rglob(*.py):"
            for py_file in search_path.rglob(*.py):"
                if py_file.name.startswith(__") or test in py_file.name.lower():"
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    for pattern in deprecated_websocket_patterns:
                        matches = re.finditer(pattern, content, re.MULTILINE)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            line_content = content.split('\n')[line_num - 1].strip()

                            websocket_violations.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': line_num,
                                'pattern': pattern,
                                'content': line_content,
                                'violation_type': 'deprecated_websocket_import'
                            }

                except Exception as e:
                    continue

        # This test should FAIL initially if deprecated WebSocket imports exist
        if websocket_violations:
            violation_details = \n.join([
                f"  - {viol['file']}:{viol['line']} - {viol['content']}"
                for viol in websocket_violations[:10]  # Limit output
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(websocket_violations)} deprecated WebSocket import patterns:\n"
                fSSOT VIOLATION: Found {len(websocket_violations)} deprecated WebSocket import patterns:\n"
                f{violation_details}\n
                f{'... and more' if len(websocket_violations) > 10 else ''}\n\n"
                f{'... and more' if len(websocket_violations) > 10 else ''}\n\n"
                f"REMEDIATION REQUIRED:\n"
                f1. Replace deprecated WebSocket imports with SSOT patterns\n
                f2. Use websocket_core modules for all WebSocket operations\n
                f3. Ensure consistent WebSocket architecture across codebase""
            )

    def test_import_path_consistency_audit(self):
        pass
        CRITICAL: Comprehensive audit of import path consistency across services.

        EXPECTED: Should FAIL initially - detects import path inconsistencies
        REMEDIATION: Standardize all import paths to SSOT patterns
        ""
        import_inconsistencies = []
        import_usage_patterns = {}

        # Track import patterns across the codebase
        search_paths = [
            self.project_root / netra_backend,
            self.project_root / auth_service,"
            self.project_root / auth_service,"
            self.project_root / shared"
            self.project_root / shared"
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for py_file in search_path.rglob(*.py):
                if py_file.name.startswith(__") or test in py_file.name.lower():"
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Extract all import statements
                    import_lines = []
                    for line_num, line in enumerate(content.split('\n'), 1):
                        line = line.strip()
                        if line.startswith(('from ', 'import ')) and not line.startswith('#'):
                            import_lines.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': line_num,
                                'import': line
                            }

                    # Check for specific inconsistency patterns
                    for import_info in import_lines:
                        import_line = import_info['import']

                        # Check for mixed auth patterns within same file
                        if 'auth_service' in import_line and 'auth_integration' in content:
                            import_inconsistencies.append({
                                **import_info,
                                'violation_type': 'mixed_auth_patterns',
                                'reason': 'File uses both auth_service and auth_integration'
                            }

                        # Check for mixed logging patterns
                        if 'shared.logging' in import_line and 'logging_config' in content:
                            import_inconsistencies.append({
                                **import_info,
                                'violation_type': 'mixed_logging_patterns',
                                'reason': 'File uses both SSOT and legacy logging'
                            }

                        # Check for direct environment access alongside SSOT config
                        if 'IsolatedEnvironment' in import_line and 'os.environ' in content:
                            import_inconsistencies.append({
                                **import_info,
                                'violation_type': 'mixed_env_access',
                                'reason': 'File uses both IsolatedEnvironment and direct os.environ'
                            }

                except Exception as e:
                    continue

        # This test should FAIL initially if import inconsistencies exist
        if import_inconsistencies:
            violation_details = \n.join([
                f  - {inc['file']):{inc['line']) - {inc['import']) ({inc['reason'])
                for inc in import_inconsistencies[:15]  # Limit output
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(import_inconsistencies)} import path inconsistencies:\n""
                f{violation_details}\n
                f{'... and more' if len(import_inconsistencies) > 15 else ''}\n\n
                f"REMEDIATION REQUIRED:\n"
                f1. Resolve mixed patterns within individual files\n"
                f1. Resolve mixed patterns within individual files\n"
                f2. Choose SSOT pattern consistently throughout each file\n
                f3. Remove all deprecated import patterns\n"
                f3. Remove all deprecated import patterns\n"
                f"4. Ensure service boundaries are respected in imports"
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v')
)))))))))))))))))
]]