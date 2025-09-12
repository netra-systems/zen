#!/usr/bin/env python3
"""
E2E Test Fixer - Process B
Scans and fixes all e2e test issues
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Set, Tuple
import ast
import json
from datetime import datetime

class E2ETestFixer:
    """Fixes common e2e test issues."""
    
    def __init__(self):
        self.test_dir = Path("tests/e2e")
        self.issues_found = []
        self.fixes_applied = []
        
    def scan_test_file(self, file_path: Path) -> Dict[str, List[str]]:
        """Scan a test file for issues."""
        issues = {
            "no_test_functions": [],
            "missing_markers": [],
            "class_without_test_prefix": [],
            "function_without_test_prefix": [],
            "missing_imports": [],
            "mock_usage_in_e2e": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse AST
            tree = ast.parse(content)
            
            # Check for test functions/methods
            has_test_functions = False
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith('test_'):
                        has_test_functions = True
                    elif not node.name.startswith('_') and 'test' in node.name.lower():
                        issues["function_without_test_prefix"].append(node.name)
                        
                elif isinstance(node, ast.ClassDef):
                    if 'Test' in node.name and not node.name.startswith('Test'):
                        issues["class_without_test_prefix"].append(node.name)
                        
            if not has_test_functions:
                issues["no_test_functions"].append(str(file_path))
                
            # Check for pytest markers
            if 'pytest.mark' not in content:
                issues["missing_markers"].append(str(file_path))
                
            # Check for mock usage in e2e tests
            if any(mock in content for mock in ['Mock(', 'MagicMock(', 'AsyncMock(', '@patch']):
                issues["mock_usage_in_e2e"].append(str(file_path))
                
            # Check for required imports
            if 'import pytest' not in content:
                issues["missing_imports"].append("pytest")
                
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
            
        return issues
    
    def fix_test_class_name(self, file_path: Path) -> bool:
        """Fix test class naming issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Fix class names
            pattern = r'class\s+(\w*[Tt]est\w*)\s*(\([^)]*\))?:'
            
            def fix_class_name(match):
                class_name = match.group(1)
                inheritance = match.group(2) or ''
                
                # Ensure class starts with Test
                if not class_name.startswith('Test'):
                    if 'Test' in class_name:
                        # Move Test to the beginning
                        class_name = 'Test' + class_name.replace('Test', '')
                    else:
                        class_name = 'Test' + class_name
                        
                return f'class {class_name}{inheritance}:'
            
            new_content = re.sub(pattern, fix_class_name, content)
            
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True
                
        except Exception as e:
            print(f"Error fixing class names in {file_path}: {e}")
            
        return False
    
    def add_test_markers(self, file_path: Path) -> bool:
        """Add appropriate pytest markers to test file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Determine appropriate markers based on file path
            markers = []
            path_str = str(file_path).lower()
            
            if 'performance' in path_str:
                markers.append('@pytest.mark.performance')
            if 'resilience' in path_str or 'recovery' in path_str:
                markers.append('@pytest.mark.resilience')
            if 'websocket' in path_str:
                markers.append('@pytest.mark.websocket')
            if 'auth' in path_str:
                markers.append('@pytest.mark.auth')
            if 'startup' in path_str:
                markers.append('@pytest.mark.startup')
                
            # Default e2e marker
            if '@pytest.mark.e2e' not in ''.join(lines):
                markers.append('@pytest.mark.e2e')
                
            if not markers:
                return False
                
            # Add markers to test functions
            modified = False
            new_lines = []
            for i, line in enumerate(lines):
                new_lines.append(line)
                
                # Add markers before test functions
                if line.strip().startswith('def test_') or line.strip().startswith('async def test_'):
                    # Check if markers already exist
                    if i > 0 and '@pytest.mark' not in lines[i-1]:
                        indent = len(line) - len(line.lstrip())
                        for marker in markers:
                            new_lines.insert(-1, ' ' * indent + marker + '\n')
                        modified = True
                        
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                return True
                
        except Exception as e:
            print(f"Error adding markers to {file_path}: {e}")
            
        return False
    
    def remove_mocks_from_e2e(self, file_path: Path) -> bool:
        """Remove mock usage from e2e tests."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            
            # Remove mock imports
            content = re.sub(r'from unittest\.mock import.*\n', '', content)
            content = re.sub(r'from mock import.*\n', '', content)
            
            # Comment out @patch decorators
            content = re.sub(r'^(\s*)@patch\([^)]+\)', r'\1# @patch(...) - Removed: No mocks in e2e tests', content, flags=re.MULTILINE)
            
            # Replace Mock/MagicMock with actual implementations or skip
            content = re.sub(r'Mock\(\)', 'None  # TODO: Use real service instead of Mock', content)
            content = re.sub(r'MagicMock\(\)', 'None  # TODO: Use real service instead of MagicMock', content)
            content = re.sub(r'AsyncMock\(\)', 'None  # TODO: Use real service instead of AsyncMock', content)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
                
        except Exception as e:
            print(f"Error removing mocks from {file_path}: {e}")
            
        return False
    
    def scan_all_tests(self) -> Dict[str, Dict]:
        """Scan all e2e test files for issues."""
        all_issues = {}
        
        for test_file in self.test_dir.rglob("test_*.py"):
            issues = self.scan_test_file(test_file)
            
            # Only include files with issues
            if any(issue_list for issue_list in issues.values()):
                all_issues[str(test_file)] = issues
                
        return all_issues
    
    def fix_all_issues(self) -> Dict[str, List[str]]:
        """Fix all identified issues."""
        fixes = {
            "class_names_fixed": [],
            "markers_added": [],
            "mocks_removed": []
        }
        
        for test_file in self.test_dir.rglob("test_*.py"):
            # Fix class names
            if self.fix_test_class_name(test_file):
                fixes["class_names_fixed"].append(str(test_file))
                
            # Add markers
            if self.add_test_markers(test_file):
                fixes["markers_added"].append(str(test_file))
                
            # Remove mocks
            if self.remove_mocks_from_e2e(test_file):
                fixes["mocks_removed"].append(str(test_file))
                
        return fixes
    
    def generate_report(self, issues: Dict, fixes: Dict) -> str:
        """Generate a report of issues and fixes."""
        report = []
        report.append(f"# E2E Test Scan Report")
        report.append(f"Generated: {datetime.now().isoformat()}\n")
        
        # Summary
        total_files = len(issues)
        total_issues = sum(len(issue_list) for file_issues in issues.values() for issue_list in file_issues.values())
        total_fixes = sum(len(fix_list) for fix_list in fixes.values())
        
        report.append("## Summary")
        report.append(f"- Files with issues: {total_files}")
        report.append(f"- Total issues found: {total_issues}")
        report.append(f"- Total fixes applied: {total_fixes}\n")
        
        # Issues by type
        report.append("## Issues Found")
        issue_counts = {}
        for file_issues in issues.values():
            for issue_type, issue_list in file_issues.items():
                if issue_list:
                    issue_counts[issue_type] = issue_counts.get(issue_type, 0) + len(issue_list)
                    
        for issue_type, count in sorted(issue_counts.items()):
            report.append(f"- {issue_type}: {count}")
        report.append("")
        
        # Fixes applied
        report.append("## Fixes Applied")
        for fix_type, files in fixes.items():
            if files:
                report.append(f"### {fix_type.replace('_', ' ').title()}")
                for file in files[:5]:  # Show first 5
                    report.append(f"- {file}")
                if len(files) > 5:
                    report.append(f"- ... and {len(files) - 5} more")
                report.append("")
                
        # Remaining issues
        report.append("## Remaining Issues")
        remaining = 0
        for file_path, file_issues in issues.items():
            has_remaining = False
            for issue_type, issue_list in file_issues.items():
                if issue_list and issue_type == "no_test_functions":
                    has_remaining = True
                    remaining += 1
                    
        report.append(f"- Files without test functions: {remaining}")
        
        return "\n".join(report)


def main():
    """Main entry point."""
    print("E2E Test Fixer - Scanning and fixing test issues...")
    
    fixer = E2ETestFixer()
    
    # Scan for issues
    print("\nScanning all e2e tests for issues...")
    issues = fixer.scan_all_tests()
    print(f"Found issues in {len(issues)} files")
    
    # Apply fixes
    print("\nApplying automated fixes...")
    fixes = fixer.fix_all_issues()
    print(f"Applied {sum(len(f) for f in fixes.values())} fixes")
    
    # Generate report
    report = fixer.generate_report(issues, fixes)
    
    # Save report
    report_path = Path("e2e_test_scan_report.md")
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")
    
    # Run tests to verify fixes
    print("\nRunning sample e2e tests to verify fixes...")
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/e2e/test_startup_comprehensive_e2e.py", "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("[U+2713] Sample tests passing after fixes!")
    else:
        print("[U+2717] Some tests still failing - manual intervention needed")
    
    return 0


if __name__ == "__main__":
    main()