#!/usr/bin/env python3
"""
Test script to verify the improved service health checking mechanism.
This script can be run independently to test service availability detection.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_service_availability():
    """Test the service availability checker."""
    logger.info("Testing improved service health checking mechanism")
    
    try:
        # Import the service availability checker
        from tests.e2e.service_availability import get_service_availability
        
        # Check service availability
        availability = await get_service_availability(timeout=10.0)
        
        print("\n" + "="*60)
        print("SERVICE AVAILABILITY TEST RESULTS")
        print("="*60)
        
        print(f"Environment Configuration:")
        print(f"  USE_REAL_SERVICES: {availability.use_real_services}")
        print(f"  USE_REAL_LLM: {availability.use_real_llm}")
        print()
        
        print("Database Services:")
        for service in [availability.postgresql, availability.redis, availability.clickhouse]:
            status = "[OK] Available" if service.available else "[FAIL] Unavailable"
            print(f"  {status} {service.name.upper()}: {service.details}")
            if service.error:
                print(f"    Error: {service.error}")
        print()
        
        print("API Services:")
        for service in [availability.openai_api, availability.anthropic_api]:
            status = "[OK] Available" if service.available else "[FAIL] Unavailable"
            print(f"  {status} {service.name.upper()}: {service.details}")
            if service.error:
                print(f"    Error: {service.error}")
        print()
        
        print("Summary:")
        print(f"  Real databases available: {availability.has_real_databases}")
        print(f"  Real LLM APIs available: {availability.has_real_llm_apis}")
        print()
        
        # Also test the HTTP service health checker
        print("Testing HTTP Service Health Checker:")
        print("-" * 40)
        
        from tests.e2e.health_service_checker import ServiceHealthChecker
        from tests.e2e.health_check_core import SERVICE_ENDPOINTS
        
        health_checker = ServiceHealthChecker()
        
        # Test each service endpoint configuration
        for service_name, config in SERVICE_ENDPOINTS.items():
            print(f"\nTesting {service_name.upper()} service:")
            result = await health_checker.check_service_endpoint(service_name, config)
            
            status = "[OK] Healthy" if result.is_healthy() else "[FAIL] Unhealthy"
            print(f"  {status} Status: {result.status}")
            print(f"  Response Time: {result.response_time_ms:.1f}ms")
            print(f"  Details: {result.details}")
            if result.error:
                print(f"  Error: {result.error}")
        
        print("\n" + "="*60)
        print("TEST COMPLETED")
        print("="*60)
        
        return True
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        print(f"\n[FAIL] Failed to import required modules: {e}")
        print("Make sure you're running from the project root directory")
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error during service availability test: {e}")
        print(f"\n[FAIL] Test failed with error: {e}")
        return False

async def test_conftest_validator():
    """Test the E2EEnvironmentValidator from conftest.py"""
    logger.info("Testing E2EEnvironmentValidator")
    
    try:
        from tests.conftest import E2EEnvironmentValidator
        
        print("\n" + "="*60)
        print("E2E ENVIRONMENT VALIDATOR TEST")
        print("="*60)
        
        # Test service availability
        service_status = await E2EEnvironmentValidator.validate_services_available()
        
        print("Service Status Results:")
        for service, status in service_status.items():
            status_text = "[OK] Available" if status else "[FAIL] Unavailable"
            print(f"  {status_text} {service}")
        
        print()
        
        # Test environment variables
        env_status = E2EEnvironmentValidator.validate_environment_variables()
        
        print("Environment Variables:")
        for var, status in env_status.items():
            status_text = "[OK] Set" if status else "[FAIL] Missing"
            print(f"  {status_text} {var}")
        
        print("\n" + "="*60)
        print("VALIDATOR TEST COMPLETED")
        print("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"E2E validator test failed: {e}")
        print(f"\n[FAIL] Validator test failed: {e}")
        return False

async def main():
    """Run all service health tests."""
    print("Service Health Checking Test Suite")
    print("="*60)
    
    # Test 1: Service Availability Checker
    print("\n[1] Testing Service Availability Checker...")
    success1 = await test_service_availability()
    
    # Test 2: Conftest E2E Environment Validator
    print("\n[2] Testing E2E Environment Validator...")
    success2 = await test_conftest_validator()
    
    # Summary
    print("\n" + "="*60)
    print("FINAL TEST RESULTS")
    print("="*60)
    
    tests = [
        ("Service Availability Checker", success1),
        ("E2E Environment Validator", success2)
    ]
    
    for test_name, success in tests:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {test_name}")
    
    overall_success = all(success for _, success in tests)
    
    if overall_success:
        print("\n[SUCCESS] All tests passed! Service health checking mechanism is working correctly.")
        return 0
    else:
        print("\n[WARNING] Some tests failed. Please check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)