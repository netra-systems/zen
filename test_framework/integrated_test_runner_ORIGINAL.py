"""
Integrated Test Runner with Docker Orchestration
Provides specialized Docker orchestration features (Alpine isolation, file watching, service refresh)
while delegating basic test execution to unified_test_runner.py as SSOT
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.docker_orchestrator import DockerOrchestrator, TestEnvironment
from shared.isolated_environment import IsolatedEnvironment

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntegratedTestRunner:
    """Integrated test runner with Docker orchestration"""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.orchestrator = DockerOrchestrator()
        self.test_results: Dict[str, Any] = {}
        self.active_environments: List[TestEnvironment] = []
        
    def run_isolated_tests(
        self,
        test_suite: str,
        use_alpine: bool = True,
        parallel: bool = False,
        real_services: bool = True
    ) -> Dict[str, Any]:
        """Run tests in isolated Docker environment"""
        
        logger.info(f"Running {test_suite} tests in isolated environment")
        
        # Determine required services based on test suite
        services = self._get_required_services(test_suite)
        
        # Create isolated test environment
        test_env = self.orchestrator.create_test_environment(
            name=f"{test_suite}-tests",
            services=services,
            use_alpine=use_alpine
        )
        
        self.active_environments.append(test_env)
        
        try:
            # Get service URLs
            backend_url = self.orchestrator.get_service_url(test_env.id, "backend")
            auth_url = self.orchestrator.get_service_url(test_env.id, "auth")
            
            # Run tests against isolated environment
            results = self._run_test_suite(
                test_suite,
                env_vars={
                    "TEST_BACKEND_URL": backend_url,
                    "TEST_AUTH_URL": auth_url,
                    "TEST_ENV_ID": test_env.id,
                    "USE_REAL_SERVICES": str(real_services)
                },
                parallel=parallel
            )
            
            return results
            
        finally:
            # Cleanup environment
            if test_env.cleanup_on_exit:
                self.orchestrator.cleanup_environment(test_env.id)
                self.active_environments.remove(test_env)
                
    def run_parallel_test_environments(
        self,
        test_suites: List[str],
        use_alpine: bool = True
    ) -> Dict[str, Any]:
        """Run multiple test suites in parallel isolated environments"""
        
        logger.info(f"Running {len(test_suites)} test suites in parallel")
        
        with ThreadPoolExecutor(max_workers=len(test_suites)) as executor:
            futures = []
            
            for suite in test_suites:
                future = executor.submit(
                    self.run_isolated_tests,
                    suite,
                    use_alpine=use_alpine,
                    parallel=False
                )
                futures.append((suite, future))
                
            # Collect results
            results = {}
            for suite, future in futures:
                try:
                    results[suite] = future.result(timeout=600)  # 10 min timeout
                except Exception as e:
                    logger.error(f"Test suite {suite} failed: {e}")
                    results[suite] = {"status": "failed", "error": str(e)}
                    
        return results
        
    def refresh_and_test(
        self,
        services: List[str],
        test_suites: List[str],
        use_alpine: bool = False
    ) -> Dict[str, Any]:
        """Refresh dev services and run tests"""
        
        logger.info("Refreshing development services with latest changes")
        
        # Refresh services
        self.orchestrator.refresh_dev_services(services)
        
        # Wait for services to be healthy
        time.sleep(10)
        
        # Run test suites
        results = {}
        for suite in test_suites:
            results[suite] = self._run_test_suite(
                suite,
                env_vars={
                    "USE_DEV_SERVICES": "true"
                }
            )
            
        return results
        
    def _get_required_services(self, test_suite: str) -> List[str]:
        """Determine required services for a test suite"""
        
        service_map = {
            "unit": ["postgres", "redis"],
            "integration": ["postgres", "redis", "backend", "auth"],
            "api": ["postgres", "redis", "backend", "auth"],
            "e2e": ["postgres", "redis", "backend", "auth", "frontend"],
            "websocket": ["postgres", "redis", "backend"],
            "agent": ["postgres", "redis", "backend", "auth"],
            "performance": ["postgres", "redis", "backend", "auth"],
        }
        
        return service_map.get(test_suite, ["postgres", "redis", "backend"])
        
    def _run_test_suite(
        self,
        test_suite: str,
        env_vars: Optional[Dict[str, str]] = None,
        parallel: bool = False
    ) -> Dict[str, Any]:
        """Run a specific test suite using unified_test_runner.py as SSOT"""
        
        # Prepare environment
        test_env = os.environ.copy()
        if env_vars:
            test_env.update(env_vars)
            
        # Use unified_test_runner.py as SSOT for test execution
        cmd = [
            "python", 
            str(PROJECT_ROOT / "tests" / "unified_test_runner.py"),
            "--category", test_suite
        ]
        
        # Add parallel execution if requested
        if parallel:
            cmd.extend(["--parallel-execution"])
            
        # Use real services for orchestrated environments
        if env_vars and any(key.startswith("TEST_") for key in env_vars):
            cmd.extend(["--real-services"])
            
        # Run tests via unified runner
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                env=test_env,
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            duration = time.time() - start_time
            
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "duration": duration,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except Exception as e:
            return {
                "status": "error",
                "duration": time.time() - start_time,
                "error": str(e)
            }
            
    def run_continuous_integration(
        self,
        watch_paths: List[str],
        test_suites: List[str],
        use_alpine: bool = True
    ):
        """Run continuous integration with file watching"""
        
        logger.info("Starting continuous integration mode")
        
        # Import watchdog
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            logger.error("watchdog package required for CI mode")
            return
            
        class ChangeHandler(FileSystemEventHandler):
            def __init__(self, runner):
                self.runner = runner
                self.last_run = 0
                
            def on_modified(self, event):
                if event.is_directory:
                    return
                    
                # Debounce - wait at least 5 seconds between runs
                current_time = time.time()
                if current_time - self.last_run < 5:
                    return
                    
                self.last_run = current_time
                
                # Check if file is relevant
                file_path = Path(event.src_path)
                if file_path.suffix in ['.py', '.js', '.jsx', '.ts', '.tsx']:
                    logger.info(f"Change detected: {file_path}")
                    
                    # Determine affected services
                    services = []
                    if 'backend' in str(file_path) or 'netra_backend' in str(file_path):
                        services.append('backend')
                    if 'auth' in str(file_path) or 'auth_service' in str(file_path):
                        services.append('auth')
                    if 'frontend' in str(file_path):
                        services.append('frontend')
                        
                    if services:
                        # Refresh and test
                        self.runner.refresh_and_test(
                            services=services,
                            test_suites=test_suites,
                            use_alpine=use_alpine
                        )
                        
        # Setup file watcher
        handler = ChangeHandler(self)
        observer = Observer()
        
        for path in watch_paths:
            observer.schedule(handler, str(PROJECT_ROOT / path), recursive=True)
            
        observer.start()
        
        try:
            logger.info("Watching for changes... Press Ctrl+C to stop")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            logger.info("Stopping continuous integration")
            
        observer.join()
        
    def cleanup_all(self):
        """Clean up all active test environments"""
        
        for env in self.active_environments:
            try:
                self.orchestrator.cleanup_environment(env.id)
            except Exception as e:
                logger.error(f"Failed to cleanup environment {env.id}: {e}")
                
        self.active_environments.clear()


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description="Integrated test runner with Docker orchestration"
    )
    
    parser.add_argument(
        "--mode",
        choices=["isolated", "parallel", "refresh", "ci"],
        default="isolated",
        help="Execution mode"
    )
    
    parser.add_argument(
        "--suites",
        nargs="+",
        default=["unit"],
        help="Test suites to run"
    )
    
    parser.add_argument(
        "--services",
        nargs="+",
        default=["backend", "auth", "frontend"],
        help="Services to refresh (for refresh mode)"
    )
    
    parser.add_argument(
        "--alpine",
        action="store_true",
        default=True,
        help="Use Alpine-based images (default: True)"
    )
    
    parser.add_argument(
        "--real-services",
        action="store_true",
        default=True,
        help="Use real services instead of mocks"
    )
    
    parser.add_argument(
        "--watch-paths",
        nargs="+",
        default=["netra_backend", "auth_service", "frontend", "shared"],
        help="Paths to watch for CI mode"
    )
    
    args = parser.parse_args()
    
    runner = IntegratedTestRunner()
    
    try:
        if args.mode == "isolated":
            # Run tests in isolated environment
            for suite in args.suites:
                results = runner.run_isolated_tests(
                    suite,
                    use_alpine=args.alpine,
                    real_services=args.real_services
                )
                
                print(f"\n{suite} Results:")
                print(f"  Status: {results['status']}")
                print(f"  Duration: {results['duration']:.2f}s")
                
        elif args.mode == "parallel":
            # Run multiple suites in parallel
            results = runner.run_parallel_test_environments(
                args.suites,
                use_alpine=args.alpine
            )
            
            print("\nParallel Test Results:")
            for suite, result in results.items():
                print(f"  {suite}: {result['status']}")
                
        elif args.mode == "refresh":
            # Refresh services and test
            results = runner.refresh_and_test(
                services=args.services,
                test_suites=args.suites,
                use_alpine=args.alpine
            )
            
            print("\nRefresh and Test Results:")
            for suite, result in results.items():
                print(f"  {suite}: {result['status']}")
                
        elif args.mode == "ci":
            # Continuous integration mode
            runner.run_continuous_integration(
                watch_paths=args.watch_paths,
                test_suites=args.suites,
                use_alpine=args.alpine
            )
            
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        
    finally:
        runner.cleanup_all()
        

if __name__ == "__main__":
    main()