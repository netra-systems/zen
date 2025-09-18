#!/usr/bin/env python3
"""
Issue #220 SSOT Consolidation Validation Script

Quick execution script for running Issue #220 SSOT validation tests.
This script follows CLAUDE.md requirements for non-Docker testing.

Usage:
    python scripts/run_issue_220_validation.py [quick|comprehensive|baseline]
"""

import sys
import subprocess
import time
import os
from pathlib import Path


def run_command(command, description, timeout=120):
    """Run a command and capture results."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent.parent  # Run from project root
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ PASS ({duration:.1f}s)")
            if result.stdout.strip():
                print("STDOUT:")
                print(result.stdout)
        else:
            print(f"❌ FAIL ({duration:.1f}s)")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        
        return {
            'success': result.returncode == 0,
            'duration': duration,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'command': command
        }
        
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT after {timeout}s")
        return {
            'success': False,
            'duration': timeout,
            'stdout': '',
            'stderr': f'Command timed out after {timeout}s',
            'command': command
        }
    except Exception as e:
        print(f"💥 ERROR: {e}")
        return {
            'success': False,
            'duration': 0,
            'stdout': '',
            'stderr': str(e),
            'command': command
        }


def run_baseline_validation():
    """Run baseline SSOT compliance validation."""
    print(f"\n🎯 ISSUE #220 BASELINE VALIDATION")
    print(f"Purpose: Validate current SSOT compliance levels")
    
    tests = [
        {
            'command': 'python -m pytest tests/unit/ssot_validation/test_issue_220_ssot_compliance_baseline.py -v',
            'description': 'SSOT Compliance Baseline',
            'timeout': 60
        }
    ]
    
    results = []
    for test in tests:
        result = run_command(test['command'], test['description'], test.get('timeout', 120))
        results.append(result)
    
    return results


def run_quick_validation():
    """Run quick SSOT validation tests."""
    print(f"\n🚀 ISSUE #220 QUICK VALIDATION")
    print(f"Purpose: Essential SSOT compliance checks (15 minutes)")
    
    tests = [
        {
            'command': 'python -m pytest tests/unit/ssot_validation/test_issue_220_ssot_compliance_baseline.py::Issue220SSOTComplianceBaselineTests::test_architectural_compliance_score_baseline -v',
            'description': 'Architectural Compliance Score',
            'timeout': 30
        },
        {
            'command': 'python -m pytest tests/integration/ssot_validation/test_message_router_ssot_consolidation.py::MessageRouterSSOTConsolidationTests::test_message_router_class_id_consistency -v',
            'description': 'MessageRouter SSOT Class ID Consistency',
            'timeout': 30
        },
        {
            'command': 'python -m pytest tests/integration/ssot_validation/test_factory_pattern_user_isolation.py::FactoryPatternUserIsolationTests::test_agent_factory_singleton_elimination -v',
            'description': 'Agent Factory Singleton Elimination',
            'timeout': 60
        },
        {
            'command': 'python -m pytest tests/unit/ssot_validation/test_agent_execution_tracker_ssot.py::AgentExecutionTrackerSSOTTests::test_execution_state_enum_consolidation -v',
            'description': 'ExecutionState Enum Consolidation',
            'timeout': 30
        }
    ]
    
    results = []
    for test in tests:
        result = run_command(test['command'], test['description'], test.get('timeout', 120))
        results.append(result)
    
    return results


def run_comprehensive_validation():
    """Run comprehensive SSOT validation tests."""
    print(f"\n🔬 ISSUE #220 COMPREHENSIVE VALIDATION")
    print(f"Purpose: Complete SSOT consolidation validation (90 minutes)")
    
    test_suites = [
        {
            'command': 'python -m pytest tests/unit/ssot_validation/ -v --tb=short',
            'description': 'Unit SSOT Validation Suite',
            'timeout': 300
        },
        {
            'command': 'python -m pytest tests/integration/ssot_validation/ -v --tb=short',
            'description': 'Integration SSOT Validation Suite',
            'timeout': 600
        },
        {
            'command': 'python -m pytest tests/e2e/golden_path_staging/test_issue_220_golden_path_ssot_preservation.py -v --tb=short',
            'description': 'Golden Path SSOT Preservation (GCP Staging)',
            'timeout': 900
        }
    ]
    
    results = []
    for test_suite in test_suites:
        result = run_command(test_suite['command'], test_suite['description'], test_suite.get('timeout', 120))
        results.append(result)
    
    return results


def run_architecture_compliance_check():
    """Run architecture compliance check if available."""
    print(f"\n📊 ARCHITECTURE COMPLIANCE CHECK")
    
    compliance_commands = [
        'python scripts/check_architecture_compliance.py',
        'python -c "print(\'Architecture compliance script not found\')"'
    ]
    
    for command in compliance_commands:
        try:
            result = run_command(command, 'Architecture Compliance Check', 60)
            if result['success']:
                return result
        except:
            continue
    
    return {'success': False, 'stderr': 'No compliance check available'}


def print_summary(results, test_type):
    """Print test results summary."""
    print(f"\n{'='*80}")
    print(f"📋 ISSUE #220 {test_type.upper()} VALIDATION SUMMARY")
    print(f"{'='*80}")
    
    total_tests = len(results)
    passed_tests = len([r for r in results if r['success']])
    failed_tests = total_tests - passed_tests
    total_duration = sum(r['duration'] for r in results)
    
    print(f"📊 Test Results:")
    print(f"    Total Tests: {total_tests}")
    print(f"    ✅ Passed: {passed_tests}")
    print(f"    ❌ Failed: {failed_tests}")
    print(f"    ⏱️  Total Duration: {total_duration:.1f}s")
    print(f"    📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests > 0:
        print(f"\n❌ Failed Tests:")
        for result in results:
            if not result['success']:
                print(f"    - {result['command']}")
                if result['stderr']:
                    print(f"      Error: {result['stderr'][:100]}...")
    
    # Determine Issue #220 status
    success_rate = (passed_tests / total_tests) * 100
    
    print(f"\n🎯 ISSUE #220 SSOT CONSOLIDATION STATUS:")
    
    if success_rate >= 95:
        print(f"    🎉 CONSOLIDATION COMPLETE")
        print(f"    ✅ SSOT patterns fully implemented")
        print(f"    ✅ Business value preserved")
    elif success_rate >= 80:
        print(f"    ⚠️  CONSOLIDATION MOSTLY COMPLETE")
        print(f"    🔧 Minor issues need resolution")
        print(f"    ✅ Core SSOT patterns working")
    elif success_rate >= 60:
        print(f"    🚧 CONSOLIDATION IN PROGRESS")
        print(f"    🔧 Significant work still needed")
        print(f"    ⚠️  Some SSOT patterns incomplete")
    else:
        print(f"    🚨 CONSOLIDATION INCOMPLETE")
        print(f"    🔧 Major SSOT work required")
        print(f"    ❌ Multiple violations detected")
    
    return success_rate >= 80


def main():
    """Main execution function."""
    if len(sys.argv) < 2:
        test_type = 'quick'
    else:
        test_type = sys.argv[1].lower()
    
    print(f"🚀 Starting Issue #220 SSOT Validation - {test_type.upper()} mode")
    print(f"Working Directory: {os.getcwd()}")
    
    # Run architecture compliance check first
    compliance_result = run_architecture_compliance_check()
    
    # Run appropriate test suite
    if test_type == 'baseline':
        results = run_baseline_validation()
    elif test_type == 'comprehensive':
        results = run_comprehensive_validation()
    else:  # default to quick
        results = run_quick_validation()
    
    # Print summary
    success = print_summary(results, test_type)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()