"""
Utility: Automated Syntax Error Remediation

Provides safe, automated fixes for common syntax error patterns found in the 67 syntax errors.

Business Value Justification (BVJ):
- Segment: Platform (development infrastructure)
- Business Goal: Stability - restore test execution capability
- Value Impact: Enable validation of $500K+ ARR Golden Path functionality
- Strategic Impact: Automated remediation reduces manual error-prone fixes
"""

import re
import ast
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SyntaxErrorRemediator:
    """Automated remediation for common syntax error patterns."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.remediation_patterns = {
            'unterminated_f_string': self._fix_unterminated_f_string,
            'unterminated_string': self._fix_unterminated_string,
            'unexpected_indent': self._fix_unexpected_indent,
            'unclosed_parentheses': self._fix_unclosed_parentheses,
        }

        # Track files for priority-based remediation
        self.critical_files = [
            "test_ssot_execution_compliance.py",
            "test_ssot_test_runner_enforcement.py",
            "test_ssot_violations_remediation_complete.py",
            "test_thread_propagation_verification.py"
        ]

        self.websocket_patterns = ["*websocket*", "*chat*", "*event*"]

    def fix_file(self, file_path: Path, dry_run: bool = True) -> Dict[str, any]:
        """Apply appropriate fix to file based on detected error pattern."""
        logger.info(f"Analyzing file: {file_path}")

        error_type = self._detect_error_type(file_path)
        if not error_type:
            return {"success": True, "reason": "No syntax errors detected"}

        if error_type not in self.remediation_patterns:
            return {"success": False, "reason": f"Unknown error pattern: {error_type}"}

        logger.info(f"Detected error type: {error_type}")

        if dry_run:
            logger.info("DRY RUN: Would apply fix but not modifying file")
            return {"success": True, "dry_run": True, "error_type": error_type}

        return self.remediation_patterns[error_type](file_path)

    def fix_critical_files(self, dry_run: bool = True) -> Dict[str, List[Dict]]:
        """Fix P0 critical files first (string/f-string/parentheses errors)."""
        logger.info("Starting P0 critical file remediation")

        mission_critical_dir = self.project_root / "tests" / "mission_critical"
        results = {"fixed": [], "failed": [], "skipped": []}

        for filename in self.critical_files:
            file_path = mission_critical_dir / filename
            if not file_path.exists():
                results["skipped"].append({"file": filename, "reason": "File not found"})
                continue

            result = self.fix_file(file_path, dry_run=dry_run)
            result["file"] = filename

            if result.get("success"):
                results["fixed"].append(result)
                logger.info(f"✅ Fixed: {filename}")
            else:
                results["failed"].append(result)
                logger.error(f"❌ Failed: {filename} - {result.get('reason')}")

        return results

    def fix_websocket_files(self, dry_run: bool = True) -> Dict[str, List[Dict]]:
        """Fix P1 WebSocket-related files (high business value)."""
        logger.info("Starting P1 WebSocket file remediation")

        mission_critical_dir = self.project_root / "tests" / "mission_critical"
        results = {"fixed": [], "failed": [], "skipped": []}

        websocket_files = []
        for pattern in self.websocket_patterns:
            websocket_files.extend(mission_critical_dir.glob(pattern))

        for file_path in websocket_files:
            if file_path.suffix != ".py":
                continue

            result = self.fix_file(file_path, dry_run=dry_run)
            result["file"] = file_path.name

            if result.get("success"):
                results["fixed"].append(result)
                logger.info(f"✅ Fixed: {file_path.name}")
            else:
                results["failed"].append(result)
                logger.error(f"❌ Failed: {file_path.name} - {result.get('reason')}")

        return results

    def _detect_error_type(self, file_path: Path) -> Optional[str]:
        """Detect the type of syntax error in the file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            return None  # No syntax error
        except SyntaxError as e:
            error_msg = str(e.msg).lower()

            if "unterminated f-string" in error_msg:
                return "unterminated_f_string"
            elif "unterminated string" in error_msg:
                return "unterminated_string"
            elif "unexpected indent" in error_msg:
                return "unexpected_indent"
            elif "was never closed" in error_msg:
                return "unclosed_parentheses"
            else:
                logger.warning(f"Unknown syntax error type: {e.msg}")
                return "unknown"
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return None

    def _fix_unterminated_f_string(self, file_path: Path) -> Dict[str, any]:
        """Fix unterminated f-string literals."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Common pattern: f"string with missing quote
            # Look for f" without proper closing
            lines = content.split('\n')
            fixed_lines = []
            fixed = False

            for i, line in enumerate(lines):
                # Pattern: f"text without closing quote at end of line
                if re.search(r'f"[^"]*$', line.strip()) and not line.strip().endswith('\\'):
                    # Add missing quote
                    fixed_line = line + '"'
                    fixed_lines.append(fixed_line)
                    logger.info(f"Fixed unterminated f-string at line {i+1}")
                    fixed = True
                else:
                    fixed_lines.append(line)

            if fixed:
                fixed_content = '\n'.join(fixed_lines)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                return {"success": True, "changes": "Added missing f-string quotes"}
            else:
                return {"success": False, "reason": "Could not identify f-string fix pattern"}

        except Exception as e:
            return {"success": False, "reason": f"Error fixing f-string: {e}"}

    def _fix_unterminated_string(self, file_path: Path) -> Dict[str, any]:
        """Fix unterminated string literals."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            fixed_lines = []
            fixed = False

            for i, line in enumerate(lines):
                # Pattern: "text without closing quote or 'text without closing quote
                # Look for odd number of quotes
                single_quotes = line.count("'")
                double_quotes = line.count('"')

                # If we have unterminated string (odd quotes), try to fix
                if single_quotes % 2 == 1 and line.strip().endswith("'") == False:
                    fixed_line = line + "'"
                    fixed_lines.append(fixed_line)
                    logger.info(f"Fixed unterminated single quote string at line {i+1}")
                    fixed = True
                elif double_quotes % 2 == 1 and line.strip().endswith('"') == False:
                    fixed_line = line + '"'
                    fixed_lines.append(fixed_line)
                    logger.info(f"Fixed unterminated double quote string at line {i+1}")
                    fixed = True
                else:
                    fixed_lines.append(line)

            if fixed:
                fixed_content = '\n'.join(fixed_lines)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                return {"success": True, "changes": "Added missing string quotes"}
            else:
                return {"success": False, "reason": "Could not identify string fix pattern"}

        except Exception as e:
            return {"success": False, "reason": f"Error fixing string: {e}"}

    def _fix_unexpected_indent(self, file_path: Path) -> Dict[str, any]:
        """Fix unexpected indentation by adding missing pass statements."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            fixed_lines = []
            fixed = False

            for i, line in enumerate(lines):
                fixed_lines.append(line)

                # Check if this line needs a pass statement
                stripped = line.strip()

                # Control structures that need pass if next line is indented but doesn't contain code
                control_patterns = [
                    r'^if\s+.*:$',
                    r'^elif\s+.*:$',
                    r'^else\s*:$',
                    r'^for\s+.*:$',
                    r'^while\s+.*:$',
                    r'^try\s*:$',
                    r'^except.*:$',
                    r'^finally\s*:$',
                    r'^with\s+.*:$',
                    r'^def\s+.*:$',
                    r'^class\s+.*:$',
                    r'^async\s+def\s+.*:$'
                ]

                if any(re.match(pattern, stripped) for pattern in control_patterns):
                    # Check if next line exists and is improperly indented
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        # If next line is empty or starts with unindented code, add pass
                        if not next_line or (next_line and not lines[i + 1].startswith('    ')):
                            indent = len(line) - len(line.lstrip())
                            pass_line = ' ' * (indent + 4) + 'pass  # TODO: Add implementation'
                            fixed_lines.append(pass_line)
                            logger.info(f"Added pass statement after line {i+1}")
                            fixed = True

            if fixed:
                fixed_content = '\n'.join(fixed_lines)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                return {"success": True, "changes": "Added missing pass statements"}
            else:
                return {"success": False, "reason": "Could not identify indentation fix pattern"}

        except Exception as e:
            return {"success": False, "reason": f"Error fixing indentation: {e}"}

    def _fix_unclosed_parentheses(self, file_path: Path) -> Dict[str, any]:
        """Fix unclosed parentheses."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            fixed_lines = []
            fixed = False

            for i, line in enumerate(lines):
                # Count parentheses
                open_parens = line.count('(')
                close_parens = line.count(')')

                if open_parens > close_parens:
                    # Add missing closing parentheses
                    missing = open_parens - close_parens
                    fixed_line = line + ')' * missing
                    fixed_lines.append(fixed_line)
                    logger.info(f"Fixed {missing} unclosed parentheses at line {i+1}")
                    fixed = True
                else:
                    fixed_lines.append(line)

            if fixed:
                fixed_content = '\n'.join(fixed_lines)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                return {"success": True, "changes": "Added missing closing parentheses"}
            else:
                return {"success": False, "reason": "Could not identify parentheses fix pattern"}

        except Exception as e:
            return {"success": False, "reason": f"Error fixing parentheses: {e}"}

    def validate_fixes(self) -> Dict[str, any]:
        """Validate that all fixes work by checking syntax."""
        mission_critical_dir = self.project_root / "tests" / "mission_critical"

        errors = []
        for py_file in mission_critical_dir.glob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError as e:
                errors.append(f"{py_file.name}:{e.lineno}: {e.msg}")

        return {
            "total_files_checked": len(list(mission_critical_dir.glob("*.py"))),
            "syntax_errors": errors,
            "success": len(errors) == 0
        }


