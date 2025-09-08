"""
Agent Execution Test Runner and Validation

This module provides utilities to run all agent execution integration tests
and validate that they follow real UserExecutionContext patterns without
mocking internal agent logic.

Business Value:
- Ensures test suite maintains high quality and authenticity
- Validates that tests actually test real agent behavior
- Provides comprehensive test execution and reporting
- Catches test anti-patterns that would compromise test value
"""

import asyncio
import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
import pytest

# Add the netra_backend path to sys.path for imports
current_dir = Path(__file__).parent
netra_backend_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(netra_backend_dir))

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ValidationReport:
    """Report on test validation results."""
    
    def __init__(self):
        self.total_tests = 0
        self.validated_tests = 0
        self.violations = []
        self.warnings = []
        self.test_modules = []
        self.execution_results = {}
        
    def add_violation(self, test_name: str, violation_type: str, description: str):
        """Add a test validation violation."""
        self.violations.append({
            'test_name': test_name,
            'type': violation_type,
            'description': description
        })
        
    def add_warning(self, test_name: str, warning_type: str, description: str):
        """Add a test validation warning."""
        self.warnings.append({
            'test_name': test_name,
            'type': warning_type,
            'description': description
        })
        
    def add_test_result(self, test_name: str, passed: bool, execution_time: float, details: Dict[str, Any]):
        """Add test execution result."""
        self.execution_results[test_name] = {
            'passed': passed,
            'execution_time': execution_time,
            'details': details
        }
        
    def generate_report(self) -> str:
        """Generate comprehensive validation report."""
        report_lines = [
            "=" * 80,
            "AGENT EXECUTION INTEGRATION TEST VALIDATION REPORT",
            "=" * 80,
            "",
            f"Total Tests Analyzed: {self.total_tests}",
            f"Validated Tests: {self.validated_tests}",
            f"Violations Found: {len(self.violations)}",
            f"Warnings Found: {len(self.warnings)}",
            f"Test Modules: {len(self.test_modules)}",
            ""
        ]
        
        if self.violations:
            report_lines.extend([
                "CRITICAL VIOLATIONS:",
                "-" * 40
            ])
            for violation in self.violations:
                report_lines.extend([
                    f"Test: {violation['test_name']}",
                    f"Type: {violation['type']}",
                    f"Description: {violation['description']}",
                    ""
                ])
        
        if self.warnings:
            report_lines.extend([
                "WARNINGS:",
                "-" * 40
            ])
            for warning in self.warnings:
                report_lines.extend([
                    f"Test: {warning['test_name']}",
                    f"Type: {warning['type']}",
                    f"Description: {warning['description']}",
                    ""
                ])
                
        if self.execution_results:
            report_lines.extend([
                "EXECUTION RESULTS:",
                "-" * 40
            ])
            
            passed_tests = sum(1 for r in self.execution_results.values() if r['passed'])
            total_executed = len(self.execution_results)
            
            report_lines.extend([
                f"Tests Executed: {total_executed}",
                f"Tests Passed: {passed_tests}",
                f"Success Rate: {passed_tests/total_executed:.1%}" if total_executed > 0 else "Success Rate: N/A",
                ""
            ])
            
            for test_name, result in self.execution_results.items():
                status = "✓ PASSED" if result['passed'] else "✗ FAILED"
                time_str = f"{result['execution_time']:.2f}s"
                report_lines.append(f"{status} {test_name} ({time_str})")
        
        report_lines.extend([
            "",
            "=" * 80,
            "VALIDATION SUMMARY:",
            f"✓ Real UserExecutionContext patterns: {self.validated_tests}/{self.total_tests}",
            f"✓ No internal logic mocks: {self.total_tests - len([v for v in self.violations if v['type'] == 'mock_violation'])}/{self.total_tests}",
            f"✓ Business value focus: {self.total_tests - len([v for v in self.violations if v['type'] == 'business_value'])}/{self.total_tests}",
            "=" * 80
        ])
        
        return "\n".join(report_lines)


