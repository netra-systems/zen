#!/usr/bin/env python3
"""
Verify that WebSocket regression tests properly catch the bugs.

This script temporarily breaks the WebSocket implementation to verify
that our regression tests would fail without the fixes, then restores
the correct implementation.

Usage:
    python scripts/verify_websocket_regression_tests.py
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple, Optional
import json
import time

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class WebSocketRegressionVerifier:
    """Verify regression tests catch the WebSocket bugs."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.utils_file = self.project_root / "netra_backend" / "app" / "websocket_core" / "utils.py"
        self.websocket_file = self.project_root / "netra_backend" / "app" / "routes" / "websocket.py"
        self.backup_dir = None
        
        # Test files to run
        self.test_files = [
            "netra_backend/tests/unit/test_websocket_state_checking_regression.py",
            "netra_backend/tests/integration/test_websocket_subprotocol_negotiation_regression.py",
            "tests/e2e/test_websocket_immediate_disconnect_regression.py"
        ]
    
    def backup_files(self):
        """Backup original files."""
        self.backup_dir = tempfile.mkdtemp(prefix="websocket_backup_")
        print(f"📁 Backing up files to: {self.backup_dir}")
        
        # Backup utils.py
        shutil.copy2(self.utils_file, Path(self.backup_dir) / "utils.py")
        
        # Backup websocket.py
        shutil.copy2(self.websocket_file, Path(self.backup_dir) / "websocket.py")
    
    def restore_files(self):
        """Restore original files from backup."""
        if not self.backup_dir:
            return
        
        print("♻️  Restoring original files...")
        
        # Restore utils.py
        shutil.copy2(Path(self.backup_dir) / "utils.py", self.utils_file)
        
        # Restore websocket.py
        shutil.copy2(Path(self.backup_dir) / "websocket.py", self.websocket_file)
        
        # Clean up backup
        shutil.rmtree(self.backup_dir, ignore_errors=True)
        self.backup_dir = None
    
    def break_state_checking(self):
        """Break is_websocket_connected to only check application_state."""
        print("🔨 Breaking WebSocket state checking (simulating bug)...")
        
        with open(self.utils_file, 'r') as f:
            content = f.read()
        
        # Find and replace the is_websocket_connected function
        broken_function = '''def is_websocket_connected(websocket: WebSocket) -> bool:
    """Check if WebSocket is connected."""
    # BROKEN: Only checking application_state (original bug)
    return hasattr(websocket, 'application_state') and websocket.application_state == WebSocketState.CONNECTED'''
        
        # Replace the function
        import re
        pattern = r'def is_websocket_connected\(.*?\).*?:\n(?:.*?\n)*?(?=\n\ndef|\Z)'
        content = re.sub(pattern, broken_function, content, flags=re.DOTALL)
        
        with open(self.utils_file, 'w') as f:
            f.write(content)
        
        print("   ❌ State checking broken - only checks application_state")
    
    def break_subprotocol_negotiation(self):
        """Remove subprotocol from websocket.accept()."""
        print("🔨 Breaking WebSocket subprotocol negotiation (simulating bug)...")
        
        with open(self.websocket_file, 'r') as f:
            content = f.read()
        
        # Find and break the accept with subprotocol
        broken_accept = '''            # Accept WebSocket connection WITHOUT subprotocol (BROKEN)
            await websocket.accept()  # Missing subprotocol parameter
            logger.info("WebSocket accepted without subprotocol")'''
        
        # Replace the subprotocol negotiation section
        import re
        pattern = r'# Accept WebSocket connection with appropriate subprotocol.*?logger\.info\(.*?"WebSocket accepted.*?"\)'
        content = re.sub(pattern, broken_accept, content, flags=re.DOTALL)
        
        with open(self.websocket_file, 'w') as f:
            f.write(content)
        
        print("   ❌ Subprotocol negotiation broken - accept() missing subprotocol")
    
    def run_tests(self, test_file: str) -> Tuple[bool, str]:
        """Run a test file and return success status and output."""
        print(f"🧪 Running: {test_file}")
        
        test_path = self.project_root / test_file
        if not test_path.exists():
            return False, f"Test file not found: {test_path}"
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=60
            )
            
            success = result.returncode == 0
            output = result.stdout + result.stderr
            
            # Extract key information
            if "PASSED" in output:
                passed = len([line for line in output.split('\n') if 'PASSED' in line])
            else:
                passed = 0
            
            if "FAILED" in output:
                failed = len([line for line in output.split('\n') if 'FAILED' in line])
            else:
                failed = 0
            
            return success, f"Passed: {passed}, Failed: {failed}"
            
        except subprocess.TimeoutExpired:
            return False, "Test timed out"
        except Exception as e:
            return False, str(e)
    
    def verify_tests_fail_without_fixes(self):
        """Verify tests fail when bugs are present."""
        print("\n" + "="*60)
        print("STEP 1: Verify tests FAIL without fixes (catch the bugs)")
        print("="*60)
        
        # Break the implementations
        self.break_state_checking()
        self.break_subprotocol_negotiation()
        
        print("\n📊 Running tests with broken implementation...")
        
        results = {}
        for test_file in self.test_files:
            success, output = self.run_tests(test_file)
            results[test_file] = (success, output)
            
            test_name = Path(test_file).name
            if success:
                print(f"   ⚠️  {test_name}: PASSED (should have FAILED!)")
            else:
                print(f"   ✅ {test_name}: FAILED as expected - {output}")
        
        # Check if tests properly failed
        all_failed = all(not success for success, _ in results.values())
        
        if all_failed:
            print("\n✅ SUCCESS: All tests FAILED with broken implementation (they catch the bugs!)")
            return True
        else:
            print("\n❌ ERROR: Some tests PASSED with broken implementation (not catching bugs!)")
            for test_file, (success, output) in results.items():
                if success:
                    print(f"   Problem test: {test_file}")
            return False
    
    def verify_tests_pass_with_fixes(self):
        """Verify tests pass when fixes are applied."""
        print("\n" + "="*60)
        print("STEP 2: Verify tests PASS with fixes applied")
        print("="*60)
        
        # Restore the correct implementation
        self.restore_files()
        
        print("\n📊 Running tests with fixed implementation...")
        
        results = {}
        for test_file in self.test_files:
            success, output = self.run_tests(test_file)
            results[test_file] = (success, output)
            
            test_name = Path(test_file).name
            if success:
                print(f"   ✅ {test_name}: PASSED - {output}")
            else:
                print(f"   ❌ {test_name}: FAILED (should have PASSED!)")
        
        # Check if all tests passed
        all_passed = all(success for success, _ in results.values())
        
        if all_passed:
            print("\n✅ SUCCESS: All tests PASSED with fixed implementation!")
            return True
        else:
            print("\n❌ ERROR: Some tests FAILED with fixed implementation!")
            for test_file, (success, output) in results.items():
                if not success:
                    print(f"   Problem test: {test_file}")
            return False
    
    def run_verification(self) -> bool:
        """Run the complete verification process."""
        print("🔍 WebSocket Regression Test Verification")
        print("=========================================")
        print("This will verify that regression tests properly catch the bugs.\n")
        
        try:
            # Backup original files
            self.backup_files()
            
            # Step 1: Verify tests fail without fixes
            tests_catch_bugs = self.verify_tests_fail_without_fixes()
            
            # Step 2: Verify tests pass with fixes
            tests_validate_fixes = self.verify_tests_pass_with_fixes()
            
            # Summary
            print("\n" + "="*60)
            print("VERIFICATION SUMMARY")
            print("="*60)
            
            if tests_catch_bugs and tests_validate_fixes:
                print("✅ All regression tests are working correctly!")
                print("   - They FAIL when bugs are present")
                print("   - They PASS when fixes are applied")
                print("\nThese tests will prevent regression of:")
                print("   1. WebSocket state checking bug (ABNORMAL_CLOSURE)")
                print("   2. WebSocket subprotocol negotiation bug")
                return True
            else:
                print("❌ Regression tests need attention:")
                if not tests_catch_bugs:
                    print("   - Tests don't properly detect the bugs")
                if not tests_validate_fixes:
                    print("   - Tests don't pass with the fixes")
                return False
                
        except Exception as e:
            print(f"❌ Verification failed with error: {e}")
            return False
        finally:
            # Always restore original files
            self.restore_files()


def main():
    """Main entry point."""
    verifier = WebSocketRegressionVerifier()
    
    # Check if we're in Docker environment
    if os.path.exists("/.dockerenv"):
        print("⚠️  Running in Docker environment")
        print("   Make sure backend service is accessible at localhost:8000")
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            return 1
    
    # Run verification
    success = verifier.run_verification()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())