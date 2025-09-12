#!/usr/bin/env python3
"""
CI Mock Policy Enforcement Script

This script enforces the "MOCKS = Abomination" policy from CLAUDE.md
by scanning all test files and failing CI builds when mocks are detected.

Usage:
    python check_violations.py
    python check_violations.py --service auth_service
    python check_violations.py --fail-on-violations --max-violations 0

Exit Codes:
    0: No violations found
    1: Violations found and --fail-on-violations enabled
    2: Script error
"""

import ast
import os
import sys
import re
import argparse
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class MockViolation:
    """Represents a single mock usage violation."""
    file_path: str
    line_number: int
    violation_type: str
    code_snippet: str
    service: str
    severity: str = "ERROR"  # ERROR, WARNING, INFO
    
    def __str__(self):
        return f"[{self.severity}] {self.file_path}:{self.line_number} - {self.violation_type}: {self.code_snippet}"


class ComprehensiveMockDetector:
    """Enhanced mock detector with comprehensive pattern recognition."""
    
    def __init__(self):
        self.mock_patterns = [
            # Import patterns
            (r'from\s+unittest\.mock\s+import', 'Mock Import', 'ERROR'),
            (r'from\s+mock\s+import', 'Mock Import', 'ERROR'),
            (r'import\s+unittest\.mock', 'Mock Import', 'ERROR'),
            (r'import\s+mock', 'Mock Import', 'ERROR'),
            (r'import\s+pytest_mock', 'Pytest Mock Import', 'ERROR'),
            (r'from\s+pytest_mock\s+import', 'Pytest Mock Import', 'ERROR'),
            
            # Constructor patterns
            (r'\bMock\s*\(', 'Mock Constructor', 'ERROR'),
            (r'\bMagicMock\s*\(', 'MagicMock Constructor', 'ERROR'),
            (r'\bAsyncMock\s*\(', 'AsyncMock Constructor', 'ERROR'),
            (r'\bPropertyMock\s*\(', 'PropertyMock Constructor', 'ERROR'),
            (r'\bNonCallableMock\s*\(', 'NonCallableMock Constructor', 'ERROR'),
            
            # Decorator patterns  
            (r'@patch\s*\(', 'Patch Decorator', 'ERROR'),
            (r'@mock\.patch', 'Mock Patch Decorator', 'ERROR'),
            (r'@unittest\.mock\.patch', 'Unittest Mock Patch Decorator', 'ERROR'),
            
            # Method call patterns
            (r'\.patch\s*\(', 'Patch Method Call', 'ERROR'),
            (r'\.patch\.object\s*\(', 'Patch Object Call', 'ERROR'),
            (r'\.patch\.dict\s*\(', 'Patch Dict Call', 'ERROR'),
            (r'\.patch\.multiple\s*\(', 'Patch Multiple Call', 'ERROR'),
            (r'create_autospec\s*\(', 'Create Autospec', 'ERROR'),
            (r'mock_open\s*\(', 'Mock Open', 'ERROR'),
            
            # Mock usage patterns
            (r'\.return_value\s*=', 'Mock Return Value', 'ERROR'),
            (r'\.side_effect\s*=', 'Mock Side Effect', 'ERROR'),
            (r'\.mock_calls', 'Mock Calls Access', 'ERROR'),
            (r'\.call_args', 'Mock Call Args Access', 'ERROR'),
            (r'\.method_calls', 'Mock Method Calls', 'ERROR'),
            
            # Assertion patterns
            (r'\.assert_called\b', 'Mock Assert Called', 'ERROR'),
            (r'\.assert_called_once\b', 'Mock Assert Called Once', 'ERROR'),
            (r'\.assert_called_with\s*\(', 'Mock Assert Called With', 'ERROR'),
            (r'\.assert_called_once_with\s*\(', 'Mock Assert Called Once With', 'ERROR'),
            (r'\.assert_any_call\s*\(', 'Mock Assert Any Call', 'ERROR'),
            (r'\.assert_has_calls\s*\(', 'Mock Assert Has Calls', 'ERROR'),
            (r'\.assert_not_called\s*\(', 'Mock Assert Not Called', 'ERROR'),
            
            # Context manager patterns
            (r'with\s+patch\s*\(', 'Patch Context Manager', 'ERROR'),
            (r'with\s+mock\.patch', 'Mock Patch Context Manager', 'ERROR'),
            
            # Pytest patterns
            (r'monkeypatch\.|mocker\.', 'Pytest Mock Usage', 'ERROR'),
            (r'pytest\.fixture.*mock', 'Pytest Mock Fixture', 'ERROR'),
            (r'@pytest\.fixture.*mocker', 'Pytest Mocker Fixture', 'ERROR'),
            
            # Variable assignment patterns
            (r'\bmock\s*=\s*Mock\s*\(', 'Mock Variable Assignment', 'ERROR'),
            (r'\bmocked_\w+\s*=', 'Mocked Variable Pattern', 'WARNING'),
            
            # Spec and configuration patterns
            (r'spec\s*=.*Mock', 'Mock Spec Configuration', 'ERROR'),
            (r'spec_set\s*=', 'Mock Spec Set Configuration', 'ERROR'),
            (r'wraps\s*=', 'Mock Wraps Configuration', 'WARNING'),
            
            # Common mock variable names
            (r'\bmock_\w+\s*=', 'Mock Variable Name Pattern', 'WARNING'),
        ]
    
    def scan_file(self, file_path: Path) -> List[MockViolation]:
        """Scan a single file for mock violations."""
        violations = []
        service = self._get_service_name(str(file_path))
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    if not line_stripped or line_stripped.startswith('#'):
                        continue
                        
                    for pattern, violation_type, severity in self.mock_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            violations.append(MockViolation(
                                file_path=str(file_path),
                                line_number=line_num,
                                violation_type=violation_type,
                                code_snippet=line_stripped[:100],
                                service=service,
                                severity=severity
                            ))
                            
        except Exception as e:
            print(f"Warning: Could not scan {file_path}: {e}")
            
        return violations
    
    def _get_service_name(self, file_path: str) -> str:
        """Determine service name from file path."""
        if '/auth_service/' in file_path:
            return 'auth_service'
        elif '/analytics_service/' in file_path:
            return 'analytics_service'
        elif '/netra_backend/' in file_path:
            return 'netra_backend'
        elif '/frontend/' in file_path:
            return 'frontend'
        elif '/dev_launcher/' in file_path:
            return 'dev_launcher'
        else:
            return 'tests'


