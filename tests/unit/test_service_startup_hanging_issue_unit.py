"""Unit Test for Service Startup Hanging Issue

This test validates RealServicesManager service startup logic to identify
hanging behavior during E2E test initialization.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development/Testing Infrastructure
- Business Goal: Prevent E2E test timeouts that block CI/CD pipeline
- Value Impact: Enables reliable test execution and faster deployment cycles
- Revenue Impact: Reduces development delays that cost ~$500/hour in team productivity

Test Strategy:
- Test startup flow with timeout mechanisms
- Validate health check timeout behavior
- Test service availability detection logic
- Reproduce hanging behavior if it exists

CRITICAL: This uses SSOT testing patterns and should initially FAIL
to demonstrate the hanging issue exists.
"""
import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.real_services_manager import RealServicesManager, ServiceStatus, ServiceEndpoint

@pytest.mark.unit
class ServiceStartupHangingIssueUnitTests(SSotAsyncTestCase):
    """Unit tests for service startup hanging behavior"""

    async def setUp(self):
        """Setup test environment"""
        await super().setUp()
        self.manager = RealServicesManager()

    async def test_health_check_timeout_behavior(self):
        """Test that health checks timeout properly and don't hang indefinitely"""
        hanging_client = Mock()
        hanging_client.get = AsyncMock()

        async def hanging_request(*args, **kwargs):
            await asyncio.sleep(300)
            return Mock(status_code=200)
        hanging_client.get.side_effect = hanging_request
        self.manager._http_client = hanging_client
        endpoint = ServiceEndpoint('test_service', 'http://localhost:9999', '/health', timeout=2.0)
        start_time = time.time()
        status = await self.manager._check_service_health(endpoint)
        elapsed_time = time.time() - start_time
        assert elapsed_time < 10.0, f'Health check took {elapsed_time:.2f}s, expected <10s'
        assert not status.healthy, 'Service should be unhealthy due to timeout'
        assert 'timeout' in (status.error.lower() if status.error else ''), 'Error should mention timeout'

    async def test_wait_for_services_healthy_timeout(self):
        """Test that _wait_for_services_healthy doesn't hang when services never become healthy"""

        async def always_unhealthy():
            return {'all_healthy': False, 'services': {'test_service': {'healthy': False}}, 'failures': ['test_service'], 'summary': '0/1 services healthy'}
        self.manager._check_all_services_health = always_unhealthy
        start_time = time.time()
        with self.assertRaises(Exception) as context:
            await self.manager._wait_for_services_healthy(timeout=3.0)
        elapsed_time = time.time() - start_time
        self.assertLess(elapsed_time, 6.0, f'Wait for services took {elapsed_time:.2f}s, expected ~3s')
        self.assertGreater(elapsed_time, 2.5, f'Wait for services took {elapsed_time:.2f}s, too fast for 3s timeout')
        self.assertIn('failed to become healthy', str(context.exception).lower())

    async def test_start_all_services_hanging_detection(self):
        """Test that start_all_services has proper timeout handling"""

        async def hanging_health_check():
            await asyncio.sleep(120)
            return {'all_healthy': False, 'failures': ['hanging_service']}

        async def hanging_service_start(*args, **kwargs):
            await asyncio.sleep(120)
            return {'success': False, 'error': 'Startup hanging'}
        self.manager._check_all_services_health = hanging_health_check
        self.manager._start_missing_services = hanging_service_start
        self.manager._ensure_http_client = AsyncMock()
        start_time = time.time()
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(self.manager.start_all_services(), timeout=5.0)
        elapsed_time = time.time() - start_time
        self.assertLess(elapsed_time, 8.0, f'Start services took {elapsed_time:.2f}s, expected ~5s')

    async def test_websocket_health_check_timeout(self):
        """Test WebSocket health check timeout behavior"""
        ws_endpoint = ServiceEndpoint('websocket', 'ws://nonexistent:9999', '/ws', timeout=2.0)
        start_time = time.time()
        healthy, error = await self.manager._check_websocket_health(ws_endpoint)
        elapsed_time = time.time() - start_time
        self.assertLess(elapsed_time, 10.0, f'WebSocket health check took {elapsed_time:.2f}s, too long')
        self.assertFalse(healthy, 'WebSocket to nonexistent host should be unhealthy')
        self.assertIsNotNone(error, 'Should have error message')

    async def test_event_loop_blocking_detection(self):
        """Test detection of event loop blocking during startup"""

        def blocking_operation():
            start = time.time()
            while time.time() - start < 2.0:
                pass
            return {'success': True}
        original_start_local = self.manager._start_local_services

        async def blocking_start_local(*args, **kwargs):
            result = blocking_operation()
            return result
        self.manager._start_local_services = blocking_start_local
        start_time = time.time()
        health_check_task = asyncio.create_task(self.manager._check_all_services_health())
        startup_task = asyncio.create_task(self.manager._start_missing_services())
        results = await asyncio.gather(health_check_task, startup_task, return_exceptions=True)
        elapsed_time = time.time() - start_time
        print(f'Concurrent operations completed in {elapsed_time:.2f}s')
        print(f'Results: {results}')
        self.assertLess(elapsed_time, 5.0, 'Event loop blocking detected - operations took too long')

    def test_synchronous_startup_hanging(self):
        """Test synchronous startup method for hanging behavior"""
        start_time = time.time()

        async def hanging_start_all():
            await asyncio.sleep(60)
            return {'success': False}
        self.manager.start_all_services = hanging_start_all
        try:
            result = asyncio.wait_for(asyncio.coroutine(lambda: self.manager.launch_dev_environment())(), timeout=3.0)
            asyncio.run(result)
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            print(f'Synchronous startup failed with: {e}')
        elapsed_time = time.time() - start_time
        self.assertLess(elapsed_time, 5.0, f'Synchronous startup took {elapsed_time:.2f}s, may indicate hanging')

    async def tearDown(self):
        """Cleanup test resources"""
        if hasattr(self, 'manager'):
            await self.manager.cleanup()
        await super().tearDown()

@pytest.mark.unit
class ServiceStartupTimeoutsTests(SSotAsyncTestCase):
    """Specific timeout behavior tests"""

    async def test_cascading_timeout_issue(self):
        """Test for cascading timeout issues that could cause hanging"""
        manager = RealServicesManager()
        services_config = [('fast_service', 1.0), ('slow_service', 10.0), ('timeout_service', 0.1), ('hanging_service', 30.0)]
        endpoints = []
        for name, timeout in services_config:
            endpoint = ServiceEndpoint(name, f'http://localhost:9999', '/health', timeout=timeout)
            endpoints.append(endpoint)
        manager.service_endpoints = endpoints
        mock_client = Mock()

        async def mock_get(url, timeout=None, **kwargs):
            if 'fast_service' in url:
                await asyncio.sleep(0.5)
                return Mock(status_code=200)
            elif 'slow_service' in url:
                await asyncio.sleep(5.0)
                return Mock(status_code=200)
            elif 'timeout_service' in url:
                await asyncio.sleep(2.0)
                return Mock(status_code=200)
            elif 'hanging_service' in url:
                await asyncio.sleep(100)
                return Mock(status_code=200)
            else:
                raise Exception('Connection refused')
        mock_client.get = mock_get
        manager._http_client = mock_client
        start_time = time.time()
        health_results = await manager._check_all_services_health()
        elapsed_time = time.time() - start_time
        self.assertLess(elapsed_time, 45.0, f'Health checks took {elapsed_time:.2f}s, too long')
        self.assertIsInstance(health_results, dict)
        self.assertIn('all_healthy', health_results)
        await manager.cleanup()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')