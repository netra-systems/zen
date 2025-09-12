"""
Unified test orchestrator for Cloud Run testing.

Coordinates test execution across different environments and manages the test lifecycle.
"""

import asyncio
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

import yaml

from test_framework.archived.duplicates.docker_testing.compose_manager import DockerComposeManager
from test_framework.archived.duplicates.gcp_integration.log_reader import GCPLogReader
from test_framework.archived.duplicates.staging_testing.endpoint_validator import StagingEndpointValidator
from test_framework.archived.duplicates.unified.base_interfaces import (
    BaseTestComponent,
    IContainerManager,
    IDeploymentValidator,
    IHealthMonitor,
    ITestExecutor,
    ITestOrchestrator,
    ITestReporter,
    ServiceConfig,
    TestEnvironment,
    TestHook,
    TestLevel,
    TestResult,
)


@dataclass
class TestSuite:
    """Represents a test suite."""
    name: str
    level: TestLevel
    environment: TestEnvironment
    tests: List[Dict[str, Any]]
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None
    parallel: bool = False
    timeout_seconds: int = 300
    retry_count: int = 1
    required_services: List[str] = field(default_factory=list)


@dataclass
class OrchestratorConfig:
    """Configuration for the test orchestrator."""
    project_root: Path
    config_dir: Path
    report_dir: Path
    parallel_workers: int = 4
    default_timeout: int = 300
    fail_fast: bool = False
    verbose: bool = False
    dry_run: bool = False
    hooks: List[TestHook] = field(default_factory=list)


