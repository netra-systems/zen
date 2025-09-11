#!/usr/bin/env python3
"""
Agent Test Validator - Comprehensive test runner and quality validator for critical agent tests.

This module discovers, executes, and validates all agent test suites with comprehensive metrics.
Maximum 300 lines, 8 lines per function as per SPEC/conventions.xml.
"""

import ast
import asyncio
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import coverage
import pytest

# Import existing test framework components
from tests.unified_test_runner import UnifiedTestRunner
from test_framework.test_discovery import TestDiscovery

PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class TestMetrics:
    """Test execution and quality metrics"""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    execution_time: float = 0.0
    coverage_percentage: float = 0.0
    async_test_count: int = 0
    mock_usage_ratio: float = 0.0
    assertion_count: int = 0
    test_dependencies: List[str] = None
    
    def __post_init__(self):
        if self.test_dependencies is None:
            self.test_dependencies = []


@dataclass
class ValidationResult:
    """Validation result for test quality analysis"""
    is_valid: bool
    metrics: TestMetrics
    issues: List[str]
    coverage_gaps: List[str]
    recommendations: List[str]


class AgentTestValidator:
    """Elite test validator for agent test suites with comprehensive analysis"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.test_discovery = TestDiscovery(self.project_root)
        self.runner = UnifiedTestRunner()
        self.coverage_data = coverage.Coverage()
        
    def find_critical_test_files(self) -> List[Path]:
        """Discover all *_critical.py test files"""
        pattern = "*_critical.py"
        critical_files = list(self.project_root.rglob(pattern))
        test_files = [f for f in critical_files if f.is_file()]
        return sorted(test_files)
    
    def validate_test_structure(self, test_file: Path) -> Tuple[bool, List[str]]:
        """Validate test file structure and conventions"""
        issues = []
        try:
            content = test_file.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except Exception as e:
            return False, [f"Parse error: {e}"]
        
        has_test_class = any(isinstance(n, ast.ClassDef) for n in tree.body)
        test_methods = self._count_test_methods(tree)
        if test_methods == 0:
            issues.append("No test methods found")
        return len(issues) == 0, issues
    
    def _count_test_methods(self, tree: ast.AST) -> int:
        """Count test methods in AST"""
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                count += 1
        return count
    
    def check_test_assertions(self, test_file: Path) -> int:
        """Count assertion statements in test file"""
        try:
            content = test_file.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except:
            return 0
        
        assertion_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                assertion_count += 1
        return assertion_count
    
    async def run_test_suite(self, test_files: List[Path]) -> TestMetrics:
        """Execute test suite and collect metrics"""
        start_time = time.time()
        
        # Start coverage collection
        self.coverage_data.start()
        
        test_args = [str(f) for f in test_files]
        exit_code, output = self.runner.run_backend_tests(test_args, timeout=600)
        
        # Stop coverage collection
        self.coverage_data.stop()
        self.coverage_data.save()
        
        execution_time = time.time() - start_time
        return self._parse_test_results(output, execution_time)
    
    def _parse_test_results(self, output: str, execution_time: float) -> TestMetrics:
        """Parse pytest output to extract metrics"""
        lines = output.split('\n')
        passed = failed = total = 0
        
        for line in lines:
            if 'passed' in line and 'failed' in line:
                # Parse pytest summary line
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'passed' in part and i > 0:
                        passed = int(parts[i-1])
                    if 'failed' in part and i > 0:
                        failed = int(parts[i-1])
        
        total = passed + failed
        return TestMetrics(total, passed, failed, execution_time)
    
    def analyze_coverage_data(self) -> Tuple[float, List[str]]:
        """Analyze code coverage metrics"""
        try:
            coverage_report = self.coverage_data.report()
            missing_lines = []
            
            for filename in self.coverage_data.get_data().measured_files():
                analysis = self.coverage_data.analysis(filename)
                missing_lines.extend([f"{filename}:{line}" for line in analysis.missing])
            
            return coverage_report, missing_lines[:20]  # Limit to first 20
        except:
            return 0.0, []
    
    def analyze_async_usage(self, test_files: List[Path]) -> int:
        """Count async test methods across all files"""
        async_count = 0
        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')
                tree = ast.parse(content)
            except:
                continue
            
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith('test_'):
                    async_count += 1
        return async_count
    
    def analyze_mock_usage(self, test_files: List[Path]) -> float:
        """Calculate mock to real test ratio"""
        mock_count = real_count = 0
        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')
            except:
                continue
            
            mock_count += content.count('Mock') + content.count('mock')
            real_count += content.count('assert')
        
        return mock_count / max(real_count, 1)
    
    def check_test_dependencies(self, test_files: List[Path]) -> List[str]:
        """Detect test interdependencies that could cause issues"""
        dependencies = []
        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')
                if 'depends_on' in content or 'pytest.mark.dependency' in content:
                    dependencies.append(str(test_file))
            except:
                continue
        return dependencies
    
    async def validate_all_tests(self) -> ValidationResult:
        """Main validation orchestration"""
        test_files = self.find_critical_test_files()
        if not test_files:
            return ValidationResult(False, TestMetrics(), ["No critical test files found"], [], [])
        
        # Validate structure and run tests
        structure_issues = []
        for test_file in test_files:
            valid, issues = self.validate_test_structure(test_file)
            structure_issues.extend(issues)
        
        metrics = await self.run_test_suite(test_files)
        return self._compile_validation_result(test_files, metrics, structure_issues)
    
    def _compile_validation_result(self, test_files: List[Path], metrics: TestMetrics, issues: List[str]) -> ValidationResult:
        """Compile comprehensive validation result"""
        # Enhance metrics with additional analysis
        metrics.async_test_count = self.analyze_async_usage(test_files)
        metrics.mock_usage_ratio = self.analyze_mock_usage(test_files)
        metrics.test_dependencies = self.check_test_dependencies(test_files)
        
        coverage_pct, coverage_gaps = self.analyze_coverage_data()
        metrics.coverage_percentage = coverage_pct
        
        # Count total assertions
        total_assertions = sum(self.check_test_assertions(f) for f in test_files)
        metrics.assertion_count = total_assertions
        
        recommendations = self._generate_recommendations(metrics, len(test_files))
        is_valid = len(issues) == 0 and metrics.failed_tests == 0
        
        return ValidationResult(is_valid, metrics, issues, coverage_gaps, recommendations)
    
    def _generate_recommendations(self, metrics: TestMetrics, file_count: int) -> List[str]:
        """Generate quality improvement recommendations"""
        recommendations = []
        
        if metrics.coverage_percentage < 80:
            recommendations.append("Increase test coverage above 80%")
        if metrics.assertion_count / max(metrics.total_tests, 1) < 2:
            recommendations.append("Add more assertions per test")
        if metrics.async_test_count == 0 and file_count > 0:
            recommendations.append("Add async test coverage")
        if metrics.mock_usage_ratio > 3.0:
            recommendations.append("Reduce mock usage, add integration tests")
        
        return recommendations
    
    def generate_console_summary(self, result: ValidationResult) -> str:
        """Generate console summary report"""
        metrics = result.metrics
        status = "✅ PASS" if result.is_valid else "❌ FAIL"
        
        summary = f"""