class ViolationScanner:
    """Main scanner for mock policy violations."""
    
    def __init__(self):
        self.detector = ComprehensiveMockDetector()
        self.project_root = Path(__file__).resolve().parent
        
    def get_test_directories(self, service_filter: str = None) -> List[Path]:
        """Get list of test directories to scan."""
        all_dirs = [
            self.project_root / 'auth_service' / 'tests',
            self.project_root / 'analytics_service' / 'tests',
            self.project_root / 'netra_backend' / 'tests',
            self.project_root / 'tests',
            self.project_root / 'dev_launcher' / 'tests',
        ]
        
        if service_filter:
            return [d for d in all_dirs if service_filter in str(d) and d.exists()]
        else:
            return [d for d in all_dirs if d.exists()]
    
    def scan_all_violations(self, service_filter: str = None) -> Dict[str, List[MockViolation]]:
        """Scan all test directories for violations."""
        all_violations = defaultdict(list)
        test_dirs = self.get_test_directories(service_filter)
        
        for test_dir in test_dirs:
            for py_file in test_dir.rglob('*.py'):
                # Skip the violation checker itself
                if py_file.name in ['test_mock_policy_violations.py', 'check_violations.py']:
                    continue
                    
                violations = self.detector.scan_file(py_file)
                if violations:
                    service = violations[0].service
                    all_violations[service].extend(violations)
        
        return dict(all_violations)
    
    def generate_report(self, violations: Dict[str, List[MockViolation]], 
                       show_details: bool = True) -> str:
        """Generate comprehensive violation report."""
        if not violations:
            return " PASS:  No mock policy violations found!"
        
        total_violations = sum(len(v) for v in violations.values())
        error_violations = sum(len([viol for viol in v if viol.severity == 'ERROR']) 
                             for v in violations.values())
        
        report = []
        report.append("=" * 80)
        report.append("MOCK POLICY VIOLATION REPORT")
        report.append("=" * 80)
        report.append(f"Total Violations: {total_violations}")
        report.append(f"Error Violations: {error_violations}")
        report.append(f"Services Affected: {len(violations)}")
        report.append("")
        
        for service, service_violations in violations.items():
            errors = [v for v in service_violations if v.severity == 'ERROR']
            warnings = [v for v in service_violations if v.severity == 'WARNING']
            
            report.append(f"{service.upper()} - {len(service_violations)} violations")
            report.append(f"  Errors: {len(errors)}, Warnings: {len(warnings)}")
            
            if show_details:
                # Group by violation type
                by_type = defaultdict(list)
                for v in service_violations:
                    by_type[v.violation_type].append(v)
                
                for vtype, vlist in by_type.items():
                    report.append(f"    {vtype}: {len(vlist)} occurrences")
                    # Show first 3 examples
                    for v in vlist[:3]:
                        short_path = v.file_path.split('/netra-apex/')[-1]
                        report.append(f"      [U+2022] {short_path}:{v.line_number}")
                    if len(vlist) > 3:
                        report.append(f"      ... and {len(vlist) - 3} more")
            
            report.append("")
        
        report.append("REQUIRED ACTIONS:")
        report.append("1. Replace ALL mocks with real service tests")
        report.append("2. Use IsolatedEnvironment for test isolation") 
        report.append("3. Use docker-compose for service dependencies")
        report.append("4. Implement real WebSocket/database connections")
        report.append("=" * 80)
        
        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Check for mock policy violations across Netra Apex platform"
    )
    parser.add_argument(
        '--service', 
        help='Filter by specific service (auth_service, analytics_service, netra_backend, tests)'
    )
    parser.add_argument(
        '--fail-on-violations', 
        action='store_true',
        help='Exit with code 1 if violations are found'
    )
    parser.add_argument(
        '--max-violations', 
        type=int, 
        default=0,
        help='Maximum number of violations allowed (default: 0)'
    )
    parser.add_argument(
        '--show-details', 
        action='store_true', 
        default=True,
        help='Show detailed violation information'
    )
    parser.add_argument(
        '--errors-only', 
        action='store_true',
        help='Only report ERROR severity violations'
    )
    parser.add_argument(
        '--output-format', 
        choices=['text', 'json'],
        default='text',
        help='Output format (text or json)'
    )
    
    args = parser.parse_args()
    
    try:
        scanner = ViolationScanner()
        violations = scanner.scan_all_violations(args.service)
        
        # Filter by severity if requested
        if args.errors_only:
            filtered_violations = {}
            for service, service_violations in violations.items():
                errors = [v for v in service_violations if v.severity == 'ERROR']
                if errors:
                    filtered_violations[service] = errors
            violations = filtered_violations
        
        # Generate report
        if args.output_format == 'json':
            import json
            json_data = {
                'total_violations': sum(len(v) for v in violations.values()),
                'services': {
                    service: [
                        {
                            'file': v.file_path,
                            'line': v.line_number,
                            'type': v.violation_type,
                            'snippet': v.code_snippet,
                            'severity': v.severity
                        }
                        for v in service_violations
                    ]
                    for service, service_violations in violations.items()
                }
            }
            print(json.dumps(json_data, indent=2))
        else:
            report = scanner.generate_report(violations, args.show_details)
            print(report)
        
        # Check if we should fail
        total_violations = sum(len(v) for v in violations.values())
        
        if args.fail_on_violations and total_violations > args.max_violations:
            print(f"\n FAIL:  FAILURE: Found {total_violations} violations (max allowed: {args.max_violations})")
            sys.exit(1)
        elif total_violations > 0:
            print(f"\n WARNING: [U+FE0F]  WARNING: Found {total_violations} violations")
        else:
            print("\n PASS:  SUCCESS: No violations found!")
            
        sys.exit(0)
        
    except Exception as e:
        print(f"ERROR: Script failed with exception: {e}")
        sys.exit(2)


if __name__ == '__main__':
    main()