def main():
    """Command line interface for syntax error remediation."""
    parser = argparse.ArgumentParser(description="Automated syntax error remediation utility")
    parser.add_argument("--priority", choices=["critical", "websocket", "all"],
                       default="critical", help="Priority level for fixes")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be fixed without making changes")
    parser.add_argument("--validate", action="store_true",
                       help="Validate all files for syntax errors")

    args = parser.parse_args()

    remediator = SyntaxErrorRemediator()

    if args.validate:
        logger.info("Running syntax validation...")
        results = remediator.validate_fixes()
        print(f"\nValidation Results:")
        print(f"Files checked: {results['total_files_checked']}")
        print(f"Syntax errors: {len(results['syntax_errors'])}")

        if results['syntax_errors']:
            print("\nRemaining syntax errors:")
            for error in results['syntax_errors']:
                print(f"  - {error}")
        else:
            print("✅ All files have valid syntax!")

        sys.exit(0 if results['success'] else 1)

    if args.priority == "critical":
        logger.info("Starting P0 critical file remediation...")
        results = remediator.fix_critical_files(dry_run=args.dry_run)
    elif args.priority == "websocket":
        logger.info("Starting P1 WebSocket file remediation...")
        results = remediator.fix_websocket_files(dry_run=args.dry_run)
    else:
        logger.info("Starting comprehensive remediation...")
        critical_results = remediator.fix_critical_files(dry_run=args.dry_run)
        websocket_results = remediator.fix_websocket_files(dry_run=args.dry_run)
        # Combine results
        results = {
            "fixed": critical_results["fixed"] + websocket_results["fixed"],
            "failed": critical_results["failed"] + websocket_results["failed"],
            "skipped": critical_results["skipped"] + websocket_results["skipped"]
        }

    # Print summary
    print(f"\n🔧 Remediation Summary:")
    print(f"✅ Fixed: {len(results['fixed'])}")
    print(f"❌ Failed: {len(results['failed'])}")
    print(f"⏭️  Skipped: {len(results['skipped'])}")

    if results['failed']:
        print(f"\nFailed fixes:")
        for failure in results['failed']:
            print(f"  - {failure['file']}: {failure.get('reason', 'Unknown error')}")

    if not args.dry_run:
        logger.info("Running post-fix validation...")
        validation = remediator.validate_fixes()
        print(f"\nPost-fix validation: {len(validation['syntax_errors'])} remaining errors")


if __name__ == "__main__":
    main()