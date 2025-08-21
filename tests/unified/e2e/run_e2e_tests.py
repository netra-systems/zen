#!/usr/bin/env python
"""
E2E Test Runner with CI/CD Integration
Business Value: $100K+ MRR protection through comprehensive E2E validation

BUSINESS VALUE JUSTIFICATION (BVJ):
1. Segment: All segments (critical for user conversion funnel)
2. Business Goal: Prevent production failures and user funnel breaks
3. Value Impact: 99.9% uptime protection, prevents $100K+ MRR loss
4. Revenue Impact: Protects entire customer acquisition and retention flow

Comprehensive E2E test runner with:
- Auto test discovery
- Parallel execution for speed
- Performance baseline tracking  
- CI/CD compatible exit codes
- Real service coordination
"""

import argparse
import asyncio
import json
import logging
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Test execution result with timing and status"""
    test_file: str
    status: str  # 'passed', 'failed', 'skipped', 'error'
    duration: float
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    error_message: Optional[str] = None

@dataclass 
class E2ERunSummary:
    """Complete E2E run summary for reporting"""
    start_time: float
    end_time: float
    total_duration: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_tests: int
    success_rate: float
    results: List[TestResult]
    performance_baseline_met: bool
    ci_exit_code: int

class TestDiscovery:
    """Discover E2E tests across the project"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        
    def discover_e2e_tests(self) -> List[Path]:
        """Find all E2E test files"""
        test_patterns = [
            "test_*e2e*.py",
            "test_*integration*.py", 
            "test_real_*.py",
            "*e2e*.py"
        ]
        
        test_files = []
        search_paths = [
            self.project_root / "tests" / "unified" / "e2e",
            self.project_root / "tests" / "unified",
            self.project_root / "app" / "tests",
            self.project_root / "integration_tests"
        ]
        
        for search_path in search_paths:
            if search_path.exists():
                for pattern in test_patterns:
                    test_files.extend(search_path.glob(pattern))
                    test_files.extend(search_path.rglob(pattern))
        
        # Remove duplicates
        unique_tests = list(set(test_files))
        
        # Filter to actual test files
        valid_tests = []
        for test_file in unique_tests:
            if self._is_valid_test_file(test_file):
                valid_tests.append(test_file)
        
        logger.info(f"Discovered {len(valid_tests)} E2E test files")
        return sorted(valid_tests)
    
    def _is_valid_test_file(self, file_path: Path) -> bool:
        """Check if file is a valid test file"""
        if not file_path.is_file() or file_path.suffix != '.py':
            return False
            
        try:
            content = file_path.read_text(encoding='utf-8')
            # Must contain pytest markers or test functions
            return any(marker in content for marker in [
                'def test_', '@pytest.mark', 'async def test_'
            ])
        except Exception:
            return False

class PerformanceTracker:
    """Track E2E test performance against baselines"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.baselines_file = project_root / "test_reports" / "performance_baselines.json"
        self.baselines = self._load_baselines()
    
    def _load_baselines(self) -> Dict[str, float]:
        """Load performance baselines"""
        if self.baselines_file.exists():
            try:
                return json.loads(self.baselines_file.read_text())
            except Exception as e:
                logger.warning(f"Could not load baselines: {e}")
        
        # Default baselines for E2E tests (in seconds)
        return {
            "total_e2e_suite": 300.0,  # 5 minutes max
            "individual_test": 30.0,   # 30 seconds max per test
            "critical_path": 10.0      # 10 seconds for critical tests
        }
    
    def check_performance(self, summary: E2ERunSummary) -> bool:
        """Check if performance baselines are met"""
        suite_baseline = self.baselines.get("total_e2e_suite", 300.0)
        individual_baseline = self.baselines.get("individual_test", 30.0)
        
        # Check total suite time
        if summary.total_duration > suite_baseline:
            logger.error(f"Suite exceeded baseline: {summary.total_duration:.1f}s > {suite_baseline}s")
            return False
        
        # Check individual test times
        slow_tests = [
            r for r in summary.results 
            if r.duration > individual_baseline and r.status != 'skipped'
        ]
        
        if slow_tests:
            logger.warning(f"Slow tests found: {len(slow_tests)}")
            for test in slow_tests[:5]:  # Show first 5
                logger.warning(f"  {test.test_file}: {test.duration:.1f}s")
        
        return True

class ServiceOrchestrator:
    """Orchestrate services needed for E2E testing"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.services = {}
        
    async def start_services(self) -> bool:
        """Start required services for E2E testing"""
        logger.info("Starting services for E2E testing...")
        
        # Use existing service manager if available
        try:
            from tests.unified.service_manager import ServiceManager
            from tests.unified.test_harness import UnifiedTestHarness
            
            harness = UnifiedTestHarness()
            service_manager = ServiceManager(harness)
            
            # Start core services
            await service_manager.start_auth_service()
            await service_manager.start_backend_service()
            
            # Wait for readiness
            await asyncio.sleep(2)
            
            self.services['service_manager'] = service_manager
            logger.info("Services started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start services: {e}")
            return False
    
    async def stop_services(self):
        """Stop all test services"""
        logger.info("Stopping test services...")
        
        service_manager = self.services.get('service_manager')
        if service_manager:
            try:
                await service_manager.stop_all_services()
            except Exception as e:
                logger.warning(f"Error stopping services: {e}")
        
        self.services.clear()

