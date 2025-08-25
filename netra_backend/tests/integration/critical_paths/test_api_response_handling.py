"""
L3 Integration Test: API Response Handling
Tests API response formatting and error handling
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json

import httpx
import pytest

from netra_backend.app.config import get_config

class TestAPIResponseHandlingL3:
    """Test API response handling scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.asyncio
    async def test_successful_response_format(self):
        """Test successful response format consistency"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.API_BASE_URL}/api/health",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Check standard response structure
            assert "status" in data or "data" in data
            assert response.headers.get("content-type") == "application/json"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.asyncio
    async def test_error_response_format(self):
        """Test error response format consistency"""
        async with httpx.AsyncClient() as client:
            # Request non-existent resource
            response = await client.get(
                f"{settings.API_BASE_URL}/api/resources/nonexistent",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 404
            error = response.json()
            
            # Check error structure
            assert "error" in error or "message" in error
            assert "status" in error or "code" in error
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.asyncio
    async def test_response_headers(self):
        """Test required response headers"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.API_BASE_URL}/api/resources",
                headers={"Authorization": "Bearer test_token"}
            )
            
            # Check security headers
            assert "X-Content-Type-Options" in response.headers
            assert "X-Frame-Options" in response.headers
            
            # Check CORS headers if applicable
            if "Access-Control-Allow-Origin" in response.headers:
                assert response.headers["Access-Control-Allow-Origin"] in ["*", settings.ALLOWED_ORIGINS]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.asyncio
    async def test_response_compression(self):
        """Test response compression for large payloads"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.API_BASE_URL}/api/resources",
                params={"limit": 100},
                headers={
                    "Authorization": "Bearer test_token",
                    "Accept-Encoding": "gzip, deflate"
                }
            )
            
            # Check if compressed
            encoding = response.headers.get("content-encoding", "")
            if len(response.content) > 1000:  # Only for large responses
                assert encoding in ["gzip", "deflate", "br"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.asyncio
    async def test_response_caching_headers(self):
        """Test response caching headers"""
        async with httpx.AsyncClient() as client:
            # GET request (should be cacheable)
            response = await client.get(
                f"{settings.API_BASE_URL}/api/resources/123",
                headers={"Authorization": "Bearer test_token"}
            )
            
            if response.status_code == 200:
                # Check cache headers
                assert "Cache-Control" in response.headers or "ETag" in response.headers
                
                # If ETag present, test conditional request
                if "ETag" in response.headers:
                    etag = response.headers["ETag"]
                    
                    # Conditional request
                    cond_response = await client.get(
                        f"{settings.API_BASE_URL}/api/resources/123",
                        headers={
                            "Authorization": "Bearer test_token",
                            "If-None-Match": etag
                        }
                    )
                    
                    # Should return 304 if unchanged
                    assert cond_response.status_code in [200, 304]