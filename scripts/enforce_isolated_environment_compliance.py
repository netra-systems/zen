#!/usr/bin/env python3
"""
CRITICAL ENVIRONMENT COMPLIANCE ENFORCEMENT SCRIPT
==================================================

Enforces unified IsolatedEnvironment usage across the entire platform.
This script detects and prevents all direct os.environ access violations.

CRITICAL REQUIREMENTS per CLAUDE.md:
- ALL environment access must go through IsolatedEnvironment
- NO direct os.environ, os.getenv, or environment patching
- Follow unified_environment_management.xml
- Automated enforcement to prevent regression

Business Value: Platform/Internal - System Stability
Prevents configuration failures that could be catastrophic.

Author: Claude Code - Critical Compliance Enforcement
Date: 2025-09-02
"""

import ast
import os
import re
import sys
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Union
from dataclasses import dataclass
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ViolationDetail:
    """Details of an environment access violation."""
    file_path: str
    line_number: int
    line_content: str
    violation_type: str
    suggested_fix: str
    severity: str = "CRITICAL"

@dataclass
class ComplianceReport:
    """Comprehensive compliance report."""
    total_files_scanned: int
    violation_count: int
    clean_files: int
    violations: List[ViolationDetail]
    critical_violations: int
    high_violations: int
    medium_violations: int
    
    @property
    def is_compliant(self) -> bool:
        """Check if codebase is fully compliant."""
        return self.violation_count == 0
    
    @property
    def compliance_score(self) -> float:
        """Calculate compliance score (0-100)."""
        if self.total_files_scanned == 0:
            return 100.0
        return (self.clean_files / self.total_files_scanned) * 100.0

