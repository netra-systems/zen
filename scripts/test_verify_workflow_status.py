#!/usr/bin/env python3
"""
Test suite for verify_workflow_status.py

Tests various scenarios and documents the verification results.
"""

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class TestResult:
    """Test result data."""
    name: str
    passed: bool
    output: str
    error: str
    exit_code: int
    description: str

class WorkflowStatusTester:
    """Test suite for workflow status verification script."""
    
    def __init__(self):
        self.script_path = "scripts/verify_workflow_status.py"
        self.results: List[TestResult] = []
    
    def run_test(self, name: str, description: str, args: List[str]) -> TestResult:
        """Run a single test case."""
        print(f"\n[TEST] Running test: {name}")
        print(f"   Description: {description}")
        print(f"   Command: python {self.script_path} {' '.join(args)}")
        
        try:
            result = subprocess.run(
                [sys.executable, self.script_path] + args,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            test_result = TestResult(
                name=name,
                passed=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
                exit_code=result.returncode,
                description=description
            )
            
            print(f"   [OK] Exit code: {result.returncode}")
            if result.stdout:
                print(f"   [OUTPUT] Output: {result.stdout[:100]}...")
            if result.stderr:
                print(f"   [ERROR] Error: {result.stderr[:100]}...")
                
        except subprocess.TimeoutExpired:
            test_result = TestResult(
                name=name,
                passed=False,
                output="",
                error="Test timed out",
                exit_code=-1,
                description=description
            )
            print(f"   [TIMEOUT] Test timed out")
        
        self.results.append(test_result)
        return test_result
    
    def test_help_functionality(self):
        """Test help display."""
        self.run_test(
            "help_display",
            "Verify help text displays correctly",
            ["--help"]
        )
    
    def test_argument_validation(self):
        """Test argument validation."""
        # Missing required arguments
        self.run_test(
            "missing_args",
            "Should fail when missing required arguments",
            ["--repo", "test/repo"]
        )
        
        # Invalid wait-for-completion usage
        self.run_test(
            "invalid_wait",
            "Should fail when --wait-for-completion used without --workflow-name",
            ["--repo", "test/repo", "--run-id", "123", "--wait-for-completion"]
        )
    
    def test_token_handling(self):
        """Test GitHub token handling."""
        # Missing token
        self.run_test(
            "missing_token",
            "Should fail when no token provided",
            ["--repo", "microsoft/vscode", "--workflow-name", "ci"]
        )
        
        # Invalid token
        self.run_test(
            "invalid_token",
            "Should fail with invalid token",
            ["--repo", "microsoft/vscode", "--workflow-name", "ci", "--token", "invalid_token"]
        )
    
    def test_repository_validation(self):
        """Test repository validation."""
        # Non-existent repository
        self.run_test(
            "nonexistent_repo",
            "Should fail with non-existent repository",
            ["--repo", "nonexistent/repo123456", "--workflow-name", "ci", "--token", "fake_token"]
        )
    
    def test_workflow_validation(self):
        """Test workflow validation."""
        # Non-existent workflow
        self.run_test(
            "nonexistent_workflow",
            "Should fail with non-existent workflow",
            ["--repo", "microsoft/vscode", "--workflow-name", "nonexistent-workflow", "--token", "fake_token"]
        )
    
    def test_output_formats(self):
        """Test different output formats."""
        # Table format (default)
        self.run_test(
            "table_output",
            "Test table output format",
            ["--repo", "microsoft/vscode", "--workflow-name", "ci", "--token", "fake_token"]
        )
        
        # JSON format
        self.run_test(
            "json_output",
            "Test JSON output format", 
            ["--repo", "microsoft/vscode", "--workflow-name", "ci", "--output", "json", "--token", "fake_token"]
        )
    
    def test_run_id_functionality(self):
        """Test specific run ID functionality."""
        self.run_test(
            "specific_run_id",
            "Test checking specific workflow run ID",
            ["--repo", "microsoft/vscode", "--run-id", "123456", "--token", "fake_token"]
        )
    
    def generate_report(self) -> str:
        """Generate test report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        report = f"""
# Workflow Status Verification Test Report

## Summary
- **Total Tests**: {total_tests}
- **Passed**: {passed_tests}
- **Failed**: {failed_tests}
- **Success Rate**: {(passed_tests/total_tests)*100:.1f}%

## Test Results

"""
        
        for result in self.results:
            status = "[PASS]" if result.passed else "[FAIL]"
            report += f"""
### {result.name} - {status}
**Description**: {result.description}
**Exit Code**: {result.exit_code}

"""
            
            if result.output:
                report += f"**Output**:\n```\n{result.output[:500]}\n```\n\n"
            
            if result.error:
                report += f"**Error**:\n```\n{result.error[:500]}\n```\n\n"
        
        return report
    
    def run_all_tests(self):
        """Run all test cases."""
        print("Starting Workflow Status Verification Tests")
        print("=" * 60)
        
        # Run test categories
        self.test_help_functionality()
        self.test_argument_validation()
        self.test_token_handling()
        self.test_repository_validation()
        self.test_workflow_validation()
        self.test_output_formats()
        self.test_run_id_functionality()
        
        print("\n" + "=" * 60)
        print("Tests completed!")
        
        # Generate and save report
        report = self.generate_report()
        
        # Save to file
        with open("workflow_verification_test_report.md", "w") as f:
            f.write(report)
        
        print(f"\nTest report saved to: workflow_verification_test_report.md")
        
        # Print summary
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        print(f"\nSummary: {passed_tests}/{total_tests} tests passed")
        
        return report

def main():
    """Main entry point."""
    tester = WorkflowStatusTester()
    report = tester.run_all_tests()
    
    # Print the report
    print("\n" + "=" * 60)
    print("DETAILED REPORT")
    print("=" * 60)
    print(report)

if __name__ == "__main__":
    main()