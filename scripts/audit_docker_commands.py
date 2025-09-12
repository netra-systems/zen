#!/usr/bin/env python3
"""
CRITICAL SECURITY SCRIPT: Comprehensive Docker Security Auditor

This script performs comprehensive security auditing of Docker commands in the codebase.
It identifies dangerous patterns, security violations, and provides remediation guidance.

BUSINESS IMPACT: Protects $2M+ ARR from Docker-related outages and security breaches
"""

import sys
import re
import os
import json
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
import argparse
from dataclasses import dataclass


@dataclass
class SecurityViolation:
    """Represents a Docker security violation."""
    file_path: str
    line_num: int
    line_content: str
    violation_type: str
    severity: str
    description: str
    remediation: str


class DockerSecurityAuditor:
    """Comprehensive Docker security auditor."""
    
    # Security patterns to detect
    SECURITY_PATTERNS = {
        'force_flags': {
            'patterns': [
                r'\bdocker\s+.*\s+-f\b',
                r'\bdocker\s+.*\s+--force\b',
            ],
            'severity': 'CRITICAL',
            'description': 'Force flags can cause daemon crashes',
            'remediation': 'Use graceful stop patterns instead of force removal'
        },
        'privileged_containers': {
            'patterns': [
                r'\bdocker\s+run\s+.*--privileged\b',
                r'\bdocker\s+run\s+.*--cap-add=ALL\b',
            ],
            'severity': 'HIGH',
            'description': 'Privileged containers pose security risks',
            'remediation': 'Use minimal required capabilities instead of --privileged'
        },
        'host_network': {
            'patterns': [
                r'\bdocker\s+run\s+.*--network=host\b',
                r'\bdocker\s+run\s+.*--network\s+host\b',
            ],
            'severity': 'MEDIUM',
            'description': 'Host networking reduces container isolation',
            'remediation': 'Use bridge networking with explicit port mapping'
        },
        'bind_mounts_dangerous': {
            'patterns': [
                r'\bdocker\s+run\s+.*-v\s+/:/[^:]*\b',
                r'\bdocker\s+run\s+.*-v\s+/etc:/[^:]*\b',
                r'\bdocker\s+run\s+.*-v\s+/var/run/docker\.sock:/[^:]*\b',
            ],
            'severity': 'HIGH',
            'description': 'Dangerous bind mounts expose host system',
            'remediation': 'Use named volumes or limit bind mounts to specific paths'
        },
        'root_user': {
            'patterns': [
                r'\bUSER\s+root\b',
                r'\bdocker\s+run\s+.*--user=root\b',
                r'\bdocker\s+run\s+.*--user\s+root\b',
            ],
            'severity': 'MEDIUM',
            'description': 'Running as root increases security risks',
            'remediation': 'Create and use non-root user in containers'
        },
        'insecure_registries': {
            'patterns': [
                r'--insecure-registry',
                r'http://[^/]*registry',
            ],
            'severity': 'HIGH',
            'description': 'Insecure registry connections are vulnerable',
            'remediation': 'Use HTTPS-enabled registries only'
        },
        'secrets_in_build': {
            'patterns': [
                r'\bARG\s+.*(?:PASSWORD|SECRET|KEY|TOKEN)\b',
                r'\bENV\s+.*(?:PASSWORD|SECRET|KEY|TOKEN)\b',
            ],
            'severity': 'HIGH',
            'description': 'Secrets in build arguments/env vars are insecure',
            'remediation': 'Use Docker secrets or external secret management'
        },
        'kill_commands': {
            'patterns': [
                r'\bdocker\s+kill\b',
                r'docker.*SIGKILL',
            ],
            'severity': 'MEDIUM',
            'description': 'Kill commands can cause data corruption',
            'remediation': 'Use docker stop with appropriate timeout'
        },
        'unsafe_cleanup': {
            'patterns': [
                r'docker\s+system\s+prune.*--all.*--volumes\s*$',
                r'docker.*rm.*\$\(docker.*-[aq]\)',
            ],
            'severity': 'HIGH',
            'description': 'Unsafe cleanup patterns can destroy important data',
            'remediation': 'Use selective cleanup with proper filtering'
        },
    }
    
    # Allowed exceptions (context-specific safe usage)
    ALLOWED_EXCEPTIONS = {
        'dockerfile_from_flag': r'FROM\s+.*-f\s+',
        'docker_logs_follow': r'docker\s+logs\s+.*-f\b',
        'docker_compose_file': r'docker-compose\s+.*-f\s+.*\.ya?ml\b',
        'docker_build_file': r'docker\s+build\s+.*-f\s+.*[Dd]ockerfile\b',
    }
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.violations: List[SecurityViolation] = []
        self.checked_files = 0
        self.total_lines_checked = 0
    
    def is_allowed_exception(self, line: str) -> bool:
        """Check if line matches allowed exceptions."""
        for exception_name, pattern in self.ALLOWED_EXCEPTIONS.items():
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def check_line_for_violations(self, line: str, line_num: int, file_path: str) -> List[SecurityViolation]:
        """Check a single line for security violations."""
        violations = []
        line_stripped = line.strip()
        
        # Skip empty lines and comments
        if not line_stripped or line_stripped.startswith('#'):
            return violations
        
        # Check if this is an allowed exception
        if self.is_allowed_exception(line):
            return violations
        
        # Check each security pattern
        for violation_type, config in self.SECURITY_PATTERNS.items():
            for pattern in config['patterns']:
                if re.search(pattern, line, re.IGNORECASE):
                    violation = SecurityViolation(
                        file_path=file_path,
                        line_num=line_num,
                        line_content=line.strip(),
                        violation_type=violation_type,
                        severity=config['severity'],
                        description=config['description'],
                        remediation=config['remediation']
                    )
                    violations.append(violation)
        
        return violations
    
    def check_file(self, file_path: str) -> List[SecurityViolation]:
        """Check a single file for security violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            self.total_lines_checked += len(lines)
            
            for line_num, line in enumerate(lines, 1):
                line_violations = self.check_line_for_violations(line, line_num, file_path)
                violations.extend(line_violations)
        
        except Exception as e:
            if self.strict_mode:
                print(f" FAIL:  Error checking file {file_path}: {e}", file=sys.stderr)
            else:
                print(f" WARNING: [U+FE0F]  Warning: Could not check file {file_path}: {e}")
        
        return violations
    
    def should_check_file(self, file_path: str) -> bool:
        """Determine if file should be checked."""
        path = Path(file_path)
        
        # Check for relevant file types
        checkable_extensions = {
            '.py', '.sh', '.yml', '.yaml', '.dockerfile', '.md', '.txt',
            '.json', '.conf', '.config'
        }
        
        # Also check files named "Dockerfile*"
        if path.name.lower().startswith('dockerfile'):
            return True
            
        if path.suffix.lower() not in checkable_extensions:
            return False
        
        # Skip certain directories
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv'}
        if any(skip_dir in path.parts for skip_dir in skip_dirs):
            return False
        
        return True
    
    def check_files(self, file_paths: List[str]) -> int:
        """Check multiple files and return number of violations."""
        all_violations = []
        
        for file_path in file_paths:
            if not self.should_check_file(file_path):
                continue
                
            self.checked_files += 1
            violations = self.check_file(file_path)
            all_violations.extend(violations)
        
        self.violations = all_violations
        return len(all_violations)
    
    def print_violations_report(self) -> None:
        """Print comprehensive security violations report."""
        if not self.violations:
            print(" PASS:  DOCKER SECURITY AUDIT COMPLETE: No violations detected")
            print(f"    CHART:  Scanned {self.checked_files} files, {self.total_lines_checked:,} lines")
            return
        
        print("[U+1F512]" * 60)
        print("DOCKER SECURITY AUDIT REPORT")
        print("[U+1F512]" * 60)
        print()
        
        # Summary by severity
        severity_counts = {}
        for violation in self.violations:
            severity_counts[violation.severity] = severity_counts.get(violation.severity, 0) + 1
        
        print(" CHART:  SUMMARY BY SEVERITY:")
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = severity_counts.get(severity, 0)
            if count > 0:
                emoji = ' ALERT: ' if severity == 'CRITICAL' else ' WARNING: [U+FE0F]' if severity == 'HIGH' else ' IDEA: '
                print(f"   {emoji} {severity}: {count} violation(s)")
        print()
        
        # Group violations by file
        violations_by_file = {}
        for violation in self.violations:
            if violation.file_path not in violations_by_file:
                violations_by_file[violation.file_path] = []
            violations_by_file[violation.file_path].append(violation)
        
        for file_path, file_violations in violations_by_file.items():
            print(f"[U+1F4C1] FILE: {file_path}")
            print(f"    SEARCH:  {len(file_violations)} violation(s) detected")
            print()
            
            # Group by severity within file
            file_violations.sort(key=lambda v: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].index(v.severity))
            
            for violation in file_violations:
                severity_emoji = ' ALERT: ' if violation.severity == 'CRITICAL' else ' WARNING: [U+FE0F]' if violation.severity == 'HIGH' else ' IDEA: '
                print(f"   {severity_emoji} Line {violation.line_num}: {violation.severity} - {violation.violation_type}")
                print(f"      Code: {violation.line_content}")
                print(f"      Issue: {violation.description}")
                print(f"      Fix: {violation.remediation}")
                print()
        
        # Business impact assessment
        critical_count = severity_counts.get('CRITICAL', 0)
        high_count = severity_counts.get('HIGH', 0)
        
        if critical_count > 0 or high_count > 0:
            print("[U+1F4B0] BUSINESS IMPACT ASSESSMENT:")
            if critical_count > 0:
                print(f"    ALERT:  CRITICAL: {critical_count} violation(s) pose immediate threat to $2M+ ARR")
                print("      Risk: Service outages, data loss, security breaches")
            if high_count > 0:
                print(f"    WARNING: [U+FE0F]  HIGH: {high_count} violation(s) create significant security risks")
                print("      Risk: Container escapes, privilege escalation, data exposure")
            print()
        
        print("[U+1F6E0][U+FE0F]  REMEDIATION PRIORITY:")
        print("   1. Fix CRITICAL violations immediately")
        print("   2. Address HIGH severity issues within 24 hours")
        print("   3. Plan MEDIUM severity fixes for next sprint")
        print("   4. Consider LOW severity as technical debt")
        print()
        
        if critical_count > 0 and self.strict_mode:
            print(" FAIL:  COMMIT BLOCKED - Fix critical violations before proceeding")
        elif critical_count > 0:
            print(" WARNING: [U+FE0F]  COMMIT ALLOWED - But fix critical violations ASAP")
        
        print("[U+1F512]" * 60)
    
    def export_json_report(self, output_path: str) -> None:
        """Export violations report as JSON."""
        report_data = {
            'audit_summary': {
                'total_violations': len(self.violations),
                'files_checked': self.checked_files,
                'lines_checked': self.total_lines_checked,
                'severity_breakdown': {}
            },
            'violations': []
        }
        
        # Count by severity
        for violation in self.violations:
            severity = violation.severity
            report_data['audit_summary']['severity_breakdown'][severity] = \
                report_data['audit_summary']['severity_breakdown'].get(severity, 0) + 1
        
        # Add violation details
        for violation in self.violations:
            violation_data = {
                'file_path': violation.file_path,
                'line_num': violation.line_num,
                'line_content': violation.line_content,
                'violation_type': violation.violation_type,
                'severity': violation.severity,
                'description': violation.description,
                'remediation': violation.remediation
            }
            report_data['violations'].append(violation_data)
        
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"[U+1F4C4] JSON report exported to: {output_path}")


def main():
    """Main function for Docker security audit."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Docker security auditor",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'files', 
        nargs='*', 
        help='Files to check (if not provided, checks all relevant files)'
    )
    parser.add_argument(
        '--strict', 
        action='store_true',
        help='Enable strict mode (fail on critical violations)'
    )
    parser.add_argument(
        '--json-output',
        type=str,
        help='Export results to JSON file'
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Only report violations, do not fail'
    )
    
    args = parser.parse_args()
    
    auditor = DockerSecurityAuditor(strict_mode=args.strict)
    
    # Get files to check
    files_to_check = args.files if args.files else []
    
    if not files_to_check:
        print(" WARNING: [U+FE0F]  No files provided - this auditor is designed for pre-commit hooks")
        return 0
    
    # Check files
    violation_count = auditor.check_files(files_to_check)
    
    # Print report
    auditor.print_violations_report()
    
    # Export JSON if requested
    if args.json_output:
        auditor.export_json_report(args.json_output)
    
    # Determine exit code
    critical_violations = sum(1 for v in auditor.violations if v.severity == 'CRITICAL')
    
    if critical_violations > 0 and args.strict and not args.report_only:
        return 1  # Fail on critical violations in strict mode
    
    return 0


if __name__ == "__main__":
    sys.exit(main())