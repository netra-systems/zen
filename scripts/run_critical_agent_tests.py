#!/usr/bin/env python

# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
🚨 CRITICAL: Run Top 5 Agent Tests with Enhanced Memory Management

BUSINESS CRITICAL: These tests protect $500K+ ARR by validating core agent functionality.
Each test requires ~850MB memory during agent operations and MUST run sequentially
with fresh Docker containers to prevent memory exhaustion.

Features:
- Sequential execution with Docker isolation
- Memory monitoring and pre-flight checks
- Failure recovery with detailed reporting
- UnifiedDockerManager integration
- Comprehensive test reporting

Usage:
    python scripts/run_critical_agent_tests.py [options]
    
Options:
    --dry-run          Show what would run without executing
    --skip-cleanup     Skip Docker cleanup (for debugging)
    --memory-limit     Set memory threshold (default: 8GB)
    --verbose          Enable detailed logging
"""

import os
import sys
import subprocess
import time
import psutil
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

# Add project root to path for absolute imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Enhanced imports using UnifiedDockerManager and MemoryGuardian
try:
    from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
    from test_framework.memory_guardian import MemoryGuardian, TestProfile
    from shared.isolated_environment import get_env
except ImportError as e:
    print(f"❌ CRITICAL: Failed to import required modules: {e}")
    print("Ensure you're running from project root with proper Python path")
    sys.exit(1)


@dataclass
class CriticalTest:
    """Definition of a critical agent test."""
    name: str
    path: str
    business_value: str
    description: str
    timeout: int
    expected_memory_mb: int = 850
    retry_count: int = 1
    
    @property
    def full_path(self) -> Path:
        """Get full path to test file."""
        return project_root / self.path
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for reporting."""
        return asdict(self)


