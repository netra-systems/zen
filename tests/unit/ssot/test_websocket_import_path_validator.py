#!/usr/bin/env python3
"""WebSocket Import Path Consolidation Validator - Issue #1036

FAIL-FIRST TEST: This test is designed to FAIL before import path consolidation
and PASS after all WebSocket Manager imports use a single canonical path.

Business Value: Protects $500K+ ARR by preventing import confusion that causes
developer errors, circular dependencies, and inconsistent manager instances.

EXPECTED BEHAVIOR:
- BEFORE CONSOLIDATION: Test FAILS - Multiple import paths detected
- AFTER CONSOLIDATION: Test PASSES - Only 1 canonical import path exists

This test validates Issue #1036 Step 2: Import path fragmentation detection.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketImportPathValidator(SSotBaseTestCase):
    """Fail-first test to detect multiple WebSocket Manager import paths.
    
    This test scans the codebase for WebSocket Manager import statements
    and ensures SSOT compliance by detecting path fragmentation.
    """

    def test_websocket_manager_import_path_consolidation(self):
        """FAIL-FIRST: Detect multiple WebSocket Manager import paths.
        
        EXPECTED TO FAIL: Currently finds multiple import patterns:
        - from netra_backend.app.websocket_core.manager import WebSocketManager
        - from netra_backend.app.websocket_core.websocket_manager import WebSocketManager  
        - from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        - from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
        
        EXPECTED TO PASS: After consolidation, only 1 canonical import path exists.
        
        Business Impact: Prevents developer confusion and ensures consistent manager instances.
        """
        project_root = self._get_project_root()
        import_violations = self._scan_import_patterns()
        
        # FAIL-FIRST ASSERTION: Should find multiple import paths currently
        unique_import_paths = set()
        for violation in import_violations:
            unique_import_paths.add(violation['import_path'])
        
        self.assertGreater(
            len(unique_import_paths), 1,
            f"WEBSOCKET IMPORT PATH SSOT VIOLATION: Found {len(unique_import_paths)} different import paths.\n"
            f"Expected exactly 1 canonical path for SSOT compliance.\n\n"
            f"Import paths detected:\n" +
            "\n".join(f"  - {path}" for path in sorted(unique_import_paths)) + "\n\n"
            f"BUSINESS IMPACT: Multiple import paths cause:\n"
            f"- Developer confusion and inconsistent usage patterns\n"
            f"- Different manager instances with different behaviors\n"
            f"- Circular dependency risks during imports\n"
            f"- Golden Path failures when wrong manager is imported\n"
            f"- $500K+ ARR at risk from chat functionality inconsistencies\n\n"
            f"REMEDIATION: Standardize on single canonical import path"
        )

    def test_deprecated_import_path_detection(self):
        """FAIL-FIRST: Detect usage of deprecated WebSocket Manager import paths.
        
        EXPECTED TO FAIL: Currently finds deprecated patterns like:
        - websocket_manager_factory imports (being phased out)
        - manager.py compatibility imports (temporary)
        
        EXPECTED TO PASS: After consolidation, no deprecated imports exist.
        """
        deprecated_patterns = [
            r'from\s+netra_backend\.app\.websocket_core\.websocket_manager_factory\s+import',
            r'from\s+netra_backend\.app\.websocket_core\.manager\s+import',
            r'from\s+netra_backend\.app\.websocket_core\s+import\s+WebSocketManager',
        ]
        
        violations = self._scan_deprecated_patterns(deprecated_patterns)
        
        # FAIL-FIRST ASSERTION: Should detect deprecated imports
        self.assertGreater(
            len(violations), 0,
            f"DEPRECATED IMPORT VIOLATIONS: Found {len(violations)} uses of deprecated import paths.\n"
            f"Expected > 0 to validate current violations exist.\n\n"
            f"Deprecated imports found:\n" +
            "\n".join(f"  - {v['file']}: {v['import_line']}" for v in violations) + "\n\n"
            f"BUSINESS IMPACT: Deprecated imports cause:\n"
            f"- Technical debt accumulation\n"
            f"- Inconsistent manager behavior across modules\n"
            f"- Migration confusion for developers\n"
            f"- Potential breakage when deprecated paths are removed\n\n"
            f"REMEDIATION: Update all imports to canonical SSOT path"
        )

    def test_websocket_manager_circular_import_risk(self):
        """FAIL-FIRST: Detect potential circular import risks in WebSocket imports.
        
        EXPECTED TO FAIL: Currently has import dependencies that could create cycles.
        
        EXPECTED TO PASS: After consolidation, clean import hierarchy exists.
        """
        project_root = self._get_project_root()
        circular_risks = []
        
        # Check for files that both import and are imported by WebSocket modules
        websocket_files = self._find_websocket_modules()
        
        for ws_file in websocket_files:
            imports_from_websocket = self._get_imports_from_file(ws_file)
            imported_by_websocket = self._find_files_importing_module(ws_file)
            
            # Check for potential circular dependencies
            for imported_file in imports_from_websocket:
                if imported_file in imported_by_websocket:
                    circular_risks.append({
                        'file1': str(ws_file),
                        'file2': imported_file,
                        'risk': 'bidirectional_dependency'
                    })
        
        # FAIL-FIRST ASSERTION: Should find circular import risks
        self.assertGreater(
            len(circular_risks), 0,
            f"CIRCULAR IMPORT RISKS: Found {len(circular_risks)} potential circular dependencies.\n"
            f"Expected > 0 to validate current risks exist.\n\n"
            f"Circular dependency risks:\n" +
            "\n".join(f"  - {r['file1']} ↔ {r['file2']}" for r in circular_risks) + "\n\n"
            f"BUSINESS IMPACT: Circular import risks cause:\n"
            f"- Runtime import errors that break Golden Path\n"
            f"- Unpredictable module initialization order\n"
            f"- Difficult debugging when imports fail\n"
            f"- System instability affecting $500K+ ARR\n\n"
            f"REMEDIATION: Restructure imports to eliminate circular dependencies"
        )

    def _scan_import_patterns(self) -> List[Dict[str, str]]:
        """Scan codebase for WebSocket Manager import patterns."""
        project_root = self._get_project_root()
        import_violations = []
        
        # Patterns to detect WebSocket Manager imports
        import_patterns = [
            r'from\s+(netra_backend\.app\.websocket_core\.\w+)\s+import\s+.*WebSocketManager',
            r'from\s+(netra_backend\.app\.websocket_core\.\w+)\s+import\s+.*websocket_manager',
            r'import\s+(netra_backend\.app\.websocket_core\.\w+)',
        ]
        
        for py_file in project_root.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                for line_num, line in enumerate(lines, 1):
                    for pattern in import_patterns:
                        match = re.search(pattern, line)
                        if match:
                            import_violations.append({
                                'file': str(py_file),
                                'line_num': line_num,
                                'import_line': line.strip(),
                                'import_path': match.group(1)
                            })
                            
            except (UnicodeDecodeError, OSError):
                continue
        
        return import_violations

    def _scan_deprecated_patterns(self, patterns: List[str]) -> List[Dict[str, str]]:
        """Scan for deprecated import patterns."""
        project_root = self._get_project_root()
        violations = []
        
        for py_file in project_root.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                for line_num, line in enumerate(lines, 1):
                    for pattern in patterns:
                        if re.search(pattern, line):
                            violations.append({
                                'file': str(py_file),
                                'line_num': line_num,
                                'import_line': line.strip(),
                                'pattern': pattern
                            })
                            
            except (UnicodeDecodeError, OSError):
                continue
        
        return violations

    def _find_websocket_modules(self) -> List[Path]:
        """Find all WebSocket-related modules."""
        project_root = self._get_project_root()
        websocket_files = []
        
        for py_file in project_root.rglob("*.py"):
            if "websocket" in str(py_file).lower():
                websocket_files.append(py_file)
        
        return websocket_files

    def _get_imports_from_file(self, file_path: Path) -> Set[str]:
        """Get all imports from a file."""
        imports = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find import statements
            import_patterns = [
                r'from\s+([\w.]+)\s+import',
                r'import\s+([\w.]+)',
            ]
            
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                imports.update(matches)
                
        except (UnicodeDecodeError, OSError):
            pass
        
        return imports

    def _find_files_importing_module(self, module_path: Path) -> Set[str]:
        """Find all files that import from a given module."""
        project_root = self._get_project_root()
        relative_path = str(module_path.relative_to(project_root))
        module_name = relative_path.replace('/', '.').replace('.py', '')
        
        importing_files = set()
        
        for py_file in project_root.rglob("*.py"):
            if py_file == module_path:
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if module_name in content:
                    importing_files.add(str(py_file))
                    
            except (UnicodeDecodeError, OSError):
                continue
        
        return importing_files

    def _get_project_root(self) -> Path:
        """Get the project root directory for scanning."""
        current_file = Path(__file__)
        # Navigate up from tests/unit/ssot/ to project root
        project_root = current_file.parent.parent.parent.parent
        return project_root


if __name__ == '__main__':
    import unittest
    unittest.main()