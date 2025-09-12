"""
Analytics Service Integration Test Runner
========================================

Comprehensive test runner for Analytics Service integration tests.
Orchestrates test execution, environment setup, and result reporting.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity and System Reliability
- Value Impact: Ensures analytics service works correctly before deployment
- Strategic Impact: Prevents production failures that would impact customer analytics

Usage:
    python run_integration_tests.py --help
    python run_integration_tests.py --suite database
    python run_integration_tests.py --suite all --parallel --report
    python run_integration_tests.py --config custom_config.json --environment ci
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import subprocess

# Add project root to path for imports
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework import setup_test_path

# CRITICAL: setup_test_path() MUST be called before any project imports per CLAUDE.md
setup_test_path()

from analytics_service.tests.integration.integration_config import (
    get_integration_test_config,
    create_test_config_for_environment,
    IntegrationTestConfig,
)
from shared.isolated_environment import get_env


class IntegrationTestSuite:
    """Represents a test suite that can be executed."""
    
    def __init__(
        self,
        name: str,
        test_files: List[str],
        description: str,
        dependencies: Optional[List[str]] = None,
        timeout_minutes: int = 30,
    ):
        self.name = name
        self.test_files = test_files
        self.description = description
        self.dependencies = dependencies or []
        self.timeout_minutes = timeout_minutes


class IntegrationTestRunner:
    """Main integration test runner for Analytics Service."""
    
    def __init__(self, config: IntegrationTestConfig):
        """Initialize test runner with configuration."""
        self.config = config
        self.results = {}
        self.start_time = None
        self.end_time = None
        
        # Define available test suites
        self.test_suites = {
            "database": IntegrationTestSuite(
                name="database",
                test_files=["test_database_integration.py"],
                description="Database connectivity and operations integration tests",
                dependencies=["clickhouse", "redis"],
                timeout_minutes=15,
            ),
            "service": IntegrationTestSuite(
                name="service",
                test_files=["test_service_integration.py"],
                description="Cross-service communication integration tests",
                dependencies=["backend-service", "auth-service"],
                timeout_minutes=20,
            ),
            "pipeline": IntegrationTestSuite(
                name="pipeline",
                test_files=["test_event_pipeline.py"],
                description="Event processing pipeline integration tests",
                dependencies=["clickhouse", "redis"],
                timeout_minutes=25,
            ),
            "api": IntegrationTestSuite(
                name="api",
                test_files=["test_api_integration.py"],
                description="REST API integration tests",
                dependencies=["analytics-service"],
                timeout_minutes=20,
            ),
            "all": IntegrationTestSuite(
                name="all",
                test_files=[
                    "test_database_integration.py",
                    "test_service_integration.py", 
                    "test_event_pipeline.py",
                    "test_api_integration.py",
                ],
                description="Complete integration test suite",
                dependencies=["clickhouse", "redis", "analytics-service"],
                timeout_minutes=60,
            ),
        }
    
    async def run_test_suite(
        self,
        suite_name: str,
        parallel: bool = False,
        verbose: bool = False,
        fail_fast: bool = False,
    ) -> Dict[str, Any]:
        """Run a specific test suite and return results."""
        if suite_name not in self.test_suites:
            raise ValueError(f"Unknown test suite: {suite_name}")
        
        suite = self.test_suites[suite_name]
        print(f"\nRunning {suite.name} integration tests: {suite.description}")
        
        # Check dependencies
        dependency_check = await self._check_dependencies(suite.dependencies)
        if not dependency_check["all_available"]:
            print(f"WARNING: Dependencies not available: {dependency_check['missing']}")
            print("Some tests may be skipped or fail")
        
        # Setup test environment
        await self._setup_test_environment()
        
        # Run tests
        suite_results = await self._execute_test_files(
            suite.test_files,
            parallel=parallel,
            verbose=verbose,
            fail_fast=fail_fast,
            timeout_minutes=suite.timeout_minutes,
        )
        
        # Cleanup test environment
        await self._cleanup_test_environment()
        
        return suite_results
    
    async def _check_dependencies(self, dependencies: List[str]) -> Dict[str, Any]:
        """Check if required dependencies are available."""
        results = {
            "all_available": True,
            "available": [],
            "missing": [],
            "details": {},
        }
        
        for dep in dependencies:
            is_available = await self._check_dependency(dep)
            results["details"][dep] = is_available
            
            if is_available:
                results["available"].append(dep)
            else:
                results["missing"].append(dep)
                results["all_available"] = False
        
        return results
    
    async def _check_dependency(self, dependency: str) -> bool:
        """Check if a specific dependency is available."""
        import httpx
        
        # Map dependencies to check methods
        checks = {
            "clickhouse": ("tcp", self.config.database.clickhouse_host, self.config.database.clickhouse_port),
            "redis": ("tcp", self.config.database.redis_host, self.config.database.redis_port),
            "analytics-service": ("http", self.config.service.analytics_service_url, "/health"),
            "backend-service": ("http", self.config.service.backend_service_url, "/health"),
            "auth-service": ("http", self.config.service.auth_service_url, "/health"),
        }
        
        if dependency not in checks:
            print(f"Unknown dependency: {dependency}")
            return False
        
        check_type, host_or_url, port_or_path = checks[dependency]
        
        try:
            if check_type == "tcp":
                # TCP connection check
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host_or_url, port_or_path))
                sock.close()
                return result == 0
                
            elif check_type == "http":
                # HTTP service check
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{host_or_url}{port_or_path}")
                    return response.status_code in [200, 404]  # 404 is OK if service is running
                    
        except Exception as e:
            print(f"Dependency check failed for {dependency}: {e}")
            return False
        
        return False
    
    async def _setup_test_environment(self) -> None:
        """Setup test environment before running tests."""
        env = get_env()
        env.enable_isolation()
        
        # Set test environment variables
        env.set("ENVIRONMENT", "test", "integration_test_runner")
        env.set("LOG_LEVEL", self.config.log_level, "integration_test_runner")
        env.set("PYTEST_CURRENT_TEST", "integration_tests", "integration_test_runner")
        
        # Database configuration
        env.set("CLICKHOUSE_HOST", self.config.database.clickhouse_host, "integration_test_runner")
        env.set("CLICKHOUSE_PORT", str(self.config.database.clickhouse_port), "integration_test_runner")
        env.set("CLICKHOUSE_DATABASE", self.config.database.clickhouse_database, "integration_test_runner")
        env.set("REDIS_HOST", self.config.database.redis_host, "integration_test_runner")
        env.set("REDIS_PORT", str(self.config.database.redis_port), "integration_test_runner")
        env.set("REDIS_ANALYTICS_DB", str(self.config.database.redis_db), "integration_test_runner")
        
        # Service configuration
        env.set("ANALYTICS_SERVICE_URL", self.config.service.analytics_service_url, "integration_test_runner")
        env.set("ANALYTICS_API_KEY", self.config.service.analytics_api_key, "integration_test_runner")
        
        print("SUCCESS: Test environment configured")
    
    async def _cleanup_test_environment(self) -> None:
        """Cleanup test environment after running tests."""
        if self.config.cleanup_test_resources:
            try:
                # Clean up test databases
                await self._cleanup_test_databases()
                print("SUCCESS: Test environment cleaned up")
            except Exception as e:
                print(f"WARNING: Test cleanup failed: {e}")
        else:
            print("INFO: Test cleanup skipped (disabled in config)")
    
    async def _cleanup_test_databases(self) -> None:
        """Clean up test data from databases."""
        try:
            # ClickHouse cleanup
            from analytics_service.analytics_core.database.clickhouse_manager import ClickHouseManager
            
            ch_manager = ClickHouseManager(
                host=self.config.database.clickhouse_host,
                port=self.config.database.clickhouse_port,
                database=self.config.database.clickhouse_database,
                user=self.config.database.clickhouse_username,
                password=self.config.database.clickhouse_password,
            )
            
            await ch_manager.connect()
            
            # Clean test tables
            test_tables = ["frontend_events", "prompt_analytics"]
            for table in test_tables:
                await ch_manager.execute_command(f"TRUNCATE TABLE IF EXISTS {table}")
            
            await ch_manager.disconnect()
            
        except Exception as e:
            print(f"ClickHouse cleanup failed: {e}")
        
        try:
            # Redis cleanup
            from analytics_service.analytics_core.database.redis_manager import RedisManager
            
            redis_manager = RedisManager(
                host=self.config.database.redis_host,
                port=self.config.database.redis_port,
                db=self.config.database.redis_db,
                password=self.config.database.redis_password,
            )
            
            await redis_manager.connect()
            await redis_manager.flushdb()  # Clear test database
            await redis_manager.disconnect()
            
        except Exception as e:
            print(f"Redis cleanup failed: {e}")
    
    async def _execute_test_files(
        self,
        test_files: List[str],
        parallel: bool = False,
        verbose: bool = False,
        fail_fast: bool = False,
        timeout_minutes: int = 30,
    ) -> Dict[str, Any]:
        """Execute test files using pytest."""
        results = {
            "total_files": len(test_files),
            "passed_files": 0,
            "failed_files": 0,
            "skipped_files": 0,
            "file_results": {},
            "total_duration_seconds": 0,
        }
        
        start_time = time.time()
        
        if parallel and len(test_files) > 1:
            # Run tests in parallel
            tasks = []
            for test_file in test_files:
                task = self._run_single_test_file(test_file, verbose, timeout_minutes)
                tasks.append(task)
            
            file_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(file_results):
                test_file = test_files[i]
                if isinstance(result, Exception):
                    results["file_results"][test_file] = {
                        "status": "error",
                        "error": str(result),
                        "duration_seconds": 0,
                    }
                    results["failed_files"] += 1
                else:
                    results["file_results"][test_file] = result
                    if result["status"] == "passed":
                        results["passed_files"] += 1
                    elif result["status"] == "failed":
                        results["failed_files"] += 1
                    else:
                        results["skipped_files"] += 1
        else:
            # Run tests sequentially
            for test_file in test_files:
                result = await self._run_single_test_file(test_file, verbose, timeout_minutes)
                results["file_results"][test_file] = result
                
                if result["status"] == "passed":
                    results["passed_files"] += 1
                elif result["status"] == "failed":
                    results["failed_files"] += 1
                    if fail_fast:
                        print(f" FAIL:  Failing fast due to failure in {test_file}")
                        break
                else:
                    results["skipped_files"] += 1
        
        results["total_duration_seconds"] = time.time() - start_time
        
        return results
    
    async def _run_single_test_file(
        self,
        test_file: str,
        verbose: bool = False,
        timeout_minutes: int = 30,
    ) -> Dict[str, Any]:
        """Run a single test file using pytest."""
        test_path = Path(__file__).parent / test_file
        
        if not test_path.exists():
            return {
                "status": "error",
                "error": f"Test file not found: {test_path}",
                "duration_seconds": 0,
            }
        
        # Build pytest command
        cmd = ["python", "-m", "pytest", str(test_path)]
        
        if verbose:
            cmd.extend(["-v", "-s"])
        else:
            cmd.append("-q")
        
        # Add output format
        cmd.extend(["--tb=short", "--no-header"])
        
        print(f"Running {test_file}...")
        
        start_time = time.time()
        
        try:
            # Run pytest with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(__file__).parent.parent.parent,  # analytics_service root
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_minutes * 60
            )
            
            duration = time.time() - start_time
            
            # Parse pytest results
            stdout_str = stdout.decode() if stdout else ""
            stderr_str = stderr.decode() if stderr else ""
            
            if process.returncode == 0:
                status = "passed"
                print(f"SUCCESS: {test_file} passed ({duration:.1f}s)")
            elif "SKIPPED" in stdout_str or "skipped" in stdout_str:
                status = "skipped"
                print(f"SKIPPED: {test_file} skipped ({duration:.1f}s)")
            else:
                status = "failed"
                print(f"FAILED: {test_file} failed ({duration:.1f}s)")
                if verbose:
                    print(f"STDOUT:\n{stdout_str}")
                    print(f"STDERR:\n{stderr_str}")
            
            return {
                "status": status,
                "return_code": process.returncode,
                "duration_seconds": duration,
                "stdout": stdout_str,
                "stderr": stderr_str,
            }
            
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "error": f"Test timed out after {timeout_minutes} minutes",
                "duration_seconds": time.time() - start_time,
            }
        except Exception as e:
            return {
                "status": "error", 
                "error": str(e),
                "duration_seconds": time.time() - start_time,
            }
    
    def generate_report(self, results: Dict[str, Any], output_file: Optional[str] = None) -> str:
        """Generate test execution report."""
        report = {
            "test_execution": {
                "started_at": self.start_time.isoformat() if self.start_time else None,
                "completed_at": self.end_time.isoformat() if self.end_time else None,
                "duration_seconds": results.get("total_duration_seconds", 0),
            },
            "configuration": self.config.create_test_environment_summary(),
            "results": results,
            "summary": {
                "total_files": results.get("total_files", 0),
                "passed_files": results.get("passed_files", 0),
                "failed_files": results.get("failed_files", 0),
                "skipped_files": results.get("skipped_files", 0),
                "success_rate": self._calculate_success_rate(results),
            },
        }
        
        report_json = json.dumps(report, indent=2, default=str)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_json)
            print(f"SUCCESS: Test report saved to: {output_file}")
        
        return report_json
    
    def _calculate_success_rate(self, results: Dict[str, Any]) -> float:
        """Calculate test success rate."""
        total = results.get("total_files", 0)
        passed = results.get("passed_files", 0)
        
        if total == 0:
            return 0.0
        
        return passed / total


async def main():
    """Main entry point for integration test runner."""
    parser = argparse.ArgumentParser(description="Analytics Service Integration Test Runner")
    
    parser.add_argument(
        "--suite",
        choices=["database", "service", "pipeline", "api", "all"],
        default="all",
        help="Test suite to run (default: all)",
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel",
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true", 
        help="Verbose test output",
    )
    
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first test failure",
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Configuration file path",
    )
    
    parser.add_argument(
        "--environment",
        choices=["local", "ci", "staging"],
        help="Environment-specific configuration",
    )
    
    parser.add_argument(
        "--report",
        type=str,
        nargs='?',
        const="integration_test_report.json",
        help="Generate test report (optional filename)",
    )
    
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Only check dependencies and exit",
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        if args.environment:
            config = create_test_config_for_environment(args.environment)
        else:
            config = get_integration_test_config(args.config)
        
        # Create test runner
        runner = IntegrationTestRunner(config)
        
        # Check dependencies only
        if args.check_deps:
            print("Checking dependencies...")
            all_deps = set()
            for suite in runner.test_suites.values():
                all_deps.update(suite.dependencies)
            
            dep_results = await runner._check_dependencies(list(all_deps))
            
            print(f"\nDependency Check Results:")
            print(f"Available: {dep_results['available']}")
            print(f"Missing: {dep_results['missing']}")
            
            if dep_results["all_available"]:
                print("SUCCESS: All dependencies are available")
                sys.exit(0)
            else:
                print("WARNING: Some dependencies are missing")
                sys.exit(1)
        
        # Run tests
        print(f"Analytics Service Integration Tests")
        print(f"Environment: {config.environment}")
        print(f"Suite: {args.suite}")
        print(f"Parallel: {args.parallel}")
        
        runner.start_time = datetime.now(timezone.utc)
        
        results = await runner.run_test_suite(
            suite_name=args.suite,
            parallel=args.parallel,
            verbose=args.verbose,
            fail_fast=args.fail_fast,
        )
        
        runner.end_time = datetime.now(timezone.utc)
        
        # Print summary
        print(f"\nTest Results Summary:")
        print(f"Total files: {results['total_files']}")
        print(f"Passed: {results['passed_files']}")
        print(f"Failed: {results['failed_files']}")
        print(f"Skipped: {results['skipped_files']}")
        print(f"Duration: {results['total_duration_seconds']:.1f}s")
        
        success_rate = runner._calculate_success_rate(results)
        print(f"Success Rate: {success_rate:.1%}")
        
        # Generate report
        if args.report:
            report = runner.generate_report(results, args.report)
        
        # Exit with appropriate code
        if results["failed_files"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\nERROR: Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nERROR: Test runner failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())