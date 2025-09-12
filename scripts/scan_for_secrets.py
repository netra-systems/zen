#!/usr/bin/env python
"""
Comprehensive secrets scanner for the Netra codebase.
Scans for hardcoded secrets, API keys, passwords, and other sensitive data.
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Pattern
from dataclasses import dataclass
import hashlib


@dataclass
class SecretPattern:
    """Pattern for detecting potential secrets."""
    name: str
    pattern: Pattern
    severity: str  # critical, high, medium, low
    description: str


@dataclass 
class Finding:
    """A potential secret finding."""
    file_path: str
    line_number: int
    line_content: str
    pattern_name: str
    severity: str
    description: str


class SecretsScanner:
    """Scans codebase for hardcoded secrets and sensitive data."""
    
    def __init__(self):
        self.patterns = self._initialize_patterns()
        self.findings: List[Finding] = []
        self.excluded_paths = self._get_excluded_paths()
        
    def _initialize_patterns(self) -> List[SecretPattern]:
        """Initialize secret detection patterns."""
        return [
            # Critical: Hardcoded passwords/secrets
            SecretPattern(
                name="Hardcoded Password",
                pattern=re.compile(r'password\s*=\s*["\'](?!your-|test-|example-|placeholder)[^"\']{8,}["\']', re.IGNORECASE),
                severity="critical",
                description="Hardcoded password detected"
            ),
            SecretPattern(
                name="JWT Secret",
                pattern=re.compile(r'JWT_SECRET(?:_KEY)?\s*=\s*["\'][^"\']{16,}["\']', re.IGNORECASE),
                severity="critical",
                description="Hardcoded JWT secret detected"
            ),
            SecretPattern(
                name="API Key",
                pattern=re.compile(r'(?:api[_-]?key|apikey)\s*=\s*["\'][A-Za-z0-9_\-]{20,}["\']', re.IGNORECASE),
                severity="critical",
                description="Hardcoded API key detected"
            ),
            
            # High: Long alphanumeric strings that could be secrets
            SecretPattern(
                name="Long Alphanumeric String",
                pattern=re.compile(r'["\'][A-Za-z0-9]{32,}["\']'),
                severity="high",
                description="Long alphanumeric string that could be a secret"
            ),
            SecretPattern(
                name="Private Key",
                pattern=re.compile(r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY'),
                severity="critical",
                description="Private key detected"
            ),
            
            # Google OAuth specific
            SecretPattern(
                name="Google Client Secret",
                pattern=re.compile(r'GOOGLE_(?:OAUTH_)?CLIENT_SECRET\s*=\s*["\'][^"\']+["\']'),
                severity="high",
                description="Google OAuth client secret detected"
            ),
            
            # Database credentials
            SecretPattern(
                name="Database URL with Password",
                pattern=re.compile(r'(?:postgresql|mysql|mongodb)://[^:]+:[^@]+@[^/]+'),
                severity="high",
                description="Database URL with embedded credentials"
            ),
            
            # Service account keys
            SecretPattern(
                name="Service Account Key",
                pattern=re.compile(r'"private_key"\s*:\s*"[^"]+-----BEGIN'),
                severity="critical",
                description="Service account private key detected"
            ),
            
            # Base64 encoded secrets
            SecretPattern(
                name="Base64 Encoded Secret",
                pattern=re.compile(r'(?:secret|password|key|token)\s*=\s*["\'][A-Za-z0-9+/]{40,}={0,2}["\']', re.IGNORECASE),
                severity="medium",
                description="Potential base64 encoded secret"
            ),
            
            # Redis password specifically
            SecretPattern(
                name="Redis Password",
                pattern=re.compile(r'["\']cpmdn7pVpsJSK2mb7lUTj2VaQhSC1L3S["\']'),
                severity="critical",
                description="Hardcoded Redis password detected"
            ),
            
            # Environment variable assignments that look like real values
            SecretPattern(
                name="Environment Variable with Value",
                pattern=re.compile(r'os\.environ\[[\'"](.*?)[\'"]\]\s*=\s*[\'"](?!test|example|placeholder|your-)[^\'"]{10,}[\'"]'),
                severity="high",
                description="Environment variable being set with potential secret"
            )
        ]
    
    def _get_excluded_paths(self) -> List[str]:
        """Get list of paths to exclude from scanning."""
        return [
            '.git',
            'node_modules',
            '__pycache__',
            '.pytest_cache',
            '.mypy_cache',
            'venv',
            'env',
            '.next',
            'dist',
            'build',
            'test_reports',
            'htmlcov',
            '.coverage',
            'SPEC/generated',  # Generated files
            '*.min.js',
            '*.min.css'
        ]
    
    def _should_scan_file(self, file_path: Path) -> bool:
        """Check if file should be scanned."""
        # Skip excluded directories
        for excluded in self.excluded_paths:
            if excluded in str(file_path):
                return False
        
        # Only scan text files
        extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yaml', '.yml', 
                     '.env', '.config', '.conf', '.ini', '.properties', '.xml']
        
        return file_path.suffix in extensions or file_path.name.startswith('.env')
    
    def scan_file(self, file_path: Path) -> List[Finding]:
        """Scan a single file for secrets."""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    # Skip comments
                    if line.strip().startswith('#') or line.strip().startswith('//'):
                        continue
                    
                    for pattern in self.patterns:
                        if pattern.pattern.search(line):
                            # Skip if it's a template/example value
                            if any(skip in line.lower() for skip in 
                                  ['your-', 'example', 'placeholder', 'template', 'mock', 'test_']):
                                continue
                            
                            findings.append(Finding(
                                file_path=str(file_path),
                                line_number=line_num,
                                line_content=line.strip()[:200],  # Truncate long lines
                                pattern_name=pattern.name,
                                severity=pattern.severity,
                                description=pattern.description
                            ))
        except Exception as e:
            print(f"Error scanning {file_path}: {e}", file=sys.stderr)
        
        return findings
    
    def scan_directory(self, directory: Path) -> None:
        """Scan directory recursively for secrets."""
        for file_path in directory.rglob('*'):
            if file_path.is_file() and self._should_scan_file(file_path):
                file_findings = self.scan_file(file_path)
                self.findings.extend(file_findings)
    
    def generate_report(self) -> Dict:
        """Generate a report of findings."""
        # Group by severity
        by_severity = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': []
        }
        
        for finding in self.findings:
            by_severity[finding.severity].append({
                'file': finding.file_path,
                'line': finding.line_number,
                'pattern': finding.pattern_name,
                'description': finding.description,
                'content': finding.line_content
            })
        
        return {
            'summary': {
                'total_findings': len(self.findings),
                'critical': len(by_severity['critical']),
                'high': len(by_severity['high']),
                'medium': len(by_severity['medium']),
                'low': len(by_severity['low'])
            },
            'findings': by_severity
        }
    
    def print_report(self) -> None:
        """Print a formatted report."""
        report = self.generate_report()
        
        print("\n" + "="*80)
        print("SECRETS SCAN REPORT")
        print("="*80)
        
        print(f"\nTotal findings: {report['summary']['total_findings']}")
        print(f"  Critical: {report['summary']['critical']}")
        print(f"  High:     {report['summary']['high']}")
        print(f"  Medium:   {report['summary']['medium']}")
        print(f"  Low:      {report['summary']['low']}")
        
        # Print critical findings first
        if report['findings']['critical']:
            print("\n" + "="*80)
            print("CRITICAL FINDINGS (Immediate action required)")
            print("="*80)
            for finding in report['findings']['critical']:
                print(f"\n[CRITICAL] {finding['pattern']}: {finding['description']}")
                print(f"  File: {finding['file']}:{finding['line']}")
                print(f"  Content: {finding['content'][:100]}...")
        
        # Print high severity findings
        if report['findings']['high']:
            print("\n" + "="*80)
            print("HIGH SEVERITY FINDINGS")
            print("="*80)
            for finding in report['findings']['high']:
                print(f"\n[HIGH] {finding['pattern']}: {finding['description']}")
                print(f"  File: {finding['file']}:{finding['line']}")
                print(f"  Content: {finding['content'][:100]}...")
        
        # Summary for medium/low
        if report['findings']['medium'] or report['findings']['low']:
            print("\n" + "="*80)
            print("OTHER FINDINGS")
            print("="*80)
            print(f"Medium severity: {report['summary']['medium']} findings")
            print(f"Low severity: {report['summary']['low']} findings")
            print("Run with --verbose to see all findings")
    
    def save_report(self, output_path: Path) -> None:
        """Save report to JSON file."""
        report = self.generate_report()
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {output_path}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scan codebase for secrets')
    parser.add_argument('--path', type=str, default='.', 
                       help='Path to scan (default: current directory)')
    parser.add_argument('--output', type=str, 
                       help='Output JSON report to file')
    parser.add_argument('--fail-on-critical', action='store_true',
                       help='Exit with error code if critical findings')
    parser.add_argument('--verbose', action='store_true',
                       help='Show all findings including medium/low severity')
    
    args = parser.parse_args()
    
    # Create scanner and run scan
    scanner = SecretsScanner()
    scan_path = Path(args.path).resolve()
    
    print(f"Scanning {scan_path} for secrets...")
    scanner.scan_directory(scan_path)
    
    # Print report
    scanner.print_report()
    
    # Save report if requested
    if args.output:
        scanner.save_report(Path(args.output))
    
    # Check for critical findings
    report = scanner.generate_report()
    if args.fail_on_critical and report['summary']['critical'] > 0:
        print("\n FAIL:  Critical secrets found! Exiting with error.")
        sys.exit(1)
    elif report['summary']['critical'] > 0:
        print("\n WARNING: [U+FE0F]  Critical secrets found! Please remediate immediately.")
    else:
        print("\n PASS:  No critical secrets found.")


if __name__ == '__main__':
    main()