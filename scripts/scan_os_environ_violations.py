#!/usr/bin/env python3
"""
CRITICAL OS.ENVIRON VIOLATIONS SCANNER

Scans for all direct os.environ access violations per CLAUDE.md requirements:
"Direct OS.env access is FORBIDDEN except in each service's canonical env config SSOT"

This scanner identifies:
1. All direct os.environ access patterns
2. Violations vs allowed canonical files
3. Detailed fix recommendations

Business Value: Platform/Internal - Environment Management Compliance
Ensures unified environment management architecture compliance.
"""
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
import json

@dataclass
class Violation:
    """Represents an os.environ violation"""
    file_path: Path
    line_number: int
    line_content: str
    pattern_type: str
    severity: str

class OSEnvironViolationScanner:
    """Comprehensive scanner for os.environ violations"""
    
    # Canonical env config files that are ALLOWED to use os.environ
    CANONICAL_ENV_FILES = {
        "netra_backend/app/core/isolated_environment.py",
        "auth_service/auth_core/isolated_environment.py", 
        "analytics_service/analytics_core/isolated_environment.py",
        "dev_launcher/isolated_environment.py"
    }
    
    # Patterns to detect os.environ usage
    OS_ENVIRON_PATTERNS = [
        (r'os\.environ\[', 'dict_access'),
        (r'os\.environ\.get\(', 'get_method'),
        (r'os\.environ\.setdefault\(', 'setdefault_method'),
        (r'os\.environ\.pop\(', 'pop_method'),
        (r'os\.environ\.update\(', 'update_method'),
        (r'os\.environ\s*=', 'assignment'),
        (r'del os\.environ\[', 'deletion')
    ]
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations: List[Violation] = []
        self.stats = {
            'total_files_scanned': 0,
            'files_with_violations': 0,
            'total_violations': 0,
            'canonical_files_checked': 0
        }
    
    def scan_all_python_files(self) -> None:
        """Scan all Python files for os.environ violations"""
        print("Scanning for os.environ violations...")
        
        # Get all Python files
        python_files = list(self.project_root.glob('**/*.py'))
        
        for py_file in python_files:
            # Skip if in .venv, __pycache__, .git
            if any(part.startswith('.') for part in py_file.parts):
                continue
                
            self.stats['total_files_scanned'] += 1
            
            try:
                violations_in_file = self._scan_file(py_file)
                if violations_in_file:
                    self.stats['files_with_violations'] += 1
                    self.violations.extend(violations_in_file)
                    
            except Exception as e:
                print(f"Error scanning {py_file}: {e}")
    
    def _scan_file(self, file_path: Path) -> List[Violation]:
        """Scan a single file for violations"""
        violations = []
        relative_path = file_path.relative_to(self.project_root)
        
        # Check if this is a canonical env config file
        relative_path_str = str(relative_path).replace('\\', '/')
        is_canonical = any(relative_path_str == canonical or 
                          relative_path_str.endswith(canonical) 
                          for canonical in self.CANONICAL_ENV_FILES)
        
        if is_canonical:
            self.stats['canonical_files_checked'] += 1
            # Canonical files are allowed to use os.environ
            return violations
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            return violations
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Skip comments
            if line_stripped.startswith('#'):
                continue
                
            # Check each pattern
            for pattern, pattern_type in self.OS_ENVIRON_PATTERNS:
                if re.search(pattern, line):
                    severity = self._determine_severity(line, pattern_type)
                    violation = Violation(
                        file_path=relative_path,
                        line_number=line_num,
                        line_content=line.rstrip(),
                        pattern_type=pattern_type,
                        severity=severity
                    )
                    violations.append(violation)
                    self.stats['total_violations'] += 1
        
        return violations
    
    def _determine_severity(self, line: str, pattern_type: str) -> str:
        """Determine violation severity"""
        # High severity for production code
        if 'production' in line.lower() or 'staging' in line.lower():
            return 'HIGH'
        # Medium for main service files
        if 'main.py' in str(line) or 'config.py' in str(line):
            return 'MEDIUM'
        # Low for test files
        if 'test_' in line.lower() or '/test' in line.lower():
            return 'LOW'
        return 'MEDIUM'
    
    def generate_report(self) -> Dict:
        """Generate comprehensive violation report"""
        # Group violations by file
        violations_by_file = {}
        severity_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        pattern_counts = {}
        
        for violation in self.violations:
            file_key = str(violation.file_path)
            if file_key not in violations_by_file:
                violations_by_file[file_key] = []
            violations_by_file[file_key].append(violation)
            
            severity_counts[violation.severity] += 1
            pattern_counts[violation.pattern_type] = pattern_counts.get(violation.pattern_type, 0) + 1
        
        return {
            'summary': {
                'total_violations': self.stats['total_violations'],
                'files_with_violations': self.stats['files_with_violations'],
                'total_files_scanned': self.stats['total_files_scanned'],
                'canonical_files_checked': self.stats['canonical_files_checked']
            },
            'severity_distribution': severity_counts,
            'pattern_distribution': pattern_counts,
            'violations_by_file': violations_by_file,
            'canonical_files': list(self.CANONICAL_ENV_FILES)
        }
    
    def print_detailed_report(self) -> None:
        """Print detailed violation report"""
        report = self.generate_report()
        
        print("\n" + "="*80)
        print("OS.ENVIRON VIOLATIONS REPORT")
        print("="*80)
        
        # Summary
        summary = report['summary']
        print(f"\nSUMMARY:")
        print(f"  Total violations found: {summary['total_violations']}")
        print(f"  Files with violations: {summary['files_with_violations']}")
        print(f"  Total Python files scanned: {summary['total_files_scanned']}")
        print(f"  Canonical env files (allowed): {summary['canonical_files_checked']}")
        
        # Severity distribution
        print(f"\nSEVERITY DISTRIBUTION:")
        for severity, count in report['severity_distribution'].items():
            print(f"  {severity}: {count} violations")
        
        # Pattern distribution  
        print(f"\nPATTERN DISTRIBUTION:")
        for pattern, count in report['pattern_distribution'].items():
            print(f"  {pattern}: {count} violations")
        
        # Top violating files
        print(f"\nTOP VIOLATING FILES:")
        violations_by_file = report['violations_by_file']
        sorted_files = sorted(violations_by_file.items(), 
                             key=lambda x: len(x[1]), reverse=True)[:10]
        
        for file_path, violations in sorted_files:
            print(f"  {file_path}: {len(violations)} violations")
            for violation in violations[:3]:  # Show first 3 violations
                print(f"    Line {violation.line_number}: {violation.line_content.strip()}")
            if len(violations) > 3:
                print(f"    ... and {len(violations) - 3} more")
        
        # Canonical files info
        print(f"\nCANONICAL ENV CONFIG FILES (ALLOWED):")
        for canonical in report['canonical_files']:
            print(f"  {canonical}")
        
        print(f"\nREMEDIATION REQUIRED:")
        print(f"  Replace all {summary['total_violations']} violations with proper IsolatedEnvironment usage")
        print(f"  Each service must use its own canonical env config SSOT")
        print(f"  Tests must also follow this rule - no exceptions")

def main():
    """Main scanner entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == '--json':
        output_json = True
    else:
        output_json = False
    
    project_root = Path(__file__).parent.parent
    scanner = OSEnvironViolationScanner(project_root)
    
    # Scan all files
    scanner.scan_all_python_files()
    
    if output_json:
        # Output JSON report for programmatic use
        report = scanner.generate_report()
        # Convert violations to serializable format
        for file_path, violations in report['violations_by_file'].items():
            report['violations_by_file'][file_path] = [
                {
                    'file_path': str(v.file_path),
                    'line_number': v.line_number,
                    'line_content': v.line_content,
                    'pattern_type': v.pattern_type,
                    'severity': v.severity
                }
                for v in violations
            ]
        print(json.dumps(report, indent=2))
    else:
        # Print detailed human-readable report
        scanner.print_detailed_report()
    
    # Return exit code based on violations found
    if scanner.stats['total_violations'] > 0:
        if not output_json:
            print(f"\nFound {scanner.stats['total_violations']} violations - remediation required!")
        sys.exit(1)
    else:
        if not output_json:
            print(f"\nNo os.environ violations found - compliance achieved!")
        sys.exit(0)

if __name__ == '__main__':
    main()