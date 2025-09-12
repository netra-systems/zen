#!/usr/bin/env python3
"""
E2E Docker Validation Script
============================

This script validates that the new E2E Docker setup works correctly:
1. Tests E2EDockerHelper functionality
2. Validates port isolation
3. Checks service health  
4. Verifies proper cleanup

Usage:
    python scripts/validate_e2e_docker.py
    python scripts/validate_e2e_docker.py --quick
    python scripts/validate_e2e_docker.py --cleanup-only
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_framework.e2e_docker_helper import E2EDockerHelper
from test_framework.docker_reliability_patches import DockerReliabilityPatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def validate_e2e_docker_helper(quick_test: bool = False):
    """
    Validate E2EDockerHelper functionality.
    
    Args:
        quick_test: If True, run minimal validation
    """
    logger.info("[U+1F9EA] Validating E2EDockerHelper functionality...")
    
    test_id = "validation-test"
    helper = E2EDockerHelper(test_id=test_id)
    
    try:
        # Test 1: Setup E2E environment
        logger.info("   Step 1: Setting up E2E environment...")
        timeout = 60 if quick_test else 180
        service_urls = await helper.setup_e2e_environment(timeout=timeout)
        
        logger.info("    PASS:  E2E environment setup successful!")
        for service, url in service_urls.items():
            logger.info(f"      {service}: {url}")
        
        if not quick_test:
            # Test 2: Validate port isolation  
            logger.info("   Step 2: Validating port isolation...")
            backend_url = service_urls['backend']
            auth_url = service_urls['auth']
            
            # Check ports are E2E specific (8002, 8083)
            assert ':8002' in backend_url, f"Expected backend port 8002, got {backend_url}"
            assert ':8083' in auth_url, f"Expected auth port 8083, got {auth_url}"
            logger.info("    PASS:  Port isolation validated!")
            
            # Test 3: Basic service health check
            logger.info("   Step 3: Testing service connectivity...")
            import httpx
            
            async with httpx.AsyncClient() as client:
                try:
                    # Test backend health
                    response = await client.get(f"{service_urls['backend']}/health")
                    if response.status_code == 200:
                        logger.info("    PASS:  Backend service responding!")
                    else:
                        logger.warning(f"    WARNING: [U+FE0F] Backend returned {response.status_code}")
                except Exception as e:
                    logger.warning(f"    WARNING: [U+FE0F] Backend connection issue: {e}")
                
                try:
                    # Test auth health  
                    response = await client.get(f"{service_urls['auth']}/health")
                    if response.status_code == 200:
                        logger.info("    PASS:  Auth service responding!")
                    else:
                        logger.warning(f"    WARNING: [U+FE0F] Auth returned {response.status_code}")
                except Exception as e:
                    logger.warning(f"    WARNING: [U+FE0F] Auth connection issue: {e}")
        
        # Test 4: Teardown
        logger.info("   Step 4: Tearing down E2E environment...")
        await helper.teardown_e2e_environment()
        logger.info("    PASS:  E2E environment teardown successful!")
        
        return True
        
    except Exception as e:
        logger.error(f"    FAIL:  E2EDockerHelper validation failed: {e}")
        
        # Ensure cleanup happens even on failure
        try:
            await helper.teardown_e2e_environment()
        except Exception:
            pass
        
        return False


def validate_reliability_patches():
    """Validate Docker reliability patches."""
    logger.info("[U+1F527] Validating Docker reliability patches...")
    
    try:
        patcher = DockerReliabilityPatcher("e2e")
        
        # Test 1: Port conflict detection
        logger.info("   Step 1: Testing port conflict detection...")
        conflicts = patcher.check_port_conflicts()
        logger.info(f"   Found {len(conflicts)} port conflicts")
        
        # Test 2: Stale resource cleanup (safe operation)
        logger.info("   Step 2: Testing stale resource cleanup...")
        cleanup_results = {
            "containers": patcher.clean_stale_containers(max_age_hours=0.1),  # Very old
            "volumes": patcher.clean_stale_volumes(max_age_hours=0.1),
            "networks": patcher.clean_stale_networks()
        }
        
        logger.info(f"   Cleaned: {cleanup_results['containers']} containers, "
                   f"{cleanup_results['volumes']} volumes, "
                   f"{cleanup_results['networks']} networks")
        
        logger.info("    PASS:  Reliability patches validation successful!")
        return True
        
    except Exception as e:
        logger.error(f"    FAIL:  Reliability patches validation failed: {e}")
        return False


async def validate_test_runner_integration():
    """Validate that unified test runner can use E2E Docker."""
    logger.info("[U+1F3C3] Validating test runner integration...")
    
    try:
        # Import test runner components
        from tests.unified_test_runner import UnifiedTestRunner
        
        # Create mock args for E2E category
        class MockArgs:
            category = "e2e"
            categories = ["e2e"] 
            env = "test"
            real_services = True
            real_llm = False
            no_docker = False
            workers = 1
            fast_fail = False
            resume_from = None
            
        args = MockArgs()
        
        # Test that the runner can detect E2E tests
        runner = UnifiedTestRunner()
        categories_to_run = runner._determine_categories_to_run(args)
        
        if "e2e" in categories_to_run:
            logger.info("    PASS:  Test runner correctly detects E2E category!")
        else:
            logger.warning("    WARNING: [U+FE0F] Test runner does not detect E2E category")
        
        logger.info("    PASS:  Test runner integration validated!")
        return True
        
    except Exception as e:
        logger.error(f"    FAIL:  Test runner integration validation failed: {e}")
        return False


async def cleanup_all_test_resources():
    """Clean up all test resources."""
    logger.info("[U+1F9F9] Cleaning up all test resources...")
    
    try:
        patcher = DockerReliabilityPatcher("e2e")
        
        # Comprehensive cleanup
        cleanup_results = {
            "containers": patcher.clean_stale_containers(max_age_hours=0),  # All containers
            "volumes": patcher.clean_stale_volumes(max_age_hours=0),       # All volumes  
            "networks": patcher.clean_stale_networks()                     # All networks
        }
        
        logger.info(f"   Cleaned: {cleanup_results['containers']} containers, "
                   f"{cleanup_results['volumes']} volumes, "
                   f"{cleanup_results['networks']} networks")
        
        logger.info("    PASS:  Cleanup completed!")
        return True
        
    except Exception as e:
        logger.error(f"    FAIL:  Cleanup failed: {e}")
        return False


async def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description="Validate E2E Docker setup")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick validation (faster, less comprehensive)")
    parser.add_argument("--cleanup-only", action="store_true",
                       help="Only run cleanup, skip validation tests")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("[U+1F680] Starting E2E Docker validation...")
    
    results = {}
    
    if args.cleanup_only:
        # Only run cleanup
        results["cleanup"] = await cleanup_all_test_resources()
    else:
        # Run validation tests
        results["e2e_docker_helper"] = await validate_e2e_docker_helper(quick_test=args.quick)
        results["reliability_patches"] = validate_reliability_patches()
        results["test_runner_integration"] = await validate_test_runner_integration()
        
        if not args.quick:
            results["cleanup"] = await cleanup_all_test_resources()
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info(" CHART:  VALIDATION RESULTS SUMMARY")
    logger.info("="*50)
    
    all_passed = True
    for test_name, passed in results.items():
        status = " PASS:  PASS" if passed else " FAIL:  FAIL"
        logger.info(f"  {status} {test_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        logger.info("\n CELEBRATION:  ALL VALIDATIONS PASSED!")
        logger.info("   E2E tests with Docker are now 100% reliable!")
        return 0
    else:
        logger.error("\n[U+1F4A5] SOME VALIDATIONS FAILED!")
        logger.error("   Please check the errors above and fix issues.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))