@dataclass
class TestResult:
    """Result of running a critical test."""
    test: CriticalTest
    passed: bool
    execution_time: float
    memory_before_mb: float
    memory_after_mb: float
    memory_peak_mb: float
    error_message: Optional[str] = None
    retry_attempt: int = 0
    docker_project: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON reporting."""
        result = asdict(self)
        result['test'] = self.test.to_dict()
        return result


# Top 5 Critical Agent Tests (in execution order - most critical first)
CRITICAL_TESTS = [
    CriticalTest(
        name="WebSocket Agent Events Suite",
        path="tests/mission_critical/test_websocket_agent_events_suite.py",
        business_value="$500K+ ARR - Core Chat Functionality",
        description="Validates all 5 WebSocket events during agent execution",
        timeout=300,
        expected_memory_mb=850,
        retry_count=2  # Most critical - allow 2 retries
    ),
    CriticalTest(
        name="Agent Orchestration Real LLM",
        path="tests/e2e/test_agent_orchestration_real_llm.py",
        business_value="Core Agent Execution Engine",
        description="ExecutionEngine with real LLM integration and tool dispatch",
        timeout=600,
        expected_memory_mb=900,
        retry_count=1
    ),
    CriticalTest(
        name="Agent WebSocket Events Comprehensive", 
        path="tests/e2e/test_agent_websocket_events_comprehensive.py",
        business_value="Complete Event Flow Coverage",
        description="Full agent lifecycle and complex event sequences",
        timeout=400,
        expected_memory_mb=850,
        retry_count=1
    ),
    CriticalTest(
        name="Agent Message Flow Implementation",
        path="tests/e2e/test_agent_message_flow_implementation.py",
        business_value="End-to-End User Chat Flow",
        description="Complete message processing and streaming pipeline",
        timeout=400,
        expected_memory_mb=800,
        retry_count=1
    ),
    CriticalTest(
        name="Agent Write-Review-Refine Integration",
        path="tests/e2e/test_agent_write_review_refine_integration_core.py",
        business_value="Multi-Agent Collaboration",
        description="Complex agent workflow and state management",
        timeout=500,
        expected_memory_mb=950,
        retry_count=1
    ),
]


class CriticalTestRunner:
    """Enhanced test runner with memory monitoring and Docker isolation."""
    
    def __init__(self, dry_run: bool = False, skip_cleanup: bool = False, 
                 memory_limit_gb: float = 8.0, verbose: bool = False):
        self.dry_run = dry_run
        self.skip_cleanup = skip_cleanup
        self.memory_limit_gb = memory_limit_gb
        self.verbose = verbose
        
        # Setup logging
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.memory_guardian = MemoryGuardian()
        self.docker_manager = None
        self.results: List[TestResult] = []
        
        # Test environment
        self.env = get_env()
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics."""
        mem = psutil.virtual_memory()
        return {
            "total_gb": mem.total / (1024**3),
            "available_gb": mem.available / (1024**3),
            "used_gb": mem.used / (1024**3),
            "percent": mem.percent,
            "total_mb": mem.total / (1024**2),
            "available_mb": mem.available / (1024**2),
            "used_mb": mem.used / (1024**2),
        }
    
    def print_memory_status(self, label: str = ""):
        """Print current memory status with enhanced details."""
        mem = self.get_memory_usage()
        status = f"[{label}] " if label else ""
        status += f"Memory: {mem['used_gb']:.1f}/{mem['total_gb']:.1f}GB ({mem['percent']:.1f}%) - Available: {mem['available_gb']:.1f}GB"
        
        # Color coding based on memory usage
        if mem['percent'] > 85:
            icon = "🔴"
        elif mem['percent'] > 70:
            icon = "🟡"
        else:
            icon = "🟢"
            
        print(f"{icon} {status}")
        
        if self.verbose:
            print(f"   └─ Available MB: {mem['available_mb']:.0f}, Used MB: {mem['used_mb']:.0f}")
    
    def perform_memory_preflight_check(self) -> bool:
        """Perform comprehensive memory check before starting tests."""
        print("\n🔍 Performing Memory Pre-flight Check...")
        
        mem = self.get_memory_usage()
        self.print_memory_status("Pre-flight")
        
        # Check if we have enough memory for critical tests
        min_required_gb = self.memory_limit_gb
        if mem['available_gb'] < min_required_gb:
            print(f"❌ INSUFFICIENT MEMORY: Available {mem['available_gb']:.1f}GB < Required {min_required_gb:.1f}GB")
            print("\n💡 Recommendations:")
            print("   • Close other applications to free memory")
            print("   • Use --memory-limit to lower threshold")
            print("   • Run tests individually instead of in sequence")
            return False
        
        # Use MemoryGuardian for detailed analysis
        # Get memory requirements for FULL profile (highest requirement)
        total_required_mb = 4096  # Estimated total for all services
        can_run, reason = self.memory_guardian.check_memory_available(total_required_mb)
        if not can_run:
            print(f"❌ MEMORY GUARDIAN FAILURE: {reason}")
            return False
        
        print(f"✅ Memory Pre-flight Check PASSED - {mem['available_gb']:.1f}GB available")
        return True
    
    def cleanup_docker_environment(self) -> bool:
        """Enhanced Docker cleanup using UnifiedDockerManager."""
        if self.skip_cleanup:
            print("⏸️ Skipping Docker cleanup (--skip-cleanup flag)")
            return True
            
        print("\n🧹 Enhanced Docker Cleanup...")
        
        try:
            # Create a temporary UnifiedDockerManager for cleanup
            temp_manager = UnifiedDockerManager(
                environment_type=EnvironmentType.DEDICATED,
                use_alpine=True,
                test_id="netra-critical-cleanup"
            )
            
            # Stop all containers and cleanup
            cleanup_success = temp_manager.cleanup()
            
            if cleanup_success:
                print("✅ Docker cleanup completed successfully")
                self.print_memory_status("After cleanup")
                return True
            else:
                print("⚠️ Docker cleanup had issues but continuing...")
                return False
                
        except Exception as e:
            self.logger.error(f"Docker cleanup failed: {e}")
            print(f"❌ Docker cleanup error: {e}")
            return False
    
    def start_docker_services(self, test: CriticalTest) -> Tuple[bool, str, Optional[UnifiedDockerManager]]:
        """Start Docker services using UnifiedDockerManager with memory optimization."""
        print(f"\n🚀 Starting Docker services for: {test.name}")
        
        if self.dry_run:
            print("🔍 DRY RUN: Would start Docker services")
            return True, "dry-run-project", None
        
        try:
            # Create unique project name for isolation
            timestamp = int(time.time())
            project_name = f"netra-critical-{test.name.lower().replace(' ', '-')}-{timestamp}"
            
            # Initialize UnifiedDockerManager with optimized settings
            self.docker_manager = UnifiedDockerManager(
                environment_type=EnvironmentType.DEDICATED,
                use_alpine=True,  # Use Alpine for memory efficiency
                test_id=project_name,
                use_production_images=False,  # Use development images for faster startup
                rebuild_images=False,  # Don't rebuild for speed
                rebuild_backend_only=True,
                pull_policy="missing"
            )
            
            self.logger.info(f"Starting Docker services with project: {project_name}")
            
            # Pre-flight memory check specific to this test
            mem_before = self.get_memory_usage()
            required_mb = test.expected_memory_mb + 1024  # Add 1GB buffer
            
            if mem_before['available_mb'] < required_mb:
                print(f"❌ Insufficient memory for test: {mem_before['available_mb']:.0f}MB < {required_mb}MB")
                return False, project_name, None
            
            # Start services with enhanced monitoring
            success = self.docker_manager.start_services(
                timeout=300,
                wait_for_healthy=True,
                services=['postgres', 'redis', 'backend', 'auth']  # Only essential services
            )
            
            if not success:
                print("❌ Failed to start Docker services")
                return False, project_name, self.docker_manager
            
            # Verify services are healthy
            health_report = self.docker_manager.get_health_status()
            unhealthy_services = [s for s in health_report if not health_report[s].is_healthy]
            
            if unhealthy_services:
                print(f"❌ Unhealthy services: {unhealthy_services}")
                return False, project_name, self.docker_manager
            
            print("✅ All services started and healthy!")
            self.print_memory_status("After Docker startup")
            
            # Store service ports for test execution
            service_ports = self.docker_manager.get_service_ports()
            self.logger.info(f"Service ports: {service_ports}")
            
            return True, project_name, self.docker_manager
            
        except Exception as e:
            self.logger.error(f"Failed to start Docker services: {e}")
            print(f"❌ Error starting Docker services: {e}")
            return False, project_name if 'project_name' in locals() else "", self.docker_manager
    
    def stop_docker_services(self, project_name: str, manager: Optional[UnifiedDockerManager] = None):
        """Stop Docker services using UnifiedDockerManager."""
        if not project_name or self.skip_cleanup:
            return
        
        print(f"\n🛑 Stopping Docker services for {project_name}...")
        
        if self.dry_run:
            print("🔍 DRY RUN: Would stop Docker services")
            return
        
        try:
            if manager:
                # Use the existing manager for clean shutdown
                success = manager.stop_services(timeout=30, remove_containers=True)
                if success:
                    print("✅ Docker services stopped cleanly")
                else:
                    print("⚠️ Docker services stopped with warnings")
            else:
                # Fallback to cleanup
                self.cleanup_docker_environment()
                
        except Exception as e:
            self.logger.error(f"Failed to stop Docker services: {e}")
            print(f"❌ Error stopping Docker services: {e}")
    
    def run_single_test(self, test: CriticalTest, attempt: int = 1) -> TestResult:
        """Run a single critical test with enhanced monitoring and reporting."""
        print(f"\n{'='*80}")
        print(f"🎯 Running: {test.name} (Attempt {attempt})")
        print(f"📊 Business Value: {test.business_value}")
        print(f"📝 Description: {test.description}")
        print(f"⏱️  Timeout: {test.timeout}s | Expected Memory: {test.expected_memory_mb}MB")
        print(f"{'='*80}")
        
        # Pre-test memory snapshot
        mem_before = self.get_memory_usage()
        self.print_memory_status("Before test")
        
        if not test.full_path.exists():
            error_msg = f"Test file not found: {test.full_path}"
            print(f"❌ {error_msg}")
            return TestResult(
                test=test,
                passed=False,
                execution_time=0.0,
                memory_before_mb=mem_before['used_mb'],
                memory_after_mb=mem_before['used_mb'],
                memory_peak_mb=mem_before['used_mb'],
                error_message=error_msg,
                retry_attempt=attempt
            )
        
        if self.dry_run:
            print("🔍 DRY RUN: Would execute test")
            return TestResult(
                test=test,
                passed=True,
                execution_time=0.0,
                memory_before_mb=mem_before['used_mb'],
                memory_after_mb=mem_before['used_mb'],
                memory_peak_mb=mem_before['used_mb'],
                retry_attempt=attempt,
                docker_project="dry-run"
            )
        
        # Build test command with enhanced options
        cmd = [
            sys.executable,
            str(test.full_path),
            "--real-services",
            "--real-llm",
            "-v" if self.verbose else "-s",
            "--tb=short",
            "--disable-warnings"
        ]
        
        # Enhanced environment variables
        test_env = os.environ.copy()
        test_env.update({
            "USE_REAL_SERVICES": "true",
            "REAL_LLM": "true", 
            "ENVIRONMENT": "test",
            "PYTHONUNBUFFERED": "1",
            "PYTEST_CURRENT_TEST": test.name,
            "TEST_MEMORY_LIMIT_MB": str(test.expected_memory_mb),
            "DISABLE_DOCKER_LOGGING": "true" if not self.verbose else "false"
        })
        
        # Add Docker service configuration if manager exists
        if self.docker_manager:
            service_ports = self.docker_manager.get_service_ports()
            for service, port in service_ports.items():
                test_env[f"{service.upper()}_PORT"] = str(port)
        
        start_time = time.time()
        peak_memory_mb = mem_before['used_mb']
        error_message = None
        
        try:
            self.logger.info(f"Executing test command: {' '.join(cmd)}")
            
            # Execute test with timeout and monitoring
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=test.timeout,
                env=test_env,
                cwd=project_root
            )
            
            execution_time = time.time() - start_time
            
            # Post-test memory snapshot
            mem_after = self.get_memory_usage()
            peak_memory_mb = max(peak_memory_mb, mem_after['used_mb'])
            
            # Analyze test result
            passed = result.returncode == 0
            
            if passed:
                print(f"✅ PASSED in {execution_time:.1f}s")
                if self.verbose:
                    print(f"   Memory Delta: {mem_after['used_mb'] - mem_before['used_mb']:+.0f}MB")
                    print(f"   Peak Memory: {peak_memory_mb:.0f}MB")
            else:
                print(f"❌ FAILED after {execution_time:.1f}s (Exit Code: {result.returncode})")
                
                # Capture error details
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    relevant_lines = [line for line in lines if any(keyword in line.lower() 
                                    for keyword in ['error', 'failed', 'exception', 'traceback'])]
                    
                    if relevant_lines:
                        error_message = '\n'.join(relevant_lines[-5:])  # Last 5 error lines
                    else:
                        error_message = '\n'.join(lines[-10:])  # Last 10 lines if no errors found
                
                if result.stderr:
                    stderr_snippet = result.stderr.strip()[-1000:]  # Last 1000 chars
                    error_message = f"{error_message}\n\nSTDERR:\n{stderr_snippet}" if error_message else stderr_snippet
                
                if self.verbose:
                    print("\n--- Test Output (Relevant Lines) ---")
                    for line in (error_message or "No error output").split('\n')[:20]:
                        if line.strip():
                            print(f"  {line}")
            
            self.print_memory_status(f"After test ({'PASSED' if passed else 'FAILED'})")
            
            return TestResult(
                test=test,
                passed=passed,
                execution_time=execution_time,
                memory_before_mb=mem_before['used_mb'],
                memory_after_mb=mem_after['used_mb'],
                memory_peak_mb=peak_memory_mb,
                error_message=error_message,
                retry_attempt=attempt,
                docker_project=getattr(self.docker_manager, 'project_name', None) if self.docker_manager else None
            )
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            mem_after = self.get_memory_usage()
            error_message = f"Test timeout after {test.timeout}s"
            
            print(f"⏱️ TIMEOUT after {test.timeout}s")
            self.print_memory_status("After test (TIMEOUT)")
            
            return TestResult(
                test=test,
                passed=False,
                execution_time=execution_time,
                memory_before_mb=mem_before['used_mb'],
                memory_after_mb=mem_after['used_mb'],
                memory_peak_mb=peak_memory_mb,
                error_message=error_message,
                retry_attempt=attempt,
                docker_project=getattr(self.docker_manager, 'project_name', None) if self.docker_manager else None
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            mem_after = self.get_memory_usage()
            error_message = f"Unexpected error: {str(e)}"
            
            print(f"❌ UNEXPECTED ERROR: {e}")
            self.print_memory_status("After test (ERROR)")
            
            return TestResult(
                test=test,
                passed=False,
                execution_time=execution_time,
                memory_before_mb=mem_before['used_mb'],
                memory_after_mb=mem_after['used_mb'],
                memory_peak_mb=peak_memory_mb,
                error_message=error_message,
                retry_attempt=attempt,
                docker_project=getattr(self.docker_manager, 'project_name', None) if self.docker_manager else None
            )
    
    def run_critical_test_with_retries(self, test: CriticalTest) -> TestResult:
        """Run a critical test with retry logic and Docker isolation."""
        print(f"\n{'#'*80}")
        print(f"STARTING: {test.name}")
        print(f"{'#'*80}")
        
        best_result = None
        
        for attempt in range(1, test.retry_count + 1):
            if attempt > 1:
                print(f"\n🔄 RETRY {attempt}/{test.retry_count} for {test.name}")
                # Extra cleanup before retry
                self.cleanup_docker_environment()
                time.sleep(10)  # Longer pause for retries
            
            # Start fresh Docker environment
            docker_started, project_name, manager = self.start_docker_services(test)
            
            if not docker_started:
                error_msg = "Docker startup failed"
                print(f"⚠️ Skipping test attempt due to Docker failure")
                
                result = TestResult(
                    test=test,
                    passed=False,
                    execution_time=0.0,
                    memory_before_mb=self.get_memory_usage()['used_mb'],
                    memory_after_mb=self.get_memory_usage()['used_mb'],
                    memory_peak_mb=self.get_memory_usage()['used_mb'],
                    error_message=error_msg,
                    retry_attempt=attempt,
                    docker_project=project_name
                )
                
                best_result = result if best_result is None else best_result
                continue
            
            try:
                # Run the test
                result = self.run_single_test(test, attempt)
                
                # Store the result
                if best_result is None or result.passed:
                    best_result = result
                
                # If test passed, no need for more retries
                if result.passed:
                    break
                    
            except Exception as e:
                self.logger.error(f"Unexpected error in test execution: {e}")
                error_msg = f"Test execution error: {str(e)}"
                
                result = TestResult(
                    test=test,
                    passed=False,
                    execution_time=0.0,
                    memory_before_mb=self.get_memory_usage()['used_mb'],
                    memory_after_mb=self.get_memory_usage()['used_mb'],
                    memory_peak_mb=self.get_memory_usage()['used_mb'],
                    error_message=error_msg,
                    retry_attempt=attempt,
                    docker_project=project_name
                )
                
                if best_result is None:
                    best_result = result
                    
            finally:
                # Always cleanup Docker after each attempt
                self.stop_docker_services(project_name, manager)
                
                # Brief pause between attempts
                if attempt < test.retry_count:
                    print(f"\n⏸️  Pausing 15 seconds before retry...")
                    time.sleep(15)
        
        return best_result
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        total_execution_time = sum(r.execution_time for r in self.results)
        
        # Memory statistics
        memory_stats = {
            "peak_usage_mb": max((r.memory_peak_mb for r in self.results), default=0),
            "total_memory_delta_mb": sum(r.memory_after_mb - r.memory_before_mb for r in self.results),
            "average_test_memory_mb": sum(r.memory_peak_mb for r in self.results) / max(total_tests, 1)
        }
        
        # Business impact analysis
        failed_business_value = []
        for result in self.results:
            if not result.passed:
                failed_business_value.append(result.test.business_value)
        
        report = {
            "execution_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": (passed_tests / max(total_tests, 1)) * 100,
                "total_execution_time_seconds": total_execution_time,
                "dry_run": self.dry_run
            },
            "memory_analysis": memory_stats,
            "business_impact": {
                "critical_failures": failed_business_value,
                "arr_at_risk": "$500K+ ARR" if failed_tests > 0 else "$0 ARR"
            },
            "test_results": [r.to_dict() for r in self.results],
            "configuration": {
                "memory_limit_gb": self.memory_limit_gb,
                "skip_cleanup": self.skip_cleanup,
                "verbose": self.verbose
            }
        }
        
        return report
    
    def save_report(self, report: Dict, filename: str = None):
        """Save comprehensive report to file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"critical_agent_tests_report_{timestamp}.json"
        
        report_path = project_root / "reports" / filename
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📄 Comprehensive report saved: {report_path}")
        return report_path
    
    def print_summary(self):
        """Print detailed test summary."""
        print("\n" + "="*80)
        print("📊 CRITICAL AGENT TESTS - FINAL SUMMARY")
        print("="*80)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        # Results table
        for result in self.results:
            icon = "✅" if result.passed else "❌"
            time_str = f"{result.execution_time:.1f}s"
            memory_str = f"{result.memory_peak_mb:.0f}MB"
            retry_str = f"(retry {result.retry_attempt})" if result.retry_attempt > 1 else ""
            
            print(f"{icon} {result.test.name}: {time_str} | {memory_str} {retry_str}")
            
            if not result.passed and result.error_message:
                # Show first line of error for quick diagnosis
                first_error_line = result.error_message.split('\n')[0].strip()
                print(f"   └─ {first_error_line[:80]}{'...' if len(first_error_line) > 80 else ''}")
        
        # Summary statistics
        print(f"\n📈 Results: {passed_tests}/{total_tests} passed ({(passed_tests/max(total_tests,1)*100):.1f}%)")
        
        total_time = sum(r.execution_time for r in self.results)
        peak_memory = max((r.memory_peak_mb for r in self.results), default=0)
        
        print(f"⏱️  Total Time: {total_time:.1f}s | Peak Memory: {peak_memory:.0f}MB")
        
        # Business impact
        if passed_tests == total_tests:
            print("\n🎉 SUCCESS! All critical tests passed!")
            print("✅ The product is ready - $500K+ ARR protected!")
        else:
            print(f"\n🚨 FAILURE! {failed_tests} critical tests failed!")
            print("❌ IMMEDIATE ACTION REQUIRED - $500K+ ARR at risk!")
            
            # Show which business values are at risk
            print("\n💰 Business Impact:")
            for result in self.results:
                if not result.passed:
                    print(f"   • {result.test.business_value} - {result.test.name}")
    
    def run_all_tests(self) -> int:
        """Main execution method - run all critical tests."""
        print("\n" + "="*80)
        print("🚨 CRITICAL AGENT TESTS - BUSINESS CRITICAL EXECUTION")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if self.dry_run:
            print("🔍 DRY RUN MODE - No actual execution")
        print("="*80)
        
        # Pre-flight checks
        if not self.perform_memory_preflight_check():
            print("\n❌ Pre-flight check failed. Aborting test execution.")
            return 1
        
        # Initial cleanup
        print("\n🧹 Initial environment cleanup...")
        self.cleanup_docker_environment()
        time.sleep(5)
        
        # Execute each critical test
        for i, test in enumerate(CRITICAL_TESTS, 1):
            print(f"\n{'='*20} TEST {i}/{len(CRITICAL_TESTS)} {'='*20}")
            
            result = self.run_critical_test_with_retries(test)
            self.results.append(result)
            
            # Memory check after each test
            mem_after_test = self.get_memory_usage()
            if mem_after_test['percent'] > 90:
                print(f"⚠️ HIGH MEMORY USAGE: {mem_after_test['percent']:.1f}% - Performing extra cleanup")
                self.cleanup_docker_environment()
                time.sleep(10)
            
            # Brief pause between tests
            if i < len(CRITICAL_TESTS):
                pause_time = 15 if result.passed else 30  # Longer pause after failures
                print(f"\n⏸️  Pausing {pause_time} seconds before next test...")
                if not self.dry_run:
                    time.sleep(pause_time)
        
        # Final cleanup
        if not self.skip_cleanup:
            print("\n🧹 Final environment cleanup...")
            self.cleanup_docker_environment()
        
        # Generate and save report
        report = self.generate_report()
        self.save_report(report)
        
        # Print summary
        self.print_summary()
        
        # Return exit code
        passed_count = sum(1 for r in self.results if r.passed)
        return 0 if passed_count == len(CRITICAL_TESTS) else 1


def main():
    """Main entry point with argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run critical agent tests with enhanced memory management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_critical_agent_tests.py
  python scripts/run_critical_agent_tests.py --dry-run
  python scripts/run_critical_agent_tests.py --memory-limit 6 --verbose
  python scripts/run_critical_agent_tests.py --skip-cleanup

This script protects $500K+ ARR by validating core agent functionality.
"""
    )
    
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would run without executing")
    parser.add_argument("--skip-cleanup", action="store_true",
                       help="Skip Docker cleanup (for debugging)")
    parser.add_argument("--memory-limit", type=float, default=8.0,
                       help="Memory threshold in GB (default: 8.0)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable detailed logging")
    
    args = parser.parse_args()
    
    # Create and run the test runner
    runner = CriticalTestRunner(
        dry_run=args.dry_run,
        skip_cleanup=args.skip_cleanup,
        memory_limit_gb=args.memory_limit,
        verbose=args.verbose
    )
    
    try:
        return runner.run_all_tests()
    except KeyboardInterrupt:
        print("\n⏹️ Test execution interrupted by user")
        if not args.skip_cleanup:
            print("🧹 Performing cleanup...")
            runner.cleanup_docker_environment()
        return 130
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        runner.logger.exception("Critical test runner failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())