class UnifiedTestOrchestrator(BaseTestComponent, ITestOrchestrator[TestSuite]):
    """Orchestrates test execution across environments."""
    
    def __init__(self, config: OrchestratorConfig):
        super().__init__(config.__dict__)
        self.config = config
        self._test_registry: Dict[str, TestSuite] = {}
        self._executors: Dict[TestEnvironment, ITestExecutor] = {}
        self._monitors: Dict[TestEnvironment, IHealthMonitor] = {}
        self._validators: Dict[TestEnvironment, IDeploymentValidator] = {}
        self._container_manager: Optional[IContainerManager] = None
        self._reporter: Optional[ITestReporter] = None
        self._executor_pool: Optional[ThreadPoolExecutor] = None
        self._test_history: List[TestResult] = []
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the orchestrator."""
        await super().initialize()
        
        # Update config if provided
        if config:
            for key, value in config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
        
        # Initialize executor pool
        self._executor_pool = ThreadPoolExecutor(max_workers=self.config.parallel_workers)
        
        # Load test suites
        await self._load_test_suites()
        
        # Initialize components based on environments
        await self._initialize_components()
    
    async def cleanup(self) -> None:
        """Clean up orchestrator resources."""
        # Clean up all executors
        for executor in self._executors.values():
            if hasattr(executor, 'cleanup'):
                await executor.cleanup()
        
        # Clean up container manager
        if self._container_manager:
            await self._container_manager.cleanup()
        
        # Shutdown executor pool
        if self._executor_pool:
            self._executor_pool.shutdown(wait=True)
        
        await super().cleanup()
    
    async def run_test_suite(
        self,
        test_level: TestLevel,
        environment: TestEnvironment
    ) -> List[TestResult]:
        """Run a complete test suite."""
        self.validate_initialized()
        
        # Find matching test suites
        matching_suites = [
            suite for suite in self._test_registry.values()
            if suite.level == test_level and suite.environment == environment
        ]
        
        if not matching_suites:
            raise ValueError(
                f"No test suites found for level={test_level}, environment={environment}"
            )
        
        all_results = []
        
        for suite in matching_suites:
            print(f"\n{'='*60}")
            print(f"Running test suite: {suite.name}")
            print(f"Level: {suite.level.value}, Environment: {suite.environment.value}")
            print(f"Tests: {len(suite.tests)}, Parallel: {suite.parallel}")
            print(f"{'='*60}\n")
            
            # Run pre-suite hooks
            for hook in self.config.hooks:
                await hook.before_test(suite.name, {"suite": suite})
            
            # Setup phase
            if suite.setup and not self.config.dry_run:
                await suite.setup()
            
            # Ensure required services are running
            if environment == TestEnvironment.DOCKER:
                await self._ensure_docker_services(suite.required_services)
            
            # Run tests
            if suite.parallel and len(suite.tests) > 1:
                results = await self._run_tests_parallel(suite)
            else:
                results = await self._run_tests_sequential(suite)
            
            all_results.extend(results)
            
            # Teardown phase
            if suite.teardown and not self.config.dry_run:
                await suite.teardown()
            
            # Run post-suite hooks
            for hook in self.config.hooks:
                for result in results:
                    await hook.after_test(suite.name, result)
            
            # Check fail-fast
            if self.config.fail_fast and any(not r.status for r in results):
                print(f"\n FAIL:  Fail-fast triggered. Stopping test execution.")
                break
        
        # Update history
        self._test_history.extend(all_results)
        
        # Generate report
        if self._reporter:
            report = await self.generate_report(all_results)
            await self._save_report(report)
        
        return all_results
    
    async def run_single_test(
        self,
        test_name: str,
        test_config: TestSuite
    ) -> TestResult:
        """Run a single test."""
        self.validate_initialized()
        
        # Find the test
        test = next(
            (t for t in test_config.tests if t.get('name') == test_name),
            None
        )
        
        if not test:
            raise ValueError(f"Test '{test_name}' not found in suite")
        
        # Get appropriate executor
        executor = self._executors.get(test_config.environment)
        if not executor:
            raise ValueError(
                f"No executor available for environment {test_config.environment}"
            )
        
        # Run pre-test hooks
        for hook in self.config.hooks:
            await hook.before_test(test_name, test)
        
        start_time = datetime.now(timezone.utc)
        
        try:
            if self.config.dry_run:
                # Dry run - just return success
                result = TestResult(
                    test_name=test_name,
                    level=test_config.level,
                    environment=test_config.environment,
                    status=True,
                    duration_ms=0,
                    metadata={"dry_run": True}
                )
            else:
                # Execute the test
                result = await asyncio.wait_for(
                    executor.execute(test),
                    timeout=test.get('timeout', test_config.timeout_seconds)
                )
        except asyncio.TimeoutError:
            result = TestResult(
                test_name=test_name,
                level=test_config.level,
                environment=test_config.environment,
                status=False,
                duration_ms=(datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
                error_message="Test timeout"
            )
        except Exception as e:
            result = TestResult(
                test_name=test_name,
                level=test_config.level,
                environment=test_config.environment,
                status=False,
                duration_ms=(datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
                error_message=str(e)
            )
            
            # Run failure hooks
            for hook in self.config.hooks:
                await hook.on_failure(test_name, e)
        
        # Run post-test hooks
        for hook in self.config.hooks:
            await hook.after_test(test_name, result)
        
        return result
    
    async def generate_report(
        self,
        results: List[TestResult]
    ) -> Dict[str, Any]:
        """Generate a test report from results."""
        self.validate_initialized()
        
        # Group results by various dimensions
        by_level = defaultdict(list)
        by_environment = defaultdict(list)
        by_status = defaultdict(list)
        
        for result in results:
            by_level[result.level.value].append(result)
            by_environment[result.environment.value].append(result)
            by_status["passed" if result.status else "failed"].append(result)
        
        # Calculate statistics
        total_tests = len(results)
        passed_tests = len(by_status["passed"])
        failed_tests = len(by_status["failed"])
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        total_duration = sum(r.duration_ms for r in results)
        avg_duration = total_duration / total_tests if total_tests > 0 else 0
        
        # Find slowest tests
        slowest_tests = sorted(results, key=lambda r: r.duration_ms, reverse=True)[:5]
        
        # Find failed tests
        failed_test_details = [
            {
                "name": r.test_name,
                "error": r.error_message,
                "duration_ms": r.duration_ms
            }
            for r in by_status["failed"]
        ]
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "pass_rate": f"{pass_rate:.2f}%",
                "total_duration_ms": total_duration,
                "avg_duration_ms": avg_duration,
                "execution_time": datetime.now(timezone.utc).isoformat()
            },
            "by_level": {
                level: {
                    "total": len(tests),
                    "passed": len([t for t in tests if t.status]),
                    "failed": len([t for t in tests if not t.status])
                }
                for level, tests in by_level.items()
            },
            "by_environment": {
                env: {
                    "total": len(tests),
                    "passed": len([t for t in tests if t.status]),
                    "failed": len([t for t in tests if not t.status])
                }
                for env, tests in by_environment.items()
            },
            "slowest_tests": [
                {
                    "name": t.test_name,
                    "duration_ms": t.duration_ms,
                    "level": t.level.value,
                    "environment": t.environment.value
                }
                for t in slowest_tests
            ],
            "failed_tests": failed_test_details,
            "configuration": {
                "parallel_workers": self.config.parallel_workers,
                "fail_fast": self.config.fail_fast,
                "dry_run": self.config.dry_run
            }
        }
        
        return report
    
    def get_test_registry(self) -> Dict[str, TestSuite]:
        """Get registry of available tests."""
        return self._test_registry.copy()
    
    async def run_health_checks(
        self,
        environment: TestEnvironment,
        service_configs: List[ServiceConfig]
    ) -> Dict[str, Any]:
        """Run health checks for services."""
        self.validate_initialized()
        
        monitor = self._monitors.get(environment)
        if not monitor:
            raise ValueError(f"No health monitor for environment {environment}")
        
        results = []
        for config in service_configs:
            result = await monitor.check_health(config)
            results.append(result)
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": environment.value,
            "services": [
                {
                    "name": r.service_name,
                    "status": r.status.value,
                    "response_time_ms": r.response_time_ms,
                    "error": r.error_message
                }
                for r in results
            ],
            "summary": {
                "total": len(results),
                "healthy": len([r for r in results if r.status.value == "healthy"]),
                "unhealthy": len([r for r in results if r.status.value == "unhealthy"]),
                "degraded": len([r for r in results if r.status.value == "degraded"])
            }
        }
    
    async def validate_deployment(
        self,
        environment: TestEnvironment,
        service_configs: List[ServiceConfig]
    ) -> Dict[str, Any]:
        """Validate deployment for an environment."""
        self.validate_initialized()
        
        validator = self._validators.get(environment)
        if not validator:
            raise ValueError(f"No deployment validator for environment {environment}")
        
        deployment_status = await validator.validate_deployment(service_configs)
        dependency_issues = await validator.validate_dependencies(service_configs)
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": environment.value,
            "deployment_status": deployment_status,
            "dependency_issues": dependency_issues,
            "all_deployed": all(deployment_status.values()),
            "has_dependency_issues": len(dependency_issues) > 0
        }
    
    async def _load_test_suites(self) -> None:
        """Load test suite configurations."""
        config_dir = self.config.config_dir
        
        # Load test suite definitions
        for config_file in config_dir.glob("test_suites/*.yaml"):
            with open(config_file, 'r') as f:
                suite_config = yaml.safe_load(f)
            
            for suite_data in suite_config.get('suites', []):
                suite = TestSuite(
                    name=suite_data['name'],
                    level=TestLevel[suite_data['level'].upper()],
                    environment=TestEnvironment[suite_data['environment'].upper()],
                    tests=suite_data.get('tests', []),
                    parallel=suite_data.get('parallel', False),
                    timeout_seconds=suite_data.get('timeout', 300),
                    retry_count=suite_data.get('retry_count', 1),
                    required_services=suite_data.get('required_services', [])
                )
                
                self._test_registry[suite.name] = suite
    
    async def _initialize_components(self) -> None:
        """Initialize test components based on configuration."""
        # Initialize Docker components if needed
        if TestEnvironment.DOCKER in [s.environment for s in self._test_registry.values()]:
            compose_file = self.config.project_root / "docker-compose.test.yml"
            if compose_file.exists():
                self._container_manager = DockerComposeManager(str(compose_file))
                await self._container_manager.initialize()
        
        # Initialize staging components if needed
        if TestEnvironment.STAGING in [s.environment for s in self._test_registry.values()]:
            staging_config_file = self.config.config_dir / "staging.yaml"
            if staging_config_file.exists():
                with open(staging_config_file, 'r') as f:
                    staging_config = yaml.safe_load(f)
                
                validator = StagingEndpointValidator(staging_config)
                await validator.initialize()
                self._validators[TestEnvironment.STAGING] = validator
    
    async def _ensure_docker_services(self, services: List[str]) -> None:
        """Ensure Docker services are running."""
        if not self._container_manager:
            return
        
        # Start required services
        if services:
            await self._container_manager.start_containers(services)
            
            # Wait for services to be healthy
            if not await self._container_manager.wait_for_healthy(timeout_seconds=120):
                raise RuntimeError("Docker services failed to become healthy")
    
    async def _run_tests_parallel(self, suite: TestSuite) -> List[TestResult]:
        """Run tests in parallel."""
        tasks = []
        
        for test in suite.tests:
            task = asyncio.create_task(
                self._run_test_with_retry(test, suite)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(TestResult(
                    test_name=suite.tests[i].get('name', f'test_{i}'),
                    level=suite.level,
                    environment=suite.environment,
                    status=False,
                    duration_ms=0,
                    error_message=str(result)
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def _run_tests_sequential(self, suite: TestSuite) -> List[TestResult]:
        """Run tests sequentially."""
        results = []
        
        for test in suite.tests:
            result = await self._run_test_with_retry(test, suite)
            results.append(result)
            
            # Check fail-fast
            if self.config.fail_fast and not result.status:
                break
        
        return results
    
    async def _run_test_with_retry(
        self,
        test: Dict[str, Any],
        suite: TestSuite
    ) -> TestResult:
        """Run a test with retry logic."""
        last_result = None
        
        for attempt in range(suite.retry_count):
            if attempt > 0:
                print(f"  Retry {attempt}/{suite.retry_count - 1} for {test.get('name')}")
            
            result = await self.run_single_test(
                test.get('name', 'unnamed_test'),
                suite
            )
            
            last_result = result
            
            if result.status:
                break
            
            # Wait before retry
            if attempt < suite.retry_count - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return last_result
    
    async def _save_report(self, report: Dict[str, Any]) -> None:
        """Save test report to file."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_file = self.config.report_dir / f"test_report_{timestamp}.json"
        
        # Ensure report directory exists
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save report
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n CHART:  Test report saved to: {report_file}")
        
        # Also save latest report
        latest_file = self.config.report_dir / "latest_report.json"
        with open(latest_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)