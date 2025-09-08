#!/usr/bin/env python3
"""Type Drift Migration Utility

This utility helps migrate from string-based types to strongly-typed identifiers
across the Netra platform to resolve critical type drift issues.

Usage:
    python scripts/type_drift_migration_utility.py --scan
    python scripts/type_drift_migration_utility.py --migrate-context --file path/to/file.py
    python scripts/type_drift_migration_utility.py --validate
"""

import ast
import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class TypeDriftIssue:
    """Represents a type drift issue found in code."""
    file_path: str
    line_number: int
    column: int
    issue_type: str
    description: str
    suggested_fix: str
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"


@dataclass
class MigrationSummary:
    """Summary of migration analysis and results."""
    total_files_scanned: int = 0
    issues_found: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    files_with_issues: Set[str] = None
    
    def __post_init__(self):
        if self.files_with_issues is None:
            self.files_with_issues = set()


class TypeDriftAnalyzer:
    """Analyzes code for type drift patterns and suggests fixes."""
    
    # Patterns that indicate type drift issues
    STRING_ID_PATTERNS = [
        # Function signatures with string IDs
        (r'def\s+\w+\([^)]*(\w*user_id|\w*thread_id|\w*session_id|\w*run_id|\w*request_id|\w*websocket_id|\w*connection_id|\w*agent_id)\s*:\s*str', 
         "CRITICAL", "Function parameter uses string type for ID"),
        
        # Class attributes with string IDs  
        (r'(\w*user_id|\w*thread_id|\w*session_id|\w*run_id|\w*request_id|\w*websocket_id|\w*connection_id|\w*agent_id)\s*:\s*str',
         "CRITICAL", "Class attribute uses string type for ID"),
         
        # Dictionary access patterns (common source of typos)
        (r'\.get\(["\'](\w*user_id|\w*thread_id|\w*session_id|\w*run_id|\w*request_id|\w*websocket_id)["\']',
         "HIGH", "Dictionary access to ID field - prone to typos"),
         
        # String literal ID usage (hardcoded IDs)
        (r'["\'](?:test_|mock_|placeholder_|default_)(?:user|thread|session|run|request|websocket|connection|agent)',
         "HIGH", "Hardcoded test/placeholder ID - should use typed constants"),
    ]
    
    # Authentication patterns
    AUTH_DICT_PATTERNS = [
        (r'return\s*\{[^}]*["\']valid["\'].*\}', "HIGH", "Untyped auth result dictionary"),
        (r'["\']permissions["\']\s*:', "MEDIUM", "Untyped permissions field"),
        (r'["\']token_type["\']\s*:', "MEDIUM", "Untyped token response field"),
    ]
    
    # WebSocket patterns
    WEBSOCKET_PATTERNS = [
        (r'["\'](?:agent_started|agent_thinking|tool_executing|agent_completed)["\']',
         "HIGH", "String literal WebSocket event type - should use enum"),
        (r'websocket.*\{.*["\']event_type["\']', "HIGH", "Untyped WebSocket event"),
    ]
    
    def __init__(self):
        self.issues: List[TypeDriftIssue] = []
    
    def scan_file(self, file_path: str) -> List[TypeDriftIssue]:
        """Scan a single file for type drift issues."""
        issues = []
        
        if not file_path.endswith('.py'):
            return issues
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check all pattern categories
            issues.extend(self._check_patterns(file_path, content, self.STRING_ID_PATTERNS))
            issues.extend(self._check_patterns(file_path, content, self.AUTH_DICT_PATTERNS))  
            issues.extend(self._check_patterns(file_path, content, self.WEBSOCKET_PATTERNS))
            
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
            
        return issues
    
    def _check_patterns(self, file_path: str, content: str, patterns: List[Tuple[str, str, str]]) -> List[TypeDriftIssue]:
        """Check content against a list of regex patterns."""
        issues = []
        lines = content.split('\n')
        
        for pattern, severity, description in patterns:
            regex = re.compile(pattern, re.MULTILINE | re.IGNORECASE)
            
            for match in regex.finditer(content):
                # Find line number
                line_start = content[:match.start()].count('\n')
                column = match.start() - content[:match.start()].rfind('\n') - 1
                
                # Generate suggested fix
                suggested_fix = self._generate_fix_suggestion(match.group(), description)
                
                issues.append(TypeDriftIssue(
                    file_path=file_path,
                    line_number=line_start + 1,
                    column=column,
                    issue_type="TYPE_DRIFT",
                    description=description,
                    suggested_fix=suggested_fix,
                    severity=severity
                ))
        
        return issues
    
    def _generate_fix_suggestion(self, matched_text: str, description: str) -> str:
        """Generate a suggested fix for the matched pattern."""
        
        # ID parameter fixes
        if "Function parameter" in description:
            if "user_id" in matched_text:
                return "Replace 'user_id: str' with 'user_id: UserID' and import from shared.types"
            elif "thread_id" in matched_text:
                return "Replace 'thread_id: str' with 'thread_id: ThreadID' and import from shared.types"
            elif "run_id" in matched_text:
                return "Replace 'run_id: str' with 'run_id: RunID' and import from shared.types"
            elif "request_id" in matched_text:
                return "Replace 'request_id: str' with 'request_id: RequestID' and import from shared.types"
                
        # Class attribute fixes
        elif "Class attribute" in description:
            return "Use NewType identifier from shared.types instead of str"
            
        # Dictionary access fixes
        elif "Dictionary access" in description:
            return "Consider using Pydantic model instead of dict access to prevent typos"
            
        # Auth result fixes
        elif "auth result" in description:
            return "Use AuthValidationResult from shared.types instead of dict"
            
        # WebSocket event fixes
        elif "WebSocket event" in description:
            return "Use WebSocketEventType enum from shared.types instead of string literal"
            
        return "Use strongly-typed alternative from shared.types"
    
    def scan_directory(self, directory: str, exclude_patterns: List[str] = None) -> MigrationSummary:
        """Scan entire directory for type drift issues."""
        if exclude_patterns is None:
            exclude_patterns = ['venv/', '__pycache__/', '.git/', 'node_modules/']
            
        summary = MigrationSummary()
        
        for root, dirs, files in os.walk(directory):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(pattern in os.path.join(root, d) for pattern in exclude_patterns)]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    summary.total_files_scanned += 1
                    
                    issues = self.scan_file(file_path)
                    if issues:
                        summary.files_with_issues.add(file_path)
                        summary.issues_found += len(issues)
                        
                        for issue in issues:
                            if issue.severity == "CRITICAL":
                                summary.critical_issues += 1
                            elif issue.severity == "HIGH":
                                summary.high_issues += 1
                                
                        self.issues.extend(issues)
        
        return summary
    
    def generate_report(self, summary: MigrationSummary) -> str:
        """Generate a comprehensive migration report."""
        report = f"""
TYPE DRIFT MIGRATION ANALYSIS REPORT
=====================================

SUMMARY:
- Files Scanned: {summary.total_files_scanned}
- Total Issues Found: {summary.issues_found}
- Critical Issues: {summary.critical_issues}
- High Priority Issues: {summary.high_issues}
- Files Affected: {len(summary.files_with_issues)}

CRITICAL ISSUES BREAKDOWN:
"""
        
        # Group issues by file and severity
        critical_issues = [i for i in self.issues if i.severity == "CRITICAL"]
        high_issues = [i for i in self.issues if i.severity == "HIGH"]
        
        if critical_issues:
            report += "\nCRITICAL ISSUES (Immediate Action Required):\n"
            for issue in critical_issues[:20]:  # Limit output
                report += f"  {issue.file_path}:{issue.line_number} - {issue.description}\n"
                report += f"    Fix: {issue.suggested_fix}\n\n"
        
        if high_issues:
            report += "\nHIGH PRIORITY ISSUES:\n"
            for issue in high_issues[:15]:  # Limit output  
                report += f"  {issue.file_path}:{issue.line_number} - {issue.description}\n"
                report += f"    Fix: {issue.suggested_fix}\n\n"
        
        report += f"""
TOP AFFECTED FILES:
"""
        # Count issues per file
        file_issue_count = {}
        for issue in self.issues:
            file_issue_count[issue.file_path] = file_issue_count.get(issue.file_path, 0) + 1
        
        # Sort by issue count
        sorted_files = sorted(file_issue_count.items(), key=lambda x: x[1], reverse=True)
        
        for file_path, count in sorted_files[:10]:
            report += f"  {file_path}: {count} issues\n"
        
        return report


