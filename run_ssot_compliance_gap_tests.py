#!/usr/bin/env python3
"""
SSOT Compliance Gap Test Execution Script - Issue #1075

This script executes the SSOT compliance validation tests designed to detect
the 16.6% compliance gap between claimed and actual compliance.

Expected outcome: Tests should FAIL initially to prove the gap exists.
"""

import sys
import os
from pathlib import Path
import unittest
import traceback
from io import StringIO

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_test_with_output_capture(test_module_path: str, test_class_name: str, test_method_name: str):
    """Run a specific test and capture its output."""
    try:
        # Import the test module
        spec = __import__(test_module_path.replace('/', '.').replace('.py', ''), fromlist=[test_class_name])
        test_class = getattr(spec, test_class_name)
        
        # Create test suite
        suite = unittest.TestSuite()
        test_instance = test_class(test_method_name)
        suite.addTest(test_instance)
        
        # Capture output
        output_buffer = StringIO()
        runner = unittest.TextTestRunner(stream=output_buffer, verbosity=2)
        
        # Run test
        result = runner.run(suite)
        
        output = output_buffer.getvalue()
        
        return {
            'success': result.wasSuccessful(),
            'failures': len(result.failures),
            'errors': len(result.errors),
            'output': output,
            'failure_details': result.failures,
            'error_details': result.errors
        }
        
    except Exception as e:
        return {
            'success': False,
            'failures': 0,
            'errors': 1,
            'output': f"Error running test: {str(e)}",
            'failure_details': [],
            'error_details': [str(e)]
        }

def main():
    """Run SSOT compliance gap validation tests."""
    print("SSOT COMPLIANCE GAP VALIDATION - Issue #1075")
    print("=" * 60)
    print("Running tests designed to FAIL and detect compliance gap...")
    print()
    
    # Tests to run (designed to fail and prove violations exist)
    test_cases = [
        {
            'name': 'Production Compliance Gap Detection',
            'module': 'tests.unit.ssot_compliance.test_production_compliance_gap_validation',
            'class': 'TestProductionComplianceGapValidation',
            'method': 'test_production_compliance_gap_detection'
        },
        {
            'name': 'Duplicate Class Detection',
            'module': 'tests.unit.ssot_compliance.test_production_compliance_gap_validation',
            'class': 'TestProductionComplianceGapValidation',
            'method': 'test_duplicate_class_definition_violations'
        },
        {
            'name': 'Duplicate Type Definition Detection',
            'module': 'tests.unit.ssot_compliance.test_duplicate_type_definition_detection',
            'class': 'TestDuplicateTypeDefinitionDetection',
            'method': 'test_comprehensive_duplicate_type_analysis'
        }
    ]
    
    results_summary = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. Testing: {test_case['name']}")
        print("-" * 40)
        
        try:
            result = run_test_with_output_capture(
                test_case['module'],
                test_case['class'],
                test_case['method']
            )
            
            results_summary.append({
                'name': test_case['name'],
                'result': result
            })
            
            # Show test output
            if result['output']:
                print("Test Output:")
                # Filter to show the key parts
                lines = result['output'].split('\n')
                for line in lines:
                    if ('===' in line or 
                        'VIOLATION' in line or 
                        'Found' in line or 
                        'Gap:' in line or
                        'compliance' in line.lower() or
                        'FAIL' in line):
                        print(f"  {line}")
            
            # Show failure details (which we expect for gap detection)
            if result['failures'] or result['errors']:
                print(f"\nTest Result: {'ERROR' if result['errors'] else 'FAILED'} (Expected for gap detection)")
                
                if result['failures']:
                    for test, failure in result['failures']:
                        print(f"  Failure Details: {failure.split('AssertionError:')[-1].strip()}")
                
                if result['errors']:
                    for error in result['error_details']:
                        print(f"  Error Details: {error}")
            else:
                print("\nTest Result: PASSED (Unexpected - gap may not exist or test needs adjustment)")
                
            print()
            
        except Exception as e:
            print(f"Error running test: {e}")
            traceback.print_exc()
            print()
    
    # Summary report
    print("=" * 60)
    print("SSOT COMPLIANCE GAP VALIDATION SUMMARY")
    print("=" * 60)
    
    failed_tests = 0
    passed_tests = 0
    error_tests = 0
    
    for summary in results_summary:
        result = summary['result']
        if result['errors'] > 0:
            status = "ERROR"
            error_tests += 1
        elif result['failures'] > 0:
            status = "FAILED (Expected for gap detection)"
            failed_tests += 1
        else:
            status = "PASSED (Unexpected)"
            passed_tests += 1
        
        print(f"- {summary['name']}: {status}")
    
    print()
    print(f"Total: {len(results_summary)} tests")
    print(f"Failed (Expected): {failed_tests}")
    print(f"Passed (Unexpected): {passed_tests}")
    print(f"Errors: {error_tests}")
    print()
    
    if failed_tests > 0:
        print("✅ SUCCESS: Tests failed as expected, proving SSOT compliance gap exists")
        print("   The failures validate the 16.6% compliance gap identified in Issue #1075")
    elif error_tests > 0:
        print("⚠️  ERRORS: Tests encountered errors - may need debugging")
    else:
        print("⚠️  UNEXPECTED: No tests failed - compliance gap may not exist or tests need adjustment")

if __name__ == "__main__":
    main()