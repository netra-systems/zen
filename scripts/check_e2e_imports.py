#!/usr/bin/env python3
"""
E2E Test Import Verification and Fixing Tool

Business Value Justification (BVJ):
- Segment: Platform
- Business Goal: Testing Reliability
- Value Impact: Ensures all e2e tests can load and run properly
- Strategic Impact: Prevents CI/CD failures and improves test coverage
"""

import ast
import importlib.util
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add project root to path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class E2EImportChecker:
    """Check and fix imports for e2e tests."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.test_dirs = [
            self.project_root / 'tests' / 'e2e',
            self.project_root / 'tests' / 'unified' / 'e2e',
            self.project_root / 'netra_backend' / 'tests' / 'e2e',
            self.project_root / 'netra_backend' / 'tests' / 'agents',
            self.project_root / 'netra_backend' / 'tests' / 'integration',
            self.project_root / 'legacy_integration_tests'
        ]
        self.results = {
            'total_files': 0,
            'successful': [],
            'failed': [],
            'import_errors': {},
            'syntax_errors': {},
            'fixed': []
        }
    
    def find_e2e_test_files(self) -> List[Path]:
        """Find all e2e test files."""
        e2e_files = []
        patterns = ['*e2e*.py', '*E2E*.py']
        
        for test_dir in self.test_dirs:
            if test_dir.exists():
                for pattern in patterns:
                    e2e_files.extend(test_dir.rglob(pattern))
        
        # Filter out __pycache__ and non-test files
        e2e_files = [
            f for f in e2e_files 
            if '__pycache__' not in str(f) and f.name.startswith('test_')
        ]
        
        return sorted(set(e2e_files))
    
    def check_file_imports(self, file_path: Path) -> Tuple[bool, str]:
        """Check if a file's imports work."""
        try:
            # First check syntax
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            ast.parse(source)
            
            # Try to load the module
            spec = importlib.util.spec_from_file_location(
                f"test_module_{file_path.stem}",
                file_path
            )
            
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return True, "OK"
            else:
                return False, "Failed to create module spec"
                
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        except ImportError as e:
            return False, f"Import error: {e}"
        except Exception as e:
            return False, f"Error: {e}"
    
    def extract_imports(self, file_path: Path) -> Set[str]:
        """Extract all imports from a file."""
        imports = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
        except:
            pass
        
        return imports
    
    def fix_common_import_issues(self, file_path: Path) -> bool:
        """Fix common import issues in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            fixed = False
            
            # Common fixes
            replacements = [
                # Fix relative imports in tests
                ('from ..', 'from netra_backend.'),
                ('from .', 'from netra_backend.'),
                
                # Fix common module paths
                ('from app.', 'from netra_backend.app.'),
                ('import app.', 'import netra_backend.app.'),
                
                # Fix test utilities
                ('from netra_backend.tests.', 'from netra_backend.tests.'),
                ('from test_utils', 'from netra_backend.tests.test_utils'),
                
                # Fix auth service imports
                ('from auth_core.', 'from auth_service.auth_core.'),
                
                # Fix frontend test imports
                ('from frontend.', 'from netra_backend.tests.frontend.'),
            ]
            
            for old, new in replacements:
                if old in content:
                    content = content.replace(old, new)
                    fixed = True
            
            # Add missing sys.path setup if needed
            if 'sys.path' not in content and fixed:
                path_setup = '''import sys
from pathlib import Path

'''
                # Insert after initial docstring and imports
                lines = content.split('\n')
                insert_pos = 0
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        insert_pos = i
                        break
                
                if insert_pos > 0:
                    lines.insert(insert_pos, path_setup)
                    content = '\n'.join(lines)
                    fixed = True
            
            if fixed and content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to fix {file_path}: {e}")
            return False
    
    def check_all(self, fix: bool = False) -> Dict:
        """Check all e2e test files."""
        logger.info("=" * 60)
        logger.info("E2E TEST IMPORT VERIFICATION")
        logger.info("=" * 60)
        
        e2e_files = self.find_e2e_test_files()
        self.results['total_files'] = len(e2e_files)
        
        logger.info(f"Found {len(e2e_files)} e2e test files")
        
        for file_path in e2e_files:
            rel_path = file_path.relative_to(self.project_root)
            success, error = self.check_file_imports(file_path)
            
            if success:
                self.results['successful'].append(str(rel_path))
                logger.info(f"  [U+2713] {rel_path}")
            else:
                self.results['failed'].append(str(rel_path))
                self.results['import_errors'][str(rel_path)] = error
                logger.warning(f"  [U+2717] {rel_path}: {error}")
                
                if fix:
                    if self.fix_common_import_issues(file_path):
                        # Re-check after fix
                        success2, error2 = self.check_file_imports(file_path)
                        if success2:
                            self.results['fixed'].append(str(rel_path))
                            self.results['failed'].remove(str(rel_path))
                            self.results['successful'].append(str(rel_path))
                            del self.results['import_errors'][str(rel_path)]
                            logger.info(f"    FIXED: {rel_path}")
        
        return self.results
    
    def generate_report(self) -> None:
        """Generate detailed report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_files': self.results['total_files'],
                'successful': len(self.results['successful']),
                'failed': len(self.results['failed']),
                'fixed': len(self.results['fixed'])
            },
            'details': self.results
        }
        
        # Save JSON report
        report_path = self.project_root / 'test_reports' / 'e2e_import_report.json'
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        # Save markdown report
        md_path = self.project_root / 'test_reports' / 'e2e_import_report.md'
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# E2E Test Import Report\n\n")
            f.write(f"Generated: {report['timestamp']}\n\n")
            f.write("## Summary\n\n")
            f.write(f"- Total Files: {report['summary']['total_files']}\n")
            f.write(f"- Successful: {report['summary']['successful']}\n")
            f.write(f"- Failed: {report['summary']['failed']}\n")
            f.write(f"- Fixed: {report['summary']['fixed']}\n\n")
            
            if self.results['failed']:
                f.write("## Failed Imports\n\n")
                for file, error in self.results['import_errors'].items():
                    f.write(f"### {file}\n")
                    f.write(f"```\n{error}\n```\n\n")
        
        logger.info(f"\nReports saved:")
        logger.info(f"  - JSON: {report_path}")
        logger.info(f"  - Markdown: {md_path}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='E2E Test Import Checker')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix import issues')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    
    args = parser.parse_args()
    
    checker = E2EImportChecker()
    results = checker.check_all(fix=args.fix)
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Files: {results['total_files']}")
    logger.info(f"Successful: {len(results['successful'])}")
    logger.info(f"Failed: {len(results['failed'])}")
    logger.info(f"Fixed: {len(results['fixed'])}")
    
    if args.report or results['failed']:
        checker.generate_report()
    
    # Return non-zero exit code if there are failures
    sys.exit(1 if results['failed'] else 0)


if __name__ == '__main__':
    main()