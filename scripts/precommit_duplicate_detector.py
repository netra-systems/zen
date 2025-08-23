#!/usr/bin/env python3
"""
Pre-commit hook for duplicate code detection.
Integrates with existing detect_duplicate_code.py for fast incremental checks.

Usage:
    python scripts/precommit_duplicate_detector.py [files...]
    
This script:
1. Performs fast duplicate detection on changed files
2. Checks against known duplicate patterns
3. Integrates with existing architecture compliance
"""

import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Set, Optional
import ast
import re
from collections import defaultdict


class PrecommitDuplicateDetector:
    """Fast duplicate detection for pre-commit hooks."""
    
    def __init__(self):
        self.root_path = Path.cwd()
        self.changed_files: List[Path] = []
        self.critical_patterns = self._load_critical_patterns()
        self.issues: List[Dict] = []
        
    def _load_critical_patterns(self) -> Dict:
        """Load critical duplicate patterns from specs."""
        return {
            'websocket_managers': [
                'WebSocketManager',
                'WSManager', 
                'ConnectionManager',
                'WebsocketConnectionManager'
            ],
            'heartbeat_implementations': [
                'heartbeat',
                'ping_pong',
                'keep_alive',
                'connection_check'
            ],
            'lifecycle_handlers': [
                'lifecycle',
                'connection_lifecycle',
                'conn_pool',
                'connection_pool'
            ],
            'duplicate_suffixes': {
                '_1.py', '_2.py', '_old.py', '_new.py',
                '_backup.py', '_copy.py', '_temp.py'
            }
        }
    
    def check_files(self, files: List[str]) -> int:
        """Check specific files for duplicates."""
        self.changed_files = [Path(f) for f in files if f.endswith('.py')]
        
        if not self.changed_files:
            return 0
            
        # Quick checks on changed files
        self._check_file_naming()
        self._check_class_duplicates()
        self._check_function_signatures()
        self._check_critical_patterns()
        
        # If issues found, run comprehensive scan
        if self.issues:
            self._run_comprehensive_scan()
            
        return self._report_issues()
    
    def _check_file_naming(self) -> None:
        """Check for problematic file naming patterns."""
        for file_path in self.changed_files:
            file_name = file_path.name
            
            # Check for duplicate suffix patterns
            for suffix in self.critical_patterns['duplicate_suffixes']:
                if file_name.endswith(suffix):
                    self.issues.append({
                        'type': 'file_naming',
                        'severity': 'high',
                        'file': str(file_path),
                        'message': f"File uses duplicate pattern suffix: {suffix}"
                    })
                    
            # Check for numbered patterns (e.g., module_1.py, feature_v2.py)
            if re.search(r'_\d+\.py$|_v\d+\.py$', file_name):
                self.issues.append({
                    'type': 'numbered_file',
                    'severity': 'high',
                    'file': str(file_path),
                    'message': f"File uses numbered naming pattern: {file_name}"
                })
    
    def _check_class_duplicates(self) -> None:
        """Quick check for duplicate class definitions."""
        class_definitions = defaultdict(list)
        
        for file_path in self.changed_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_definitions[node.name].append(str(file_path))
                        
                        # Check against critical patterns
                        for pattern_type, patterns in [
                            ('websocket_managers', self.critical_patterns['websocket_managers']),
                            ('heartbeat_implementations', self.critical_patterns['heartbeat_implementations']),
                            ('lifecycle_handlers', self.critical_patterns['lifecycle_handlers'])
                        ]:
                            for pattern in patterns:
                                if pattern.lower() in node.name.lower():
                                    self._check_existing_implementations(
                                        node.name, str(file_path), pattern_type
                                    )
            except Exception:
                pass
    
    def _check_existing_implementations(self, class_name: str, file_path: str, pattern_type: str) -> None:
        """Check if similar implementations already exist."""
        # Quick grep for similar patterns
        try:
            result = subprocess.run(
                ['python', '-c', f'''
import re
import pathlib
pattern = r"class.*{re.escape(class_name[:5])}.*:"
files = list(pathlib.Path("netra_backend/app").rglob("*.py"))
files.extend(list(pathlib.Path("auth_service").rglob("*.py")))
matches = []
for f in files[:100]:  # Limit for speed
    try:
        if "{file_path}" not in str(f):
            content = f.read_text()
            if re.search(pattern, content, re.IGNORECASE):
                matches.append(str(f))
    except: pass
print(len(matches))
'''],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            match_count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            
            if match_count > 0:
                self.issues.append({
                    'type': 'potential_duplicate',
                    'severity': 'high',
                    'class': class_name,
                    'file': file_path,
                    'pattern_type': pattern_type,
                    'message': f"Class '{class_name}' may duplicate existing {pattern_type} implementations"
                })
        except Exception:
            pass
    
    def _check_function_signatures(self) -> None:
        """Check for duplicate function signatures."""
        for file_path in self.changed_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Quick pattern matching for common duplicate functions
                duplicate_prone_functions = [
                    (r'def\s+connect_to_websocket', 'WebSocket connection'),
                    (r'def\s+handle_message', 'Message handling'),
                    (r'def\s+send_heartbeat', 'Heartbeat'),
                    (r'def\s+manage_connection', 'Connection management'),
                    (r'def\s+process_event', 'Event processing')
                ]
                
                for pattern, func_type in duplicate_prone_functions:
                    if re.search(pattern, content):
                        # Check if this function type already exists elsewhere
                        self._check_function_uniqueness(pattern, func_type, str(file_path))
                        
            except Exception:
                pass
    
    def _check_function_uniqueness(self, pattern: str, func_type: str, file_path: str) -> None:
        """Quick check if function pattern exists elsewhere."""
        # Use existing architecture scanner if available
        scanner_path = self.root_path / 'scripts' / 'architecture_scanner.py'
        if scanner_path.exists():
            try:
                # Quick scan with timeout
                result = subprocess.run(
                    ['python', str(scanner_path), '--quick-scan', '--pattern', pattern],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                
                if 'duplicate' in result.stdout.lower():
                    self.issues.append({
                        'type': 'duplicate_function_pattern',
                        'severity': 'medium',
                        'function_type': func_type,
                        'file': file_path,
                        'message': f"Function pattern for {func_type} may already exist"
                    })
            except Exception:
                pass
    
    def _check_critical_patterns(self) -> None:
        """Check for critical duplicate patterns in changed files."""
        for file_path in self.changed_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for copy-paste indicators
                copy_indicators = [
                    (r'#\s*TODO:\s*remove\s*duplicate', 'TODO remove duplicate'),
                    (r'#\s*FIXME:\s*duplicate', 'FIXME duplicate'),
                    (r'#\s*XXX:\s*copied\s*from', 'Copied from comment'),
                    (r'#\s*Based on:', 'Based on comment'),
                    (r'#\s*Copied from:', 'Copied from comment')
                ]
                
                for pattern, indicator in copy_indicators:
                    if re.search(pattern, content, re.IGNORECASE):
                        self.issues.append({
                            'type': 'copy_paste_indicator',
                            'severity': 'high',
                            'file': str(file_path),
                            'indicator': indicator,
                            'message': f"File contains copy-paste indicator: {indicator}"
                        })
                        
            except Exception:
                pass
    
    def _run_comprehensive_scan(self) -> None:
        """Run comprehensive duplicate detection if issues found."""
        try:
            # Run the full duplicate detector with strict settings
            result = subprocess.run(
                ['python', 'scripts/detect_duplicate_code.py', 
                 '--threshold', '0.7', '--json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Parse JSON report if generated
            report_file = Path('duplicate_code_report.json')
            if report_file.exists():
                with open(report_file, 'r') as f:
                    full_report = json.load(f)
                    
                # Add critical issues from full scan
                for issue in full_report.get('issues', []):
                    if issue.get('severity') in ['critical', 'high']:
                        # Check if issue involves changed files
                        issue_files = issue.get('files', [])
                        changed_paths = [str(f) for f in self.changed_files]
                        
                        if any(cf in ' '.join(issue_files) for cf in changed_paths):
                            self.issues.append(issue)
                            
                # Clean up report file
                report_file.unlink(missing_ok=True)
                
        except subprocess.TimeoutExpired:
            print("Warning: Comprehensive scan timed out, using quick scan results only")
        except Exception as e:
            print(f"Warning: Could not run comprehensive scan: {e}")
    
    def _report_issues(self) -> int:
        """Report found issues and return exit code."""
        if not self.issues:
            print("[OK] No duplicate code patterns detected in changed files")
            return 0
        
        # Group by severity
        by_severity = defaultdict(list)
        for issue in self.issues:
            by_severity[issue.get('severity', 'low')].append(issue)
        
        print("\n" + "=" * 60)
        print("DUPLICATE CODE DETECTION - PRE-COMMIT CHECK FAILED")
        print("=" * 60)
        
        for severity in ['critical', 'high', 'medium', 'low']:
            if severity in by_severity:
                print(f"\n{severity.upper()} ({len(by_severity[severity])} issues):")
                print("-" * 40)
                
                for issue in by_severity[severity][:5]:  # Limit output
                    print(f"  X {issue['message']}")
                    if 'file' in issue:
                        print(f"    File: {issue['file']}")
                    if 'indicator' in issue:
                        print(f"    Indicator: {issue['indicator']}")
                
                if len(by_severity[severity]) > 5:
                    print(f"  ... and {len(by_severity[severity]) - 5} more")
        
        print("\n" + "=" * 60)
        print("ACTIONS REQUIRED:")
        print("=" * 60)
        
        if 'critical' in by_severity or 'high' in by_severity:
            print("\n1. Review and consolidate duplicate code")
            print("2. Run: python scripts/detect_duplicate_code.py --report-only")
            print("3. Follow consolidation patterns in SPEC/learnings/websocket_consolidation.xml")
            print("\nCommit blocked due to duplicate code patterns.")
            return 1
        else:
            print("\nWarning: Medium/low severity duplicates found.")
            print("Consider consolidation before merging.")
            return 0


def main():
    """Main entry point for pre-commit hook."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/precommit_duplicate_detector.py [files...]")
        return 0
    
    detector = PrecommitDuplicateDetector()
    return detector.check_files(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())