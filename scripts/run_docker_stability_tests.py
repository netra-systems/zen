#!/usr/bin/env python3
"""
MISSION CRITICAL: Docker Stability Test Suite Orchestrator
BUSINESS IMPACT: PROTECTS $2M+ ARR PLATFORM WITH COMPREHENSIVE DOCKER VALIDATION

This script orchestrates the execution of ALL Docker stability tests with proper
sequencing, resource management, and comprehensive reporting. It ensures that
our Docker infrastructure is bulletproof under all conditions.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Infrastructure Validation & Risk Mitigation
2. Business Goal: Ensure Docker stability prevents development team downtime
3. Value Impact: Validates infrastructure supporting 10+ developers and CI/CD
4. Revenue Impact: Protects $2M+ ARR platform from Docker-related outages

ORCHESTRATION FEATURES:
- Sequential and parallel test execution modes
- Resource cleanup between test suites
- Comprehensive performance metrics collection
- Failure isolation and detailed reporting
- Cross-platform compatibility (Windows/Mac/Linux)
- CI/CD integration support
- Real-time progress monitoring
- Automated baseline establishment
- Emergency stop capabilities
"""

import argparse
import asyncio
import logging
import sys
import os
import time
import threading
import subprocess
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import psutil
import uuid

# Add parent directory to path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# CRITICAL IMPORTS: All Docker infrastructure
from test_framework.docker_force_flag_guardian import (
    DockerForceFlagGuardian,
    DockerForceFlagViolation,
    validate_docker_command
)
from test_framework.docker_rate_limiter import (
    DockerRateLimiter,
    execute_docker_command,
    get_docker_rate_limiter
)
from test_framework.unified_docker_manager import UnifiedDockerManager
from shared.isolated_environment import get_env

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('docker_stability_test_execution.log')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TestSuiteResult:
    """Result of executing a test suite."""
    suite_name: str
    success: bool
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    tests_run: int
    tests_passed: int
    tests_failed: int
    tests_skipped: int
    error_messages: List[str]
    performance_metrics: Dict[str, Any]
    resource_usage: Dict[str, float]


@dataclass
class OverallTestReport:
    """Comprehensive test execution report."""
    execution_id: str
    start_time: datetime
    end_time: datetime
    total_duration_seconds: float
    suite_results: List[TestSuiteResult]
    overall_success: bool
    total_tests_run: int
    total_tests_passed: int
    total_tests_failed: int
    total_tests_skipped: int
    success_rate_percent: float
    system_metrics: Dict[str, Any]
    docker_metrics: Dict[str, Any]


