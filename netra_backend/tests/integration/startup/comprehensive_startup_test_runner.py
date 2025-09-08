"""
Comprehensive Startup Phase Test Runner
=====================================

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Ensure complete startup validation across all phases
- Value Impact: Prevents broken chat from reaching production (90% of business value)
- Strategic Impact: Reduces downtime and improves system reliability

This runner executes all startup phase tests in the correct order and generates
comprehensive reports on startup system health and chat readiness.

CRITICAL: Tests validate the deterministic startup sequence ensures chat functionality.
"""

import asyncio
import logging
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import json
import subprocess

from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class TestResult:
    """Individual test result with detailed metrics."""
    test_name: str
    phase: str
    status: str  # 'passed', 'failed', 'skipped', 'error'
    execution_time: float
    error_message: Optional[str] = None
    business_value: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'test_name': self.test_name,
            'phase': self.phase,
            'status': self.status,
            'execution_time': self.execution_time,
            'error_message': self.error_message,
            'business_value': self.business_value,
            'details': self.details
        }


@dataclass
class PhaseResult:
    """Results for an entire startup phase."""
    phase_name: str
    total_tests: int
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    total_time: float = 0.0
    tests: List[TestResult] = field(default_factory=list)
    
    def add_test_result(self, result: TestResult):
        """Add a test result to this phase."""
        self.tests.append(result)
        self.total_time += result.execution_time
        
        if result.status == 'passed':
            self.passed += 1
        elif result.status == 'failed':
            self.failed += 1
        elif result.status == 'skipped':
            self.skipped += 1
        elif result.status == 'error':
            self.errors += 1
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate for this phase."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'phase_name': self.phase_name,
            'total_tests': self.total_tests,
            'passed': self.passed,
            'failed': self.failed,
            'skipped': self.skipped,
            'errors': self.errors,
            'total_time': self.total_time,
            'success_rate': self.success_rate,
            'tests': [test.to_dict() for test in self.tests]
        }


@dataclass
class StartupTestReport:
    """Comprehensive startup test report."""
    timestamp: str
    environment: str
    total_execution_time: float
    phases: List[PhaseResult] = field(default_factory=list)
    overall_status: str = 'unknown'
    chat_readiness: bool = False
    business_value_validated: bool = False
    
    @property
    def total_tests(self) -> int:
        return sum(phase.total_tests for phase in self.phases)
    
    @property
    def total_passed(self) -> int:
        return sum(phase.passed for phase in self.phases)
    
    @property
    def total_failed(self) -> int:
        return sum(phase.failed for phase in self.phases)
    
    @property
    def overall_success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.total_passed / self.total_tests) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp,
            'environment': self.environment,
            'total_execution_time': self.total_execution_time,
            'total_tests': self.total_tests,
            'total_passed': self.total_passed,
            'total_failed': self.total_failed,
            'overall_success_rate': self.overall_success_rate,
            'overall_status': self.overall_status,
            'chat_readiness': self.chat_readiness,
            'business_value_validated': self.business_value_validated,
            'phases': [phase.to_dict() for phase in self.phases]
        }