Agent Test Validation Summary {status}
=====================================
Files: {len(self.find_critical_test_files())} critical test files
Tests: {metrics.total_tests} total ({metrics.passed_tests} passed, {metrics.failed_tests} failed)
Coverage: {metrics.coverage_percentage:.1f}%
Execution Time: {metrics.execution_time:.2f}s
Async Tests: {metrics.async_test_count}
Mock Ratio: {metrics.mock_usage_ratio:.2f}
Assertions: {metrics.assertion_count}
"""
        return summary
    
    def create_html_report(self, result: ValidationResult) -> str:
        """Create detailed HTML report"""
        timestamp = datetime.now().isoformat()
        html = f"""
<!DOCTYPE html>
<html><head><title>Agent Test Validation Report</title></head>
<body>
<h1>Agent Test Validation Report</h1>
<p>Generated: {timestamp}</p>
<h2>Summary</h2>
<p>Status: {'PASS' if result.is_valid else 'FAIL'}</p>
<p>Coverage: {result.metrics.coverage_percentage:.1f}%</p>
<h2>Issues</h2>
<ul>{''.join(f'<li>{issue}</li>' for issue in result.issues)}</ul>
<h2>Recommendations</h2>
<ul>{''.join(f'<li>{rec}</li>' for rec in result.recommendations)}</ul>
</body></html>
"""
        return html
    
    def export_json_metrics(self, result: ValidationResult) -> Dict[str, Any]:
        """Export metrics as JSON for CI/CD integration"""
        return {
            "timestamp": datetime.now().isoformat(),
            "validation_passed": result.is_valid,
            "metrics": {
                "total_tests": result.metrics.total_tests,
                "passed_tests": result.metrics.passed_tests,
                "failed_tests": result.metrics.failed_tests,
                "coverage_percentage": result.metrics.coverage_percentage,
                "execution_time": result.metrics.execution_time,
                "async_test_count": result.metrics.async_test_count,
                "mock_usage_ratio": result.metrics.mock_usage_ratio,
                "assertion_count": result.metrics.assertion_count
            },
            "issues": result.issues,
            "coverage_gaps": result.coverage_gaps[:10],  # Limit for JSON size
            "recommendations": result.recommendations
        }
    
    async def save_reports(self, result: ValidationResult) -> None:
        """Save all report formats to test_reports directory"""
        reports_dir = self.project_root / "test_reports"
        reports_dir.mkdir(exist_ok=True)
        
        # Console summary
        console_report = self.generate_console_summary(result)
        print(console_report)
        
        # HTML report
        html_report = self.create_html_report(result)
        (reports_dir / "agent_validation_report.html").write_text(html_report)
        
        # JSON metrics
        json_metrics = self.export_json_metrics(result)
        (reports_dir / "agent_validation_metrics.json").write_text(json.dumps(json_metrics, indent=2))


async def main():
    """Main entry point for agent test validation"""
    import argparse
    parser = argparse.ArgumentParser(description="Validate agent tests")
    parser.add_argument("--dry-run", action="store_true", help="Analyze structure only, don't run tests")
    args = parser.parse_args()
    
    validator = AgentTestValidator()
    
    if args.dry_run:
        # Just analyze structure without running tests
        test_files = validator.find_critical_test_files()
        print(f"Found {len(test_files)} critical test files:")
        for f in test_files:
            print(f"  {f.relative_to(validator.project_root)}")
        
        # Test structure validation on first file
        if test_files:
            test_file = test_files[0]
            print(f"\nAnalyzing structure of: {test_file.name}")
            valid, issues = validator.validate_test_structure(test_file)
            print(f"  Valid: {valid}")
            if issues:
                print(f"  Issues: {issues}")
            
            async_count = validator.analyze_async_usage([test_file])
            assertion_count = validator.check_test_assertions(test_file)
            mock_ratio = validator.analyze_mock_usage([test_file])
            
            print(f"  Async tests: {async_count}")
            print(f"  Assertions: {assertion_count}")
            print(f"  Mock ratio: {mock_ratio:.2f}")
        
        return
    
    result = await validator.validate_all_tests()
    await validator.save_reports(result)
    
    # Exit with appropriate code for CI/CD
    exit_code = 0 if result.is_valid else 1
    print(f"\nValidation {'PASSED' if result.is_valid else 'FAILED'}")
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())