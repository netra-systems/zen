#!/usr/bin/env python3
"""
Issue #1332 Phase 1: Mission-Critical Test Syntax Fixer
Enhanced AST-based syntax validation and fixing utility for test files.

Priority: Golden Path tests and WebSocket event tests
Focus: test_websocket_agent_events_suite.py and mission-critical tests
"""

import ast
import os
import re
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
import traceback
from dataclasses import dataclass


@dataclass
class SyntaxFix:
    """Represents a syntax fix that was applied"""
    file_path: str
    line_number: int
    issue_type: str
    original_line: str
    fixed_line: str
    description: str


@dataclass
class FixResult:
    """Result of attempting to fix a file"""
    file_path: str
    success: bool
    fixes_applied: List[SyntaxFix]
    error_message: Optional[str] = None
    backup_path: Optional[str] = None


class TestSyntaxFixer:
    """Enhanced syntax fixer for test files with common pattern fixes"""

    def __init__(self):
        self.fixes_applied: List[SyntaxFix] = []
        self.backup_dir = None

    def setup_backup_dir(self, base_dir: Path) -> Path:
        """Create backup directory for original files"""
        backup_dir = base_dir / "syntax_fix_backups"
        backup_dir.mkdir(exist_ok=True)
        self.backup_dir = backup_dir
        return backup_dir

    def backup_file(self, file_path: Path) -> Path:
        """Create backup of file before modification"""
        if not self.backup_dir:
            raise ValueError("Backup directory not set up")

        backup_path = self.backup_dir / f"{file_path.name}.backup"
        shutil.copy2(file_path, backup_path)
        return backup_path

    def check_syntax(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """Check if file has valid Python syntax"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content, filename=str(file_path))
            return True, None
        except SyntaxError as e:
            error_msg = f"Syntax Error at line {e.lineno}: {e.msg}"
            if e.text:
                error_msg += f"\n  Code: {e.text.strip()}"
            return False, error_msg
        except Exception as e:
            return False, f"Parse Error: {str(e)}"

    def apply_pattern_fixes(self, file_path: Path) -> List[SyntaxFix]:
        """Apply common pattern-based fixes to test files"""
        fixes = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            modified = False

            for i, line in enumerate(lines):
                original_line = line
                fixed_line = line

                # Fix 1: Replace $500K+ with 500K in strings and comments
                if '$500K+' in fixed_line:
                    fixed_line = fixed_line.replace('$500K+', '500K')
                    if fixed_line != original_line:
                        fixes.append(SyntaxFix(
                            file_path=str(file_path),
                            line_number=i + 1,
                            issue_type="currency_format",
                            original_line=original_line.rstrip(),
                            fixed_line=fixed_line.rstrip(),
                            description="Replaced $500K+ with 500K to prevent syntax issues"
                        ))
                        lines[i] = fixed_line
                        modified = True

                # Fix 2: Fix unterminated f-strings
                if re.search(r'f"[^"]*$', fixed_line.strip()) and not fixed_line.strip().endswith('\\'):
                    if not any('"' in lines[j] for j in range(i+1, min(i+3, len(lines)))):
                        fixed_line = fixed_line.rstrip() + '"\n'
                        fixes.append(SyntaxFix(
                            file_path=str(file_path),
                            line_number=i + 1,
                            issue_type="unterminated_string",
                            original_line=original_line.rstrip(),
                            fixed_line=fixed_line.rstrip(),
                            description="Added missing closing quote to f-string"
                        ))
                        lines[i] = fixed_line
                        modified = True

                # Fix 3: Fix unterminated regular strings
                if fixed_line.count('"') % 2 != 0 and not fixed_line.strip().endswith('\\'):
                    # Check if this is a multi-line string continuation
                    if i < len(lines) - 1:
                        next_line = lines[i + 1]
                        if '"' not in next_line and not next_line.strip().startswith('#'):
                            fixed_line = fixed_line.rstrip() + '"\n'
                            fixes.append(SyntaxFix(
                                file_path=str(file_path),
                                line_number=i + 1,
                                issue_type="unterminated_string",
                                original_line=original_line.rstrip(),
                                fixed_line=fixed_line.rstrip(),
                                description="Added missing closing quote to string"
                            ))
                            lines[i] = fixed_line
                            modified = True

                # Fix 4: Fix bracket mismatches (simple cases)
                open_brackets = fixed_line.count('(') - fixed_line.count(')')
                open_squares = fixed_line.count('[') - fixed_line.count(']')
                open_braces = fixed_line.count('{') - fixed_line.count('}')

                # If line has unmatched opening brackets and ends without continuation
                if (open_brackets > 0 or open_squares > 0 or open_braces > 0) and \
                   not fixed_line.strip().endswith('\\') and \
                   not fixed_line.strip().endswith(',') and \
                   i == len(lines) - 1:  # Last line

                    close_chars = ')' * open_brackets + ']' * open_squares + '}' * open_braces
                    if close_chars:
                        fixed_line = fixed_line.rstrip() + close_chars + '\n'
                        fixes.append(SyntaxFix(
                            file_path=str(file_path),
                            line_number=i + 1,
                            issue_type="bracket_mismatch",
                            original_line=original_line.rstrip(),
                            fixed_line=fixed_line.rstrip(),
                            description=f"Added missing closing brackets: {close_chars}"
                        ))
                        lines[i] = fixed_line
                        modified = True

                # Fix 5: Fix indentation issues (basic cases)
                if fixed_line.strip() and not fixed_line.startswith(' ') and not fixed_line.startswith('\t'):
                    # Check if previous line suggests this should be indented
                    if i > 0:
                        prev_line = lines[i-1].strip()
                        if prev_line.endswith(':') or prev_line.endswith('\\'):
                            # Should be indented
                            fixed_line = '    ' + fixed_line
                            fixes.append(SyntaxFix(
                                file_path=str(file_path),
                                line_number=i + 1,
                                issue_type="indentation",
                                original_line=original_line.rstrip(),
                                fixed_line=fixed_line.rstrip(),
                                description="Added missing indentation"
                            ))
                            lines[i] = fixed_line
                            modified = True

            # Save modified file if changes were made
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

        except Exception as e:
            print(f"Error applying pattern fixes to {file_path}: {e}")

        return fixes

    def fix_file(self, file_path: Path) -> FixResult:
        """Attempt to fix syntax errors in a file"""
        try:
            # First check if file has syntax errors
            is_valid, error = self.check_syntax(file_path)
            if is_valid:
                return FixResult(
                    file_path=str(file_path),
                    success=True,
                    fixes_applied=[],
                    error_message="File already has valid syntax"
                )

            print(f"Attempting to fix syntax errors in: {file_path}")
            print(f"Original error: {error}")

            # Create backup
            backup_path = self.backup_file(file_path)

            # Apply pattern fixes
            fixes = self.apply_pattern_fixes(file_path)

            # Check if fixes resolved the issue
            is_valid_after_fix, error_after_fix = self.check_syntax(file_path)

            if is_valid_after_fix:
                print(f"✅ Successfully fixed {len(fixes)} issues in {file_path}")
                return FixResult(
                    file_path=str(file_path),
                    success=True,
                    fixes_applied=fixes,
                    backup_path=str(backup_path)
                )
            else:
                print(f"❌ Fixes applied but syntax errors remain in {file_path}")
                print(f"Remaining error: {error_after_fix}")
                return FixResult(
                    file_path=str(file_path),
                    success=False,
                    fixes_applied=fixes,
                    error_message=f"Remaining error after fixes: {error_after_fix}",
                    backup_path=str(backup_path)
                )

        except Exception as e:
            return FixResult(
                file_path=str(file_path),
                success=False,
                fixes_applied=[],
                error_message=f"Unexpected error during fix: {str(e)}"
            )

    def find_mission_critical_test_files(self, project_root: Path) -> List[Path]:
        """Find all mission-critical test files"""
        mission_critical_files = []

        # Primary mission-critical directory
        mission_critical_dir = project_root / "tests" / "mission_critical"
        if mission_critical_dir.exists():
            mission_critical_files.extend(mission_critical_dir.glob("*.py"))

        # Also check for Golden Path tests in other locations
        test_dirs = [
            project_root / "tests",
            project_root / "netra_backend" / "tests" / "critical",
            project_root / "netra_backend" / "tests" / "mission_critical"
        ]

        for test_dir in test_dirs:
            if test_dir.exists():
                # Look for golden path and websocket tests
                golden_path_files = list(test_dir.rglob("*golden_path*.py"))
                websocket_files = list(test_dir.rglob("*websocket*.py"))
                agent_event_files = list(test_dir.rglob("*agent_event*.py"))

                mission_critical_files.extend(golden_path_files)
                mission_critical_files.extend(websocket_files)
                mission_critical_files.extend(agent_event_files)

        # Remove duplicates
        unique_files = list(set(mission_critical_files))

        # Sort by priority (websocket_agent_events_suite first)
        def priority_sort(file_path: Path) -> int:
            name = file_path.name.lower()
            if "websocket_agent_events_suite" in name:
                return 0
            elif "golden_path" in name:
                return 1
            elif "websocket" in name:
                return 2
            elif "mission_critical" in str(file_path):
                return 3
            else:
                return 4

        unique_files.sort(key=priority_sort)
        return unique_files

    def run_phase1_fixes(self, project_root: Path) -> Dict[str, FixResult]:
        """Run Phase 1 fixes on mission-critical test files"""
        print("="*80)
        print("ISSUE #1332 PHASE 1: MISSION-CRITICAL TEST SYNTAX FIXES")
        print("="*80)

        # Set up backup directory
        self.setup_backup_dir(project_root)

        # Find mission-critical test files
        test_files = self.find_mission_critical_test_files(project_root)

        print(f"\nFound {len(test_files)} mission-critical test files to check:")
        for file_path in test_files:
            rel_path = file_path.relative_to(project_root)
            print(f"  - {rel_path}")

        print(f"\nBackup directory: {self.backup_dir}")
        print("\n" + "="*50)
        print("PROCESSING FILES")
        print("="*50)

        results = {}

        for file_path in test_files:
            rel_path = file_path.relative_to(project_root)
            print(f"\n🔍 Processing: {rel_path}")

            result = self.fix_file(file_path)
            results[str(rel_path)] = result

            if result.success and result.fixes_applied:
                print(f"   ✅ Applied {len(result.fixes_applied)} fixes")
                for fix in result.fixes_applied:
                    print(f"      - Line {fix.line_number}: {fix.description}")
            elif result.success and not result.fixes_applied:
                print(f"   ✅ No fixes needed (already valid)")
            else:
                print(f"   ❌ Failed to fix: {result.error_message}")

        return results

    def print_phase1_report(self, results: Dict[str, FixResult]):
        """Print comprehensive report of Phase 1 results"""
        print("\n" + "="*80)
        print("PHASE 1 COMPLETION REPORT")
        print("="*80)

        total_files = len(results)
        successful_fixes = sum(1 for r in results.values() if r.success)
        files_with_fixes = sum(1 for r in results.values() if r.fixes_applied)
        total_fixes = sum(len(r.fixes_applied) for r in results.values())

        print(f"\nSUMMARY:")
        print(f"  Total files processed: {total_files}")
        print(f"  Successfully processed: {successful_fixes}")
        print(f"  Files that needed fixes: {files_with_fixes}")
        print(f"  Total fixes applied: {total_fixes}")
        print(f"  Success rate: {successful_fixes/total_files*100:.1f}%")

        # Successful fixes
        successful_files = [path for path, result in results.items() if result.success and result.fixes_applied]
        if successful_files:
            print(f"\n✅ SUCCESSFULLY FIXED FILES ({len(successful_files)}):")
            for file_path in successful_files:
                result = results[file_path]
                print(f"  - {file_path} ({len(result.fixes_applied)} fixes)")

        # Files that were already valid
        already_valid = [path for path, result in results.items() if result.success and not result.fixes_applied]
        if already_valid:
            print(f"\n✅ ALREADY VALID FILES ({len(already_valid)}):")
            for file_path in already_valid:
                print(f"  - {file_path}")

        # Failed fixes
        failed_files = [path for path, result in results.items() if not result.success]
        if failed_files:
            print(f"\n❌ FAILED TO FIX ({len(failed_files)}):")
            for file_path in failed_files:
                result = results[file_path]
                print(f"  - {file_path}")
                print(f"    Error: {result.error_message}")

        # Detailed fix breakdown
        if total_fixes > 0:
            print(f"\n📊 FIX TYPE BREAKDOWN:")
            fix_types = {}
            for result in results.values():
                for fix in result.fixes_applied:
                    fix_types[fix.issue_type] = fix_types.get(fix.issue_type, 0) + 1

            for fix_type, count in sorted(fix_types.items()):
                print(f"  - {fix_type}: {count} fixes")

        print(f"\n📁 BACKUP LOCATION: {self.backup_dir}")
        print("   Original files backed up before modification")

        return successful_fixes, total_files


def main():
    """Main function for Issue #1332 Phase 1"""
    if len(sys.argv) > 1:
        project_root = Path(sys.argv[1])
    else:
        script_dir = Path(__file__).parent
        project_root = script_dir.parent

    if not project_root.exists():
        print(f"ERROR: Project root {project_root} does not exist")
        sys.exit(1)

    fixer = TestSyntaxFixer()
    results = fixer.run_phase1_fixes(project_root)
    successful_fixes, total_files = fixer.print_phase1_report(results)

    # Exit with appropriate code
    if successful_fixes == total_files:
        print(f"\n🎉 SUCCESS: All {total_files} files processed successfully!")
        sys.exit(0)
    else:
        failed_count = total_files - successful_fixes
        print(f"\n⚠️  PARTIAL SUCCESS: {failed_count} files still need manual attention")
        sys.exit(1)


if __name__ == "__main__":
    main()