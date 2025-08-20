"""
Test runner for dev launcher startup E2E tests.

Executes comprehensive startup tests with proper setup and teardown.
Follows 300-line file limit and 8-line function limit constraints.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from .dev_launcher_test_fixtures import TestEnvironmentManager


class DevStartupTestRunner:
    """Runs dev launcher startup tests with proper environment setup."""
    
    def __init__(self):
        self.test_env = TestEnvironmentManager()
        self.test_results: Dict[str, bool] = {}
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup logging for test execution."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    async def setup_test_environment(self) -> bool:
        """Setup test environment for startup testing."""
        try:
            await self.test_env.initialize()
            self.test_env.setup_test_db()
            self.test_env.setup_test_redis()
            self.test_env.setup_test_secrets()
            
            self.logger.info("Test environment setup completed")
            return True
        except Exception as e:
            self.logger.error(f"Test environment setup failed: {e}")
            return False
    
    def run_startup_tests(self) -> bool:
        """Run all startup tests."""
        test_files = [
            "test_dev_launcher_startup.py",
            "test_service_health_checks.py", 
            "test_database_connections.py"
        ]
        
        success = True
        test_dir = Path(__file__).parent
        
        for test_file in test_files:
            test_path = test_dir / test_file
            if test_path.exists():
                result = self._run_single_test_file(str(test_path))
                self.test_results[test_file] = result
                if not result:
                    success = False
            else:
                self.logger.warning(f"Test file not found: {test_file}")
                self.test_results[test_file] = False
                success = False
        
        return success
    
    def _run_single_test_file(self, test_path: str) -> bool:
        """Run single test file with pytest."""
        try:
            self.logger.info(f"Running tests in {test_path}")
            
            exit_code = pytest.main([
                test_path,
                "-v",
                "--tb=short",
                "--no-header",
                "--disable-warnings"
            ])
            
            success = exit_code == 0
            if success:
                self.logger.info(f"Tests passed: {test_path}")
            else:
                self.logger.error(f"Tests failed: {test_path}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error running tests in {test_path}: {e}")
            return False
    
    def cleanup_test_environment(self) -> None:
        """Cleanup test environment."""
        try:
            self.test_env.cleanup()
            self.logger.info("Test environment cleanup completed")
        except Exception as e:
            self.logger.error(f"Test environment cleanup failed: {e}")
    
    def print_test_summary(self) -> None:
        """Print test execution summary."""
        print("\n" + "="*60)
        print("DEV LAUNCHER STARTUP TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        print(f"Total test files: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\nDetailed Results:")
        for test_file, result in self.test_results.items():
            status = "PASS" if result else "FAIL"
            print(f"  {test_file:<35} : {status}")
        
        print("="*60)


async def main():
    """Main test execution function."""
    runner = DevStartupTestRunner()
    
    try:
        # Setup test environment
        setup_success = await runner.setup_test_environment()
        if not setup_success:
            print("❌ Test environment setup failed")
            return 1
        
        print("✅ Test environment setup successful")
        
        # Run tests
        print("🚀 Starting dev launcher startup tests...")
        test_success = runner.run_startup_tests()
        
        # Print summary
        runner.print_test_summary()
        
        return 0 if test_success else 1
        
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1
    finally:
        runner.cleanup_test_environment()


def run_quick_smoke_test() -> bool:
    """Run quick smoke test for dev launcher."""
    try:
        test_dir = Path(__file__).parent
        exit_code = pytest.main([
            str(test_dir / "test_dev_launcher_startup.py::test_dev_launcher_starts_successfully"),
            "-v",
            "--tb=short"
        ])
        return exit_code == 0
    except Exception as e:
        print(f"Smoke test failed: {e}")
        return False


def run_database_tests_only() -> bool:
    """Run only database connection tests."""
    try:
        test_dir = Path(__file__).parent
        exit_code = pytest.main([
            str(test_dir / "test_database_connections.py"),
            "-v",
            "--tb=short"
        ])
        return exit_code == 0
    except Exception as e:
        print(f"Database tests failed: {e}")
        return False


def run_health_tests_only() -> bool:
    """Run only health check tests."""
    try:
        test_dir = Path(__file__).parent
        exit_code = pytest.main([
            str(test_dir / "test_service_health_checks.py"),
            "-v",
            "--tb=short"
        ])
        return exit_code == 0
    except Exception as e:
        print(f"Health check tests failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Dev launcher startup test runner")
    parser.add_argument("--smoke", action="store_true", help="Run smoke test only")
    parser.add_argument("--database", action="store_true", help="Run database tests only")
    parser.add_argument("--health", action="store_true", help="Run health tests only")
    
    args = parser.parse_args()
    
    if args.smoke:
        success = run_quick_smoke_test()
        sys.exit(0 if success else 1)
    elif args.database:
        success = run_database_tests_only()
        sys.exit(0 if success else 1)
    elif args.health:
        success = run_health_tests_only()
        sys.exit(0 if success else 1)
    else:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)