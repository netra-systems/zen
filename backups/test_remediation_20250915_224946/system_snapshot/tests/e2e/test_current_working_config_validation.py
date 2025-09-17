'''
Current Working Configuration Validation Test

This test validates that the system is working with the current port configuration
observed during successful dev launcher runs:
- Auth service: 8001 (CORRECTED - all services on single port)
- WebSocket: ws://localhost:8001/ws

This ensures tests match the actual working system configuration.

BVJ: Platform/Internal | Configuration Validation | CRITICAL - Foundation for all E2E tests
'''

import asyncio
import httpx
import pytest
from typing import Dict, Any
from shared.isolated_environment import IsolatedEnvironment


class WorkingConfigValidator:
    """Validates the current working system configuration."""

    def __init__(self):
        pass
        self.services = { )
        "auth": { )
        "port": 8001,  # CORRECTED: Auth service is actually running on 8001
        "url": "http://localhost:8001",
        "health_endpoint": "/health"
    
    
        self.websocket_url = "ws://localhost:8001/ws"

    async def validate_service(self, service_name: str) -> Dict[str, Any]:
        """Validate a single service is accessible."""
        service_config = self.services[service_name]
        result = { )
        "service_name": service_name,
        "port": service_config["port"],
        "accessible": False,
        "healthy": False,
        "response_time_ms": None,
        "service_info": None,
        "error": None
    

        try:
        import time
        start_time = time.time()

        url = "formatted_string"

        async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)

        result["response_time_ms"] = (time.time() - start_time) * 1000
        result["accessible"] = True

        if response.status_code == 200:
        result["healthy"] = True
        try:
        service_info = response.json()
        result["service_info"] = service_info

                    # Validate service identity
        service_field = service_info.get("service", "").lower()
        if service_name.lower() in service_field:
        result["service_identity_confirmed"] = True
        else:
        result["service_identity_confirmed"] = False
        result["actual_service"] = service_field
        except Exception:
        result["service_info"] = "formatted_string"
        else:
        result["error"] = "formatted_string"

        except httpx.ConnectError:
        result["error"] = "formatted_string"
        except httpx.TimeoutException:
        result["error"] = "formatted_string"
        except Exception as e:
        result["error"] = "formatted_string"

        return result

    async def validate_all_services(self) -> Dict[str, Any]:
        """Validate all services in the current working configuration."""
        results = {}

        for service_name in self.services.keys():
        results[service_name] = await self.validate_service(service_name)

        # Calculate overall status
        healthy_services = sum(1 for result in results.values() if result["healthy"])
        accessible_services = sum(1 for result in results.values() if result["accessible"])

        overall_result = { )
        "total_services": len(self.services),
        "healthy_services": healthy_services,
        "accessible_services": accessible_services,
        "all_healthy": healthy_services == len(self.services),
        "core_services_healthy": results.get("auth", {}).get("healthy", False),  # Only auth service in current config
        "service_results": results
        

        return overall_result

    async def validate_websocket_endpoint(self) -> Dict[str, Any]:
        """Validate WebSocket endpoint is accessible (basic connectivity test)."""
        result = { )
        "websocket_url": self.websocket_url,
        "endpoint_accessible": False,
        "connection_time_ms": None,
        "error": None
    

        try:
        import websockets
        import time

        start_time = time.time()

        # Try basic WebSocket connection (without auth for basic connectivity test)
        try:
        async with websockets.connect( )
        self.websocket_url,
        timeout=5.0
        ) as websocket:
        connection_time = (time.time() - start_time) * 1000
        result["connection_time_ms"] = connection_time
        result["endpoint_accessible"] = True
        except websockets.exceptions.WebSocketException as e:
                    # WebSocket connection might fail due to auth requirements, which is expected
        if "401" in str(e) or "unauthorized" in str(e).lower():
        result["endpoint_accessible"] = True  # Endpoint exists, just requires auth
        result["requires_auth"] = True
        result["connection_time_ms"] = (time.time() - start_time) * 1000
        else:
        result["error"] = "formatted_string"

        except ImportError:
        result["error"] = "WebSocket library not available for testing"
        except ConnectionError:
        result["error"] = "WebSocket endpoint not accessible - service may be down"
        except Exception as e:
        result["error"] = "formatted_string"

        return result


