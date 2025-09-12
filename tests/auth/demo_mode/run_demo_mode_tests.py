#!/usr/bin/env python3
"""
Demo Mode Authentication Test Runner

This script runs the comprehensive demo mode authentication test suite.
These tests are designed to INITIALLY FAIL, demonstrating current restrictive behavior.

BUSINESS VALUE: Free Segment - Demo Environment Usability
GOAL: Conversion - Eliminate authentication friction for demo evaluation

Usage:
    python tests/auth/demo_mode/run_demo_mode_tests.py
    python tests/auth/demo_mode/run_demo_mode_tests.py --verbose
    python tests/auth/demo_mode/run_demo_mode_tests.py --integration-only
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import IsolatedEnvironment


class DemoModeTestRunner:
    """Test runner for demo mode authentication tests."""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.test_results = []
        
    def setup_demo_environment(self):
        """Setup environment for demo mode testing."""
        print("🔧 Setting up demo mode test environment...")
        
        # Set demo mode environment
        self.env.set_env("DEMO_MODE", "true")
        self.env.set_env("ENVIRONMENT", "demo")
        self.env.set_env("JWT_SECRET_KEY", "demo_test_secret_key_for_testing")
        
        # Additional test environment setup
        self.env.set_env("LOG_LEVEL", "DEBUG")
        self.env.set_env("TESTING", "true")
        
        print("✅ Demo mode environment configured")
        
    def cleanup_environment(self):
        """Cleanup test environment."""
        print("🧹 Cleaning up test environment...")
        
        # Restore original environment
        self.env.unset_env("DEMO_MODE")
        self.env.unset_env("ENVIRONMENT") 
        self.env.unset_env("JWT_SECRET_KEY")
        self.env.unset_env("LOG_LEVEL")
        self.env.unset_env("TESTING")
        
        print("✅ Environment cleaned up")
        
    def run_test_module(self, test_file, description):
        """Run a specific test module."""
        print(f"\n📋 Running {description}")
        print(f"   File: {test_file}")
        
        try:
            # Run pytest with verbose output
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                test_file,
                "-v",
                "--tb=short",
                "--no-header"
            ], capture_output=True, text=True, timeout=300)
            
            # Parse results
            output = result.stdout + result.stderr
            return_code = result.returncode
            
            # Store results
            self.test_results.append({
                "module": test_file,
                "description": description,
                "return_code": return_code,
                "output": output,
                "passed": return_code == 0
            })
            
            # Print summary
            if return_code == 0:
                print("   ✅ UNEXPECTED PASS (Tests should fail initially)")
                print("   ⚠️  This indicates demo features may already be implemented")
            else:
                print("   ❌ EXPECTED FAIL (Current restrictive behavior)")
                print("   ✅ This demonstrates need for demo mode implementation")
                
            return return_code == 0
            
        except subprocess.TimeoutExpired:
            print("   ⏰ TEST TIMEOUT (> 5 minutes)")
            self.test_results.append({
                "module": test_file,
                "description": description, 
                "return_code": -1,
                "output": "Test execution timeout",
                "passed": False
            })
            return False
            
        except Exception as e:
            print(f"   💥 TEST ERROR: {e}")
            self.test_results.append({
                "module": test_file,
                "description": description,
                "return_code": -2, 
                "output": f"Execution error: {e}",
                "passed": False
            })
            return False
    
    def run_all_tests(self, verbose=False, integration_only=False):
        """Run all demo mode tests."""
        print("🚀 Starting Demo Mode Authentication Test Suite")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n" + "="*60)
        
        # Setup environment
        self.setup_demo_environment()
        
        try:
            # Define test modules
            test_modules = []
            
            if not integration_only:
                test_modules.extend([
                    ("tests/auth/demo_mode/test_demo_mode_configuration.py", 
                     "Demo Mode Configuration Tests"),
                    ("tests/auth/demo_mode/test_jwt_validation_permissive.py",
                     "JWT Validation Permissive Tests"), 
                    ("tests/auth/demo_mode/test_user_creation_flexible.py",
                     "User Creation Flexible Tests"),
                    ("tests/auth/demo_mode/test_circuit_breaker_relaxed.py",
                     "Circuit Breaker Relaxed Tests")
                ])
            
            test_modules.append(
                ("tests/integration/test_demo_mode_auth_integration.py",
                 "Demo Mode Auth Integration Tests")
            )
            
            # Run each test module
            passed_count = 0
            total_count = len(test_modules)
            
            for test_file, description in test_modules:
                test_file_path = project_root / test_file
                if test_file_path.exists():
                    if self.run_test_module(str(test_file_path), description):
                        passed_count += 1
                else:
                    print(f"\n⚠️  Test file not found: {test_file}")
                    print(f"   Expected: {test_file_path}")
            
            # Print detailed results if verbose
            if verbose:
                self.print_detailed_results()
            
            # Print summary
            self.print_summary(passed_count, total_count)
            
        finally:
            # Always cleanup
            self.cleanup_environment()
        
        return self.test_results
        
    def print_detailed_results(self):
        """Print detailed test results."""
        print("\n" + "="*60)
        print("📊 DETAILED TEST RESULTS")
        print("="*60)
        
        for result in self.test_results:
            print(f"\n🔍 {result['description']}")
            print(f"   Module: {result['module']}")
            print(f"   Status: {'✅ PASS' if result['passed'] else '❌ FAIL'}")
            print(f"   Return Code: {result['return_code']}")
            
            if result['output']:
                # Show first few lines of output
                output_lines = result['output'].split('\n')[:10]
                for line in output_lines:
                    if line.strip():
                        print(f"   │ {line}")
                        
                if len(result['output'].split('\n')) > 10:
                    print(f"   │ ... ({len(result['output'].split('\n')) - 10} more lines)")
    
    def print_summary(self, passed_count, total_count):
        """Print test execution summary."""
        print("\n" + "="*60)
        print("📋 TEST EXECUTION SUMMARY")
        print("="*60)
        
        print(f"🎯 Expected Result: ALL TESTS SHOULD FAIL (demonstrating restrictive behavior)")
        print(f"📊 Tests Passed: {passed_count}/{total_count}")
        print(f"📊 Tests Failed: {total_count - passed_count}/{total_count}")
        
        if passed_count == 0:
            print("\n✅ PERFECT! All tests failed as expected")
            print("   This demonstrates current restrictive authentication behavior")
            print("   Ready to implement demo mode features to make tests pass")
        elif passed_count < total_count:
            print(f"\n⚠️  MIXED RESULTS: {passed_count} tests passed unexpectedly")
            print("   Some demo features may already be partially implemented")
            print("   Review passing tests to understand current state")
        else:
            print("\n🎉 ALL TESTS PASSED!")
            print("   Demo mode features appear to be fully implemented")
            print("   Verify this is intended behavior")
        
        print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n🔗 Next Steps:")
        print("   1. Review failing tests to understand implementation needs")
        print("   2. Begin implementing demo mode configuration")
        print("   3. Implement authentication relaxations")
        print("   4. Re-run tests to validate implementations")
        print("   5. See tests/auth/demo_mode/README_DEMO_MODE_TESTS.md for guidance")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run demo mode authentication tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_demo_mode_tests.py                    # Run all tests
  python run_demo_mode_tests.py --verbose          # Detailed output
  python run_demo_mode_tests.py --integration-only # Integration tests only
        """
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed test output"
    )
    
    parser.add_argument(
        "--integration-only", "-i", 
        action="store_true",
        help="Run only integration tests"
    )
    
    args = parser.parse_args()
    
    # Create and run test runner
    runner = DemoModeTestRunner()
    results = runner.run_all_tests(
        verbose=args.verbose,
        integration_only=args.integration_only
    )
    
    # Exit with appropriate code
    failed_tests = [r for r in results if not r['passed']]
    if len(failed_tests) == len(results):
        # All tests failed - this is expected initially
        print("\n✅ Expected result achieved: All tests demonstrate need for demo implementation")
        sys.exit(0)
    else:
        # Some tests passed - unexpected initially
        print(f"\n⚠️  Unexpected results: {len(results) - len(failed_tests)} tests passed")
        sys.exit(1)


if __name__ == "__main__":
    main()