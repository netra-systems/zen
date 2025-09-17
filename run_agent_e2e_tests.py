#!/usr/bin/env python3
"""
Agent and E2E Test Runner for Netra Apex Platform
Focuses on GCP staging environment without Docker requirements
"""

import sys
import os
import subprocess
import time
from pathlib import Path
import json

# Setup path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

class TestExecutionReport:
    def __init__(self):
        self.results = []
        self.start_time = time.time()
        
    def add_result(self, test_type, test_command, success, output, error):
        self.results.append({
            'test_type': test_type,
            'test_command': test_command,
            'success': success,
            'output': output,
            'error': error,
            'duration': time.time() - self.start_time
        })
        
    def print_summary(self):
        print("\n" + "="*80)
        print("📊 NETRA APEX TEST EXECUTION SUMMARY")
        print("="*80)
        
        successful_tests = [r for r in self.results if r['success']]
        failed_tests = [r for r in self.results if not r['success']]
        
        print(f"✅ Successful tests: {len(successful_tests)}")
        print(f"❌ Failed tests: {len(failed_tests)}")
        print(f"⏱️  Total duration: {time.time() - self.start_time:.2f}s")
        
        if failed_tests:
            print("\n🔍 FAILED TESTS DETAILS:")
            print("-" * 40)
            for test in failed_tests:
                print(f"❌ {test['test_type']}")
                print(f"   Command: {test['test_command']}")
                if test['error']:
                    print(f"   Error: {test['error'][:200]}...")
                print()

def run_command(command, timeout=300):
    """Run a command and return success, output, error."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=PROJECT_ROOT
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return False, "", str(e)

def main():
    print("🚀 Starting Netra Apex Agent and E2E Tests")
    print("Focus: GCP Staging Environment (No Docker)")
    print("=" * 60)
    
    report = TestExecutionReport()
    
    # Test commands to run
    test_commands = [
        # Agent-related unit tests
        {
            'type': 'Agent Unit Tests',
            'command': 'python tests/unified_test_runner.py --category unit --pattern agent --fast-fail --no-docker'
        },
        
        # E2E staging tests
        {
            'type': 'E2E Staging Tests',  
            'command': 'python tests/unified_test_runner.py --category e2e --env staging --fast-fail --no-docker'
        },
        
        # Mission critical agent tests
        {
            'type': 'Mission Critical Agent Tests',
            'command': 'python tests/unified_test_runner.py --category mission_critical --pattern agent --fast-fail --no-docker'
        },
        
        # Staging specific agent tests
        {
            'type': 'Staging Agent Tests',
            'command': 'python -m pytest tests/staging/test_staging_agent_execution.py -v --tb=short'
        }
    ]
    
    print(f"📋 Running {len(test_commands)} test categories...")
    
    for i, test_config in enumerate(test_commands, 1):
        print(f"\n[{i}/{len(test_commands)}] 🧪 {test_config['type']}")
        print(f"Command: {test_config['command']}")
        print("-" * 40)
        
        success, output, error = run_command(test_config['command'])
        report.add_result(
            test_config['type'],
            test_config['command'],
            success,
            output,
            error
        )
        
        if success:
            print("✅ PASSED")
            if output:
                # Show last few lines of output for successful tests
                output_lines = output.strip().split('\n')
                for line in output_lines[-5:]:
                    print(f"   {line}")
        else:
            print("❌ FAILED")
            if error:
                print("Error output:")
                error_lines = error.strip().split('\n')
                for line in error_lines[:10]:  # Show first 10 lines of error
                    print(f"   ❌ {line}")
            if output:
                print("Standard output:")
                output_lines = output.strip().split('\n')
                for line in output_lines[:5]:  # Show first 5 lines of output
                    print(f"   📄 {line}")
    
    # Print final summary
    report.print_summary()
    
    # Return appropriate exit code
    failed_count = len([r for r in report.results if not r['success']])
    return 0 if failed_count == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)