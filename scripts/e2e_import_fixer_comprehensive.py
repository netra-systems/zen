#!/usr/bin/env python3
"""
Comprehensive E2E Import Fixer for Netra Backend
Discovers and fixes all import issues in E2E tests to ensure they can load and run.
"""

import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add project root to path

@dataclass
class ImportIssue:
    """Represents an import issue found in a file."""
    file_path: str
    line_number: int
    issue_type: str  # 'missing_module', 'incorrect_path', 'circular', 'syntax_error', etc.
    original_import: str
    suggested_fix: str
    error_message: str
    severity: str  # 'critical', 'warning', 'info'

@dataclass
class FileAnalysisResult:
    """Result of analyzing a single file."""
    file_path: str
    can_import: bool
    issues: List[ImportIssue]
    dependencies: List[str]
    import_errors: List[str]
    syntax_errors: List[str]

@dataclass
class E2EImportReport:
    """Comprehensive report of E2E import analysis."""
    timestamp: str
    total_files: int
    files_with_issues: int
    files_fixed: int
    critical_issues: int
    warnings: int
    file_results: List[FileAnalysisResult]
    common_patterns: Dict[str, int]
    recommendations: List[str]

class E2EImportFixer:
    """Comprehensive import fixer for E2E tests."""
    
    def __init__(self, project_root: Path = None, dry_run: bool = False, verbose: bool = False):
        self.project_root = project_root or PROJECT_ROOT
        self.dry_run = dry_run
        self.verbose = verbose
        
        # Test directories
        self.e2e_dirs = [
            self.project_root / "tests" / "unified" / "e2e",
            self.project_root / "netra_backend" / "tests" / "integration",
            self.project_root / "netra_backend" / "tests" / "auth_integration",
            self.project_root / "netra_backend" / "tests" / "critical",
        ]
        
        # Common import mappings
        self.import_mappings = {
            # Backend app imports
            r'^from app\.': 'from netra_backend.app.',
            r'^import app\.': 'import netra_backend.app.',
            
            # Test imports
            r'^from tests\.': 'from netra_backend.tests.',
            r'^import tests\.': 'import netra_backend.tests.',
            
            # Unified test imports
            r'^from unified\.': 'from tests.',
            r'^import unified\.': 'import tests.unified.',
            
            # E2E specific
            r'^from e2e\.': 'from tests.e2e.',
            r'^import e2e\.': 'import tests.unified.e2e.',
            
            # Integration test imports
            r'^from integration\.': 'from netra_backend.tests.integration.',
            r'^import integration\.': 'import netra_backend.tests.integration.',
            
            # Test framework imports
            r'^from test_framework\.': 'from test_framework.',
            r'^import test_framework\.': 'import test_framework.',
        }
        
        # Known module relocations
        self.module_relocations = {
            'validate_token': ('netra_backend.app.auth_integration.auth', 'validate_token_jwt'),
            'websocket_endpoint': ('netra_backend.app.routes.websocket_routes', 'websocket_endpoint'),
            'ConnectionManager': ('netra_backend.app.services.connection_manager', 'ConnectionManager'),
            'WebSocketManager': ('netra_backend.app.services.websocket_manager', 'WebSocketManager'),
        }
        
        # Track results
        self.file_results: List[FileAnalysisResult] = []
        self.fixes_applied: Dict[str, List[str]] = {}
        
    def discover_all_e2e_tests(self) -> List[Path]:
        """Discover all E2E test files."""
        test_files = []
        
        for test_dir in self.e2e_dirs:
            if test_dir.exists():
                # Find all test files
                test_files.extend(test_dir.glob("test_*.py"))
                test_files.extend(test_dir.glob("*_test.py"))
                test_files.extend(test_dir.glob("**/test_*.py"))
                test_files.extend(test_dir.glob("**/*_test.py"))
                
                # Also include helper and fixture files
                test_files.extend(test_dir.glob("*_helpers.py"))
                test_files.extend(test_dir.glob("*_fixtures.py"))
                test_files.extend(test_dir.glob("*_utils.py"))
                test_files.extend(test_dir.glob("*_core.py"))
                test_files.extend(test_dir.glob("*_services.py"))
                test_files.extend(test_dir.glob("*_managers.py"))
                
        # Remove duplicates and sort
        test_files = list(set(test_files))
        test_files.sort()
        
        if self.verbose:
            print(f"Discovered {len(test_files)} E2E test files")
            
        return test_files
        
    def analyze_file(self, file_path: Path) -> FileAnalysisResult:
        """Analyze a single file for import issues."""
        issues = []
        dependencies = []
        import_errors = []
        syntax_errors = []
        can_import = True
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Check syntax first
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                syntax_errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
                can_import = False
                return FileAnalysisResult(
                    file_path=str(file_path),
                    can_import=False,
                    issues=[],
                    dependencies=[],
                    import_errors=[],
                    syntax_errors=syntax_errors
                )
            
            # Analyze imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        dependencies.append(module_name)
                        issue = self._check_import(module_name, node.lineno, file_path)
                        if issue:
                            issues.append(issue)
                            
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    dependencies.append(module)
                    
                    # Check each imported name
                    for alias in node.names:
                        full_import = f"from {module} import {alias.name}"
                        issue = self._check_import_from(module, alias.name, node.lineno, file_path)
                        if issue:
                            issues.append(issue)
            
            # Try to actually import the file to catch runtime issues
            if can_import and not syntax_errors:
                import_error = self._try_import_file(file_path)
                if import_error:
                    import_errors.append(import_error)
                    can_import = False
                    
        except Exception as e:
            import_errors.append(f"Error analyzing file: {str(e)}")
            can_import = False
            
        return FileAnalysisResult(
            file_path=str(file_path),
            can_import=can_import,
            issues=issues,
            dependencies=list(set(dependencies)),
            import_errors=import_errors,
            syntax_errors=syntax_errors
        )
        
    def _check_import(self, module_name: str, line_number: int, file_path: Path) -> Optional[ImportIssue]:
        """Check if an import statement is valid."""
        # Check against known patterns
        for pattern, replacement in self.import_mappings.items():
            if re.match(pattern, f"import {module_name}"):
                suggested = re.sub(pattern, replacement, f"import {module_name}")
                return ImportIssue(
                    file_path=str(file_path),
                    line_number=line_number,
                    issue_type='incorrect_path',
                    original_import=f"import {module_name}",
                    suggested_fix=suggested,
                    error_message=f"Import path needs updating",
                    severity='warning'
                )
                
        # Try to import the module
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                return ImportIssue(
                    file_path=str(file_path),
                    line_number=line_number,
                    issue_type='missing_module',
                    original_import=f"import {module_name}",
                    suggested_fix=self._suggest_fix_for_module(module_name),
                    error_message=f"Module '{module_name}' not found",
                    severity='critical'
                )
        except (ImportError, ModuleNotFoundError, ValueError) as e:
            return ImportIssue(
                file_path=str(file_path),
                line_number=line_number,
                issue_type='import_error',
                original_import=f"import {module_name}",
                suggested_fix=self._suggest_fix_for_module(module_name),
                error_message=str(e),
                severity='critical'
            )
            
        return None
        
    def _check_import_from(self, module: str, name: str, line_number: int, file_path: Path) -> Optional[ImportIssue]:
        """Check if a 'from X import Y' statement is valid."""
        full_import = f"from {module} import {name}"
        
        # Check for known relocations
        if name in self.module_relocations:
            new_module, new_name = self.module_relocations[name]
            if module != new_module or name != new_name:
                return ImportIssue(
                    file_path=str(file_path),
                    line_number=line_number,
                    issue_type='relocated_module',
                    original_import=full_import,
                    suggested_fix=f"from {new_module} import {new_name}",
                    error_message=f"Module/function relocated",
                    severity='warning'
                )
        
        # Check against known patterns
        for pattern, replacement in self.import_mappings.items():
            if re.match(pattern, full_import):
                suggested = re.sub(pattern, replacement, full_import)
                return ImportIssue(
                    file_path=str(file_path),
                    line_number=line_number,
                    issue_type='incorrect_path',
                    original_import=full_import,
                    suggested_fix=suggested,
                    error_message=f"Import path needs updating",
                    severity='warning'
                )
                
        # Try to import
        try:
            if module:
                spec = importlib.util.find_spec(module)
                if spec is None:
                    suggested_module = self._suggest_fix_for_module(module)
                    return ImportIssue(
                        file_path=str(file_path),
                        line_number=line_number,
                        issue_type='missing_module',
                        original_import=full_import,
                        suggested_fix=f"from {suggested_module} import {name}" if suggested_module else full_import,
                        error_message=f"Module '{module}' not found",
                        severity='critical'
                    )
                    
                # Try to import the specific name
                try:
                    exec(full_import)
                except (ImportError, AttributeError) as e:
                    return ImportIssue(
                        file_path=str(file_path),
                        line_number=line_number,
                        issue_type='import_error',
                        original_import=full_import,
                        suggested_fix=self._suggest_fix_for_import(module, name),
                        error_message=str(e),
                        severity='critical'
                    )
                    
        except Exception as e:
            return ImportIssue(
                file_path=str(file_path),
                line_number=line_number,
                issue_type='import_error',
                original_import=full_import,
                suggested_fix=full_import,
                error_message=str(e),
                severity='warning'
            )
            
        return None
        
    def _suggest_fix_for_module(self, module: str) -> str:
        """Suggest a fix for a missing module."""
        # Common fixes
        if module.startswith('app.'):
            return module.replace('app.', 'netra_backend.app.')
        elif module.startswith('tests.') and 'unified' not in module:
            return module.replace('tests.', 'netra_backend.tests.')
        elif module.startswith('unified.'):
            return module.replace('unified.', 'tests.unified.')
        elif module.startswith('e2e.'):
            return module.replace('e2e.', 'tests.unified.e2e.')
        elif module.startswith('integration.'):
            return module.replace('integration.', 'netra_backend.tests.integration.')
            
        return module
        
    def _suggest_fix_for_import(self, module: str, name: str) -> str:
        """Suggest a fix for a specific import."""
        # Check relocations
        if name in self.module_relocations:
            new_module, new_name = self.module_relocations[name]
            return f"from {new_module} import {new_name}"
            
        # Try fixing the module path
        fixed_module = self._suggest_fix_for_module(module)
        return f"from {fixed_module} import {name}"
        
    def _try_import_file(self, file_path: Path) -> Optional[str]:
        """Try to import a file and return any error."""
        try:
            # Create a module name from the file path
            relative_path = file_path.relative_to(self.project_root)
            module_name = str(relative_path).replace(os.sep, '.').replace('.py', '')
            
            # Try to import
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return None
                
        except Exception as e:
            return f"Import failed: {str(e)}"
            
        return None
        
    def fix_file(self, file_path: Path, issues: List[ImportIssue]) -> bool:
        """Fix import issues in a file."""
        if not issues:
            return False
            
        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            fixes = []
            
            # Sort issues by line number in reverse to avoid offset issues
            issues.sort(key=lambda x: x.line_number, reverse=True)
            
            for issue in issues:
                if issue.suggested_fix and issue.suggested_fix != issue.original_import:
                    # Apply the fix
                    content = content.replace(issue.original_import, issue.suggested_fix)
                    fixes.append(f"Line {issue.line_number}: {issue.original_import} -> {issue.suggested_fix}")
                    
            if content != original_content:
                if not self.dry_run:
                    file_path.write_text(content, encoding='utf-8')
                    
                self.fixes_applied[str(file_path)] = fixes
                if self.verbose:
                    print(f"Fixed {len(fixes)} issues in {file_path.name}")
                return True
                
        except Exception as e:
            if self.verbose:
                print(f"Error fixing {file_path}: {e}")
                
        return False
        
    def run_comprehensive_fix(self) -> E2EImportReport:
        """Run comprehensive import discovery and fixing."""
        print("Starting comprehensive E2E import analysis and fixing...")
        
        # Discover all test files
        test_files = self.discover_all_e2e_tests()
        
        # Analyze each file
        print(f"Analyzing {len(test_files)} files...")
        for i, file_path in enumerate(test_files, 1):
            if self.verbose or i % 10 == 0:
                print(f"Progress: {i}/{len(test_files)} files...")
                
            result = self.analyze_file(file_path)
            self.file_results.append(result)
            
            # Fix issues if found
            if result.issues and not self.dry_run:
                self.fix_file(file_path, result.issues)
                
        # Generate report
        report = self.generate_report()
        
        return report
        
    def generate_report(self) -> E2EImportReport:
        """Generate comprehensive report."""
        # Calculate statistics
        total_files = len(self.file_results)
        files_with_issues = sum(1 for r in self.file_results if r.issues or r.import_errors or r.syntax_errors)
        files_fixed = len(self.fixes_applied)
        
        # Count issue severities
        critical_issues = 0
        warnings = 0
        for result in self.file_results:
            for issue in result.issues:
                if issue.severity == 'critical':
                    critical_issues += 1
                elif issue.severity == 'warning':
                    warnings += 1
                    
        # Find common patterns
        pattern_counts = {}
        for result in self.file_results:
            for issue in result.issues:
                pattern = issue.issue_type
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
                
        # Generate recommendations
        recommendations = []
        if critical_issues > 0:
            recommendations.append(f"Fix {critical_issues} critical import issues preventing tests from loading")
        if pattern_counts.get('incorrect_path', 0) > 10:
            recommendations.append("Many incorrect import paths found - review import conventions")
        if pattern_counts.get('missing_module', 0) > 5:
            recommendations.append("Several missing modules - ensure all dependencies are installed")
        if files_with_issues > total_files * 0.3:
            recommendations.append("Over 30% of files have issues - consider running comprehensive fix")
            
        return E2EImportReport(
            timestamp=datetime.now().isoformat(),
            total_files=total_files,
            files_with_issues=files_with_issues,
            files_fixed=files_fixed,
            critical_issues=critical_issues,
            warnings=warnings,
            file_results=self.file_results,
            common_patterns=pattern_counts,
            recommendations=recommendations
        )
        
    def validate_all_tests_load(self) -> Tuple[bool, List[str]]:
        """Validate that all E2E tests can be loaded."""
        print("\nValidating all E2E tests can be loaded...")
        
        failed_files = []
        test_files = self.discover_all_e2e_tests()
        
        for file_path in test_files:
            error = self._try_import_file(file_path)
            if error:
                failed_files.append(f"{file_path.name}: {error}")
                
        success = len(failed_files) == 0
        
        if success:
            print(f"[U+2713] All {len(test_files)} E2E tests can be loaded successfully!")
        else:
            print(f"[U+2717] {len(failed_files)} out of {len(test_files)} tests failed to load")
            
        return success, failed_files
        
    def print_report(self, report: E2EImportReport):
        """Print human-readable report."""
        print("\n" + "=" * 80)
        print("E2E IMPORT ANALYSIS REPORT")
        print("=" * 80)
        print(f"Timestamp: {report.timestamp}")
        print(f"Total files analyzed: {report.total_files}")
        print(f"Files with issues: {report.files_with_issues}")
        print(f"Files fixed: {report.files_fixed}")
        print(f"Critical issues: {report.critical_issues}")
        print(f"Warnings: {report.warnings}")
        
        if report.common_patterns:
            print("\nCommon Issue Patterns:")
            for pattern, count in sorted(report.common_patterns.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {pattern}: {count} occurrences")
                
        if report.recommendations:
            print("\nRecommendations:")
            for rec in report.recommendations:
                print(f"  [U+2022] {rec}")
                
        # Show files that still can't import
        cant_import = [r for r in report.file_results if not r.can_import]
        if cant_import:
            print(f"\nFiles that cannot be imported ({len(cant_import)}):")
            for result in cant_import[:10]:  # Show first 10
                file_name = Path(result.file_path).name
                print(f"  - {file_name}")
                if result.syntax_errors:
                    print(f"    Syntax errors: {result.syntax_errors[0]}")
                elif result.import_errors:
                    print(f"    Import errors: {result.import_errors[0]}")
                    
            if len(cant_import) > 10:
                print(f"  ... and {len(cant_import) - 10} more")
                
    def save_report(self, report: E2EImportReport, output_path: Optional[Path] = None) -> Path:
        """Save report to JSON file."""
        if output_path is None:
            reports_dir = self.project_root / "test_reports"
            reports_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = reports_dir / f"e2e_import_report_{timestamp}.json"
            
        # Convert to dict for JSON
        report_dict = asdict(report)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
            
        return output_path


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive E2E Import Fixer")
    parser.add_argument('--dry-run', action='store_true', help='Show what would be fixed without making changes')
    parser.add_argument('--verbose', action='store_true', help='Show detailed progress')
    parser.add_argument('--validate', action='store_true', help='Validate all tests can load after fixing')
    parser.add_argument('--output', type=Path, help='Save report to this file')
    
    args = parser.parse_args()
    
    print("E2E Import Fixer - Comprehensive Analysis and Fixing")
    print(f"Project root: {PROJECT_ROOT}")
    if args.dry_run:
        print("Mode: DRY RUN (no changes will be made)")
    print()
    
    fixer = E2EImportFixer(dry_run=args.dry_run, verbose=args.verbose)
    
    # Run comprehensive fix
    report = fixer.run_comprehensive_fix()
    
    # Print report
    fixer.print_report(report)
    
    # Save report if requested
    if args.output:
        report_path = fixer.save_report(report, args.output)
        print(f"\nReport saved to: {report_path}")
    else:
        report_path = fixer.save_report(report)
        print(f"\nReport saved to: {report_path}")
        
    # Validate if requested
    if args.validate:
        success, failed = fixer.validate_all_tests_load()
        if not success:
            print("\nFailed to load files:")
            for failure in failed[:20]:  # Show first 20
                print(f"  - {failure}")
            if len(failed) > 20:
                print(f"  ... and {len(failed) - 20} more")
            return 1
            
    return 0 if report.files_with_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())