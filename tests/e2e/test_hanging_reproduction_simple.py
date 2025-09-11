"""Simple E2E Hanging Reproduction Test

This is a focused test to reproduce the exact hanging behavior observed
in E2E tests when using RealServicesManager.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Critical Infrastructure
- Business Goal: Identify and fix E2E test hanging that blocks deployments
- Value Impact: Enable reliable CI/CD pipeline execution
- Revenue Impact: Prevent deployment delays costing $500+ per hour

Test Strategy:
- Minimal reproduction case focusing on RealServicesManager startup
- Uses same pattern as failing E2E tests
- Should hang or timeout to demonstrate the issue
- No complex logic - just pure reproduction

CRITICAL: This test should FAIL/TIMEOUT initially to prove the hanging issue exists
"""

import asyncio
import pytest
import time
from typing import Dict, Any

from tests.e2e.real_services_manager import RealServicesManager
from tests.e2e.enforce_real_services import E2EServiceValidator


class TestHangingReproductionSimple:
    """Simple reproduction of E2E hanging behavior"""
    
    def setup_method(self):
        """Setup exactly like the failing E2E test"""
        # Initialize real services exactly like test_auth_jwt_critical.py
        E2EServiceValidator.enforce_real_services()
        self.services_manager = RealServicesManager()
    
    def teardown_method(self):
        """Cleanup"""
        if hasattr(self, 'services_manager'):
            self.services_manager.cleanup()
    
    @pytest.mark.e2e
    def test_simple_hanging_reproduction(self):
        """Minimal reproduction of hanging behavior in RealServicesManager startup"""
        
        print("Starting hanging reproduction test...")
        start_time = time.time()
        
        async def _test():
            print("Calling start_all_services...")
            
            # This is the exact call that hangs in real E2E tests
            await self.services_manager.start_all_services(skip_frontend=True)
            
            print("start_all_services completed successfully")
        
        try:
            # Use timeout to prevent infinite hanging in test environment
            # In real E2E tests, this hangs indefinitely
            asyncio.run(asyncio.wait_for(_test(), timeout=60.0))
            
            elapsed_time = time.time() - start_time
            print(f"Test completed in {elapsed_time:.2f} seconds")
            
            # If we get here without timeout, the hanging issue may be resolved
            # or may not reproduce in this specific environment
            print("SUCCESS: No hanging detected in this run")
            
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            print(f"HANGING DETECTED: Test hung for {elapsed_time:.2f} seconds")
            pytest.fail(f"RealServicesManager.start_all_services() hung for {elapsed_time:.2f}s - HANGING BEHAVIOR CONFIRMED")
        
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"Test failed with error after {elapsed_time:.2f} seconds: {e}")
            # Errors are acceptable - hanging is the main concern
            if elapsed_time > 30.0:
                pytest.fail(f"Test took {elapsed_time:.2f}s before failing - possible hanging before error")
    
    @pytest.mark.e2e
    def test_health_check_hanging_reproduction(self):
        """Reproduce hanging in health check process"""
        
        print("Testing health check hanging...")
        start_time = time.time()
        
        async def _test():
            print("Calling check_all_service_health...")
            
            # Test the health checking process specifically
            health_result = await self.services_manager.check_all_service_health()
            
            print(f"Health check completed: {health_result}")
        
        try:
            asyncio.run(asyncio.wait_for(_test(), timeout=30.0))
            
            elapsed_time = time.time() - start_time
            print(f"Health check completed in {elapsed_time:.2f} seconds")
            
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            print(f"HANGING DETECTED: Health check hung for {elapsed_time:.2f} seconds")
            pytest.fail(f"Health check hung for {elapsed_time:.2f}s - HANGING BEHAVIOR CONFIRMED")
        
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"Health check failed after {elapsed_time:.2f} seconds: {e}")
    
    @pytest.mark.e2e
    def test_service_wait_hanging_reproduction(self):
        """Reproduce hanging in service wait process"""
        
        print("Testing service wait hanging...")
        start_time = time.time()
        
        async def _test():
            print("Testing _wait_for_services_healthy...")
            
            # Test the wait process that might hang
            try:
                await self.services_manager._wait_for_services_healthy(timeout=10.0)
                print("Wait for services completed")
            except Exception as e:
                print(f"Wait for services failed: {e}")
                # Failure is acceptable, hanging is not
        
        try:
            asyncio.run(asyncio.wait_for(_test(), timeout=20.0))
            
            elapsed_time = time.time() - start_time
            print(f"Service wait test completed in {elapsed_time:.2f} seconds")
            
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            print(f"HANGING DETECTED: Service wait hung for {elapsed_time:.2f} seconds")
            pytest.fail(f"Service wait hung for {elapsed_time:.2f}s - HANGING BEHAVIOR CONFIRMED")
    
    @pytest.mark.e2e  
    def test_synchronous_launch_hanging_reproduction(self):
        """Reproduce hanging in synchronous launch method"""
        
        print("Testing synchronous launch hanging...")
        start_time = time.time()
        
        # Test the synchronous method that might have event loop issues
        try:
            # This method has complex event loop handling that might hang
            result = self.services_manager.launch_dev_environment()
            
            elapsed_time = time.time() - start_time
            print(f"Synchronous launch completed in {elapsed_time:.2f} seconds: {result}")
            
            # Should complete quickly for synchronous interface
            if elapsed_time > 30.0:
                pytest.fail(f"Synchronous launch took {elapsed_time:.2f}s - possible hanging")
                
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"Synchronous launch failed after {elapsed_time:.2f} seconds: {e}")
            
            # If it takes too long even to fail, that indicates hanging
            if elapsed_time > 30.0:
                pytest.fail(f"Synchronous launch hung for {elapsed_time:.2f}s before failing")


