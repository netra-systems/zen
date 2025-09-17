'''
'''
Fixed Auth Service Port Validation Test

This test validates that the auth service is running on the correct port (8081)
as configured in the dev launcher, fixing the port mismatch issues identified
in previous test runs.

BVJ: Enterprise | Infrastructure | Service Discovery | BLOCKING - Port consistency for E2E tests
'''
'''

import asyncio
import httpx
import pytest
from typing import Dict, Any, Optional
from shared.isolated_environment import IsolatedEnvironment


class AuthServicePortValidator:
    """Validates auth service is accessible on the correct port."""

    def __init__(self):
        pass
        self.correct_port = 8081  # Port configured in dev launcher
        self.auth_url = ""

    async def validate_auth_service_accessibility(self) -> Dict[str, Any]:
        """Test that auth service is accessible on the correct port."""
        result = { }
        "port": self.correct_port,
        "accessible": False,
        "health_status": None,
        "response_time_ms": None,
        "error": None
    

        try:
        import time
        start_time = time.time()

        async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get("formatted_string")

        result["response_time_ms"] = (time.time() - start_time) * 1000
        result["accessible"] = True
        result["health_status"] = response.status_code

        if response.status_code == 200:
        response_data = response.json()
                # Verify this is actually the auth service
        service_name = response_data.get("service", "").lower()
        if "auth" in service_name:
        result["verified_auth_service"] = True
        else:
        result["verified_auth_service"] = False
        result["actual_service"] = service_name
        else:
        result["error"] = ""

        except httpx.ConnectError:
        result["error"] = ""
        except httpx.TimeoutException:
        result["error"] = ""
        except Exception as e:
        result["error"] = ""

        return result

    async def validate_auth_endpoints(self) -> Dict[str, Any]:
        """Validate that key auth endpoints are available."""
        endpoints = { }
        "/health": "Health check endpoint",
        "/": "Root endpoint",
        "/oauth/google": "Google OAuth endpoint",
        "/oauth/google/callback": "Google OAuth callback"
    

        results = {}

        async with httpx.AsyncClient(timeout=5.0) as client:
        for endpoint, description in endpoints.items():
        endpoint_result = { }
        "description": description,
        "accessible": False,
        "status_code": None,
        "error": None
            

        try:
        response = await client.get("formatted_string")
        endpoint_result["accessible"] = True
        endpoint_result["status_code"] = response.status_code

                # For OAuth endpoints, redirects (302) are expected
        if endpoint.startswith("/oauth") and response.status_code in [302, 307, 308]:
        endpoint_result["expected_redirect"] = True

        except httpx.ConnectError:
        endpoint_result["error"] = "Connection refused"
        except httpx.TimeoutException:
        endpoint_result["error"] = "Timeout"
        except Exception as e:
        endpoint_result["error"] = str(e)

        results[endpoint] = endpoint_result

        return results


@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_auth_service_port_8081_accessibility():
'''
'''
Test that auth service is accessible on port 8081 as configured in dev launcher.

This test ensures the port configuration matches between the dev launcher
configuration and the actual running auth service.
'''
'''
pass
validator = AuthServicePortValidator()
result = await validator.validate_auth_service_accessibility()

                                    # Print results for debugging
print(f" )"
=== AUTH SERVICE PORT VALIDATION ===")"
print("")
print("")
print("")
print("" if result['response_time_ms'] else "N/A")

if result['error']:
    print("")

                                        # Validate auth service is accessible
assert result['accessible'], ""

                                        # Validate health endpoint responds successfully
assert result['health_status'] == 200, ""

                                        # Validate response time is reasonable (under 5 seconds)
assert result['response_time_ms'] < 5000, ""

                                        # If we can verify it's the auth service, do so'
if 'verified_auth_service' in result:
    pass
assert result['verified_auth_service'], ""


@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_auth_service_endpoints_availability():
'''
'''
Test that key auth service endpoints are available.

This validates the auth service is properly initialized with its main endpoints.
'''
'''
pass
validator = AuthServicePortValidator()
results = await validator.validate_auth_endpoints()

print(f" )"
=== AUTH SERVICE ENDPOINTS ===")"
for endpoint, result in results.items():
status = " PASS: " if result['accessible'] else " FAIL: "
print("")
if result['error']:
    print("")

                                                        # Health endpoint must be accessible
health_result = results.get('/health')
assert health_result['accessible'], ""
assert health_result['status_code'] == 200, ""

                                                        # Root endpoint should be accessible
root_result = results.get('/')
assert root_result['accessible'], ""
assert root_result['status_code'] == 200, ""

                                                        # OAuth endpoints should be accessible (may redirect, which is expected)
oauth_google = results.get('/oauth/google')
if oauth_google['accessible']:
                                                            # OAuth endpoints typically redirect, so 200 or 3xx are acceptable
acceptable_codes = [200, 302, 307, 308, 400]  # 400 might occur if no proper OAuth request
assert oauth_google['status_code'] in acceptable_codes, \
""


@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_auth_service_timing_expectations():
'''
'''
Test auth service response timing meets expectations for WebSocket handshakes.

This ensures the auth service responds quickly enough for WebSocket authentication
during connection establishment.
'''
'''
pass
validator = AuthServicePortValidator()

                                                                # Test multiple rapid requests to simulate WebSocket handshake timing
request_times = []

for i in range(5):
result = await validator.validate_auth_service_accessibility()

if result['accessible'] and result['response_time_ms']:
    pass
request_times.append(result['response_time_ms'])

                                                                        # Small delay between requests
await asyncio.sleep(0.1)

                                                                        # Validate we got some successful requests
assert len(request_times) >= 3, "Not enough successful auth service requests for timing validation"

                                                                        # Calculate timing statistics
avg_response_time = sum(request_times) / len(request_times)
max_response_time = max(request_times)
min_response_time = min(request_times)

print(f" )"
=== AUTH SERVICE TIMING ANALYSIS ===")"
print("")
print("")
print("")
print("")

                                                                        # Validate timing expectations for WebSocket handshakes
                                                                        # WebSocket auth should complete within 2 seconds for good UX
assert avg_response_time < 2000, ""
assert max_response_time < 5000, ""

                                                                        # Consistency check - responses should be reasonably consistent
if len(request_times) > 2:
    pass
response_range = max_response_time - min_response_time
assert response_range < 3000, ""


if __name__ == "__main__":
    pass
async def main():
pass
validator = AuthServicePortValidator()

print("=== AUTH SERVICE PORT VALIDATION ===")
result = await validator.validate_auth_service_accessibility()
print("")

print("")
=== AUTH SERVICE ENDPOINTS ===")"
endpoints = await validator.validate_auth_endpoints()
for endpoint, result in endpoints.items():
    print("")

asyncio.run(main())