class E2ETestExecutor:
    """Execute E2E tests with parallel support"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        
    async def run_tests_parallel(self, test_files: List[Path], max_workers: int = 4) -> List[TestResult]:
        """Run tests in parallel for faster execution"""
        logger.info(f"Running {len(test_files)} tests in parallel (workers={max_workers})")
        
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all test jobs
            future_to_test = {
                executor.submit(self._run_single_test, test_file): test_file
                for test_file in test_files
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_test):
                test_file = future_to_test[future]
                try:
                    result = future.result(timeout=60)  # 1 minute per test max
                    results.append(result)
                    logger.info(f"✅ {test_file.name}: {result.status} ({result.duration:.1f}s)")
                except Exception as e:
                    error_result = TestResult(
                        test_file=str(test_file),
                        status='error',
                        duration=0.0,
                        exit_code=-1,
                        error_message=str(e)
                    )
                    results.append(error_result)
                    logger.error(f"❌ {test_file.name}: {e}")
        
        return results
    
    def _run_single_test(self, test_file: Path) -> TestResult:
        """Run a single test file and capture results"""
        start_time = time.time()
        
        try:
            # Run pytest on single file
            cmd = [
                sys.executable, "-m", "pytest", 
                str(test_file),
                "-v", "--tb=short",
                "--timeout=30",  # 30 second timeout per test
                "-x"  # Stop on first failure
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60  # 1 minute total timeout
            )
            
            duration = time.time() - start_time
            status = 'passed' if result.returncode == 0 else 'failed'
            
            return TestResult(
                test_file=str(test_file),
                status=status,
                duration=duration,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                test_file=str(test_file),
                status='error',
                duration=time.time() - start_time,
                exit_code=-1,
                error_message="Test timed out"
            )
        except Exception as e:
            return TestResult(
                test_file=str(test_file),
                status='error',
                duration=time.time() - start_time,
                exit_code=-1,
                error_message=str(e)
            )

class ResultReporter:
    """Generate comprehensive test reports"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.reports_dir = project_root / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
    
    def generate_summary(self, results: List[TestResult]) -> E2ERunSummary:
        """Generate comprehensive run summary"""
        if not results:
            return E2ERunSummary(
                start_time=time.time(),
                end_time=time.time(),
                total_duration=0.0,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                error_tests=0,
                success_rate=0.0,
                results=[],
                performance_baseline_met=False,
                ci_exit_code=1
            )
        
        # Calculate metrics
        passed = len([r for r in results if r.status == 'passed'])
        failed = len([r for r in results if r.status == 'failed'])
        skipped = len([r for r in results if r.status == 'skipped'])
        errors = len([r for r in results if r.status == 'error'])
        total = len(results)
        
        success_rate = (passed / total * 100) if total > 0 else 0.0
        total_duration = sum(r.duration for r in results)
        
        # Determine CI exit code
        ci_exit_code = 0 if failed == 0 and errors == 0 else 1
        
        return E2ERunSummary(
            start_time=min(time.time() - r.duration for r in results) if results else time.time(),
            end_time=time.time(),
            total_duration=total_duration,
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            error_tests=errors,
            success_rate=success_rate,
            results=results,
            performance_baseline_met=total_duration < 300,  # 5 minutes baseline
            ci_exit_code=ci_exit_code
        )
    
    def save_json_report(self, summary: E2ERunSummary) -> Path:
        """Save JSON report for CI/CD consumption"""
        report_file = self.reports_dir / "e2e_test_results.json"
        
        report_data = asdict(summary)
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"JSON report saved: {report_file}")
        return report_file
    
    def print_console_summary(self, summary: E2ERunSummary):
        """Print user-friendly console summary"""
        print("\n" + "="*80)
        print("🚀 E2E TEST RESULTS SUMMARY")
        print("="*80)
        
        # Overall status
        if summary.ci_exit_code == 0:
            print("✅ ALL E2E TESTS PASSED")
        else:
            print("❌ E2E TESTS FAILED")
        
        print(f"\n📊 Test Metrics:")
        print(f"   Total Tests: {summary.total_tests}")
        print(f"   ✅ Passed: {summary.passed_tests}")
        print(f"   ❌ Failed: {summary.failed_tests}")
        print(f"   ⏭️  Skipped: {summary.skipped_tests}")
        print(f"   🚨 Errors: {summary.error_tests}")
        print(f"   📈 Success Rate: {summary.success_rate:.1f}%")
        
        print(f"\n⏱️ Performance:")
        print(f"   Total Duration: {summary.total_duration:.1f}s")
        print(f"   Baseline Met: {'✅ Yes' if summary.performance_baseline_met else '❌ No'}")
        print(f"   Average Test Time: {summary.total_duration/summary.total_tests:.1f}s")
        
        # Show failed tests
        failed_tests = [r for r in summary.results if r.status in ['failed', 'error']]
        if failed_tests:
            print(f"\n💥 Failed Tests ({len(failed_tests)}):")
            for test in failed_tests:
                test_name = Path(test.test_file).name
                print(f"   ❌ {test_name}: {test.error_message or test.status}")
        
        print(f"\n💰 Business Impact:")
        if summary.ci_exit_code == 0:
            print(f"   ✅ $100K+ MRR protected")
            print(f"   ✅ User funnel validated")
            print(f"   ✅ Production deployment ready")
        else:
            print(f"   🚨 Revenue at risk - E2E failures detected")
            print(f"   🚨 User experience may be impacted")
            print(f"   🚨 Production deployment blocked")
        
        print("="*80)

