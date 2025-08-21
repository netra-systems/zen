"""API Versioning Compatibility L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (API evolution and backward compatibility)
- Business Goal: Enable API evolution without breaking existing clients
- Value Impact: Supports gradual migration and maintains client compatibility
- Strategic Impact: $15K MRR protection through API version management

Critical Path: Version detection -> Route mapping -> Compatibility layer -> Response formatting -> Client adaptation
Coverage: API versioning, backward compatibility, version negotiation, deprecation handling
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import time
import logging
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ApiVersion:
    """API version configuration."""
    version: str
    status: str  # active, deprecated, sunset
    deprecation_date: Optional[str]
    sunset_date: Optional[str]
    supported_features: List[str]
    breaking_changes: List[str]


class ApiVersioningManager:
    """Manages L3 API versioning tests with real version routing."""
    
    def __init__(self):
        self.test_server = None
        self.api_versions = {}
        self.version_requests = []
        self.compatibility_issues = []
        
    async def initialize_versioning(self):
        """Initialize API versioning testing."""
        try:
            await self.setup_api_versions()
            await self.start_versioned_api_server()
            logger.info("API versioning testing initialized")
        except Exception as e:
            logger.error(f"Failed to initialize versioning: {e}")
            raise
    
    async def setup_api_versions(self):
        """Configure API versions."""
        self.api_versions = {
            "v1": ApiVersion(
                version="v1",
                status="deprecated",
                deprecation_date="2024-01-01",
                sunset_date="2024-12-31",
                supported_features=["basic_auth", "simple_responses"],
                breaking_changes=[]
            ),
            "v2": ApiVersion(
                version="v2",
                status="active",
                deprecation_date=None,
                sunset_date=None,
                supported_features=["oauth2", "pagination", "filtering"],
                breaking_changes=["auth_format_change", "response_structure_change"]
            ),
            "v3": ApiVersion(
                version="v3",
                status="active",
                deprecation_date=None,
                sunset_date=None,
                supported_features=["oauth2", "graphql", "real_time", "webhooks"],
                breaking_changes=["endpoint_restructure", "field_renaming"]
            )
        }
    
    async def start_versioned_api_server(self):
        """Start API server with version support."""
        from aiohttp import web
        
        async def version_middleware(request, handler):
            """Version handling middleware."""
            version = self.detect_api_version(request)
            request['api_version'] = version
            
            # Check version status
            if version not in self.api_versions:
                return web.Response(status=400, json={"error": "Unsupported API version"})
            
            version_info = self.api_versions[version]
            
            if version_info.status == "sunset":
                return web.Response(status=410, json={"error": "API version no longer supported"})
            
            response = await handler(request)
            
            # Add version headers
            response.headers["API-Version"] = version
            response.headers["API-Status"] = version_info.status
            
            if version_info.deprecation_date:
                response.headers["Deprecation"] = version_info.deprecation_date
            
            if version_info.sunset_date:
                response.headers["Sunset"] = version_info.sunset_date
            
            self.record_version_request(request, version)
            return response
        
        async def handle_users_v1(request):
            """Handle users endpoint v1 format."""
            return web.Response(status=200, json={
                "user": {
                    "id": 123,
                    "name": "John Doe",
                    "email": "john@example.com"
                }
            })
        
        async def handle_users_v2(request):
            """Handle users endpoint v2 format."""
            return web.Response(status=200, json={
                "data": {
                    "id": 123,
                    "full_name": "John Doe",
                    "email_address": "john@example.com",
                    "created_at": "2024-01-01T00:00:00Z"
                },
                "meta": {
                    "version": "v2",
                    "pagination": {"page": 1, "total": 1}
                }
            })
        
        async def handle_users_v3(request):
            """Handle users endpoint v3 format."""
            return web.Response(status=200, json={
                "users": [{
                    "id": 123,
                    "profile": {
                        "displayName": "John Doe",
                        "contactEmail": "john@example.com"
                    },
                    "metadata": {
                        "createdAt": "2024-01-01T00:00:00Z",
                        "lastUpdated": "2024-01-01T00:00:00Z"
                    }
                }],
                "pagination": {"cursor": "abc123", "hasMore": False}
            })
        
        async def handle_versioned_request(request):
            """Route to appropriate version handler."""
            version = request['api_version']
            path = request.path
            
            if "/users" in path:
                if version == "v1":
                    return await handle_users_v1(request)
                elif version == "v2":
                    return await handle_users_v2(request)
                elif version == "v3":
                    return await handle_users_v3(request)
            
            return web.Response(status=404, json={"error": "Endpoint not found"})
        
        app = web.Application(middlewares=[version_middleware])
        
        # Register versioned routes
        app.router.add_route('*', '/api/v1/{path:.*}', handle_versioned_request)
        app.router.add_route('*', '/api/v2/{path:.*}', handle_versioned_request)
        app.router.add_route('*', '/api/v3/{path:.*}', handle_versioned_request)
        
        # Header-based versioning
        app.router.add_route('*', '/api/{path:.*}', handle_versioned_request)
        
        self.test_server = await asyncio.create_task(
            aiohttp.web.create_server(app, "localhost", 0)
        )
        
        logger.info(f"Versioned API server started on {self.test_server.sockets[0].getsockname()}")
    
    def detect_api_version(self, request) -> str:
        """Detect API version from request."""
        # URL path versioning
        if "/api/v1/" in request.path:
            return "v1"
        elif "/api/v2/" in request.path:
            return "v2"
        elif "/api/v3/" in request.path:
            return "v3"
        
        # Header-based versioning
        version_header = request.headers.get("API-Version", "")
        if version_header in self.api_versions:
            return version_header
        
        # Accept header versioning
        accept_header = request.headers.get("Accept", "")
        if "version=v1" in accept_header:
            return "v1"
        elif "version=v2" in accept_header:
            return "v2"
        elif "version=v3" in accept_header:
            return "v3"
        
        # Default to latest stable version
        return "v2"
    
    def record_version_request(self, request, version: str):
        """Record version request for metrics."""
        self.version_requests.append({
            "path": request.path,
            "method": request.method,
            "version": version,
            "user_agent": request.headers.get("User-Agent", ""),
            "timestamp": time.time()
        })
    
    async def make_versioned_request(self, path: str, version_method: str = "url",
                                   version: str = "v2", method: str = "GET",
                                   headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make versioned API request."""
        base_url = f"http://localhost:{self.test_server.sockets[0].getsockname()[1]}"
        
        request_headers = headers or {}
        
        if version_method == "url":
            url = f"{base_url}/api/{version}{path}"
        elif version_method == "header":
            url = f"{base_url}/api{path}"
            request_headers["API-Version"] = version
        elif version_method == "accept":
            url = f"{base_url}/api{path}"
            request_headers["Accept"] = f"application/json; version={version}"
        else:
            url = f"{base_url}/api{path}"
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                request_method = getattr(session, method.lower())
                
                async with request_method(url, headers=request_headers) as response:
                    response_time = time.time() - start_time
                    
                    result = {
                        "status_code": response.status,
                        "response_time": response_time,
                        "headers": dict(response.headers),
                        "version_method": version_method,
                        "requested_version": version
                    }
                    
                    if response.status == 200:
                        result["body"] = await response.json()
                    else:
                        try:
                            result["body"] = await response.json()
                        except:
                            result["body"] = await response.text()
                    
                    return result
                    
        except Exception as e:
            return {
                "status_code": 500,
                "response_time": time.time() - start_time,
                "error": str(e),
                "version_method": version_method,
                "requested_version": version
            }
    
    async def test_version_compatibility(self, path: str, 
                                       version_tests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test compatibility across API versions."""
        results = []
        
        for test in version_tests:
            version = test["version"]
            method = test.get("method", "url")
            expected_fields = test.get("expected_fields", [])
            
            result = await self.make_versioned_request(path, method, version)
            
            # Check if response has expected structure
            compatibility_score = 0
            if result["status_code"] == 200 and "body" in result:
                body = result["body"]
                found_fields = self.extract_response_fields(body)
                
                if expected_fields:
                    matching_fields = len(set(expected_fields) & set(found_fields))
                    compatibility_score = matching_fields / len(expected_fields) * 100
            
            test_result = {
                "version": version,
                "method": method,
                "result": result,
                "compatibility_score": compatibility_score,
                "expected_fields": expected_fields,
                "found_fields": found_fields if result["status_code"] == 200 else []
            }
            
            results.append(test_result)
        
        return {
            "path": path,
            "version_tests": results,
            "average_compatibility": sum(r["compatibility_score"] for r in results) / len(results) if results else 0
        }
    
    def extract_response_fields(self, data: Any, prefix: str = "") -> List[str]:
        """Extract all field paths from response data."""
        fields = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                field_path = f"{prefix}.{key}" if prefix else key
                fields.append(field_path)
                
                if isinstance(value, (dict, list)):
                    fields.extend(self.extract_response_fields(value, field_path))
        elif isinstance(data, list) and data:
            fields.extend(self.extract_response_fields(data[0], f"{prefix}[0]"))
        
        return fields
    
    async def get_versioning_metrics(self) -> Dict[str, Any]:
        """Get API versioning metrics."""
        total_requests = len(self.version_requests)
        
        if total_requests == 0:
            return {"total_requests": 0}
        
        # Version usage breakdown
        version_usage = {}
        for request in self.version_requests:
            version = request["version"]
            version_usage[version] = version_usage.get(version, 0) + 1
        
        # Calculate usage percentages
        version_percentages = {}
        for version, count in version_usage.items():
            version_percentages[version] = count / total_requests * 100
        
        return {
            "total_requests": total_requests,
            "configured_versions": len(self.api_versions),
            "version_usage": version_usage,
            "version_percentages": version_percentages,
            "deprecated_version_usage": sum(
                count for version, count in version_usage.items()
                if self.api_versions.get(version, {}).status == "deprecated"
            )
        }
    
    async def cleanup(self):
        """Clean up versioning resources."""
        try:
            if self.test_server:
                self.test_server.close()
                await self.test_server.wait_closed()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def versioning_manager():
    """Create versioning manager for L3 testing."""
    manager = ApiVersioningManager()
    await manager.initialize_versioning()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_url_based_versioning(versioning_manager):
    """Test URL-based API versioning."""
    versions_to_test = ["v1", "v2", "v3"]
    
    for version in versions_to_test:
        result = await versioning_manager.make_versioned_request(
            "/users", "url", version
        )
        
        assert result["status_code"] == 200
        assert result["headers"]["API-Version"] == version
        
        # Check version-specific response format
        body = result["body"]
        if version == "v1":
            assert "user" in body
            assert "name" in body["user"]
        elif version == "v2":
            assert "data" in body
            assert "meta" in body
            assert "full_name" in body["data"]
        elif version == "v3":
            assert "users" in body
            assert "pagination" in body


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_header_based_versioning(versioning_manager):
    """Test header-based API versioning."""
    result = await versioning_manager.make_versioned_request(
        "/users", "header", "v2"
    )
    
    assert result["status_code"] == 200
    assert result["headers"]["API-Version"] == "v2"
    
    # Should get v2 format
    body = result["body"]
    assert "data" in body
    assert "meta" in body


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_accept_header_versioning(versioning_manager):
    """Test Accept header-based versioning."""
    result = await versioning_manager.make_versioned_request(
        "/users", "accept", "v3"
    )
    
    assert result["status_code"] == 200
    assert result["headers"]["API-Version"] == "v3"
    
    # Should get v3 format
    body = result["body"]
    assert "users" in body
    assert "pagination" in body


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_deprecated_version_warnings(versioning_manager):
    """Test deprecated version warning headers."""
    result = await versioning_manager.make_versioned_request(
        "/users", "url", "v1"
    )
    
    assert result["status_code"] == 200
    assert result["headers"]["API-Status"] == "deprecated"
    assert "Deprecation" in result["headers"]
    assert "Sunset" in result["headers"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_version_compatibility_matrix(versioning_manager):
    """Test compatibility across different API versions."""
    version_tests = [
        {
            "version": "v1",
            "expected_fields": ["user", "user.id", "user.name", "user.email"]
        },
        {
            "version": "v2", 
            "expected_fields": ["data", "data.id", "data.full_name", "data.email_address", "meta"]
        },
        {
            "version": "v3",
            "expected_fields": ["users", "users[0].id", "users[0].profile", "pagination"]
        }
    ]
    
    compatibility_result = await versioning_manager.test_version_compatibility(
        "/users", version_tests
    )
    
    assert compatibility_result["average_compatibility"] >= 80
    
    # Check that each version has its expected structure
    for test_result in compatibility_result["version_tests"]:
        assert test_result["compatibility_score"] >= 80
        assert test_result["result"]["status_code"] == 200


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_unsupported_version_handling(versioning_manager):
    """Test handling of unsupported API versions."""
    result = await versioning_manager.make_versioned_request(
        "/users", "url", "v99"
    )
    
    assert result["status_code"] == 400
    assert "error" in result["body"]
    assert "Unsupported API version" in result["body"]["error"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_concurrent_version_requests(versioning_manager):
    """Test concurrent requests to different API versions."""
    concurrent_tasks = []
    
    for i in range(15):
        version = ["v1", "v2", "v3"][i % 3]
        task = versioning_manager.make_versioned_request(
            "/users", "url", version
        )
        concurrent_tasks.append(task)
    
    results = await asyncio.gather(*concurrent_tasks)
    
    # All requests should succeed
    successful_results = [r for r in results if r["status_code"] == 200]
    assert len(successful_results) == 15
    
    # Should have used all three versions
    versions_used = set(r["headers"]["API-Version"] for r in successful_results)
    assert versions_used == {"v1", "v2", "v3"}


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_versioning_metrics_accuracy(versioning_manager):
    """Test accuracy of versioning metrics."""
    # Generate test traffic across versions
    test_requests = [
        ("v1", 3),
        ("v2", 5), 
        ("v3", 2)
    ]
    
    for version, count in test_requests:
        for i in range(count):
            await versioning_manager.make_versioned_request(
                "/users", "url", version
            )
    
    metrics = await versioning_manager.get_versioning_metrics()
    
    assert metrics["total_requests"] == 10
    assert metrics["configured_versions"] == 3
    
    # Check version usage
    version_usage = metrics["version_usage"]
    assert version_usage["v1"] == 3
    assert version_usage["v2"] == 5
    assert version_usage["v3"] == 2
    
    # Check percentages
    version_percentages = metrics["version_percentages"]
    assert version_percentages["v1"] == 30.0
    assert version_percentages["v2"] == 50.0
    assert version_percentages["v3"] == 20.0
    
    # Check deprecated usage
    assert metrics["deprecated_version_usage"] == 3  # v1 requests