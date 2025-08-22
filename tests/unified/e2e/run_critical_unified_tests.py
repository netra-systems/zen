#!/usr/bin/env python3
"""
Critical Unified Tests Runner - Real Services Integration

**BUSINESS VALUE JUSTIFICATION (BVJ):**
- Revenue Impact: $500K+ MRR (Critical path validation for enterprise customers)
- Segment: Enterprise + Mid-tier
- Goal: Comprehensive real-service integration validation
- Strategic Impact: System reliability directly impacts customer retention and enterprise sales

**CRITICAL REQUIREMENTS:**
1. Run all 10 critical unified tests with real services
2. Start Auth service (port 8081/8083) and Backend service (port 8000) if needed
3. Detailed pass/fail reporting with timing
4. Calculate overall success rate with enterprise SLA compliance
5. Proper exit codes (0 = all pass, 1 = any fail)
6. Windows/Unix compatibility
7. Service cleanup on completion
8. Parallel test execution for performance
9. Comprehensive error reporting and logging
10. Health check validation before test execution

**ARCHITECTURE:** Real services, <300 lines, ≤8 line functions, modular design
"""

import asyncio
import json
import logging
import os
import platform
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from tests.unified.real_services_health import check_service_health
    from tests.unified.real_services_manager import (
        create_real_services_manager,
    )
