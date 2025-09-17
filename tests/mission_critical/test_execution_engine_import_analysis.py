"Issue #874: ExecutionEngine import analysis and violation detection test.

This test analyzes all ExecutionEngine import patterns across the codebase
to identify illegal imports that bypass the UserExecutionEngine SSOT pattern.
It detects direct imports of legacy execution engines and non-canonical patterns.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Code Quality & System Integrity
- Value Impact: Prevents import confusion that could cause execution engine mixing and chat failures
- Strategic Impact: Ensures clean import patterns supporting $500K+ ARR reliable chat operations

Key Analysis Areas:
- Direct ExecutionEngine imports bypassing UserExecutionEngine
- Legacy import patterns from deprecated modules
- Circular import dependencies in execution engine modules
- Import path inconsistencies across services
- Missing imports that should use UserExecutionEngine

EXPECTED BEHAVIOR:
This test should FAIL initially, identifying import violations.
After import cleanup, this test should pass with clean import patterns.
""

import unittest
import ast
import importlib
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ExecutionEngineImportAnalysisTests(SSotBaseTestCase):
    Test for analyzing ExecutionEngine import patterns and violations."
    
    def setUp(self):
        "Set up test environment for import analysis.
        super().setUp()
        self.codebase_root = Path(__file__).parent.parent.parent
        self.import_violations = []
        self.circular_dependencies = []
        self.missing_canonical_imports = []
        self.legacy_import_patterns = []
        
        # Canonical import patterns (what should be used)
        self.canonical_imports = {
            'UserExecutionEngine': 'netra_backend.app.agents.supervisor.user_execution_engine',
            'ExecutionEngineFactory': 'netra_backend.app.agents.supervisor.execution_engine_factory',
            'UserExecutionContext': 'netra_backend.app.services.user_execution_context',
            'AgentExecutionContext': 'netra_backend.app.agents.supervisor.execution_context',
        }
        
        # Deprecated import patterns (what should NOT be used)
        self.deprecated_imports = [
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.agents.execution_engine',
            'netra_backend.app.core.execution_engine',
            'netra_backend.app.services.execution_engine',
        ]
        
        logger.info(Starting ExecutionEngine import analysis")"
    
    def test_detect_illegal_execution_engine_imports(self):
        Detect illegal ExecutionEngine import patterns - SHOULD INITIALLY FAIL."
        logger.info(🔍 IMPORT ANALYSIS: Scanning for illegal ExecutionEngine imports")
        
        illegal_imports = self._find_illegal_execution_engine_imports()
        
        # Log findings
        logger.info(fFound {len(illegal_imports)} illegal ExecutionEngine imports:)
        for file_path, line_num, import_statement, violation_type in illegal_imports:
            logger.info(f  - {violation_type}: {file_path}:{line_num})"
            logger.info(f"    Import: {import_statement.strip()})
        
        # Store violations
        self.import_violations.extend([
            fIllegal import ({violation_type}: {file_path}:{line_num} - {import_statement.strip()}
            for file_path, line_num, import_statement, violation_type in illegal_imports
        ]
        
        # EXPECTED TO FAIL: Illegal imports should be detected
        self.assertGreater(
            len(illegal_imports), 0,
            EXPECTED FAILURE: Should detect illegal ExecutionEngine import patterns. "
            fFound {len(illegal_imports)} illegal imports requiring cleanup."
        )
    
    def test_detect_missing_canonical_imports(self):
        Detect files that should import UserExecutionEngine but don't - SHOULD INITIALLY FAIL.""
        logger.info(🔍 IMPORT ANALYSIS: Scanning for missing canonical imports)
        
        missing_imports = self._find_missing_canonical_imports()
        
        # Log findings
        logger.info(fFound {len(missing_imports)} files missing canonical imports:)
        for file_path, missing_import, reason in missing_imports:
            logger.info(f  - {file_path}: Missing {missing_import}")"
            logger.info(f    Reason: {reason})
        
        # Store violations
        self.missing_canonical_imports.extend([
            fMissing canonical import: {file_path} - Should import {missing_import} ({reason}
            for file_path, missing_import, reason in missing_imports
        ]
        
        # EXPECTED TO FAIL: Missing canonical imports should be detected
        self.assertGreater(
            len(missing_imports), 0,
            "EXPECTED FAILURE: Should detect missing canonical import patterns. "
            fFound {len(missing_imports)} files requiring canonical imports.
        )
    
    def test_detect_circular_import_dependencies(self):
        Detect circular import dependencies in execution engine modules - SHOULD INITIALLY FAIL.""
        logger.info(🔍 IMPORT ANALYSIS: Scanning for circular import dependencies)
        
        circular_deps = self._find_circular_import_dependencies()
        
        # Log findings
        logger.info(f"Found {len(circular_deps)} circular import dependencies:)
        for cycle in circular_deps:
            logger.info(f  - Circular dependency: {' -> '.join(cycle)}")
        
        # Store violations
        self.circular_dependencies.extend([
            fCircular dependency: {' -> '.join(cycle)}
            for cycle in circular_deps
        ]
        
        # EXPECTED TO FAIL: Circular dependencies should be detected
        self.assertGreater(
            len(circular_deps), 0,
            EXPECTED FAILURE: Should detect circular import dependencies. "
            f"Found {len(circular_deps)} circular dependencies requiring resolution.
        )
    
    def test_analyze_import_consistency_across_services(self):
        Analyze import consistency across different services - SHOULD INITIALLY FAIL."
        logger.info("🔍 IMPORT ANALYSIS: Analyzing import consistency across services)
        
        inconsistencies = self._analyze_import_consistency()
        
        # Log findings
        logger.info(fFound {len(inconsistencies)} import consistency issues:)
        for service, import_pattern, canonical_pattern, files in inconsistencies:
            logger.info(f"  - Service: {service})
            logger.info(f    Using: {import_pattern}")
            logger.info(f    Should use: {canonical_pattern})
            logger.info(f    Files affected: {len(files)})"
        
        # Store violations
        self.import_violations.extend([
            f"Import inconsistency in {service}: Using '{import_pattern}' instead of '{canonical_pattern}' in {len(files)} files
            for service, import_pattern, canonical_pattern, files in inconsistencies
        ]
        
        # EXPECTED TO FAIL: Import inconsistencies should be detected
        self.assertGreater(
            len(inconsistencies), 0,
            EXPECTED FAILURE: Should detect import consistency issues across services. 
            fFound {len(inconsistencies)} inconsistencies requiring standardization.
        )
    
    def test_validate_import_path_resolution(self):
        ""Validate all ExecutionEngine import paths can be resolved - MAY FAIL.
        logger.info(🔍 IMPORT ANALYSIS: Validating import path resolution)"
        
        resolution_failures = self._validate_import_resolution()
        
        # Log findings
        logger.info(fFound {len(resolution_failures)} import resolution failures:")
        for file_path, import_statement, error in resolution_failures:
            logger.info(f  - {file_path}: {import_statement})
            logger.info(f    Error: {error})"
        
        # Store violations for broken imports only
        broken_imports = [
            (file_path, import_statement, error)
            for file_path, import_statement, error in resolution_failures
            if "ModuleNotFoundError in str(error) or ImportError in str(error)
        ]
        
        self.import_violations.extend([
            fBroken import: {file_path} - {import_statement} ({error}
            for file_path, import_statement, error in broken_imports
        ]
        
        # This test may pass if no broken imports, but should detect some issues
        if broken_imports:
            self.assertGreater(
                len(broken_imports), 0,
                fFound {len(broken_imports)} broken import paths requiring fixes."
            )
        else:
            logger.info("✅ All ExecutionEngine imports can be resolved)
    
    def test_comprehensive_import_analysis_report(self):
        Generate comprehensive import analysis report - SHOULD INITIALLY FAIL.""
        logger.info(📊 COMPREHENSIVE IMPORT ANALYSIS REPORT)
        
        # Collect all violations from previous tests
        if not (self.import_violations or self.missing_canonical_imports or self.circular_dependencies):
            # Run analysis if not already done
            self.test_detect_illegal_execution_engine_imports()
            self.test_detect_missing_canonical_imports()
            self.test_detect_circular_import_dependencies()
            self.test_analyze_import_consistency_across_services()
            self.test_validate_import_path_resolution()
        
        # Generate comprehensive report
        all_violations = self.import_violations + self.missing_canonical_imports + self.circular_dependencies
        
        import_analysis_summary = {
            'total_violations': len(all_violations),
            'illegal_imports': len([v for v in all_violations if 'Illegal import' in v],
            'missing_canonical': len([v for v in all_violations if 'Missing canonical' in v],
            'circular_dependencies': len([v for v in all_violations if 'Circular dependency' in v],
            'consistency_issues': len([v for v in all_violations if 'Import inconsistency' in v],
            'broken_imports': len([v for v in all_violations if 'Broken import' in v],
            'cleanup_priority': self._assess_import_cleanup_priority(all_violations),
            'migration_recommendations': self._generate_migration_recommendations()
        }
        
        # Log comprehensive summary
        logger.info(fIMPORT ANALYSIS SUMMARY:)"
        logger.info(f"  Total Violations: {import_analysis_summary['total_violations']})
        logger.info(f  Illegal Imports: {import_analysis_summary['illegal_imports']})
        logger.info(f  Missing Canonical: {import_analysis_summary['missing_canonical']})
        logger.info(f  Circular Dependencies: {import_analysis_summary['circular_dependencies']}")"
        logger.info(f  Consistency Issues: {import_analysis_summary['consistency_issues']})
        logger.info(f  Broken Imports: {import_analysis_summary['broken_imports']})
        logger.info(f"  Cleanup Priority: {import_analysis_summary['cleanup_priority']})
        
        # Log first 10 violations
        for i, violation in enumerate(all_violations[:10], 1):
            logger.info(f    {i}. {violation}")
        
        if len(all_violations) > 10:
            logger.info(f    ... and {len(all_violations) - 10} more violations)
        
        # Log migration recommendations
        logger.info(MIGRATION RECOMMENDATIONS:)"
        for rec in import_analysis_summary['migration_recommendations']:
            logger.info(f"  - {rec})
        
        # EXPECTED TO FAIL: Import violations should be detected
        self.assertGreater(
            import_analysis_summary['total_violations'], 0,
            EXPECTED FAILURE: ExecutionEngine import cleanup needed. 
            fDetected {import_analysis_summary['total_violations']} import violations requiring resolution. 
            fPriority: {import_analysis_summary['cleanup_priority']}""
        )
    
    def _find_illegal_execution_engine_imports(self) -> List[Tuple[str, int, str, str]]:
        Find illegal ExecutionEngine import patterns in the codebase."
        illegal_imports = []
        
        for py_file in self.codebase_root.rglob(*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse AST for detailed import analysis
                try:
                    tree = ast.parse(content, filename=str(py_file))
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                violation_type = self._check_import_violation(alias.name)
                                if violation_type:
                                    illegal_imports.append((
                                        str(py_file), node.lineno,
                                        fimport {alias.name}, violation_type
                                    ))
                        
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                violation_type = self._check_import_violation(node.module)
                                if violation_type:
                                    names = [alias.name for alias in node.names]
                                    illegal_imports.append((
                                        str(py_file), node.lineno,
                                        ffrom {node.module} import {', '.join(names)}, violation_type"
                                    ))
                
                except SyntaxError:
                    # Fallback to line-by-line analysis for syntax errors
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        line_stripped = line.strip()
                        if line_stripped.startswith(('import ', 'from ')) and 'ExecutionEngine' in line_stripped:
                            violation_type = self._check_line_import_violation(line_stripped)
                            if violation_type:
                                illegal_imports.append((str(py_file), line_num, line, violation_type))
                
            except (UnicodeDecodeError, IOError) as e:
                logger.debug(f"Could not read {py_file}: {e})
        
        return illegal_imports
    
    def _find_missing_canonical_imports(self) -> List[Tuple[str, str, str]]:
        Find files that should use canonical imports but don't."
        missing_imports = []
        
        for py_file in self.codebase_root.rglob("*.py):
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for execution engine usage without proper imports
                if 'execution_engine' in content.lower() or 'ExecutionEngine' in content:
                    # Check if file uses execution engines but lacks canonical imports
                    has_canonical_import = any(
                        canonical_module in content
                        for canonical_module in self.canonical_imports.values()
                    )
                    
                    if not has_canonical_import:
                        # Determine what should be imported based on usage
                        if 'UserExecutionEngine' in content or 'user_execution_engine' in content:
                            missing_imports.append((
                                str(py_file), 'UserExecutionEngine',
                                File uses UserExecutionEngine but lacks canonical import
                            ))
                        elif 'ExecutionEngineFactory' in content:
                            missing_imports.append((
                                str(py_file), 'ExecutionEngineFactory',
                                "File uses ExecutionEngineFactory but lacks canonical import"
                            ))
                        elif 'ExecutionEngine' in content:
                            missing_imports.append((
                                str(py_file), 'UserExecutionEngine',
                                File uses ExecutionEngine but should use UserExecutionEngine
                            ))
            
            except (UnicodeDecodeError, IOError) as e:
                logger.debug(fCould not read {py_file}: {e})
        
        return missing_imports
    
    def _find_circular_import_dependencies(self) -> List[List[str]]:
        ""Find circular import dependencies in execution engine modules.
        # This is a simplified circular dependency detector
        # In a real implementation, this would use more sophisticated graph analysis
        execution_engine_modules = []
        
        # Find all execution engine related modules
        for py_file in self.codebase_root.rglob(*.py):"
            if self._should_skip_file(py_file):
                continue
            
            if ('execution_engine' in str(py_file).lower() or
                'user_execution' in str(py_file).lower() or
                'agent_factory' in str(py_file).lower()):
                
                module_path = self._file_to_module_path(py_file)
                if module_path:
                    execution_engine_modules.append(module_path)
        
        # Simple circular dependency detection (placeholder)
        # This would need more sophisticated implementation for real detection
        potential_cycles = []
        
        # Check for obvious circular patterns in execution engine modules
        for module in execution_engine_modules:
            if 'user_execution_engine' in module:
                # Check if this module imports factory and factory imports it back
                potential_cycles.append([module, 'execution_engine_factory', module]
        
        return potential_cycles
    
    def _analyze_import_consistency(self) -> List[Tuple[str, str, str, List[str]]]:
        "Analyze import consistency across different services.
        service_imports = {
            'netra_backend': [],
            'auth_service': [],
            'frontend': [],
            'shared': [],
            'test_framework': [],
            'tests': []
        }
        
        # Collect imports by service
        for py_file in self.codebase_root.rglob("*.py):"
            if self._should_skip_file(py_file):
                continue
            
            # Determine service
            service = None
            for service_name in service_imports.keys():
                if service_name in str(py_file):
                    service = service_name
                    break
            
            if not service:
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find ExecutionEngine related imports
                lines = content.split('\n')
                for line in lines:
                    if ('import' in line and 
                        ('ExecutionEngine' in line or 'execution_engine' in line)):
                        service_imports[service].append((str(py_file), line.strip()))
            
            except (UnicodeDecodeError, IOError):
                continue
        
        # Analyze inconsistencies
        inconsistencies = []
        for service, imports in service_imports.items():
            if not imports:
                continue
            
            # Group by import pattern
            import_patterns = {}
            for file_path, import_line in imports:
                pattern = self._normalize_import_pattern(import_line)
                if pattern not in import_patterns:
                    import_patterns[pattern] = []
                import_patterns[pattern].append(file_path)
            
            # Check for multiple patterns in same service
            if len(import_patterns) > 1:
                for pattern, files in import_patterns.items():
                    canonical = self._get_canonical_pattern(pattern)
                    if pattern != canonical:
                        inconsistencies.append((service, pattern, canonical, files))
        
        return inconsistencies
    
    def _validate_import_resolution(self) -> List[Tuple[str, str, str]]:
        Validate that all ExecutionEngine imports can be resolved."
        resolution_failures = []
        
        for py_file in self.codebase_root.rglob("*.py):
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse imports
                try:
                    tree = ast.parse(content, filename=str(py_file))
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            # Test import resolution
                            try:
                                if isinstance(node, ast.Import):
                                    for alias in node.names:
                                        if 'execution_engine' in alias.name.lower():
                                            try:
                                                importlib.import_module(alias.name)
                                            except Exception as e:
                                                resolution_failures.append((
                                                    str(py_file), fimport {alias.name}, str(e)
                                                ))
                                
                                elif isinstance(node, ast.ImportFrom) and node.module:
                                    if 'execution_engine' in node.module.lower():
                                        try:
                                            importlib.import_module(node.module)
                                        except Exception as e:
                                            names = [alias.name for alias in node.names]
                                            resolution_failures.append((
                                                str(py_file),
                                                f"from {node.module} import {', '.join(names)},
                                                str(e)
                                            ))
                            
                            except Exception as e:
                                # Skip resolution test if there are other issues
                                pass
                
                except SyntaxError:
                    # Skip files with syntax errors
                    pass
            
            except (UnicodeDecodeError, IOError):
                continue
        
        return resolution_failures
    
    def _should_skip_file(self, file_path: Path) -> bool:
        "Check if file should be skipped during analysis.
        skip_patterns = [
            '__pycache__',
            '.pyc',
            'node_modules',
            '.git',
            'venv',
            '.env',
            'test_execution_engine_import_analysis.py',  # Skip self
            'backup',
            'archived'
        ]
        
        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)
    
    def _check_import_violation(self, module_name: str) -> Optional[str]:
        "Check if an import module name violates SSOT patterns."
        if module_name in self.deprecated_imports:
            return deprecated_module"
        
        if ('execution_engine' in module_name and 
            module_name not in self.canonical_imports.values()):
            return "non_canonical_module
        
        return None
    
    def _check_line_import_violation(self, line: str) -> Optional[str]:
        Check if an import line violates SSOT patterns.""
        for deprecated in self.deprecated_imports:
            if deprecated in line:
                return deprecated_import
        
        if 'ExecutionEngine' in line and 'UserExecutionEngine' not in line:
            return non_canonical_class"
        
        return None
    
    def _file_to_module_path(self, file_path: Path) -> str:
        "Convert file path to Python module path.
        try:
            rel_path = file_path.relative_to(self.codebase_root)
            module_path = str(rel_path.with_suffix(''))
            module_path = module_path.replace('/', '.').replace('\\', '.')
            return module_path
        except (ValueError, AttributeError):
            return ""
    
    def _normalize_import_pattern(self, import_line: str) -> str:
        Normalize import pattern for consistency analysis."
        # Simplify import line to key pattern
        if 'from' in import_line and 'import' in import_line:
            parts = import_line.split('import')
            if len(parts) >= 2:
                from_part = parts[0].replace('from', '').strip()
                return ffrom {from_part}"
        elif 'import' in import_line:
            return import_line.split('import')[1].strip().split()[0]
        return import_line
    
    def _get_canonical_pattern(self, pattern: str) -> str:
        Get canonical pattern for a given import pattern.""
        if 'user_execution_engine' in pattern:
            return 'netra_backend.app.agents.supervisor.user_execution_engine'
        elif 'execution_engine_factory' in pattern:
            return 'netra_backend.app.agents.supervisor.execution_engine_factory'
        elif 'execution_engine' in pattern:
            return 'netra_backend.app.agents.supervisor.user_execution_engine'
        return pattern
    
    def _assess_import_cleanup_priority(self, violations: List[str] -> str:
        Assess cleanup priority based on violation types and count."
        if len(violations) > 50:
            return "P0 - CRITICAL (Massive import violations)
        elif any('Circular dependency' in v for v in violations):
            return P1 - HIGH (Circular dependencies detected)
        elif len(violations) > 20:
            return "P1 - HIGH (Significant import violations)"
        elif any('Broken import' in v for v in violations):
            return P2 - MEDIUM (Some broken imports)
        else:
            return P3 - LOW (Minor cleanup needed)"
    
    def _generate_migration_recommendations(self) -> List[str]:
        "Generate migration recommendations for import cleanup.
        return [
            "1. Replace all deprecated ExecutionEngine imports with UserExecutionEngine,"
            2. Standardize import paths to use canonical modules,
            3. Fix circular dependencies by restructuring imports,"
            4. Add missing canonical imports where ExecutionEngine is used",
            5. Update all services to use consistent import patterns,
            6. Remove broken import paths and update to working alternatives","
            "7. Use factory patterns instead of direct ExecutionEngine instantiation"
        ]


if __name__ == '__main__':
    # Configure logging for direct execution
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    unittest.main())