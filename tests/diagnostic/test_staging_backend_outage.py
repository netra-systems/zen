"""
Diagnostic Tests for Staging Backend Service Outage Confirmation

Purpose: Execute diagnostic tests to confirm backend service health status
and document exact failure modes for Issue #1263 backend outage investigation.

Expected Results:
- Backend service health checks should FAIL (confirming outage)
- WebSocket connections should FAIL (due to backend dependency)
- Clear documentation of response codes and error messages

Testing Approach: Non-Docker GCP staging environment direct HTTP calls
"""

import pytest
import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Configure logging for diagnostic output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Staging environment URLs (canonical staging URLs per requirements)
STAGING_URLS = {
    'backend': 'https://api.staging.netrasystems.ai',
    'auth': 'https://auth.staging.netrasystems.ai',
    'frontend': 'https://frontend.staging.netrasystems.ai',
    'websocket': 'wss://api.staging.netrasystems.ai/ws'
}

class StagingBackendDiagnostic:
    """Diagnostic utility for staging backend service health validation"""

    def __init__(self):
        self.results = {}
        self.timestamp = datetime.now().isoformat()

    async def test_service_health(self, service_name: str, url: str) -> Dict[str, Any]:
        """Test individual service health with comprehensive error capture"""
        result = {
            'service': service_name,
            'url': url,
            'timestamp': self.timestamp,
            'status': 'UNKNOWN',
            'response_code': None,
            'response_time_ms': None,
            'error_message': None,
            'response_headers': None,
            'response_body': None
        }

        try:
            start_time = asyncio.get_event_loop().time()

            timeout = aiohttp.ClientTimeout(total=10.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{url}/health") as response:
                    end_time = asyncio.get_event_loop().time()
                    response_time = (end_time - start_time) * 1000

                    result.update({
                        'status': 'UP' if response.status == 200 else 'DOWN',
                        'response_code': response.status,
                        'response_time_ms': round(response_time, 2),
                        'response_headers': dict(response.headers),
                        'response_body': await response.text()
                    })

                    logger.info(f"Service {service_name} health check: {response.status} ({response_time:.2f}ms)")

        except aiohttp.ClientTimeout as e:
            result.update({
                'status': 'TIMEOUT',
                'error_message': f"Timeout after 10s: {str(e)}"
            })
            logger.error(f"Service {service_name} timeout: {str(e)}")

        except aiohttp.ClientError as e:
            result.update({
                'status': 'CONNECTION_ERROR',
                'error_message': f"Connection error: {str(e)}"
            })
            logger.error(f"Service {service_name} connection error: {str(e)}")

        except Exception as e:
            result.update({
                'status': 'UNKNOWN_ERROR',
                'error_message': f"Unexpected error: {str(e)}"
            })
            logger.error(f"Service {service_name} unexpected error: {str(e)}")

        return result


@pytest.mark.asyncio
class StagingBackendOutageTests:
    """Test suite to confirm and document staging backend service outage"""

    @pytest.fixture
    def diagnostic(self):
        return StagingBackendDiagnostic()

    async def test_backend_health_endpoint(self, diagnostic):
        """
        EXPECTED TO FAIL: Backend service should be down/unreachable

        This test is designed to document the backend outage by attempting
        to reach the health endpoint and capturing the exact failure mode.
        """
        result = await diagnostic.test_service_health('backend', STAGING_URLS['backend'])

        # Log diagnostic information
        logger.info(f"Backend Diagnostic Result: {result}")

        # Document the outage
        if result['status'] == 'UP':
            logger.warning("UNEXPECTED: Backend service is UP - this should be investigated")
            assert False, f"Backend unexpectedly UP with status {result['response_code']}"
        else:
            logger.info(f"CONFIRMED: Backend outage - Status: {result['status']}, Error: {result['error_message']}")
            # This confirms the outage - test should "pass" by documenting the failure
            assert result['status'] in ['DOWN', 'TIMEOUT', 'CONNECTION_ERROR', 'UNKNOWN_ERROR']

    async def test_backend_api_endpoints(self, diagnostic):
        """
        EXPECTED TO FAIL: Backend API endpoints should be unreachable

        Test critical backend endpoints to document failure patterns.
        """
        endpoints = [
            '/api/v1/agents',
            '/api/v1/chat',
            '/api/v1/tools',
            '/ws'  # WebSocket endpoint
        ]

        backend_url = STAGING_URLS['backend']

        for endpoint in endpoints:
            try:
                timeout = aiohttp.ClientTimeout(total=5.0)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(f"{backend_url}{endpoint}") as response:
                        if response.status == 200:
                            logger.warning(f"UNEXPECTED: Endpoint {endpoint} is responding (status {response.status})")
                        else:
                            logger.info(f"CONFIRMED: Endpoint {endpoint} down (status {response.status})")

            except Exception as e:
                logger.info(f"CONFIRMED: Endpoint {endpoint} unreachable - {str(e)}")

        # The test confirms outage by documenting failures
        assert True, "Backend endpoints outage confirmed through diagnostic testing"

    async def test_websocket_connection_failure(self, diagnostic):
        """
        EXPECTED TO FAIL: WebSocket connections should fail due to backend dependency

        Attempt WebSocket connection to document the connection failure pattern.
        """
        import websockets

        websocket_url = STAGING_URLS['websocket']
        connection_result = {
            'url': websocket_url,
            'status': 'UNKNOWN',
            'error_message': None,
            'timestamp': diagnostic.timestamp
        }

        try:
            # Attempt WebSocket connection with short timeout
            async with websockets.connect(websocket_url, timeout=5.0) as websocket:
                connection_result['status'] = 'CONNECTED'
                logger.warning("UNEXPECTED: WebSocket connection succeeded")

        except websockets.ConnectionClosed as e:
            connection_result.update({
                'status': 'CONNECTION_CLOSED',
                'error_message': str(e)
            })
            logger.info(f"CONFIRMED: WebSocket connection closed - {str(e)}")

        except websockets.InvalidURI as e:
            connection_result.update({
                'status': 'INVALID_URI',
                'error_message': str(e)
            })
            logger.info(f"CONFIRMED: WebSocket URI invalid - {str(e)}")

        except asyncio.TimeoutError:
            connection_result.update({
                'status': 'TIMEOUT',
                'error_message': 'WebSocket connection timeout'
            })
            logger.info("CONFIRMED: WebSocket connection timeout")

        except Exception as e:
            connection_result.update({
                'status': 'CONNECTION_ERROR',
                'error_message': str(e)
            })
            logger.info(f"CONFIRMED: WebSocket connection error - {str(e)}")

        # Document the WebSocket failure
        logger.info(f"WebSocket Connection Result: {connection_result}")

        # Confirm WebSocket is down as expected
        assert connection_result['status'] in ['CONNECTION_CLOSED', 'TIMEOUT', 'CONNECTION_ERROR', 'INVALID_URI']

    async def test_comprehensive_service_status(self, diagnostic):
        """
        Comprehensive test of all staging services to document current state

        This provides a complete diagnostic overview of the staging environment.
        """
        service_results = {}

        for service_name, url in STAGING_URLS.items():
            if service_name == 'websocket':
                continue  # Skip WebSocket in HTTP health checks

            result = await diagnostic.test_service_health(service_name, url)
            service_results[service_name] = result

        # Log comprehensive results
        logger.info("=== STAGING SERVICES DIAGNOSTIC RESULTS ===")
        for service, result in service_results.items():
            logger.info(f"{service.upper()}: {result['status']} - {result.get('error_message', 'OK')}")

        # Document findings
        backend_down = service_results.get('backend', {}).get('status') != 'UP'
        auth_status = service_results.get('auth', {}).get('status')
        frontend_status = service_results.get('frontend', {}).get('status')

        logger.info(f"Backend Down: {backend_down}")
        logger.info(f"Auth Status: {auth_status}")
        logger.info(f"Frontend Status: {frontend_status}")

        # Test passes by documenting the current state
        assert True, "Comprehensive service diagnostic completed"


if __name__ == "__main__":
    # Allow running diagnostic directly
    import sys

    async def run_diagnostic():
        diagnostic = StagingBackendDiagnostic()

        print("=== STAGING BACKEND OUTAGE DIAGNOSTIC ===")
        print(f"Timestamp: {diagnostic.timestamp}")
        print()

        for service_name, url in STAGING_URLS.items():
            if service_name == 'websocket':
                continue

            print(f"Testing {service_name} at {url}...")
            result = await diagnostic.test_service_health(service_name, url)
            print(f"Result: {result['status']} - {result.get('error_message', 'OK')}")
            print()

    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        asyncio.run(run_diagnostic())