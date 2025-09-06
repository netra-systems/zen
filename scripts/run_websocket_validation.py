#!/usr/bin/env python
"""Comprehensive WebSocket Validation Test Runner

Business Value Justification:
- Segment: Platform/Internal (Mission Critical Infrastructure)
- Business Goal: Ensure 100% reliability of $500K+ ARR chat functionality before deployment
- Value Impact: Validates all critical WebSocket events that enable substantive AI interactions
- Strategic Impact: Prevents deployment of broken chat functionality that causes customer churn

This test runner provides:
1. Comprehensive execution of all WebSocket validation tests
2. Real-time monitoring and event analysis during test execution
3. Detailed reporting with actionable remediation steps
4. Performance benchmarking and compliance validation
5. Staging environment validation for deployment approval
6. Failure pattern detection and root cause analysis

CRITICAL: This runner must be executed before any staging deployment.
ALL TESTS MUST PASS for deployment approval.
"""

import asyncio
import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess
import traceback

# CRITICAL: Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from loguru import logger

# Import test infrastructure
from shared.isolated_environment import get_env, IsolatedEnvironment
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
from test_framework.websocket_helpers import ensure_websocket_service_ready

# Import monitoring utilities
from tests.mission_critical.websocket_monitoring_utils import (
    WebSocketMonitoringOrchestrator, create_monitoring_session,
    EventMetrics, FailurePatternDetector
)

# Import test components
from tests.mission_critical.websocket_real_test_base import is_docker_available


# ============================================================================
# TEST RUNNER CONFIGURATION
# ============================================================================

class WebSocketValidationConfig:
    """Configuration for WebSocket validation test execution."""
    
    def __init__(self):
        # Test execution settings
        self.test_suite_path = "tests/mission_critical/test_websocket_event_validation_suite.py"
        self.output_dir = "websocket_validation_reports"
        self.timeout_seconds = 900  # 15 minutes
        
        # Environment settings
        self.target_environment = "staging"  # Default to staging validation
        self.require_real_services = True
        self.validate_docker = True
        
        # Test categories
        self.test_categories = [
            "functional",    # Individual event validation
            "integration",   # Full pipeline tests
            "performance",   # Latency and throughput
            "resilience",    # Recovery and reconnection
            "security"       # User isolation and security
        ]
        
        # Performance thresholds
        self.performance_thresholds = {
            "max_avg_latency_ms": 100.0,
            "max_individual_latency_ms": 200.0,
            "min_success_rate_percent": 95.0,
            "max_error_rate_percent": 5.0
        }
        
        # Staging validation requirements
        self.staging_requirements = {
            "min_test_duration_seconds": 60,
            "min_events_validated": 50,
            "required_event_types": [
                "agent_started",
                "agent_thinking", 
                "tool_executing",
                "tool_completed",
                "agent_completed"
            ],
            "max_critical_failures": 0,
            "max_error_failures": 2
        }


# ============================================================================
# TEST EXECUTION ENGINE
# ============================================================================

