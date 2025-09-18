#!/usr/bin/env python3
"""
Syntax Error Repair Script for Test Infrastructure
Issue #837 - Emergency Test File Syntax Repair

This script automatically repairs common syntax errors found in test files.
Based on the analysis from syntax_error_detector.py
"""

import ast
import os
import sys
import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class SyntaxErrorRepairer:
    def __init__(self, report_file: str = "syntax_error_analysis_report.json"):
        self.report_file = report_file
        self.repairs_made = []
        self.backup_dir = Path("syntax_repair_backups")
        self.backup_dir.mkdir(exist_ok=True)

    def load_error_report(self) -> Dict:
        """Load the syntax error analysis report."""
        with open(self.report_file, 'r') as f:
            return json.load(f)

    def create_backup(self, file_path: Path) -> Path:
        """Create a backup of the file before modification."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{file_path.name}.backup_{timestamp}"
        shutil.copy2(file_path, backup_path)
        return backup_path

    def repair_mismatched_parentheses(self, file_path: Path, error_info: Dict) -> bool:
        """Repair mismatched parentheses, brackets, and braces."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            original_content = ''.join(lines)
            line_no = error_info.get('line', 1) - 1  # Convert to 0-based index

            if line_no < 0 or line_no >= len(lines):
                return False

            line = lines[line_no]
            message = error_info.get('message', '')

            repaired = False

            # Common patterns to fix
            if "closing parenthesis ')' does not match opening parenthesis '{'" in message:
                # Replace ')' with '}' at the end of the line
                lines[line_no] = line.rstrip().rstrip(')') + '}\n'
                repaired = True

            elif "closing parenthesis ')' does not match opening parenthesis '['" in message:
                # Replace ')' with ']' at the end of the line
                lines[line_no] = line.rstrip().rstrip(')') + ']\n'
                repaired = True

            elif "unmatched ')'" in message:
                # Remove extra closing parenthesis
                lines[line_no] = line.replace(')', '', 1)
                repaired = True

            elif "unmatched '}'" in message:
                # Remove extra closing brace
                lines[line_no] = line.replace('}', '', 1)
                repaired = True

            elif "unmatched ']'" in message:
                # Remove extra closing bracket
                lines[line_no] = line.replace(']', '', 1)
                repaired = True

            if repaired:
                # Create backup and write repaired content
                backup_path = self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                # Verify the fix worked
                if self.verify_syntax(file_path):
                    self.repairs_made.append({
                        "file": str(file_path),
                        "error_type": "mismatched_parentheses",
                        "backup": str(backup_path),
                        "success": True
                    })
                    return True
                else:
                    # Restore from backup if fix didn't work
                    shutil.copy2(backup_path, file_path)
                    return False

        except Exception as e:
            print(f"Error repairing {file_path}: {e}")
            return False

        return False

    def repair_unterminated_strings(self, file_path: Path, error_info: Dict) -> bool:
        """Repair unterminated string literals."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            line_no = error_info.get('line', 1) - 1

            if line_no < 0 or line_no >= len(lines):
                return False

            line = lines[line_no]
            message = error_info.get('message', '')

            repaired = False

            if "unterminated string literal" in message:
                # Common patterns: missing closing quote

                # Check for single quotes
                if line.count("'") % 2 == 1:
                    # Add missing single quote at end of line
                    lines[line_no] = line.rstrip() + "'\n"
                    repaired = True

                # Check for double quotes
                elif line.count('"') % 2 == 1:
                    # Add missing double quote at end of line
                    lines[line_no] = line.rstrip() + '"\n'
                    repaired = True

                # Check for triple quotes
                elif '"""' in line and line.count('"""') == 1:
                    # Add closing triple quotes
                    lines[line_no] = line.rstrip() + '"""\n'
                    repaired = True

            if repaired:
                backup_path = self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                if self.verify_syntax(file_path):
                    self.repairs_made.append({
                        "file": str(file_path),
                        "error_type": "unterminated_strings",
                        "backup": str(backup_path),
                        "success": True
                    })
                    return True
                else:
                    shutil.copy2(backup_path, file_path)
                    return False

        except Exception as e:
            print(f"Error repairing {file_path}: {e}")
            return False

        return False

    def repair_indentation_errors(self, file_path: Path, error_info: Dict) -> bool:
        """Repair indentation errors."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            line_no = error_info.get('line', 1) - 1
            message = error_info.get('message', '')

            repaired = False

            if "expected an indented block" in message:
                # Add a pass statement for empty blocks
                if line_no < len(lines):
                    indent = len(lines[line_no]) - len(lines[line_no].lstrip())
                    lines.insert(line_no, ' ' * (indent + 4) + 'pass\n')
                    repaired = True

            elif "unexpected unindent" in message:
                # Fix indentation by aligning with previous line
                if line_no > 0 and line_no < len(lines):
                    prev_line = lines[line_no - 1]
                    current_line = lines[line_no]
                    prev_indent = len(prev_line) - len(prev_line.lstrip())
                    lines[line_no] = ' ' * prev_indent + current_line.lstrip()
                    repaired = True

            if repaired:
                backup_path = self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                if self.verify_syntax(file_path):
                    self.repairs_made.append({
                        "file": str(file_path),
                        "error_type": "indentation_errors",
                        "backup": str(backup_path),
                        "success": True
                    })
                    return True
                else:
                    shutil.copy2(backup_path, file_path)
                    return False

        except Exception as e:
            print(f"Error repairing {file_path}: {e}")
            return False

        return False

    def repair_invalid_syntax(self, file_path: Path, error_info: Dict) -> bool:
        """Repair invalid syntax errors (like escape sequences)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            message = error_info.get('message', '')
            repaired = False

            if "invalid escape sequence" in message or "truncated \\uXXXX escape" in message:
                # Fix raw string literals for Windows paths
                content = re.sub(r'\\([cCdDeE])\\', r'\\\\\\1\\\\', content)
                content = re.sub(r'([\"\'])([^\"\']*\\[cCdDeE]\\[^\"\']*)([\"\'])', r'r\1\2\3', content)
                repaired = True

            if repaired:
                backup_path = self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                if self.verify_syntax(file_path):
                    self.repairs_made.append({
                        "file": str(file_path),
                        "error_type": "invalid_syntax",
                        "backup": str(backup_path),
                        "success": True
                    })
                    return True
                else:
                    shutil.copy2(backup_path, file_path)
                    return False

        except Exception as e:
            print(f"Error repairing {file_path}: {e}")
            return False

        return False

    def verify_syntax(self, file_path: Path) -> bool:
        """Verify that a file has valid syntax after repair."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content, filename=str(file_path))
            return True
        except:
            return False

    def repair_file(self, error_info: Dict) -> bool:
        """Repair a single file based on its error information."""
        file_path = Path(error_info['file'])

        if not file_path.exists():
            print(f"File not found: {file_path}")
            return False

        category = error_info.get('category', '')

        print(f"Repairing {file_path} (Category: {category})")

        if category == "mismatched_parentheses":
            return self.repair_mismatched_parentheses(file_path, error_info)
        elif category == "unterminated_strings":
            return self.repair_unterminated_strings(file_path, error_info)
        elif category == "indentation_errors":
            return self.repair_indentation_errors(file_path, error_info)
        elif category == "invalid_syntax":
            return self.repair_invalid_syntax(file_path, error_info)
        else:
            print(f"Unknown error category: {category}")
            return False

    def repair_all_errors(self, max_files: int = None) -> Dict:
        """Repair all syntax errors found in the report."""
        report = self.load_error_report()
        errors = report.get('detailed_errors', [])

        if max_files:
            errors = errors[:max_files]

        total_errors = len(errors)
        successful_repairs = 0

        print(f"Starting repair of {total_errors} syntax errors...")
        print("=" * 60)

        for i, error_info in enumerate(errors):
            if i % 50 == 0:
                print(f"Progress: {i}/{total_errors} files processed")

            if self.repair_file(error_info):
                successful_repairs += 1
                print(f"[SUCCESS] Successfully repaired: {error_info['file']}")
            else:
                print(f"[FAILED] Failed to repair: {error_info['file']}")

        print("=" * 60)
        print(f"Repair Summary:")
        print(f"Total files processed: {total_errors}")
        print(f"Successfully repaired: {successful_repairs}")
        print(f"Failed repairs: {total_errors - successful_repairs}")
        print(f"Success rate: {(successful_repairs/total_errors)*100:.1f}%")

        return {
            "total_processed": total_errors,
            "successful_repairs": successful_repairs,
            "failed_repairs": total_errors - successful_repairs,
            "repairs_made": self.repairs_made
        }

    def save_repair_report(self, results: Dict, filename: str = "syntax_repair_report.json"):
        """Save the repair results to a JSON file."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "repair_summary": results,
            "backups_location": str(self.backup_dir)
        }

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Repair report saved to {filename}")


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description="Repair syntax errors in test files")
    parser.add_argument("--max-files", type=int, help="Maximum number of files to repair (for testing)")
    parser.add_argument("--report", default="syntax_error_analysis_report.json", help="Input error report file")

    args = parser.parse_args()

    print("Starting syntax error repair for test infrastructure...")
    print("=" * 60)

    repairer = SyntaxErrorRepairer(args.report)
    results = repairer.repair_all_errors(max_files=args.max_files)
    repairer.save_repair_report(results)

    if results["successful_repairs"] > 0:
        print(f"\n[SUCCESS] Successfully repaired {results['successful_repairs']} files!")
        print(f"Backups stored in: {repairer.backup_dir}")
        return 0
    else:
        print(f"\n[FAILED] No files were successfully repaired.")
        return 1


if __name__ == "__main__":
    exit(main())