def main():
    parser = argparse.ArgumentParser(description='Type Drift Migration Utility')
    parser.add_argument('--scan', action='store_true', help='Scan codebase for type drift issues')
    parser.add_argument('--validate', action='store_true', help='Validate type safety with mypy')
    parser.add_argument('--directory', default='.', help='Directory to scan (default: current)')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    
    args = parser.parse_args()
    
    analyzer = TypeDriftAnalyzer()
    
    if args.scan or args.report:
        print("SCANNING: Analyzing codebase for type drift issues...")
        
        # Focus on critical paths first
        critical_paths = [
            'netra_backend/app/services/',
            'netra_backend/app/agents/',
            'netra_backend/app/clients/', 
            'netra_backend/app/websocket_core/',
            'auth_service/',
            'shared/'
        ]
        
        all_summary = MigrationSummary()
        
        for path in critical_paths:
            if os.path.exists(path):
                print(f"  Scanning {path}...")
                summary = analyzer.scan_directory(path)
                
                all_summary.total_files_scanned += summary.total_files_scanned
                all_summary.issues_found += summary.issues_found
                all_summary.critical_issues += summary.critical_issues
                all_summary.high_issues += summary.high_issues
                all_summary.files_with_issues.update(summary.files_with_issues)
        
        print(f"\nSUCCESS: Scan complete!")
        print(f"STATS: Found {all_summary.issues_found} type drift issues across {len(all_summary.files_with_issues)} files")
        print(f"CRITICAL: {all_summary.critical_issues} critical issues")
        print(f"HIGH: {all_summary.high_issues} high priority issues")
        
        if args.report:
            report = analyzer.generate_report(all_summary)
            
            # Save report
            report_path = PROJECT_ROOT / "reports" / "type_safety" / "type_drift_scan_results.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
                
            print(f"\nREPORT: Detailed report saved to: {report_path}")
            
            # Also print summary
            print("\n" + "="*50)
            print("QUICK SUMMARY:")
            print("="*50)
            
            # Show top 5 critical issues
            critical_issues = [i for i in analyzer.issues if i.severity == "CRITICAL"][:5]
            if critical_issues:
                print("\nCRITICAL ISSUES:")
                for i, issue in enumerate(critical_issues, 1):
                    print(f"{i}. {issue.file_path}:{issue.line_number}")
                    print(f"   {issue.description}")
                    print(f"   Fix: {issue.suggested_fix}\n")
    
    if args.validate:
        print("VALIDATE: Running type validation with mypy...")
        
        # Run mypy on critical files
        import subprocess
        try:
            result = subprocess.run([
                'mypy', 
                '--ignore-missing-imports',
                '--show-error-codes', 
                'shared/types/',
                'netra_backend/app/services/user_execution_context.py'
            ], capture_output=True, text=True, cwd=PROJECT_ROOT)
            
            if result.returncode == 0:
                print("SUCCESS: Type validation passed!")
            else:
                print("ISSUES: Type validation issues found:")
                print(result.stdout)
                print(result.stderr)
                
        except FileNotFoundError:
            print("WARNING: mypy not found. Install with: pip install mypy")


if __name__ == '__main__':
    main()