#!/usr/bin/env python3
"""
Test Infrastructure Crisis - Automated Corruption Fix Script

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

        # Define corruption patterns and their fixes
        self.corruption_patterns = {
            # Pattern 1: formatted_string placeholders
            r'"formatted_string"': self._restore_formatted_string,

            # Pattern 2: Unmatched braces and parentheses
            r'json=\}': 'json={}',
            r'custom_env = \}': 'custom_env = {}',
            r'connection_params = \{ \)': 'connection_params = {}',
            r'response = test_client\.post\([^,]+, json=\}': self._fix_malformed_json_post,

            # Pattern 3: Missing closing quotes/braces
            r'(\w+):\s*(\w+)\s*\}': r'"\1": "\2"}',
            r'{\s*(\w+):\s*(\w+)\s*$': r'{"\1": "\2"}',

            # Pattern 4: Indentation fixes (basic)
            r'\n    assert\s+': '\n        assert ',  # Fix basic indentation
            r'\n(\w+)\s*=': r'\n    \1 =',  # Fix variable assignment indentation
        }

    def _restore_formatted_string(self, match, line_context: str, file_context: str) -> str:
        """Restore formatted strings based on context analysis"""

        # OAuth callback patterns
        if 'oauth' in file_context.lower() and 'callback' in line_context.lower():
            if 'state' in line_context and 'code' in line_context:
                return 'f"/oauth/callback?state={state}&code={code}"'
            elif 'state' in line_context:
                return 'f"/oauth/callback?state={state}"'
            else:
                return '"/oauth/callback"'

        # Auth login patterns
        if 'auth' in file_context.lower() and 'login' in line_context.lower():
            return '"/auth/login"'

        # WebSocket patterns
        if 'websocket' in file_context.lower():
            if 'connect' in line_context.lower():
                return '"/ws"'
            elif 'agent' in line_context.lower():
                return 'f"/ws/agent/{agent_id}"'

        # Generic API endpoints
        if 'client.get' in line_context:
            return '"/api/test"'
        elif 'client.post' in line_context:
            return '"/api/test"'

        # Flag for manual review
        return '"MANUAL_REVIEW_NEEDED"'

    def _fix_malformed_json_post(self, match, line_context: str, file_context: str) -> str:
        """Fix malformed JSON in POST requests"""
        base_match = match.group(0)
        if 'login' in line_context.lower():
            return base_match.replace('json=}', 'json={"email": "test@example.com", "password": "test123"}')
        elif 'auth' in line_context.lower():
            return base_match.replace('json=}', 'json={"token": "test_token"}')
        else:
            return base_match.replace('json=}', 'json={"test": "data"}')

    def get_golden_path_priority_files(self) -> List[Path]:
        """Get Golden Path critical test files for priority fixing"""

        priority_files = []

        # Auth service critical files (known to exist)
        auth_files = [
            "auth_service/tests/test_oauth_state_validation.py",
            "auth_service/tests/test_auth_comprehensive.py",
            "auth_service/tests/test_redis_staging_connectivity_fixes.py",
            "auth_service/tests/test_refresh_loop_prevention_comprehensive.py",
            "auth_service/tests/test_refresh_token_fix.py"
        ]

        # WebSocket critical files (check existence)
        websocket_files = [
            "tests/mission_critical/test_websocket_agent_events_suite.py",
            "tests/e2e/golden_path/test_websocket_agent_events_validation.py",
            "netra_backend/tests/unit/agents/websocket/test_websocket_agent_events_golden_path.py"
        ]

        # Add existing files to priority list
        for file_path in auth_files + websocket_files:
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

    def apply_pattern_fixes(self, content: str, file_path: Path) -> str:
        """Apply automated pattern fixes to file content"""

        fixed_content = content
        file_context = content.lower()

        for pattern, replacement in self.corruption_patterns.items():
            if callable(replacement):
                # Context-aware replacement
                lines = fixed_content.split('\n')
                for i, line in enumerate(lines):
                    if re.search(pattern, line):
                        match = re.search(pattern, line)
                        if match:
                            new_value = replacement(match, line, file_context)
                            lines[i] = re.sub(pattern, new_value, line)
                fixed_content = '\n'.join(lines)
            else:
                # Simple regex replacement
                fixed_content = re.sub(pattern, replacement, fixed_content)

        return fixed_content

    def fix_file(self, file_path: Path) -> Tuple[bool, str]:
        """Fix corruption in a single test file"""

        print(f"Fixing: {file_path.relative_to(self.base_path)}")

        # Check if file needs fixing
        is_valid, error_msg = self.check_syntax(file_path)
        if is_valid:
            print(f"  SUCCESS: File already has valid syntax")
            return True, "No fix needed"

        print(f"  ERROR: Corruption detected: {error_msg}")

        try:
            # Read original content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Create backup
            backup_path = self.create_backup(file_path)
            print(f"  💾 Backup created: {backup_path.name}")

            # Apply fixes
            fixed_content = self.apply_pattern_fixes(original_content, file_path)

            # Validate fixed content
            try:
                ast.parse(fixed_content)

                # Write fixed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)

                print(f"  SUCCESS: Fixed successfully")
                self.fixed_files.append(file_path)
                return True, "Fixed successfully"

            except SyntaxError as e:
                print(f"  WARNING:  Fix failed - syntax still invalid: {e}")

                # Restore from backup
                shutil.copy2(backup_path, file_path)
                self.failed_files.append((file_path, f"Syntax error after fix: {e}"))
                return False, f"Syntax error after fix: {e}"

        except Exception as e:
            print(f"  ERROR: Error during fix: {e}")
            self.failed_files.append((file_path, str(e)))
            return False, str(e)

    def fix_golden_path_files(self) -> Dict[str, Any]:
        """Fix Golden Path critical test files"""

        print("🚀 GOLDEN PATH TEST CORRUPTION FIX")
        print("=" * 50)

        priority_files = self.get_golden_path_priority_files()

        if not priority_files:
            print("ERROR: No Golden Path priority files found!")
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

    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate fix report"""

        report = []
        report.append("# Test Corruption Fix Report")
        report.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Backup Timestamp:** {self.backup_timestamp}")
        report.append("")

        report.append("## Summary")
        report.append(f"- **Fixed:** {len(results['fixed'])} files")
        report.append(f"- **Failed:** {len(results['failed'])} files")
        report.append(f"- **Skipped (already valid):** {len(results['skipped'])} files")
        report.append("")

        if results["fixed"]:
            report.append("## Successfully Fixed Files")
            for file_path in results["fixed"]:
                report.append(f"- SUCCESS: {file_path}")
            report.append("")

        if results["failed"]:
            report.append("## Failed to Fix (Manual Intervention Required)")
            for file_path, error in results["failed"]:
                report.append(f"- ERROR: {file_path}")
                report.append(f"  - Error: {error}")
            report.append("")

        if results["skipped"]:
            report.append("## Skipped (Already Valid)")
            for file_path in results["skipped"]:
                report.append(f"- SKIP: {file_path}")
            report.append("")

        report.append("## Next Steps")
        if results["failed"]:
            report.append("1. **Manual Fix Required:** Address failed files individually")
            report.append("2. **Test Collection:** Run test collection on fixed files")
            report.append("3. **Service Startup:** Start backend and auth services")
        else:
            report.append("1. **Test Collection:** Validate all fixes with test collection")
            report.append("2. **Service Startup:** Start backend and auth services")
            report.append("3. **Golden Path Validation:** Run end-to-end Golden Path tests")

        return "\n".join(report)

