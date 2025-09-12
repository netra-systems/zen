"""Test Runner for Example Message Flow System

Comprehensive test runner for the example message flow implementation
with detailed reporting and validation.

Business Value: Ensures reliability of AI optimization demonstration system
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ExampleMessageFlowTestRunner:
    """Comprehensive test runner for example message flow"""
    
    def __init__(self):
        self.project_root = project_root
        self.test_results: Dict[str, Any] = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.errors = []
        
    def run_all_tests(self) -> bool:
        """Run all example message flow tests"""
        
        print("[U+1F680] Starting Example Message Flow Test Suite")
        print("=" * 60)
        
        success = True
        
        # Test categories
        test_suites = [
            {
                'name': 'Unit Tests',
                'file': 'tests/test_example_message_flow.py',
                'description': 'Core functionality unit tests'
            },
            {
                'name': 'Integration Tests', 
                'file': 'tests/test_example_message_integration.py',
                'description': 'End-to-end integration tests'
            }
        ]
        
        for suite in test_suites:
            print(f"\n[U+1F4CB] Running {suite['name']}: {suite['description']}")
            print("-" * 50)
            
            suite_success = self._run_test_suite(suite)
            if not suite_success:
                success = False
                
        # Run validation checks
        print(f"\n SEARCH:  Running Validation Checks")
        print("-" * 50)
        validation_success = self._run_validation_checks()
        if not validation_success:
            success = False
            
        # Generate report
        self._generate_test_report()
        
        return success
        
    def _run_test_suite(self, suite: Dict[str, Any]) -> bool:
        """Run a specific test suite"""
        
        test_file = self.project_root / suite['file']
        
        if not test_file.exists():
            print(f" FAIL:  Test file not found: {test_file}")
            self.errors.append(f"Missing test file: {suite['file']}")
            return False
            
        try:
            # Run pytest on the specific file
            cmd = [
                sys.executable, '-m', 'pytest',
                str(test_file),
                '-v',
                '--tb=short',
                '--no-header',
                '--json-report',
                '--json-report-file=test_results.json'
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Parse results
            suite_results = self._parse_test_results(result, suite['name'])
            self.test_results[suite['name']] = suite_results
            
            if result.returncode == 0:
                print(f" PASS:  {suite['name']} passed")
                return True
            else:
                print(f" FAIL:  {suite['name']} failed")
                print(f"   Output: {result.stdout}")
                print(f"   Errors: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"[U+23F0] {suite['name']} timed out")
            self.errors.append(f"Timeout in {suite['name']}")
            return False
        except Exception as e:
            print(f"[U+1F4A5] Error running {suite['name']}: {e}")
            self.errors.append(f"Exception in {suite['name']}: {str(e)}")
            return False
            
    def _parse_test_results(self, result: subprocess.CompletedProcess, suite_name: str) -> Dict[str, Any]:
        """Parse test results from pytest output"""
        
        # Try to parse JSON report if available
        json_file = self.project_root / 'test_results.json'
        if json_file.exists():
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    
                return {
                    'total': data.get('summary', {}).get('total', 0),
                    'passed': data.get('summary', {}).get('passed', 0),
                    'failed': data.get('summary', {}).get('failed', 0),
                    'errors': data.get('summary', {}).get('error', 0),
                    'duration': data.get('duration', 0)
                }
            except Exception as e:
                logger.warning(f"Could not parse JSON results: {e}")
                
        # Fallback to parsing stdout
        output_lines = result.stdout.split('\n')
        
        passed = 0
        failed = 0
        errors = 0
        
        for line in output_lines:
            if '::' in line and 'PASSED' in line:
                passed += 1
            elif '::' in line and 'FAILED' in line:
                failed += 1
            elif '::' in line and 'ERROR' in line:
                errors += 1
                
        return {
            'total': passed + failed + errors,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'duration': 0  # Unknown without timing info
        }
        
    def _run_validation_checks(self) -> bool:
        """Run additional validation checks"""
        
        success = True
        
        # Check 1: Validate imports
        print("   Checking imports...")
        import_success = self._validate_imports()
        if not import_success:
            success = False
            
        # Check 2: Validate configuration
        print("   Checking configuration...")
        config_success = self._validate_configuration()
        if not config_success:
            success = False
            
        # Check 3: Test handler initialization
        print("   Testing handler initialization...")
        handler_success = self._test_handler_initialization()
        if not handler_success:
            success = False
            
        # Check 4: Test message validation
        print("   Testing message validation...")
        validation_success = self._test_message_validation()
        if not validation_success:
            success = False
            
        return success
        
    def _validate_imports(self) -> bool:
        """Validate that all required imports work"""
        
        try:
            from netra_backend.app.agents.example_message_processor import (
                ExampleMessageProcessor,
            )
            from netra_backend.app.error_handling.example_message_errors import (
                ExampleMessageErrorHandler,
            )
            from netra_backend.app.formatters.example_response_formatter import (
                ExampleResponseFormatter,
            )
            from netra_backend.app.handlers.example_message_handler import (
                ExampleMessageHandler,
            )
            
            print("      PASS:  All imports successful")
            return True
        except Exception as e:
            print(f"      FAIL:  Import error: {e}")
            self.errors.append(f"Import validation failed: {str(e)}")
            return False
            
    def _validate_configuration(self) -> bool:
        """Validate system configuration"""
        
        try:
            # Check that WebSocket manager can be initialized
            from netra_backend.app.websocket_core import get_websocket_manager
            ws_manager = get_websocket_manager()
            
            if ws_manager is None:
                print("      FAIL:  WebSocket manager not available")
                return False
                
            print("      PASS:  Configuration validation passed")
            return True
        except Exception as e:
            print(f"      FAIL:  Configuration error: {e}")
            self.errors.append(f"Configuration validation failed: {str(e)}")
            return False
            
    def _test_handler_initialization(self) -> bool:
        """Test that handlers can be initialized"""
        
        try:
            from netra_backend.app.agents.example_message_processor import (
                ExampleMessageSupervisor,
            )
            from netra_backend.app.handlers.example_message_handler import (
                ExampleMessageHandler,
            )
            
            handler = ExampleMessageHandler()
            supervisor = ExampleMessageSupervisor()
            
            if handler is None or supervisor is None:
                print("      FAIL:  Handler initialization failed")
                return False
                
            print("      PASS:  Handler initialization successful")
            return True
        except Exception as e:
            print(f"      FAIL:  Handler initialization error: {e}")
            self.errors.append(f"Handler initialization failed: {str(e)}")
            return False
            
    def _test_message_validation(self) -> bool:
        """Test message validation functionality"""
        
        try:
            from netra_backend.app.handlers.example_message_handler import (
                ExampleMessageRequest,
            )
            
            # Test valid message
            valid_message = {
                "content": "Test message for validation",
                "example_message_id": "validation_test",
                "example_message_metadata": {
                    "title": "Validation Test",
                    "category": "cost-optimization",
                    "complexity": "basic",
                    "businessValue": "conversion",
                    "estimatedTime": "30s"
                },
                "user_id": "test_user",
                "timestamp": 1234567890
            }
            
            request = ExampleMessageRequest(**valid_message)
            
            if request.content != "Test message for validation":
                print("      FAIL:  Message validation failed")
                return False
                
            print("      PASS:  Message validation successful")
            return True
        except Exception as e:
            print(f"      FAIL:  Message validation error: {e}")
            self.errors.append(f"Message validation failed: {str(e)}")
            return False
            
    def _generate_test_report(self):
        """Generate comprehensive test report"""
        
        print("\n" + "=" * 60)
        print(" CHART:  TEST RESULTS SUMMARY")
        print("=" * 60)
        
        # Overall statistics
        total_passed = sum(suite.get('passed', 0) for suite in self.test_results.values())
        total_failed = sum(suite.get('failed', 0) for suite in self.test_results.values())
        total_errors = sum(suite.get('errors', 0) for suite in self.test_results.values())
        total_tests = total_passed + total_failed + total_errors
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {total_passed}  PASS: ")
        print(f"Failed: {total_failed}  FAIL: ")
        print(f"Errors: {total_errors} [U+1F4A5]")
        
        if total_tests > 0:
            success_rate = (total_passed / total_tests) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        else:
            print("Success Rate: N/A")
            
        # Suite breakdown
        print("\nSuite Breakdown:")
        for suite_name, results in self.test_results.items():
            total = results.get('total', 0)
            passed = results.get('passed', 0)
            failed = results.get('failed', 0)
            errors = results.get('errors', 0)
            
            if total > 0:
                rate = (passed / total) * 100
                print(f"  {suite_name}: {passed}/{total} ({rate:.1f}%)")
            else:
                print(f"  {suite_name}: No tests run")
                
        # Error summary
        if self.errors:
            print("\nErrors Encountered:")
            for error in self.errors:
                print(f"  [U+2022] {error}")
                
        print("\n" + "=" * 60)
        
        # Overall result
        if total_failed == 0 and total_errors == 0 and total_tests > 0:
            print(" CELEBRATION:  ALL TESTS PASSED!")
            print("Example Message Flow system is ready for production.")
        elif total_tests == 0:
            print(" WARNING: [U+FE0F]  NO TESTS WERE RUN")
            print("Please check test configuration.")
        else:
            print(" FAIL:  SOME TESTS FAILED")
            print("Please review failures before deploying.")
            
        print("=" * 60)


def run_quick_validation():
    """Run quick validation checks only"""
    
    print(" SEARCH:  Running Quick Validation Checks")
    print("-" * 40)
    
    try:
        # Test imports
        print("Checking imports...")
        from netra_backend.app.agents.example_message_processor import (
            ExampleMessageProcessor,
        )
        from netra_backend.app.error_handling.example_message_errors import (
            ExampleMessageErrorHandler,
        )
        from netra_backend.app.formatters.example_response_formatter import (
            ExampleResponseFormatter,
        )
        from netra_backend.app.handlers.example_message_handler import (
            ExampleMessageHandler,
        )
        print(" PASS:  Imports successful")
        
        # Test initialization
        print("Testing initialization...")
        handler = ExampleMessageHandler()
        processor = ExampleMessageProcessor()
        print(" PASS:  Initialization successful")
        
        # Test basic functionality
        print("Testing message validation...")
        from netra_backend.app.handlers.example_message_handler import (
            ExampleMessageRequest,
        )
        
        test_message = {
            "content": "Quick validation test",
            "example_message_id": "quick_test",
            "example_message_metadata": {
                "title": "Quick Test",
                "category": "cost-optimization",
                "complexity": "basic", 
                "businessValue": "conversion",
                "estimatedTime": "30s"
            },
            "user_id": "quick_user",
            "timestamp": 1234567890
        }
        
        request = ExampleMessageRequest(**test_message)
        print(" PASS:  Message validation successful")
        
        print("\n CELEBRATION:  Quick validation passed!")
        return True
        
    except Exception as e:
        print(f"\n FAIL:  Quick validation failed: {e}")
        return False


def main():
    """Main test runner entry point"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Example Message Flow Test Runner')
    parser.add_argument('--quick', action='store_true', help='Run quick validation only')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.quick:
        success = run_quick_validation()
        sys.exit(0 if success else 1)
    else:
        runner = ExampleMessageFlowTestRunner()
        success = runner.run_all_tests()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()