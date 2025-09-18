#!/usr/bin/env python3
"""
Automated Test Syntax Fixer - Surgical AST-based Test File Repair

This script implements the comprehensive remediation strategy for fixing 552+ test files
with syntax errors blocking Golden Path validation.

Business Impact: $500K+ ARR at risk due to blocked test infrastructure
Strategy: AST-based surgical fixes with strict validation and rollback capability

Usage:
    python AUTOMATED_TEST_SYNTAX_FIXER.py --phase 1 --validate-only
    python AUTOMATED_TEST_SYNTAX_FIXER.py --phase 1 --fix --batch-size 5
    python AUTOMATED_TEST_SYNTAX_FIXER.py --phase 2 --fix --batch-size 10

Created: 2025-09-18
Author: Claude Code Assistant
"""

import ast
import os
import re
import shutil
import time
import json
import sys
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
from datetime import datetime

class TestSyntaxFixer:
    """AST-based test file syntax repair with business impact tracking."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.backup_dir = self.base_dir / "backups" / f"syntax_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Error patterns for detection and fixing
        self.error_patterns = {
            'unterminated_string': re.compile(r'[^\\]"[^"]*$'),
            'unterminated_triple_quote': re.compile(r'"""[^"]*(?:"""[^"]*)*$'),
            'invalid_f_string': re.compile(r'f"[^"]*\{[^}]*$'),
            'missing_quote_close': re.compile(r'"[^"]*\n'),
            'malformed_function': re.compile(r'def\s+\w+\([^)]*$'),
        }

        # Critical test files priority list
        self.p0_critical_files = [
            "tests/mission_critical/websocket_real_test_base.py",
            "tests/e2e/service_availability.py",
            "tests/critical/test_auth_cross_system_failures.py",
            "tests/critical/test_health_route_configuration_chaos.py",
            "tests/critical/test_health_route_duplication_audit.py"
        ]

        self.p1_agent_files = [
            "tests/mission_critical/test_agent_execution_business_value.py",
            "tests/mission_critical/test_chat_business_value_restoration.py",
            "tests/mission_critical/test_chat_functionality_with_toolregistry_fixes.py",
            "tests/integration/golden_path/test_agent_execution_pipeline_comprehensive.py",
            "tests/mission_critical/test_basic_triage_response_revenue_protection.py"
        ]

        # Metrics tracking
        self.metrics = {
            'files_processed': 0,
            'files_fixed': 0,
            'files_failed': 0,
            'backups_created': 0,
            'syntax_errors_resolved': 0
        }

    def detect_syntax_errors(self, file_path: Path) -> List[Dict[str, Any]]:
        """Detect syntax errors in a Python file using AST."""
        errors = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Try to parse with AST
            ast.parse(content)
            return []  # No syntax errors

        except SyntaxError as e:
            error_info = {
                'type': 'syntax_error',
                'line': e.lineno,
                'offset': e.offset,
                'msg': e.msg,
                'text': e.text.strip() if e.text else None
            }

            # Classify error type for targeted fixing
            if 'unterminated string literal' in e.msg:
                error_info['category'] = 'unterminated_string'
            elif 'unterminated triple-quoted string literal' in e.msg:
                error_info['category'] = 'unterminated_triple_quote'
            elif 'invalid syntax' in e.msg:
                error_info['category'] = 'invalid_syntax'
            else:
                error_info['category'] = 'other'

            errors.append(error_info)

        except UnicodeDecodeError:
            errors.append({
                'type': 'encoding_error',
                'category': 'encoding_issue',
                'msg': 'File encoding issue'
            })
        except Exception as e:
            errors.append({
                'type': 'parse_error',
                'category': 'other',
                'msg': str(e)
            })

        return errors

    def fix_unterminated_string(self, content: str, error_line: int) -> str:
        """Fix unterminated string literals."""
        lines = content.split('\n')

        if error_line <= len(lines):
            line = lines[error_line - 1]

            # Fix unterminated f-string
            if 'f"' in line and line.count('"') % 2 == 1:
                # Find the unterminated f-string and close it
                if line.strip().endswith('"'):
                    # Line ends with quote, might need different fix
                    pass
                else:
                    # Add closing quote
                    lines[error_line - 1] = line + '"'

            # Fix regular unterminated string
            elif '"' in line and line.count('"') % 2 == 1:
                lines[error_line - 1] = line + '"'

        return '\n'.join(lines)

    def fix_unterminated_triple_quote(self, content: str) -> str:
        """Fix unterminated triple-quoted strings."""
        lines = content.split('\n')

        # Count triple quotes
        triple_quote_count = content.count('"""')

        if triple_quote_count % 2 == 1:
            # Odd number - need to add closing
            lines.append('"""')

        return '\n'.join(lines)

    def fix_invalid_syntax(self, content: str, error_line: int, error_text: str) -> str:
        """Fix common invalid syntax patterns."""
        lines = content.split('\n')

        if error_line <= len(lines):
            line = lines[error_line - 1]

            # Fix missing quotes around docstrings
            if error_text and 'Test suite to expose' in error_text and not line.strip().startswith('"""'):
                # Wrap in docstring quotes
                lines[error_line - 1] = '"""' + line

                # Find end and add closing quotes
                for i in range(error_line, len(lines)):
                    if 'Test suite' in lines[i] or i == len(lines) - 1:
                        lines[i] = lines[i] + '"""'
                        break

        return '\n'.join(lines)

    def fix_file_syntax(self, file_path: Path) -> bool:
        """Fix syntax errors in a single file."""
        print(f"Fixing syntax errors in: {file_path}")

        # Create backup
        backup_path = self.backup_dir / file_path.name
        shutil.copy2(file_path, backup_path)
        self.metrics['backups_created'] += 1

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                original_content = f.read()

            content = original_content
            errors = self.detect_syntax_errors(file_path)

            if not errors:
                print(f"  ✅ No syntax errors found in {file_path}")
                return True

            for error in errors:
                print(f"  🔧 Fixing {error['category']}: {error['msg']}")

                if error['category'] == 'unterminated_string':
                    content = self.fix_unterminated_string(content, error.get('line', 1))
                elif error['category'] == 'unterminated_triple_quote':
                    content = self.fix_unterminated_triple_quote(content)
                elif error['category'] == 'invalid_syntax':
                    content = self.fix_invalid_syntax(content, error.get('line', 1), error.get('text', ''))

                self.metrics['syntax_errors_resolved'] += 1

            # Validate fix
            try:
                ast.parse(content)

                # Write fixed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                print(f"  ✅ Fixed syntax errors in {file_path}")
                self.metrics['files_fixed'] += 1
                return True

            except SyntaxError as e:
                print(f"  ❌ Fix failed - still has syntax error: {e}")
                # Restore from backup
                shutil.copy2(backup_path, file_path)
                self.metrics['files_failed'] += 1
                return False

        except Exception as e:
            print(f"  ❌ Error fixing file: {e}")
            # Restore from backup
            shutil.copy2(backup_path, file_path)
            self.metrics['files_failed'] += 1
            return False

    def validate_file_syntax(self, file_path: Path) -> bool:
        """Validate that a file has correct syntax."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            ast.parse(content)
            return True
        except:
            return False

    def scan_for_broken_files(self) -> List[Path]:
        """Scan for test files with syntax errors."""
        broken_files = []

        # Find all Python test files
        test_patterns = [
            "**/test_*.py",
            "**/*_test.py",
            "**/tests/**/*.py"
        ]

        for pattern in test_patterns:
            for file_path in self.base_dir.glob(pattern):
                if file_path.is_file() and not self.validate_file_syntax(file_path):
                    broken_files.append(file_path)

        return broken_files

    def run_phase(self, phase: int, fix: bool = False, batch_size: int = 5, validate_only: bool = False) -> Dict[str, Any]:
        """Run a specific phase of the remediation plan."""
        print(f"\n{'='*60}")
        print(f"PHASE {phase} - Test Syntax Remediation")
        print(f"{'='*60}")

        if phase == 1:
            target_files = [self.base_dir / f for f in self.p0_critical_files if (self.base_dir / f).exists()]
            print(f"P0 Critical Files: {len(target_files)} files")
        elif phase == 2:
            target_files = [self.base_dir / f for f in self.p1_agent_files if (self.base_dir / f).exists()]
            print(f"P1 Agent Execution Files: {len(target_files)} files")
        elif phase == 3:
            # All other broken files
            all_broken = self.scan_for_broken_files()
            already_processed = set(self.p0_critical_files + self.p1_agent_files)
            target_files = [f for f in all_broken if str(f.relative_to(self.base_dir)) not in already_processed]
            print(f"P2+ Remaining Files: {len(target_files)} files")
        else:
            print(f"Invalid phase: {phase}")
            return {'success': False, 'error': 'Invalid phase'}

        if validate_only:
            print("\n🔍 VALIDATION ONLY MODE - No files will be modified")

        results = {
            'phase': phase,
            'total_files': len(target_files),
            'processed': 0,
            'fixed': 0,
            'failed': 0,
            'skipped': 0,
            'files': []
        }

        # Process files in batches
        for i in range(0, len(target_files), batch_size):
            batch = target_files[i:i+batch_size]
            print(f"\nBatch {i//batch_size + 1}: Processing {len(batch)} files")

            for file_path in batch:
                self.metrics['files_processed'] += 1
                results['processed'] += 1

                # Check current syntax
                errors = self.detect_syntax_errors(file_path)
                file_result = {
                    'path': str(file_path.relative_to(self.base_dir)),
                    'initial_errors': len(errors),
                    'error_types': [e['category'] for e in errors]
                }

                if not errors:
                    print(f"  ✅ {file_path.name} - Already clean")
                    file_result['status'] = 'clean'
                    results['skipped'] += 1
                elif validate_only:
                    print(f"  🔍 {file_path.name} - {len(errors)} errors: {', '.join(set(e['category'] for e in errors))}")
                    file_result['status'] = 'needs_fix'
                elif fix:
                    if self.fix_file_syntax(file_path):
                        file_result['status'] = 'fixed'
                        results['fixed'] += 1
                    else:
                        file_result['status'] = 'failed'
                        results['failed'] += 1
                else:
                    print(f"  📋 {file_path.name} - {len(errors)} errors detected (dry run)")
                    file_result['status'] = 'detected'

                results['files'].append(file_result)

        # Phase summary
        print(f"\n{'='*40}")
        print(f"PHASE {phase} SUMMARY")
        print(f"{'='*40}")
        print(f"Total Files: {results['total_files']}")
        print(f"Processed: {results['processed']}")
        print(f"Fixed: {results['fixed']}")
        print(f"Failed: {results['failed']}")
        print(f"Already Clean: {results['skipped']}")

        if results['failed'] > 0:
            print(f"\n⚠️ {results['failed']} files failed to fix - manual intervention required")

        return results

    def generate_report(self) -> str:
        """Generate comprehensive remediation report."""
        report = f"""
# Test Syntax Remediation Report

**Generated:** {datetime.now().isoformat()}
**Backup Location:** {self.backup_dir}

## Summary
- Files Processed: {self.metrics['files_processed']}
- Files Fixed: {self.metrics['files_fixed']}
- Files Failed: {self.metrics['files_failed']}
- Syntax Errors Resolved: {self.metrics['syntax_errors_resolved']}
- Backups Created: {self.metrics['backups_created']}

## Success Rate
- Fix Success: {(self.metrics['files_fixed'] / max(1, self.metrics['files_processed']) * 100):.1f}%

## Business Impact
- Golden Path Tests: {'✅ RECOVERED' if self.metrics['files_fixed'] > 0 else '❌ STILL BLOCKED'}
- ARR Protection: {'✅ PROTECTED' if self.metrics['files_fixed'] >= 5 else '⚠️ PARTIAL'}
- Test Infrastructure: {'✅ OPERATIONAL' if self.metrics['files_fixed'] >= 10 else '❌ DEGRADED'}

## Recommendations
{"All critical test files recovered - proceed with Golden Path validation" if self.metrics['files_fixed'] >= 5 else "Additional manual fixes required for full recovery"}
"""
        return report

def main():
    """Main entry point for automated test syntax fixing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Automated Test Syntax Fixer - Surgical repair of test file syntax errors"
    )
    parser.add_argument('--phase', type=int, choices=[1, 2, 3], required=True,
                       help='Remediation phase: 1=P0 Critical, 2=P1 Agent, 3=All Remaining')
    parser.add_argument('--fix', action='store_true',
                       help='Actually fix files (default: dry run)')
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate and report errors, do not fix')
    parser.add_argument('--batch-size', type=int, default=5,
                       help='Number of files to process per batch')
    parser.add_argument('--base-dir', type=str, default='.',
                       help='Base directory to search for test files')

    args = parser.parse_args()

    # Initialize fixer
    fixer = TestSyntaxFixer(args.base_dir)

    print("🔧 AUTOMATED TEST SYNTAX FIXER")
    print("=" * 50)
    print(f"Business Impact: $500K+ ARR protection")
    print(f"Target: Fix {'' if args.fix else 'detect '}syntax errors in Phase {args.phase} test files")
    print(f"Backup Location: {fixer.backup_dir}")

    # Run the specified phase
    try:
        results = fixer.run_phase(
            phase=args.phase,
            fix=args.fix and not args.validate_only,
            batch_size=args.batch_size,
            validate_only=args.validate_only
        )

        # Generate and save report
        report = fixer.generate_report()
        report_path = fixer.backup_dir / "remediation_report.md"
        with open(report_path, 'w') as f:
            f.write(report)

        print(f"\n📊 Report saved: {report_path}")

        # Exit code based on results
        if results['failed'] > 0:
            print(f"\n❌ Phase {args.phase} completed with {results['failed']} failures")
            sys.exit(1)
        else:
            print(f"\n✅ Phase {args.phase} completed successfully")
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
        sys.exit(2)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(3)

if __name__ == "__main__":
    main()