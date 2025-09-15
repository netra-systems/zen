"""
Test Basic Health Endpoint - Missing from existing coverage

Business Value Justification (BVJ):
- Segment: Free, Early, Mid, Enterprise (All customer segments)
- Business Goal: Core system reliability monitoring
- Value Impact: Validates fundamental health check endpoint that load balancers and monitoring systems depend on
- Revenue Impact: Foundation for system uptime monitoring ($1M+ ARR dependency)

This test validates the basic /health endpoint functionality that was missing from existing test coverage.
The /health endpoint is critical for:
1. Load balancer health checks
2. Kubernetes readiness probes
3. Monitoring system status validation
4. Basic system availability verification

Current test coverage exists for /health/live and /health/ready but not the basic /health endpoint.
"""
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import MagicMock, AsyncMock, Mock, patch
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.redis_manager import redis_manager
from shared.isolated_environment import IsolatedEnvironment
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

class MockAppState:
    """Mock app state for testing startup scenarios."""

    def __init__(self, startup_complete=True, startup_in_progress=False, startup_failed=False):
        self.startup_complete = startup_complete
        self.startup_in_progress = startup_in_progress
        self.startup_failed = startup_failed
        self.startup_error = None
        self.startup_start_time = None
        self.startup_phase = 'complete'
        self.startup_progress = 100