class IsolatedEnvironmentEnforcer:
    """Enforces IsolatedEnvironment usage compliance across the codebase."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        
        # Violation patterns to detect
        self.violation_patterns = {
            'direct_os_environ': {
                'pattern': r'os\.environ(?:\[|\.|get\()',
                'description': 'Direct os.environ access',
                'fix': 'Replace with get_env().get() or get_env().set()',
                'severity': 'CRITICAL'
            },
            'patch_dict_os_environ': {
                'pattern': r'patch\.dict\s*\(\s*os\.environ',
                'description': 'patch.dict(os.environ) usage',
                'fix': 'Replace with IsolatedEnvironment context manager',
                'severity': 'CRITICAL'
            },
            'os_getenv': {
                'pattern': r'os\.getenv\s*\(',
                'description': 'Direct os.getenv() call',
                'fix': 'Replace with get_env().get()',
                'severity': 'CRITICAL'
            },
            'environ_import': {
                'pattern': r'from\s+os\s+import.*environ',
                'description': 'Direct environ import',
                'fix': 'Remove import and use get_env() instead',
                'severity': 'HIGH'
            },
            'os_environ_direct': {
                'pattern': r'\bos\.environ\b',
                'description': 'Any os.environ reference',
                'fix': 'Use IsolatedEnvironment methods instead',
                'severity': 'CRITICAL'
            },
            'missing_import': {
                'pattern': r'(?:^|\n)(?!.*from shared\.isolated_environment import)',
                'description': 'Missing IsolatedEnvironment import',
                'fix': 'Add: from shared.isolated_environment import get_env',
                'severity': 'MEDIUM'
            }
        }
        
        # Files/directories to exclude from scanning
        self.excluded_paths = {
            'shared/isolated_environment.py',  # The implementation itself
            '__pycache__',
            '.git',
            'node_modules',
            '.venv',
            'venv',
            'build',
            'dist',
            '.pytest_cache',
            'htmlcov'
        }
        
        # Files that are allowed to have direct os.environ access
        self.allowed_exceptions = {
            'shared/isolated_environment.py',  # The SSOT implementation
            'scripts/enforce_isolated_environment_compliance.py',  # This script
            # Add other legitimate exceptions here
        }

    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during scanning."""
        # Convert to relative path for consistent checking
        try:
            rel_path = file_path.relative_to(self.project_root)
            rel_path_str = str(rel_path).replace('\\', '/')
        except ValueError:
            # File is outside project root
            return True
        
        # Check against excluded paths
        for excluded in self.excluded_paths:
            if excluded in rel_path_str:
                return True
        
        # Only scan Python files
        if file_path.suffix != '.py':
            return True
        
        return False

    def is_allowed_exception(self, file_path: Path) -> bool:
        """Check if file is an allowed exception."""
        try:
            rel_path = file_path.relative_to(self.project_root)
            rel_path_str = str(rel_path).replace('\\', '/')
            return rel_path_str in self.allowed_exceptions
        except ValueError:
            return False

    def scan_file_for_violations(self, file_path: Path) -> List[ViolationDetail]:
        """Scan a single file for environment access violations."""
        violations = []
        
        if self.should_skip_file(file_path) or self.is_allowed_exception(file_path):
            return violations
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Check each pattern
            for violation_type, config in self.violation_patterns.items():
                if violation_type == 'missing_import':
                    # Special handling for missing import check
                    self._check_missing_import(file_path, content, violations)
                    continue
                
                pattern = config['pattern']
                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        violations.append(ViolationDetail(
                            file_path=str(file_path),
                            line_number=line_num,
                            line_content=line.strip(),
                            violation_type=violation_type,
                            suggested_fix=config['fix'],
                            severity=config['severity']
                        ))
        
        except Exception as e:
            logger.warning(f"Error scanning {file_path}: {e}")
        
        return violations

    def _check_missing_import(self, file_path: Path, content: str, violations: List[ViolationDetail]) -> None:
        """Check if file needs IsolatedEnvironment import but doesn't have it."""
        # If file has environment access patterns, it should have the import
        has_env_access = any(
            re.search(pattern['pattern'], content) 
            for pattern in self.violation_patterns.values()
            if pattern != self.violation_patterns['missing_import']
        )
        
        has_isolated_env_import = (
            'from shared.isolated_environment import' in content or
            'import shared.isolated_environment' in content
        )
        
        if has_env_access and not has_isolated_env_import:
            violations.append(ViolationDetail(
                file_path=str(file_path),
                line_number=1,
                line_content="# Missing IsolatedEnvironment import",
                violation_type='missing_import',
                suggested_fix=self.violation_patterns['missing_import']['fix'],
                severity=self.violation_patterns['missing_import']['severity']
            ))

    def scan_directory(self, directory: Path) -> List[ViolationDetail]:
        """Scan directory recursively for violations."""
        all_violations = []
        
        for file_path in directory.rglob('*.py'):
            violations = self.scan_file_for_violations(file_path)
            all_violations.extend(violations)
        
        return all_violations

    def generate_compliance_report(self, violations: List[ViolationDetail]) -> ComplianceReport:
        """Generate comprehensive compliance report."""
        # Count files scanned
        scanned_files = set()
        for violation in violations:
            scanned_files.add(violation.file_path)
        
        # Count all Python files
        total_files = sum(1 for _ in self.project_root.rglob('*.py') if not self.should_skip_file(Path(_)))
        
        # Count violations by severity
        critical_count = sum(1 for v in violations if v.severity == 'CRITICAL')
        high_count = sum(1 for v in violations if v.severity == 'HIGH')
        medium_count = sum(1 for v in violations if v.severity == 'MEDIUM')
        
        clean_files = total_files - len(scanned_files)
        
        return ComplianceReport(
            total_files_scanned=total_files,
            violation_count=len(violations),
            clean_files=clean_files,
            violations=violations,
            critical_violations=critical_count,
            high_violations=high_count,
            medium_violations=medium_count
        )

    def print_compliance_report(self, report: ComplianceReport) -> None:
        """Print formatted compliance report."""
        print("\n" + "="*80)
        print("ISOLATED ENVIRONMENT COMPLIANCE REPORT")
        print("="*80)
        
        print(f"\nOVERVIEW:")
        print(f"  Total Files Scanned: {report.total_files_scanned}")
        print(f"  Clean Files: {report.clean_files}")
        print(f"  Files with Violations: {len(set(v.file_path for v in report.violations))}")
        print(f"  Total Violations: {report.violation_count}")
        print(f"  Compliance Score: {report.compliance_score:.1f}%")
        
        if report.violation_count > 0:
            print(f"\nVIOLATIONS BY SEVERITY:")
            print(f"  [CRITICAL]: {report.critical_violations}")
            print(f"  [HIGH]:     {report.high_violations}")
            print(f"  [MEDIUM]:   {report.medium_violations}")
            
            print(f"\nDETAILED VIOLATIONS:")
            print("-" * 80)
            
            # Group violations by file
            violations_by_file = {}
            for violation in report.violations:
                if violation.file_path not in violations_by_file:
                    violations_by_file[violation.file_path] = []
                violations_by_file[violation.file_path].append(violation)
            
            for file_path, violations in sorted(violations_by_file.items()):
                print(f"\nFile: {file_path}")
                for violation in violations:
                    severity_icon = {
                        'CRITICAL': '[CRIT]',
                        'HIGH': '[HIGH]',
                        'MEDIUM': '[MED]'
                    }.get(violation.severity, '[?]')
                    
                    print(f"  {severity_icon} Line {violation.line_number}: {violation.violation_type}")
                    print(f"     Code: {violation.line_content}")
                    print(f"     Fix:  {violation.suggested_fix}")
        
        if report.is_compliant:
            print("\n[OK] COMPLIANCE STATUS: FULLY COMPLIANT")
            print("All environment access follows IsolatedEnvironment patterns!")
        else:
            print("\n[FAIL] COMPLIANCE STATUS: VIOLATIONS DETECTED")
            print("CRITICAL: Fix all violations to ensure system stability!")

    def fix_violations_automatically(self, violations: List[ViolationDetail]) -> Dict[str, int]:
        """Attempt to automatically fix common violations."""
        fixes_applied = {
            'direct_os_environ': 0,
            'patch_dict_os_environ': 0,
            'os_getenv': 0,
            'missing_import': 0
        }
        
        # Group violations by file
        violations_by_file = {}
        for violation in violations:
            if violation.file_path not in violations_by_file:
                violations_by_file[violation.file_path] = []
            violations_by_file[violation.file_path].append(violation)
        
        for file_path, file_violations in violations_by_file.items():
            if self.is_allowed_exception(Path(file_path)):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                
                modified = False
                new_lines = lines[:]
                
                # Sort violations by line number (descending) to avoid index issues
                file_violations.sort(key=lambda v: v.line_number, reverse=True)
                
                for violation in file_violations:
                    if violation.violation_type == 'os_getenv':
                        # Replace os.getenv with get_env().get()
                        line_idx = violation.line_number - 1
                        if line_idx < len(new_lines):
                            old_line = new_lines[line_idx]
                            new_line = re.sub(
                                r'os\.getenv\s*\(',
                                'get_env().get(',
                                old_line
                            )
                            if new_line != old_line:
                                new_lines[line_idx] = new_line
                                modified = True
                                fixes_applied['os_getenv'] += 1
                
                # Add missing import if needed
                needs_import = any(v.violation_type == 'missing_import' for v in file_violations)
                if needs_import and not any('from shared.isolated_environment import' in line for line in new_lines):
                    # Find best place to insert import
                    import_line = "from shared.isolated_environment import get_env\n"
                    
                    # Insert after existing imports
                    insert_idx = 0
                    for i, line in enumerate(new_lines):
                        if line.strip().startswith(('import ', 'from ')):
                            insert_idx = i + 1
                        elif line.strip() and not line.strip().startswith('#'):
                            break
                    
                    new_lines.insert(insert_idx, import_line.strip())
                    modified = True
                    fixes_applied['missing_import'] += 1
                
                if modified:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(new_lines) + '\n')
                    logger.info(f"Applied automatic fixes to {file_path}")
            
            except Exception as e:
                logger.error(f"Error applying fixes to {file_path}: {e}")
        
        return fixes_applied

    def run_compliance_check(self, auto_fix: bool = False) -> ComplianceReport:
        """Run complete compliance check."""
        logger.info("Starting IsolatedEnvironment compliance scan...")
        
        # Scan for violations
        violations = self.scan_directory(self.project_root)
        
        # Generate report
        report = self.generate_compliance_report(violations)
        
        # Apply automatic fixes if requested
        if auto_fix and not report.is_compliant:
            logger.info("Applying automatic fixes...")
            fixes = self.fix_violations_automatically(violations)
            
            # Re-scan after fixes
            violations = self.scan_directory(self.project_root)
            report = self.generate_compliance_report(violations)
            
            print(f"\nAUTOMATIC FIXES APPLIED:")
            for fix_type, count in fixes.items():
                if count > 0:
                    print(f"  {fix_type}: {count} fixes")
        
        return report

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Enforce IsolatedEnvironment compliance across the codebase"
    )
    parser.add_argument(
        '--auto-fix',
        action='store_true',
        help='Automatically fix violations where possible'
    )
    parser.add_argument(
        '--fail-on-violations',
        action='store_true',
        help='Exit with non-zero code if violations are found'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress detailed output, only show summary'
    )
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    
    # Run compliance check
    enforcer = IsolatedEnvironmentEnforcer()
    report = enforcer.run_compliance_check(auto_fix=args.auto_fix)
    
    # Print report
    if not args.quiet:
        enforcer.print_compliance_report(report)
    else:
        # Just print summary
        status = "COMPLIANT" if report.is_compliant else "NON-COMPLIANT"
        print(f"Compliance Status: {status} ({report.compliance_score:.1f}%)")
        if not report.is_compliant:
            print(f"Violations: {report.violation_count} ({report.critical_violations} critical)")
    
    # Exit with appropriate code
    if args.fail_on_violations and not report.is_compliant:
        sys.exit(1)
    
    sys.exit(0)

if __name__ == '__main__':
    main()