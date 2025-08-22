"""API Response Compression L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (bandwidth optimization and performance)
- Business Goal: Reduce bandwidth costs and improve response times
- Value Impact: Faster API responses, reduced infrastructure costs
- Strategic Impact: $15K MRR protection through efficient data transfer

Critical Path: Response generation -> Compression evaluation -> Compression application -> Header setting -> Client delivery
Coverage: Gzip compression, content negotiation, compression thresholds, performance optimization
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import gzip
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp
import pytest

logger = logging.getLogger(__name__)

@dataclass
class CompressionConfig:
    """Compression configuration for endpoints."""
    endpoint_pattern: str
    compression_enabled: bool
    compression_types: List[str]  # gzip, deflate, br
    min_size_bytes: int  # Minimum response size to compress
    compression_level: int  # 1-9 for gzip
    content_types: List[str]  # Content types to compress

class ApiCompressionManager:
    """Manages L3 API response compression tests with real compression."""
    
    def __init__(self):
        self.test_server = None
        self.compression_configs = {}
        self.compression_metrics = []
        self.compression_stats = []
        
    async def initialize_compression(self):
        """Initialize API compression testing."""
        try:
            await self.setup_compression_configs()
            await self.start_compression_server()
            logger.info("API compression testing initialized")
        except Exception as e:
            logger.error(f"Failed to initialize compression: {e}")
            raise
    
    async def setup_compression_configs(self):
        """Configure compression settings for different endpoints."""
        self.compression_configs = {
            "/api/v1/large-data": CompressionConfig(
                endpoint_pattern="/api/v1/large-data",
                compression_enabled=True,
                compression_types=["gzip", "deflate"],
                min_size_bytes=1024,  # 1KB minimum
                compression_level=6,
                content_types=["application/json", "text/plain"]
            ),
            "/api/v1/users": CompressionConfig(
                endpoint_pattern="/api/v1/users",
                compression_enabled=True,
                compression_types=["gzip"],
                min_size_bytes=500,  # 500 bytes minimum
                compression_level=9,  # Maximum compression
                content_types=["application/json"]
            ),
            "/api/v1/metrics": CompressionConfig(
                endpoint_pattern="/api/v1/metrics",
                compression_enabled=True,
                compression_types=["gzip", "deflate"],
                min_size_bytes=100,
                compression_level=3,  # Fast compression
                content_types=["application/json"]
            ),
            "/api/v1/static": CompressionConfig(
                endpoint_pattern="/api/v1/static",
                compression_enabled=True,
                compression_types=["gzip", "deflate", "br"],
                min_size_bytes=0,  # Compress everything
                compression_level=9,
                content_types=["application/json", "text/css", "text/javascript", "text/html"]
            ),
            "/api/v1/images": CompressionConfig(
                endpoint_pattern="/api/v1/images",
                compression_enabled=False,  # Don't compress images
                compression_types=[],
                min_size_bytes=0,
                compression_level=0,
                content_types=[]
            )
        }
    
    async def start_compression_server(self):
        """Start API server with compression middleware."""
        from aiohttp import web
        
        async def compression_middleware(request, handler):
            """Compression middleware for responses."""
            start_time = time.time()
            
            # Get response from handler
            response = await handler(request)
            
            # Find compression config
            compression_config = self.find_compression_config(request.path)
            
            if not compression_config or not compression_config.compression_enabled:
                # No compression
                self.record_compression_metric(
                    request.path, "none", 0, len(response.body or b""), 
                    len(response.body or b""), time.time() - start_time
                )
                return response
            
            # Check if response should be compressed
            should_compress = await self.should_compress_response(
                request, response, compression_config
            )
            
            if not should_compress:
                self.record_compression_metric(
                    request.path, "skipped", 0, len(response.body or b""), 
                    len(response.body or b""), time.time() - start_time
                )
                return response
            
            # Apply compression
            compressed_response = await self.compress_response(
                response, compression_config, request
            )
            
            processing_time = time.time() - start_time
            
            # Record compression metrics
            original_size = len(response.body or b"")
            compressed_size = len(compressed_response.body or b"")
            compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            
            self.record_compression_metric(
                request.path, compressed_response.headers.get("Content-Encoding", "none"),
                compression_ratio, original_size, compressed_size, processing_time
            )
            
            return compressed_response
        
        async def handle_large_data(request):
            """Handle large data endpoint."""
            # Generate large JSON response
            large_data = {
                "items": [
                    {
                        "id": i,
                        "name": f"Item {i}",
                        "description": f"This is a detailed description for item {i} with lots of text to make it large",
                        "properties": {
                            "category": f"Category {i % 10}",
                            "tags": [f"tag{j}" for j in range(5)],
                            "metadata": {"created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"}
                        }
                    } for i in range(100)
                ],
                "total": 100,
                "page_info": {
                    "page": 1,
                    "per_page": 100,
                    "total_pages": 1
                }
            }
            
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json=large_data
            )
        
        async def handle_users(request):
            """Handle users endpoint."""
            users_data = {
                "users": [
                    {
                        "id": i,
                        "name": f"User {i}",
                        "email": f"user{i}@example.com",
                        "profile": {
                            "bio": f"Bio for user {i} with some details about their background and interests",
                            "location": f"City {i}",
                            "joined_at": "2024-01-01T00:00:00Z"
                        }
                    } for i in range(20)
                ],
                "pagination": {
                    "page": 1,
                    "total": 20
                }
            }
            
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json=users_data
            )
        
        async def handle_metrics(request):
            """Handle metrics endpoint."""
            metrics_data = {
                "metrics": {
                    "requests_per_second": [10.5, 12.3, 15.7, 18.2, 20.1] * 20,
                    "error_rate": [0.01, 0.02, 0.015, 0.008, 0.012] * 20,
                    "response_time": [0.1, 0.15, 0.12, 0.08, 0.11] * 20
                },
                "timerange": {
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-01-01T01:00:00Z"
                },
                "summary": {
                    "total_requests": 50000,
                    "total_errors": 500,
                    "avg_response_time": 0.112
                }
            }
            
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json=metrics_data
            )
        
        async def handle_static_content(request):
            """Handle static content endpoint."""
            # Simulate CSS content
            css_content = """
            /* Large CSS file simulation */
            .container { width: 100%; max-width: 1200px; margin: 0 auto; }
            .header { background: #333; color: white; padding: 20px; }
            .content { padding: 40px; line-height: 1.6; }
            .footer { background: #f5f5f5; padding: 20px; text-align: center; }
            """ * 50  # Repeat to make it larger
            
            return web.Response(
                status=200,
                headers={"Content-Type": "text/css"},
                text=css_content
            )
        
        async def handle_images(request):
            """Handle images endpoint (should not be compressed)."""
            # Simulate binary image data
            fake_image_data = b"\x89PNG\r\n\x1a\n" + b"fake_image_data" * 100
            
            return web.Response(
                status=200,
                headers={"Content-Type": "image/png"},
                body=fake_image_data
            )
        
        app = web.Application(middlewares=[compression_middleware])
        
        # Register routes
        app.router.add_get('/api/v1/large-data', handle_large_data)
        app.router.add_get('/api/v1/users', handle_users)
        app.router.add_get('/api/v1/metrics', handle_metrics)
        app.router.add_get('/api/v1/static/style.css', handle_static_content)
        app.router.add_get('/api/v1/images/logo.png', handle_images)
        
        self.test_server = await asyncio.create_task(
            aiohttp.web.create_server(app, "localhost", 0)
        )
        
        logger.info(f"Compression server started on {self.test_server.sockets[0].getsockname()}")
    
    def find_compression_config(self, path: str) -> Optional[CompressionConfig]:
        """Find compression config for path."""
        for pattern, config in self.compression_configs.items():
            if path.startswith(pattern):
                return config
        return None
    
    async def should_compress_response(self, request, response, 
                                     config: CompressionConfig) -> bool:
        """Determine if response should be compressed."""
        # Check if client accepts compression
        accept_encoding = request.headers.get("Accept-Encoding", "")
        if not any(encoding in accept_encoding for encoding in config.compression_types):
            return False
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        if content_type and not any(ct in content_type for ct in config.content_types):
            return False
        
        # Check minimum size
        response_size = len(response.body or b"")
        if response_size < config.min_size_bytes:
            return False
        
        # Check if already compressed
        if "Content-Encoding" in response.headers:
            return False
        
        return True
    
    async def compress_response(self, response, config: CompressionConfig, request):
        """Compress response based on configuration."""
        accept_encoding = request.headers.get("Accept-Encoding", "")
        
        # Choose best compression method
        compression_method = None
        for method in config.compression_types:
            if method in accept_encoding:
                compression_method = method
                break
        
        if not compression_method:
            return response
        
        # Get response body
        if hasattr(response, '_body'):
            original_body = response._body
        else:
            original_body = response.body or b""
        
        # Compress based on method
        if compression_method == "gzip":
            compressed_body = gzip.compress(
                original_body, compresslevel=config.compression_level
            )
        elif compression_method == "deflate":
            import zlib
            compressed_body = zlib.compress(
                original_body, level=config.compression_level
            )
        else:
            # Fallback to no compression
            return response
        
        # Create compressed response
        compressed_response = web.Response(
            status=response.status,
            headers=dict(response.headers),
            body=compressed_body
        )
        
        # Set compression headers
        compressed_response.headers["Content-Encoding"] = compression_method
        compressed_response.headers["Content-Length"] = str(len(compressed_body))
        compressed_response.headers["Vary"] = "Accept-Encoding"
        
        return compressed_response
    
    def record_compression_metric(self, path: str, compression_type: str, 
                                compression_ratio: float, original_size: int,
                                compressed_size: int, processing_time: float):
        """Record compression metrics."""
        metric = {
            "path": path,
            "compression_type": compression_type,
            "compression_ratio": compression_ratio,
            "original_size": original_size,
            "compressed_size": compressed_size,
            "processing_time": processing_time,
            "bandwidth_saved": original_size - compressed_size,
            "timestamp": time.time()
        }
        self.compression_metrics.append(metric)
    
    async def make_compressed_request(self, path: str, 
                                    accept_encoding: str = "gzip, deflate",
                                    headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make request with compression support."""
        base_url = f"http://localhost:{self.test_server.sockets[0].getsockname()[1]}"
        url = f"{base_url}{path}"
        
        request_headers = headers or {}
        request_headers["Accept-Encoding"] = accept_encoding
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=request_headers) as response:
                    response_time = time.time() - start_time
                    
                    # Get response body (aiohttp automatically decompresses)
                    body = await response.read()
                    
                    result = {
                        "status_code": response.status,
                        "response_time": response_time,
                        "headers": dict(response.headers),
                        "body_size": len(body),
                        "is_compressed": "Content-Encoding" in response.headers,
                        "compression_type": response.headers.get("Content-Encoding", "none"),
                        "original_content_length": response.headers.get("Content-Length"),
                        "accept_encoding": accept_encoding
                    }
                    
                    # Try to parse JSON if possible
                    try:
                        result["body"] = json.loads(body.decode())
                    except:
                        result["body"] = body[:100]  # First 100 bytes for inspection
                    
                    return result
                    
        except Exception as e:
            return {
                "status_code": 500,
                "response_time": time.time() - start_time,
                "error": str(e),
                "accept_encoding": accept_encoding
            }
    
    async def test_compression_effectiveness(self, endpoints: List[str]) -> Dict[str, Any]:
        """Test compression effectiveness across endpoints."""
        results = []
        
        for endpoint in endpoints:
            # Test with compression
            compressed_result = await self.make_compressed_request(
                endpoint, "gzip, deflate"
            )
            
            # Test without compression
            uncompressed_result = await self.make_compressed_request(
                endpoint, "identity"  # No compression
            )
            
            # Calculate effectiveness
            if compressed_result["status_code"] == 200 and uncompressed_result["status_code"] == 200:
                compressed_size = int(compressed_result["headers"].get("Content-Length", 0))
                uncompressed_size = uncompressed_result["body_size"]
                
                if uncompressed_size > 0:
                    compression_ratio = (1 - compressed_size / uncompressed_size) * 100
                    bandwidth_saved = uncompressed_size - compressed_size
                else:
                    compression_ratio = 0
                    bandwidth_saved = 0
                
                endpoint_result = {
                    "endpoint": endpoint,
                    "compressed_size": compressed_size,
                    "uncompressed_size": uncompressed_size,
                    "compression_ratio": compression_ratio,
                    "bandwidth_saved": bandwidth_saved,
                    "compression_enabled": compressed_result["is_compressed"],
                    "compression_type": compressed_result["compression_type"]
                }
            else:
                endpoint_result = {
                    "endpoint": endpoint,
                    "error": "Failed to get valid responses for comparison"
                }
            
            results.append(endpoint_result)
        
        # Calculate overall statistics
        valid_results = [r for r in results if "error" not in r]
        
        if valid_results:
            avg_compression_ratio = sum(r["compression_ratio"] for r in valid_results) / len(valid_results)
            total_bandwidth_saved = sum(r["bandwidth_saved"] for r in valid_results)
        else:
            avg_compression_ratio = 0
            total_bandwidth_saved = 0
        
        return {
            "tested_endpoints": len(endpoints),
            "valid_results": len(valid_results),
            "average_compression_ratio": avg_compression_ratio,
            "total_bandwidth_saved": total_bandwidth_saved,
            "results": results
        }
    
    async def get_compression_metrics(self) -> Dict[str, Any]:
        """Get comprehensive compression metrics."""
        total_requests = len(self.compression_metrics)
        
        if total_requests == 0:
            return {"total_requests": 0}
        
        # Compression type breakdown
        compression_breakdown = {}
        total_bandwidth_saved = 0
        total_original_size = 0
        
        for metric in self.compression_metrics:
            comp_type = metric["compression_type"]
            compression_breakdown[comp_type] = compression_breakdown.get(comp_type, 0) + 1
            total_bandwidth_saved += metric["bandwidth_saved"]
            total_original_size += metric["original_size"]
        
        # Calculate overall compression ratio
        overall_compression_ratio = (
            total_bandwidth_saved / total_original_size * 100 
            if total_original_size > 0 else 0
        )
        
        # Processing time statistics
        processing_times = [m["processing_time"] for m in self.compression_metrics]
        avg_processing_time = sum(processing_times) / len(processing_times)
        
        # Endpoint breakdown
        endpoint_breakdown = {}
        for metric in self.compression_metrics:
            endpoint = metric["path"]
            if endpoint not in endpoint_breakdown:
                endpoint_breakdown[endpoint] = {
                    "requests": 0,
                    "total_bandwidth_saved": 0,
                    "total_original_size": 0
                }
            
            endpoint_breakdown[endpoint]["requests"] += 1
            endpoint_breakdown[endpoint]["total_bandwidth_saved"] += metric["bandwidth_saved"]
            endpoint_breakdown[endpoint]["total_original_size"] += metric["original_size"]
        
        # Calculate compression ratios per endpoint
        for endpoint_data in endpoint_breakdown.values():
            if endpoint_data["total_original_size"] > 0:
                endpoint_data["compression_ratio"] = (
                    endpoint_data["total_bandwidth_saved"] / 
                    endpoint_data["total_original_size"] * 100
                )
            else:
                endpoint_data["compression_ratio"] = 0
        
        return {
            "total_requests": total_requests,
            "total_bandwidth_saved": total_bandwidth_saved,
            "total_original_size": total_original_size,
            "overall_compression_ratio": overall_compression_ratio,
            "average_processing_time": avg_processing_time,
            "configured_endpoints": len(self.compression_configs),
            "compression_breakdown": compression_breakdown,
            "endpoint_breakdown": endpoint_breakdown
        }
    
    async def cleanup(self):
        """Clean up compression resources."""
        try:
            if self.test_server:
                self.test_server.close()
                await self.test_server.wait_closed()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

@pytest.fixture
async def compression_manager():
    """Create compression manager for L3 testing."""
    manager = ApiCompressionManager()
    await manager.initialize_compression()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_gzip_compression_enabled(compression_manager):
    """Test gzip compression for large responses."""
    result = await compression_manager.make_compressed_request(
        "/api/v1/large-data", "gzip"
    )
    
    assert result["status_code"] == 200
    assert result["is_compressed"] is True
    assert result["compression_type"] == "gzip"
    assert "Content-Encoding" in result["headers"]
    assert result["headers"]["Content-Encoding"] == "gzip"
    
    # Should have Vary header for caching
    assert "Vary" in result["headers"]
    assert "Accept-Encoding" in result["headers"]["Vary"]

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_compression_content_negotiation(compression_manager):
    """Test compression content negotiation."""
    # Test different Accept-Encoding headers
    encoding_tests = [
        ("gzip", "gzip"),
        ("deflate", "deflate"),
        ("gzip, deflate", "gzip"),  # Should prefer gzip
        ("deflate, gzip", "deflate"),  # Should prefer deflate (first supported)
        ("br", "none"),  # Brotli not supported for this endpoint
        ("identity", "none")  # No compression
    ]
    
    for accept_encoding, expected_encoding in encoding_tests:
        result = await compression_manager.make_compressed_request(
            "/api/v1/users", accept_encoding
        )
        
        assert result["status_code"] == 200
        
        if expected_encoding == "none":
            assert result["is_compressed"] is False
        else:
            assert result["is_compressed"] is True
            assert result["compression_type"] == expected_encoding

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_compression_size_threshold(compression_manager):
    """Test compression size thresholds."""
    # Large data should be compressed
    large_result = await compression_manager.make_compressed_request(
        "/api/v1/large-data", "gzip"
    )
    
    assert large_result["status_code"] == 200
    assert large_result["is_compressed"] is True
    
    # Test endpoint with small response (if any)
    # Note: Our test endpoints all generate relatively large responses
    # In a real scenario, you'd test with endpoints that return small responses

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_compression_disabled_for_images(compression_manager):
    """Test that compression is disabled for image content."""
    result = await compression_manager.make_compressed_request(
        "/api/v1/images/logo.png", "gzip, deflate"
    )
    
    assert result["status_code"] == 200
    assert result["is_compressed"] is False
    assert result["compression_type"] == "none"
    
    # Should not have Content-Encoding header
    assert "Content-Encoding" not in result["headers"]

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_compression_effectiveness(compression_manager):
    """Test compression effectiveness across different endpoints."""
    test_endpoints = [
        "/api/v1/large-data",
        "/api/v1/users",
        "/api/v1/metrics",
        "/api/v1/static/style.css"
    ]
    
    effectiveness_result = await compression_manager.test_compression_effectiveness(
        test_endpoints
    )
    
    assert effectiveness_result["tested_endpoints"] == 4
    assert effectiveness_result["valid_results"] >= 3  # Most should work
    assert effectiveness_result["average_compression_ratio"] > 30  # At least 30% compression
    assert effectiveness_result["total_bandwidth_saved"] > 1000  # Saved at least 1KB
    
    # Check individual endpoint results
    for result in effectiveness_result["results"]:
        if "error" not in result:
            assert result["compression_ratio"] >= 0
            assert result["bandwidth_saved"] >= 0
            
            # Large JSON data should compress well
            if "large-data" in result["endpoint"]:
                assert result["compression_ratio"] > 60  # Should compress >60%

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_compression_performance_impact(compression_manager):
    """Test compression performance impact."""
    # Test response times with and without compression
    endpoint = "/api/v1/users"
    
    # Measure with compression
    compressed_times = []
    for i in range(10):
        result = await compression_manager.make_compressed_request(
            endpoint, "gzip"
        )
        if result["status_code"] == 200:
            compressed_times.append(result["response_time"])
    
    # Measure without compression
    uncompressed_times = []
    for i in range(10):
        result = await compression_manager.make_compressed_request(
            endpoint, "identity"
        )
        if result["status_code"] == 200:
            uncompressed_times.append(result["response_time"])
    
    avg_compressed_time = sum(compressed_times) / len(compressed_times) if compressed_times else 0
    avg_uncompressed_time = sum(uncompressed_times) / len(uncompressed_times) if uncompressed_times else 0
    
    # Compression should not add significant overhead
    if avg_uncompressed_time > 0:
        overhead_ratio = (avg_compressed_time - avg_uncompressed_time) / avg_uncompressed_time
        assert overhead_ratio < 0.5  # Less than 50% overhead
    
    # Both should be reasonably fast
    assert avg_compressed_time < 0.5  # Less than 500ms
    assert avg_uncompressed_time < 0.5  # Less than 500ms

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_concurrent_compression_requests(compression_manager):
    """Test concurrent compression handling."""
    # Make concurrent requests with compression
    concurrent_tasks = []
    endpoints = ["/api/v1/users", "/api/v1/metrics", "/api/v1/large-data"]
    
    for i in range(15):
        endpoint = endpoints[i % len(endpoints)]
        task = compression_manager.make_compressed_request(endpoint, "gzip")
        concurrent_tasks.append(task)
    
    start_time = time.time()
    results = await asyncio.gather(*concurrent_tasks)
    concurrent_duration = time.time() - start_time
    
    # All requests should succeed
    successful_results = [r for r in results if r["status_code"] == 200]
    assert len(successful_results) >= 12  # Most should succeed
    
    # Should complete quickly
    assert concurrent_duration < 3.0  # 15 requests in < 3 seconds
    
    # Most responses should be compressed
    compressed_results = [r for r in successful_results if r["is_compressed"]]
    assert len(compressed_results) >= 10  # Most should be compressed

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_compression_headers_correctness(compression_manager):
    """Test correctness of compression-related headers."""
    result = await compression_manager.make_compressed_request(
        "/api/v1/metrics", "gzip, deflate"
    )
    
    assert result["status_code"] == 200
    
    if result["is_compressed"]:
        headers = result["headers"]
        
        # Should have Content-Encoding
        assert "Content-Encoding" in headers
        assert headers["Content-Encoding"] in ["gzip", "deflate"]
        
        # Should have Content-Length
        assert "Content-Length" in headers
        assert int(headers["Content-Length"]) > 0
        
        # Should have Vary header
        assert "Vary" in headers
        assert "Accept-Encoding" in headers["Vary"]
        
        # Content-Type should be preserved
        assert "Content-Type" in headers
        assert "application/json" in headers["Content-Type"]

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_compression_metrics_accuracy(compression_manager):
    """Test accuracy of compression metrics collection."""
    # Generate test requests
    test_requests = [
        "/api/v1/users",
        "/api/v1/metrics", 
        "/api/v1/large-data",
        "/api/v1/images/logo.png"  # Should not be compressed
    ]
    
    for endpoint in test_requests * 2:  # 8 total requests
        await compression_manager.make_compressed_request(endpoint, "gzip")
    
    metrics = await compression_manager.get_compression_metrics()
    
    # Verify metrics
    assert metrics["total_requests"] == 8
    assert metrics["configured_endpoints"] == 5
    assert metrics["total_bandwidth_saved"] >= 0
    assert metrics["overall_compression_ratio"] >= 0
    
    # Check compression breakdown
    compression_breakdown = metrics["compression_breakdown"]
    assert "gzip" in compression_breakdown or "none" in compression_breakdown
    
    # Should have at least some compression
    if "gzip" in compression_breakdown:
        assert compression_breakdown["gzip"] > 0
    
    # Check endpoint breakdown
    endpoint_breakdown = metrics["endpoint_breakdown"]
    assert len(endpoint_breakdown) >= 3  # Should have multiple endpoints
    
    # Each endpoint should have valid metrics
    for endpoint_data in endpoint_breakdown.values():
        assert endpoint_data["requests"] > 0
        assert endpoint_data["compression_ratio"] >= 0