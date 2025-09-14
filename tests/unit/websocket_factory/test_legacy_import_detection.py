"""
Unit Tests for WebSocket Factory Legacy Import Detection (Issue #1128)

PURPOSE: Detect legacy import patterns that bypass SSOT WebSocket factory patterns.
These tests should FAIL initially to demonstrate the scope of legacy imports,
then PASS after import cleanup is complete.

Business Impact: $500K+ ARR chat functionality depends on proper WebSocket SSOT patterns.
"""

import os
import re
import pytest
from pathlib import Path
from typing import List, Dict, Set, Tuple


class TestWebSocketLegacyImportDetection:
    """
    Test suite to detect and validate WebSocket import patterns across the codebase.

    EXPECTED BEHAVIOR:
    - Tests should FAIL initially showing legacy import violations
    - Tests should PASS after SSOT import cleanup
    - Provides clear reporting on scope of legacy imports
    """

    @pytest.fixture
    def codebase_root(self) -> Path:
        """Get the codebase root directory."""
        return Path(__file__).parent.parent.parent.parent

    @pytest.fixture
    def legacy_import_patterns(self) -> List[str]:
        """Define legacy import patterns that should be eliminated."""
        return [
            # Legacy unified manager imports (should use websocket_manager.py)
            r"from\s+netra_backend\.app\.websocket_core\.unified_manager\s+import",
            r"from\s+netra_backend\.app\.websocket_core\s+import\s+.*UnifiedWebSocketManager",

            # Legacy factory imports (deprecated patterns)
            r"from\s+netra_backend\.app\.websocket_core\.factory\s+import",
            r"from\s+netra_backend\.app\.websocket_core\.websocket_factory\s+import",

            # Legacy direct websocket_core module imports (should be specific)
            r"from\s+netra_backend\.app\.websocket_core\s+import\s+WebSocketManager",

            # Legacy supervisor factory imports (wrong location)
            r"from\s+netra_backend\.app\.websocket_core\.supervisor_factory\s+import",

            # Legacy auth patterns
            r"from\s+netra_backend\.app\.websocket_core\.auth\s+import\s+.*(?:secure_websocket_context|WebSocketAuthenticator)",
        ]

    @pytest.fixture
    def canonical_import_patterns(self) -> List[str]:
        """Define canonical SSOT import patterns that should be used."""
        return [
            # SSOT WebSocket manager imports
            r"from\s+netra_backend\.app\.websocket_core\.websocket_manager\s+import\s+WebSocketManager",
            r"from\s+netra_backend\.app\.websocket_core\.websocket_manager\s+import\s+get_websocket_manager",
            r"from\s+netra_backend\.app\.websocket_core\.websocket_manager\s+import\s+WebSocketConnection",

            # SSOT auth patterns
            r"from\s+netra_backend\.app\.websocket_core\.auth\s+import\s+WebSocketAuth",

            # SSOT factory patterns (if any legitimate factories exist)
            r"from\s+netra_backend\.app\.agents\.supervisor\.agent_instance_factory\s+import",
        ]

    def scan_files_for_patterns(self, root_path: Path, patterns: List[str],
                               exclude_dirs: Set[str] = None) -> Dict[str, List[Tuple[int, str]]]:
        """
        Scan Python files for import patterns.

        Returns:
            Dict mapping file paths to list of (line_number, matched_line) tuples
        """
        if exclude_dirs is None:
            exclude_dirs = {
                '.git', '__pycache__', 'node_modules', '.pytest_cache',
                'backup', 'backups', 'backup_untracked', 'build', 'dist'
            }

        violations = {}

        for py_file in root_path.rglob("*.py"):
            # Skip excluded directories
            if any(exclude_dir in py_file.parts for exclude_dir in exclude_dirs):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                file_violations = []
                for line_num, line in enumerate(lines, 1):
                    for pattern in patterns:
                        if re.search(pattern, line.strip()):
                            file_violations.append((line_num, line.strip()))

                if file_violations:
                    violations[str(py_file)] = file_violations

            except (UnicodeDecodeError, PermissionError):
                # Skip files that can't be read
                continue

        return violations

    def test_legacy_websocket_import_detection(self, codebase_root, legacy_import_patterns):
        """
        Test that detects legacy WebSocket import patterns.

        EXPECTED: This test should FAIL initially, showing all legacy imports.
        After cleanup: This test should PASS with no violations.
        """
        legacy_violations = self.scan_files_for_patterns(
            codebase_root,
            legacy_import_patterns,
            exclude_dirs={'backup', 'backups', 'backup_untracked', 'build', 'dist', '.git'}
        )

        if legacy_violations:
            violation_report = "\n".join([
                f"\n📁 {file_path}:" + "\n".join([
                    f"  Line {line_num}: {line}"
                    for line_num, line in violations
                ])
                for file_path, violations in legacy_violations.items()
            ])

            # This should fail initially to show scope
            pytest.fail(
                f"🚨 LEGACY IMPORT VIOLATIONS DETECTED (Issue #1128)\n"
                f"Found {len(legacy_violations)} files with {sum(len(v) for v in legacy_violations.values())} legacy imports:\n"
                f"{violation_report}\n\n"
                f"❌ These imports bypass SSOT WebSocket factory patterns\n"
                f"💰 Business Impact: $500K+ ARR chat functionality at risk\n"
                f"🔧 Action Required: Replace with canonical SSOT import patterns"
            )

    def test_canonical_websocket_import_validation(self, codebase_root, canonical_import_patterns):
        """
        Test that validates canonical SSOT WebSocket import patterns exist and are accessible.

        EXPECTED: This test should PASS, confirming canonical patterns are available.
        """
        # Test that canonical imports can be resolved
        canonical_imports_found = self.scan_files_for_patterns(
            codebase_root,
            canonical_import_patterns,
            exclude_dirs={'backup', 'backups', 'backup_untracked', 'test', 'tests'}
        )

        # Verify websocket_manager.py exists
        websocket_manager_path = codebase_root / "netra_backend" / "app" / "websocket_core" / "websocket_manager.py"
        assert websocket_manager_path.exists(), (
            f"❌ Canonical WebSocket manager not found at {websocket_manager_path}\n"
            f"🔧 Required for SSOT WebSocket import patterns"
        )

        # Test import resolution
        try:
            # This should work if SSOT patterns are properly implemented
            import sys
            backend_path = str(codebase_root / "netra_backend")
            if backend_path not in sys.path:
                sys.path.insert(0, backend_path)

            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            assert WebSocketManager is not None, "WebSocketManager class should be importable"

        except ImportError as e:
            pytest.fail(
                f"❌ Canonical import failed: {e}\n"
                f"🔧 SSOT WebSocket patterns not properly implemented"
            )

    def test_websocket_core_file_structure_compliance(self, codebase_root):
        """
        Test WebSocket core directory structure for SSOT compliance.

        EXPECTED: Should validate proper file organization supports SSOT patterns.
        """
        websocket_core_path = codebase_root / "netra_backend" / "app" / "websocket_core"

        # Required SSOT files
        required_files = [
            "websocket_manager.py",  # Primary SSOT manager
            "auth.py",               # WebSocket authentication
            "__init__.py"            # Module initialization
        ]

        missing_files = []
        for required_file in required_files:
            file_path = websocket_core_path / required_file
            if not file_path.exists():
                missing_files.append(required_file)

        assert not missing_files, (
            f"❌ Missing required SSOT WebSocket files: {missing_files}\n"
            f"📁 Expected in: {websocket_core_path}\n"
            f"🔧 Required for proper SSOT WebSocket factory patterns"
        )

        # Check for problematic legacy files that should be consolidated
        legacy_files_to_check = [
            "unified_manager.py",      # Should be consolidated into websocket_manager.py
            "factory.py",              # Should use agent factory patterns
            "websocket_factory.py"     # Should use agent factory patterns
        ]

        found_legacy_files = []
        for legacy_file in legacy_files_to_check:
            file_path = websocket_core_path / legacy_file
            if file_path.exists():
                found_legacy_files.append(legacy_file)

        if found_legacy_files:
            print(f"⚠️  Legacy files detected (may need consolidation): {found_legacy_files}")

    def test_websocket_import_fragmentation_scope(self, codebase_root):
        """
        Test to measure the scope of WebSocket import fragmentation.

        EXPECTED: Provides metrics on import pattern fragmentation.
        """
        all_websocket_imports = self.scan_files_for_patterns(
            codebase_root,
            [r"from\s+netra_backend\.app\.websocket_core\..*\s+import"],
            exclude_dirs={'backup', 'backups', 'backup_untracked'}
        )

        # Categorize imports by module
        import_categories = {}
        for file_path, violations in all_websocket_imports.items():
            for line_num, line in violations:
                # Extract module name
                match = re.search(r"from\s+netra_backend\.app\.websocket_core\.(\w+)", line)
                if match:
                    module_name = match.group(1)
                    if module_name not in import_categories:
                        import_categories[module_name] = []
                    import_categories[module_name].append((file_path, line_num, line))

        # Report fragmentation metrics
        total_files = len(all_websocket_imports)
        total_imports = sum(len(violations) for violations in all_websocket_imports.values())

        fragmentation_report = f"""
📊 WebSocket Import Fragmentation Analysis (Issue #1128):
📁 Files with websocket_core imports: {total_files}
📥 Total websocket_core imports: {total_imports}
🔀 Unique modules imported: {len(import_categories)}

🗂️  Import distribution by module:
""" + "\n".join([
    f"  {module}: {len(imports)} imports"
    for module, imports in sorted(import_categories.items(), key=lambda x: len(x[1]), reverse=True)
])

        print(fragmentation_report)

        # This is informational - only fail if scope is extreme
        if total_files > 100:  # Arbitrary threshold for "extreme fragmentation"
            pytest.fail(
                f"🚨 EXTREME WEBSOCKET IMPORT FRAGMENTATION DETECTED\n"
                f"📁 {total_files} files importing from websocket_core\n"
                f"💰 Business Risk: Import fragmentation complicates SSOT migration\n"
                f"🔧 Recommendation: Prioritize SSOT consolidation"
            )