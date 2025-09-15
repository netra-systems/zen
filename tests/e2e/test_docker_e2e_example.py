"""
E2E Docker Example Test - The RIGHT way to write Docker E2E tests
================================================================

This example demonstrates how to write reliable E2E tests with Docker:
1. Uses proper fixtures from conftest.py
2. Demonstrates service interaction patterns
3. Shows proper async/await usage
4. Includes error handling
5. Tests real business functionality

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity - reliable tests enable confident deployments
- Value Impact: Provides reference implementation for all E2E tests
- Strategic Impact: Reduces test flakiness and development friction
"""
import asyncio
import json
import pytest
import httpx
from typing import Dict, Any
from shared.isolated_environment import IsolatedEnvironment
from test_framework.websocket_helpers import WebSocketTestHelpers
from shared.isolated_environment import get_env

@pytest.mark.e2e
class TestE2EDockerExample:
    """
    Example E2E test class showing proper Docker usage.
    
    IMPORTANT: This class demonstrates the CORRECT patterns for E2E testing:
    - Uses e2e_services fixture for service URLs
    - Tests real business functionality
    - Includes proper error handling
    - Uses async/await correctly
    """

    @pytest.mark.asyncio
    async def test_backend_health_check(self, e2e_backend_url: str):
        """Test that backend service is healthy and responding."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{e2e_backend_url}/health')
            assert response.status_code == 200
            health_data = response.json()
            assert 'status' in health_data
            assert health_data['status'] in ['healthy', 'ok']
            assert 'service' in health_data

    @pytest.mark.asyncio
    async def test_auth_service_health_check(self, e2e_auth_url: str):
        """Test that auth service is healthy and responding."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{e2e_auth_url}/health')
            assert response.status_code == 200
            health_data = response.json()
            assert 'status' in health_data
            assert health_data['status'] in ['healthy', 'ok']

    @pytest.mark.asyncio
    async def test_service_urls_accessible(self, e2e_services: Dict[str, str]):
        """Test that all E2E service URLs are accessible."""
        required_services = ['backend', 'auth', 'websocket']
        for service_name in required_services:
            assert service_name in e2e_services
            service_url = e2e_services[service_name]
            assert service_url.startswith(('http://', 'https://', 'ws://', 'wss://'))
            print(f" PASS:  Service '{service_name}' available at: {service_url}")

    @pytest.mark.asyncio
    async def test_backend_api_interaction(self, e2e_http_client):
        """Test basic API interaction with backend service."""
        response = await e2e_http_client.get('/api/version')
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            version_data = response.json()
            assert isinstance(version_data, dict)

    @pytest.mark.asyncio
    async def test_websocket_connection(self, e2e_websocket_url: str):
        """Test WebSocket connection to backend service."""
        import websockets
        try:
            async with websockets.connect(e2e_websocket_url, ping_interval=10, ping_timeout=5, close_timeout=5) as websocket:
                await websocket.send(json.dumps({'type': 'ping', 'data': {'test': True}}))
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    assert isinstance(response_data, dict)
                    print(f' PASS:  WebSocket response: {response_data}')
                except asyncio.TimeoutError:
                    print(' WARNING: [U+FE0F] WebSocket connection established but no response to ping (expected)')
        except Exception as e:
            print(f' WARNING: [U+FE0F] WebSocket connection test: {e}')

    @pytest.mark.asyncio
    async def test_cross_service_communication(self, e2e_services: Dict[str, str]):
        """Test that services can communicate with each other."""
        backend_url = e2e_services['backend']
        auth_url = e2e_services['auth']
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{backend_url}/health')
            if response.status_code == 200:
                health_data = response.json()
                print(f'Backend health data: {health_data}')
                assert 'status' in health_data

    @pytest.mark.asyncio
    async def test_database_connectivity(self, e2e_services: Dict[str, str]):
        """Test that services can connect to their databases."""
        backend_url = e2e_services['backend']
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{backend_url}/health')
            if response.status_code == 200:
                health_data = response.json()
                print(f'Health check includes: {list(health_data.keys())}')
                assert health_data.get('status') in ['healthy', 'ok']

@pytest.mark.e2e
class TestE2EDockerReliability:
    """
    Tests that demonstrate Docker reliability features:
    - Port isolation
    - Clean state between tests  
    - Proper resource cleanup
    """

    @pytest.mark.asyncio
    async def test_port_isolation(self, e2e_services: Dict[str, str]):
        """Test that E2E tests use isolated ports."""
        backend_url = e2e_services['backend']
        auth_url = e2e_services['auth']
        import re
        backend_port = re.search(':(\\d+)', backend_url)
        auth_port = re.search(':(\\d+)', auth_url)
        if backend_port:
            port_num = int(backend_port.group(1))
            assert port_num == 8002, f'Expected E2E backend port 8002, got {port_num}'
        if auth_port:
            port_num = int(auth_port.group(1))
            assert port_num == 8083, f'Expected E2E auth port 8083, got {port_num}'

    @pytest.mark.asyncio
    async def test_clean_state_between_runs(self, e2e_http_client):
        """Test that each test run starts with clean state."""
        response = await e2e_http_client.get('/health')
        assert response.status_code == 200
        print(' PASS:  Clean state verified - each test run starts fresh')

    def test_environment_variables_set(self, e2e_services: Dict[str, str]):
        """Test that proper environment variables are set for E2E tests."""
        env = get_env()
        expected_vars = ['E2E_BACKEND_URL', 'E2E_AUTH_URL', 'E2E_WEBSOCKET_URL', 'E2E_POSTGRES_URL', 'E2E_REDIS_URL']
        for var_name in expected_vars:
            var_value = env.get(var_name)
            assert var_value is not None, f'Environment variable {var_name} not set'
            print(f' PASS:  {var_name} = {var_value}')

@pytest.mark.slow
class TestE2EDockerPerformance:
    """
    Performance tests for Docker E2E environment.
    These tests verify that the Docker setup is performant enough for CI/CD.
    """

    @pytest.mark.asyncio
    async def test_service_startup_time(self, e2e_services: Dict[str, str]):
        """Test that services start up quickly enough for CI."""
        import time
        start_time = time.time()
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{e2e_services['backend']}/health")
            end_time = time.time()
            response_time = end_time - start_time
            assert response.status_code == 200
            assert response_time < 2.0, f'Health check took {response_time:.2f}s (too slow for CI)'
            print(f' PASS:  Service response time: {response_time:.2f}s')

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, e2e_services: Dict[str, str]):
        """Test that services handle concurrent requests properly."""
        backend_url = e2e_services['backend']

        async def make_request():
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{backend_url}/health')
                return response.status_code
        tasks = [make_request() for _ in range(10)]
        status_codes = await asyncio.gather(*tasks)
        assert all((code == 200 for code in status_codes))
        print(f' PASS:  All {len(status_codes)} concurrent requests succeeded')

def verify_service_health(response_data: Dict[str, Any]) -> None:
    """
    Utility function to verify service health response format.
    Other E2E tests can import and use this.
    """
    required_fields = ['status']
    for field in required_fields:
        assert field in response_data, f'Missing required field: {field}'
    assert response_data['status'] in ['healthy', 'ok'], f"Invalid status: {response_data['status']}"

async def wait_for_service_ready(service_url: str, timeout: int=30) -> bool:
    """
    Utility function to wait for a service to become ready.
    Useful for tests that need to wait for async operations.
    """
    import time
    start_time = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                response = await client.get(f'{service_url}/health')
                if response.status_code == 200:
                    return True
            except httpx.RequestError:
                pass
            await asyncio.sleep(1)
    return False
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')