class WebSocketValidationRunner:
    """Executes comprehensive WebSocket validation tests with monitoring."""
    
    def __init__(self, config: WebSocketValidationConfig):
        self.config = config
        self.start_time = time.time()
        
        # Setup output directories
        self.output_dir = Path(config.output_dir)
        self.session_dir = self.output_dir / f"validation_session_{int(self.start_time)}"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize monitoring
        self.monitoring_orchestrator = create_monitoring_session(
            str(self.session_dir / "monitoring")
        )
        
        # Test execution state
        self.test_results = {}
        self.validation_passed = False
        self.critical_failures = []
        
        # Docker management
        self.docker_manager = None
        
        # Configure logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup comprehensive logging for test execution."""
        log_file = self.session_dir / "validation_execution.log"
        
        # Remove default logger and add file logging
        logger.remove()
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO"
        )
        logger.add(
            str(log_file),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            rotation="10 MB"
        )
    
    async def run_validation(self) -> Dict[str, Any]:
        """Execute comprehensive WebSocket validation."""
        logger.info("=" * 80)
        logger.info("WEBSOCKET VALIDATION TEST SUITE - MISSION CRITICAL")
        logger.info("=" * 80)
        logger.info(f"Target Environment: {self.config.target_environment}")
        logger.info(f"Output Directory: {self.session_dir}")
        logger.info(f"Session ID: {self.session_dir.name}")
        
        try:
            # Phase 1: Environment Preparation
            await self._prepare_environment()
            
            # Phase 2: Service Validation
            await self._validate_services()
            
            # Phase 3: Test Execution with Monitoring
            with self.monitoring_orchestrator.monitor_session("validation_monitoring"):
                await self._execute_test_suite()
            
            # Phase 4: Results Analysis
            await self._analyze_results()
            
            # Phase 5: Generate Comprehensive Report
            final_report = await self._generate_final_report()
            
            # Phase 6: Validation Decision
            self._make_validation_decision(final_report)
            
            return final_report
            
        except Exception as e:
            logger.error(f"Critical error during validation: {e}")
            logger.error(traceback.format_exc())
            
            # Generate error report
            error_report = await self._generate_error_report(e)
            return error_report
    
    async def _prepare_environment(self):
        """Prepare the test environment."""
        logger.info("Phase 1: Environment Preparation")
        
        # Check Docker availability
        if self.config.validate_docker and not is_docker_available():
            raise RuntimeError("Docker is required but not available. Cannot run real WebSocket tests.")
        
        # Initialize Docker manager
        if is_docker_available():
            self.docker_manager = UnifiedDockerManager(
                environment_type=EnvironmentType.TEST,
                use_alpine=True  # Use optimized Alpine containers
            )
            
            # Start required services
            logger.info("Starting Docker services for WebSocket testing...")
            required_services = ["backend", "auth", "db", "redis"]
            
            self.docker_manager.start_services(required_services)
            
            # Verify service health
            health_status = self.docker_manager.get_service_health()
            for service, health in health_status.items():
                if service in required_services and not health.is_healthy:
                    raise RuntimeError(f"Service {service} is not healthy: {health.status}")
            
            logger.info("✓ All Docker services are healthy and ready")
        
        # Validate environment configuration
        env = IsolatedEnvironment()
        
        # Check WebSocket endpoint availability
        if self.config.target_environment == "staging":
            websocket_url = f"ws://{env.get_backend_host('staging')}:{env.get_backend_port('staging')}/ws"
        else:
            websocket_url = f"ws://localhost:8000/ws"
        
        logger.info(f"Target WebSocket URL: {websocket_url}")
        
        # Wait for WebSocket service to be ready
        await ensure_websocket_service_ready(max_wait_seconds=60)
        
        logger.info("✓ Environment preparation completed")
    
    async def _validate_services(self):
        """Validate that required services are operational."""
        logger.info("Phase 2: Service Validation")
        
        # Basic connectivity test
        try:
            # Test database connection
            if self.docker_manager:
                db_healthy = self.docker_manager.get_service_health().get("db", {}).is_healthy
                if not db_healthy:
                    raise RuntimeError("Database service is not healthy")
            
            # Test auth service
            auth_healthy = self.docker_manager.get_service_health().get("auth", {}).is_healthy if self.docker_manager else True
            if not auth_healthy:
                raise RuntimeError("Auth service is not healthy") 
            
            # Test backend service
            backend_healthy = self.docker_manager.get_service_health().get("backend", {}).is_healthy if self.docker_manager else True
            if not backend_healthy:
                raise RuntimeError("Backend service is not healthy")
            
            logger.info("✓ All services validated successfully")
            
        except Exception as e:
            logger.error(f"Service validation failed: {e}")
            raise
    
    async def _execute_test_suite(self):
        """Execute the comprehensive WebSocket validation test suite."""
        logger.info("Phase 3: Test Suite Execution")
        
        # Build pytest command
        test_command = [
            sys.executable, "-m", "pytest",
            self.config.test_suite_path,
            "-v",  # Verbose output
            "--tb=short",  # Short traceback format
            "--capture=no",  # Don't capture output
            f"--timeout={self.config.timeout_seconds}",  # Set timeout
            "--disable-warnings",  # Reduce noise
            "-x",  # Stop on first failure for critical validation
        ]
        
        # Add category markers if specified
        if hasattr(self.config, 'test_markers') and self.config.test_markers:
            test_command.extend(["-m", " or ".join(self.config.test_markers)])
        
        # Add environment variables
        env_vars = os.environ.copy()
        env_vars["PYTHONPATH"] = project_root
        env_vars["WEBSOCKET_TEST_TARGET"] = self.config.target_environment
        
        logger.info(f"Executing test command: {' '.join(test_command)}")
        
        # Execute tests
        try:
            start_time = time.time()
            
            result = subprocess.run(
                test_command,
                cwd=project_root,
                env=env_vars,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds
            )
            
            execution_time = time.time() - start_time
            
            # Store test results
            self.test_results = {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time_seconds": execution_time,
                "command": " ".join(test_command),
                "passed": result.returncode == 0
            }
            
            # Log results summary
            if result.returncode == 0:
                logger.info(f"✓ Test suite PASSED in {execution_time:.1f} seconds")
            else:
                logger.error(f"✗ Test suite FAILED with return code {result.returncode}")
                logger.error("STDOUT:", result.stdout[-2000:])  # Last 2000 chars
                logger.error("STDERR:", result.stderr[-2000:])  # Last 2000 chars
            
        except subprocess.TimeoutExpired:
            logger.error(f"Test suite timed out after {self.config.timeout_seconds} seconds")
            self.test_results = {
                "return_code": -1,
                "stdout": "",
                "stderr": "Test execution timed out",
                "execution_time_seconds": self.config.timeout_seconds,
                "passed": False,
                "timeout": True
            }
        except Exception as e:
            logger.error(f"Error executing test suite: {e}")
            self.test_results = {
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "execution_time_seconds": 0,
                "passed": False,
                "error": str(e)
            }
    
    async def _analyze_results(self):
        """Analyze test execution results and extract metrics."""
        logger.info("Phase 4: Results Analysis")
        
        # Parse test output for metrics
        stdout = self.test_results.get("stdout", "")
        stderr = self.test_results.get("stderr", "")
        
        # Extract pytest results
        self._parse_pytest_output(stdout)
        
        # Extract WebSocket event metrics from monitoring
        if hasattr(self.monitoring_orchestrator, 'real_time_monitor'):
            monitoring_metrics = self.monitoring_orchestrator.real_time_monitor.get_current_metrics()
            self.test_results["monitoring_metrics"] = monitoring_metrics
        
        # Analyze failure patterns if any failures occurred
        if not self.test_results["passed"]:
            await self._analyze_failures()
        
        logger.info("✓ Results analysis completed")
    
    def _parse_pytest_output(self, output: str):
        """Parse pytest output to extract test metrics."""
        lines = output.split('\n')
        
        # Initialize counters
        tests_passed = 0
        tests_failed = 0
        tests_skipped = 0
        tests_errors = 0
        
        # Parse test results
        for line in lines:
            if " PASSED " in line:
                tests_passed += 1
            elif " FAILED " in line:
                tests_failed += 1
                # Extract failure details
                if "CRITICAL" in line.upper():
                    self.critical_failures.append(line)
            elif " SKIPPED " in line:
                tests_skipped += 1
            elif " ERROR " in line:
                tests_errors += 1
        
        # Find summary line
        summary_line = None
        for line in lines:
            if " passed" in line and (" failed" in line or " error" in line or " skipped" in line):
                summary_line = line
                break
        
        self.test_results["pytest_metrics"] = {
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "tests_skipped": tests_skipped,
            "tests_errors": tests_errors,
            "total_tests": tests_passed + tests_failed + tests_skipped + tests_errors,
            "summary_line": summary_line
        }
    
    async def _analyze_failures(self):
        """Analyze test failures and categorize them."""
        logger.info("Analyzing test failures...")
        
        # Analyze stderr for specific failure patterns
        stderr = self.test_results.get("stderr", "")
        
        failure_categories = {
            "docker_issues": [],
            "websocket_connection": [],
            "event_validation": [],
            "performance_issues": [],
            "timeout_issues": [],
            "security_violations": [],
            "other": []
        }
        
        lines = stderr.split('\n')
        for line in lines:
            line_lower = line.lower()
            
            if "docker" in line_lower or "container" in line_lower:
                failure_categories["docker_issues"].append(line)
            elif "websocket" in line_lower and ("connect" in line_lower or "connection" in line_lower):
                failure_categories["websocket_connection"].append(line)
            elif "validation" in line_lower or "event" in line_lower:
                failure_categories["event_validation"].append(line)
            elif "timeout" in line_lower or "timed out" in line_lower:
                failure_categories["timeout_issues"].append(line)
            elif "latency" in line_lower or "performance" in line_lower:
                failure_categories["performance_issues"].append(line)
            elif "isolation" in line_lower or "security" in line_lower:
                failure_categories["security_violations"].append(line)
            elif "error" in line_lower or "failed" in line_lower:
                failure_categories["other"].append(line)
        
        self.test_results["failure_analysis"] = failure_categories
    
    async def _generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final validation report."""
        logger.info("Phase 5: Final Report Generation")
        
        end_time = time.time()
        total_duration = end_time - self.start_time
        
        # Compile comprehensive report
        report = {
            "validation_session": {
                "session_id": self.session_dir.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": total_duration,
                "target_environment": self.config.target_environment,
                "configuration": {
                    "test_suite_path": self.config.test_suite_path,
                    "timeout_seconds": self.config.timeout_seconds,
                    "performance_thresholds": self.config.performance_thresholds,
                    "staging_requirements": self.config.staging_requirements
                }
            },
            "execution_results": self.test_results,
            "environment_validation": {
                "docker_available": is_docker_available(),
                "services_validated": True,  # Set based on actual validation
                "websocket_endpoint_accessible": True  # Set based on actual test
            },
            "compliance_check": self._check_compliance(),
            "recommendations": self._generate_recommendations(),
            "deployment_decision": {
                "approved": False,  # Will be set by _make_validation_decision
                "reason": "",
                "critical_issues": self.critical_failures,
                "required_actions": []
            }
        }
        
        # Save report to file
        report_path = self.session_dir / "comprehensive_validation_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"✓ Final report generated: {report_path}")
        
        return report
    
    def _check_compliance(self) -> Dict[str, Any]:
        """Check compliance against staging requirements."""
        compliance = {
            "overall_passed": True,
            "checks": {},
            "violations": []
        }
        
        # Get monitoring metrics if available
        monitoring_metrics = self.test_results.get("monitoring_metrics", {})
        pytest_metrics = self.test_results.get("pytest_metrics", {})
        
        # Check test duration
        duration_ok = self.test_results.get("execution_time_seconds", 0) >= self.config.staging_requirements["min_test_duration_seconds"]
        compliance["checks"]["min_test_duration"] = duration_ok
        if not duration_ok:
            compliance["violations"].append("Test duration below minimum requirement")
            compliance["overall_passed"] = False
        
        # Check success rate
        success_rate = monitoring_metrics.get("success_rate_percent", 0)
        success_rate_ok = success_rate >= self.config.performance_thresholds["min_success_rate_percent"]
        compliance["checks"]["success_rate"] = success_rate_ok
        if not success_rate_ok:
            compliance["violations"].append(f"Success rate {success_rate}% below {self.config.performance_thresholds['min_success_rate_percent']}%")
            compliance["overall_passed"] = False
        
        # Check critical failures
        critical_failures_ok = len(self.critical_failures) <= self.config.staging_requirements["max_critical_failures"]
        compliance["checks"]["max_critical_failures"] = critical_failures_ok
        if not critical_failures_ok:
            compliance["violations"].append(f"Too many critical failures: {len(self.critical_failures)}")
            compliance["overall_passed"] = False
        
        # Check performance
        avg_latency = monitoring_metrics.get("recent_performance", {}).get("avg_latency_ms", 0)
        performance_ok = avg_latency <= self.config.performance_thresholds["max_avg_latency_ms"]
        compliance["checks"]["performance"] = performance_ok
        if not performance_ok:
            compliance["violations"].append(f"Average latency {avg_latency}ms exceeds {self.config.performance_thresholds['max_avg_latency_ms']}ms")
            compliance["overall_passed"] = False
        
        # Check test passage
        tests_passed = self.test_results.get("passed", False)
        compliance["checks"]["tests_passed"] = tests_passed
        if not tests_passed:
            compliance["violations"].append("One or more tests failed")
            compliance["overall_passed"] = False
        
        return compliance
    
    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on results."""
        recommendations = []
        
        # Check if tests passed
        if not self.test_results.get("passed", False):
            recommendations.append("🚨 CRITICAL: Fix failing tests before deployment")
            
            # Analyze failure categories
            failure_analysis = self.test_results.get("failure_analysis", {})
            
            if failure_analysis.get("docker_issues"):
                recommendations.append("🐳 Docker Issues: Verify Docker setup and service health")
            
            if failure_analysis.get("websocket_connection"):
                recommendations.append("🔌 WebSocket Connection: Check network connectivity and service availability")
            
            if failure_analysis.get("event_validation"):
                recommendations.append("📨 Event Validation: Review WebSocket event generation and validation logic")
            
            if failure_analysis.get("performance_issues"):
                recommendations.append("⚡ Performance Issues: Optimize system performance and review latency bottlenecks")
            
            if failure_analysis.get("security_violations"):
                recommendations.append("🛡️ Security Violations: URGENT - Fix user isolation issues immediately")
            
            if failure_analysis.get("timeout_issues"):
                recommendations.append("⏱️ Timeout Issues: Investigate slow operations and increase timeouts if needed")
        
        # Performance recommendations
        monitoring_metrics = self.test_results.get("monitoring_metrics", {})
        avg_latency = monitoring_metrics.get("recent_performance", {}).get("avg_latency_ms", 0)
        
        if avg_latency > 50:
            recommendations.append("💡 Consider performance optimization - latency above 50ms")
        
        # General recommendations
        if not recommendations:
            recommendations.append("✅ All validations passed - system ready for deployment")
            recommendations.append("💡 Continue monitoring performance in production")
            recommendations.append("🔄 Schedule regular validation runs for ongoing quality assurance")
        
        return recommendations
    
    def _make_validation_decision(self, report: Dict[str, Any]):
        """Make final validation decision for deployment approval."""
        logger.info("Phase 6: Validation Decision")
        
        compliance = report.get("compliance_check", {})
        overall_passed = compliance.get("overall_passed", False)
        
        if overall_passed and self.test_results.get("passed", False):
            self.validation_passed = True
            decision_reason = "All validation checks passed successfully"
            logger.info("✅ VALIDATION APPROVED - Deployment authorized")
        else:
            self.validation_passed = False
            violations = compliance.get("violations", [])
            decision_reason = f"Validation failed due to: {'; '.join(violations)}"
            logger.error("❌ VALIDATION REJECTED - Deployment blocked")
        
        # Update report with decision
        report["deployment_decision"]["approved"] = self.validation_passed
        report["deployment_decision"]["reason"] = decision_reason
        
        if not self.validation_passed:
            report["deployment_decision"]["required_actions"] = [
                "Fix all critical issues identified in the failure analysis",
                "Re-run validation suite to confirm fixes",
                "Review performance metrics and optimize if necessary",
                "Ensure all WebSocket events are properly validated"
            ]
        
        # Log summary
        logger.info("=" * 80)
        logger.info("WEBSOCKET VALIDATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Environment: {self.config.target_environment}")
        logger.info(f"Duration: {report['validation_session']['duration_seconds']:.1f} seconds")
        logger.info(f"Tests Passed: {self.test_results.get('pytest_metrics', {}).get('tests_passed', 0)}")
        logger.info(f"Tests Failed: {self.test_results.get('pytest_metrics', {}).get('tests_failed', 0)}")
        logger.info(f"Critical Failures: {len(self.critical_failures)}")
        logger.info(f"Deployment Approved: {'YES' if self.validation_passed else 'NO'}")
        if not self.validation_passed:
            logger.info(f"Rejection Reason: {decision_reason}")
        logger.info("=" * 80)
    
    async def _generate_error_report(self, error: Exception) -> Dict[str, Any]:
        """Generate error report for critical failures."""
        return {
            "validation_session": {
                "session_id": self.session_dir.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "CRITICAL_ERROR",
                "error": str(error),
                "traceback": traceback.format_exc()
            },
            "deployment_decision": {
                "approved": False,
                "reason": f"Critical error during validation: {error}",
                "required_actions": [
                    "Investigate and fix the critical error",
                    "Verify test infrastructure is properly setup",
                    "Re-run validation suite after fixes"
                ]
            }
        }


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Comprehensive WebSocket Validation Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full validation against staging
  python scripts/run_websocket_validation.py --environment staging

  # Quick validation with custom output directory
  python scripts/run_websocket_validation.py --output-dir custom_reports --timeout 300

  # Validation for specific test categories
  python scripts/run_websocket_validation.py --categories functional integration

  # Continuous validation mode (for CI/CD)
  python scripts/run_websocket_validation.py --ci-mode --fail-fast
        """
    )
    
    parser.add_argument(
        "--environment",
        choices=["local", "staging", "development"],
        default="staging",
        help="Target environment for validation (default: staging)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="websocket_validation_reports",
        help="Output directory for validation reports (default: websocket_validation_reports)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="Test execution timeout in seconds (default: 900)"
    )
    
    parser.add_argument(
        "--categories",
        nargs="*",
        choices=["functional", "integration", "performance", "resilience", "security"],
        help="Specific test categories to run (default: all)"
    )
    
    parser.add_argument(
        "--performance-threshold",
        type=float,
        default=100.0,
        help="Maximum acceptable average latency in ms (default: 100.0)"
    )
    
    parser.add_argument(
        "--ci-mode",
        action="store_true",
        help="Enable CI/CD mode with reduced output and strict validation"
    )
    
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first test failure (useful for quick feedback)"
    )
    
    parser.add_argument(
        "--skip-docker-check",
        action="store_true",
        help="Skip Docker availability check (use with caution)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output"
    )
    
    return parser


async def main():
    """Main execution function."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Create configuration
    config = WebSocketValidationConfig()
    config.target_environment = args.environment
    config.output_dir = args.output_dir
    config.timeout_seconds = args.timeout
    config.validate_docker = not args.skip_docker_check
    
    # Update performance thresholds
    config.performance_thresholds["max_avg_latency_ms"] = args.performance_threshold
    
    # Set test markers if specific categories requested
    if args.categories:
        config.test_markers = args.categories
    
    # Create and run validator
    runner = WebSocketValidationRunner(config)
    
    try:
        # Execute validation
        report = await runner.run_validation()
        
        # Handle CI mode output
        if args.ci_mode:
            # Minimal output for CI/CD systems
            if runner.validation_passed:
                print("VALIDATION_RESULT=PASSED")
                sys.exit(0)
            else:
                print("VALIDATION_RESULT=FAILED")
                print(f"FAILURE_REASON={report['deployment_decision']['reason']}")
                sys.exit(1)
        else:
            # Full interactive output
            print("\n" + "="*80)
            print("WEBSOCKET VALIDATION COMPLETED")
            print("="*80)
            print(f"Session ID: {report['validation_session']['session_id']}")
            print(f"Duration: {report['validation_session']['duration_seconds']:.1f} seconds")
            print(f"Result: {'PASSED' if runner.validation_passed else 'FAILED'}")
            
            if not runner.validation_passed:
                print(f"Reason: {report['deployment_decision']['reason']}")
                print("\nRequired Actions:")
                for action in report['deployment_decision']['required_actions']:
                    print(f"  - {action}")
            
            print(f"\nDetailed report: {runner.session_dir}/comprehensive_validation_report.json")
            print("="*80)
        
        # Exit with appropriate code
        sys.exit(0 if runner.validation_passed else 1)
        
    except KeyboardInterrupt:
        logger.warning("Validation interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"Validation failed with critical error: {e}")
        if args.verbose:
            logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    # Run the validation
    asyncio.run(main())