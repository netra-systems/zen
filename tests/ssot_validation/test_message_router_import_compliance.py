"""Test 3: MessageRouter Import Path Validation

This test ensures all MessageRouter imports use the canonical SSOT path to prevent
import inconsistencies that cause connection failures and WebSocket race conditions.

Business Value: Platform/Internal - Import Consistency & Golden Path Protection
- Prevents import path drift causing module resolution failures
- Ensures consistent MessageRouter instantiation across all usage points
- Protects chat functionality from import-related startup failures

EXPECTED BEHAVIOR:
- FAIL initially: 135+ files with inconsistent import paths detected
- PASS after import standardization: All imports use canonical SSOT path

GitHub Issue: #217 - MessageRouter SSOT violations blocking golden path
"""

import ast
import re
from typing import Dict, List, Set, Optional, Tuple, Any
from pathlib import Path
from collections import defaultdict

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestMessageRouterImportCompliance(SSotBaseTestCase):
    """Test that all MessageRouter imports use canonical SSOT path."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        # Expected canonical import path after SSOT consolidation
        self.canonical_import_path = "netra_backend.app.websocket_core.handlers"
        self.canonical_import_statement = f"from {self.canonical_import_path} import MessageRouter"
        
        self.base_path = Path(__file__).parent.parent.parent
        
        # Track different import patterns found
        self.import_violations: Dict[str, List[str]] = defaultdict(list)
        self.total_files_scanned = 0
        self.files_with_imports = 0

    def test_all_message_router_imports_use_canonical_path(self):
        """Test that all MessageRouter imports use the canonical SSOT path.
        
        EXPECTED: FAIL initially - Multiple import paths detected across 135+ files
        EXPECTED: PASS after standardization - All imports use canonical path
        """
        import_analysis = self._analyze_all_message_router_imports()
        
        self.total_files_scanned = sum(len(files) for files in import_analysis.values())
        self.files_with_imports = len(set().union(*import_analysis.values()))
        
        # Log import analysis results
        self.logger.info(f"Scanned for MessageRouter imports - Files with imports: {self.files_with_imports}")
        
        if not import_analysis:
            self.fail(
                "No MessageRouter imports found! This indicates either:\n"
                "1. Scanner failed to detect imports (bug in test)\n"
                "2. MessageRouter has been completely removed (breaks chat functionality)\n"
                "3. All imports have been refactored to different patterns"
            )
        
        # Check for import path consistency
        non_canonical_imports = {}
        canonical_files = set()
        
        for import_path, files in import_analysis.items():
            if self.canonical_import_path in import_path:
                canonical_files.update(files)
            else:
                non_canonical_imports[import_path] = files
        
        if non_canonical_imports:
            violation_summary = self._format_import_violations(non_canonical_imports)
            total_violating_files = sum(len(files) for files in non_canonical_imports.values())
            
            self.fail(
                f"❌ IMPORT PATH VIOLATIONS: {len(non_canonical_imports)} different "
                f"non-canonical import paths found across {total_violating_files} files.\n"
                f"BUSINESS IMPACT: Inconsistent imports cause module resolution failures, "
                f"WebSocket connection errors, and chat functionality breakdown.\n"
                f"CANONICAL PATH: {self.canonical_import_path}\n"
                f"VIOLATING IMPORTS:\n{violation_summary}"
            )
        
        self.logger.info(
            f"✅ All {len(canonical_files)} files use canonical import path: {self.canonical_import_path}"
        )

    def test_no_relative_message_router_imports(self):
        """Test that no relative imports are used for MessageRouter.
        
        EXPECTED: FAIL initially - Relative imports detected
        EXPECTED: PASS after standardization - Only absolute imports used
        """
        relative_imports = self._find_relative_message_router_imports()
        
        if relative_imports:
            relative_summary = self._format_relative_import_violations(relative_imports)
            self.fail(
                f"❌ RELATIVE IMPORT VIOLATIONS: {len(relative_imports)} files use "
                f"relative imports for MessageRouter.\n"
                f"BUSINESS IMPACT: Relative imports break when modules are moved or "
                f"refactored, causing import errors and chat failures.\n"
                f"REQUIREMENT: All imports must be absolute.\n"
                f"RELATIVE IMPORTS FOUND:\n{relative_summary}"
            )
        
        self.logger.info("✅ No relative MessageRouter imports detected")

    def test_no_wildcard_imports_containing_message_router(self):
        """Test that no wildcard imports are used that might import MessageRouter.
        
        EXPECTED: FAIL initially - Wildcard imports from router modules detected
        EXPECTED: PASS after standardization - Explicit imports only
        """
        wildcard_imports = self._find_wildcard_imports_with_message_router()
        
        if wildcard_imports:
            wildcard_summary = self._format_wildcard_import_violations(wildcard_imports)
            self.fail(
                f"❌ WILDCARD IMPORT VIOLATIONS: {len(wildcard_imports)} files use "
                f"wildcard imports that may include MessageRouter.\n"
                f"BUSINESS IMPACT: Wildcard imports create namespace pollution and "
                f"make it unclear where MessageRouter originates, complicating debugging.\n"
                f"REQUIREMENT: Use explicit imports only.\n"
                f"WILDCARD IMPORTS FOUND:\n{wildcard_summary}"
            )
        
        self.logger.info("✅ No wildcard imports containing MessageRouter detected")

    def test_import_statement_formatting_consistency(self):
        """Test that MessageRouter import statements follow consistent formatting.
        
        EXPECTED: FAIL initially - Inconsistent formatting across files
        EXPECTED: PASS after standardization - Consistent import formatting
        """
        import_statements = self._analyze_import_statement_formatting()
        
        # Find unique formatting patterns
        unique_patterns = set(import_statements.values())
        
        if len(unique_patterns) > 1:
            formatting_analysis = self._group_files_by_import_pattern(import_statements)
            pattern_summary = self._format_pattern_inconsistencies(formatting_analysis)
            
            self.fail(
                f"❌ IMPORT FORMATTING INCONSISTENCY: {len(unique_patterns)} different "
                f"formatting patterns found for MessageRouter imports.\n"
                f"BUSINESS IMPACT: Inconsistent formatting makes code maintenance harder "
                f"and can lead to import statement errors during refactoring.\n"
                f"EXPECTED FORMAT: {self.canonical_import_statement}\n"
                f"PATTERNS FOUND:\n{pattern_summary}"
            )
        
        self.logger.info("✅ All MessageRouter imports use consistent formatting")

    def test_no_dynamic_message_router_imports(self):
        """Test that no dynamic imports are used for MessageRouter.
        
        EXPECTED: FAIL initially - Dynamic imports detected via importlib
        EXPECTED: PASS after standardization - Static imports only
        """
        dynamic_imports = self._find_dynamic_message_router_imports()
        
        if dynamic_imports:
            dynamic_summary = self._format_dynamic_import_violations(dynamic_imports)
            self.fail(
                f"❌ DYNAMIC IMPORT VIOLATIONS: {len(dynamic_imports)} files use "
                f"dynamic imports for MessageRouter.\n"
                f"BUSINESS IMPACT: Dynamic imports bypass static analysis, make "
                f"dependencies unclear, and can fail at runtime with cryptic errors.\n"
                f"REQUIREMENT: Use static imports only.\n"
                f"DYNAMIC IMPORTS FOUND:\n{dynamic_summary}"
            )
        
        self.logger.info("✅ No dynamic MessageRouter imports detected")

    def _analyze_all_message_router_imports(self) -> Dict[str, List[str]]:
        """Analyze all MessageRouter import statements in the codebase."""
        import_analysis = defaultdict(list)
        
        for py_file in self.base_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                imports = self._extract_message_router_imports(py_file)
                for import_path in imports:
                    import_analysis[import_path].append(str(py_file))
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return dict(import_analysis)

    def _extract_message_router_imports(self, file_path: Path) -> List[str]:
        """Extract MessageRouter import paths from a single file."""
        import_paths = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST for precise import detection
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if (node.module and 
                            any(alias.name == 'MessageRouter' or 'MessageRouter' in str(alias.name) 
                                for alias in (node.names or []))):
                            import_paths.append(node.module)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if 'MessageRouter' in alias.name:
                                import_paths.append(alias.name)
                                
            except SyntaxError:
                # Fallback to regex if AST parsing fails
                import_paths.extend(self._regex_extract_imports(content))
                
        except (UnicodeDecodeError, PermissionError):
            pass
            
        return import_paths

    def _regex_extract_imports(self, content: str) -> List[str]:
        """Extract imports using regex as fallback."""
        import_paths = []
        
        # Match "from module import MessageRouter"
        from_pattern = r'from\s+([\w.]+)\s+import.*MessageRouter'
        for match in re.finditer(from_pattern, content):
            import_paths.append(match.group(1))
        
        # Match "import module.MessageRouter" or "import module"
        import_pattern = r'import\s+([\w.]+(?:\.MessageRouter)?)'
        for match in re.finditer(import_pattern, content):
            module = match.group(1)
            if 'MessageRouter' in module or self._module_contains_message_router(module):
                import_paths.append(module)
        
        return import_paths

    def _find_relative_message_router_imports(self) -> Dict[str, List[Tuple[int, str]]]:
        """Find files using relative imports for MessageRouter."""
        relative_imports = {}
        
        for py_file in self.base_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                relative_lines = []
                for line_num, line in enumerate(lines, 1):
                    # Look for relative imports (starting with .)
                    if ('from .' in line or 'from ..' in line) and 'MessageRouter' in line:
                        relative_lines.append((line_num, line.strip()))
                
                if relative_lines:
                    relative_imports[str(py_file)] = relative_lines
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return relative_imports

    def _find_wildcard_imports_with_message_router(self) -> Dict[str, List[Tuple[int, str]]]:
        """Find wildcard imports that might include MessageRouter."""
        wildcard_imports = {}
        
        # Modules that likely contain MessageRouter
        router_modules = [
            'websocket_core', 'handlers', 'websocket', 'routing', 'message'
        ]
        
        for py_file in self.base_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                wildcard_lines = []
                for line_num, line in enumerate(lines, 1):
                    if 'from ' in line and 'import *' in line:
                        # Check if the module might contain MessageRouter
                        if any(module in line.lower() for module in router_modules):
                            wildcard_lines.append((line_num, line.strip()))
                
                if wildcard_lines:
                    wildcard_imports[str(py_file)] = wildcard_lines
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return wildcard_imports

    def _analyze_import_statement_formatting(self) -> Dict[str, str]:
        """Analyze formatting consistency of import statements."""
        import_formatting = {}
        
        for py_file in self.base_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find lines containing MessageRouter imports
                lines = content.split('\n')
                for line in lines:
                    if 'import' in line and 'MessageRouter' in line:
                        # Normalize whitespace for comparison
                        normalized = ' '.join(line.split())
                        import_formatting[str(py_file)] = normalized
                        break  # Take first import statement
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return import_formatting

    def _find_dynamic_message_router_imports(self) -> Dict[str, List[Tuple[int, str]]]:
        """Find dynamic imports using importlib or __import__."""
        dynamic_imports = {}
        
        for py_file in self.base_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                dynamic_lines = []
                for line_num, line in enumerate(lines, 1):
                    line_lower = line.lower()
                    if (('importlib' in line_lower or '__import__' in line_lower) and 
                        ('messagerouter' in line_lower or 'websocket' in line_lower)):
                        dynamic_lines.append((line_num, line.strip()))
                
                if dynamic_lines:
                    dynamic_imports[str(py_file)] = dynamic_lines
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return dynamic_imports

    def _module_contains_message_router(self, module_name: str) -> bool:
        """Check if a module likely contains MessageRouter."""
        router_indicators = [
            'websocket_core', 'handlers', 'websocket', 'routing', 'message'
        ]
        return any(indicator in module_name.lower() for indicator in router_indicators)

    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if file should be skipped."""
        skip_patterns = [
            '__pycache__', '.git', '.pytest_cache', 'node_modules',
            '.venv', '.test_venv', 'venv'
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def _relativize_path(self, file_path: str) -> str:
        """Convert absolute path to relative for readability."""
        return file_path.replace(str(self.base_path), "").lstrip('/')

    def _format_import_violations(self, violations: Dict[str, List[str]]) -> str:
        """Format import path violations for error reporting."""
        formatted = []
        for import_path, files in violations.items():
            formatted.append(f"\nImport Path: {import_path}")
            formatted.append(f"  Used in {len(files)} files:")
            for file_path in files[:5]:  # Show first 5 files
                formatted.append(f"    - {self._relativize_path(file_path)}")
            if len(files) > 5:
                formatted.append(f"    ... and {len(files) - 5} more files")
        return "\n".join(formatted)

    def _format_relative_import_violations(self, violations: Dict[str, List[Tuple[int, str]]]) -> str:
        """Format relative import violations for error reporting."""
        formatted = []
        for file_path, lines in violations.items():
            formatted.append(f"\n{self._relativize_path(file_path)}:")
            for line_num, line in lines:
                formatted.append(f"  Line {line_num}: {line}")
        return "\n".join(formatted)

    def _format_wildcard_import_violations(self, violations: Dict[str, List[Tuple[int, str]]]) -> str:
        """Format wildcard import violations for error reporting."""
        formatted = []
        for file_path, lines in violations.items():
            formatted.append(f"\n{self._relativize_path(file_path)}:")
            for line_num, line in lines:
                formatted.append(f"  Line {line_num}: {line}")
        return "\n".join(formatted)

    def _group_files_by_import_pattern(self, import_statements: Dict[str, str]) -> Dict[str, List[str]]:
        """Group files by their import statement patterns."""
        pattern_groups = defaultdict(list)
        for file_path, pattern in import_statements.items():
            pattern_groups[pattern].append(file_path)
        return dict(pattern_groups)

    def _format_pattern_inconsistencies(self, patterns: Dict[str, List[str]]) -> str:
        """Format import pattern inconsistencies for error reporting."""
        formatted = []
        for pattern, files in patterns.items():
            formatted.append(f"\nPattern: {pattern}")
            formatted.append(f"  Used in {len(files)} files:")
            for file_path in files[:3]:  # Show first 3 files
                formatted.append(f"    - {self._relativize_path(file_path)}")
            if len(files) > 3:
                formatted.append(f"    ... and {len(files) - 3} more files")
        return "\n".join(formatted)

    def _format_dynamic_import_violations(self, violations: Dict[str, List[Tuple[int, str]]]) -> str:
        """Format dynamic import violations for error reporting."""
        formatted = []
        for file_path, lines in violations.items():
            formatted.append(f"\n{self._relativize_path(file_path)}:")
            for line_num, line in lines:
                formatted.append(f"  Line {line_num}: {line}")
        return "\n".join(formatted)


if __name__ == "__main__":
    import unittest
    unittest.main()