class AgentExecutionTestValidator:
    """Validator for agent execution integration tests."""
    
    def __init__(self):
        self.report = ValidationReport()
        
    def validate_test_file(self, file_path: Path) -> None:
        """Validate a single test file for compliance."""
        try:
            # Import the test module
            module_name = file_path.stem
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            self.report.test_modules.append(module_name)
            
            # Find all test methods
            for class_name in dir(module):
                cls = getattr(module, class_name)
                if inspect.isclass(cls) and class_name.startswith('Test'):
                    self._validate_test_class(cls, module_name)
                    
        except Exception as e:
            logger.error(f"Failed to validate test file {file_path}: {e}")
            self.report.add_violation(
                str(file_path), 
                "import_error", 
                f"Could not import test module: {e}"
            )
    
    def _validate_test_class(self, test_class, module_name: str) -> None:
        """Validate a test class for compliance."""
        class_name = test_class.__name__
        
        for method_name in dir(test_class):
            method = getattr(test_class, method_name)
            if callable(method) and method_name.startswith('test_'):
                full_test_name = f"{module_name}.{class_name}.{method_name}"
                self.report.total_tests += 1
                self._validate_test_method(method, full_test_name)
    
    def _validate_test_method(self, test_method, test_name: str) -> None:
        """Validate a single test method for compliance."""
        try:
            # Get method source code
            source_lines = inspect.getsourcelines(test_method)[0]
            source_code = ''.join(source_lines)
            
            # Validate UserExecutionContext usage
            self._validate_user_execution_context_usage(source_code, test_name)
            
            # Validate no internal logic mocking
            self._validate_no_internal_logic_mocks(source_code, test_name)
            
            # Validate business value focus
            self._validate_business_value_focus(source_code, test_name)
            
            # Validate real WebSocket events
            self._validate_websocket_event_patterns(source_code, test_name)
            
            # Validate agent execution patterns
            self._validate_agent_execution_patterns(source_code, test_name)
            
            self.report.validated_tests += 1
            
        except Exception as e:
            self.report.add_violation(
                test_name,
                "validation_error", 
                f"Could not validate test method: {e}"
            )
    
    def _validate_user_execution_context_usage(self, source_code: str, test_name: str) -> None:
        """Validate proper UserExecutionContext usage."""
        context_patterns = [
            "UserExecutionContext",
            "create_user_execution_context",
            "context.user_id",
            "context.run_id",
            "context.metadata"
        ]
        
        context_usage_count = sum(1 for pattern in context_patterns if pattern in source_code)
        
        if context_usage_count < 2:
            self.report.add_violation(
                test_name,
                "context_usage",
                "Test does not appear to use UserExecutionContext patterns adequately"
            )
        
        # Check for proper context creation
        if "create_user_execution_context" not in source_code and "UserExecutionContext.from_request" not in source_code:
            self.report.add_warning(
                test_name,
                "context_creation",
                "Test should create UserExecutionContext using proper factory methods"
            )
    
    def _validate_no_internal_logic_mocks(self, source_code: str, test_name: str) -> None:
        """Validate that internal agent logic is not mocked."""
        prohibited_mocks = [
            "mock.*execute.*=",  # Mocking agent execute method
            "patch.*agent.*execute",  # Patching agent execution
            "AsyncMock.*BaseAgent",  # Mocking BaseAgent class
            "MagicMock.*SupervisorAgent",  # Mocking SupervisorAgent
        ]
        
        for pattern in prohibited_mocks:
            import re
            if re.search(pattern, source_code, re.IGNORECASE):
                self.report.add_violation(
                    test_name,
                    "mock_violation",
                    f"Test appears to mock internal agent logic: {pattern}"
                )
        
        # Allow external dependency mocks (these are acceptable)
        acceptable_mocks = [
            "MockWebSocketManager",  # External WebSocket infrastructure
            "MockLLMManager",  # External LLM services
            "mock_tool_classes",  # External tool dependencies
        ]
        
        # Check if test uses acceptable patterns
        has_acceptable_mocks = any(pattern in source_code for pattern in acceptable_mocks)
        has_any_mocks = "Mock" in source_code or "mock" in source_code
        
        if has_any_mocks and not has_acceptable_mocks:
            self.report.add_warning(
                test_name,
                "mock_pattern",
                "Test uses mocking - verify it only mocks external dependencies"
            )
    
    def _validate_business_value_focus(self, source_code: str, test_name: str) -> None:
        """Validate that test focuses on business value delivery."""
        business_value_indicators = [
            "business_output",
            "insights",
            "recommendations", 
            "cost",
            "optimization",
            "performance",
            "analysis",
            "value",
            "deliverable"
        ]
        
        business_focus_count = sum(1 for indicator in business_value_indicators if indicator in source_code.lower())
        
        if business_focus_count < 3:
            self.report.add_violation(
                test_name,
                "business_value",
                "Test does not appear to focus adequately on business value delivery"
            )
        
        # Check for business assertions
        business_assertions = [
            "assert.*business",
            "assert.*insight",
            "assert.*recommendation",
            "assert.*value"
        ]
        
        import re
        has_business_assertions = any(re.search(pattern, source_code, re.IGNORECASE) for pattern in business_assertions)
        
        if not has_business_assertions:
            self.report.add_warning(
                test_name,
                "business_assertions",
                "Test should include assertions about business value delivery"
            )
    
    def _validate_websocket_event_patterns(self, source_code: str, test_name: str) -> None:
        """Validate WebSocket event patterns in tests."""
        critical_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        # Check if test is WebSocket-focused
        if "websocket" in test_name.lower() or "event" in test_name.lower():
            event_coverage = sum(1 for event in critical_events if event in source_code)
            
            if event_coverage < 3:
                self.report.add_violation(
                    test_name,
                    "websocket_events",
                    f"WebSocket test should cover more critical events (found {event_coverage}/5)"
                )
        
        # Check for proper event validation
        if "websocket" in source_code.lower():
            event_validation_patterns = [
                "validate_websocket_events",
                "get_events_for_run",
                "events_by_type"
            ]
            
            has_event_validation = any(pattern in source_code for pattern in event_validation_patterns)
            
            if not has_event_validation:
                self.report.add_warning(
                    test_name,
                    "event_validation",
                    "WebSocket test should validate event delivery and content"
                )
    
    def _validate_agent_execution_patterns(self, source_code: str, test_name: str) -> None:
        """Validate proper agent execution patterns."""
        execution_patterns = [
            "await.*execute",
            "stream_updates=True",
            "context",
            "result"
        ]
        
        execution_pattern_count = sum(1 for pattern in execution_patterns if pattern in source_code)
        
        if execution_pattern_count < 2:
            self.report.add_warning(
                test_name,
                "execution_patterns",
                "Test should use proper agent execution patterns"
            )
        
        # Check for isolation validation
        isolation_patterns = [
            "isolation",
            "user_id",
            "context.user_id",
            "validate.*context"
        ]
        
        has_isolation_validation = any(pattern in source_code for pattern in isolation_patterns)
        
        if not has_isolation_validation:
            self.report.add_warning(
                test_name,
                "isolation_validation",
                "Test should validate user isolation and context integrity"
            )


