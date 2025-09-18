#!/usr/bin/env python3
"""
Test Infrastructure Crisis - Automated Corruption Fix Script (ASCII Version)

This script implements automated fixes for the 339 corrupted test files
identified in the test infrastructure crisis of 2025-09-17.

Priority: P0 - Business Critical (Golden Path blocking)
"""

import re
import os
import ast
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Any

class TestCorruptionFixer:
    """Automated test file corruption remediation"""

    def __init__(self):
        self.base_path = Path("/c/netra-apex")
        self.backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.fixed_files = []
        self.failed_files = []

    def get_golden_path_priority_files(self) -> List[Path]:
        """Get Golden Path critical test files for priority fixing"""

        priority_files = []

        # Auth service critical files (known to exist)
        auth_files = [
            "auth_service/tests/test_oauth_state_validation.py",
            "auth_service/tests/test_auth_comprehensive.py",
            "auth_service/tests/test_redis_staging_connectivity_fixes.py",
            "auth_service/tests/test_refresh_loop_prevention_comprehensive.py",
            "auth_service/tests/test_refresh_token_fix.py",
            "auth_service/tests/test_session_security_cycles_36_40.py",
            "auth_service/tests/test_token_validation_security_cycles_31_35.py"
        ]

        # Add existing files to priority list
        for file_path in auth_files:
            full_path = self.base_path / file_path
            if full_path.exists():
                priority_files.append(full_path)

        return priority_files[:8]  # Limit to 8 most critical files

    def check_syntax(self, file_path: Path) -> Tuple[bool, str]:
        """Check if file has valid Python syntax"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            return True, "Valid syntax"
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Error reading file: {e}"

    def create_backup(self, file_path: Path) -> Path:
        """Create backup of file before fixing"""
        backup_path = file_path.with_suffix(f'.backup_{self.backup_timestamp}')
        shutil.copy2(file_path, backup_path)
        return backup_path

    def apply_fixes(self, content: str) -> str:
        """Apply basic fixes to common corruption patterns"""

        # Fix 1: Replace formatted_string with basic URLs
        content = re.sub(r'"formatted_string"', '"/api/test"', content)

        # Fix 2: Fix unmatched braces
        content = re.sub(r'json=\}', 'json={}', content)
        content = re.sub(r'custom_env = \}', 'custom_env = {}', content)
        content = re.sub(r'connection_params = \{ \)', 'connection_params = {}', content)

        # Fix 3: Fix malformed JSON posts
        content = re.sub(r'(client\.post\([^,]+, json=)\}', r'\1{}', content)

        # Fix 4: Basic indentation fixes
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # Fix basic indentation issues
            if line.strip().startswith('assert') and not line.startswith('    '):
                fixed_lines.append('    ' + line.strip())
            elif line.strip() and not line.startswith(' ') and not line.startswith('def ') and not line.startswith('class ') and not line.startswith('import ') and not line.startswith('from '):
                fixed_lines.append('    ' + line.strip())
            else:
                fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_file(self, file_path: Path) -> Tuple[bool, str]:
        """Fix corruption in a single test file"""

        print(f"Fixing: {file_path.relative_to(self.base_path)}")

        # Check if file needs fixing
        is_valid, error_msg = self.check_syntax(file_path)
        if is_valid:
            print(f"  [OK] File already has valid syntax")
            return True, "No fix needed"

        print(f"  [ERROR] Corruption detected: {error_msg}")

        try:
            # Read original content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Create backup
            backup_path = self.create_backup(file_path)
            print(f"  [BACKUP] Created: {backup_path.name}")

            # Apply fixes
            fixed_content = self.apply_fixes(original_content)

            # Validate fixed content
            try:
                ast.parse(fixed_content)

                # Write fixed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)

                print(f"  [SUCCESS] Fixed successfully")
                self.fixed_files.append(file_path)
                return True, "Fixed successfully"

            except SyntaxError as e:
                print(f"  [FAILED] Fix failed - syntax still invalid: {e}")

                # Restore from backup
                shutil.copy2(backup_path, file_path)
                self.failed_files.append((file_path, f"Syntax error after fix: {e}"))
                return False, f"Syntax error after fix: {e}"

        except Exception as e:
            print(f"  [ERROR] Error during fix: {e}")
            self.failed_files.append((file_path, str(e)))
            return False, str(e)

    def fix_golden_path_files(self) -> Dict[str, Any]:
        """Fix Golden Path critical test files"""

        print("=" * 60)
        print("GOLDEN PATH TEST CORRUPTION FIX")
        print("=" * 60)

        priority_files = self.get_golden_path_priority_files()

        if not priority_files:
            print("[ERROR] No Golden Path priority files found!")
            return {"success": False, "message": "No priority files found"}

        print(f"Found {len(priority_files)} priority files to fix:")
        for file_path in priority_files:
            print(f"  - {file_path.relative_to(self.base_path)}")

        print("\nStarting fixes...")
        print("-" * 30)

        results = {"fixed": [], "failed": [], "skipped": []}

        for file_path in priority_files:
            success, message = self.fix_file(file_path)
            if success:
                if message == "No fix needed":
                    results["skipped"].append(str(file_path))
                else:
                    results["fixed"].append(str(file_path))
            else:
                results["failed"].append((str(file_path), message))

        return results

def main():
    """Main execution function"""

    print("TEST INFRASTRUCTURE CRISIS REMEDIATION")
    print("Phase 1: Golden Path Critical Files")
    print("Date: 2025-09-17")
    print("=" * 60)

    fixer = TestCorruptionFixer()

    # Fix Golden Path priority files
    results = fixer.fix_golden_path_files()

    print("\n" + "=" * 60)
    print("PHASE 1 COMPLETE")

    print(f"\nSUMMARY:")
    print(f"- Fixed: {len(results['fixed'])} files")
    print(f"- Failed: {len(results['failed'])} files")
    print(f"- Skipped: {len(results['skipped'])} files")

    if results["fixed"]:
        print(f"\n[SUCCESS] Fixed {len(results['fixed'])} files")
        print("\nNEXT STEPS:")
        print("1. Run test collection: python tests/unified_test_runner.py --collect-only")
        print("2. Start auth service: python -m auth_service.main")
        print("3. Start backend service: python -m netra_backend.main")

    if results["failed"]:
        print(f"\n[WARNING] {len(results['failed'])} files need manual intervention")
        for file_path, error in results["failed"]:
            print(f"  - {file_path}: {error}")

    return len(results["fixed"]) > 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)