"""Integration Test for Service Startup Hanging Issue

This test validates RealServicesManager with real service interactions
to identify hanging behavior in realistic scenarios.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development/Testing Infrastructure  
- Business Goal: Prevent E2E test suite hangs that block CI/CD pipeline
- Value Impact: Ensures reliable test execution for Golden Path business validation
- Revenue Impact: Prevents $500+ per hour developer delays from hanging tests

Test Strategy:
- Test real service startup and health checking
- Use real HTTP calls where possible (SSOT no-mocks policy)
- Test timeout behavior with actual network conditions
- Test concurrent service startup scenarios
- Should initially FAIL to demonstrate hanging behavior

CRITICAL: No mocks in integration tests - uses real services
"""
import asyncio
import pytest
import time
import httpx
from pathlib import Path
from typing import Dict, Any
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.real_services_manager import RealServicesManager, ServiceEndpoint
from tests.e2e.config import TEST_CONFIG
from shared.isolated_environment import IsolatedEnvironment

class TestServiceStartupHangingIntegration(SSotAsyncTestCase):
    """Integration tests for service startup hanging behavior with real services"""

    async def setUp(self):
        """Setup with real service environment"""
        await super().setUp()
        self.env = IsolatedEnvironment()
        self.manager = RealServicesManager()
        self.local_endpoints = [ServiceEndpoint('auth_service', 'http://localhost:8081', '/auth/health', timeout=5.0), ServiceEndpoint('backend', 'http://localhost:8000', '/health', timeout=5.0), ServiceEndpoint('websocket', 'ws://localhost:8000/ws', '/ws/health', timeout=5.0)]
        self.manager.service_endpoints = self.local_endpoints

    async def test_real_service_startup_timeout_behavior(self):
        """Test startup behavior with real services that may not be running"""
        start_time = time.time()
        try:
            startup_result = await asyncio.wait_for(self.manager.start_all_services(skip_frontend=True), timeout=30.0)
            elapsed_time = time.time() - start_time
            print(f'Service startup completed in {elapsed_time:.2f}s')
            print(f'Startup result: {startup_result}')
            self.assertLess(elapsed_time, 25.0, f'Service startup took {elapsed_time:.2f}s, may indicate hanging')
            self.assertIsInstance(startup_result, dict)
            self.assertIn('success', startup_result)
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            self.fail(f'Service startup hung for {elapsed_time:.2f}s - HANGING BEHAVIOR DETECTED')
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f'Service startup failed in {elapsed_time:.2f}s with error: {e}')
            self.assertLess(elapsed_time, 25.0, f'Service startup error took {elapsed_time:.2f}s, may indicate hanging before error')

    async def test_real_health_check_hanging_detection(self):
        """Test health checks against real endpoints for hanging behavior"""
        test_endpoints = [ServiceEndpoint('nonexistent1', 'http://localhost:9991', '/health', timeout=3.0), ServiceEndpoint('nonexistent2', 'http://localhost:9992', '/health', timeout=3.0), ServiceEndpoint('nonexistent3', 'http://localhost:9993', '/health', timeout=3.0)]
        start_time = time.time()
        try:
            health_tasks = []
            for endpoint in test_endpoints:
                task = self.manager._check_service_health(endpoint)
                health_tasks.append(task)
            results = await asyncio.wait_for(asyncio.gather(*health_tasks, return_exceptions=True), timeout=15.0)
            elapsed_time = time.time() - start_time
            print(f'Health checks completed in {elapsed_time:.2f}s')
            print(f'Results: {[str(r)[:100] for r in results]}')
            self.assertLess(elapsed_time, 12.0, f'Health checks took {elapsed_time:.2f}s, may indicate hanging')
            self.assertEqual(len(results), len(test_endpoints))
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            self.fail(f'Health checks hung for {elapsed_time:.2f}s - HANGING BEHAVIOR DETECTED')

    async def test_real_http_client_timeout_behavior(self):
        """Test HTTP client timeout behavior with real requests"""
        test_cases = [('http://httpbin.org/delay/1', 2.0, False), ('http://httpbin.org/delay/5', 3.0, True), ('http://httpbin.org/status/500', 2.0, False), ('http://nonexistent.invalid', 2.0, True)]
        async with httpx.AsyncClient() as client:
            for url, timeout_seconds, should_timeout in test_cases:
                print(f'Testing {url} with {timeout_seconds}s timeout')
                start_time = time.time()
                try:
                    response = await asyncio.wait_for(client.get(url, timeout=timeout_seconds), timeout=timeout_seconds + 2.0)
                    elapsed_time = time.time() - start_time
                    if should_timeout:
                        print(f'Expected timeout but got response: {response.status_code} in {elapsed_time:.2f}s')
                    else:
                        print(f'Got expected response: {response.status_code} in {elapsed_time:.2f}s')
                    self.assertLess(elapsed_time, timeout_seconds + 1.0, f'Request to {url} took {elapsed_time:.2f}s, expected ~{timeout_seconds}s')
                except (asyncio.TimeoutError, httpx.TimeoutException):
                    elapsed_time = time.time() - start_time
                    print(f'Got timeout for {url} in {elapsed_time:.2f}s')
                    self.assertLess(elapsed_time, timeout_seconds + 2.0, f'Timeout for {url} took {elapsed_time:.2f}s, too long')
                except Exception as e:
                    elapsed_time = time.time() - start_time
                    print(f'Got error for {url} in {elapsed_time:.2f}s: {e}')
                    self.assertLess(elapsed_time, timeout_seconds + 1.0, f'Error for {url} took {elapsed_time:.2f}s, may indicate hanging')

    async def test_concurrent_service_operations_hanging(self):
        """Test concurrent service operations for hanging behavior"""
        managers = [RealServicesManager() for _ in range(3)]
        for manager in managers:
            manager.service_endpoints = self.local_endpoints
        start_time = time.time()
        try:
            tasks = []
            tasks.append(managers[0].start_all_services(skip_frontend=True))
            tasks.append(managers[1]._check_all_services_health())
            tasks.append(managers[2]._check_all_services_health())
            results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=45.0)
            elapsed_time = time.time() - start_time
            print(f'Concurrent operations completed in {elapsed_time:.2f}s')
            print(f'Results summary: {[type(r).__name__ for r in results]}')
            self.assertLess(elapsed_time, 40.0, f'Concurrent operations took {elapsed_time:.2f}s, may indicate hanging')
            self.assertEqual(len(results), 3)
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            self.fail(f'Concurrent operations hung for {elapsed_time:.2f}s - HANGING BEHAVIOR DETECTED')
        finally:
            for manager in managers:
                try:
                    await manager.cleanup()
                except Exception as e:
                    print(f'Cleanup error: {e}')

    async def test_websocket_connection_hanging_detection(self):
        """Test WebSocket connection attempts for hanging behavior"""
        websocket_tests = [('ws://localhost:8000/ws', 5.0), ('ws://httpbin.org/websocket', 5.0), ('ws://nonexistent.invalid/ws', 3.0)]
        for ws_url, timeout_seconds in websocket_tests:
            print(f'Testing WebSocket connection to {ws_url}')
            start_time = time.time()
            try:
                result = await asyncio.wait_for(self.manager.test_websocket_connection_basic(), timeout=timeout_seconds + 2.0)
                elapsed_time = time.time() - start_time
                print(f'WebSocket test to {ws_url} completed in {elapsed_time:.2f}s: {result}')
                self.assertLess(elapsed_time, timeout_seconds + 1.0, f'WebSocket test took {elapsed_time:.2f}s, may indicate hanging')
            except asyncio.TimeoutError:
                elapsed_time = time.time() - start_time
                print(f'WebSocket test to {ws_url} timed out after {elapsed_time:.2f}s')
                if elapsed_time > timeout_seconds + 1.0:
                    self.fail(f'WebSocket test hung for {elapsed_time:.2f}s - HANGING BEHAVIOR DETECTED')
            except Exception as e:
                elapsed_time = time.time() - start_time
                print(f'WebSocket test to {ws_url} failed in {elapsed_time:.2f}s: {e}')
                self.assertLess(elapsed_time, timeout_seconds + 1.0, f'WebSocket error took {elapsed_time:.2f}s, may indicate hanging')

    async def test_startup_with_mixed_service_availability(self):
        """Test startup behavior with mix of available and unavailable services"""
        mixed_endpoints = [ServiceEndpoint('httpbin', 'http://httpbin.org', '/status/200', timeout=10.0), ServiceEndpoint('local_backend', 'http://localhost:8000', '/health', timeout=5.0), ServiceEndpoint('nonexistent', 'http://localhost:9999', '/health', timeout=3.0)]
        self.manager.service_endpoints = mixed_endpoints
        start_time = time.time()
        try:
            health_result = await asyncio.wait_for(self.manager._check_all_services_health(), timeout=30.0)
            elapsed_time = time.time() - start_time
            print(f'Mixed service health check completed in {elapsed_time:.2f}s')
            print(f'Health result: {health_result}')
            self.assertLess(elapsed_time, 25.0, f'Mixed service check took {elapsed_time:.2f}s, may indicate hanging')
            self.assertIsInstance(health_result, dict)
            self.assertIn('all_healthy', health_result)
            self.assertIn('services', health_result)
            self.assertEqual(len(health_result['services']), len(mixed_endpoints))
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            self.fail(f'Mixed service check hung for {elapsed_time:.2f}s - HANGING BEHAVIOR DETECTED')

    async def tearDown(self):
        """Cleanup test resources"""
        if hasattr(self, 'manager'):
            await self.manager.cleanup()
        await super().tearDown()

