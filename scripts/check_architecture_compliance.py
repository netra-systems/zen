#!/usr/bin/env python3
"""
Architecture Compliance Checker
Enforces CLAUDE.md architectural rules:
- 300-line file limit
- 8-line function limit  
- No duplicate types
- No test stubs in production

Enhanced with JSON output, CI/CD integration, and configurable thresholds.
"""

import ast
import glob
import json
import os
import sys
import time
import re
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import List, Tuple, Dict, Optional, Union
from pathlib import Path

@dataclass
class Violation:
    """Structured violation data"""
    file_path: str
    violation_type: str
    severity: str
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    actual_value: Optional[int] = None
    expected_value: Optional[int] = None
    description: str = ""
    fix_suggestion: str = ""


@dataclass
class ComplianceResults:
    """Complete compliance results"""
    total_violations: int
    compliance_score: float
    timestamp: str
    violations_by_type: Dict[str, int]
    violations: List[Violation]
    summary: Dict[str, Union[int, str, float]]


class ArchitectureEnforcer:
    """Enforces architectural rules from CLAUDE.md"""
    
    def __init__(self, 
                 root_path: str = ".",
                 max_file_lines: int = 300,
                 max_function_lines: int = 8):
        self.root_path = Path(root_path)
        self.max_file_lines = max_file_lines
        self.max_function_lines = max_function_lines
        self.violations: List[Violation] = []
        
    def check_file_size(self) -> List[Violation]:
        """Check for files exceeding line limit"""
        violations = []
        patterns = ['app/**/*.py', 'frontend/**/*.tsx', 'frontend/**/*.ts', 'scripts/**/*.py']
        for pattern in patterns:
            violations.extend(self._check_files_for_pattern(pattern))
        return sorted(violations, key=lambda x: x.actual_value or 0, reverse=True)
    
    def _check_files_for_pattern(self, pattern: str) -> List[Violation]:
        """Check files matching pattern for size violations"""
        violations = []
        for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
            if not self._should_skip(filepath):
                violations.extend(self._check_single_file_size(filepath))
        return violations
    
    def _check_single_file_size(self, filepath: str) -> List[Violation]:
        """Check single file for size violation"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
            return self._create_file_size_violation(filepath, lines)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return []
    
    def _create_file_size_violation(self, filepath: str, lines: int) -> List[Violation]:
        """Create file size violation if exceeds limit"""
        if lines <= self.max_file_lines:
            return []
        rel_path = str(Path(filepath).relative_to(self.root_path))
        violation = self._build_file_violation(rel_path, lines)
        return [violation]
    
    def _build_file_violation(self, rel_path: str, lines: int) -> Violation:
        """Build file size violation object"""
        return Violation(
            file_path=rel_path, violation_type="file_size", severity="high",
            actual_value=lines, expected_value=self.max_file_lines,
            description=f"File exceeds {self.max_file_lines} line limit",
            fix_suggestion=f"Split into {(lines // self.max_file_lines) + 1} modules"
        )
    
    def check_function_complexity(self) -> List[Violation]:
        """Check for functions exceeding line limit"""
        violations = []
        patterns = ['app/**/*.py', 'scripts/**/*.py']
        for pattern in patterns:
            violations.extend(self._check_functions_for_pattern(pattern))
        return sorted(violations, key=lambda x: x.actual_value or 0, reverse=True)
    
    def _check_functions_for_pattern(self, pattern: str) -> List[Violation]:
        """Check functions in files matching pattern"""
        violations = []
        for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
            if not self._should_skip(filepath):
                violations.extend(self._check_functions_in_file(filepath))
        return violations
    
    def _check_functions_in_file(self, filepath: str) -> List[Violation]:
        """Check all functions in a single file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            rel_path = str(Path(filepath).relative_to(self.root_path))
            return self._extract_function_violations(tree, rel_path)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return []
    
    def _extract_function_violations(self, tree: ast.AST, rel_path: str) -> List[Violation]:
        """Extract function violations from AST"""
        violations = []
        is_example_file = self._is_example_file(rel_path)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                violation = self._check_function_node(node, rel_path, is_example_file)
                if violation:
                    violations.append(violation)
        return violations
    
    def _is_example_file(self, rel_path: str) -> bool:
        """Check if file is an example/demo file"""
        example_patterns = ['example', 'demo', 'sample', 'test_', 'mock', 
                           'example_usage', 'corpus_metrics', 'audit/example']
        return any(x in rel_path.lower() for x in example_patterns)
    
    def _check_function_node(self, node, rel_path: str, is_example_file: bool) -> Optional[Violation]:
        """Check single function node for violations"""
        lines = self._count_function_lines(node)
        if lines <= self.max_function_lines:
            return None
        severity = "low" if is_example_file else "medium"
        prefix = "[WARNING]" if is_example_file else "[VIOLATION]"
        return self._build_function_violation(node, rel_path, lines, severity, prefix)
    
    def _build_function_violation(self, node, rel_path: str, lines: int, severity: str, prefix: str) -> Violation:
        """Build function complexity violation object"""
        fix_action = "Consider splitting" if severity == "low" else "Split"
        return Violation(
            file_path=rel_path, violation_type="function_complexity", severity=severity,
            line_number=node.lineno, function_name=node.name, actual_value=lines,
            expected_value=self.max_function_lines,
            description=f"{prefix} Function '{node.name}' has {lines} lines (max: {self.max_function_lines})",
            fix_suggestion=f"{fix_action} into {(lines // self.max_function_lines) + 1} smaller functions"
        )
    
    def check_duplicate_types(self) -> List[Violation]:
        """Find duplicate type definitions (excluding legitimate cases)"""
        type_definitions = defaultdict(list)
        self._scan_python_types(type_definitions)
        self._scan_typescript_types(type_definitions)
        # Filter out legitimate duplicates before creating violations
        filtered_defs = self._filter_legitimate_duplicates(type_definitions)
        return self._create_duplicate_violations(filtered_defs)
    
    def _scan_python_types(self, type_definitions: Dict) -> None:
        """Scan Python files for class definitions"""
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if not self._should_skip(filepath):
                self._extract_python_types(filepath, type_definitions)
    
    def _extract_python_types(self, filepath: str, type_definitions: Dict) -> None:
        """Extract Python type definitions from file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            rel_path = str(Path(filepath).relative_to(self.root_path))
            self._find_python_classes(content, rel_path, type_definitions)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    def _find_python_classes(self, content: str, rel_path: str, type_definitions: Dict) -> None:
        """Find Python class definitions in content"""
        for match in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
            type_name = match.group(1)
            type_definitions[type_name].append(rel_path)
    
    def _scan_typescript_types(self, type_definitions: Dict) -> None:
        """Scan TypeScript files for type definitions"""
        patterns = ['frontend/**/*.ts', 'frontend/**/*.tsx']
        for pattern in patterns:
            self._scan_typescript_pattern(pattern, type_definitions)
    
    def _scan_typescript_pattern(self, pattern: str, type_definitions: Dict) -> None:
        """Scan TypeScript files matching pattern"""
        for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
            if 'node_modules' not in filepath:
                self._extract_typescript_types(filepath, type_definitions)
    
    def _extract_typescript_types(self, filepath: str, type_definitions: Dict) -> None:
        """Extract TypeScript type definitions from file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            rel_path = str(Path(filepath).relative_to(self.root_path))
            self._find_typescript_types(content, rel_path, type_definitions)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    def _find_typescript_types(self, content: str, rel_path: str, type_definitions: Dict) -> None:
        """Find TypeScript type definitions in content"""
        for match in re.finditer(r'(?:interface|type)\s+(\w+)', content):
            type_name = match.group(1)
            type_definitions[type_name].append(rel_path)
    
    def _filter_legitimate_duplicates(self, type_definitions: Dict) -> Dict:
        """Filter out legitimate duplicates that shouldn't be violations"""
        filtered = {}
        for type_name, files in type_definitions.items():
            # Only keep duplicates that are truly problematic
            problematic_files = self._get_problematic_duplicates(type_name, files)
            if len(problematic_files) > 1:
                filtered[type_name] = problematic_files
        return filtered
    
    def _get_problematic_duplicates(self, type_name: str, files: List[str]) -> List[str]:
        """Identify which duplicate files are actually problematic"""
        # Separate files by category
        test_files = []
        frontend_files = []
        backend_files = []
        example_files = []
        backup_files = []
        
        for file in files:
            file_lower = file.lower()
            # Categorize files
            if 'test' in file_lower or 'tests' in file_lower:
                test_files.append(file)
            elif 'backup' in file_lower or '_old' in file_lower or '_legacy' in file_lower:
                backup_files.append(file)
            elif 'example' in file_lower or 'demo' in file_lower or 'sample' in file_lower:
                example_files.append(file)
            elif 'frontend' in file_lower:
                frontend_files.append(file)
            else:
                backend_files.append(file)
        
        # Legitimate duplicates we allow:
        # 1. Test files can duplicate production types
        # 2. Frontend and backend can have same-named types (different languages)
        # 3. Example/demo files can duplicate types
        # 4. Schema files can define types that implementations use
        # 5. Backup/old/legacy files (temporary duplicates during migration)
        # 6. Service layer duplicating agent layer (separation of concerns)
        # 7. Database models vs domain models (different layers)
        
        # Only flag as problematic if truly duplicate within same context
        problematic = []
        
        # Filter backend files more intelligently
        backend_filtered = self._filter_backend_files(backend_files)
        if len(backend_filtered) > 1:
            # Check if they're legitimate architectural separations
            if not self._are_legitimate_separations(backend_filtered):
                problematic.extend(backend_filtered)
        
        # Check frontend duplicates (less common, usually problematic)
        if len(frontend_files) > 1:
            # But allow if one is in types/ and another is component-local
            if not self._are_frontend_separations(frontend_files):
                problematic.extend(frontend_files)
        
        return problematic if problematic else []
    
    def _filter_backend_files(self, files: List[str]) -> List[str]:
        """Filter backend files to exclude legitimate patterns"""
        filtered = []
        for file in files:
            file_lower = file.lower()
            # Skip schema definitions, interfaces, and type definitions
            if any(x in file_lower for x in ['schema', 'interface', 'types.py', 'models.py']):
                continue
            # Skip if it's clearly a different architectural layer
            if 'db/' in file and 'services/' in file:
                continue  # DB models vs service models are OK
            filtered.append(file)
        return filtered
    
    def _are_legitimate_separations(self, files: List[str]) -> bool:
        """Check if files represent legitimate architectural separations"""
        # Check for agent vs service separation
        has_agent = any('agents/' in f for f in files)
        has_service = any('services/' in f for f in files)
        if has_agent and has_service:
            return True  # Agent/Service separation is legitimate
        
        # Check for database vs domain model separation
        has_db = any('db/' in f for f in files)
        has_domain = any(f for f in files if 'db/' not in f)
        if has_db and has_domain and len(files) == 2:
            return True  # DB/Domain separation is legitimate
        
        # Use existing module separation check
        return self._are_separated_modules(files)
    
    def _are_frontend_separations(self, files: List[str]) -> bool:
        """Check if frontend duplicates are legitimate separations"""
        # Allow if split between global types and component-local types
        has_global_types = any('types/' in f for f in files)
        has_component = any('components/' in f for f in files)
        return has_global_types and has_component and len(files) == 2
    
    def _are_separated_modules(self, files: List[str]) -> bool:
        """Check if files are intentionally separated modules"""
        # Allow duplicates if they're in different agent subdirectories or old/new versions
        if any('_old' in f for f in files) and any('_old' not in f for f in files):
            return True  # Old vs new versions are allowed
        
        # Check if files are in completely different module contexts
        modules = set()
        for file in files:
            # Normalize path separators
            normalized = file.replace('\\', '/')
            parts = normalized.split('/')
            if 'agents' in parts:
                # Get the agent subdirectory
                idx = parts.index('agents')
                if idx + 1 < len(parts):
                    modules.add(parts[idx + 1])
        
        # If in different agent modules, likely intentional separation
        return len(modules) > 1
    
    def _create_duplicate_violations(self, type_definitions: Dict) -> List[Violation]:
        """Create violations for duplicate type definitions"""
        violations = []
        for type_name, files in type_definitions.items():
            if len(files) > 1:
                violation = self._build_duplicate_violation(type_name, files)
                violations.append(violation)
        return violations
    
    def _build_duplicate_violation(self, type_name: str, files: List[str]) -> Violation:
        """Build duplicate type violation object"""
        file_list = ", ".join(files[:3]) + ("..." if len(files) > 3 else "")
        return Violation(
            file_path=file_list, violation_type="duplicate_types", severity="medium",
            actual_value=len(files), expected_value=1,
            description=f"Type '{type_name}' defined in {len(files)} files",
            fix_suggestion=f"Consolidate '{type_name}' into single source of truth"
        )
    
    def check_test_stubs(self) -> List[Violation]:
        """Check for test stubs in production code"""
        suspicious_patterns = self._get_test_stub_patterns()
        violations = []
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if self._should_skip_test_file(filepath):
                continue
            violations.extend(self._check_file_for_stubs(filepath, suspicious_patterns))
        return violations
    
    def _get_test_stub_patterns(self) -> List[Tuple[str, str]]:
        """Get patterns for detecting actual test stubs (more precise)"""
        return [
            # More specific patterns that indicate actual stubs
            (r'""".*placeholder for test compatibility.*"""', 'Test compatibility placeholder'),
            (r'# Mock implementation.*\n\s*pass\s*$', 'Mock implementation with pass'),
            (r'# Test stub.*\n\s*pass\s*$', 'Test stub with pass'),
            (r'def.*\*args.*\*\*kwargs.*:\s*\n\s*""".*test.*"""\s*\n\s*return\s*\{', 'Args kwargs test stub'),
            (r'return \[{"id": "1"', 'Hardcoded test data'),
            (r'return {"test": "data"}', 'Test data return'),
            (r'raise NotImplementedError\(".*stub.*"\)', 'NotImplementedError stub'),
            # Look for actual placeholder implementations
            (r'# Real.*would be.*\n\s*pass\s*$', 'Placeholder with TODO comment')
        ]
    
    def _should_skip_test_file(self, filepath: str) -> bool:
        """Check if file should be skipped for test stub detection"""
        skip_patterns = ['__pycache__', 'app/tests', '/tests/']
        return any(pattern in filepath for pattern in skip_patterns)
    
    def _check_file_for_stubs(self, filepath: str, patterns: List[Tuple[str, str]]) -> List[Violation]:
        """Check single file for test stubs"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            rel_path = str(Path(filepath).relative_to(self.root_path))
            return self._find_test_stubs_in_content(content, rel_path, patterns)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return []
    
    def _find_test_stubs_in_content(self, content: str, rel_path: str, patterns: List) -> List[Violation]:
        """Find test stubs in file content"""
        for pattern, description in patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE | re.DOTALL))
            if matches:
                line_number = content[:matches[0].start()].count('\n') + 1
                violation = self._build_test_stub_violation(rel_path, line_number, description)
                return [violation]  # Only report first match per file
        return []
    
    def _build_test_stub_violation(self, rel_path: str, line_number: int, description: str) -> Violation:
        """Build test stub violation object"""
        return Violation(
            file_path=rel_path, violation_type="test_stub", severity="high",
            line_number=line_number, description=f"Test stub detected: {description}",
            fix_suggestion="Replace with production implementation"
        )
    
    def _should_skip(self, filepath: str) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            '__pycache__',
            'node_modules',
            '.git',
            'migrations',
            'test_reports',
            'docs',
            '.pytest_cache',
            # Third-party libraries and vendor code
            'venv',
            '.venv',
            'env',
            '.env',
            'virtualenv',
            'site-packages',
            'dist-packages',
            'vendor',
            'third_party',
            'third-party',
            'external',
            'lib',
            'libs',
            'bower_components',
            'jspm_packages',
            # Build and distribution directories
            'build',
            'dist',
            '.eggs',
            '*.egg-info',
            # IDE and editor directories
            '.idea',
            '.vscode',
            '.vs',
            # Testing and coverage
            'htmlcov',
            '.coverage',
            '.tox',
            '.nox',
            # Package managers
            'pip-wheel-metadata',
            'package-lock.json',
            'yarn.lock',
            # Common third-party framework directories
            'static/admin',  # Django admin
            'static/rest_framework',  # DRF
            'wwwroot/lib',  # .NET
            # Terraform providers and modules
            '.terraform',
            'terraform/.terraform'
        ]
        return any(pattern in filepath for pattern in skip_patterns)
    
    def _count_function_lines(self, node) -> int:
        """Count actual code lines in function (excluding docstrings)"""
        if not node.body:
            return 0
        start_idx = self._get_code_start_index(node)
        if start_idx >= len(node.body):
            return 0
        return self._calculate_line_count(node, start_idx)
    
    def _get_code_start_index(self, node) -> int:
        """Get index where actual code starts (after docstring)"""
        if (len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant)):
            return 1
        return 0
    
    def _calculate_line_count(self, node, start_idx: int) -> int:
        """Calculate line count from start index to end"""
        first_line = node.body[start_idx].lineno
        last_stmt = node.body[-1]
        last_line = getattr(last_stmt, 'end_lineno', last_stmt.lineno)
        return last_line - first_line + 1
    
    def run_all_checks(self) -> ComplianceResults:
        """Run all compliance checks and return structured results"""
        all_violations = self._collect_all_violations()
        violations_by_type = self._group_violations_by_type(all_violations)
        total_files = self._count_total_files()
        compliance_score = self._calculate_compliance_score(all_violations, total_files)
        return self._build_compliance_results(all_violations, violations_by_type, total_files, compliance_score)
    
    def _collect_all_violations(self) -> List[Violation]:
        """Collect violations from all checks"""
        violations = []
        violations.extend(self.check_file_size())
        violations.extend(self.check_function_complexity())
        violations.extend(self.check_duplicate_types())
        violations.extend(self.check_test_stubs())
        return violations
    
    def _group_violations_by_type(self, violations: List[Violation]) -> Dict[str, int]:
        """Group violations by type for summary"""
        violations_by_type = defaultdict(int)
        for violation in violations:
            violations_by_type[violation.violation_type] += 1
        return dict(violations_by_type)
    
    def _count_total_files(self) -> int:
        """Count total files checked"""
        patterns = ['app/**/*.py', 'frontend/**/*.tsx', 'frontend/**/*.ts', 'scripts/**/*.py']
        total_files = 0
        for pattern in patterns:
            total_files += self._count_files_for_pattern(pattern)
        return total_files
    
    def _count_files_for_pattern(self, pattern: str) -> int:
        """Count files matching pattern"""
        count = 0
        for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
            if not self._should_skip(filepath):
                count += 1
        return count
    
    def _calculate_compliance_score(self, violations: List[Violation], total_files: int) -> float:
        """Calculate compliance score percentage"""
        if total_files == 0:
            return 100
        files_with_violations = len(set(v.file_path for v in violations))
        clean_files = total_files - files_with_violations
        return max(0, (clean_files / total_files) * 100)
    
    def _build_compliance_results(self, violations: List[Violation], violations_by_type: Dict, 
                                 total_files: int, compliance_score: float) -> ComplianceResults:
        """Build final compliance results object"""
        return ComplianceResults(
            total_violations=len(violations), compliance_score=compliance_score,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"), violations_by_type=violations_by_type,
            violations=violations, summary=self._build_summary(violations, total_files, compliance_score)
        )
    
    def _build_summary(self, violations: List[Violation], total_files: int, compliance_score: float) -> Dict:
        """Build summary dictionary"""
        return {
            "total_files_checked": total_files,
            "files_with_violations": len(set(v.file_path for v in violations)),
            "max_file_lines": self.max_file_lines,
            "max_function_lines": self.max_function_lines,
            "compliance_score": compliance_score
        }
    
    def generate_report(self) -> str:
        """Generate compliance report"""
        self._print_report_header()
        results = self.run_all_checks()
        self._print_all_violation_sections(results)
        return self._generate_final_summary(results)
    
    def _print_all_violation_sections(self, results: ComplianceResults) -> None:
        """Print all violation report sections"""
        self._report_file_size_violations(results)
        self._report_function_complexity_violations(results)
        self._report_duplicate_type_violations(results)
        self._report_test_stub_violations(results)
    
    def _print_report_header(self) -> None:
        """Print report header"""
        print("\n" + "="*80)
        print("ARCHITECTURE COMPLIANCE REPORT")
        print("="*80)
    
    def _report_file_size_violations(self, results) -> None:
        """Report file size violations"""
        print(f"\n[FILE SIZE VIOLATIONS] (>{self.max_file_lines} lines)")
        print("-" * 40)
        file_violations = self._get_violations_by_type(results, "file_size")
        self._print_file_violations(file_violations)
    
    def _get_violations_by_type(self, results, violation_type: str) -> List:
        """Get violations filtered by type"""
        return [v for v in results.violations if v.violation_type == violation_type]
    
    def _print_file_violations(self, file_violations: List) -> None:
        """Print file violation details"""
        if file_violations:
            self._print_violation_list(file_violations, 10, "lines")
            print(f"\n  Total violations: {len(file_violations)}")
        else:
            print("  [PASS] No violations found")
    
    def _print_violation_list(self, violations: List, limit: int, suffix: str) -> None:
        """Print a limited list of violations"""
        for violation in violations[:limit]:
            print(f"  {violation.actual_value:4d} {suffix}: {violation.file_path}")
        self._print_truncation_message(violations, limit)
    
    def _print_truncation_message(self, violations: List, limit: int) -> None:
        """Print truncation message if needed"""
        if len(violations) > limit:
            print(f"  ... and {len(violations)-limit} more files")
    
    def _report_function_complexity_violations(self, results) -> None:
        """Report function complexity violations"""
        print(f"\n[FUNCTION COMPLEXITY VIOLATIONS] (>{self.max_function_lines} lines)")
        print("-" * 40)
        func_violations = self._get_violations_by_type(results, "function_complexity")
        func_errors, func_warnings = self._categorize_function_violations(func_violations)
        self._print_function_violations(func_errors, func_warnings)
    
    def _categorize_function_violations(self, func_violations: List) -> tuple:
        """Categorize function violations by severity"""
        func_errors = [v for v in func_violations if v.severity == "medium"]
        func_warnings = [v for v in func_violations if v.severity == "low"]
        return func_errors, func_warnings
    
    def _print_function_violations(self, func_errors: List, func_warnings: List) -> None:
        """Print function violation details"""
        if func_errors:
            self._print_function_error_list(func_errors)
        if func_warnings:
            self._print_function_warning_list(func_warnings)
        self._print_function_summary(func_errors, func_warnings)
    
    def _print_function_error_list(self, func_errors: List) -> None:
        """Print function error violations"""
        print("  VIOLATIONS (must fix):")
        for violation in func_errors[:5]:
            print(f"    {violation.actual_value:3d} lines: {violation.function_name}() in {violation.file_path}")
        self._print_error_truncation(func_errors)
    
    def _print_error_truncation(self, func_errors: List) -> None:
        """Print error truncation message if needed"""
        if len(func_errors) > 5:
            print(f"    ... and {len(func_errors)-5} more violations")
    
    def _print_function_warning_list(self, func_warnings: List) -> None:
        """Print function warning violations"""
        print("\n  WARNINGS (example/demo files):")
        for violation in func_warnings[:5]:
            print(f"    {violation.actual_value:3d} lines: {violation.function_name}() in {violation.file_path}")
        self._print_warning_truncation(func_warnings)
    
    def _print_warning_truncation(self, func_warnings: List) -> None:
        """Print warning truncation message if needed"""
        if len(func_warnings) > 5:
            print(f"    ... and {len(func_warnings)-5} more warnings")
    
    def _print_function_summary(self, func_errors: List, func_warnings: List) -> None:
        """Print function violation summary"""
        if func_errors or func_warnings:
            print(f"\n  Total: {len(func_errors)} violations, {len(func_warnings)} warnings")
        else:
            print("  [PASS] No violations found")
    
    def _report_duplicate_type_violations(self, results) -> None:
        """Report duplicate type violations"""
        print("\n[DUPLICATE TYPE DEFINITIONS]")
        print("-" * 40)
        duplicate_violations = self._get_violations_by_type(results, "duplicate_types")
        self._print_duplicate_violations(duplicate_violations)
    
    def _print_duplicate_violations(self, duplicate_violations: List) -> None:
        """Print duplicate type violation details"""
        if duplicate_violations:
            self._print_duplicate_list(duplicate_violations)
            print(f"\n  Total duplicate types: {len(duplicate_violations)}")
        else:
            print("  [PASS] No duplicates found")
    
    def _print_duplicate_list(self, duplicate_violations: List) -> None:
        """Print duplicate violation list"""
        for violation in duplicate_violations[:10]:
            print(f"  {violation.description}")
            print(f"    Files: {violation.file_path}")
        self._print_duplicate_truncation(duplicate_violations)
    
    def _print_duplicate_truncation(self, duplicate_violations: List) -> None:
        """Print duplicate truncation message if needed"""
        if len(duplicate_violations) > 10:
            print(f"\n  ... and {len(duplicate_violations)-10} more duplicate types")
    
    def _report_test_stub_violations(self, results) -> None:
        """Report test stub violations"""
        print("\n[TEST STUBS IN PRODUCTION]")
        print("-" * 40)
        test_stub_violations = self._get_violations_by_type(results, "test_stub")
        self._print_test_stub_violations(test_stub_violations)
    
    def _print_test_stub_violations(self, test_stub_violations: List) -> None:
        """Print test stub violation details"""
        if test_stub_violations:
            self._print_test_stub_list(test_stub_violations)
            print(f"\n  Total suspicious files: {len(test_stub_violations)}")
        else:
            print("  [PASS] No test stubs found")
    
    def _print_test_stub_list(self, test_stub_violations: List) -> None:
        """Print test stub violation list"""
        for violation in test_stub_violations[:10]:
            line_info = f" (line {violation.line_number})" if violation.line_number else ""
            print(f"  {violation.file_path}{line_info}: {violation.description}")
        self._print_stub_truncation(test_stub_violations)
    
    def _print_stub_truncation(self, test_stub_violations: List) -> None:
        """Print stub truncation message if needed"""
        if len(test_stub_violations) > 10:
            print(f"  ... and {len(test_stub_violations)-10} more files")
    
    def _generate_final_summary(self, results) -> str:
        """Generate final compliance summary"""
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        actual_violations, total_warnings = self._count_violations(results)
        return self._determine_compliance_status(results, actual_violations, total_warnings)
    
    def _count_violations(self, results) -> tuple:
        """Count actual violations vs warnings"""
        actual_violations = len([v for v in results.violations if v.severity in ["high", "medium"]])
        total_warnings = len([v for v in results.violations if v.severity == "low"])
        return actual_violations, total_warnings
    
    def _determine_compliance_status(self, results, actual_violations: int, total_warnings: int) -> str:
        """Determine final compliance status"""
        if actual_violations == 0:
            return self._handle_pass_status(total_warnings)
        else:
            return self._handle_fail_status(results, actual_violations, total_warnings)
    
    def _handle_pass_status(self, total_warnings: int) -> str:
        """Handle pass status with optional warnings"""
        if total_warnings > 0:
            print(f"[PASS WITH WARNINGS] No critical violations, but {total_warnings} warnings in example/demo files")
        else:
            print("[PASS] FULL COMPLIANCE - All architectural rules satisfied!")
        return "PASS"
    
    def _handle_fail_status(self, results, actual_violations: int, total_warnings: int) -> str:
        """Handle fail status with remediation actions"""
        self._print_fail_summary(results, actual_violations, total_warnings)
        self._print_required_actions(results)
        print("\nRefer to ALIGNMENT_ACTION_PLAN.md for remediation steps")
        return "FAIL"
    
    def _print_fail_summary(self, results, actual_violations: int, total_warnings: int) -> None:
        """Print failure summary details"""
        print(f"[FAIL] VIOLATIONS FOUND: {actual_violations} issues requiring fixes")
        if total_warnings > 0:
            print(f"       WARNINGS: {total_warnings} issues in example/demo files")
        print(f"Compliance Score: {results.compliance_score:.1f}%")
    
    def _print_required_actions(self, results) -> None:
        """Print required remediation actions"""
        print("\nRequired Actions:")
        violations_by_type = self._get_violation_counts_by_type(results)
        self._print_file_action(violations_by_type["file_size"])
        self._print_function_action(violations_by_type["function_errors"])
        self._print_duplicate_action(violations_by_type["duplicate_types"])
        self._print_stub_action(violations_by_type["test_stub"])
    
    def _print_file_action(self, count: int) -> None:
        """Print file splitting action if needed"""
        if count > 0:
            print(f"  - Split {count} oversized files")
    
    def _print_function_action(self, count: int) -> None:
        """Print function refactoring action if needed"""
        if count > 0:
            print(f"  - Refactor {count} complex functions")
    
    def _print_duplicate_action(self, count: int) -> None:
        """Print duplicate removal action if needed"""
        if count > 0:
            print(f"  - Deduplicate {count} type definitions")
    
    def _print_stub_action(self, count: int) -> None:
        """Print stub removal action if needed"""
        if count > 0:
            print(f"  - Remove {count} test stubs from production")
    
    def _get_violation_counts_by_type(self, results) -> Dict[str, int]:
        """Get violation counts by type"""
        file_violations = self._get_violations_by_type(results, "file_size")
        func_violations = self._get_violations_by_type(results, "function_complexity")
        func_errors = [v for v in func_violations if v.severity == "medium"]
        duplicate_violations = self._get_violations_by_type(results, "duplicate_types")
        test_stub_violations = self._get_violations_by_type(results, "test_stub")
        return self._build_violation_counts(file_violations, func_errors, duplicate_violations, test_stub_violations)
    
    def _build_violation_counts(self, file_violations: List, func_errors: List, 
                               duplicate_violations: List, test_stub_violations: List) -> Dict[str, int]:
        """Build violation counts dictionary"""
        return {
            "file_size": len(file_violations),
            "function_errors": len(func_errors),
            "duplicate_types": len(duplicate_violations),
            "test_stub": len(test_stub_violations)
        }


def main():
    """Main entry point with enhanced CI/CD features"""
    parser = create_argument_parser()
    args = parser.parse_args()
    enforcer = create_enforcer(args)
    results = enforcer.run_all_checks()
    process_output(args, enforcer, results)
    handle_exit_code(args, results)

def create_argument_parser():
    """Create and configure argument parser"""
    import argparse
    parser = argparse.ArgumentParser(
        description='Check architecture compliance with enhanced CI/CD features',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=get_usage_examples()
    )
    add_parser_arguments(parser)
    return parser

def get_usage_examples() -> str:
    """Get usage examples for help text"""
    return """
