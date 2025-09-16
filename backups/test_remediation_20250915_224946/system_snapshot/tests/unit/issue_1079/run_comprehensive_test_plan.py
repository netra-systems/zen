#!/usr/bin/env python3
"""
Issue #1079 Comprehensive Test Plan Execution

This script runs all 4 phases of the Issue #1079 test reproduction plan:
- Phase 1: Import Failures Reproduction
- Phase 2: Dependency Analysis
- Phase 3: Environment Validation
- Phase 4: Test Execution Simulation

The goal is to reproduce the exact conditions described in Issue #1079:
- 217-second timeout during test execution
- ModuleNotFoundError for supply_database_manager
- KeyError for missing Agent class
- Infinite import loops causing hangs
"""

import sys
import os
import time
import subprocess
import json
from pathlib import Path
from datetime import datetime

class Issue1079TestPlanExecutor:
    """Comprehensive test plan executor for Issue #1079"""

    def __init__(self):
        self.results = {
            'execution_time': None,
            'phases': {},
            'summary': {
                'total_tests_run': 0,
                'total_failures': 0,
                'total_errors': 0,
                'issue_reproduced': False,
                'key_findings': []
            }
        }
        self.start_time = time.time()

    def run_phase(self, phase_num, phase_name, script_path):
        """Run a single phase of the test plan"""
        print(f"\n{'='*80}")
        print(f"EXECUTING PHASE {phase_num}: {phase_name}")
        print(f"{'='*80}")
        print(f"Script: {script_path}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        phase_start = time.time()

        try:
            # Run the phase test script
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per phase
                cwd=os.getcwd()
            )

            duration = time.time() - phase_start

            # Parse results
            phase_result = {
                'duration': duration,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'status': 'passed' if result.returncode == 0 else 'failed'
            }

            # Extract key information from output
            self._extract_phase_findings(phase_num, result.stdout)

            print(f"\nPhase {phase_num} completed in {duration:.2f} seconds")
            print(f"Return code: {result.returncode}")

            if result.returncode != 0:
                print("STDERR:")
                print(result.stderr)

            # Show key parts of stdout
            stdout_lines = result.stdout.split('\n')
            print("\nKey output:")
            for line in stdout_lines:
                if any(keyword in line.lower() for keyword in
                      ['error', 'failed', 'timeout', 'success', 'reproduced', 'found']):
                    print(f"  {line}")

            self.results['phases'][f'phase_{phase_num}'] = phase_result

        except subprocess.TimeoutExpired:
            duration = time.time() - phase_start
            print(f"\n! PHASE {phase_num} TIMED OUT after {duration:.2f} seconds")

            self.results['phases'][f'phase_{phase_num}'] = {
                'duration': duration,
                'return_code': -1,
                'status': 'timeout',
                'error': 'Phase execution timed out'
            }

            # Timeout might indicate the hanging import issue
            self.results['summary']['key_findings'].append(
                f"Phase {phase_num} timeout - possible import hang reproduction"
            )

        except Exception as e:
            duration = time.time() - phase_start
            print(f"\n- PHASE {phase_num} FAILED with exception: {e}")

            self.results['phases'][f'phase_{phase_num}'] = {
                'duration': duration,
                'return_code': -2,
                'status': 'error',
                'error': str(e)
            }

    def _extract_phase_findings(self, phase_num, output):
        """Extract key findings from phase output"""
        findings = []

        # Look for specific patterns in output
        lines = output.split('\n')

        for line in lines:
            line_lower = line.lower()

            # Import failures
            if 'modulenotfounderror' in line_lower and 'supply_database_manager' in line_lower:
                findings.append("Reproduced supply_database_manager import failure")

            # Timeouts
            if 'timeout' in line_lower and ('217' in line or 'second' in line_lower):
                findings.append("Reproduced 217-second timeout scenario")

            # KeyError for Agent
            if 'keyerror' in line_lower and 'agent' in line_lower:
                findings.append("Reproduced Agent class KeyError")

            # Circular imports
            if 'circular' in line_lower and 'import' in line_lower:
                findings.append("Detected circular import patterns")

            # Memory issues
            if 'memory' in line_lower and ('growth' in line_lower or 'leak' in line_lower):
                findings.append("Detected memory issues during imports")

            # Successful reproductions
            if 'successfully reproduced' in line_lower:
                findings.append(f"Phase {phase_num}: Successfully reproduced issue conditions")

        # Add findings to summary
        self.results['summary']['key_findings'].extend(findings)

        # Check if we reproduced the core issue
        critical_reproductions = [
            'supply_database_manager import failure',
            '217-second timeout',
            'circular import'
        ]

        if any(any(critical in finding.lower() for critical in critical_reproductions)
               for finding in findings):
            self.results['summary']['issue_reproduced'] = True

    def run_fake_test_validation(self):
        """Run fake test validation to ensure our tests work"""
        print(f"\n{'='*80}")
        print("RUNNING FAKE TEST VALIDATION")
        print(f"{'='*80}")

        fake_test_script = Path("tests/fake_test_check.py")

        if fake_test_script.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(fake_test_script)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=os.getcwd()
                )

                if result.returncode == 0:
                    print("+ Fake test validation passed")
                else:
                    print("- Fake test validation failed")
                    print(f"Error: {result.stderr}")

            except Exception as e:
                print(f"- Fake test validation error: {e}")
        else:
            print("! Fake test script not found, creating simple validation...")

            # Create and run a simple validation
            validation_script = '''
import sys
import time

print("Fake test validation:")
print(f"Python version: {sys.version}")
print(f"Current directory: {sys.path[0] if sys.path else 'Unknown'}")

# Test basic imports
try:
    import unittest
    print("+ unittest import successful")
except ImportError as e:
    print(f"- unittest import failed: {e}")

try:
    from pathlib import Path
    print("+ pathlib import successful")
except ImportError as e:
    print(f"- pathlib import failed: {e}")

print("Fake test validation completed")
'''

            try:
                result = subprocess.run(
                    [sys.executable, '-c', validation_script],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                print(result.stdout)
            except Exception as e:
                print(f"Validation error: {e}")

    def generate_final_report(self):
        """Generate final test execution report"""
        total_duration = time.time() - self.start_time
        self.results['execution_time'] = total_duration

        print(f"\n{'='*80}")
        print("ISSUE #1079 COMPREHENSIVE TEST PLAN - FINAL REPORT")
        print(f"{'='*80}")
        print(f"Total execution time: {total_duration:.2f} seconds")
        print(f"Phases executed: {len(self.results['phases'])}")

        # Phase summary
        print(f"\nPhase Results:")
        for phase_name, phase_data in self.results['phases'].items():
            status = phase_data['status']
            duration = phase_data['duration']
            return_code = phase_data.get('return_code', 'N/A')

            status_symbol = "+" if status == 'passed' else "-" if status == 'failed' else "!"
            print(f"  {status_symbol} {phase_name}: {status} ({duration:.2f}s, rc:{return_code})")

        # Key findings
        print(f"\nKey Findings ({len(self.results['summary']['key_findings'])}):")
        for finding in self.results['summary']['key_findings']:
            print(f"  * {finding}")

        # Issue reproduction assessment
        issue_reproduced = self.results['summary']['issue_reproduced']
        print(f"\nIssue #1079 Reproduction Status:")
        if issue_reproduced:
            print("  + SUCCESS: Core issue conditions successfully reproduced")
            print("    This confirms the import failures and timeout issues described in Issue #1079")
        else:
            print("  - PARTIAL: Could not fully reproduce all issue conditions")
            print("    Further investigation may be needed")

        # Test execution decision
        print(f"\nTEST EXECUTION DECISION:")

        failed_phases = sum(1 for phase_data in self.results['phases'].values()
                           if phase_data['status'] != 'passed')

        if failed_phases == 0:
            print("  [X] TESTS NEED REVISION:")
            print("    All phases passed - tests may not be reproducing the actual issue")
            print("    Recommendation: Revise tests to be more sensitive to failure conditions")
        elif issue_reproduced:
            print("  [+] TESTS ARE VALID:")
            print("    Tests successfully reproduce Issue #1079 conditions")
            print("    Recommendation: Use these tests for debugging and validation")
        else:
            print("  [!] TESTS PARTIALLY VALID:")
            print("    Some failures detected but core issue not fully reproduced")
            print("    Recommendation: Enhance tests to capture more failure modes")

        # Save detailed results
        report_file = Path(f"tests/unit/issue_1079/test_execution_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        try:
            with open(report_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\nDetailed report saved: {report_file}")
        except Exception as e:
            print(f"\nFailed to save report: {e}")

        return issue_reproduced, failed_phases

def main():
    """Main execution function"""
    print("ISSUE #1079 - AGENT UNIT TEST EXECUTION FAILURE")
    print("Comprehensive Test Plan Execution")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    executor = Issue1079TestPlanExecutor()

    # Define test phases
    phases = [
        (1, "Import Failures Reproduction", "tests/unit/issue_1079/phase1_import_failures_reproduction.py"),
        (2, "Dependency Analysis", "tests/unit/issue_1079/phase2_dependency_analysis.py"),
        (3, "Environment Validation", "tests/unit/issue_1079/phase3_environment_validation.py"),
        (4, "Test Execution Simulation", "tests/unit/issue_1079/phase4_test_execution_simulation.py")
    ]

    # Run fake test validation first
    executor.run_fake_test_validation()

    # Execute each phase
    for phase_num, phase_name, script_path in phases:
        script_file = Path(script_path)

        if not script_file.exists():
            print(f"\n- SKIPPING PHASE {phase_num}: Script not found - {script_path}")
            continue

        executor.run_phase(phase_num, phase_name, script_path)

    # Generate final report and decision
    issue_reproduced, failed_phases = executor.generate_final_report()

    # Return appropriate exit code
    if issue_reproduced and failed_phases > 0:
        print("\n[TARGET] MISSION ACCOMPLISHED: Issue #1079 successfully reproduced!")
        return 0  # Success - we reproduced the issue
    elif failed_phases == 0:
        print("\n[WRENCH] TESTS NEED WORK: No failures detected - tests may be too permissive")
        return 1  # Tests need revision
    else:
        print("\n[SEARCH] PARTIAL SUCCESS: Some issues detected but core problem not reproduced")
        return 2  # Partial success

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)