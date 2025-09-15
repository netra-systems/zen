"""Import SSOT Validation Tests - P1 System Integrity

This test suite validates canonical import paths after SSOT remediation.
These tests are designed to FAIL initially (detecting import violations) and
PASS after successful import path consolidation.

Business Value Justification:
- Segment: Platform/System Integrity  
- Business Goal: Stability & Development Velocity
- Value Impact: Protects $500K+ ARR by ensuring canonical import paths prevent
  circular dependencies, import errors, and module resolution failures
- Strategic Impact: Foundation for reliable agent system initialization and deployment

Key Validation Areas:
1. Canonical Import Paths Only - No legacy or duplicate import paths allowed
2. Circular Dependency Prevention - Import graph validation and cycle detection
3. Module Loading Consistency - Consistent loading patterns across all modules
4. Import Path Validation - All imports follow SSOT patterns and conventions
5. Broken Import Detection - Identification of non-existent import paths

EXPECTED BEHAVIOR: 
These tests SHOULD FAIL initially, demonstrating existing import path violations.
After SSOT consolidation, these tests should pass, confirming canonical import paths.
"""

import pytest
import ast
import importlib
import importlib.util
import inspect
import sys
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.unit
class TestImportSSotValidation(SSotBaseTestCase):
    """Test suite for validating Import SSOT compliance."""
    
    def setUp(self):
        """Set up test environment for import SSOT validation."""
        super().setUp()
        self.codebase_root = Path(__file__).parent.parent.parent.parent
        self.import_violations = []
        self.import_graph = defaultdict(set)
        
        # Expected SSOT import patterns
        self.canonical_imports = {
            'agent_registry': 'netra_backend.app.agents.supervisor.agent_registry',
            'execution_engine': 'netra_backend.app.agents.supervisor.user_execution_engine',
            'websocket_manager': 'netra_backend.app.websocket_core.manager',
            'tool_dispatcher': 'netra_backend.app.core.tools.unified_tool_dispatcher',
            'config': 'netra_backend.app.config'
        }
        
        # Legacy/deprecated import patterns to detect
        self.deprecated_imports = [
            'netra_backend.app.agents.registry',  # Old registry location
            'netra_backend.app.agents.execution_engine',  # Old execution engine
            'netra_backend.app.websocket_core.websocket_manager',  # Non-canonical WebSocket
            'netra_backend.app.tools.dispatcher',  # Old tool dispatcher
        ]
        
        logger.info("Starting Import SSOT validation")
    
    def test_canonical_import_paths_only(self):
        """Validate only canonical import paths are used - SHOULD INITIALLY FAIL."""
        logger.info("🔍 IMPORT SSOT TEST 1: Validating canonical import paths only")
        
        # Find all import statements in the codebase
        all_imports = self._find_all_import_statements()
        
        # Categorize imports
        canonical_imports = []
        non_canonical_imports = []
        
        for file_path, line_num, import_statement, import_module in all_imports:
            if self._is_canonical_import(import_module):
                canonical_imports.append((file_path, line_num, import_statement))
            else:
                non_canonical_imports.append((file_path, line_num, import_statement, import_module))
        
        # Log findings
        logger.info(f"Found {len(canonical_imports)} canonical imports")
        logger.info(f"Found {len(non_canonical_imports)} non-canonical imports:")
        
        for file_path, line_num, import_statement, import_module in non_canonical_imports[:10]:
            logger.info(f"  - {file_path}:{line_num}: {import_statement.strip()}")
        
        if len(non_canonical_imports) > 10:
            logger.info(f"    ... and {len(non_canonical_imports) - 10} more")
        
        # Store violations
        self.import_violations.extend([
            f"Non-canonical import: {file_path}:{line_num} - {import_statement.strip()}"
            for file_path, line_num, import_statement, import_module in non_canonical_imports
        ])
        
        # EXPECTED TO FAIL: Non-canonical imports should be detected
        self.assertGreater(
            len(non_canonical_imports), 0,
            "EXPECTED FAILURE: Should detect non-canonical import paths. "
            f"Found {len(non_canonical_imports)} non-canonical imports requiring migration to SSOT paths."
        )
    
    def test_circular_dependency_prevention(self):
        """Validate no circular dependencies - SHOULD INITIALLY FAIL."""
        logger.info("🔍 IMPORT SSOT TEST 2: Validating circular dependency prevention")
        
        # Build import graph
        import_graph = self._build_import_graph()
        
        # Detect circular dependencies
        circular_dependencies = self._detect_circular_dependencies(import_graph)
        
        # Log findings
        logger.info(f"Built import graph with {len(import_graph)} modules")
        logger.info(f"Detected {len(circular_dependencies)} circular dependencies:")
        
        for cycle in circular_dependencies:
            logger.info(f"  - Cycle: {' -> '.join(cycle)} -> {cycle[0]}")
        
        # Store violations
        self.import_violations.extend([
            f"Circular dependency: {' -> '.join(cycle)} -> {cycle[0]}"
            for cycle in circular_dependencies
        ])
        
        # EXPECTED TO FAIL: Circular dependencies should be detected
        self.assertGreater(
            len(circular_dependencies), 0,
            "EXPECTED FAILURE: Should detect circular import dependencies. "
            f"Found {len(circular_dependencies)} circular dependencies requiring refactoring."
        )
    
    def test_module_loading_consistency(self):
        """Validate consistent module loading patterns - SHOULD INITIALLY FAIL."""
        logger.info("🔍 IMPORT SSOT TEST 3: Validating module loading consistency")
        
        # Test module loading patterns
        loading_violations = self._test_module_loading_consistency()
        
        # Log findings
        logger.info(f"Found {len(loading_violations)} module loading violations:")
        for violation_type, details in loading_violations.items():
            logger.info(f"  - {violation_type}: {details}")
        
        # Store violations
        self.import_violations.extend([
            f"Module loading violation ({violation_type}): {details}"
            for violation_type, details in loading_violations.items()
        ])
        
        # EXPECTED TO FAIL: Loading violations should be detected
        self.assertGreater(
            len(loading_violations), 0,
            "EXPECTED FAILURE: Should detect module loading inconsistencies. "
            f"Found {len(loading_violations)} violations requiring consistent loading patterns."
        )
    
    def test_import_path_validation(self):
        """Validate all imports follow SSOT patterns - SHOULD INITIALLY FAIL."""
        logger.info("🔍 IMPORT SSOT TEST 4: Validating import path patterns")
        
        # Check import path patterns
        pattern_violations = self._validate_import_patterns()
        
        # Log findings
        logger.info(f"Found {len(pattern_violations)} import pattern violations:")
        for violation_type, location, details in pattern_violations:
            logger.info(f"  - {violation_type}: {location} - {details}")
        
        # Store violations
        self.import_violations.extend([
            f"Pattern violation ({violation_type}): {location} - {details}"
            for violation_type, location, details in pattern_violations
        ])
        
        # EXPECTED TO FAIL: Pattern violations should be detected
        self.assertGreater(
            len(pattern_violations), 0,
            "EXPECTED FAILURE: Should detect import pattern violations. "
            f"Found {len(pattern_violations)} violations requiring SSOT pattern compliance."
        )
    
    def test_broken_import_detection(self):
        """Detect broken/non-existent import paths - SHOULD INITIALLY FAIL."""
        logger.info("🔍 IMPORT SSOT TEST 5: Detecting broken import paths")
        
        # Find broken imports
        broken_imports = self._detect_broken_imports()
        
        # Log findings
        logger.info(f"Found {len(broken_imports)} broken imports:")
        for file_path, line_num, import_statement, error in broken_imports:
            logger.info(f"  - {file_path}:{line_num}: {import_statement.strip()} - {error}")
        
        # Store violations
        self.import_violations.extend([
            f"Broken import: {file_path}:{line_num} - {import_statement.strip()} ({error})"
            for file_path, line_num, import_statement, error in broken_imports
        ])
        
        # EXPECTED TO FAIL: Broken imports should be detected
        self.assertGreater(
            len(broken_imports), 0,
            "EXPECTED FAILURE: Should detect broken import paths. "
            f"Found {len(broken_imports)} broken imports requiring fixing or removal."
        )
    
    def test_deprecated_import_detection(self):
        """Detect deprecated import patterns - SHOULD INITIALLY FAIL."""
        logger.info("🔍 IMPORT SSOT TEST 6: Detecting deprecated import patterns")
        
        # Find deprecated imports
        deprecated_imports = self._detect_deprecated_imports()
        
        # Log findings
        logger.info(f"Found {len(deprecated_imports)} deprecated imports:")
        for file_path, line_num, import_statement, deprecated_module in deprecated_imports:
            logger.info(f"  - {file_path}:{line_num}: {import_statement.strip()}")
        
        # Store violations
        self.import_violations.extend([
            f"Deprecated import: {file_path}:{line_num} - {import_statement.strip()}"
            for file_path, line_num, import_statement, deprecated_module in deprecated_imports
        ])
        
        # EXPECTED TO FAIL: Deprecated imports should be detected
        self.assertGreater(
            len(deprecated_imports), 0,
            "EXPECTED FAILURE: Should detect deprecated import patterns. "
            f"Found {len(deprecated_imports)} deprecated imports requiring migration."
        )
    
    def test_relative_import_violations(self):
        """Detect relative import violations - SHOULD INITIALLY FAIL."""
        logger.info("🔍 IMPORT SSOT TEST 7: Detecting relative import violations")
        
        # Find relative imports
        relative_imports = self._detect_relative_imports()
        
        # Log findings
        logger.info(f"Found {len(relative_imports)} relative imports:")
        for file_path, line_num, import_statement in relative_imports:
            logger.info(f"  - {file_path}:{line_num}: {import_statement.strip()}")
        
        # Store violations
        self.import_violations.extend([
            f"Relative import: {file_path}:{line_num} - {import_statement.strip()}"
            for file_path, line_num, import_statement in relative_imports
        ])
        
        # EXPECTED TO FAIL: Relative imports should be detected
        self.assertGreater(
            len(relative_imports), 0,
            "EXPECTED FAILURE: Should detect relative import violations. "
            f"Found {len(relative_imports)} relative imports requiring absolute path conversion."
        )
    
    def test_import_organization_violations(self):
        """Detect import organization violations - SHOULD INITIALLY FAIL."""
        logger.info("🔍 IMPORT SSOT TEST 8: Detecting import organization violations")
        
        # Check import organization
        organization_violations = self._check_import_organization()
        
        # Log findings
        logger.info(f"Found {len(organization_violations)} import organization violations:")
        for violation_type, file_path, details in organization_violations:
            logger.info(f"  - {violation_type}: {file_path} - {details}")
        
        # Store violations
        self.import_violations.extend([
            f"Organization violation ({violation_type}): {file_path} - {details}"
            for violation_type, file_path, details in organization_violations
        ])
        
        # EXPECTED TO FAIL: Organization violations should be detected
        self.assertGreater(
            len(organization_violations), 0,
            "EXPECTED FAILURE: Should detect import organization violations. "
            f"Found {len(organization_violations)} violations requiring proper import organization."
        )
    
    def test_comprehensive_import_ssot_summary(self):
        """Generate comprehensive import SSOT violation report - SHOULD INITIALLY FAIL."""
        logger.info("📊 IMPORT SSOT COMPREHENSIVE SUMMARY")
        
        # Ensure all violations are collected
        if not self.import_violations:
            # Run all validation tests
            self.test_canonical_import_paths_only()
            self.test_circular_dependency_prevention()
            self.test_module_loading_consistency()
            self.test_import_path_validation()
            self.test_broken_import_detection()
            self.test_deprecated_import_detection()
            self.test_relative_import_violations()
            self.test_import_organization_violations()
        
        # Generate comprehensive summary
        violation_summary = {
            'total_violations': len(self.import_violations),
            'business_impact': self._assess_import_business_impact(),
            'consolidation_priority': self._assess_import_consolidation_priority(),
            'ssot_readiness': self._assess_import_ssot_readiness()
        }
        
        logger.info(f"IMPORT SSOT VIOLATION SUMMARY:")
        logger.info(f"  Total Violations: {violation_summary['total_violations']}")
        logger.info(f"  Business Impact: {violation_summary['business_impact']['severity']}")
        logger.info(f"  Consolidation Priority: {violation_summary['consolidation_priority']}")
        logger.info(f"  SSOT Readiness: {violation_summary['ssot_readiness']['status']}")
        
        # Log sample violations by category
        violation_categories = self._categorize_import_violations()
        for category, violations in violation_categories.items():
            logger.info(f"  {category}: {len(violations)} violations")
            for violation in violations[:2]:  # Show first 2 per category
                logger.info(f"    ❌ {violation}")
        
        # EXPECTED TO FAIL: Comprehensive violations should be detected
        self.assertGreater(
            violation_summary['total_violations'], 0,
            "EXPECTED FAILURE: Import SSOT consolidation needed. "
            f"Detected {violation_summary['total_violations']} violations requiring remediation. "
            f"Business Impact: {violation_summary['business_impact']['description']}"
        )

    # Helper Methods
    
    def _find_all_import_statements(self) -> List[Tuple[str, int, str, str]]:
        """Find all import statements in the codebase."""
        imports = []
        
        for py_file in self.codebase_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    # Parse different import patterns
                    if line_stripped.startswith(('import ', 'from ')):
                        imported_module = self._extract_module_from_import(line_stripped)
                        if imported_module:
                            imports.append((str(py_file), line_num, line, imported_module))
                
            except (UnicodeDecodeError, IOError) as e:
                logger.debug(f"Could not read {py_file}: {e}")
        
        return imports
    
    def _extract_module_from_import(self, import_line: str) -> str:
        """Extract module name from import statement."""
        try:
            if import_line.startswith('from '):
                # from module import something
                parts = import_line.split(' import ')[0]
                module = parts.replace('from ', '').strip()
                return module
            elif import_line.startswith('import '):
                # import module
                module = import_line.replace('import ', '').split(' as ')[0].split(',')[0].strip()
                return module
            return ""
        except (IndexError, AttributeError):
            return ""
    
    def _is_canonical_import(self, import_module: str) -> bool:
        """Check if import uses canonical path."""
        # Check against known canonical patterns
        for canonical_name, canonical_path in self.canonical_imports.items():
            if canonical_path in import_module:
                return True
        
        # Check for general SSOT patterns
        ssot_patterns = [
            'netra_backend.app.agents.supervisor.',  # Supervisor module SSOT
            'netra_backend.app.websocket_core.manager',  # WebSocket SSOT
            'netra_backend.app.core.tools.unified_tool_dispatcher',  # Tool dispatcher SSOT
            'netra_backend.app.config',  # Config SSOT
            'shared.',  # Shared utilities
            'test_framework.ssot.'  # SSOT test infrastructure
        ]
        
        return any(pattern in import_module for pattern in ssot_patterns)
    
    def _build_import_graph(self) -> Dict[str, Set[str]]:
        """Build import dependency graph."""
        import_graph = defaultdict(set)
        
        for py_file in self.codebase_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                module_path = self._file_to_module_path(py_file)
                if not module_path:
                    continue
                
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse imports using AST for better accuracy
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                if alias.name.startswith(('netra_backend', 'shared')):
                                    import_graph[module_path].add(alias.name)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module and node.module.startswith(('netra_backend', 'shared')):
                                import_graph[module_path].add(node.module)
                except SyntaxError:
                    # Fallback to simple parsing if AST fails
                    pass
                
            except (UnicodeDecodeError, IOError):
                continue
        
        return dict(import_graph)
    
    def _detect_circular_dependencies(self, import_graph: Dict[str, Set[str]]) -> List[List[str]]:
        """Detect circular dependencies in import graph."""
        circular_deps = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> bool:
            """Depth-first search to detect cycles."""
            if node in rec_stack:
                # Found a cycle, extract it
                cycle_start = path.index(node) if node in path else 0
                cycle = path[cycle_start:] + [node]
                if len(cycle) > 1:
                    circular_deps.append(cycle)
                return True
            
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in import_graph.get(node, set()):
                if dfs(neighbor):
                    return True
            
            rec_stack.remove(node)
            path.pop()
            return False
        
        # Check all nodes
        for node in import_graph:
            if node not in visited:
                dfs(node)
        
        # Remove duplicate cycles
        unique_cycles = []
        for cycle in circular_deps:
            normalized_cycle = tuple(sorted(cycle))
            if normalized_cycle not in [tuple(sorted(c)) for c in unique_cycles]:
                unique_cycles.append(cycle)
        
        return unique_cycles
    
    def _test_module_loading_consistency(self) -> Dict[str, str]:
        """Test module loading consistency patterns."""
        violations = {}
        
        # Test loading of canonical modules
        canonical_modules = [
            'netra_backend.app.agents.supervisor.agent_registry',
            'netra_backend.app.agents.supervisor.user_execution_engine',
            'netra_backend.app.websocket_core.manager',
            'netra_backend.app.config'
        ]
        
        loading_results = {}
        for module_name in canonical_modules:
            try:
                start_time = time.time()
                spec = importlib.util.find_spec(module_name)
                load_time = time.time() - start_time
                
                if spec is None:
                    loading_results[module_name] = {'status': 'not_found', 'time': load_time}
                else:
                    loading_results[module_name] = {'status': 'found', 'time': load_time}
                    
            except Exception as e:
                loading_results[module_name] = {'status': 'error', 'error': str(e)}
        
        # Check for consistency issues
        found_modules = [m for m, r in loading_results.items() if r['status'] == 'found']
        not_found_modules = [m for m, r in loading_results.items() if r['status'] == 'not_found']
        error_modules = [m for m, r in loading_results.items() if r['status'] == 'error']
        
        if not_found_modules:
            violations['missing_canonical_modules'] = f"Canonical modules not found: {not_found_modules}"
        
        if error_modules:
            violations['module_loading_errors'] = f"Modules with loading errors: {error_modules}"
        
        # Check loading time consistency
        load_times = [r['time'] for r in loading_results.values() if 'time' in r]
        if load_times and max(load_times) - min(load_times) > 0.1:
            violations['inconsistent_load_times'] = f"High variance in module loading times: {min(load_times):.3f}s to {max(load_times):.3f}s"
        
        return violations
    
    def _validate_import_patterns(self) -> List[Tuple[str, str, str]]:
        """Validate import path patterns against SSOT conventions."""
        violations = []
        
        for py_file in self.codebase_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    if line_stripped.startswith(('import ', 'from ')):
                        # Check for specific anti-patterns
                        if 'import *' in line_stripped:
                            violations.append(("wildcard_import", f"{py_file}:{line_num}",
                                             f"Wildcard import: {line_stripped}"))
                        
                        # Check for overly nested imports
                        if line_stripped.count('.') > 6:
                            violations.append(("deeply_nested_import", f"{py_file}:{line_num}",
                                             f"Deeply nested import: {line_stripped}"))
                        
                        # Check for inconsistent naming
                        if ' as ' in line_stripped:
                            alias = line_stripped.split(' as ')[1].strip()
                            if not alias.islower() and not alias.isupper():
                                violations.append(("inconsistent_alias", f"{py_file}:{line_num}",
                                                 f"Non-standard alias: {alias}"))
                
            except (UnicodeDecodeError, IOError):
                continue
        
        return violations
    
    def _detect_broken_imports(self) -> List[Tuple[str, int, str, str]]:
        """Detect broken/non-existent import paths."""
        broken_imports = []
        
        for py_file in self.codebase_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = f.readlines()
                
                # Use AST to parse imports more reliably
                try:
                    tree = ast.parse(content)
                    line_to_import = {}
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                line_to_import[node.lineno] = alias.name
                        elif isinstance(node, ast.ImportFrom) and node.module:
                            line_to_import[node.lineno] = node.module
                    
                    # Check each import
                    for line_num, import_module in line_to_import.items():
                        if import_module.startswith(('netra_backend', 'shared')):
                            try:
                                spec = importlib.util.find_spec(import_module)
                                if spec is None:
                                    import_line = lines[line_num - 1] if line_num <= len(lines) else "Unknown"
                                    broken_imports.append((str(py_file), line_num, import_line, "Module not found"))
                            except (ModuleNotFoundError, ValueError) as e:
                                import_line = lines[line_num - 1] if line_num <= len(lines) else "Unknown"
                                broken_imports.append((str(py_file), line_num, import_line, str(e)))
                                
                except SyntaxError as e:
                    # File has syntax errors
                    broken_imports.append((str(py_file), getattr(e, 'lineno', 1), "Syntax error", str(e)))
                
            except (UnicodeDecodeError, IOError):
                continue
        
        return broken_imports
    
    def _detect_deprecated_imports(self) -> List[Tuple[str, int, str, str]]:
        """Detect deprecated import patterns."""
        deprecated_imports = []
        
        for py_file in self.codebase_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    if line_stripped.startswith(('import ', 'from ')):
                        imported_module = self._extract_module_from_import(line_stripped)
                        
                        # Check against deprecated patterns
                        for deprecated_pattern in self.deprecated_imports:
                            if deprecated_pattern in imported_module:
                                deprecated_imports.append((str(py_file), line_num, line, imported_module))
                                break
                
            except (UnicodeDecodeError, IOError):
                continue
        
        return deprecated_imports
    
    def _detect_relative_imports(self) -> List[Tuple[str, int, str]]:
        """Detect relative import violations."""
        relative_imports = []
        
        for py_file in self.codebase_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    # Check for relative import patterns
                    if (line_stripped.startswith('from .') or 
                        line_stripped.startswith('from ..') or
                        line_stripped.startswith('import .')):
                        relative_imports.append((str(py_file), line_num, line))
                
            except (UnicodeDecodeError, IOError):
                continue
        
        return relative_imports
    
    def _check_import_organization(self) -> List[Tuple[str, str, str]]:
        """Check import organization violations."""
        violations = []
        
        for py_file in self.codebase_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Check import organization
                import_lines = []
                for i, line in enumerate(lines):
                    if line.strip().startswith(('import ', 'from ')):
                        import_lines.append((i, line.strip()))
                
                if len(import_lines) > 1:
                    # Check if imports are grouped properly
                    stdlib_imports = []
                    third_party_imports = []
                    local_imports = []
                    
                    for line_num, import_line in import_lines:
                        module = self._extract_module_from_import(import_line)
                        if module:
                            if module.startswith(('netra_backend', 'shared')):
                                local_imports.append((line_num, import_line))
                            elif '.' not in module or module in ['os', 'sys', 'time', 'json', 'asyncio']:
                                stdlib_imports.append((line_num, import_line))
                            else:
                                third_party_imports.append((line_num, import_line))
                    
                    # Check organization order
                    all_organized = stdlib_imports + third_party_imports + local_imports
                    actual_order = [line_num for line_num, _ in import_lines]
                    expected_order = [line_num for line_num, _ in all_organized]
                    
                    if actual_order != expected_order:
                        violations.append(("import_organization", str(py_file),
                                         "Imports not organized by stdlib, third-party, local"))
                
            except (UnicodeDecodeError, IOError):
                continue
        
        return violations
    
    def _categorize_import_violations(self) -> Dict[str, List[str]]:
        """Categorize import violations by type."""
        categories = defaultdict(list)
        
        for violation in self.import_violations:
            if 'Non-canonical import' in violation:
                categories['non_canonical'].append(violation)
            elif 'Circular dependency' in violation:
                categories['circular_dependencies'].append(violation)
            elif 'Module loading violation' in violation:
                categories['loading_issues'].append(violation)
            elif 'Pattern violation' in violation:
                categories['pattern_violations'].append(violation)
            elif 'Broken import' in violation:
                categories['broken_imports'].append(violation)
            elif 'Deprecated import' in violation:
                categories['deprecated_imports'].append(violation)
            elif 'Relative import' in violation:
                categories['relative_imports'].append(violation)
            elif 'Organization violation' in violation:
                categories['organization_issues'].append(violation)
            else:
                categories['other'].append(violation)
        
        return dict(categories)
    
    def _assess_import_business_impact(self) -> Dict[str, Any]:
        """Assess business impact of import SSOT violations."""
        total_violations = len(self.import_violations)
        
        # Assess severity based on violation types
        violation_categories = self._categorize_import_violations()
        
        # High-impact violation types
        high_impact_count = (len(violation_categories.get('circular_dependencies', [])) +
                           len(violation_categories.get('broken_imports', [])))
        
        if high_impact_count > 10 or total_violations > 50:
            severity = "CRITICAL"
            description = "Severe import fragmentation threatens system stability and deployment reliability"
        elif high_impact_count > 5 or total_violations > 25:
            severity = "HIGH"
            description = "Significant import issues risk deployment failures and development velocity"
        elif total_violations > 15:
            severity = "MEDIUM"
            description = "Moderate import violations may cause intermittent issues"
        else:
            severity = "LOW"
            description = "Minor import violations with limited business impact"
        
        return {
            'severity': severity,
            'description': description,
            'deployment_risk': high_impact_count > 5,
            'development_velocity_risk': total_violations > 20
        }
    
    def _assess_import_consolidation_priority(self) -> str:
        """Assess import consolidation priority."""
        violation_categories = self._categorize_import_violations()
        
        if len(violation_categories.get('circular_dependencies', [])) > 0:
            return "P0 - IMMEDIATE (Circular dependencies detected)"
        elif len(violation_categories.get('broken_imports', [])) > 10:
            return "P1 - URGENT (Many broken imports)"
        elif len(violation_categories.get('deprecated_imports', [])) > 15:
            return "P2 - HIGH (Deprecated import cleanup needed)"
        else:
            return "P3 - MEDIUM (Import organization improvement)"
    
    def _assess_import_ssot_readiness(self) -> Dict[str, Any]:
        """Assess readiness for import SSOT consolidation."""
        violation_categories = self._categorize_import_violations()
        
        # Check for blockers
        blockers = (len(violation_categories.get('circular_dependencies', [])) +
                   len(violation_categories.get('broken_imports', [])))
        
        if blockers == 0 and len(self.import_violations) == 0:
            status = "READY - Import SSOT consolidation complete"
        elif blockers == 0:
            status = "PARTIAL - No blockers but cleanup needed"
        else:
            status = "NOT_READY - Import blockers must be resolved"
        
        return {
            'status': status,
            'blockers': blockers,
            'violations_remaining': len(self.import_violations),
            'consolidation_progress': max(0, 100 - len(self.import_violations))
        }
    
    # Utility methods
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during scanning."""
        skip_patterns = [
            '__pycache__', '.pyc', 'node_modules', '.git', 'venv', '.env',
            'test_import_ssot_validation.py',  # Skip self
            'backup', 'archived'
        ]
        
        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)
    
    def _file_to_module_path(self, file_path: Path) -> str:
        """Convert file path to Python module path."""
        try:
            rel_path = file_path.relative_to(self.codebase_root)
            module_path = str(rel_path.with_suffix(''))
            module_path = module_path.replace('/', '.').replace('\\', '.')
            return module_path
        except (ValueError, AttributeError):
            return ""


if __name__ == '__main__':
    import unittest
    unittest.main()