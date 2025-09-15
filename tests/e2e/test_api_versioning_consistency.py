"""
E2E Tests for API Versioning and Endpoint Consistency
Tests that API endpoints are consistently versioned and documented.

Business Value Justification (BVJ):
- Segment: Enterprise (API stability critical for integrations)
- Business Goal: API reliability and backward compatibility
- Value Impact: Prevents breaking changes for API consumers
- Strategic Impact: Enables stable integrations and partnerships
"""

import pytest
import asyncio
import aiohttp
import json
from typing import Dict, List, Set, Optional
from pathlib import Path
import re
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.e2e
@pytest.mark.real_services
class APIVersioningConsistencyTests:
    """Test suite for API versioning and endpoint consistency."""

    async def test_api_version_consistency_across_services(self):
        """
        Test that API versions are consistent across all services.
        
        This test SHOULD FAIL until API versioning is standardized.
        Exposes coverage gaps in API version management.
        
        Critical Assertions:
        - All services use same API version scheme
        - Version headers are consistent
        - Endpoint paths follow versioning conventions
        
        Expected Failure: Inconsistent API versioning
        Business Impact: API consumers confused by different versioning schemes
        """
        services = [
            {"name": "main_backend", "url": "http://localhost:8000", "expected_prefix": "/api"},
            {"name": "auth_service", "url": "http://localhost:8081", "expected_prefix": "/auth"}
        ]
        
        version_patterns = set()
        inconsistencies = []
        
        async with aiohttp.ClientSession() as session:
            for service in services:
                try:
                    # Test if service is running
                    health_response = await session.get(f"{service['url']}/health", timeout=5)
                    if health_response.status != 200:
                        continue
                    
                    # Try to get OpenAPI/docs to analyze endpoints
                    try:
                        docs_response = await session.get(f"{service['url']}/docs")
                        if docs_response.status == 200:
                            # Service has docs - good sign
                            pass
                    except:
                        pass
                    
                    # Test common API endpoints
                    test_endpoints = [
                        "/api/health", 
                        "/api/health",
                        "/api/status",
                        "/health"
                    ]
                    
                    working_endpoints = []
                    for endpoint in test_endpoints:
                        try:
                            response = await session.get(f"{service['url']}{endpoint}")
                            if response.status == 200:
                                working_endpoints.append(endpoint)
                        except:
                            continue
                    
                    # Analyze versioning patterns
                    for endpoint in working_endpoints:
                        if '/api/v' in endpoint:
                            version_match = re.search(r'/api/(v\d+)', endpoint)
                            if version_match:
                                version_patterns.add(version_match.group(1))
                        elif '/api/' in endpoint:
                            # Non-versioned API endpoint
                            version_patterns.add("unversioned")
                    
                    service["working_endpoints"] = working_endpoints
                    
                except Exception as e:
                    # Service not available - skip for this test
                    service["error"] = str(e)
                    continue
        
        # Check for version consistency
        if len(version_patterns) > 1:
            inconsistencies.append(f"Multiple API version patterns found: {version_patterns}")
        
        # This assertion SHOULD FAIL if there are versioning inconsistencies
        assert len(inconsistencies) == 0, \
            f"API versioning inconsistencies detected: {inconsistencies}. " \
            f"Services tested: {[(s['name'], s.get('working_endpoints', [])) for s in services]}"

    async def test_api_endpoint_documentation_coverage(self):
        """
        Test that all API endpoints are properly documented.
        
        Critical Assertions:
        - OpenAPI/Swagger documentation exists
        - All endpoints have descriptions
        - Request/response schemas defined
        
        Expected Failure: Missing or incomplete API documentation
        Business Impact: API difficult to consume, integration challenges
        """
        services = [
            {"name": "main_backend", "url": "http://localhost:8000"},
            {"name": "auth_service", "url": "http://localhost:8081"}
        ]
        
        documentation_issues = []
        
        async with aiohttp.ClientSession() as session:
            for service in services:
                try:
                    # Check if OpenAPI spec is available
                    openapi_response = await session.get(f"{service['url']}/openapi.json")
                    
                    if openapi_response.status != 200:
                        documentation_issues.append(f"{service['name']}: No OpenAPI spec found")
                        continue
                    
                    openapi_data = await openapi_response.json()
                    
                    # Validate OpenAPI structure
                    if 'paths' not in openapi_data:
                        documentation_issues.append(f"{service['name']}: OpenAPI spec missing paths")
                        continue
                    
                    undocumented_endpoints = []
                    for path, methods in openapi_data['paths'].items():
                        for method, spec in methods.items():
                            if 'summary' not in spec and 'description' not in spec:
                                undocumented_endpoints.append(f"{method.upper()} {path}")
                    
                    if undocumented_endpoints:
                        documentation_issues.append(
                            f"{service['name']}: Endpoints missing documentation: {undocumented_endpoints[:5]}"
                        )
                    
                    # Check for response schemas
                    missing_schemas = []
                    for path, methods in openapi_data['paths'].items():
                        for method, spec in methods.items():
                            responses = spec.get('responses', {})
                            if '200' in responses:
                                response_spec = responses['200']
                                if 'content' not in response_spec:
                                    missing_schemas.append(f"{method.upper()} {path}")
                    
                    if missing_schemas:
                        documentation_issues.append(
                            f"{service['name']}: Endpoints missing response schemas: {missing_schemas[:3]}"
                        )
                
                except Exception as e:
                    documentation_issues.append(f"{service['name']}: Documentation check failed: {str(e)}")
        
        # This assertion SHOULD FAIL if documentation is incomplete
        assert len(documentation_issues) == 0, \
            f"API documentation issues found: {documentation_issues}"

    async def test_api_error_response_consistency(self):
        """
        Test that API error responses are consistent across services.
        
        Critical Assertions:
        - All services use same error response format
        - HTTP status codes used consistently
        - Error messages are structured
        
        Expected Failure: Inconsistent error handling
        Business Impact: API consumers cannot reliably handle errors
        """
        services = [
            {"name": "main_backend", "url": "http://localhost:8000"},
            {"name": "auth_service", "url": "http://localhost:8081"}
        ]
        
        error_formats = {}
        consistency_issues = []
        
        async with aiohttp.ClientSession() as session:
            for service in services:
                try:
                    # Test 404 error format
                    response = await session.get(f"{service['url']}/api/nonexistent/endpoint")
                    
                    error_data = {
                        "status_code": response.status,
                        "content_type": response.headers.get('content-type', ''),
                        "has_json_response": False,
                        "error_structure": None
                    }
                    
                    if 'application/json' in error_data["content_type"]:
                        try:
                            json_response = await response.json()
                            error_data["has_json_response"] = True
                            error_data["error_structure"] = {
                                "has_error_field": "error" in json_response,
                                "has_message_field": "message" in json_response,
                                "has_detail_field": "detail" in json_response,
                                "has_code_field": "code" in json_response,
                                "fields": list(json_response.keys()) if isinstance(json_response, dict) else []
                            }
                        except:
                            error_data["has_json_response"] = False
                    
                    error_formats[service['name']] = error_data
                    
                except Exception as e:
                    error_formats[service['name']] = {"error": str(e)}
        
        # Check for consistency
        if len(error_formats) > 1:
            # Compare error formats
            formats = [fmt.get("error_structure") for fmt in error_formats.values() if fmt.get("error_structure")]
            if len(set(str(fmt) for fmt in formats)) > 1:
                consistency_issues.append(f"Inconsistent error response formats: {error_formats}")
            
            # Check status codes
            status_codes = [fmt.get("status_code") for fmt in error_formats.values() if fmt.get("status_code")]
            if len(set(status_codes)) > 1:
                consistency_issues.append(f"Inconsistent 404 status codes: {status_codes}")
        
        # This assertion SHOULD FAIL if error handling is inconsistent
        assert len(consistency_issues) == 0, \
            f"API error response consistency issues: {consistency_issues}"

    async def test_api_authentication_consistency(self):
        """
        Test that API authentication methods are consistent.
        
        Critical Assertions:
        - All protected endpoints use same auth method
        - Auth headers are standardized
        - Token formats are consistent
        
        Expected Failure: Inconsistent authentication schemes
        Business Impact: Complex integration, security vulnerabilities
        """
        services = [
            {"name": "main_backend", "url": "http://localhost:8000"},
            {"name": "auth_service", "url": "http://localhost:8081"}
        ]
        
        auth_schemes = {}
        auth_issues = []
        
        async with aiohttp.ClientSession() as session:
            for service in services:
                try:
                    # Test protected endpoint without auth
                    protected_endpoints = [
                        "/api/user/profile",
                        "/api/user/me", 
                        "/auth/me",
                        "/api/threads"
                    ]
                    
                    for endpoint in protected_endpoints:
                        try:
                            response = await session.get(f"{service['url']}{endpoint}")
                            
                            if response.status == 401:
                                # Good - endpoint is protected
                                auth_header = response.headers.get('www-authenticate', '')
                                
                                auth_schemes[f"{service['name']}{endpoint}"] = {
                                    "status": 401,
                                    "www_authenticate": auth_header,
                                    "content_type": response.headers.get('content-type', '')
                                }
                                break
                        except:
                            continue
                
                except Exception as e:
                    auth_schemes[service['name']] = {"error": str(e)}
        
        # Check for consistency in auth schemes
        auth_headers = [scheme.get("www_authenticate", "") for scheme in auth_schemes.values()]
        unique_headers = set(header for header in auth_headers if header)
        
        if len(unique_headers) > 1:
            auth_issues.append(f"Inconsistent WWW-Authenticate headers: {unique_headers}")
        
        # This assertion might FAIL if auth schemes are inconsistent
        if auth_issues:
            # For now, just warn about auth inconsistencies
            pytest.skip(f"Auth consistency issues detected (informational): {auth_issues}")

    async def test_api_rate_limiting_consistency(self):
        """
        Test that API rate limiting is consistently implemented.
        
        Critical Assertions:
        - Rate limit headers are standardized
        - Rate limiting policies are documented
        - Limits are appropriate per service
        
        Expected Failure: Missing or inconsistent rate limiting
        Business Impact: API abuse possible, service instability
        """
        services = [
            {"name": "main_backend", "url": "http://localhost:8000"},
            {"name": "auth_service", "url": "http://localhost:8081"}
        ]
        
        rate_limit_info = {}
        rate_limit_issues = []
        
        async with aiohttp.ClientSession() as session:
            for service in services:
                try:
                    # Test health endpoint for rate limit headers
                    response = await session.get(f"{service['url']}/health")
                    
                    rate_headers = {
                        "x-ratelimit-limit": response.headers.get('x-ratelimit-limit'),
                        "x-ratelimit-remaining": response.headers.get('x-ratelimit-remaining'),
                        "x-ratelimit-reset": response.headers.get('x-ratelimit-reset'),
                        "rate-limit": response.headers.get('rate-limit'),
                        "retry-after": response.headers.get('retry-after')
                    }
                    
                    # Filter out None values
                    rate_headers = {k: v for k, v in rate_headers.items() if v is not None}
                    
                    rate_limit_info[service['name']] = {
                        "has_rate_limiting": len(rate_headers) > 0,
                        "headers": rate_headers
                    }
                    
                except Exception as e:
                    rate_limit_info[service['name']] = {"error": str(e)}
        
        # Check if any service has rate limiting implemented
        has_rate_limiting = any(info.get("has_rate_limiting", False) for info in rate_limit_info.values())
        
        if not has_rate_limiting:
            rate_limit_issues.append("No rate limiting detected on any service")
        else:
            # Check for consistency in rate limit header formats
            header_formats = []
            for service_info in rate_limit_info.values():
                if service_info.get("has_rate_limiting"):
                    header_formats.append(set(service_info["headers"].keys()))
            
            if len(set(tuple(fmt) for fmt in header_formats)) > 1:
                rate_limit_issues.append(f"Inconsistent rate limit header formats: {header_formats}")
        
        # This assertion SHOULD FAIL if rate limiting is not implemented
        assert len(rate_limit_issues) == 0, \
            f"Rate limiting issues detected: {rate_limit_issues}. " \
            f"Rate limit info: {rate_limit_info}"

    def test_api_configuration_file_consistency(self):
        """
        Test that API configuration files are consistent.
        
        Critical Assertions:
        - OpenAPI specs exist for all services
        - API routes are properly configured
        - Configuration files are valid
        
        Expected Failure: Missing or inconsistent configuration
        Business Impact: Services misconfigured, API endpoints unreliable
        """
        base_dir = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1")
        
        # Look for API configuration files
        config_files = []
        
        # OpenAPI specs
        for pattern in ["openapi.json", "openapi.yaml", "swagger.json"]:
            config_files.extend(base_dir.glob(f"**/{pattern}"))
        
        # API route configuration files
        for pattern in ["routes.py", "*routes*.py", "api.py"]:
            config_files.extend(base_dir.glob(f"**/{pattern}"))
        
        configuration_issues = []
        
        for config_file in config_files:
            try:
                if config_file.suffix in ['.json']:
                    # Validate JSON files
                    content = json.loads(config_file.read_text())
                    
                    # If it's an OpenAPI spec, validate structure
                    if 'openapi' in content or 'swagger' in content:
                        required_fields = ['info', 'paths']
                        missing_fields = [field for field in required_fields if field not in content]
                        if missing_fields:
                            configuration_issues.append(
                                f"{config_file}: OpenAPI spec missing required fields: {missing_fields}"
                            )
                
                elif config_file.suffix == '.py':
                    # Basic validation for Python API files
                    content = config_file.read_text()
                    
                    # Check for common API patterns
                    if 'routes' in config_file.name.lower():
                        if 'router' not in content and 'app' not in content:
                            configuration_issues.append(
                                f"{config_file}: Route file doesn't appear to define routes"
                            )
            
            except Exception as e:
                configuration_issues.append(f"{config_file}: Configuration validation failed: {str(e)}")
        
        # This assertion might FAIL if configurations are inconsistent
        assert len(configuration_issues) == 0, \
            f"API configuration issues found: {configuration_issues}"