class StartupTestRunner:
    """
    Comprehensive runner for all startup phase tests.
    
    Executes tests in the correct phase order and validates system readiness
    for chat operations (primary business value delivery).
    """
    
    # Define startup phases in execution order
    STARTUP_PHASES = [
        'init',
        'dependencies', 
        'database',
        'cache',
        'services',
        'websocket',
        'finalize'
    ]
    
    # Map phases to test files
    PHASE_TEST_FILES = {
        'init': ['test_init_phase_comprehensive.py'],
        'dependencies': ['test_dependencies_phase_comprehensive.py'],
        'database': ['test_database_phase_comprehensive.py'],
        'cache': ['test_cache_phase_comprehensive.py'],
        'services': ['test_services_phase_comprehensive.py'],
        'websocket': ['test_websocket_phase_comprehensive.py'],
        'finalize': ['test_finalize_phase_comprehensive.py']
    }
    
    def __init__(self, test_dir: Optional[Path] = None):
        """Initialize startup test runner."""
        self.test_dir = test_dir or Path(__file__).parent
        self.report = StartupTestReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            environment=get_env().get('ENVIRONMENT', 'test'),
            total_execution_time=0.0
        )
        
        # Test execution configuration
        self.timeout_per_test = 300.0  # 5 minutes per test
        self.timeout_per_phase = 900.0  # 15 minutes per phase
        self.fail_fast = False  # Continue testing even if phase fails
        
    async def run_all_phases(self, specific_phases: Optional[List[str]] = None) -> StartupTestReport:
        """
        Run all startup phase tests in correct order.
        
        Args:
            specific_phases: Optional list of phases to run (defaults to all)
            
        Returns:
            Comprehensive test report
        """
        start_time = time.time()
        phases_to_run = specific_phases or self.STARTUP_PHASES
        
        logger.info("=" * 80)
        logger.info("🚀 COMPREHENSIVE STARTUP PHASE TEST EXECUTION")
        logger.info("=" * 80)
        logger.info(f"Environment: {self.report.environment}")
        logger.info(f"Phases to run: {', '.join(phases_to_run)}")
        logger.info(f"Test directory: {self.test_dir}")
        logger.info("")
        
        try:
            # Run phases in order
            for phase_name in phases_to_run:
                if phase_name not in self.STARTUP_PHASES:
                    logger.warning(f"Unknown phase '{phase_name}' - skipping")
                    continue
                    
                logger.info(f"🔄 PHASE: {phase_name.upper()}")
                phase_result = await self._run_phase_tests(phase_name)
                self.report.phases.append(phase_result)
                
                # Log phase summary
                logger.info(f"✅ Phase {phase_name}: {phase_result.passed}/{phase_result.total_tests} passed "
                          f"({phase_result.success_rate:.1f}%) in {phase_result.total_time:.2f}s")
                
                # Check if phase failed critically
                if phase_result.failed > 0 or phase_result.errors > 0:
                    logger.warning(f"⚠️ Phase {phase_name} had {phase_result.failed} failures, "
                                 f"{phase_result.errors} errors")
                    
                    if self.fail_fast:
                        logger.error(f"🛑 Stopping execution due to phase {phase_name} failures (fail-fast mode)")
                        break
                
                logger.info("")
            
            # Calculate overall results
            self.report.total_execution_time = time.time() - start_time
            self._determine_overall_status()
            
            # Generate final report
            self._log_final_summary()
            
            return self.report
            
        except Exception as e:
            logger.error(f"Critical error during test execution: {e}")
            logger.error(traceback.format_exc())
            self.report.overall_status = 'critical_error'
            self.report.total_execution_time = time.time() - start_time
            raise
    
    async def _run_phase_tests(self, phase_name: str) -> PhaseResult:
        """Run all tests for a specific phase."""
        phase_start = time.time()
        test_files = self.PHASE_TEST_FILES.get(phase_name, [])
        
        phase_result = PhaseResult(
            phase_name=phase_name,
            total_tests=0
        )
        
        if not test_files:
            logger.warning(f"No test files defined for phase {phase_name}")
            return phase_result
        
        for test_file in test_files:
            test_path = self.test_dir / test_file
            
            if not test_path.exists():
                logger.warning(f"Test file not found: {test_path}")
                continue
                
            # Run pytest on the test file
            try:
                logger.info(f"  📋 Running {test_file}...")
                test_results = await self._run_pytest_file(test_path, phase_name)
                
                for result in test_results:
                    phase_result.add_test_result(result)
                    phase_result.total_tests += 1
                    
                    # Log individual test result
                    status_icon = {
                        'passed': '✅',
                        'failed': '❌', 
                        'skipped': '⏭️',
                        'error': '💥'
                    }.get(result.status, '❓')
                    
                    logger.info(f"    {status_icon} {result.test_name} ({result.execution_time:.2f}s)")
                    
                    if result.error_message:
                        logger.error(f"      Error: {result.error_message}")
                
            except Exception as e:
                # Create error result for failed test file
                error_result = TestResult(
                    test_name=f"{test_file}_execution",
                    phase=phase_name,
                    status='error',
                    execution_time=0.0,
                    error_message=f"Test file execution failed: {str(e)}",
                    details={'exception_type': type(e).__name__}
                )
                phase_result.add_test_result(error_result)
                phase_result.total_tests += 1
                
                logger.error(f"    💥 Failed to execute {test_file}: {e}")
        
        return phase_result
    
    async def _run_pytest_file(self, test_path: Path, phase_name: str) -> List[TestResult]:
        """Run pytest on a specific test file and parse results."""
        results = []
        
        # Build pytest command
        cmd = [
            sys.executable, '-m', 'pytest',
            str(test_path),
            '-v',  # Verbose output
            '--tb=short',  # Short traceback format
            '--durations=10',  # Show 10 slowest tests
            '--json-report',  # Generate JSON report
            f'--json-report-file={test_path.parent / f".pytest_cache/{test_path.stem}_report.json"}'
        ]
        
        try:
            # Run pytest with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=test_path.parent.parent.parent.parent  # Project root
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout_per_test
                )
            except asyncio.TimeoutError:
                process.terminate()
                await process.wait()
                
                # Create timeout result
                timeout_result = TestResult(
                    test_name=f"{test_path.stem}_timeout",
                    phase=phase_name,
                    status='error',
                    execution_time=self.timeout_per_test,
                    error_message=f"Test execution timed out after {self.timeout_per_test}s"
                )
                return [timeout_result]
            
            # Parse pytest output for test results
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')
            
            # Try to parse JSON report if available
            json_report_path = test_path.parent / f".pytest_cache/{test_path.stem}_report.json"
            if json_report_path.exists():
                try:
                    results = self._parse_json_report(json_report_path, phase_name)
                except Exception as e:
                    logger.warning(f"Failed to parse JSON report: {e}")
                    results = self._parse_stdout_results(stdout_str, stderr_str, phase_name, test_path.stem)
            else:
                results = self._parse_stdout_results(stdout_str, stderr_str, phase_name, test_path.stem)
            
        except Exception as e:
            # Create error result for subprocess failure
            error_result = TestResult(
                test_name=f"{test_path.stem}_subprocess_error",
                phase=phase_name,
                status='error',
                execution_time=0.0,
                error_message=f"Subprocess execution failed: {str(e)}"
            )
            results = [error_result]
        
        return results
    
    def _parse_json_report(self, json_path: Path, phase_name: str) -> List[TestResult]:
        """Parse pytest JSON report into TestResult objects."""
        results = []
        
        try:
            with open(json_path, 'r') as f:
                report_data = json.load(f)
            
            for test in report_data.get('tests', []):
                # Extract test information
                test_name = test.get('nodeid', 'unknown_test')
                if '::' in test_name:
                    test_name = test_name.split('::')[-1]
                
                status = test.get('outcome', 'unknown')
                execution_time = test.get('duration', 0.0)
                
                # Get error information
                error_message = None
                if status in ['failed', 'error'] and 'call' in test:
                    call_info = test['call']
                    if 'longrepr' in call_info:
                        error_message = str(call_info['longrepr'])[:500]  # Truncate long errors
                
                # Determine business value based on test name
                business_value = self._extract_business_value(test_name)
                
                result = TestResult(
                    test_name=test_name,
                    phase=phase_name,
                    status=status,
                    execution_time=execution_time,
                    error_message=error_message,
                    business_value=business_value,
                    details={
                        'test_file': json_path.stem,
                        'full_nodeid': test.get('nodeid', '')
                    }
                )
                results.append(result)
                
        except Exception as e:
            logger.error(f"Error parsing JSON report {json_path}: {e}")
        
        return results
    
    def _parse_stdout_results(self, stdout: str, stderr: str, phase_name: str, file_stem: str) -> List[TestResult]:
        """Parse pytest stdout output into TestResult objects."""
        results = []
        
        # Look for test result lines in stdout
        lines = stdout.split('\n')
        for line in lines:
            if '::' in line and any(status in line for status in ['PASSED', 'FAILED', 'SKIPPED', 'ERROR']):
                try:
                    # Parse test result line
                    parts = line.split()
                    if len(parts) >= 2:
                        test_name = parts[0].split('::')[-1] if '::' in parts[0] else parts[0]
                        status_part = parts[-1]
                        
                        # Map pytest status to our status
                        status_mapping = {
                            'PASSED': 'passed',
                            'FAILED': 'failed',
                            'SKIPPED': 'skipped',
                            'ERROR': 'error'
                        }
                        
                        status = 'unknown'
                        for pytest_status, our_status in status_mapping.items():
                            if pytest_status in status_part:
                                status = our_status
                                break
                        
                        # Extract execution time if available
                        execution_time = 0.0
                        for part in parts:
                            if 's' in part and any(c.isdigit() for c in part):
                                try:
                                    time_str = part.replace('s', '').replace('[', '').replace(']', '')
                                    execution_time = float(time_str)
                                    break
                                except ValueError:
                                    pass
                        
                        result = TestResult(
                            test_name=test_name,
                            phase=phase_name,
                            status=status,
                            execution_time=execution_time,
                            business_value=self._extract_business_value(test_name),
                            details={'test_file': file_stem}
                        )
                        results.append(result)
                        
                except Exception as e:
                    logger.debug(f"Error parsing test line '{line}': {e}")
        
        # If no results parsed, create a generic result
        if not results:
            status = 'passed' if 'failed' not in stderr.lower() else 'failed'
            result = TestResult(
                test_name=f"{file_stem}_execution",
                phase=phase_name,
                status=status,
                execution_time=0.0,
                error_message=stderr[:500] if status == 'failed' else None,
                details={'test_file': file_stem}
            )
            results.append(result)
        
        return results
    
    def _extract_business_value(self, test_name: str) -> Optional[str]:
        """Extract business value description from test name."""
        business_value_indicators = {
            'chat': 'Enables chat functionality (90% of business value)',
            'readiness': 'Ensures system ready for production',
            'health': 'Validates system health for reliability',
            'performance': 'Ensures acceptable response times',
            'scalability': 'Supports business growth',
            'validation': 'Prevents broken functionality reaching users',
            'critical_path': 'Validates core business workflows',
            'completion': 'Ensures complete startup sequence',
            'business': 'Direct business value validation',
            'integration': 'Validates service integration for reliability'
        }
        
        test_name_lower = test_name.lower()
        for indicator, value in business_value_indicators.items():
            if indicator in test_name_lower:
                return value
        
        return None
    
    def _determine_overall_status(self):
        """Determine overall test status based on phase results."""
        total_tests = self.total_tests
        total_failed = self.total_failed
        total_errors = sum(phase.errors for phase in self.phases)
        
        # Check for critical startup phases
        critical_phases = ['database', 'services', 'finalize']
        critical_failures = sum(
            phase.failed + phase.errors 
            for phase in self.phases 
            if phase.phase_name in critical_phases
        )
        
        # Determine chat readiness based on critical phases
        self.report.chat_readiness = critical_failures == 0
        
        # Determine business value validation
        business_value_tests = sum(
            1 for phase in self.report.phases 
            for test in phase.tests 
            if test.business_value and test.status == 'passed'
        )
        self.report.business_value_validated = business_value_tests > 0
        
        # Overall status logic
        if total_tests == 0:
            self.report.overall_status = 'no_tests'
        elif critical_failures > 0:
            self.report.overall_status = 'critical_failure'
        elif total_errors > 0:
            self.report.overall_status = 'error'
        elif total_failed > 0:
            self.report.overall_status = 'failure'
        elif self.overall_success_rate >= 95.0:
            self.report.overall_status = 'excellent'
        elif self.overall_success_rate >= 80.0:
            self.report.overall_status = 'good'
        elif self.overall_success_rate >= 60.0:
            self.report.overall_status = 'acceptable'
        else:
            self.report.overall_status = 'poor'
    
    def _log_final_summary(self):
        """Log comprehensive final summary."""
        logger.info("=" * 80)
        logger.info("📊 COMPREHENSIVE STARTUP TEST RESULTS")
        logger.info("=" * 80)
        
        # Overall metrics
        logger.info(f"🎯 Overall Status: {self.report.overall_status.upper()}")
        logger.info(f"⏱️  Total Time: {self.report.total_execution_time:.2f}s")
        logger.info(f"📈 Success Rate: {self.report.overall_success_rate:.1f}%")
        logger.info(f"🧪 Total Tests: {self.report.total_tests}")
        logger.info(f"✅ Passed: {self.report.total_passed}")
        logger.info(f"❌ Failed: {self.report.total_failed}")
        logger.info("")
        
        # Business value validation
        chat_icon = "✅" if self.report.chat_readiness else "❌"
        business_icon = "✅" if self.report.business_value_validated else "❌"
        
        logger.info("🎯 BUSINESS VALUE VALIDATION:")
        logger.info(f"  {chat_icon} Chat Readiness: {'READY' if self.report.chat_readiness else 'NOT READY'}")
        logger.info(f"  {business_icon} Business Value: {'VALIDATED' if self.report.business_value_validated else 'NOT VALIDATED'}")
        logger.info("")
        
        # Phase breakdown
        logger.info("📋 PHASE BREAKDOWN:")
        for phase in self.report.phases:
            phase_icon = "✅" if phase.success_rate >= 80 else "❌" if phase.success_rate < 50 else "⚠️"
            logger.info(f"  {phase_icon} {phase.phase_name.upper()}: {phase.passed}/{phase.total_tests} "
                       f"({phase.success_rate:.1f}%) - {phase.total_time:.2f}s")
        
        # Critical issues
        critical_issues = []
        for phase in self.report.phases:
            for test in phase.tests:
                if test.status in ['failed', 'error'] and test.business_value:
                    critical_issues.append(f"{phase.phase_name}::{test.test_name}")
        
        if critical_issues:
            logger.warning("")
            logger.warning("🚨 CRITICAL BUSINESS VALUE ISSUES:")
            for issue in critical_issues[:5]:  # Show top 5
                logger.warning(f"  ⚠️ {issue}")
            if len(critical_issues) > 5:
                logger.warning(f"  ... and {len(critical_issues) - 5} more")
        
        logger.info("=" * 80)
        
        # Final recommendation
        if self.report.chat_readiness and self.report.business_value_validated:
            logger.info("🟢 RECOMMENDATION: System ready for chat operations")
        elif self.report.chat_readiness:
            logger.info("🟡 RECOMMENDATION: Chat ready but business validation needs attention")  
        else:
            logger.error("🔴 RECOMMENDATION: System NOT ready for chat operations")
        
        logger.info("=" * 80)
    
    def save_report(self, output_path: Optional[Path] = None) -> Path:
        """Save comprehensive report to JSON file."""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.test_dir / f"startup_test_report_{timestamp}.json"
        
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save report
        with open(output_path, 'w') as f:
            json.dump(self.report.to_dict(), f, indent=2)
        
        logger.info(f"📄 Test report saved: {output_path}")
        return output_path


