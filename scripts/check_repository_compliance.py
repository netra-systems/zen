#!/usr/bin/env python3
"""
Repository Compliance Checker - Pre-commit Hook

This script enforces SSOT repository access patterns by scanning for violations
and preventing commits that bypass the TestRepositoryFactory.

Usage:
    python scripts/check_repository_compliance.py [--fix] [--verbose]

Returns:
    0: No violations found
    1: Violations found (blocks commit)
    2: Script error

Business Value: Platform/Internal - Code Quality & SSOT Enforcement
Prevents repository pattern violations from entering the codebase.
"""

import argparse
import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Set, Any, Tuple
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


@dataclass
class Violation:
    """Repository compliance violation."""
    file_path: str
    line_number: int
    violation_type: str
    message: str
    severity: str = "error"  # error, warning, info
    
    def __str__(self) -> str:
        return f"{self.file_path}:{self.line_number}: {self.severity.upper()}: {self.message}"


class RepositoryComplianceChecker:
    """
    Checks Python code for repository pattern compliance violations.
    
    Detects:
    - Direct SQLAlchemy session creation in tests
    - Direct repository instantiation without factory
    - Missing TestRepositoryFactory usage in test files
    - Session management violations
    """
    
    # Patterns that indicate direct SQLAlchemy usage
    DIRECT_SQLALCHEMY_PATTERNS = [
        r'create_async_engine\s*\(',
        r'async_sessionmaker\s*\(',
        r'AsyncSession\s*\(',
        r'sessionmaker\s*\(',
        r'Session\s*\(',
        r'\.execute\s*\(\s*text\s*\(',  # Direct query execution
        r'\.scalar\s*\(',
        r'\.fetch',
    ]
    
    # Repository classes that should use factory
    REPOSITORY_CLASSES = {
        'UserRepository',
        'SecretRepository', 
        'ToolUsageRepository',
        'AuthUserRepository',
        'AuthSessionRepository',
        'AuthAuditRepository',
        'BaseRepository'
    }
    
    # Imports that suggest direct SQLAlchemy usage in tests
    BANNED_TEST_IMPORTS = {
        'sqlalchemy.ext.asyncio.create_async_engine',
        'sqlalchemy.ext.asyncio.AsyncSession',
        'sqlalchemy.ext.asyncio.async_sessionmaker',
        'sqlalchemy.orm.sessionmaker',
        'sqlalchemy.orm.Session',
    }
    
    def __init__(self, project_root: Path):
        """Initialize compliance checker."""
        self.project_root = project_root
        self.violations: List[Violation] = []
        
    def check_file(self, file_path: Path) -> List[Violation]:
        """
        Check a single Python file for compliance violations.
        
        Args:
            file_path: Path to Python file to check
            
        Returns:
            List of violations found
        """
        violations = []
        
        if not file_path.suffix == '.py':
            return violations
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse AST for detailed analysis
            try:
                tree = ast.parse(content)
                violations.extend(self._check_ast(file_path, tree, content))
            except SyntaxError as e:
                violations.append(Violation(
                    file_path=str(file_path),
                    line_number=e.lineno or 1,
                    violation_type="syntax_error",
                    message=f"Syntax error prevents compliance checking: {e}",
                    severity="warning"
                ))
                
            # Text-based pattern matching as backup
            violations.extend(self._check_patterns(file_path, content))
            
        except Exception as e:
            violations.append(Violation(
                file_path=str(file_path),
                line_number=1,
                violation_type="check_error",
                message=f"Error checking file: {e}",
                severity="warning"
            ))
        
        return violations
    
    def _check_ast(self, file_path: Path, tree: ast.AST, content: str) -> List[Violation]:
        """Check AST for compliance violations."""
        violations = []
        is_test_file = self._is_test_file(file_path)
        
        class ComplianceVisitor(ast.NodeVisitor):
            def __init__(self, checker, violations_list):
                self.checker = checker
                self.violations = violations_list
                self.imports = set()
                self.has_factory_import = False
                self.direct_repo_instantiation = []
                
            def visit_Import(self, node):
                for alias in node.names:
                    self.imports.add(alias.name)
                    if 'test_repository_factory' in alias.name:
                        self.has_factory_import = True
                self.generic_visit(node)
            
            def visit_ImportFrom(self, node):
                if node.module:
                    for alias in node.names:
                        full_name = f"{node.module}.{alias.name}"
                        self.imports.add(full_name)
                        
                        if 'test_repository_factory' in node.module:
                            self.has_factory_import = True
                        
                        # Check for banned imports in test files
                        if is_test_file and full_name in self.checker.BANNED_TEST_IMPORTS:
                            self.violations.append(Violation(
                                file_path=str(file_path),
                                line_number=node.lineno,
                                violation_type="banned_import",
                                message=f"Direct SQLAlchemy import '{full_name}' in test file. Use TestRepositoryFactory instead.",
                                severity="error"
                            ))
                
                self.generic_visit(node)
            
            def visit_Call(self, node):
                # Check for direct repository instantiation
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.checker.REPOSITORY_CLASSES:
                        if is_test_file and not self._is_factory_call(node):
                            self.violations.append(Violation(
                                file_path=str(file_path),
                                line_number=node.lineno,
                                violation_type="direct_repo_instantiation",
                                message=f"Direct {node.func.id} instantiation in test. Use TestRepositoryFactory.create_{node.func.id.lower()} instead.",
                                severity="error"
                            ))
                
                # Check for direct SQLAlchemy calls
                if isinstance(node.func, ast.Name):
                    banned_calls = {'create_async_engine', 'async_sessionmaker', 'AsyncSession', 'sessionmaker'}
                    if node.func.id in banned_calls and is_test_file:
                        self.violations.append(Violation(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            violation_type="direct_sqlalchemy_call",
                            message=f"Direct SQLAlchemy call '{node.func.id}' in test. Use TestRepositoryFactory.get_test_session() instead.",
                            severity="error"
                        ))
                
                self.generic_visit(node)
            
            def _is_factory_call(self, node):
                """Check if this is a call through the factory."""
                # Look for factory.create_* pattern in surrounding context
                return False  # Simplified for now
        
        visitor = ComplianceVisitor(self, violations)
        visitor.visit(tree)
        
        # Check if test file is missing factory import
        if is_test_file and not visitor.has_factory_import:
            # Look for repository usage
            content_lower = content.lower()
            if any(repo.lower() in content_lower for repo in self.REPOSITORY_CLASSES):
                violations.append(Violation(
                    file_path=str(file_path),
                    line_number=1,
                    violation_type="missing_factory_import",
                    message="Test file uses repositories but doesn't import TestRepositoryFactory",
                    severity="warning"
                ))
        
        return violations
    
    def _check_patterns(self, file_path: Path, content: str) -> List[Violation]:
        """Check file content using regex patterns."""
        violations = []
        is_test_file = self._is_test_file(file_path)
        
        if not is_test_file:
            return violations
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Skip comments and docstrings
            if line_stripped.startswith('#') or '"""' in line or "'''" in line:
                continue
            
            # Check for direct SQLAlchemy patterns
            for pattern in self.DIRECT_SQLALCHEMY_PATTERNS:
                if re.search(pattern, line):
                    violations.append(Violation(
                        file_path=str(file_path),
                        line_number=line_num,
                        violation_type="direct_sqlalchemy_usage",
                        message=f"Direct SQLAlchemy usage detected: {line_stripped[:50]}...",
                        severity="error"
                    ))
            
            # Check for session variable assignments without factory
            session_patterns = [
                r'session\s*=\s*AsyncSession\s*\(',
                r'session\s*=\s*sessionmaker\s*\(',
                r'session\s*=.*\.execute\s*\(',
            ]
            
            for pattern in session_patterns:
                if re.search(pattern, line) and 'factory' not in line.lower():
                    violations.append(Violation(
                        file_path=str(file_path),
                        line_number=line_num,
                        violation_type="unmanaged_session",
                        message=f"Unmanaged session usage: {line_stripped[:50]}...",
                        severity="error"
                    ))
        
        return violations
    
    def _is_test_file(self, file_path: Path) -> bool:
        """Check if file is a test file."""
        path_str = str(file_path).lower()
        return (
            'test_' in file_path.name or
            '/tests/' in path_str or
            '\\tests\\' in path_str or
            file_path.name.endswith('_test.py')
        )
    
    def check_directory(self, directory: Path, recursive: bool = True) -> List[Violation]:
        """
        Check all Python files in a directory.
        
        Args:
            directory: Directory to check
            recursive: Whether to check subdirectories
            
        Returns:
            List of all violations found
        """
        violations = []
        
        if recursive:
            python_files = directory.rglob('*.py')
        else:
            python_files = directory.glob('*.py')
        
        for file_path in python_files:
            # Skip certain directories
            skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'venv', '.venv', 'node_modules'}
            if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                continue
                
            file_violations = self.check_file(file_path)
            violations.extend(file_violations)
        
        return violations
    
    def generate_report(self, violations: List[Violation]) -> str:
        """Generate a formatted compliance report."""
        if not violations:
            return " PASS:  No repository compliance violations found!"
        
        # Group violations by type and severity
        errors = [v for v in violations if v.severity == "error"]
        warnings = [v for v in violations if v.severity == "warning"]
        
        report_lines = [
            "Repository Compliance Report",
            "=" * 35,
            ""
        ]
        
        if errors:
            report_lines.extend([
                f" FAIL:  ERRORS ({len(errors)}):",
                ""
            ])
            
            for error in errors:
                report_lines.append(f"  {error}")
            
            report_lines.append("")
        
        if warnings:
            report_lines.extend([
                f" WARNING: [U+FE0F]  WARNINGS ({len(warnings)}):",
                ""
            ])
            
            for warning in warnings:
                report_lines.append(f"  {warning}")
            
            report_lines.append("")
        
        # Add summary
        report_lines.extend([
            f"Summary: {len(errors)} errors, {len(warnings)} warnings",
            ""
        ])
        
        if errors:
            report_lines.extend([
                "To fix errors:",
                "1. Replace direct SQLAlchemy usage with TestRepositoryFactory",
                "2. Import: from test_framework.repositories import TestRepositoryFactory",
                "3. Use: async with factory.get_test_session() as session",
                "4. Create repos: factory.create_user_repository(session)",
                ""
            ])
        
        return "\n".join(report_lines)
    
    def fix_violations(self, violations: List[Violation]) -> Dict[str, List[str]]:
        """
        Attempt to automatically fix certain violations.
        
        Returns:
            Dictionary mapping file paths to lists of applied fixes
        """
        fixes = {}
        
        # Group violations by file
        by_file = {}
        for violation in violations:
            if violation.file_path not in by_file:
                by_file[violation.file_path] = []
            by_file[violation.file_path].append(violation)
        
        for file_path, file_violations in by_file.items():
            applied_fixes = []
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                modified_content = content
                
                # Fix missing factory import
                missing_import_violations = [
                    v for v in file_violations 
                    if v.violation_type == "missing_factory_import"
                ]
                
                if missing_import_violations:
                    # Add import at the top
                    import_line = "from test_framework.repositories import TestRepositoryFactory\n"
                    
                    # Find a good place to add the import
                    lines = modified_content.split('\n')
                    insert_index = 0
                    
                    # Skip shebang and encoding declarations
                    for i, line in enumerate(lines):
                        if (line.startswith('#!') or 
                            'coding:' in line or 
                            'encoding:' in line):
                            insert_index = i + 1
                        elif line.strip() == '':
                            continue
                        else:
                            break
                    
                    # Insert import
                    lines.insert(insert_index, import_line.rstrip())
                    modified_content = '\n'.join(lines)
                    applied_fixes.append("Added TestRepositoryFactory import")
                
                # Save fixes if any were applied
                if applied_fixes:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(modified_content)
                    
                    fixes[file_path] = applied_fixes
                    
            except Exception as e:
                logger.error(f"Failed to fix violations in {file_path}: {e}")
        
        return fixes


