#!/usr/bin/env python3
"""
Priority Syntax Repair Script for Test Infrastructure
Issue #837 - Emergency Test File Syntax Repair

Focus on the most critical test files needed for basic test collection.
"""

import ast
import json
import shutil
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class PrioritySyntaxRepairer:
    def __init__(self):
        self.repairs_made = []
        self.backup_dir = Path("priority_repair_backups")
        self.backup_dir.mkdir(exist_ok=True)

    def get_priority_files(self) -> List[str]:
        """Get list of priority files that are most critical for test infrastructure."""
        priority_patterns = [
            # Main test runner and configuration
            "tests/unified_test_runner.py",
            "tests/conftest*.py",

            # Core test directories (avoid backup directories)
            "tests/e2e/*.py",
            "tests/integration/*.py",
            "tests/unit/*.py",
            "tests/mission_critical/*.py",

            # Service-specific tests
            "netra_backend/tests/**/*.py",
            "auth_service/tests/**/*.py",
            "frontend/tests/**/*.py",

            # Critical business tests
            "tests/agents/*.py",
            "tests/websocket/*.py",
            "tests/database/*.py",
        ]

        # Find actual files matching patterns
        priority_files = []
        for pattern in priority_patterns:
            if '*' in pattern:
                files = list(Path('.').glob(pattern))
                for f in files:
                    if ('backup' not in str(f).lower() and
                        'archive' not in str(f).lower() and
                        f.suffix == '.py'):
                        priority_files.append(str(f))
            else:
                if Path(pattern).exists():
                    priority_files.append(pattern)

        return list(set(priority_files))  # Remove duplicates

    def check_syntax(self, file_path: Path) -> tuple[bool, str]:
        """Check if file has valid syntax."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content, filename=str(file_path))
            return True, ""
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def create_backup(self, file_path: Path) -> Path:
        """Create backup before repair."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{file_path.name}.backup_{timestamp}"
        shutil.copy2(file_path, backup_path)
        return backup_path

    def manual_repair_enhanced_error_handling(self, file_path: Path) -> bool:
        """Manually repair the enhanced_error_handling_tests.py file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Find and fix the specific indentation error on line 11
            if len(lines) > 10:
                line_11 = lines[10]  # 0-based index
                if line_11.strip().startswith('raise RuntimeError'):
                    # Fix indentation
                    lines[10] = '            ' + line_11.lstrip()

                    backup_path = self.create_backup(file_path)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)

                    is_valid, _ = self.check_syntax(file_path)
                    if is_valid:
                        return True
                    else:
                        # Restore backup
                        shutil.copy2(backup_path, file_path)
        except Exception as e:
            print(f"Error in manual repair: {e}")

        return False

    def simple_indentation_fix(self, file_path: Path, error_msg: str) -> bool:
        """Try to fix simple indentation errors."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Extract line number from error message
            import re
            line_match = re.search(r'Line (\d+):', error_msg)
            if not line_match:
                return False

            line_no = int(line_match.group(1)) - 1  # Convert to 0-based

            if 0 <= line_no < len(lines):
                current_line = lines[line_no]

                # Common fixes
                if "expected an indented block" in error_msg:
                    # Add pass statement
                    indent = len(current_line) - len(current_line.lstrip())
                    lines.insert(line_no, ' ' * (indent + 4) + 'pass\n')

                elif current_line.strip() and not current_line.startswith(' '):
                    # Try adding standard indentation
                    lines[line_no] = '    ' + current_line.lstrip()

                backup_path = self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                is_valid, _ = self.check_syntax(file_path)
                if is_valid:
                    return True
                else:
                    shutil.copy2(backup_path, file_path)

        except Exception as e:
            print(f"Error in indentation fix: {e}")

        return False

    def simple_bracket_fix(self, file_path: Path, error_msg: str) -> bool:
        """Try to fix simple bracket/parentheses errors."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # Fix dictionary pattern: { ) -> {
            content = re.sub(r'\{\s*\)', '{', content)

            # Fix obvious mismatches
            if "closing parenthesis ')' does not match opening parenthesis '{'" in error_msg:
                # Simple case: replace ) with } at end of lines
                content = re.sub(r'\)\s*$', '}', content, flags=re.MULTILINE)

            if content != original_content:
                backup_path = self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                is_valid, _ = self.check_syntax(file_path)
                if is_valid:
                    return True
                else:
                    shutil.copy2(backup_path, file_path)

        except Exception as e:
            print(f"Error in bracket fix: {e}")

        return False

    def repair_file(self, file_path: Path) -> bool:
        """Attempt to repair a single file."""
        is_valid, error_msg = self.check_syntax(file_path)
        if is_valid:
            return True  # Already valid

        print(f"Attempting repair of {file_path}")
        print(f"  Error: {error_msg}")

        # Try specific repairs based on filename and error
        if "enhanced_error_handling_tests.py" in str(file_path):
            if self.manual_repair_enhanced_error_handling(file_path):
                print(f"  [SUCCESS] Manual repair worked")
                return True

        # Try general repairs
        if "indentation" in error_msg.lower() or "expected an indented block" in error_msg:
            if self.simple_indentation_fix(file_path, error_msg):
                print(f"  [SUCCESS] Indentation fix worked")
                return True

        if "parenthesis" in error_msg or "bracket" in error_msg:
            if self.simple_bracket_fix(file_path, error_msg):
                print(f"  [SUCCESS] Bracket fix worked")
                return True

        print(f"  [FAILED] Could not repair")
        return False

    def repair_priority_files(self) -> Dict:
        """Repair priority files for test infrastructure."""
        priority_files = self.get_priority_files()

        print(f"Found {len(priority_files)} priority test files")
        print("=" * 60)

        total_files = len(priority_files)
        files_with_errors = 0
        successful_repairs = 0

        for i, file_path_str in enumerate(priority_files):
            file_path = Path(file_path_str)

            if not file_path.exists():
                continue

            is_valid, error_msg = self.check_syntax(file_path)

            if not is_valid:
                files_with_errors += 1
                if self.repair_file(file_path):
                    successful_repairs += 1
                    self.repairs_made.append({
                        "file": str(file_path),
                        "success": True,
                        "error_was": error_msg
                    })

            if (i + 1) % 50 == 0:
                print(f"Progress: {i + 1}/{total_files} files checked")

        print("=" * 60)
        print(f"Priority Repair Summary:")
        print(f"Total files checked: {total_files}")
        print(f"Files with syntax errors: {files_with_errors}")
        print(f"Successfully repaired: {successful_repairs}")
        print(f"Remaining errors: {files_with_errors - successful_repairs}")

        if files_with_errors > 0:
            success_rate = (successful_repairs / files_with_errors) * 100
            print(f"Repair success rate: {success_rate:.1f}%")

        return {
            "total_files": total_files,
            "files_with_errors": files_with_errors,
            "successful_repairs": successful_repairs,
            "remaining_errors": files_with_errors - successful_repairs,
            "repairs_made": self.repairs_made
        }


def main():
    """Main execution function."""
    print("Starting priority syntax repair for test infrastructure...")
    print("Focusing on critical test files needed for basic test collection")
    print("=" * 60)

    repairer = PrioritySyntaxRepairer()
    results = repairer.repair_priority_files()

    # Save results
    with open("priority_repair_results.json", 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "backups_location": str(repairer.backup_dir)
        }, f, indent=2)

    if results["successful_repairs"] > 0:
        print(f"\n[SUCCESS] Repaired {results['successful_repairs']} critical test files!")
        print(f"This should help restore basic test collection capability")
        print(f"Backups stored in: {repairer.backup_dir}")

        # Suggest next steps
        if results["remaining_errors"] > 0:
            print(f"\nNext steps:")
            print(f"- Try running test collection to see if it works now")
            print(f"- {results['remaining_errors']} files still need manual attention")

        return 0
    else:
        print(f"\n[INFO] No priority files were repaired.")
        if results["files_with_errors"] == 0:
            print("All priority files already have valid syntax!")
        else:
            print(f"{results['files_with_errors']} files need manual intervention")
        return 1


if __name__ == "__main__":
    exit(main())