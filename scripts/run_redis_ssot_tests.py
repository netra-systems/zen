#!/usr/bin/env python3
"""
Redis SSOT Test Suite Runner

BUSINESS VALUE JUSTIFICATION:
- Segment: Platform/Internal
- Business Goal: Chat Functionality Reliability (90% of platform value) 
- Value Impact: Validates Redis SSOT compliance to prevent WebSocket 1011 errors
- Strategic Impact: Protects $500K+ ARR by ensuring reliable chat functionality

This script runs the complete Redis SSOT test suite to validate:
1. SSOT compliance and legacy removal
2. WebSocket 1011 error prevention
3. Performance characteristics
4. Production readiness in staging

Usage:
    python scripts/run_redis_ssot_tests.py [--category CATEGORY] [--staging] [--performance]
"""

import asyncio
import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

class RedisSSotTestRunner:
    """Redis SSOT test suite runner."""
    
    def __init__(self):
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
    
    def run_test_file(self, test_file: Path, test_name: str, env_vars: Dict[str, str] = None) -> bool:
        """Run a single test file and return success status."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Running {test_name}")
        logger.info(f"File: {test_file}")
        logger.info(f"{'='*60}")
        
        # Build command
        cmd = [sys.executable, str(test_file), "-v", "--tb=short"]
        
        # Set environment variables
        env = {}
        if env_vars:
            env.update(env_vars)
        
        try:
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                env={**env, **dict(os.environ)} if env else None,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            duration = time.time() - start_time
            
            # Parse result
            success = result.returncode == 0
            
            self.test_results[test_name] = {
                "success": success,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
            if success:
                logger.info(f"✅ {test_name} PASSED ({duration:.2f}s)")
                self.passed_tests += 1
            else:
                logger.error(f"❌ {test_name} FAILED ({duration:.2f}s)")
                logger.error(f"STDOUT:\n{result.stdout}")
                logger.error(f"STDERR:\n{result.stderr}")
                self.failed_tests += 1
            
            self.total_tests += 1
            return success
            
        except subprocess.TimeoutExpired:
            logger.error(f"❌ {test_name} TIMEOUT (>300s)")
            self.test_results[test_name] = {"success": False, "duration": 300, "error": "timeout"}
            self.failed_tests += 1
            self.total_tests += 1
            return False
        except Exception as e:
            logger.error(f"❌ {test_name} ERROR: {e}")
            self.test_results[test_name] = {"success": False, "duration": 0, "error": str(e)}
            self.failed_tests += 1
            self.total_tests += 1
            return False
    
    def run_mission_critical_tests(self) -> bool:
        """Run mission critical Redis SSOT tests."""
        logger.info("\n🎯 MISSION CRITICAL TESTS - Redis SSOT Compliance")
        
        mission_critical_tests = [
            (
                PROJECT_ROOT / "tests/mission_critical/test_redis_ssot_compliance_suite.py",
                "Redis SSOT Compliance Suite",
                {"TESTING": "true", "ENVIRONMENT": "test", "TEST_DISABLE_REDIS": "false"}
            ),
            (
                PROJECT_ROOT / "tests/mission_critical/test_redis_websocket_1011_regression.py", 
                "WebSocket 1011 Regression Prevention",
                {"TESTING": "true", "ENVIRONMENT": "test", "TEST_DISABLE_REDIS": "false"}
            )
        ]
        
        all_passed = True
        for test_file, test_name, env_vars in mission_critical_tests:
            if test_file.exists():
                success = self.run_test_file(test_file, test_name, env_vars)
                all_passed = all_passed and success
            else:
                logger.error(f"❌ Test file not found: {test_file}")
                all_passed = False
        
        return all_passed
    
    def run_integration_tests(self) -> bool:
        """Run integration tests (non-Docker)."""
        logger.info("\n🔗 INTEGRATION TESTS - Redis + WebSocket Integration")
        
        integration_tests = [
            (
                PROJECT_ROOT / "tests/integration/test_redis_websocket_integration_no_docker.py",
                "Redis WebSocket Integration (No Docker)",
                {"TESTING": "true", "ENVIRONMENT": "test", "TEST_DISABLE_REDIS": "false"}
            )
        ]
        
        all_passed = True
        for test_file, test_name, env_vars in integration_tests:
            if test_file.exists():
                success = self.run_test_file(test_file, test_name, env_vars)
                all_passed = all_passed and success
            else:
                logger.error(f"❌ Test file not found: {test_file}")
                all_passed = False
        
        return all_passed
    
    def run_performance_tests(self) -> bool:
        """Run performance validation tests."""
        logger.info("\n⚡ PERFORMANCE TESTS - Redis Performance Validation")
        
        performance_tests = [
            (
                PROJECT_ROOT / "tests/performance/test_redis_performance_validation.py",
                "Redis Performance Validation",
                {"TESTING": "true", "ENVIRONMENT": "test", "TEST_DISABLE_REDIS": "false"}
            )
        ]
        
        all_passed = True
        for test_file, test_name, env_vars in performance_tests:
            if test_file.exists():
                success = self.run_test_file(test_file, test_name, env_vars)
                all_passed = all_passed and success
            else:
                logger.error(f"❌ Test file not found: {test_file}")
                all_passed = False
        
        return all_passed
    
    def run_staging_tests(self) -> bool:
        """Run GCP staging validation tests."""
        logger.info("\n🚀 STAGING TESTS - GCP Production Readiness")
        
        staging_tests = [
            (
                PROJECT_ROOT / "tests/e2e/test_redis_gcp_staging_validation.py",
                "GCP Staging Redis Validation",
                {
                    "ENVIRONMENT": "staging",
                    "GCP_PROJECT": "netra-staging",
                    "BACKEND_URL": "https://staging.netrasystems.ai",
                    "REDIS_URL": "redis://10.0.0.3:6379/0"
                }
            )
        ]
        
        all_passed = True
        for test_file, test_name, env_vars in staging_tests:
            if test_file.exists():
                success = self.run_test_file(test_file, test_name, env_vars)
                all_passed = all_passed and success
            else:
                logger.error(f"❌ Test file not found: {test_file}")
                all_passed = False
        
        return all_passed
    
    def print_summary(self):
        """Print test execution summary."""
        logger.info("\n" + "="*80)
        logger.info("REDIS SSOT TEST SUITE SUMMARY")
        logger.info("="*80)
        
        logger.info(f"Total Tests: {self.total_tests}")
        logger.info(f"Passed: {self.passed_tests} ✅")
        logger.info(f"Failed: {self.failed_tests} ❌")
        
        if self.failed_tests == 0:
            logger.info("\n🎉 ALL REDIS SSOT TESTS PASSED!")
            logger.info("✅ SSOT compliance validated")
            logger.info("✅ WebSocket 1011 errors prevented") 
            logger.info("✅ Chat functionality protected")
            logger.info("✅ Golden path: users login → get AI responses ✅")
        else:
            logger.error(f"\n💥 {self.failed_tests} TESTS FAILED!")
            logger.error("❌ Redis SSOT compliance issues detected")
            logger.error("❌ Chat functionality may be at risk")
        
        # Detailed results
        logger.info("\nDetailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            duration = result.get("duration", 0)
            logger.info(f"  {status} {test_name} ({duration:.2f}s)")
        
        logger.info("="*80)


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Redis SSOT Test Suite Runner")
    parser.add_argument(
        "--category",
        choices=["mission_critical", "integration", "performance", "staging", "all"],
        default="all",
        help="Test category to run"
    )
    parser.add_argument(
        "--staging",
        action="store_true",
        help="Run staging environment tests"
    )
    parser.add_argument(
        "--performance", 
        action="store_true",
        help="Include performance tests"
    )
    
    args = parser.parse_args()
    
    runner = RedisSSotTestRunner()
    
    logger.info("🚀 Starting Redis SSOT Test Suite")
    logger.info("Business Goal: Protect Chat Functionality (90% of platform value)")
    logger.info("Technical Goal: Validate SSOT compliance and prevent WebSocket 1011 errors")
    
    overall_success = True
    
    # Run tests based on category
    if args.category == "all" or args.category == "mission_critical":
        success = runner.run_mission_critical_tests()
        overall_success = overall_success and success
    
    if args.category == "all" or args.category == "integration":
        success = runner.run_integration_tests()
        overall_success = overall_success and success
    
    if args.category == "all" or args.category == "performance" or args.performance:
        success = runner.run_performance_tests()
        overall_success = overall_success and success
    
    if args.category == "staging" or args.staging:
        success = runner.run_staging_tests()
        overall_success = overall_success and success
    
    # Print summary
    runner.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    import os
    main()