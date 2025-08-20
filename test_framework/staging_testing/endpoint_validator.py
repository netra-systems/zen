"""
Staging endpoint validation implementation.

Validates Cloud Run staging endpoints and API contracts.
"""

import aiohttp
import asyncio
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
import time
from pathlib import Path
import yaml

from ..unified.base_interfaces import (
    IDeploymentValidator,
    BaseTestComponent,
    ServiceConfig,
    ServiceStatus,
    TestEnvironment,
    HealthCheckResult
)
from ..gcp_integration.base import GCPConfig, CloudRunService


@dataclass
class EndpointTestResult:
    """Result of an endpoint test."""
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    success: bool
    error_message: Optional[str] = None
    response_body: Optional[Any] = None
    headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


@dataclass
class APIContractViolation:
    """Represents an API contract violation."""
    endpoint: str
    method: str
    violation_type: str  # missing_field, type_mismatch, invalid_status
    expected: Any
    actual: Any
    path: str  # JSON path to violation


class StagingEndpointValidator(BaseTestComponent, IDeploymentValidator):
    """Validates staging environment endpoints."""
    
    def __init__(
        self,
        staging_config: Dict[str, Any],
        gcp_config: Optional[GCPConfig] = None
    ):
        super().__init__(staging_config)
        self.staging_config = staging_config
        self.gcp_config = gcp_config
        self._session: Optional[aiohttp.ClientSession] = None
        self._auth_token: Optional[str] = None
        self._test_results: List[EndpointTestResult] = []
    
    async def initialize(self) -> None:
        """Initialize the validator."""
        await super().initialize()
        
        # Create HTTP session with timeout
        timeout = aiohttp.ClientTimeout(total=30)
        self._session = aiohttp.ClientSession(timeout=timeout)
        
        # Get auth token if needed
        if self.staging_config.get('requires_auth'):
            self._auth_token = await self._get_auth_token()
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._session:
            await self._session.close()
        await super().cleanup()
    
    async def validate_deployment(
        self,
        service_configs: List[ServiceConfig]
    ) -> Dict[str, bool]:
        """Validate that services are properly deployed."""
        self.validate_initialized()
        
        results = {}
        
        for config in service_configs:
            is_deployed = await self._check_service_deployed(config)
            results[config.name] = is_deployed
        
        return results
    
    async def validate_api_contracts(
        self,
        openapi_spec_path: str
    ) -> Dict[str, List[str]]:
        """Validate API contracts against OpenAPI spec."""
        self.validate_initialized()
        
        # Load OpenAPI spec
        spec_path = Path(openapi_spec_path)
        if not spec_path.exists():
            raise FileNotFoundError(f"OpenAPI spec not found: {openapi_spec_path}")
        
        with open(spec_path, 'r') as f:
            if spec_path.suffix == '.yaml':
                openapi_spec = yaml.safe_load(f)
            else:
                openapi_spec = json.load(f)
        
        violations = {}
        
        # Test each endpoint in the spec
        for path, path_spec in openapi_spec.get('paths', {}).items():
            for method, operation_spec in path_spec.items():
                if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    continue
                
                endpoint_violations = await self._validate_endpoint_contract(
                    path,
                    method.upper(),
                    operation_spec
                )
                
                if endpoint_violations:
                    key = f"{method.upper()} {path}"
                    violations[key] = [
                        f"{v.violation_type}: {v.path} - expected {v.expected}, got {v.actual}"
                        for v in endpoint_violations
                    ]
        
        return violations
    
    async def validate_dependencies(
        self,
        service_configs: List[ServiceConfig]
    ) -> Dict[str, List[str]]:
        """Validate service dependencies are met."""
        self.validate_initialized()
        
        dependency_issues = {}
        
        for config in service_configs:
            issues = []
            
            for dep in config.dependencies:
                # Find dependency config
                dep_config = next(
                    (c for c in service_configs if c.name == dep),
                    None
                )
                
                if not dep_config:
                    issues.append(f"Dependency {dep} not found in configuration")
                    continue
                
                # Check if dependency is healthy
                health_result = await self._check_health(dep_config)
                if health_result.status != ServiceStatus.HEALTHY:
                    issues.append(
                        f"Dependency {dep} is not healthy: {health_result.status.value}"
                    )
                
                # Check if dependency is reachable from service
                if not await self._check_connectivity(config, dep_config):
                    issues.append(f"Cannot connect to dependency {dep}")
            
            if issues:
                dependency_issues[config.name] = issues
        
        return dependency_issues
    
    async def validate_health_endpoints(
        self,
        service_configs: List[ServiceConfig]
    ) -> List[HealthCheckResult]:
        """Validate all service health endpoints."""
        self.validate_initialized()
        
        tasks = []
        for config in service_configs:
            tasks.append(self._check_health(config))
        
        return await asyncio.gather(*tasks)
    
    async def run_smoke_tests(
        self,
        test_cases: List[Dict[str, Any]]
    ) -> List[EndpointTestResult]:
        """Run smoke tests against staging endpoints."""
        self.validate_initialized()
        
        results = []
        
        for test_case in test_cases:
            result = await self._run_endpoint_test(test_case)
            results.append(result)
            self._test_results.append(result)
        
        return results
    
    async def validate_ssl_certificates(
        self,
        service_urls: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Validate SSL certificates for services."""
        self.validate_initialized()
        
        cert_info = {}
        
        for url in service_urls:
            info = await self._check_ssl_certificate(url)
            cert_info[url] = info
        
        return cert_info
    
    async def test_cors_configuration(
        self,
        service_configs: List[ServiceConfig]
    ) -> Dict[str, bool]:
        """Test CORS configuration for services."""
        self.validate_initialized()
        
        cors_results = {}
        
        for config in service_configs:
            if not config.url:
                continue
            
            # Send OPTIONS request to test CORS
            headers = {
                'Origin': 'https://example.com',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            try:
                async with self._session.options(
                    config.url,
                    headers=headers
                ) as response:
                    cors_headers = {
                        'access_control_allow_origin': response.headers.get(
                            'Access-Control-Allow-Origin'
                        ),
                        'access_control_allow_methods': response.headers.get(
                            'Access-Control-Allow-Methods'
                        ),
                        'access_control_allow_headers': response.headers.get(
                            'Access-Control-Allow-Headers'
                        )
                    }
                    
                    # Check if CORS is properly configured
                    cors_results[config.name] = (
                        cors_headers['access_control_allow_origin'] is not None and
                        cors_headers['access_control_allow_methods'] is not None
                    )
            except:
                cors_results[config.name] = False
        
        return cors_results
    
    async def measure_endpoint_performance(
        self,
        endpoints: List[Dict[str, str]],
        iterations: int = 10
    ) -> Dict[str, Dict[str, float]]:
        """Measure performance of endpoints."""
        self.validate_initialized()
        
        performance_data = {}
        
        for endpoint in endpoints:
            url = endpoint['url']
            method = endpoint.get('method', 'GET')
            
            response_times = []
            
            for _ in range(iterations):
                start_time = time.perf_counter()
                
                try:
                    async with self._session.request(
                        method,
                        url,
                        headers=self._get_auth_headers()
                    ) as response:
                        await response.read()
                        response_time = (time.perf_counter() - start_time) * 1000
                        response_times.append(response_time)
                except:
                    pass
            
            if response_times:
                response_times.sort()
                performance_data[url] = {
                    'min_ms': min(response_times),
                    'max_ms': max(response_times),
                    'avg_ms': sum(response_times) / len(response_times),
                    'p50_ms': response_times[len(response_times) // 2],
                    'p95_ms': response_times[int(len(response_times) * 0.95)],
                    'p99_ms': response_times[int(len(response_times) * 0.99)]
                }
        
        return performance_data
    
    async def _check_service_deployed(self, config: ServiceConfig) -> bool:
        """Check if a service is deployed."""
        if not config.url:
            return False
        
        try:
            async with self._session.get(
                f"{config.url}{config.health_endpoint}",
                headers=self._get_auth_headers()
            ) as response:
                return response.status < 500
        except:
            return False
    
    async def _check_health(self, config: ServiceConfig) -> HealthCheckResult:
        """Check health of a service."""
        if not config.url:
            return HealthCheckResult(
                service_name=config.name,
                status=ServiceStatus.UNKNOWN,
                response_time_ms=0,
                error_message="No URL configured"
            )
        
        start_time = time.perf_counter()
        
        try:
            async with self._session.get(
                f"{config.url}{config.health_endpoint}",
                headers=self._get_auth_headers(),
                timeout=aiohttp.ClientTimeout(total=config.timeout)
            ) as response:
                response_time = (time.perf_counter() - start_time) * 1000
                
                if response.status == 200:
                    status = ServiceStatus.HEALTHY
                elif response.status < 500:
                    status = ServiceStatus.DEGRADED
                else:
                    status = ServiceStatus.UNHEALTHY
                
                body = await response.json() if response.content_type == 'application/json' else {}
                
                return HealthCheckResult(
                    service_name=config.name,
                    status=status,
                    response_time_ms=response_time,
                    details=body
                )
        except asyncio.TimeoutError:
            return HealthCheckResult(
                service_name=config.name,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=(time.perf_counter() - start_time) * 1000,
                error_message="Health check timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                service_name=config.name,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=(time.perf_counter() - start_time) * 1000,
                error_message=str(e)
            )
    
    async def _check_connectivity(
        self,
        from_service: ServiceConfig,
        to_service: ServiceConfig
    ) -> bool:
        """Check if one service can connect to another."""
        # In staging, we assume services can connect if both are healthy
        from_health = await self._check_health(from_service)
        to_health = await self._check_health(to_service)
        
        return (
            from_health.status == ServiceStatus.HEALTHY and
            to_health.status == ServiceStatus.HEALTHY
        )
    
    async def _validate_endpoint_contract(
        self,
        path: str,
        method: str,
        operation_spec: Dict[str, Any]
    ) -> List[APIContractViolation]:
        """Validate a single endpoint against its contract."""
        violations = []
        
        # Build full URL
        base_url = self.staging_config.get('base_url', '')
        full_url = f"{base_url}{path}"
        
        # Make request
        try:
            async with self._session.request(
                method,
                full_url,
                headers=self._get_auth_headers()
            ) as response:
                # Check status code
                expected_statuses = list(operation_spec.get('responses', {}).keys())
                if str(response.status) not in expected_statuses:
                    violations.append(APIContractViolation(
                        endpoint=path,
                        method=method,
                        violation_type='invalid_status',
                        expected=expected_statuses,
                        actual=response.status,
                        path='status_code'
                    ))
                
                # Check response schema if 200
                if response.status == 200 and response.content_type == 'application/json':
                    response_body = await response.json()
                    schema = operation_spec.get('responses', {}).get('200', {}).get('content', {}).get('application/json', {}).get('schema')
                    
                    if schema:
                        schema_violations = self._validate_json_schema(
                            response_body,
                            schema,
                            path
                        )
                        violations.extend(schema_violations)
        except Exception as e:
            violations.append(APIContractViolation(
                endpoint=path,
                method=method,
                violation_type='request_failed',
                expected='successful_request',
                actual=str(e),
                path='request'
            ))
        
        return violations
    
    def _validate_json_schema(
        self,
        data: Any,
        schema: Dict[str, Any],
        base_path: str
    ) -> List[APIContractViolation]:
        """Validate JSON data against a schema."""
        violations = []
        
        # Simple schema validation (would use jsonschema library in production)
        if schema.get('type') == 'object' and isinstance(data, dict):
            required_fields = schema.get('required', [])
            properties = schema.get('properties', {})
            
            # Check required fields
            for field in required_fields:
                if field not in data:
                    violations.append(APIContractViolation(
                        endpoint=base_path,
                        method='',
                        violation_type='missing_field',
                        expected=field,
                        actual='missing',
                        path=f'$.{field}'
                    ))
            
            # Check field types
            for field, field_schema in properties.items():
                if field in data:
                    expected_type = field_schema.get('type')
                    actual_type = type(data[field]).__name__
                    
                    type_mapping = {
                        'string': 'str',
                        'integer': 'int',
                        'number': 'float',
                        'boolean': 'bool',
                        'array': 'list',
                        'object': 'dict'
                    }
                    
                    if expected_type and type_mapping.get(expected_type) != actual_type:
                        violations.append(APIContractViolation(
                            endpoint=base_path,
                            method='',
                            violation_type='type_mismatch',
                            expected=expected_type,
                            actual=actual_type,
                            path=f'$.{field}'
                        ))
        
        return violations
    
    async def _run_endpoint_test(self, test_case: Dict[str, Any]) -> EndpointTestResult:
        """Run a single endpoint test."""
        url = test_case['url']
        method = test_case.get('method', 'GET')
        headers = test_case.get('headers', {})
        body = test_case.get('body')
        expected_status = test_case.get('expected_status', 200)
        
        # Add auth headers
        headers.update(self._get_auth_headers())
        
        start_time = time.perf_counter()
        
        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                json=body if body else None
            ) as response:
                response_time = (time.perf_counter() - start_time) * 1000
                response_body = await response.text()
                
                try:
                    response_body = json.loads(response_body)
                except:
                    pass
                
                return EndpointTestResult(
                    endpoint=url,
                    method=method,
                    status_code=response.status,
                    response_time_ms=response_time,
                    success=response.status == expected_status,
                    response_body=response_body,
                    headers=dict(response.headers)
                )
        except Exception as e:
            return EndpointTestResult(
                endpoint=url,
                method=method,
                status_code=0,
                response_time_ms=(time.perf_counter() - start_time) * 1000,
                success=False,
                error_message=str(e)
            )
    
    async def _check_ssl_certificate(self, url: str) -> Dict[str, Any]:
        """Check SSL certificate for a URL."""
        import ssl
        import certifi
        
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        try:
            async with self._session.get(url, ssl=ssl_context) as response:
                # Get certificate info from the connection
                return {
                    'valid': True,
                    'status_code': response.status
                }
        except ssl.SSLError as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    async def _get_auth_token(self) -> Optional[str]:
        """Get authentication token for staging."""
        auth_config = self.staging_config.get('auth', {})
        
        if auth_config.get('type') == 'oauth2':
            # Implement OAuth2 flow
            pass
        elif auth_config.get('type') == 'api_key':
            return auth_config.get('api_key')
        elif auth_config.get('type') == 'jwt':
            # Generate JWT token
            pass
        
        return None
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        if self._auth_token:
            return {'Authorization': f'Bearer {self._auth_token}'}
        return {}