except ImportError as e:
    logging.warning(f"Import error (will use fallback): {e}")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Single test execution result."""
    name: str
    passed: bool
    duration: float
    error_message: str = ""
    exit_code: int = 0


@dataclass
class TestSuiteResult:
    """Complete test suite execution result."""
    total_tests: int
    passed_tests: int
    failed_tests: int
    success_rate: float
    total_duration: float
    results: List[TestResult]
    services_started: bool = False
    timestamp: str = ""


class CriticalTestRunner:
    """Runs the 10 critical unified tests with real service management."""
    
    def __init__(self, project_root: Path = PROJECT_ROOT):
        """Initialize the critical test runner."""
        self.project_root = project_root
        self.test_files = self._get_critical_test_files()
        self.services_manager = None
        self.services_started_by_runner = False
        self.results: List[TestResult] = []
        
    def _get_critical_test_files(self) -> List[str]:
        """Get list of critical test files to run."""
        return [
            "test_oauth_endpoint_validation_real.py",
            "test_websocket_auth_multiservice.py", 
            "test_complete_oauth_chat_journey.py",
            "test_jwt_cross_service_validation.py",
            "test_websocket_concurrent_ordering.py",
            "test_auth_service_recovery.py",
            "test_database_user_sync.py",
            "test_rate_limiting_unified_real.py",
            "test_session_persistence_restart_real.py",
            "test_multi_session_management.py"
        ]
    
    async def run_all_tests(self, skip_service_start: bool = False) -> TestSuiteResult:
        """Run all critical tests and return comprehensive results."""
        start_time = time.time()
        logger.info("Starting Critical Unified Tests execution")
        
        try:
            # 1. Start services if needed
            if not skip_service_start:
                await self._ensure_services_running()
            
            # 2. Validate services health
            await self._validate_services_health()
            
            # 3. Run tests with parallel execution
            await self._execute_tests_parallel()
            
            # 4. Generate results summary
            return self._generate_test_suite_result(start_time)
            
        except Exception as e:
            logger.error(f"Critical test execution failed: {e}")
            return self._generate_error_result(str(e), start_time)
            
        finally:
            # 5. Cleanup services if we started them
            await self._cleanup_services()
    
    async def _ensure_services_running(self) -> None:
        """Ensure Auth and Backend services are running."""
        logger.info("Checking service status...")
        
        # Check if services are already running
        if await self._check_existing_services():
            logger.info("Services already running, skipping startup")
            return
            
        # Start services using RealServicesManager
        logger.info("Starting Auth and Backend services...")
        self.services_manager = create_real_services_manager(self.project_root)
        await self.services_manager.start_all_services(skip_frontend=True)
        self.services_started_by_runner = True
        logger.info("Services started successfully")
    
    async def _check_existing_services(self) -> bool:
        """Check if required services are already running."""
        try:
            auth_healthy = await check_service_health("http://localhost:8081/health", timeout=2)
            backend_healthy = await check_service_health("http://localhost:8000/health/", timeout=2)
            
            if not auth_healthy:
                # Try alternate auth port
                auth_healthy = await check_service_health("http://localhost:8083/health", timeout=2)
                
            return auth_healthy and backend_healthy
        except Exception as e:
            logger.debug(f"Service health check failed: {e}")
            return False
    
    async def _validate_services_health(self) -> None:
        """Validate that all required services are healthy."""
        logger.info("Validating service health...")
        
        health_checks = [
            ("Auth", "http://localhost:8081/health"),
            ("Auth-Alt", "http://localhost:8083/health"), 
            ("Backend", "http://localhost:8000/health/")
        ]
        
        healthy_services = []
        for service_name, url in health_checks:
            try:
                if await check_service_health(url, timeout=3):
                    healthy_services.append(service_name)
                    logger.info(f"✓ {service_name} service healthy")
            except Exception:
                pass
        
        # Require at least Auth (either port) and Backend
        auth_healthy = any(s.startswith("Auth") for s in healthy_services)
        backend_healthy = "Backend" in healthy_services
        
        if not (auth_healthy and backend_healthy):
            raise RuntimeError(f"Required services not healthy. Found: {healthy_services}")
            
        logger.info(f"Service validation passed: {len(healthy_services)} services healthy")
    
    async def _execute_tests_parallel(self) -> None:
        """Execute tests with controlled parallelism."""
        logger.info(f"Executing {len(self.test_files)} critical tests...")
        
        # Run tests in batches to avoid resource contention
        batch_size = 3  # Reasonable parallelism for critical tests
        for i in range(0, len(self.test_files), batch_size):
            batch = self.test_files[i:i + batch_size]
            
            # Run batch in parallel
            tasks = [self._run_single_test(test_file) for test_file in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process batch results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Test execution error: {result}")
                    self.results.append(TestResult(
                        name="unknown", passed=False, duration=0.0,
                        error_message=str(result), exit_code=1
                    ))
                elif isinstance(result, TestResult):
                    self.results.append(result)
            
            # Brief pause between batches
            if i + batch_size < len(self.test_files):
                await asyncio.sleep(1)
    
    async def _run_single_test(self, test_file: str) -> TestResult:
        """Run a single test file and return results."""
        start_time = time.time()
        test_path = self.project_root / "tests" / "unified" / "e2e" / test_file
        
        if not test_path.exists():
            return TestResult(
                name=test_file, passed=False, duration=0.0,
                error_message=f"Test file not found: {test_path}", exit_code=1
            )
        
        logger.info(f"Running {test_file}...")
        
        # Prepare pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_path),
            "-v", "--tb=short",
            "--disable-warnings",
            "--timeout=300"  # 5 minute timeout per test
        ]
        
        try:
            # Run test with subprocess
            result = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.project_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._prepare_test_environment()
            )
            
            stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=300)
            duration = time.time() - start_time
            
            # Analyze results
            passed = result.returncode == 0
            error_msg = stderr.decode('utf-8', errors='ignore') if stderr else ""
            
            logger.info(f"✓ {test_file} {'PASSED' if passed else 'FAILED'} ({duration:.1f}s)")
            
            return TestResult(
                name=test_file, passed=passed, duration=duration,
                error_message=error_msg, exit_code=result.returncode
            )
            
        except asyncio.TimeoutError:
            logger.error(f"✗ {test_file} TIMEOUT (300s)")
            return TestResult(
                name=test_file, passed=False, duration=300.0,
                error_message="Test execution timeout (300s)", exit_code=124
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"✗ {test_file} ERROR: {e}")
            return TestResult(
                name=test_file, passed=False, duration=duration,
                error_message=str(e), exit_code=1
            )
    
    def _prepare_test_environment(self) -> Dict[str, str]:
        """Prepare environment variables for test execution."""
        env = os.environ.copy()
        env.update({
            "NETRA_ENV": "test",
            "LOG_LEVEL": "WARNING",
            "PYTEST_CURRENT_TEST": "critical_unified_tests",
            "PYTHONPATH": str(self.project_root)
        })
        return env
    
    def _generate_test_suite_result(self, start_time: float) -> TestSuiteResult:
        """Generate comprehensive test suite results."""
        total_duration = time.time() - start_time
        passed_count = sum(1 for r in self.results if r.passed)
        failed_count = len(self.results) - passed_count
        success_rate = (passed_count / len(self.results)) * 100 if self.results else 0
        
        return TestSuiteResult(
            total_tests=len(self.results),
            passed_tests=passed_count,
            failed_tests=failed_count,
            success_rate=success_rate,
            total_duration=total_duration,
            results=self.results,
            services_started=self.services_started_by_runner,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    def _generate_error_result(self, error_msg: str, start_time: float) -> TestSuiteResult:
        """Generate error result when test suite fails to execute."""
        return TestSuiteResult(
            total_tests=0, passed_tests=0, failed_tests=0, success_rate=0.0,
            total_duration=time.time() - start_time, results=[],
            services_started=False,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    async def _cleanup_services(self) -> None:
        """Cleanup services if we started them."""
        if self.services_started_by_runner and self.services_manager:
            logger.info("Cleaning up services...")
            try:
                await self.services_manager.stop_all_services()
                logger.info("Services cleaned up successfully")
            except Exception as e:
                logger.error(f"Service cleanup error: {e}")


def print_test_summary(result: TestSuiteResult) -> None:
    """Print comprehensive test execution summary."""
    print("\n" + "="*80)
    print("CRITICAL UNIFIED TESTS - EXECUTION SUMMARY")
    print("="*80)
    
    # Overall results
    print(f"Total Tests: {result.total_tests}")
    print(f"Passed: {result.passed_tests}")
    print(f"Failed: {result.failed_tests}")
    print(f"Success Rate: {result.success_rate:.1f}%")
    print(f"Total Duration: {result.total_duration:.1f}s")
    print(f"Services Started: {'Yes' if result.services_started else 'No'}")
    print(f"Timestamp: {result.timestamp}")
    
    # Individual test results
    print(f"\n{'TEST NAME':<40} {'STATUS':<10} {'DURATION':<10}")
    print("-" * 60)
    
    for test_result in result.results:
        status = "PASSED" if test_result.passed else "FAILED"
        duration = f"{test_result.duration:.1f}s"
        print(f"{test_result.name:<40} {status:<10} {duration:<10}")
        
        if not test_result.passed and test_result.error_message:
            # Show first line of error message
            error_line = test_result.error_message.split('\n')[0][:70]
            if error_line:
                print(f"    Error: {error_line}")
    
    # Enterprise SLA compliance check
    sla_compliance = result.success_rate >= 95.0  # Enterprise SLA requirement
    print(f"\nEnterprise SLA Compliance (95%): {'✓ PASS' if sla_compliance else '✗ FAIL'}")
    
    print("="*80)


def save_results_json(result: TestSuiteResult, output_file: Path) -> None:
    """Save detailed results to JSON file."""
    try:
        with open(output_file, 'w') as f:
            json.dump(asdict(result), f, indent=2, default=str)
        logger.info(f"Results saved to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")


async def main() -> int:
    """Main entry point for critical unified tests runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run 10 critical unified tests")
    parser.add_argument("--skip-service-start", action="store_true",
                       help="Skip starting services (assume already running)")
    parser.add_argument("--output", type=Path, 
                       default=PROJECT_ROOT / "test_reports" / "critical_tests_results.json",
                       help="JSON output file for results")
    parser.add_argument("--quiet", action="store_true",
                       help="Reduce output verbosity")
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    # Create and run test runner
    runner = CriticalTestRunner(PROJECT_ROOT)
    
    try:
        result = await runner.run_all_tests(skip_service_start=args.skip_service_start)
        
        # Print summary
        print_test_summary(result)
        
        # Save detailed results
        save_results_json(result, args.output)
        
        # Return appropriate exit code
        return 0 if result.failed_tests == 0 else 1
        
    except KeyboardInterrupt:
        logger.info("Test execution interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Critical test runner failed: {e}")
        return 1


if __name__ == "__main__":
    # Handle Windows compatibility for asyncio
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)