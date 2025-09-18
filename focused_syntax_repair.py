#!/usr/bin/env python3
"""
Focused Syntax Repair Script for Test Infrastructure
Issue #837 - Emergency Test File Syntax Repair

This script focuses on the most easily repairable and common syntax patterns
to quickly restore test collection capability.
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


class FocusedSyntaxRepairer:
    def __init__(self, report_file: str = "syntax_error_analysis_report.json"):
        self.report_file = report_file
        self.repairs_made = []
        self.backup_dir = Path("focused_repair_backups")
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

    def verify_syntax(self, file_path: Path) -> bool:
        """Verify that a file has valid syntax after repair."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content, filename=str(file_path))
            return True
        except:
            return False

    def repair_dict_curly_paren_pattern(self, file_path: Path) -> bool:
        """
        Repair the pattern: variable = { )
        where the dictionary entries are on subsequent lines
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # Pattern: variable = { ) followed by key-value pairs
            pattern = r'(\w+\s*=\s*\{\s*\))\s*\n((?:\s*[\'"][^\'"]+[\'"]\s*:\s*[^\n]+\n?)+)'

            def replace_dict_pattern(match):
                var_assignment = match.group(1)
                dict_entries = match.group(2)

                # Extract variable name
                var_name = var_assignment.split('=')[0].strip()

                # Process the dictionary entries
                lines = dict_entries.strip().split('\n')
                processed_entries = []

                for line in lines:
                    line = line.strip()
                    if line and ':' in line:
                        processed_entries.append('    ' + line)

                if processed_entries:
                    # Add comma to all but last entry
                    for i in range(len(processed_entries) - 1):
                        if not processed_entries[i].endswith(','):
                            processed_entries[i] += ','

                    result = f"{var_name} = {{\n" + '\n'.join(processed_entries) + '\n}'
                    return result

                return match.group(0)  # Return original if can't parse

            content = re.sub(pattern, replace_dict_pattern, content, flags=re.MULTILINE)

            if content != original_content:
                backup_path = self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                if self.verify_syntax(file_path):
                    return True
                else:
                    # Restore backup if repair didn't work
                    shutil.copy2(backup_path, file_path)
                    return False

        except Exception as e:
            print(f"Error in dict repair for {file_path}: {e}")
            return False

        return False

    def repair_simple_mismatched_brackets(self, file_path: Path, error_info: Dict) -> bool:
        """Repair simple mismatched bracket cases."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            line_no = error_info.get('line', 1) - 1
            if line_no < 0 or line_no >= len(lines):
                return False

            line = lines[line_no]
            message = error_info.get('message', '')
            original_line = line

            # Simple cases that are safe to fix
            if "closing parenthesis ')' does not match opening parenthesis '{'" in message:
                # If the line only has one ) at the end, replace with }
                if line.count(')') == 1 and line.strip().endswith(')'):
                    lines[line_no] = line.replace(')', '}')

            elif "closing parenthesis ')' does not match opening parenthesis '['" in message:
                # If the line only has one ) at the end, replace with ]
                if line.count(')') == 1 and line.strip().endswith(')'):
                    lines[line_no] = line.replace(')', ']')

            elif "unmatched ')'" in message:
                # Remove extra ) if there's an obvious mismatch
                open_count = line.count('(')
                close_count = line.count(')')
                if close_count > open_count:
                    lines[line_no] = line[:line.rfind(')')] + line[line.rfind(')') + 1:]

            if lines[line_no] != original_line:
                backup_path = self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                if self.verify_syntax(file_path):
                    return True
                else:
                    shutil.copy2(backup_path, file_path)
                    return False

        except Exception as e:
            print(f"Error in bracket repair for {file_path}: {e}")
            return False

        return False

    def repair_simple_unterminated_strings(self, file_path: Path, error_info: Dict) -> bool:
        """Repair simple unterminated string cases."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            line_no = error_info.get('line', 1) - 1
            if line_no < 0 or line_no >= len(lines):
                return False

            line = lines[line_no]
            original_line = line

            # Count quotes to determine which type is missing
            single_quotes = line.count("'")
            double_quotes = line.count('"')

            # Only fix if there's an odd number of one type of quote
            if single_quotes % 2 == 1 and double_quotes % 2 == 0:
                # Add missing single quote at end
                lines[line_no] = line.rstrip() + "'\n"
            elif double_quotes % 2 == 1 and single_quotes % 2 == 0:
                # Add missing double quote at end
                lines[line_no] = line.rstrip() + '"\n'

            if lines[line_no] != original_line:
                backup_path = self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                if self.verify_syntax(file_path):
                    return True
                else:
                    shutil.copy2(backup_path, file_path)
                    return False

        except Exception as e:
            print(f"Error in string repair for {file_path}: {e}")
            return False

        return False

    def repair_simple_indentation(self, file_path: Path, error_info: Dict) -> bool:
        """Repair simple indentation cases."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            line_no = error_info.get('line', 1) - 1
            message = error_info.get('message', '')

            if "expected an indented block" in message and line_no < len(lines):
                # Add pass statement for empty blocks
                current_line = lines[line_no] if line_no < len(lines) else ""
                indent = len(current_line) - len(current_line.lstrip()) if current_line.strip() else 4

                lines.insert(line_no, ' ' * (indent + 4) + 'pass\n')

                backup_path = self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                if self.verify_syntax(file_path):
                    return True
                else:
                    shutil.copy2(backup_path, file_path)
                    return False

        except Exception as e:
            print(f"Error in indentation repair for {file_path}: {e}")
            return False

        return False

    def repair_file(self, error_info: Dict) -> bool:
        """Attempt to repair a file using focused strategies."""
        file_path = Path(error_info['file'])

        if not file_path.exists():
            return False

        category = error_info.get('category', '')
        message = error_info.get('message', '')

        # Try specific pattern repairs first
        if "{ )" in message:
            if self.repair_dict_curly_paren_pattern(file_path):
                return True

        # Try category-based repairs
        if category == "mismatched_parentheses":
            return self.repair_simple_mismatched_brackets(file_path, error_info)
        elif category == "unterminated_strings":
            return self.repair_simple_unterminated_strings(file_path, error_info)
        elif category == "indentation_errors":
            return self.repair_simple_indentation(file_path, error_info)

        return False

    def filter_repairable_errors(self, errors: List[Dict]) -> List[Dict]:
        """Filter errors to focus on the most easily repairable ones."""
        repairable = []

        for error in errors:
            category = error.get('category', '')
            message = error.get('message', '')

            # Skip backup directories to avoid duplicate work
            if 'backup' in error.get('file', '').lower():
                continue

            # Focus on specific repairable patterns
            if category in ['mismatched_parentheses', 'unterminated_strings', 'indentation_errors']:
                # Additional filters for high-success patterns
                if ("{ )" in message or
                    "unmatched ')'" in message or
                    "unterminated string literal" in message or
                    "expected an indented block" in message):
                    repairable.append(error)

        return repairable

    def repair_focused_errors(self) -> Dict:
        """Repair the most easily fixable syntax errors."""
        report = self.load_error_report()
        all_errors = report.get('detailed_errors', [])

        # Filter to focus on repairable errors
        repairable_errors = self.filter_repairable_errors(all_errors)

        print(f"Filtered {len(repairable_errors)} repairable errors from {len(all_errors)} total errors")

        successful_repairs = 0
        total_attempts = len(repairable_errors)

        print(f"Starting focused repair of {total_attempts} syntax errors...")
        print("=" * 60)

        for i, error_info in enumerate(repairable_errors):
            if i % 25 == 0:
                print(f"Progress: {i}/{total_attempts} files processed")

            file_path = error_info['file']
            print(f"Attempting repair: {file_path}")

            if self.repair_file(error_info):
                successful_repairs += 1
                print(f"[SUCCESS] Repaired: {file_path}")
                self.repairs_made.append({
                    "file": file_path,
                    "category": error_info.get('category'),
                    "success": True
                })
            else:
                print(f"[SKIP] Could not repair: {file_path}")

        print("=" * 60)
        print(f"Focused Repair Summary:")
        print(f"Total attempts: {total_attempts}")
        print(f"Successfully repaired: {successful_repairs}")
        print(f"Failed repairs: {total_attempts - successful_repairs}")
        if total_attempts > 0:
            print(f"Success rate: {(successful_repairs/total_attempts)*100:.1f}%")

        return {
            "total_attempted": total_attempts,
            "successful_repairs": successful_repairs,
            "failed_repairs": total_attempts - successful_repairs,
            "repairs_made": self.repairs_made,
            "total_original_errors": len(all_errors)
        }


def main():
    """Main execution function."""
    print("Starting focused syntax error repair for test infrastructure...")
    print("=" * 60)

    repairer = FocusedSyntaxRepairer()
    results = repairer.repair_focused_errors()

    # Save results
    with open("focused_repair_results.json", 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "backups_location": str(repairer.backup_dir)
        }, f, indent=2)

    if results["successful_repairs"] > 0:
        print(f"\n[SUCCESS] Repaired {results['successful_repairs']} files!")
        print(f"Reduced syntax errors from {results['total_original_errors']} to approximately {results['total_original_errors'] - results['successful_repairs']}")
        print(f"Backups stored in: {repairer.backup_dir}")
        return 0
    else:
        print(f"\n[INFO] No files were successfully repaired with focused approach.")
        print(f"May need manual intervention for remaining {results['total_original_errors']} errors.")
        return 1


if __name__ == "__main__":
    exit(main())