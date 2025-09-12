#!/usr/bin/env python
"""
Test Environment Hardening Migration Script

This script migrates test files from using direct os.environ patches
to using IsolatedEnvironment for proper environment isolation.

This addresses the CRITICAL finding from CRITICAL_CONFIG_REGRESSION_AUDIT_REPORT.md
about test environment variable pollution risks.
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def analyze_file(file_path: Path) -> List[Tuple[int, str]]:
    """
    Analyze a file for patch.dict(os.environ) patterns.
    
    Returns:
        List of (line_number, line_content) tuples with the bad pattern
    """
    bad_patterns = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines, 1):
            if 'patch.dict(os.environ' in line:
                bad_patterns.append((i, line.strip()))
                
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        
    return bad_patterns

def generate_migration_report(test_files: List[Path]) -> str:
    """
    Generate a comprehensive migration report.
    """
    report = []
    report.append("# Test Environment Hardening Migration Report\n")
    report.append(f"**Total Files to Migrate:** {len(test_files)}\n")
    report.append("\n## Files with Direct os.environ Patches\n")
    
    total_occurrences = 0
    by_category = {
        'e2e': [],
        'integration': [],
        'unit': [],
        'mission_critical': [],
        'security': [],
        'other': []
    }
    
    for file_path in test_files:
        patterns = analyze_file(file_path)
        if patterns:
            total_occurrences += len(patterns)
            
            # Categorize by test type
            file_str = str(file_path)
            if 'e2e' in file_str:
                category = 'e2e'
            elif 'integration' in file_str:
                category = 'integration'
            elif 'unit' in file_str:
                category = 'unit'
            elif 'mission_critical' in file_str:
                category = 'mission_critical'
            elif 'security' in file_str:
                category = 'security'
            else:
                category = 'other'
                
            by_category[category].append({
                'file': file_path,
                'occurrences': len(patterns),
                'lines': patterns
            })
    
    report.append(f"\n**Total Occurrences:** {total_occurrences}\n")
    
    # Report by category
    for category, files in by_category.items():
        if files:
            report.append(f"\n### {category.upper()} Tests ({len(files)} files)\n")
            for file_info in files:
                rel_path = file_info['file'].relative_to(project_root)
                report.append(f"\n#### {rel_path}\n")
                report.append(f"- **Occurrences:** {file_info['occurrences']}\n")
                report.append("- **Lines:**\n")
                for line_num, line_content in file_info['lines'][:3]:  # Show first 3
                    report.append(f"  - Line {line_num}: `{line_content[:80]}...`\n")
                if len(file_info['lines']) > 3:
                    report.append(f"  - ... and {len(file_info['lines']) - 3} more\n")
    
    # Add migration guidance
    report.append("\n## Migration Pattern\n")
    report.append("### Bad Pattern (Direct os.environ patch):\n")
    report.append("```python\n")
    report.append("with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):\n")
    report.append("    # test code\n")
    report.append("```\n\n")
    
    report.append("### Good Pattern (IsolatedEnvironment):\n")
    report.append("```python\n")
    report.append("from shared.isolated_environment import IsolatedEnvironment\n\n")
    report.append("env = IsolatedEnvironment()\n")
    report.append("env.set('ENVIRONMENT', 'staging')\n")
    report.append("# test code\n")
    report.append("env.reset()  # Clean up\n")
    report.append("```\n\n")
    
    report.append("### Alternative Pattern (Context Manager):\n")
    report.append("```python\n")
    report.append("from shared.isolated_environment import IsolatedEnvironment\n\n")
    report.append("with IsolatedEnvironment.temporary_override({'ENVIRONMENT': 'staging'}):\n")
    report.append("    # test code\n")
    report.append("```\n\n")
    
    # Add risk assessment
    report.append("## Risk Assessment\n")
    report.append("- **Current Risk:** MEDIUM - Test environment configs can leak between tests\n")
    report.append("- **Post-Migration Risk:** LOW - Each test has isolated environment\n")
    report.append("- **Business Impact:** Prevents false test passes due to environment pollution\n")
    report.append("- **Technical Impact:** Ensures test reliability and reproducibility\n")
    
    return ''.join(report)

def create_migration_helper() -> str:
    """
    Create a helper module for test environment isolation.
    """
    helper_code = '''"""