def main():
    """Main entry point for the compliance checker."""
    parser = argparse.ArgumentParser(
        description="Check repository compliance for SSOT enforcement"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to automatically fix violations"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--files",
        nargs="*",
        help="Specific files to check (default: all Python files)"
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Directories to exclude from checking"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Find project root
    current_dir = Path.cwd()
    project_root = current_dir
    
    # Look for project markers
    while project_root.parent != project_root:
        if any((project_root / marker).exists() for marker in ['.git', 'pyproject.toml', 'setup.py']):
            break
        project_root = project_root.parent
    
    print(f"Checking repository compliance in: {project_root}")
    
    checker = RepositoryComplianceChecker(project_root)
    violations = []
    
    if args.files:
        # Check specific files
        for file_path in args.files:
            file_path = Path(file_path)
            if file_path.exists():
                violations.extend(checker.check_file(file_path))
            else:
                print(f"Warning: File not found: {file_path}")
    else:
        # Check entire project
        violations.extend(checker.check_directory(project_root))
    
    # Filter out excluded directories
    if args.exclude:
        filtered_violations = []
        for violation in violations:
            if not any(excluded in violation.file_path for excluded in args.exclude):
                filtered_violations.append(violation)
        violations = filtered_violations
    
    # Generate report
    report = checker.generate_report(violations)
    print(report)
    
    # Apply fixes if requested
    if args.fix and violations:
        print("Applying automatic fixes...")
        fixes = checker.fix_violations(violations)
        
        if fixes:
            print("\nApplied fixes:")
            for file_path, file_fixes in fixes.items():
                print(f"  {file_path}:")
                for fix in file_fixes:
                    print(f"    - {fix}")
            
            # Re-check after fixes
            print("\nRe-checking after fixes...")
            new_violations = []
            if args.files:
                for file_path in args.files:
                    file_path = Path(file_path)
                    if file_path.exists():
                        new_violations.extend(checker.check_file(file_path))
            else:
                new_violations.extend(checker.check_directory(project_root))
            
            new_report = checker.generate_report(new_violations)
            print(new_report)
            
            violations = new_violations
        else:
            print("No automatic fixes available for current violations.")
    
    # Return appropriate exit code
    error_count = len([v for v in violations if v.severity == "error"])
    
    if error_count > 0:
        print(f"\n FAIL:  Found {error_count} error(s). Commit blocked.")
        return 1
    elif violations:
        warning_count = len([v for v in violations if v.severity == "warning"])
        print(f"\n WARNING: [U+FE0F]  Found {warning_count} warning(s). Commit allowed.")
        return 0
    else:
        print("\n PASS:  No violations found. Commit allowed.")
        return 0


if __name__ == "__main__":
    sys.exit(main())