async def run_agent_execution_tests() -> ValidationReport:
    """Run all agent execution integration tests and validate compliance."""
    validator = AgentExecutionTestValidator()
    
    # Find all test files in the agent_execution directory
    test_dir = Path(__file__).parent
    test_files = list(test_dir.glob("test_*.py"))
    
    # Exclude this validation file
    test_files = [f for f in test_files if f.name != "test_runner_validation.py"]
    
    logger.info(f"Found {len(test_files)} test files to validate")
    
    # Validate each test file
    for test_file in test_files:
        logger.info(f"Validating {test_file.name}")
        validator.validate_test_file(test_file)
    
    # Execute tests and collect results
    logger.info("Executing tests with pytest")
    
    try:
        # Run pytest on the agent_execution directory
        import subprocess
        import time
        
        test_start_time = time.time()
        
        # Run pytest with detailed output
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            str(test_dir),
            "-v",
            "--tb=short",
            "-x",  # Stop on first failure for faster feedback
            "--durations=10"  # Show slowest 10 tests
        ], capture_output=True, text=True, cwd=str(netra_backend_dir))
        
        test_end_time = time.time()
        test_execution_time = test_end_time - test_start_time
        
        # Parse pytest results
        output_lines = result.stdout.split('\n')
        passed_tests = []
        failed_tests = []
        
        for line in output_lines:
            if "PASSED" in line:
                test_name = line.split("::")[0] if "::" in line else line
                passed_tests.append(test_name.strip())
            elif "FAILED" in line:
                test_name = line.split("::")[0] if "::" in line else line
                failed_tests.append(test_name.strip())
        
        # Add execution results to report
        for test_name in passed_tests:
            validator.report.add_test_result(test_name, True, 0.0, {"pytest_result": "passed"})
        
        for test_name in failed_tests:
            validator.report.add_test_result(test_name, False, 0.0, {"pytest_result": "failed"})
        
        # Add overall execution info
        validator.report.execution_results["_overall"] = {
            "passed": result.returncode == 0,
            "execution_time": test_execution_time,
            "details": {
                "total_passed": len(passed_tests),
                "total_failed": len(failed_tests),
                "pytest_output": result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout  # Last 1000 chars
            }
        }
        
        logger.info(f"Test execution completed in {test_execution_time:.2f}s")
        logger.info(f"Passed: {len(passed_tests)}, Failed: {len(failed_tests)}")
        
    except Exception as e:
        logger.error(f"Failed to execute tests: {e}")
        validator.report.add_violation(
            "_test_execution",
            "execution_error",
            f"Could not execute tests: {e}"
        )
    
    return validator.report


def validate_test_authenticity() -> bool:
    """Main function to validate test authenticity and patterns.
    
    Returns:
        True if all tests pass validation, False otherwise
    """
    print("🚀 Starting Agent Execution Test Validation...")
    print("=" * 60)
    
    # Run async validation
    report = asyncio.run(run_agent_execution_tests())
    
    # Generate and display report
    report_text = report.generate_report()
    print(report_text)
    
    # Determine overall success
    critical_issues = len(report.violations)
    test_failures = sum(1 for r in report.execution_results.values() if not r.get('passed', True))
    
    overall_success = critical_issues == 0 and test_failures == 0
    
    if overall_success:
        print("✅ ALL TESTS PASS VALIDATION - Agent execution tests use real patterns!")
    else:
        print(f"❌ VALIDATION ISSUES FOUND - {critical_issues} violations, {test_failures} test failures")
    
    return overall_success


if __name__ == "__main__":
    # Run validation when script is executed directly
    success = validate_test_authenticity()
    sys.exit(0 if success else 1)