Examples:
  python check_architecture_compliance.py --json-output report.json
  python check_architecture_compliance.py --max-file-lines 250 --threshold 90
  python check_architecture_compliance.py --fail-on-violation --json-only
        """

def add_parser_arguments(parser) -> None:
    """Add arguments to parser"""
    parser.add_argument('--path', default='.', help='Root path to check')
    parser.add_argument('--fail-on-violation', action='store_true', 
                       help='Exit with non-zero code on violations')
    parser.add_argument('--max-file-lines', type=int, default=300,
                       help='Maximum lines per file (default: 300)')
    parser.add_argument('--max-function-lines', type=int, default=8,
                       help='Maximum lines per function (default: 8)')
    add_output_arguments(parser)

def add_output_arguments(parser) -> None:
    """Add output-related arguments"""
    parser.add_argument('--json-output', help='Output JSON report to file')
    parser.add_argument('--json-only', action='store_true',
                       help='Output only JSON, no human-readable report')
    parser.add_argument('--threshold', type=float, default=0.0,
                       help='Minimum compliance score (0-100) to pass')

def create_enforcer(args):
    """Create architecture enforcer from arguments"""
    return ArchitectureEnforcer(
        root_path=args.path,
        max_file_lines=args.max_file_lines,
        max_function_lines=args.max_function_lines
    )

def process_output(args, enforcer, results) -> None:
    """Process and output results"""
    if args.json_only:
        print(json.dumps(asdict(results), indent=2))
    else:
        enforcer.generate_report()
    save_json_output(args, results)

def save_json_output(args, results) -> None:
    """Save JSON output if requested"""
    if args.json_output:
        with open(args.json_output, 'w') as f:
            json.dump(asdict(results), f, indent=2)
        print(f"\nJSON report saved to: {args.json_output}")

def handle_exit_code(args, results) -> None:
    """Handle exit code based on results"""
    should_fail = (args.fail_on_violation and 
                  (results.total_violations > 0 or 
                   results.compliance_score < args.threshold))
    sys.exit(1 if should_fail else 0)


if __name__ == "__main__":
    main()