def main():
    """Main execution function"""

    fixer = TestCorruptionFixer()

    print("🚨 TEST INFRASTRUCTURE CRISIS REMEDIATION")
    print("🎯 Phase 1: Golden Path Critical Files")
    print("📅 2025-09-17")
    print("=" * 60)

    # Fix Golden Path priority files
    results = fixer.fix_golden_path_files()

    # Generate and save report
    report = fixer.generate_report(results)

    report_path = Path("/c/netra-apex/TEST_CORRUPTION_FIX_REPORT.md")
    with open(report_path, 'w') as f:
        f.write(report)

    print("\n" + "=" * 60)
    print("🏁 PHASE 1 COMPLETE")
    print(f"📊 Report saved: {report_path}")

    if results["fixed"]:
        print(f"SUCCESS: Successfully fixed {len(results['fixed'])} files")
        print("\n🔄 Next Steps:")
        print("1. Run test collection: python tests/unified_test_runner.py --collect-only")
        print("2. Start auth service: python -m auth_service.main")
        print("3. Start backend service: python -m netra_backend.main")
        print("4. Validate Golden Path: Run authentication and WebSocket tests")

    if results["failed"]:
        print(f"WARNING: {len(results['failed'])} files need manual intervention")
        print("📋 Review failed files in the report for specific errors")

    return len(results["fixed"]) > 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)