Test Environment Isolation Helper

Provides utilities for proper test environment isolation using IsolatedEnvironment.
This replaces direct os.environ patches to prevent test pollution.
"""

from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager
import unittest
from unittest.mock import patch
from shared.isolated_environment import IsolatedEnvironment


class IsolatedTestCase(SSotBaseTestCase):
    """
    Base test case with automatic environment isolation.
    """
    
    def setUp(self):
        """Set up isolated environment for each test."""
        super().setUp()
        self.env = IsolatedEnvironment()
        self.env.enable_isolation_mode()
        self.addCleanup(self.env.reset)
    
    def set_env(self, key: str, value: str) -> None:
        """
        Set an environment variable in the isolated environment.
        
        Args:
            key: Environment variable name
            value: Environment variable value
        """
        self.env.set(key, value)
    
    def set_env_batch(self, env_vars: Dict[str, str]) -> None:
        """
        Set multiple environment variables at once.
        
        Args:
            env_vars: Dictionary of environment variables
        """
        for key, value in env_vars.items():
            self.env.set(key, value)


@contextmanager
def isolated_env(**env_vars):
    """
    Context manager for temporary environment isolation.
    
    Usage:
        with isolated_env(ENVIRONMENT='staging', DEBUG='true'):
            # test code runs with isolated environment
            pass
    """
    env = IsolatedEnvironment()
    env.enable_isolation_mode()
    
    for key, value in env_vars.items():
        env.set(key, value)
    
    try:
        yield env
    finally:
        env.reset()


def patch_env(target: str, **env_vars) -> Callable:
    """
    Decorator for patching environment variables in tests.
    
    Usage:
        @patch_env('netra_backend.app.core.config', ENVIRONMENT='staging')
        def test_something(self):
            # test code
            pass
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with isolated_env(**env_vars):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# MIGRATION GUIDE:
# 
# 1. Replace SSotBaseTestCase with IsolatedTestCase:
#    class TestMyFeature(IsolatedTestCase):
#        def test_something(self):
#            self.set_env('KEY', 'value')
#
# 2. Replace patch.dict(os.environ) with isolated_env():
#    with isolated_env(KEY='value'):
#        # test code
#
# 3. Use decorator for method-level isolation:
#    @patch_env('module.path', KEY='value')
#    def test_something(self):
#        # test code
'''
    return helper_code

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Migrate tests to use IsolatedEnvironment')
    parser.add_argument('--analyze', action='store_true', 
                       help='Analyze files and generate report only')
    parser.add_argument('--create-helper', action='store_true',
                       help='Create test isolation helper module')
    
    args = parser.parse_args()
    
    # Find all test files with the bad pattern
    test_files = []
    for pattern in ['**/*test*.py', '**/test_*.py']:
        test_files.extend(project_root.glob(pattern))
    
    # Filter to only files with patch.dict(os.environ
    files_to_migrate = []
    for file_path in test_files:
        if file_path.is_file():
            try:
                content = file_path.read_text(encoding='utf-8')
                if 'patch.dict(os.environ' in content:
                    files_to_migrate.append(file_path)
            except:
                pass
    
    print(f"Found {len(files_to_migrate)} test files with direct os.environ patches")
    
    if args.analyze:
        # Generate analysis report
        report = generate_migration_report(files_to_migrate)
        report_path = project_root / 'TEST_ENVIRONMENT_HARDENING_REPORT.md'
        report_path.write_text(report, encoding='utf-8')
        print(f"Analysis report saved to: {report_path}")
        
    if args.create_helper:
        # Create helper module
        helper_path = project_root / 'test_framework' / 'ssot' / 'isolated_test_helper.py'
        helper_path.parent.mkdir(parents=True, exist_ok=True)
        helper_path.write_text(create_migration_helper(), encoding='utf-8')
        print(f"Test helper module created at: {helper_path}")
        
    if not args.analyze and not args.create_helper:
        print("\nUse --analyze to generate migration report")
        print("Use --create-helper to create test isolation helper module")
        print("\nRecommended workflow:")
        print("1. python scripts/migrate_test_environment_hardening.py --analyze")
        print("2. python scripts/migrate_test_environment_hardening.py --create-helper")
        print("3. Migrate tests using the helper module")

if __name__ == '__main__':
    main()