class TestRealServiceInteractionPatterns(SSotAsyncTestCase):
    """Test real service interaction patterns that might cause hanging"""

    async def test_rapid_consecutive_health_checks(self):
        """Test rapid consecutive health checks for resource exhaustion/hanging"""
        manager = RealServicesManager()
        test_endpoints = [ServiceEndpoint('httpbin1', 'http://httpbin.org', '/status/200', timeout=5.0), ServiceEndpoint('httpbin2', 'http://httpbin.org', '/delay/1', timeout=3.0), ServiceEndpoint('local1', 'http://localhost:8000', '/health', timeout=2.0), ServiceEndpoint('local2', 'http://localhost:8081', '/auth/health', timeout=2.0)]
        manager.service_endpoints = test_endpoints
        start_time = time.time()
        try:
            results = []
            for i in range(5):
                print(f'Performing health check {i + 1}/5')
                result = await asyncio.wait_for(manager._check_all_services_health(), timeout=15.0)
                results.append(result)
                await asyncio.sleep(0.1)
            elapsed_time = time.time() - start_time
            print(f'Rapid health checks completed in {elapsed_time:.2f}s')
            print(f'Got {len(results)} results')
            self.assertEqual(len(results), 5)
            self.assertLess(elapsed_time, 30.0, f'Rapid health checks took {elapsed_time:.2f}s, may indicate hanging')
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            self.fail(f'Rapid health checks hung for {elapsed_time:.2f}s - HANGING BEHAVIOR DETECTED')
        finally:
            await manager.cleanup()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')