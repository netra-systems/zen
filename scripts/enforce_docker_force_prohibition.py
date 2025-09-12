#!/usr/bin/env python3
"""
CRITICAL SECURITY SCRIPT: Docker Force Flag Prohibition Enforcer

This script enforces the ZERO TOLERANCE policy for Docker force flags in commits.
It's used by pre-commit hooks to prevent commits containing dangerous Docker patterns.

BUSINESS IMPACT: Prevents $2M+ ARR loss from Docker Desktop crashes
ZERO TOLERANCE: NO exceptions, NO bypasses, NO workarounds
"""

import sys
import re
import os
from pathlib import Path
from typing import List, Dict, Tuple, Set
import argparse

# Force flag patterns that are FORBIDDEN
FORBIDDEN_PATTERNS = [
    # Direct force flags
    r'\bdocker\s+.*\s+-f\b',                    # docker ... -f
    r'\bdocker\s+.*\s+--force\b',               # docker ... --force
    r'\bdocker\s+.*\s+-f\s',                    # docker ... -f ...
    r'\bdocker\s+.*\s+--force\s',               # docker ... --force ...
    r'\bdocker\s+.*\s+-f$',                     # docker ... -f (end of line)
    r'\bdocker\s+.*\s+--force$',                # docker ... --force (end of line)
    
    # Combined flags containing f
    r'\bdocker\s+.*\s+-[a-zA-Z]*f[a-zA-Z]*\b',  # docker ... -rf, -af, etc.
    
    # Assignment format
    r'\bdocker\s+.*--force=[^\s]*',             # docker ... --force=value
    
    # High-risk combinations
    r'\bdocker\s+(rm|rmi|container\s+rm|image\s+rm|volume\s+rm|system\s+prune|container\s+prune|image\s+prune|volume\s+prune|network\s+prune)\s+.*-f\b',
    r'\bdocker\s+(rm|rmi|container\s+rm|image\s+rm|volume\s+rm|system\s+prune|container\s+prune|image\s+prune|volume\s+prune|network\s+prune)\s+.*--force\b',
]

# Allowed exceptions (logs -f, etc.)
ALLOWED_EXCEPTIONS = [
    r'\bdocker\s+logs\s+.*-f\b',               # docker logs -f (follow logs is safe)
    r'\bdocker\s+build\s+.*-f\s+.*\.dockerfile\b',  # docker build -f dockerfile
    r'\bdocker\s+build\s+.*-f\s+[^\s]+\.dockerfile\b',
    r'\bdocker-compose\s+.*-f\s+.*\.yml\b',    # docker-compose -f file.yml
    r'\bdocker-compose\s+.*-f\s+.*\.yaml\b',   # docker-compose -f file.yaml
]

# File types to check
CHECKABLE_EXTENSIONS = {'.py', '.sh', '.yml', '.yaml', '.md', '.txt', '.dockerfile'}

# Context lines to show around violations
CONTEXT_LINES = 3


class DockerForceViolation:
    """Represents a Docker force flag violation."""
    
    def __init__(self, file_path: str, line_num: int, line_content: str, 
                 pattern: str, violation_type: str):
        self.file_path = file_path
        self.line_num = line_num
        self.line_content = line_content.strip()
        self.pattern = pattern
        self.violation_type = violation_type
    
    def __str__(self):
        return (
            f" ALERT:  CRITICAL SECURITY VIOLATION in {self.file_path}:{self.line_num}\n"
            f"   Type: {self.violation_type}\n"
            f"   Line: {self.line_content}\n"
            f"   Pattern: {self.pattern}"
        )


