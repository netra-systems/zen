#!/usr/bin/env python3
"""
Test Executor Module
Handles test execution and autonomous review operations
Complies with 300-line limit and 8-line function constraint
"""

import subprocess
import re
from pathlib import Path
from typing import List
from dataclasses import dataclass

@dataclass
class TestExecutionResult:
    """Test execution results with comprehensive metrics"""
    success: bool = False
    exit_code: int = 0
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    execution_time: float = 0.0
    coverage_percentage: float = 0.0
    output: str = ""
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class TestExecutor:
    """Executes comprehensive test suites with coverage analysis"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root

    async def run_comprehensive_tests(self) -> TestExecutionResult:
        """Execute comprehensive test suite with full coverage"""
        result = await self._execute_test_command([
            "python", "test_runner.py", "--mode", "comprehensive"
        ])
        return result

    async def run_unit_tests(self) -> TestExecutionResult:
        """Execute unit test suite with coverage"""
        result = await self._execute_test_command([
            "python", "test_runner.py", "--level", "unit"
        ])
        return result

    async def run_integration_tests(self) -> TestExecutionResult:
        """Execute integration test suite"""
        result = await self._execute_test_command([
            "python", "test_runner.py", "--level", "integration"
        ])
        return result

    async def _execute_test_command(self, command: List[str]) -> TestExecutionResult:
        """Execute test command and parse results"""
        try:
            process = subprocess.run(
                command, capture_output=True, text=True, 
                cwd=self.project_root, timeout=600
            )
            return self._parse_test_output(process)
        except subprocess.TimeoutExpired:
            return TestExecutionResult(success=False, errors=["Test execution timeout"])

    def _parse_test_output(self, process: subprocess.CompletedProcess) -> TestExecutionResult:
        """Parse test execution output into structured result"""
        result = TestExecutionResult()
        result.exit_code = process.returncode
        result.success = process.returncode == 0
        result.output = process.stdout
        
        if process.stderr:
            result.errors = [process.stderr]
        
        self._extract_test_metrics(result)
        return result

    def _extract_test_metrics(self, result: TestExecutionResult) -> None:
        """Extract test metrics from execution output"""
        # Parse test counts and coverage from output
        
        # Extract test counts
        test_match = re.search(r'(\d+) passed.*?(\d+) failed', result.output)
        if test_match:
            result.passed_tests = int(test_match.group(1))
            result.failed_tests = int(test_match.group(2))
        
        # Extract coverage percentage
        coverage_match = re.search(r'TOTAL.*?(\d+)%', result.output)
        if coverage_match:
            result.coverage_percentage = float(coverage_match.group(1))

class AutonomousReviewRunner:
    """Runs autonomous test review system"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root

    async def run_autonomous_review(self, mode: str = "auto") -> bool:
        """Execute autonomous test review with specified mode"""
        try:
            result = subprocess.run(
                ["python", "scripts/test_autonomous_review.py", f"--{mode}"],
                capture_output=True, text=True, cwd=self.project_root, timeout=300
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    async def run_quick_review(self) -> bool:
        """Execute quick autonomous review"""
        return await self.run_autonomous_review("quick")

    async def run_comprehensive_review(self) -> bool:
        """Execute comprehensive autonomous review"""
        return await self.run_autonomous_review("comprehensive")