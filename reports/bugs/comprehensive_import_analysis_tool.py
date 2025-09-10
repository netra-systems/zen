#!/usr/bin/env python3
"""
Comprehensive Import Error Analysis Tool
Identifies ALL import issues preventing unit tests from running

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Fix all import errors to enable test suite execution
- Value Impact: Unlocks unit test execution, enabling quality assurance
- Strategic Impact: Critical for ensuring code quality and preventing regressions
"""

import ast
import os
import sys
import traceback
import importlib
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class ImportIssue:
    file_path: str
    line_number: int
    import_statement: str
    error_type: str
    error_message: str
    fix_suggestion: str

class ImportAnalyzer:
    """Comprehensive import analyzer for test files."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues: List[ImportIssue] = []
        self.known_fixes = {
            'AuthenticationResult': 'AuthResult',  # Known rename
            'AuthenticationError': 'AuthServiceError',  # Known rename
            'ConfigurationError': 'netra_backend.app.core.managers.unified_configuration_manager.ConfigurationError',
        }
        
    def analyze_test_directory(self, test_dir: str) -> List[ImportIssue]:
        """Analyze all test files in directory for import issues."""
        test_path = self.project_root / test_dir
        
        for test_file in test_path.glob("test_*.py"):
            print(f"Analyzing {test_file}...")
            self._analyze_file(test_file)
            
        return self.issues
    
    def _analyze_file(self, file_path: Path):
        """Analyze individual file for import issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse AST to find import statements
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    self._validate_import(file_path, node, content)
                    
        except SyntaxError as e:
            self.issues.append(ImportIssue(
                file_path=str(file_path),
                line_number=e.lineno or 0,
                import_statement="SYNTAX_ERROR",
                error_type="SyntaxError",
                error_message=str(e),
                fix_suggestion="Fix syntax error before analyzing imports"
            ))
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    def _validate_import(self, file_path: Path, node: ast.AST, content: str):
        """Validate a specific import statement."""
        try:
            line_number = node.lineno
            lines = content.split('\n')
            import_line = lines[line_number - 1] if line_number <= len(lines) else "UNKNOWN"
            
            if isinstance(node, ast.ImportFrom):
                module_name = node.module
                if module_name:
                    self._validate_from_import(file_path, node, import_line, line_number)
            elif isinstance(node, ast.Import):
                self._validate_direct_import(file_path, node, import_line, line_number)
                
        except Exception as e:
            # Record validation error
            self.issues.append(ImportIssue(
                file_path=str(file_path),
                line_number=getattr(node, 'lineno', 0),
                import_statement=str(node),
                error_type="ValidationError",
                error_message=str(e),
                fix_suggestion="Check import syntax and module availability"
            ))
    
    def _validate_from_import(self, file_path: Path, node: ast.ImportFrom, import_line: str, line_number: int):
        """Validate 'from X import Y' statements."""
        module_name = node.module
        if not module_name:
            return
            
        try:
            # Try to import the module
            module = importlib.import_module(module_name)
            
            # Check each imported name
            for alias in node.names:
                name = alias.name
                if name == '*':
                    continue  # Skip wildcard imports
                    
                if not hasattr(module, name):
                    # Check if it's a known rename
                    fix_suggestion = self.known_fixes.get(name)
                    if not fix_suggestion:
                        fix_suggestion = f"'{name}' not found in {module_name}. Check module contents or spelling."
                    else:
                        fix_suggestion = f"Rename '{name}' to '{fix_suggestion}'"
                    
                    self.issues.append(ImportIssue(
                        file_path=str(file_path),
                        line_number=line_number,
                        import_statement=import_line,
                        error_type="AttributeError",
                        error_message=f"module '{module_name}' has no attribute '{name}'",
                        fix_suggestion=fix_suggestion
                    ))
                    
        except ModuleNotFoundError as e:
            self.issues.append(ImportIssue(
                file_path=str(file_path),
                line_number=line_number,
                import_statement=import_line,
                error_type="ModuleNotFoundError",
                error_message=str(e),
                fix_suggestion=f"Module '{module_name}' not found. Check module path or installation."
            ))
        except Exception as e:
            self.issues.append(ImportIssue(
                file_path=str(file_path),
                line_number=line_number,
                import_statement=import_line,
                error_type=type(e).__name__,
                error_message=str(e),
                fix_suggestion="Generic import error - check module availability"
            ))
    
    def _validate_direct_import(self, file_path: Path, node: ast.Import, import_line: str, line_number: int):
        """Validate 'import X' statements."""
        for alias in node.names:
            module_name = alias.name
            try:
                importlib.import_module(module_name)
            except ModuleNotFoundError as e:
                self.issues.append(ImportIssue(
                    file_path=str(file_path),
                    line_number=line_number,
                    import_statement=import_line,
                    error_type="ModuleNotFoundError",
                    error_message=str(e),
                    fix_suggestion=f"Module '{module_name}' not found. Check module path or installation."
                ))
    
    def generate_report(self) -> str:
        """Generate comprehensive report of all import issues."""
        if not self.issues:
            return "✅ No import issues found!"
        
        # Group issues by type and file
        issues_by_type = defaultdict(list)
        issues_by_file = defaultdict(list)
        
        for issue in self.issues:
            issues_by_type[issue.error_type].append(issue)
            issues_by_file[issue.file_path].append(issue)
        
        report = []
        report.append("# Comprehensive Import Analysis Report")
        report.append(f"Total Issues Found: {len(self.issues)}")
        report.append("")
        
        # Summary by error type
        report.append("## Issues by Type")
        for error_type, issues in issues_by_type.items():
            report.append(f"- **{error_type}**: {len(issues)} issues")
        report.append("")
        
        # Detailed issues by file
        report.append("## Detailed Issues by File")
        for file_path, file_issues in issues_by_file.items():
            report.append(f"### {file_path}")
            report.append(f"Issues: {len(file_issues)}")
            report.append("")
            
            for issue in file_issues:
                report.append(f"**Line {issue.line_number}**: {issue.error_type}")
                report.append(f"```")
                report.append(f"{issue.import_statement}")
                report.append(f"```")
                report.append(f"Error: {issue.error_message}")
                report.append(f"Fix: {issue.fix_suggestion}")
                report.append("")
        
        # Priority fixes section
        report.append("## Priority Fixes (Most Impact)")
        priority_fixes = []
        
        # Find issues that block multiple files
        module_impact = defaultdict(set)
        for issue in self.issues:
            if "module" in issue.error_message:
                module_name = issue.error_message.split("'")[1] if "'" in issue.error_message else "unknown"
                module_impact[module_name].add(issue.file_path)
        
        for module, files in module_impact.items():
            if len(files) > 1:
                priority_fixes.append(f"- **{module}**: Affects {len(files)} files")
        
        if priority_fixes:
            report.extend(priority_fixes)
        else:
            report.append("- All issues are file-specific")
        
        report.append("")
        
        # Fix implementation plan
        report.append("## Implementation Plan")
        report.append("1. Fix high-impact module issues first")
        report.append("2. Address attribute errors (likely renames)")
        report.append("3. Fix syntax errors")
        report.append("4. Validate all fixes with test runner")
        
        return "\n".join(report)