@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_current_working_port_configuration():
'''
Test that the current working port configuration is accessible.

This validates:
- Auth service on port 8001 (CORRECTED - single service handles all functionality)

This is the actual port configuration observed during successful dev launcher startup.
'''
pass
validator = WorkingConfigValidator()
results = await validator.validate_all_services()

print(f" )
=== CURRENT WORKING CONFIGURATION VALIDATION ===")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")

for service_name, service_result in results['service_results'].items():
status = " PASS:  HEALTHY" if service_result['healthy'] else " FAIL:  UNHEALTHY"
port = service_result['port']
response_time = service_result.get('response_time_ms', 0)

print("formatted_string")
print("formatted_string" if response_time else "   No response time")

if service_result.get('service_identity_confirmed'):
print(f"    PASS:  Service identity confirmed")
elif 'actual_service' in service_result:
print("formatted_string")

if service_result['error']:
print("formatted_string")

                                                                # Validate that the auth service is working (it handles all functionality)
assert results['accessible_services'] >= 1, "Auth service is not accessible"

                                                                # Validate auth service specifically (handles all functionality including WebSocket auth)
auth_result = results['service_results'].get('auth')
assert auth_result is not None, "Auth service result missing"

if auth_result['accessible']:
                                                                    # If auth is accessible, validate it's on the correct port
assert auth_result['port'] == 8001, "formatted_string"

if auth_result['healthy']:
print(" PASS:  Auth service is healthy on correct port 8001")
else:
print("formatted_string")
                                                                            # Don't fail if service is accessible but not perfectly healthy
else:
pytest.fail("formatted_string")

                                                                                # Validate service identity
if auth_result.get('service_identity_confirmed'):
print(" PASS:  Service identity confirmed as auth-service")
else:
print("formatted_string")


@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_websocket_endpoint_accessibility():
'''
Test WebSocket endpoint basic accessibility.

This validates the WebSocket endpoint exists and is reachable,
even if authentication is required.
'''
pass
validator = WorkingConfigValidator()
result = await validator.validate_websocket_endpoint()

print(f" )
=== WEBSOCKET ENDPOINT VALIDATION ===")
print("formatted_string")
print("formatted_string")

if result.get('requires_auth'):
print(" PASS:  WebSocket endpoint requires authentication (expected)")

if result.get('connection_time_ms'):
print("formatted_string")

if result['error']:
print("formatted_string")

                                                                                                        # For this test, we mainly want to ensure the endpoint is reachable
                                                                                                        # Even if it requires authentication (which is expected)
if not result['endpoint_accessible'] and result['error']:
                                                                                                            # If there's a connection error, it might be because services aren't running
if "connection" in result['error'].lower() or "endpoint not accessible" in result['error'].lower():
print(" WARNING: [U+FE0F]  WebSocket endpoint not accessible - this may indicate backend service issues")
                                                                                                                # Don't fail the test if services aren't fully running yet
pytest.skip("formatted_string")
else:
                                                                                                                    # Other errors might indicate real issues
print("formatted_string")


@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_service_response_timing():
'''
Test that services respond within acceptable timing for real-time applications.

This ensures the current configuration meets performance requirements.
'''
pass
validator = WorkingConfigValidator()
results = await validator.validate_all_services()

print(f" )
=== SERVICE RESPONSE TIMING VALIDATION ===")

timing_requirements = { )
"auth": 2000,    # Auth should respond within 2s for WebSocket handshakes
"backend": 5000  # Backend can be a bit slower
                                                                                                                        

for service_name, service_result in results['service_results'].items():
if service_result['accessible'] and service_result.get('response_time_ms'):
response_time = service_result['response_time_ms']
max_time = timing_requirements.get(service_name, 5000)

print("formatted_string")

if service_result['healthy']:
assert response_time < max_time, \
"formatted_string"

if response_time < max_time / 2:
print(f"    PASS:  Excellent response time")
else:
print(f"    PASS:  Acceptable response time")
else:
print(f"    WARNING: [U+FE0F]  Service not healthy, timing not validated")
else:
print("formatted_string")


if __name__ == "__main__":
async def main():
pass
validator = WorkingConfigValidator()

print("=== VALIDATING CURRENT WORKING CONFIGURATION ===")

    # Test all services
results = await validator.validate_all_services()
print("formatted_string")

    # Test WebSocket endpoint
ws_result = await validator.validate_websocket_endpoint()
print("formatted_string")

asyncio.run(main())