class DockerStabilityTestOrchestrator:
    """Orchestrates comprehensive Docker stability testing."""
    
    def __init__(self, args):
        """Initialize the test orchestrator."""
        self.args = args
        self.execution_id = f"docker_stability_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        self.start_time = datetime.now()
        
        # Test suite configurations
        self.test_suites = {
            'stability': {
                'name': 'Docker Stability Suite',
                'module': 'tests.mission_critical.test_docker_stability_suite',
                'description': 'Comprehensive stability testing with stress scenarios',
                'priority': 1,
                'estimated_duration': 300,  # 5 minutes
                'required_resources': {'cpu': 50, 'memory': 1024}  # MB
            },
            'edge_cases': {
                'name': 'Docker Edge Cases Suite',
                'module': 'tests.mission_critical.test_docker_edge_cases',
                'description': 'Edge case and failure recovery scenarios',
                'priority': 2,
                'estimated_duration': 240,  # 4 minutes
                'required_resources': {'cpu': 40, 'memory': 768}
            },
            'performance': {
                'name': 'Docker Performance Benchmark',
                'module': 'tests.mission_critical.test_docker_performance',
                'description': 'Performance benchmarking and optimization validation',
                'priority': 3,
                'estimated_duration': 360,  # 6 minutes
                'required_resources': {'cpu': 60, 'memory': 1536}
            },
            'integration': {
                'name': 'Docker Full Integration Test',
                'module': 'tests.mission_critical.test_docker_full_integration',
                'description': 'End-to-end integration and multi-service scenarios',
                'priority': 4,
                'estimated_duration': 480,  # 8 minutes
                'required_resources': {'cpu': 70, 'memory': 2048}
            }
        }
        
        # Results tracking
        self.suite_results = []
        self.docker_manager = None
        self.rate_limiter = None
        self.force_guardian = None
        
        # Emergency stop flag
        self.emergency_stop = threading.Event()
        
        logger.info(f"[U+1F527] Docker Stability Test Orchestrator initialized")
        logger.info(f"   Execution ID: {self.execution_id}")
        logger.info(f"   Test Suites: {len(self.test_suites)}")
        
        # Initialize Docker components
        self.initialize_docker_infrastructure()
    
    def initialize_docker_infrastructure(self):
        """Initialize Docker infrastructure components."""
        try:
            self.docker_manager = UnifiedDockerManager()
            self.rate_limiter = get_docker_rate_limiter()
            self.force_guardian = DockerForceFlagGuardian()
            
            # Validate Docker is available
            health_check = self.rate_limiter.health_check()
            if not health_check:
                raise RuntimeError("Docker is not available or not responding")
            
            logger.info(" PASS:  Docker infrastructure initialized and validated")
            
        except Exception as e:
            logger.critical(f" FAIL:  Failed to initialize Docker infrastructure: {e}")
            raise
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': memory.used / (1024**3),
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3),
                'load_avg_1min': load_avg[0],
                'load_avg_5min': load_avg[1],
                'load_avg_15min': load_avg[2],
                'active_processes': len(psutil.pids())
            }
        except Exception as e:
            logger.warning(f"Failed to get system metrics: {e}")
            return {'error': str(e)}
    
    def get_docker_metrics(self) -> Dict[str, Any]:
        """Get Docker-specific metrics."""
        try:
            rate_limiter_stats = self.rate_limiter.get_statistics()
            
            # Get Docker system info
            docker_info = {}
            try:
                result = execute_docker_command(['docker', 'system', 'df', '--format', 'json'])
                if result.returncode == 0:
                    docker_info = json.loads(result.stdout)
            except:
                pass
            
            return {
                'rate_limiter_stats': rate_limiter_stats,
                'docker_system_info': docker_info,
                'force_guardian_status': 'ACTIVE'
            }
        except Exception as e:
            logger.warning(f"Failed to get Docker metrics: {e}")
            return {'error': str(e)}
    
    def check_resource_requirements(self, suite_config: Dict[str, Any]) -> bool:
        """Check if system has sufficient resources for test suite."""
        try:
            system_metrics = self.get_system_metrics()
            
            # Check memory availability
            available_memory_mb = system_metrics.get('memory_available_gb', 0) * 1024
            required_memory = suite_config['required_resources']['memory']
            
            if available_memory_mb < required_memory:
                logger.warning(f" WARNING: [U+FE0F] Insufficient memory: {available_memory_mb:.0f}MB available, {required_memory}MB required")
                return False
            
            # Check CPU availability (if load is too high)
            cpu_percent = system_metrics.get('cpu_percent', 100)
            if cpu_percent > 80:
                logger.warning(f" WARNING: [U+FE0F] High CPU usage: {cpu_percent:.1f}%")
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Resource check failed: {e}")
            return True  # Default to allowing test if check fails
    
    def run_test_suite(self, suite_key: str, suite_config: Dict[str, Any]) -> TestSuiteResult:
        """Run a single test suite with comprehensive monitoring."""
        logger.info(f"[U+1F680] Starting test suite: {suite_config['name']}")
        
        start_time = datetime.now()
        error_messages = []
        performance_metrics = {}
        
        # Get initial system metrics
        initial_metrics = self.get_system_metrics()
        
        try:
            # Check emergency stop
            if self.emergency_stop.is_set():
                raise RuntimeError("Emergency stop activated")
            
            # Check resource requirements
            if not self.check_resource_requirements(suite_config):
                if not self.args.force:
                    raise RuntimeError("Insufficient system resources")
                else:
                    logger.warning(" WARNING: [U+FE0F] Forcing execution despite resource constraints")
            
            # Build pytest command
            pytest_cmd = [
                sys.executable, '-m', 'pytest',
                '-v',  # Verbose output
                '--tb=short',  # Short traceback format
                f"--junit-xml=test_results_{suite_key}_{self.execution_id}.xml",
                suite_config['module']
            ]
            
            # Add additional pytest arguments based on configuration
            if self.args.parallel and suite_key in ['stability', 'edge_cases']:
                pytest_cmd.extend(['-n', 'auto'])  # Run tests in parallel
            
            if self.args.timeout:
                pytest_cmd.extend(['--timeout', str(self.args.timeout)])
            
            if self.args.verbose:
                pytest_cmd.extend(['-s', '--capture=no'])
            
            # Execute test suite
            logger.info(f"   Executing: {' '.join(pytest_cmd)}")
            
            result = subprocess.run(
                pytest_cmd,
                capture_output=True,
                text=True,
                timeout=suite_config['estimated_duration'] * 2,  # 2x estimated time as timeout
                cwd=Path(__file__).parent.parent
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Get final system metrics
            final_metrics = self.get_system_metrics()
            
            # Parse pytest output for test counts
            tests_run = 0
            tests_passed = 0
            tests_failed = 0
            tests_skipped = 0
            
            # Simple parsing of pytest output
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if ' passed' in line or ' failed' in line or ' skipped' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'passed' and i > 0:
                            try:
                                tests_passed = int(parts[i-1])
                            except (ValueError, IndexError):
                                pass
                        elif part == 'failed' and i > 0:
                            try:
                                tests_failed = int(parts[i-1])
                            except (ValueError, IndexError):
                                pass
                        elif part == 'skipped' and i > 0:
                            try:
                                tests_skipped = int(parts[i-1])
                            except (ValueError, IndexError):
                                pass
            
            tests_run = tests_passed + tests_failed + tests_skipped
            
            # Collect error messages from stderr
            if result.stderr:
                error_messages.append(result.stderr[:1000])  # Limit error message length
            
            # Calculate performance metrics
            performance_metrics = {
                'cpu_usage_change': final_metrics.get('cpu_percent', 0) - initial_metrics.get('cpu_percent', 0),
                'memory_usage_change_mb': (final_metrics.get('memory_used_gb', 0) - initial_metrics.get('memory_used_gb', 0)) * 1024,
                'execution_efficiency': tests_run / duration if duration > 0 else 0,
                'estimated_vs_actual': duration / suite_config['estimated_duration'] if suite_config['estimated_duration'] > 0 else 1
            }
            
            # Resource usage summary
            resource_usage = {
                'peak_cpu_percent': max(initial_metrics.get('cpu_percent', 0), final_metrics.get('cpu_percent', 0)),
                'peak_memory_gb': max(initial_metrics.get('memory_used_gb', 0), final_metrics.get('memory_used_gb', 0)),
                'memory_delta_mb': performance_metrics['memory_usage_change_mb']
            }
            
            success = result.returncode == 0 and tests_failed == 0
            
            # Log results
            status = " PASS:  SUCCESS" if success else " FAIL:  FAILED"
            logger.info(f"{status} Test suite: {suite_config['name']}")
            logger.info(f"   Duration: {duration:.1f}s (estimated: {suite_config['estimated_duration']}s)")
            logger.info(f"   Tests: {tests_run} run, {tests_passed} passed, {tests_failed} failed, {tests_skipped} skipped")
            
            if not success and result.stderr:
                logger.error(f"   Errors: {result.stderr[:200]}...")
            
            return TestSuiteResult(
                suite_name=suite_config['name'],
                success=success,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                tests_run=tests_run,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                tests_skipped=tests_skipped,
                error_messages=error_messages,
                performance_metrics=performance_metrics,
                resource_usage=resource_usage
            )
            
        except subprocess.TimeoutExpired:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            error_messages.append(f"Test suite timed out after {duration:.1f}s")
            
            logger.error(f"[U+23F0] Test suite timed out: {suite_config['name']}")
            
            return TestSuiteResult(
                suite_name=suite_config['name'],
                success=False,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                tests_run=0,
                tests_passed=0,
                tests_failed=1,
                tests_skipped=0,
                error_messages=error_messages,
                performance_metrics={'timeout': True},
                resource_usage={}
            )
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            error_messages.append(str(e))
            
            logger.error(f" FAIL:  Test suite failed with exception: {suite_config['name']}: {e}")
            
            return TestSuiteResult(
                suite_name=suite_config['name'],
                success=False,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                tests_run=0,
                tests_passed=0,
                tests_failed=1,
                tests_skipped=0,
                error_messages=error_messages,
                performance_metrics={'exception': str(e)},
                resource_usage={}
            )
    
    def cleanup_between_suites(self):
        """Clean up resources between test suites."""
        logger.info("[U+1F9F9] Cleaning up resources between test suites...")
        
        try:
            # Force garbage collection
            import gc
            gc.collect()
            
            # Wait for Docker operations to settle
            time.sleep(2)
            
            # Check for lingering Docker resources and clean them
            try:
                # Get containers
                result = execute_docker_command(['docker', 'ps', '-a', '--format', '{{.Names}}'])
                if result.returncode == 0:
                    containers = [name.strip() for name in result.stdout.split('\n') if name.strip()]
                    test_containers = [c for c in containers if any(test_prefix in c for test_prefix in 
                                                                  ['stress_test', 'pressure_', 'orphan_', 'perf_test', 'concurrent_'])]
                    
                    if test_containers:
                        logger.info(f"   Cleaning up {len(test_containers)} test containers")
                        for container in test_containers:
                            try:
                                execute_docker_command(['docker', 'container', 'stop', container])
                                execute_docker_command(['docker', 'container', 'rm', container])
                            except:
                                pass
                
                # Get networks
                result = execute_docker_command(['docker', 'network', 'ls', '--format', '{{.Name}}'])
                if result.returncode == 0:
                    networks = [name.strip() for name in result.stdout.split('\n') if name.strip()]
                    test_networks = [n for n in networks if any(test_prefix in n for test_prefix in 
                                                               ['stress_', 'test_', 'orphan_', 'perf_'])]
                    
                    if test_networks:
                        logger.info(f"   Cleaning up {len(test_networks)} test networks")
                        for network in test_networks:
                            try:
                                execute_docker_command(['docker', 'network', 'rm', network])
                            except:
                                pass
                
                # Get volumes
                result = execute_docker_command(['docker', 'volume', 'ls', '--format', '{{.Name}}'])
                if result.returncode == 0:
                    volumes = [name.strip() for name in result.stdout.split('\n') if name.strip()]
                    test_volumes = [v for v in volumes if any(test_prefix in v for test_prefix in 
                                                             ['test_', 'orphan_', 'perf_', 'pressure_'])]
                    
                    if test_volumes:
                        logger.info(f"   Cleaning up {len(test_volumes)} test volumes")
                        for volume in test_volumes:
                            try:
                                execute_docker_command(['docker', 'volume', 'rm', volume])
                            except:
                                pass
                
            except Exception as e:
                logger.warning(f"Resource cleanup error: {e}")
            
            logger.info(" PASS:  Inter-suite cleanup completed")
            
        except Exception as e:
            logger.error(f"Critical cleanup error: {e}")
    
    def run_all_suites(self) -> OverallTestReport:
        """Run all test suites with comprehensive orchestration."""
        logger.info("[U+1F680] Starting Docker Stability Test Suite Orchestration")
        
        overall_start_time = datetime.now()
        
        # Determine execution order
        if self.args.suites:
            # Run only specified suites
            suite_order = [s for s in self.args.suites if s in self.test_suites]
        else:
            # Run all suites in priority order
            suite_order = sorted(self.test_suites.keys(), 
                               key=lambda x: self.test_suites[x]['priority'])
        
        if not suite_order:
            raise ValueError("No valid test suites specified")
        
        logger.info(f"[U+1F4CB] Execution plan: {', '.join(suite_order)}")
        
        # Execute test suites
        if self.args.parallel_suites and len(suite_order) > 1:
            logger.info(" CYCLE:  Running suites in parallel")
            self.run_suites_parallel(suite_order)
        else:
            logger.info("[U+27A1][U+FE0F] Running suites sequentially")
            self.run_suites_sequential(suite_order)
        
        overall_end_time = datetime.now()
        total_duration = (overall_end_time - overall_start_time).total_seconds()
        
        # Calculate overall metrics
        total_tests_run = sum(r.tests_run for r in self.suite_results)
        total_tests_passed = sum(r.tests_passed for r in self.suite_results)
        total_tests_failed = sum(r.tests_failed for r in self.suite_results)
        total_tests_skipped = sum(r.tests_skipped for r in self.suite_results)
        
        success_rate = (total_tests_passed / total_tests_run * 100) if total_tests_run > 0 else 0
        overall_success = all(r.success for r in self.suite_results) and total_tests_failed == 0
        
        # Get final system and Docker metrics
        final_system_metrics = self.get_system_metrics()
        final_docker_metrics = self.get_docker_metrics()
        
        report = OverallTestReport(
            execution_id=self.execution_id,
            start_time=overall_start_time,
            end_time=overall_end_time,
            total_duration_seconds=total_duration,
            suite_results=self.suite_results,
            overall_success=overall_success,
            total_tests_run=total_tests_run,
            total_tests_passed=total_tests_passed,
            total_tests_failed=total_tests_failed,
            total_tests_skipped=total_tests_skipped,
            success_rate_percent=success_rate,
            system_metrics=final_system_metrics,
            docker_metrics=final_docker_metrics
        )
        
        return report
    
    def run_suites_sequential(self, suite_order: List[str]):
        """Run test suites sequentially with cleanup between each."""
        for i, suite_key in enumerate(suite_order):
            suite_config = self.test_suites[suite_key]
            
            logger.info(f"[U+1F4E6] [{i+1}/{len(suite_order)}] {suite_config['name']}")
            
            # Check for emergency stop
            if self.emergency_stop.is_set():
                logger.warning(" ALERT:  Emergency stop activated - halting test execution")
                break
            
            # Run test suite
            result = self.run_test_suite(suite_key, suite_config)
            self.suite_results.append(result)
            
            # Cleanup between suites (except after last suite)
            if i < len(suite_order) - 1:
                self.cleanup_between_suites()
                
                # Brief pause between suites
                time.sleep(3)
    
    def run_suites_parallel(self, suite_order: List[str]):
        """Run compatible test suites in parallel."""
        # For safety, limit parallel execution to lightweight suites
        parallel_safe = ['stability', 'edge_cases']
        sequential_required = ['performance', 'integration']
        
        parallel_suites = [s for s in suite_order if s in parallel_safe]
        sequential_suites = [s for s in suite_order if s in sequential_required]
        
        # Run parallel-safe suites first
        if parallel_suites and len(parallel_suites) > 1:
            logger.info(f" CYCLE:  Running parallel suites: {', '.join(parallel_suites)}")
            
            with ThreadPoolExecutor(max_workers=min(2, len(parallel_suites))) as executor:
                futures = {
                    executor.submit(self.run_test_suite, suite_key, self.test_suites[suite_key]): suite_key
                    for suite_key in parallel_suites
                }
                
                for future in as_completed(futures):
                    suite_key = futures[future]
                    try:
                        result = future.result()
                        self.suite_results.append(result)
                    except Exception as e:
                        logger.error(f"Parallel suite {suite_key} failed: {e}")
        else:
            # Run parallel suites sequentially if only one
            for suite_key in parallel_suites:
                result = self.run_test_suite(suite_key, self.test_suites[suite_key])
                self.suite_results.append(result)
        
        # Cleanup after parallel suites
        if parallel_suites:
            self.cleanup_between_suites()
        
        # Run sequential suites
        for suite_key in sequential_suites:
            if self.emergency_stop.is_set():
                break
                
            result = self.run_test_suite(suite_key, self.test_suites[suite_key])
            self.suite_results.append(result)
            
            # Cleanup between sequential suites
            self.cleanup_between_suites()
    
    def generate_report(self, report: OverallTestReport):
        """Generate comprehensive test execution report."""
        report_filename = f"docker_stability_report_{self.execution_id}.json"
        
        # Convert report to dictionary for JSON serialization
        report_dict = asdict(report)
        
        # Convert datetime objects to ISO strings
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            else:
                return obj
        
        report_dict = convert_datetime(report_dict)
        
        # Save JSON report
        with open(report_filename, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)
        
        # Generate CSV summary
        csv_filename = f"docker_stability_summary_{self.execution_id}.csv"
        with open(csv_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Suite', 'Success', 'Duration (s)', 'Tests Run', 'Passed', 'Failed', 'Skipped'])
            
            for result in report.suite_results:
                writer.writerow([
                    result.suite_name,
                    result.success,
                    f"{result.duration_seconds:.1f}",
                    result.tests_run,
                    result.tests_passed,
                    result.tests_failed,
                    result.tests_skipped
                ])
        
        # Print console summary
        self.print_summary(report)
        
        logger.info(f" CHART:  Reports generated:")
        logger.info(f"   Detailed: {report_filename}")
        logger.info(f"   Summary:  {csv_filename}")
        
        return report_filename, csv_filename
    
    def print_summary(self, report: OverallTestReport):
        """Print comprehensive test execution summary."""
        print("\n" + "="*80)
        print("[U+1F433] DOCKER STABILITY TEST SUITE EXECUTION REPORT")
        print("="*80)
        
        print(f"Execution ID: {report.execution_id}")
        print(f"Duration: {report.total_duration_seconds:.1f}s ({report.total_duration_seconds/60:.1f} minutes)")
        
        status = " PASS:  SUCCESS" if report.overall_success else " FAIL:  FAILED"
        print(f"Overall Status: {status}")
        
        print(f"\nTest Summary:")
        print(f"  Total Tests: {report.total_tests_run}")
        print(f"  Passed:      {report.total_tests_passed}")
        print(f"  Failed:      {report.total_tests_failed}")
        print(f"  Skipped:     {report.total_tests_skipped}")
        print(f"  Success Rate: {report.success_rate_percent:.1f}%")
        
        print(f"\nSuite Results:")
        for result in report.suite_results:
            status = " PASS: " if result.success else " FAIL: "
            print(f"  {status} {result.suite_name}")
            print(f"     Duration: {result.duration_seconds:.1f}s")
            print(f"     Tests: {result.tests_passed}/{result.tests_run} passed")
            
            if not result.success and result.error_messages:
                print(f"     Errors: {len(result.error_messages)} error(s)")
        
        # Performance summary
        if report.suite_results:
            avg_duration = sum(r.duration_seconds for r in report.suite_results) / len(report.suite_results)
            print(f"\nPerformance:")
            print(f"  Average Suite Duration: {avg_duration:.1f}s")
            print(f"  Total Resource Usage: {sum(r.resource_usage.get('peak_memory_gb', 0) for r in report.suite_results):.1f}GB peak memory")
        
        # System health
        if report.system_metrics:
            print(f"\nFinal System State:")
            print(f"  CPU Usage: {report.system_metrics.get('cpu_percent', 0):.1f}%")
            print(f"  Memory Usage: {report.system_metrics.get('memory_percent', 0):.1f}%")
            print(f"  Disk Free: {report.system_metrics.get('disk_free_gb', 0):.1f}GB")
        
        # Docker health
        if report.docker_metrics and 'rate_limiter_stats' in report.docker_metrics:
            docker_stats = report.docker_metrics['rate_limiter_stats']
            print(f"\nDocker Infrastructure:")
            print(f"  Total Operations: {docker_stats.get('total_operations', 0)}")
            print(f"  Success Rate: {docker_stats.get('success_rate', 0):.1f}%")
            print(f"  Force Flag Violations: {docker_stats.get('force_flag_violations', 0)}")
            print(f"  Rate Limited Operations: {docker_stats.get('rate_limited_operations', 0)}")
        
        print("="*80)


def setup_emergency_stop_handler(orchestrator):
    """Setup emergency stop signal handler."""
    import signal
    
    def emergency_stop_handler(signum, frame):
        logger.warning(" ALERT:  Emergency stop signal received")
        orchestrator.emergency_stop.set()
        print("\n ALERT:  Emergency stop activated - Test execution will halt after current suite")
    
    signal.signal(signal.SIGINT, emergency_stop_handler)
    signal.signal(signal.SIGTERM, emergency_stop_handler)


def main():
    """Main entry point for Docker stability test orchestration."""
    parser = argparse.ArgumentParser(
        description='Docker Stability Test Suite Orchestrator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run all test suites sequentially
  %(prog)s --suites stability edge_cases      # Run specific suites
  %(prog)s --parallel-suites                  # Run compatible suites in parallel
  %(prog)s --verbose --timeout 300            # Verbose output with 5min timeout per suite
  %(prog)s --force                           # Force execution despite resource constraints
        """
    )
    
    parser.add_argument(
        '--suites', 
        nargs='+',
        choices=['stability', 'edge_cases', 'performance', 'integration'],
        help='Specific test suites to run (default: all)'
    )
    
    parser.add_argument(
        '--parallel-suites',
        action='store_true',
        help='Run compatible test suites in parallel'
    )
    
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Enable parallel test execution within suites'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        help='Timeout in seconds for each test suite'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose test output'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force execution despite resource constraints'
    )
    
    parser.add_argument(
        '--baseline',
        action='store_true',
        help='Establish performance baselines (saves metrics for future comparison)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize orchestrator
        orchestrator = DockerStabilityTestOrchestrator(args)
        
        # Setup emergency stop handler
        setup_emergency_stop_handler(orchestrator)
        
        # Run all test suites
        report = orchestrator.run_all_suites()
        
        # Generate comprehensive reports
        report_files = orchestrator.generate_report(report)
        
        # Exit with appropriate code
        exit_code = 0 if report.overall_success else 1
        
        if report.overall_success:
            logger.info(" CELEBRATION:  ALL DOCKER STABILITY TESTS PASSED!")
            print("\n CELEBRATION:  Docker infrastructure is BULLETPROOF! [U+1F6E1][U+FE0F]")
        else:
            logger.error("[U+1F4A5] DOCKER STABILITY TEST FAILURES DETECTED!")
            print("\n[U+1F4A5] Docker infrastructure needs attention!  WARNING: [U+FE0F]")
        
        print(f"\nReport files: {', '.join(report_files)}")
        
        return exit_code
        
    except KeyboardInterrupt:
        logger.warning(" ALERT:  Test execution interrupted by user")
        return 130
    except Exception as e:
        logger.error(f" FAIL:  Test orchestration failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)