async def main():
    """Main entry point for running startup tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run comprehensive startup phase tests')
    parser.add_argument('--phases', nargs='+', 
                       choices=StartupTestRunner.STARTUP_PHASES,
                       help='Specific phases to test (default: all)')
    parser.add_argument('--fail-fast', action='store_true',
                       help='Stop on first phase failure')
    parser.add_argument('--output', type=Path,
                       help='Output path for test report')
    parser.add_argument('--test-dir', type=Path,
                       help='Directory containing test files')
    
    args = parser.parse_args()
    
    # Create runner
    runner = StartupTestRunner(test_dir=args.test_dir)
    runner.fail_fast = args.fail_fast
    
    try:
        # Run tests
        report = await runner.run_all_phases(specific_phases=args.phases)
        
        # Save report
        report_path = runner.save_report(args.output)
        
        # Exit with appropriate code
        if report.chat_readiness and report.business_value_validated:
            sys.exit(0)  # Success
        elif report.overall_status in ['critical_failure', 'error']:
            sys.exit(2)  # Critical error
        else:
            sys.exit(1)  # Some failures
            
    except KeyboardInterrupt:
        logger.warning("Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Critical error during test execution: {e}")
        logger.error(traceback.format_exc())
        sys.exit(3)


if __name__ == "__main__":
    asyncio.run(main())