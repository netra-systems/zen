#!/usr/bin/env python3
"""
Targeted Critical File Repair Script
Issue #837 - Emergency Test File Syntax Repair

Manual repair of the 19 critical test files with syntax errors.
"""

import ast
import re
import shutil
from pathlib import Path
from datetime import datetime


class TargetedCriticalRepairer:
    def __init__(self):
        self.backup_dir = Path("critical_repair_backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.repairs_made = []

    def create_backup(self, file_path: Path) -> Path:
        """Create backup before repair."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{file_path.name}.backup_{timestamp}"
        shutil.copy2(file_path, backup_path)
        return backup_path

    def verify_syntax(self, file_path: Path) -> bool:
        """Verify file has valid syntax."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content, filename=str(file_path))
            return True
        except:
            return False

    def repair_enhanced_error_handling_tests(self, file_path: Path) -> bool:
        """Fix tests/enhanced_error_handling_tests.py indentation."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Fix line 11 indentation
            if len(lines) > 10:
                line_11 = lines[10]
                if 'raise RuntimeError' in line_11:
                    lines[10] = '            ' + line_11.lstrip()

                    backup = self.create_backup(file_path)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)

                    if self.verify_syntax(file_path):
                        return True
                    else:
                        shutil.copy2(backup, file_path)
        except Exception as e:
            print(f"Error repairing {file_path}: {e}")
        return False

    def repair_unicode_escape_files(self, file_path: Path) -> bool:
        """Fix unicode escape sequence errors by using raw strings."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # Fix Windows path escapes by making them raw strings
            # Pattern: "...\\u..." or "...\\c\\" etc
            content = re.sub(r'(["\'])([^"\']*\\[a-zA-Z]\\[^"\']*)\1', r'r\1\2\1', content)

            # Alternative fix: escape backslashes
            content = re.sub(r'\\([a-zA-Z])\\', r'\\\\\\1\\\\', content)

            if content != original_content:
                backup = self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                if self.verify_syntax(file_path):
                    return True
                else:
                    shutil.copy2(backup, file_path)
        except Exception as e:
            print(f"Error repairing {file_path}: {e}")
        return False

    def repair_bracket_mismatch(self, file_path: Path) -> bool:
        """Fix bracket/parenthesis mismatches."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            modified = False
            for i, line in enumerate(lines):
                # Fix { ) pattern
                if '{ )' in line:
                    lines[i] = line.replace('{ )', '{')
                    modified = True
                # Fix obvious ) -> } cases
                elif line.strip().endswith(')') and '{' in line and '}' not in line:
                    lines[i] = line.replace(')', '}')
                    modified = True

            if modified:
                backup = self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                if self.verify_syntax(file_path):
                    return True
                else:
                    shutil.copy2(backup, file_path)
        except Exception as e:
            print(f"Error repairing {file_path}: {e}")
        return False

    def repair_unterminated_string(self, file_path: Path) -> bool:
        """Fix unterminated string literals."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            modified = False
            for i, line in enumerate(lines):
                # Count quotes
                single_quotes = line.count("'")
                double_quotes = line.count('"')

                # Fix odd number of quotes
                if single_quotes % 2 == 1 and double_quotes % 2 == 0:
                    lines[i] = line.rstrip() + "'\n"
                    modified = True
                elif double_quotes % 2 == 1 and single_quotes % 2 == 0:
                    lines[i] = line.rstrip() + '"\n'
                    modified = True

            if modified:
                backup = self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                if self.verify_syntax(file_path):
                    return True
                else:
                    shutil.copy2(backup, file_path)
        except Exception as e:
            print(f"Error repairing {file_path}: {e}")
        return False

    def repair_indentation_error(self, file_path: Path) -> bool:
        """Fix indentation errors."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Add pass statements to empty blocks
            modified = False
            for i, line in enumerate(lines):
                if line.strip().endswith(':') and i + 1 < len(lines):
                    next_line = lines[i + 1] if i + 1 < len(lines) else ""
                    # If next line is not indented or is empty, add pass
                    if (not next_line.strip() or
                        (next_line.strip() and len(next_line) - len(next_line.lstrip()) <= len(line) - len(line.lstrip()))):
                        indent = len(line) - len(line.lstrip()) + 4
                        lines.insert(i + 1, ' ' * indent + 'pass\n')
                        modified = True
                        break

            if modified:
                backup = self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                if self.verify_syntax(file_path):
                    return True
                else:
                    shutil.copy2(backup, file_path)
        except Exception as e:
            print(f"Error repairing {file_path}: {e}")
        return False

    def repair_critical_files(self) -> dict:
        """Repair all critical files with targeted fixes."""

        critical_files = [
            "tests/enhanced_error_handling_tests.py",
            "tests/unit/test_loguru_gcp_formatter_fix.py",
            "tests/unit/test_universal_registry.py",
            "tests/unit/test_websocket_notifications.py",
            "tests/unit/test_websocket_warnings_fix.py",
            "tests/unit/test_health_monitoring_fix_verification.py",
            "tests/e2e/dev_launcher_real_system.py",
            "tests/e2e/validate_orchestration_tests.py",
            "tests/e2e/demo_usage.py",
            "tests/e2e/llm_initialization_helpers.py",
            "tests/e2e/agent_state_validator.py",
            "tests/conftest_new.py",
            "tests/integration/cors_validation_utils.py",
            "tests/mission_critical/run_ssot_orchestration_tests.py",
            "tests/mission_critical/validate_docker_stability.py",
            "tests/mission_critical/validate_loud_failures.py",
            "auth_service/tests/unit/test_auth_environment_urls.py",
            "auth_service/tests/unit/test_auth_endpoint_routing_regression_prevention.py",
        ]

        results = {
            "total_files": len(critical_files),
            "successful_repairs": 0,
            "failed_repairs": 0,
            "repairs_made": []
        }

        print(f"Attempting targeted repair of {len(critical_files)} critical files...")
        print("=" * 60)

        for file_path_str in critical_files:
            file_path = Path(file_path_str)

            if not file_path.exists():
                print(f"[SKIP] File not found: {file_path}")
                continue

            print(f"Repairing: {file_path}")

            success = False

            # Try different repair strategies based on file characteristics
            if "enhanced_error_handling_tests.py" in str(file_path):
                success = self.repair_enhanced_error_handling_tests(file_path)
            elif any(pattern in str(file_path) for pattern in ["loguru", "universal_registry", "websocket_notifications", "websocket_warnings", "health_monitoring", "auth_environment", "auth_endpoint"]):
                success = self.repair_unicode_escape_files(file_path)
            elif any(pattern in str(file_path) for pattern in ["dev_launcher_real_system", "run_ssot_orchestration"]):
                success = self.repair_bracket_mismatch(file_path)
            elif any(pattern in str(file_path) for pattern in ["validate_orchestration_tests", "demo_usage", "validate_loud_failures"]):
                success = self.repair_unterminated_string(file_path)
            elif any(pattern in str(file_path) for pattern in ["llm_initialization_helpers", "validate_docker_stability", "conftest_new"]):
                success = self.repair_indentation_error(file_path)
            else:
                # Try all strategies
                success = (self.repair_unicode_escape_files(file_path) or
                          self.repair_bracket_mismatch(file_path) or
                          self.repair_unterminated_string(file_path) or
                          self.repair_indentation_error(file_path))

            if success:
                results["successful_repairs"] += 1
                results["repairs_made"].append(str(file_path))
                print(f"  [SUCCESS] Repaired successfully")
            else:
                results["failed_repairs"] += 1
                print(f"  [FAILED] Could not repair")

        print("=" * 60)
        print(f"Critical File Repair Summary:")
        print(f"Total files: {results['total_files']}")
        print(f"Successfully repaired: {results['successful_repairs']}")
        print(f"Failed repairs: {results['failed_repairs']}")

        if results['total_files'] > 0:
            success_rate = (results['successful_repairs'] / results['total_files']) * 100
            print(f"Success rate: {success_rate:.1f}%")

        return results


def main():
    """Main execution function."""
    print("Starting targeted repair of 19 critical test files...")
    print("=" * 60)

    repairer = TargetedCriticalRepairer()
    results = repairer.repair_critical_files()

    if results["successful_repairs"] > 0:
        print(f"\n[SUCCESS] Repaired {results['successful_repairs']} critical test files!")
        print("This should significantly improve test collection capability.")

        # Test syntax of repaired files
        print("\nVerifying repairs...")
        for file_path_str in results["repairs_made"]:
            file_path = Path(file_path_str)
            if repairer.verify_syntax(file_path):
                print(f"✓ {file_path} - syntax verified")
            else:
                print(f"✗ {file_path} - syntax still invalid")

        return 0
    else:
        print("\n[INFO] No files were successfully repaired.")
        print("Manual intervention may be needed.")
        return 1


if __name__ == "__main__":
    exit(main())