def main():
    """Main analysis function."""
    project_root = os.getcwd()
    print(f"Analyzing project: {project_root}")
    
    analyzer = ImportAnalyzer(project_root)
    
    # Analyze test directories
    test_dirs = [
        "netra_backend/tests/unit",
        "tests/e2e",
        "test_framework"
    ]
    
    for test_dir in test_dirs:
        test_path = Path(project_root) / test_dir
        if test_path.exists():
            print(f"\nAnalyzing {test_dir}...")
            analyzer.analyze_test_directory(test_dir)
        else:
            print(f"Directory not found: {test_dir}")
    
    # Generate and save report
    report = analyzer.generate_report()
    
    report_file = Path(project_root) / "reports" / "bugs" / "comprehensive_import_analysis_20250909.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n✅ Analysis complete. Report saved to: {report_file}")
    print(f"Found {len(analyzer.issues)} import issues across all test files.")
    
    # Print summary to console
    if analyzer.issues:
        print("\n⚠️  CRITICAL ISSUES FOUND:")
        error_types = defaultdict(int)
        for issue in analyzer.issues:
            error_types[issue.error_type] += 1
        
        for error_type, count in error_types.items():
            print(f"  - {error_type}: {count} issues")
    
    return len(analyzer.issues)

if __name__ == "__main__":
    sys.exit(main())