class TestSpecificHangingScenarios:
    """Test specific scenarios that might cause hanging"""
    
    def setup_method(self):
        """Setup for specific scenario testing"""
        E2EServiceValidator.enforce_real_services()
        self.manager = RealServicesManager()
    
    def teardown_method(self):
        """Cleanup"""
        if hasattr(self, 'manager'):
            self.manager.cleanup()
    
    @pytest.mark.e2e
    def test_docker_related_hanging(self):
        """Test if hanging is related to Docker operations"""
        
        print("Testing Docker-related hanging scenarios...")
        start_time = time.time()
        
        async def _test():
            # Test the local service startup which might involve Docker
            result = await self.manager._start_local_services(skip_frontend=True)
            print(f"Local services startup result: {result}")
        
        try:
            asyncio.run(asyncio.wait_for(_test(), timeout=30.0))
            
            elapsed_time = time.time() - start_time
            print(f"Docker-related test completed in {elapsed_time:.2f} seconds")
            
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            print(f"HANGING DETECTED: Docker operations hung for {elapsed_time:.2f} seconds")
            pytest.fail(f"Docker operations hung for {elapsed_time:.2f}s - DOCKER HANGING CONFIRMED")
    
    @pytest.mark.e2e
    def test_http_client_hanging(self):
        """Test if hanging is related to HTTP client initialization/usage"""
        
        print("Testing HTTP client hanging scenarios...")
        start_time = time.time()
        
        async def _test():
            # Test HTTP client initialization and usage
            await self.manager._ensure_http_client()
            print("HTTP client initialized")
            
            # Test a simple HTTP operation
            if self.manager._http_client:
                try:
                    response = await self.manager._http_client.get("http://httpbin.org/status/200", timeout=5.0)
                    print(f"HTTP test successful: {response.status_code}")
                except Exception as e:
                    print(f"HTTP test failed: {e}")
        
        try:
            asyncio.run(asyncio.wait_for(_test(), timeout=15.0))
            
            elapsed_time = time.time() - start_time
            print(f"HTTP client test completed in {elapsed_time:.2f} seconds")
            
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            print(f"HANGING DETECTED: HTTP client operations hung for {elapsed_time:.2f} seconds")
            pytest.fail(f"HTTP client hung for {elapsed_time:.2f}s - HTTP CLIENT HANGING CONFIRMED")


if __name__ == "__main__":
    print("Running hanging reproduction tests...")
    print("These tests are designed to identify hanging behavior in RealServicesManager")
    print("Expected behavior: Tests should either pass quickly or timeout/fail to demonstrate hanging")
    
    pytest.main([__file__, "-v", "-s"])