class BasicHealthEndpointTests:
    """Test the basic /health endpoint that was missing from existing coverage."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_basic_health_endpoint_startup_complete(self):
        """Test /health endpoint when startup is complete."""
        from netra_backend.app.routes.health import health
        mock_request = MagicMock()
        mock_request.app.state = MockAppState(startup_complete=True)
        with patch('netra_backend.app.routes.health.health_interface') as mock_health_interface:
            mock_health_interface.get_health_status = AsyncMock(return_value={'status': 'healthy', 'service': 'netra-ai-platform', 'version': '1.0.0', 'timestamp': datetime.now(timezone.utc).isoformat(), 'uptime_seconds': 3600, 'checks': {'postgres': True, 'clickhouse': True, 'redis': True}, 'metrics': {'requests_per_second': 10.5, 'response_time_ms': 25.3}})
            mock_response = MagicMock()
            mock_response.headers = {}
            result = await health(mock_request, mock_response)
            assert isinstance(result, dict)
            assert result['status'] == 'healthy'
            assert result['service'] == 'netra-ai-platform'
            assert 'timestamp' in result
            assert 'uptime_seconds' in result
            assert result['checks']['postgres'] is True
            assert result['checks']['clickhouse'] is True
            assert result['checks']['redis'] is True
            print(f' PASS:  Basic health endpoint returned: {result}')

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_basic_health_endpoint_startup_in_progress(self):
        """Test /health endpoint when startup is in progress."""
        from netra_backend.app.routes.health import health
        from starlette.responses import Response
        mock_request = MagicMock()
        mock_request.app.state = MockAppState(startup_complete=False, startup_in_progress=True, startup_failed=False)
        mock_request.app.state.startup_phase = 'initializing_database'
        mock_request.app.state.startup_progress = 75
        mock_response = MagicMock()
        mock_response.headers = {}
        result = await health(mock_request, mock_response)
        assert isinstance(result, Response)
        assert result.status_code == 503
        assert result.media_type == 'application/json'
        response_data = json.loads(result.body.decode())
        assert response_data['status'] == 'unhealthy'
        assert response_data['message'] == 'Startup in progress'
        assert response_data['startup_in_progress'] is True
        assert response_data['details']['phase'] == 'initializing_database'
        assert response_data['details']['progress'] == 75
        print(f' PASS:  Health endpoint correctly reported startup in progress: {response_data}')

    @pytest.mark.asyncio
    async def test_basic_health_endpoint_startup_failed(self):
        """Test /health endpoint when startup failed."""
        from netra_backend.app.routes.health import health
        from starlette.responses import Response
        mock_request = MagicMock()
        mock_request.app.state = MockAppState(startup_complete=False, startup_in_progress=False, startup_failed=True)
        mock_request.app.state.startup_error = 'Database connection failed'
        mock_response = MagicMock()
        mock_response.headers = {}
        result = await health(mock_request, mock_response)
        assert isinstance(result, Response)
        assert result.status_code == 503
        response_data = json.loads(result.body.decode())
        assert response_data['status'] == 'unhealthy'
        assert response_data['message'] == 'Startup failed: Database connection failed'
        assert response_data['startup_failed'] is True
        print(f' PASS:  Health endpoint correctly reported startup failure: {response_data}')

    @pytest.mark.asyncio
    async def test_basic_health_endpoint_no_startup_state(self):
        """Test /health endpoint when startup state is unknown."""
        from netra_backend.app.routes.health import health
        from starlette.responses import Response
        mock_request = MagicMock()
        mock_request.app.state = MockAppState(startup_complete=None)
        mock_response = MagicMock()
        mock_response.headers = {}
        result = await health(mock_request, mock_response)
        assert isinstance(result, Response)
        assert result.status_code == 503
        response_data = json.loads(result.body.decode())
        assert response_data['status'] == 'unhealthy'
        assert response_data['message'] == 'Startup state unknown'
        assert response_data['startup_complete'] is None
        print(f' PASS:  Health endpoint correctly reported unknown startup state: {response_data}')

    @pytest.mark.asyncio
    async def test_basic_health_endpoint_startup_timeout(self):
        """Test /health endpoint when startup is taking too long."""
        from netra_backend.app.routes.health import health
        from starlette.responses import Response
        mock_request = MagicMock()
        mock_request.app.state = MockAppState(startup_complete=False, startup_in_progress=True, startup_failed=False)
        mock_request.app.state.startup_start_time = time.time() - 360
        mock_response = MagicMock()
        mock_response.headers = {}
        result = await health(mock_request, mock_response)
        assert isinstance(result, Response)
        assert result.status_code == 503
        response_data = json.loads(result.body.decode())
        assert response_data['status'] == 'unhealthy'
        assert 'Startup taking too long' in response_data['message']
        assert response_data['startup_in_progress'] is True
        assert 'startup_duration' in response_data
        assert response_data['startup_duration'] >= 360
        print(f' PASS:  Health endpoint correctly reported startup timeout: {response_data}')

    @pytest.mark.asyncio
    async def test_basic_health_endpoint_mock_objects_handling(self):
        """Test /health endpoint properly handles MagicMock objects in test environment."""
        from netra_backend.app.routes.health import health
        from starlette.responses import Response
        mock_request = MagicMock()
        mock_request.app.state = MagicMock()
        mock_startup_complete = MagicMock()
        mock_startup_complete._mock_name = 'startup_complete'
        mock_request.app.state.startup_complete = mock_startup_complete
        mock_response = MagicMock()
        mock_response.headers = {}
        result = await health(mock_request, mock_response)
        assert isinstance(result, Response)
        assert result.status_code == 503
        response_data = json.loads(result.body.decode())
        assert response_data['status'] == 'unhealthy'
        assert response_data['message'] == 'Startup state unknown'
        assert response_data['startup_complete'] is None
        print(f' PASS:  Health endpoint correctly handled MagicMock objects: {response_data}')

    @pytest.mark.asyncio
    async def test_basic_health_endpoint_with_fastapi_app(self):
        """Test /health endpoint integrated with FastAPI app."""
        from netra_backend.app.routes.health import router as health_router
        app = FastAPI()
        app.include_router(health_router, prefix='/health')
        app.state.startup_complete = True
        with patch('netra_backend.app.routes.health.health_interface') as mock_health_interface:
            mock_health_interface.get_health_status = AsyncMock(return_value={'status': 'healthy', 'service': 'netra-ai-platform', 'version': '1.0.0', 'timestamp': datetime.now(timezone.utc).isoformat(), 'uptime_seconds': 3600})
            with TestClient(app) as client:
                response = client.get('/health/')
                assert response.status_code == 200
                data = response.json()
                assert data['status'] == 'healthy'
                assert data['service'] == 'netra-ai-platform'
                assert 'timestamp' in data
                print(f' PASS:  FastAPI integration test passed: {data}')
                response_no_slash = client.get('/health')
                assert response_no_slash.status_code == 200
                data_no_slash = response_no_slash.json()
                assert data_no_slash['status'] == 'healthy'
                print(f' PASS:  No-slash endpoint also works: {data_no_slash}')

    @pytest.mark.asyncio
    async def test_basic_health_endpoint_error_response_format(self):
        """Test that health endpoint error responses have correct format."""
        from netra_backend.app.routes.health import health
        from starlette.responses import Response
        mock_request = MagicMock()
        mock_request.app.state = MockAppState(startup_complete=False, startup_failed=True)
        mock_request.app.state.startup_error = 'Test error'
        mock_response = MagicMock()
        mock_response.headers = {}
        result = await health(mock_request, mock_response)
        assert isinstance(result, Response)
        assert result.status_code == 503
        response_data = json.loads(result.body.decode())
        required_fields = ['status', 'message', 'startup_failed']
        for field in required_fields:
            assert field in response_data, f'Missing required field: {field}'
        assert response_data['status'] == 'unhealthy'
        assert isinstance(response_data['startup_failed'], bool)
        assert response_data['startup_failed'] is True
        print(f' PASS:  Error response format is correct: {response_data}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')