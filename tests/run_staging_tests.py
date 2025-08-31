#!/usr/bin/env python3
"""
Staging E2E Test Runner

This script runs E2E tests against the deployed staging environment.
It validates that staging services are accessible and functioning correctly.

Usage:
    python tests/run_staging_tests.py [options]
    
Options:
    --quick     Run only quick health checks
    --full      Run full test suite including slow tests
    --auth      Run only authentication tests
    --api       Run only API tests
    --ws        Run only WebSocket tests
    
Environment Variables Required:
    E2E_BYPASS_KEY - Key for auth bypass (simulates OAuth)
    ENVIRONMENT    - Must be set to "staging"
"""

import asyncio
import os
import sys
import argparse
import logging
from pathlib import Path
import subprocess
from typing import List, Optional
import json
import time

# Fix Windows Unicode encoding issues
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.e2e.staging_config import get_staging_config
from tests.e2e.staging_auth_client import test_staging_auth
from tests.e2e.staging_websocket_client import test_staging_websocket

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StagingTestRunner:
    """Runner for staging E2E tests."""
    
    def __init__(self):
        """Initialize test runner."""
        self.config = None
        self.test_results = []
        
    def validate_environment(self) -> bool:
        """Validate environment is set up for staging tests."""
        issues = []
        
        # Check E2E bypass key
        if not os.getenv("E2E_BYPASS_KEY"):
            issues.append("E2E_BYPASS_KEY not set - required for auth bypass")
            
        # Check environment setting
        if os.getenv("ENVIRONMENT") != "staging":
            logger.warning("ENVIRONMENT not set to 'staging', setting it now")
            os.environ["ENVIRONMENT"] = "staging"
        
        if issues:
            logger.error("Environment validation failed:")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False
            
        logger.info("[OK] Environment validated for staging tests")
        return True
    
    async def test_connectivity(self) -> bool:
        """Test basic connectivity to staging services."""
        logger.info("Testing connectivity to staging services...")
        
        try:
            self.config = get_staging_config()
            
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                for service, url in self.config.urls.health_endpoints.items():
                    try:
                        start = time.time()
                        response = await client.get(url)
                        elapsed = time.time() - start
                        
                        if response.status_code == 200:
                            logger.info(f"  [OK] {service}: OK ({elapsed:.2f}s)")
                        else:
                            logger.warning(f"  [WARN] {service}: {response.status_code} ({elapsed:.2f}s)")
                            
                    except Exception as e:
                        logger.error(f"  [FAIL] {service}: {str(e)}")
                        return False
                        
            return True
            
        except Exception as e:
            logger.error(f"Connectivity test failed: {e}")
            return False
    
    async def run_quick_tests(self) -> bool:
        """Run quick smoke tests."""
        logger.info("\n=== Running Quick Staging Tests ===")
        
        all_passed = True
        
        # Test auth
        logger.info("\n1. Testing Authentication...")
        auth_passed = await test_staging_auth()
        self.test_results.append(("Authentication", auth_passed))
        all_passed = all_passed and auth_passed
        
        # Test WebSocket
        logger.info("\n2. Testing WebSocket...")
        ws_passed = await test_staging_websocket()
        self.test_results.append(("WebSocket", ws_passed))
        all_passed = all_passed and ws_passed
        
        return all_passed
    
    def run_pytest_suite(self, markers: Optional[List[str]] = None) -> bool:
        """Run pytest test suite."""
        logger.info("\n=== Running Pytest Suite ===")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/e2e/test_staging_e2e_comprehensive.py",
            "-v",
            "--tb=short",
            "--color=yes"
        ]
        
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=False)
        
        passed = result.returncode == 0
        self.test_results.append(("Pytest Suite", passed))
        
        return passed
    
    def print_summary(self) -> None:
        """Print test summary."""
        logger.info("\n" + "=" * 50)
        logger.info("STAGING TEST SUMMARY")
        logger.info("=" * 50)
        
        for test_name, passed in self.test_results:
            status = "✓ PASSED" if passed else "✗ FAILED"
            logger.info(f"{test_name}: {status}")
        
        total = len(self.test_results)
        passed = sum(1 for _, p in self.test_results if p)
        
        logger.info("-" * 50)
        logger.info(f"Total: {passed}/{total} passed")
        
        if passed == total:
            logger.info("🎉 All staging tests passed!")
        else:
            logger.error(f"⚠️  {total - passed} test(s) failed")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run staging E2E tests")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    parser.add_argument("--full", action="store_true", help="Run full test suite")
    parser.add_argument("--auth", action="store_true", help="Run auth tests only")
    parser.add_argument("--api", action="store_true", help="Run API tests only")  
    parser.add_argument("--ws", action="store_true", help="Run WebSocket tests only")
    parser.add_argument("--skip-connectivity", action="store_true", help="Skip connectivity check")
    
    args = parser.parse_args()
    
    runner = StagingTestRunner()
    
    # Validate environment
    if not runner.validate_environment():
        logger.error("\nPlease set required environment variables:")
        logger.error("  export E2E_BYPASS_KEY=<your-key>")
        logger.error("  export ENVIRONMENT=staging")
        return 1
    
    # Test connectivity
    if not args.skip_connectivity:
        if not await runner.test_connectivity():
            logger.error("\nCannot connect to staging services")
            logger.error("Ensure staging environment is deployed and accessible")
            return 1
    
    # Run tests based on arguments
    all_passed = True
    
    if args.quick or (not args.full and not args.auth and not args.api and not args.ws):
        # Default to quick tests
        all_passed = await runner.run_quick_tests()
        
    if args.full:
        # Run full pytest suite
        all_passed = runner.run_pytest_suite() and all_passed
        
    if args.auth:
        # Run auth-specific tests
        all_passed = runner.run_pytest_suite(["staging", "auth"]) and all_passed
        
    if args.api:
        # Run API-specific tests
        all_passed = runner.run_pytest_suite(["staging", "api"]) and all_passed
        
    if args.ws:
        # Run WebSocket-specific tests
        all_passed = runner.run_pytest_suite(["staging", "websocket"]) and all_passed
    
    # Print summary
    runner.print_summary()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)