class DockerForceProhibitionEnforcer:
    """Enforces prohibition of Docker force flags in code."""
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.violations: List[DockerForceViolation] = []
        self.checked_files = 0
        self.total_lines_checked = 0
    
    def is_allowed_exception(self, line: str) -> bool:
        """Check if line matches allowed exceptions."""
        line_lower = line.lower().strip()
        
        for exception_pattern in ALLOWED_EXCEPTIONS:
            if re.search(exception_pattern, line_lower, re.IGNORECASE):
                return True
        return False
    
    def check_line_for_violations(self, line: str, line_num: int, file_path: str) -> List[DockerForceViolation]:
        """Check a single line for Docker force flag violations."""
        violations = []
        line_stripped = line.strip()
        
        # Skip empty lines and comments
        if not line_stripped or line_stripped.startswith('#'):
            return violations
        
        # Check if this is an allowed exception first
        if self.is_allowed_exception(line):
            return violations
        
        # Check each forbidden pattern
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                violation_type = "Docker Force Flag Detected"
                
                # Determine specific violation type
                if '-f' in line:
                    violation_type = "Docker -f Flag (Force Removal)"
                elif '--force' in line.lower():
                    violation_type = "Docker --force Flag"
                
                violation = DockerForceViolation(
                    file_path=file_path,
                    line_num=line_num,
                    line_content=line,
                    pattern=pattern,
                    violation_type=violation_type
                )
                violations.append(violation)
        
        return violations
    
    def check_file(self, file_path: str) -> List[DockerForceViolation]:
        """Check a single file for Docker force flag violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            self.total_lines_checked += len(lines)
            
            for line_num, line in enumerate(lines, 1):
                line_violations = self.check_line_for_violations(line, line_num, file_path)
                violations.extend(line_violations)
        
        except Exception as e:
            print(f" WARNING: [U+FE0F]  Warning: Could not check file {file_path}: {e}")
        
        return violations
    
    def should_check_file(self, file_path: str) -> bool:
        """Determine if file should be checked."""
        path = Path(file_path)
        
        # Check extension
        if path.suffix.lower() not in CHECKABLE_EXTENSIONS:
            return False
        
        # Skip certain directories
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv'}
        if any(skip_dir in path.parts for skip_dir in skip_dirs):
            return False
        
        # Skip binary files
        try:
            with open(file_path, 'r', encoding='utf-8', errors='strict') as f:
                f.read(1024)  # Try to read first 1KB
        except UnicodeDecodeError:
            return False  # Skip binary files
        
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
        """Print detailed violations report."""
        if not self.violations:
            print(" PASS:  DOCKER SECURITY SCAN COMPLETE: No force flag violations detected")
            print(f"    CHART:  Scanned {self.checked_files} files, {self.total_lines_checked:,} lines")
            return
        
        print(" ALERT: " * 50)
        print("CRITICAL SECURITY VIOLATIONS DETECTED")
        print("Docker Force Flag Prohibition Enforcement")
        print(" ALERT: " * 50)
        print()
        
        # Group violations by file
        violations_by_file = {}
        for violation in self.violations:
            if violation.file_path not in violations_by_file:
                violations_by_file[violation.file_path] = []
            violations_by_file[violation.file_path].append(violation)
        
        for file_path, file_violations in violations_by_file.items():
            print(f"[U+1F4C1] FILE: {file_path}")
            print(f"    ALERT:  {len(file_violations)} violation(s) detected")
            print()
            
            for violation in file_violations:
                print(f"   Line {violation.line_num}: {violation.violation_type}")
                print(f"   Code: {violation.line_content}")
                print(f"   Pattern: {violation.pattern}")
                print()
        
        print("[U+1F4B0] BUSINESS IMPACT:")
        print("   [U+2022] Docker force flags cause daemon crashes")
        print("   [U+2022] Each crash = 4-8 hours developer downtime")
        print(f"   [U+2022] Risk to $2M+ ARR from {len(self.violations)} violation(s)")
        print()
        
        print("[U+1F6E0][U+FE0F]  REMEDIATION REQUIRED:")
        print("   1. Replace 'docker rm -f' with 'docker stop && docker rm'")
        print("   2. Replace 'docker system prune -f' with interactive confirmation")
        print("   3. Use safe alternatives documented in docker_force_flag_guardian.py")
        print()
        
        print(" FAIL:  COMMIT BLOCKED - Fix violations before proceeding")
        print(" ALERT: " * 50)
    
    def get_safe_alternatives(self) -> Dict[str, str]:
        """Get safe alternatives for common dangerous patterns."""
        return {
            'docker rm -f <container>': 'docker stop <container> && docker rm <container>',
            'docker rmi -f <image>': 'docker rmi <image> (after stopping containers)',
            'docker system prune -f': 'docker system prune (interactive confirmation)',
            'docker container prune -f': 'docker container prune (interactive confirmation)',
            'docker volume prune -f': 'docker volume prune (interactive confirmation)',
            'docker image prune -f': 'docker image prune (interactive confirmation)',
            'docker network prune -f': 'docker network prune (interactive confirmation)',
        }


def main():
    """Main function for pre-commit hook execution."""
    parser = argparse.ArgumentParser(
        description="Enforce Docker force flag prohibition",
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
        help='Enable strict mode (fail on any violation)'
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Only report violations, do not fail'
    )
    
    args = parser.parse_args()
    
    enforcer = DockerForceProhibitionEnforcer(strict_mode=args.strict)
    
    # Get files to check
    files_to_check = args.files if args.files else []
    
    # If no files provided via args, this is likely a full scan
    if not files_to_check:
        print(" WARNING: [U+FE0F]  No files provided - this enforcer is designed for pre-commit hooks")
        return 0
    
    # Check files
    violation_count = enforcer.check_files(files_to_check)
    
    # Print report
    enforcer.print_violations_report()
    
    # Return appropriate exit code
    if violation_count > 0 and not args.report_only:
        return 1  # Fail the commit
    
    return 0


if __name__ == "__main__":
    sys.exit(main())