class E2ETestRunner:
    """Main E2E test runner orchestrating all components"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.discovery = TestDiscovery(self.project_root)
        self.executor = E2ETestExecutor(self.project_root)
        self.reporter = ResultReporter(self.project_root)
        self.performance_tracker = PerformanceTracker(self.project_root)
        self.orchestrator = ServiceOrchestrator(self.project_root)
    
    async def run_e2e_suite(self, 
                           parallel: bool = True,
                           max_workers: int = 4,
                           start_services: bool = True) -> E2ERunSummary:
        """Run complete E2E test suite"""
        logger.info("🚀 Starting E2E Test Suite")
        
        try:
            # Step 1: Service orchestration
            if start_services:
                services_started = await self.orchestrator.start_services()
                if not services_started:
                    logger.error("Failed to start services - aborting E2E tests")
                    return self._create_error_summary("Service startup failed")
            
            # Step 2: Test discovery
            test_files = self.discovery.discover_e2e_tests()
            if not test_files:
                logger.warning("No E2E tests discovered")
                return self._create_error_summary("No tests found")
            
            # Step 3: Test execution
            if parallel and len(test_files) > 1:
                results = await self.executor.run_tests_parallel(test_files, max_workers)
            else:
                results = [self.executor._run_single_test(f) for f in test_files]
            
            # Step 4: Generate summary
            summary = self.reporter.generate_summary(results)
            
            # Step 5: Performance validation
            summary.performance_baseline_met = self.performance_tracker.check_performance(summary)
            
            # Step 6: Save reports
            self.reporter.save_json_report(summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"E2E test suite failed: {e}")
            return self._create_error_summary(str(e))
        
        finally:
            # Always cleanup
            if start_services:
                await self.orchestrator.stop_services()
    
    def _create_error_summary(self, error: str) -> E2ERunSummary:
        """Create error summary for failures"""
        return E2ERunSummary(
            start_time=time.time(),
            end_time=time.time(),
            total_duration=0.0,
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            error_tests=1,
            success_rate=0.0,
            results=[],
            performance_baseline_met=False,
            ci_exit_code=1
        )

async def main():
    """CLI entry point for E2E test runner"""
    parser = argparse.ArgumentParser(description="E2E Test Runner with CI/CD Integration")
    parser.add_argument("--parallel", action="store_true", default=True,
                       help="Run tests in parallel (default: True)")
    parser.add_argument("--sequential", action="store_true", 
                       help="Run tests sequentially")
    parser.add_argument("--workers", type=int, default=4,
                       help="Number of parallel workers (default: 4)")
    parser.add_argument("--no-services", action="store_true",
                       help="Skip service startup (assume services running)")
    parser.add_argument("--ci", action="store_true",
                       help="CI mode - optimized for CI/CD environments")
    
    args = parser.parse_args()
    
    # Configure for CI/CD
    if args.ci:
        logging.getLogger().setLevel(logging.WARNING)
        args.workers = min(args.workers, 2)  # Limit workers in CI
    
    # Create runner
    runner = E2ETestRunner()
    
    # Execute E2E suite
    parallel = not args.sequential
    start_services = not args.no_services
    
    summary = await runner.run_e2e_suite(
        parallel=parallel,
        max_workers=args.workers,
        start_services=start_services
    )
    
    # Report results
    runner.reporter.print_console_summary(summary)
    
    # Exit with appropriate code for CI/CD
    sys.exit(summary.ci_exit_code)

if __name__ == "__main__":
    asyncio.run(main())
