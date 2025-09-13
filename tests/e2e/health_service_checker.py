"""

Service Health Checker Module



Business Value Justification (BVJ):

- Segment: Enterprise  

- Business Goal: Service availability monitoring

- Value Impact: $8K MRR from uptime monitoring

- Revenue Impact: Prevents cascading service failures



Focused module for HTTP service health checking:

- Service endpoint validation

- Inter-service communication testing

- Timeout handling with detailed error reporting

- Response validation and service identification



CRITICAL: Maximum 300 lines, async/await pattern, comprehensive error handling

"""



import asyncio

import time

import httpx

from typing import Dict, Any



from netra_backend.app.logging_config import central_logger

from tests.e2e.health_check_core import (

    HealthCheckResult, SERVICE_ENDPOINTS,

    create_service_error_result, create_timeout_result,

    create_healthy_result, validate_service_response

)



logger = central_logger.get_logger(__name__)





class ServiceHealthChecker:

    """HTTP service health checker with timeout and error handling."""

    

    def __init__(self):

        self.client_timeout = 30.0  # Overall client timeout

    

    async def check_service_endpoint(self, service_name: str, config: Dict[str, Any]) -> HealthCheckResult:

        """Check individual service health endpoint with comprehensive error handling and multiple URL fallbacks."""

        start_time = time.time()

        

        # Support both single URL (legacy) and multiple URLs (new format)

        urls = config.get("urls", [config.get("url")]) if config.get("urls") else [config.get("url")]

        urls = [url for url in urls if url]  # Filter out None values

        

        last_error = None

        

        for url in urls:

            try:

                async with httpx.AsyncClient(timeout=config["timeout"], follow_redirects=True) as client:

                    response = await client.get(url)

                    response_time_ms = (time.time() - start_time) * 1000

                    

                    result = self._process_service_response(

                        service_name, response, response_time_ms, config

                    )

                    

                    # If this URL succeeded, return the result

                    if result.is_healthy():

                        logger.info(f"Service {service_name} health check succeeded at {url}")

                        return result

                    else:

                        logger.debug(f"Service {service_name} returned unhealthy status at {url}: {result.error}")

                        last_error = result.error

                        

            except asyncio.TimeoutError:

                last_error = f"Timeout at {url}"

                logger.debug(f"Service {service_name} timeout at {url}")

                continue

                

            except httpx.ConnectError as e:

                last_error = f"Connection failed at {url}: {str(e)}"

                logger.debug(f"Service {service_name} connection failed at {url}: {e}")

                continue

                

            except httpx.RequestError as e:

                last_error = f"Request error at {url}: {str(e)}"

                logger.debug(f"Service {service_name} request error at {url}: {e}")

                continue

                

            except Exception as e:

                last_error = f"Unexpected error at {url}: {str(e)}"

                logger.debug(f"Service {service_name} unexpected error at {url}: {e}")

                continue

        

        # If we get here, all URLs failed

        response_time_ms = (time.time() - start_time) * 1000

        

        # Try port connectivity as final fallback

        if await self._check_port_fallback(service_name, config):

            return create_service_error_result(

                service_name, 

                f"Port accessible but health endpoints failed. Last error: {last_error}", 

                response_time_ms

            )

        

        return create_service_error_result(

            service_name, 

            f"All endpoints failed. Last error: {last_error}. URLs tried: {urls}", 

            response_time_ms

        )

    

    async def _check_port_fallback(self, service_name: str, config: Dict[str, Any]) -> bool:

        """Check if service ports are accessible as a fallback diagnostic."""

        import socket

        

        fallback_ports = config.get("fallback_ports", [])

        for port in fallback_ports:

            try:

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                sock.settimeout(2.0)

                result = sock.connect_ex(('localhost', port))

                sock.close()

                if result == 0:

                    logger.info(f"Service {service_name} port {port} is accessible")

                    return True

            except Exception:

                continue

        return False

    

    def _process_service_response(self, service_name: str, response: httpx.Response, 

                                response_time_ms: float, config: Dict[str, Any]) -> HealthCheckResult:

        """Process HTTP response and validate service health."""

        if response.status_code != 200:

            return create_service_error_result(

                service_name, f"HTTP {response.status_code}", response_time_ms

            )

        

        # Handle different response types

        if config.get("check_type") == "build_verification":

            return self._validate_build_response(service_name, response, response_time_ms)

        

        return self._validate_health_response(service_name, response, response_time_ms, config)

    

    def _validate_health_response(self, service_name: str, response: httpx.Response,

                                response_time_ms: float, config: Dict[str, Any]) -> HealthCheckResult:

        """Validate health endpoint JSON response."""

        try:

            response_data = response.json()

            expected_service = config.get("expected_service")

            

            if validate_service_response(response_data, expected_service):

                return create_healthy_result(service_name, response_time_ms, response_data)

            else:

                error_msg = f"Service mismatch: expected {expected_service}, got {response_data.get('service')}"

                return create_service_error_result(service_name, error_msg, response_time_ms)

                

        except Exception as e:

            return create_service_error_result(

                service_name, f"Invalid JSON response: {str(e)}", response_time_ms

            )

    

    def _validate_build_response(self, service_name: str, response: httpx.Response, 

                               response_time_ms: float) -> HealthCheckResult:

        """Validate frontend build/static content response."""

        content_length = len(response.content)

        

        # Simple build validation - should have meaningful content

        if content_length > 1000:  # Reasonable threshold for built frontend

            return create_healthy_result(

                service_name, response_time_ms, 

                {"content_length": content_length, "build_status": "valid"}

            )

        else:

            return create_service_error_result(

                service_name, f"Build appears incomplete: {content_length} bytes", response_time_ms

            )

    

    async def check_inter_service_communication(self) -> HealthCheckResult:

        """Test inter-service communication by checking service-to-service accessibility."""

        start_time = time.time()

        

        try:

            # Test critical service pair: auth and backend

            auth_config = SERVICE_ENDPOINTS.get("auth", {})

            backend_config = SERVICE_ENDPOINTS.get("backend", {})

            

            if not auth_config or not backend_config:

                return create_service_error_result(

                    "inter_service", "Missing service configuration", 0

                )

            

            return await self._test_service_pair_communication(

                auth_config, backend_config, start_time

            )

            

        except Exception as e:

            response_time_ms = (time.time() - start_time) * 1000

            return create_service_error_result(

                "inter_service", f"Communication test failed: {str(e)}", response_time_ms

            )

    

    async def _test_service_pair_communication(self, auth_config: Dict, backend_config: Dict, 

                                             start_time: float) -> HealthCheckResult:

        """Test communication between auth and backend services."""

        timeout = min(auth_config.get("timeout", 5.0), backend_config.get("timeout", 5.0))

        

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:

            # Parallel health checks to both services

            tasks = [

                client.get(auth_config["url"]),

                client.get(backend_config["url"])

            ]

            

            try:

                responses = await asyncio.gather(*tasks, return_exceptions=True)

                response_time_ms = (time.time() - start_time) * 1000

                

                return self._evaluate_service_pair_responses(responses, response_time_ms)

                

            except Exception as e:

                response_time_ms = (time.time() - start_time) * 1000

                return create_service_error_result(

                    "inter_service", f"Service pair test failed: {str(e)}", response_time_ms

                )

    

    def _evaluate_service_pair_responses(self, responses: list, response_time_ms: float) -> HealthCheckResult:

        """Evaluate responses from service pair communication test."""

        auth_response, backend_response = responses

        

        # Check for exceptions

        if isinstance(auth_response, Exception):

            return create_service_error_result(

                "inter_service", f"Auth service unreachable: {auth_response}", response_time_ms

            )

        

        if isinstance(backend_response, Exception):

            return create_service_error_result(

                "inter_service", f"Backend service unreachable: {backend_response}", response_time_ms

            )

        

        # Check response codes

        if auth_response.status_code == 200 and backend_response.status_code == 200:

            return create_healthy_result(

                "inter_service", response_time_ms,

                {

                    "auth_status": auth_response.status_code,

                    "backend_status": backend_response.status_code,

                    "communication": "successful"

                }

            )

        else:

            return create_service_error_result(

                "inter_service", 

                f"Service communication failed: auth={auth_response.status_code}, backend={backend_response.status_code}",

                response_time_ms

            )

    

    async def check_all_services(self) -> list[HealthCheckResult]:

        """Check all configured service endpoints concurrently."""

        tasks = []

        

        # Add service endpoint checks (exclude frontend for now)

        for service_name, config in SERVICE_ENDPOINTS.items():

            if service_name != "frontend":  # Skip frontend for basic health checks

                tasks.append(self.check_service_endpoint(service_name, config))

        

        # Add inter-service communication check

        tasks.append(self.check_inter_service_communication())

        

        # Execute all checks concurrently

        results = await asyncio.gather(*tasks, return_exceptions=True)

        

        # Process results and handle any exceptions

        processed_results = []

        for i, result in enumerate(results):

            if isinstance(result, Exception):

                processed_results.append(create_service_error_result(

                    f"service_check_{i}", f"Check failed: {str(result)}", 0

                ))

            else:

                processed_results.append(result)

        

        return processed_results

    

    async def check_critical_services_only(self) -> list[HealthCheckResult]:

        """Check only critical services for faster health validation."""

        tasks = []

        

        for service_name, config in SERVICE_ENDPOINTS.items():

            if config.get("critical", False):

                tasks.append(self.check_service_endpoint(service_name, config))

        

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [r for r in results if not isinstance(r, Exception)]





# Export main class

__all__ = ['ServiceHealthChecker']

