#!/usr/bin/env python3
"""
Comprehensive import checker for netra_backend structure.
Verifies all imports follow the correct pattern for the new project structure.
"""

import ast
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple


@dataclass
class ImportIssue:
    """Represents an import issue found in a file."""
    file_path: str
    line_number: int
    import_statement: str
    issue_type: str
    expected_pattern: str
    
@dataclass
class FileAnalysis:
    """Analysis results for a single file."""
    file_path: str
    total_imports: int
    correct_imports: List[str]
    incorrect_imports: List[ImportIssue]
    warnings: List[str]

class ImportAnalyzer:
    """Analyzes Python imports for correct netra_backend structure."""
    
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.netra_backend_path = root_path / "netra_backend"
        self.app_path = self.netra_backend_path / "app"
        self.tests_path = self.netra_backend_path / "tests"
        self.issues: List[ImportIssue] = []
        self.file_analyses: Dict[str, FileAnalysis] = {}
        
        # Define valid import patterns
        self.valid_patterns = {
            'absolute': [
                'netra_backend.app.',
                'netra_backend.tests.',
            ],
            'relative': ['.', '..'],
            'external': [],  # Will be populated with standard library and third-party packages
        }
        
        # Legacy patterns that should be replaced
        self.legacy_patterns = [
            'app.',  # Old pattern without netra_backend prefix
            'tests.',  # Old pattern without netra_backend prefix
            'from app import',
            'from tests import',
        ]
        
    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a single Python file for import issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content, filename=str(file_path))
            
            correct_imports = []
            incorrect_imports = []
            warnings = []
            total_imports = 0
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        total_imports += 1
                        import_str = f"import {alias.name}"
                        if self._check_import(alias.name, file_path, node.lineno):
                            correct_imports.append(import_str)
                        else:
                            issue = self._create_issue(
                                file_path, node.lineno, import_str, alias.name
                            )
                            if issue:
                                incorrect_imports.append(issue)
                                
                elif isinstance(node, ast.ImportFrom):
                    if node.module is not None:
                        total_imports += 1
                        import_str = f"from {node.module} import ..."
                        if self._check_import(node.module, file_path, node.lineno, is_from=True, level=node.level):
                            correct_imports.append(import_str)
                        else:
                            issue = self._create_issue(
                                file_path, node.lineno, import_str, node.module, level=node.level
                            )
                            if issue:
                                incorrect_imports.append(issue)
                    elif node.level > 0:
                        # Relative import
                        total_imports += 1
                        import_str = f"from {'.' * node.level} import ..."
                        correct_imports.append(import_str)
                        
            # Check for potential issues
            rel_path = file_path.relative_to(self.root_path)
            if str(rel_path).startswith('netra_backend'):
                if 'netra_backend/app' in str(rel_path):
                    for imp in incorrect_imports:
                        if 'tests' in imp.import_statement:
                            warnings.append(f"App file importing from tests: {imp.import_statement}")
                            
            analysis = FileAnalysis(
                file_path=str(file_path),
                total_imports=total_imports,
                correct_imports=correct_imports,
                incorrect_imports=incorrect_imports,
                warnings=warnings
            )
            
            self.file_analyses[str(file_path)] = analysis
            return analysis
            
        except Exception as e:
            return FileAnalysis(
                file_path=str(file_path),
                total_imports=0,
                correct_imports=[],
                incorrect_imports=[],
                warnings=[f"Error parsing file: {e}"]
            )
            
    def _check_import(self, module_name: str, file_path: Path, line_no: int, 
                     is_from: bool = False, level: int = 0) -> bool:
        """Check if an import follows the correct pattern."""
        if level > 0:
            # Relative imports are generally acceptable
            return True
            
        # Check for legacy patterns
        for legacy in self.legacy_patterns:
            if module_name.startswith(legacy.replace('from ', '').replace(' import', '')):
                return False
                
        # Check if it's a netra_backend import
        if module_name.startswith('netra_backend.'):
            # Verify it's using the correct structure
            if module_name.startswith('netra_backend.app.') or \
               module_name.startswith('netra_backend.tests.'):
                return True
            return False
            
        # Check if it's an old app/tests import without netra_backend prefix
        if module_name.startswith('app.') or module_name.startswith('tests.'):
            return False
            
        # External imports (standard library or third-party) are fine
        return True
        
    def _create_issue(self, file_path: Path, line_no: int, import_str: str, 
                     module_name: str, level: int = 0) -> ImportIssue:
        """Create an ImportIssue for an incorrect import."""
        issue_type = "Unknown"
        expected = ""
        
        if module_name.startswith('app.'):
            issue_type = "Legacy app import"
            expected = module_name.replace('app.', 'netra_backend.app.')
        elif module_name.startswith('tests.'):
            issue_type = "Legacy tests import"
            expected = module_name.replace('tests.', 'netra_backend.tests.')
        elif module_name == 'app':
            issue_type = "Legacy app module import"
            expected = "netra_backend.app"
        elif module_name == 'tests':
            issue_type = "Legacy tests module import"
            expected = "netra_backend.tests"
            
        if expected:
            return ImportIssue(
                file_path=str(file_path),
                line_number=line_no,
                import_statement=import_str,
                issue_type=issue_type,
                expected_pattern=expected
            )
        return None
        
    def analyze_directory(self, directory: Path) -> Dict[str, FileAnalysis]:
        """Analyze all Python files in a directory."""
        analyses = {}
        
        for root, dirs, files in os.walk(directory):
            # Skip __pycache__ and other hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    analysis = self.analyze_file(file_path)
                    analyses[str(file_path)] = analysis
                    
        return analyses
        
    def generate_report(self) -> str:
        """Generate a comprehensive report of all import issues."""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("NETRA BACKEND IMPORT ANALYSIS REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # Collect statistics
        total_files = len(self.file_analyses)
        files_with_issues = sum(1 for a in self.file_analyses.values() if a.incorrect_imports)
        total_imports = sum(a.total_imports for a in self.file_analyses.values())
        total_issues = sum(len(a.incorrect_imports) for a in self.file_analyses.values())
        
        # Summary statistics
        report_lines.append("SUMMARY STATISTICS")
        report_lines.append("-" * 40)
        report_lines.append(f"Total files analyzed: {total_files}")
        report_lines.append(f"Files with import issues: {files_with_issues}")
        report_lines.append(f"Total imports analyzed: {total_imports}")
        report_lines.append(f"Total import issues found: {total_issues}")
        report_lines.append(f"Success rate: {((total_imports - total_issues) / total_imports * 100):.1f}%")
        report_lines.append("")
        
        # Group issues by type
        issues_by_type = defaultdict(list)
        for analysis in self.file_analyses.values():
            for issue in analysis.incorrect_imports:
                issues_by_type[issue.issue_type].append(issue)
                
        # Report issues by type
        if issues_by_type:
            report_lines.append("ISSUES BY TYPE")
            report_lines.append("-" * 40)
            for issue_type, issues in sorted(issues_by_type.items()):
                report_lines.append(f"\n{issue_type}: {len(issues)} occurrences")
                report_lines.append("-" * 30)
                
                # Group by file for better readability
                by_file = defaultdict(list)
                for issue in issues:
                    by_file[issue.file_path].append(issue)
                    
                for file_path, file_issues in sorted(by_file.items()):
                    rel_path = Path(file_path).relative_to(self.root_path)
                    report_lines.append(f"\n  {rel_path}:")
                    for issue in file_issues:
                        report_lines.append(f"    Line {issue.line_number}: {issue.import_statement}")
                        report_lines.append(f"      -> Should be: {issue.expected_pattern}")
                        
        # Files with warnings
        files_with_warnings = [
            (path, analysis) for path, analysis in self.file_analyses.items() 
            if analysis.warnings
        ]
        
        if files_with_warnings:
            report_lines.append("\n" + "=" * 40)
            report_lines.append("WARNINGS")
            report_lines.append("-" * 40)
            for path, analysis in files_with_warnings:
                rel_path = Path(path).relative_to(self.root_path)
                report_lines.append(f"\n{rel_path}:")
                for warning in analysis.warnings:
                    report_lines.append(f"  WARNING: {warning}")
                    
        # Success message if no issues
        if total_issues == 0:
            report_lines.append("\n[SUCCESS] All imports follow the correct netra_backend structure!")
        else:
            report_lines.append("\n" + "=" * 40)
            report_lines.append("RECOMMENDED ACTIONS")
            report_lines.append("-" * 40)
            report_lines.append("1. Update all legacy 'app.' imports to 'netra_backend.app.'")
            report_lines.append("2. Update all legacy 'tests.' imports to 'netra_backend.tests.'")
            report_lines.append("3. Ensure app files don't import from tests")
            report_lines.append("4. Consider using relative imports within the same package")
            
        return "\n".join(report_lines)
        
    def export_issues_json(self, output_path: Path):
        """Export issues to JSON for further processing."""
        issues_data = []
        for analysis in self.file_analyses.values():
            if analysis.incorrect_imports:
                for issue in analysis.incorrect_imports:
                    issues_data.append({
                        'file': str(Path(issue.file_path).relative_to(self.root_path)),
                        'line': issue.line_number,
                        'current': issue.import_statement,
                        'expected': issue.expected_pattern,
                        'type': issue.issue_type
                    })
                    
        with open(output_path, 'w') as f:
            json.dump(issues_data, f, indent=2)
            
        return len(issues_data)


def main():
    """Main entry point."""
    # Get the project root
    root_path = Path.cwd()
    
    # Verify we're in the right directory
    if not (root_path / "netra_backend").exists():
        print("Error: netra_backend directory not found. Please run from project root.")
        sys.exit(1)
        
    print("Starting netra_backend import analysis...")
    print(f"Project root: {root_path}")
    print()
    
    analyzer = ImportAnalyzer(root_path)
    
    # Analyze app directory
    print("Analyzing netra_backend/app...")
    app_analyses = analyzer.analyze_directory(analyzer.app_path)
    print(f"  Analyzed {len(app_analyses)} files")
    
    # Analyze tests directory
    print("Analyzing netra_backend/tests...")
    tests_analyses = analyzer.analyze_directory(analyzer.tests_path)
    print(f"  Analyzed {len(tests_analyses)} files")
    
    print()
    
    # Generate and print report
    report = analyzer.generate_report()
    print(report)
    
    # Export issues to JSON
    json_path = root_path / "import_issues.json"
    num_issues = analyzer.export_issues_json(json_path)
    
    if num_issues > 0:
        print(f"\n[JSON] Import issues exported to: {json_path}")
        print(f"   Run 'python scripts/fix_netra_backend_imports.py' to automatically fix these issues")
        
    return 0 if num_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())