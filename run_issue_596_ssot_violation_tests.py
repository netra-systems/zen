#!/usr/bin/env python3
"""
Issue #596 SSOT Environment Variable Violations - Test Runner

This script runs the comprehensive test suite designed to detect and reproduce
SSOT environment variable violations that are blocking Golden Path authentication.

Expected Result: ALL TESTS SHOULD FAIL INITIALLY
This proves the SSOT violations exist and are impacting the system.

Business Impact: $500K+ ARR Golden Path user flow protection
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class Issue596TestRunner:
    """Test runner for Issue #596 SSOT environment variable violations."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_results = {}
        
    def run_unit_tests(self):
        """Run unit tests that detect SSOT violations."""
        print("\n" + "="*80)
        print("🧪 PHASE 1: UNIT TESTS - SSOT Violation Detection")
        print("="*80)
        print("Expected: ALL TESTS SHOULD FAIL - proving violations exist")
        print()
        
        unit_test_files = [
            "tests/unit/environment/test_auth_startup_validator_ssot_violations.py",
            "tests/unit/environment/test_unified_secrets_ssot_violations.py", 
            "tests/unit/environment/test_unified_corpus_admin_ssot_violations.py"
        ]
        
        for test_file in unit_test_files:
            test_path = self.project_root / test_file
            if test_path.exists():
                self._run_test_file(test_file, "unit")
            else:
                print(f"⚠️  Test file not found: {test_file}")
                
    def run_integration_tests(self):
        """Run integration tests that detect environment consistency issues."""
        print("\n" + "="*80)
        print("🔄 PHASE 2: INTEGRATION TESTS - Environment Consistency")
        print("="*80)
        print("Expected: TESTS FAIL - showing environment inconsistencies")
        print()
        
        integration_test_files = [
            "tests/integration/environment/test_ssot_environment_consistency.py"
        ]
        
        for test_file in integration_test_files:
            test_path = self.project_root / test_file
            if test_path.exists():
                self._run_test_file(test_file, "integration")
            else:
                print(f"⚠️  Test file not found: {test_file}")
                
    def run_e2e_staging_tests(self):
        """Run E2E tests against GCP staging environment."""
        print("\n" + "="*80)
        print("🌐 PHASE 3: E2E STAGING TESTS - Golden Path Authentication")
        print("="*80)
        print("Expected: TESTS FAIL - Golden Path blocked by SSOT violations")
        print()
        
        # Check if staging environment is available
        env = os.environ.get('ENVIRONMENT', '').lower()
        if env not in ['staging', 'gcp-staging'] and not os.environ.get('GCP_PROJECT'):
            print("⏭️  Skipping E2E staging tests - staging environment not detected")
            print("   Set ENVIRONMENT=staging or GCP_PROJECT=netra-staging to enable")
            return
            
        e2e_test_files = [
            "tests/e2e/gcp_staging_environment/test_golden_path_auth_ssot_violations.py"
        ]
        
        for test_file in e2e_test_files:
            test_path = self.project_root / test_file
            if test_path.exists():
                self._run_test_file(test_file, "e2e")
            else:
                print(f"⚠️  Test file not found: {test_file}")
    
    def _run_test_file(self, test_file: str, category: str):
        """Run a specific test file and capture results."""
        print(f"📋 Running {category.upper()} test: {test_file}")
        
        try:
            # Use pytest to run the specific test file
            cmd = [
                sys.executable, "-m", "pytest", 
                str(test_file),
                "-v",  # Verbose output
                "--tb=short",  # Shorter traceback format
                "--no-header",  # No pytest header
                f"-m", "ssot_violation",  # Run only SSOT violation tests
                "--disable-warnings"  # Reduce noise
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            self.test_results[test_file] = {
                'category': category,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            # Print results
            if result.returncode == 0:
                print(f"❌ UNEXPECTED: Tests PASSED - violations may not be active")
                print("   This requires investigation - violations should cause failures")
            else:
                print(f"✅ EXPECTED: Tests FAILED - proving SSOT violations exist")
                print(f"   Return code: {result.returncode}")
            
            # Print key output lines  
            if result.stdout:
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if 'SSOT VIOLATION' in line or 'FAIL' in line or '::' in line:
                        print(f"   {line}")
            
            if result.stderr and 'collected' not in result.stderr:
                print(f"   stderr: {result.stderr[:200]}...")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ TIMEOUT: Test execution exceeded 5 minutes")
            self.test_results[test_file] = {
                'category': category,
                'return_code': -1,
                'error': 'Timeout after 5 minutes'
            }
        except Exception as e:
            print(f"💥 ERROR: Failed to run test - {str(e)}")
            self.test_results[test_file] = {
                'category': category,
                'return_code': -2,
                'error': str(e)
            }
    
    def generate_summary_report(self):
        """Generate a summary report of all test results."""
        print("\n" + "="*80)
        print("📊 ISSUE #596 SSOT VIOLATION TEST RESULTS SUMMARY")
        print("="*80)
        
        categories = {}
        for test_file, result in self.test_results.items():
            category = result['category']
            if category not in categories:
                categories[category] = {'total': 0, 'failed': 0, 'passed': 0, 'error': 0}
            
            categories[category]['total'] += 1
            
            if result['return_code'] == 0:
                categories[category]['passed'] += 1
            elif result['return_code'] > 0:
                categories[category]['failed'] += 1
            else:
                categories[category]['error'] += 1
        
        # Print category summaries
        for category, stats in categories.items():
            print(f"\n{category.upper()} TESTS:")
            print(f"  Total: {stats['total']}")
            print(f"  ✅ Expected Failures: {stats['failed']} (proves violations exist)")
            print(f"  ❌ Unexpected Passes: {stats['passed']} (violations may be inactive)")
            print(f"  💥 Execution Errors: {stats['error']}")
        
        # Overall assessment
        total_tests = len(self.test_results)
        total_failed = sum(1 for r in self.test_results.values() if r['return_code'] > 0)
        total_passed = sum(1 for r in self.test_results.values() if r['return_code'] == 0)
        
        print(f"\n🎯 OVERALL ASSESSMENT:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Expected Failures: {total_failed} / {total_tests}")
        print(f"  Unexpected Passes: {total_passed} / {total_tests}")
        
        if total_failed == total_tests:
            print(f"\n🚨 PERFECT RESULT: All tests failed as expected!")
            print(f"   This confirms SSOT violations exist and are blocking Golden Path")
        elif total_failed > total_passed:
            print(f"\n⚠️  MIXED RESULTS: Most tests failed, confirming violations exist")
            print(f"   Some passes may indicate partial fixes or test environment differences")
        else:
            print(f"\n🤔 UNEXPECTED: More tests passed than failed")
            print(f"   This requires investigation - violations may be inactive or fixed")
        
        print(f"\n📋 DETAILED RESULTS:")
        for test_file, result in self.test_results.items():
            status = "✅ FAIL (Expected)" if result['return_code'] > 0 else "❌ PASS (Unexpected)" if result['return_code'] == 0 else "💥 ERROR"
            print(f"  {status} {test_file}")
            
        print(f"\n🔗 NEXT STEPS:")
        if total_failed > 0:
            print(f"  1. ✅ Violations confirmed - proceed with SSOT compliance fixes")
            print(f"  2. 🔧 Fix os.environ usage in auth_startup_validator.py lines 507-516")
            print(f"  3. 🔧 Fix os.getenv() usage in unified_secrets.py lines 52, 69")  
            print(f"  4. 🔧 Fix os.getenv() usage in unified_corpus_admin.py lines 155, 281")
            print(f"  5. 🧪 Re-run tests to verify fixes (tests should PASS after fix)")
        else:
            print(f"  1. 🔍 Investigate why tests passed - violations may be inactive")
            print(f"  2. 📋 Review test implementation for accuracy")
            print(f"  3. 🧪 Run tests in different environments")
            print(f"  4. ✅ If violations are fixed, update issue #596 status")


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Run Issue #596 SSOT environment variable violation tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Expected Results:
  - ALL TESTS SHOULD FAIL INITIALLY
  - This proves SSOT violations exist and block Golden Path
  - After violations are fixed, tests should PASS

Business Impact:
  - $500K+ ARR Golden Path authentication protection
  - SSOT compliance prevents cascade failures
        """
    )
    
    parser.add_argument(
        "--phase",
        choices=["unit", "integration", "e2e", "all"],
        default="all",
        help="Which test phase to run (default: all)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v", 
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    print("🚨 ISSUE #596 SSOT ENVIRONMENT VARIABLE VIOLATIONS - TEST SUITE")
    print("="*80)
    print("CRITICAL: Legacy os.environ access blocking Golden Path authentication")
    print("")
    print("VIOLATIONS TARGETED:")
    print("  • auth_startup_validator.py (Lines 507-516) - Direct os.environ fallback")
    print("  • unified_secrets.py (Lines 52, 69) - Direct os.getenv() calls")  
    print("  • unified_corpus_admin.py (Lines 155, 281) - Direct os.getenv() calls")
    print("")
    print("BUSINESS IMPACT: $500K+ ARR Golden Path user authentication flow")
    print("="*80)
    
    runner = Issue596TestRunner()
    
    try:
        if args.phase in ["unit", "all"]:
            runner.run_unit_tests()
            
        if args.phase in ["integration", "all"]:
            runner.run_integration_tests()
            
        if args.phase in ["e2e", "all"]:
            runner.run_e2e_staging_tests()
            
        runner.generate_summary_report()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test execution interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n💥 FATAL ERROR: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())