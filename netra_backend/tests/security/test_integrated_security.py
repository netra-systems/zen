"""
Integrated Security Tests
Tests integrated security across all components
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from netra_backend.app.middleware.security_headers import SecurityHeadersMiddleware

from netra_backend.app.middleware.security_middleware import SecurityMiddleware

class TestIntegratedSecurity:
    """Test integrated security across all components."""
    
    @pytest.fixture
    def app_with_security(self):
        """Create FastAPI app with all security middleware."""
        app = FastAPI()
        
        # Add security middleware properly to the app (order matters)
        app.add_middleware(SecurityMiddleware)  # Input validation comes first
        app.add_middleware(SecurityHeadersMiddleware, environment="development")
        
        @app.post("/api/test")
        @pytest.mark.asyncio
        async def test_endpoint(data: dict):
            return {"status": "success", "data": data}
        
        return app
    
    def test_end_to_end_security(self, app_with_security):
        """Test end-to-end security with all middleware."""
        client = TestClient(app_with_security)
        
        # Test normal request
        response = client.post("/api/test", json={"test": "data"})
        assert response.status_code == 200
        
        # Check security headers are present
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        
        # Test malicious request (should be blocked)
        with pytest.raises(Exception):
            client.post("/api/test", json={"query": "'; DROP TABLE users; --"})

    @pytest.mark.asyncio
    async def test_performance_under_load(self, app_with_security):
        """Test security performance under load."""
        client = TestClient(app_with_security)
        
        # Simulate concurrent requests
        async def make_request():
            return client.post("/api/test", json={"test": "data"})
        
        start_time = time.time()
        
        # Make 100 concurrent requests
        tasks = [make_request() for _ in range(100)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        
        # Should complete within reasonable time
        assert end_time - start_time < 10  # 10 seconds max
        
        # Most requests should succeed
        successful_responses = [r for r in responses if hasattr(r, 'status_code') and r.status_code == 200]
        assert len(successful_responses) > 90  # At least 90% success rate
    
    def test_security_chain_validation(self, app_with_security):
        """Test that security checks work in proper chain."""
        client = TestClient(app_with_security)
        
        # Test request size validation (first in chain)
        large_data = {"data": "x" * (10 * 1024 * 1024)}  # 10MB
        response = client.post("/api/test", json=large_data)
        assert response.status_code == 413  # Request too large
        
        # Test input validation (second in chain)
        malicious_data = {"query": "<script>alert('xss')</script>"}
        response = client.post("/api/test", json=malicious_data)
        assert response.status_code == 400  # Bad request due to validation
    
    def test_security_headers_integration(self, app_with_security):
        """Test security headers are properly integrated."""
        client = TestClient(app_with_security)
        
        response = client.get("/")
        
        # Should have all required security headers
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Content-Security-Policy",
            "Referrer-Policy"
        ]
        
        for header in required_headers:
            assert header in response.headers
    
    def test_rate_limiting_integration(self, app_with_security):
        """Test rate limiting works with other security measures."""
        client = TestClient(app_with_security)
        
        # Make requests up to limit
        for i in range(100):
            response = client.post("/api/test", json={"test": f"data_{i}"})
            if i < 99:
                assert response.status_code == 200
            else:
                # Should hit rate limit
                assert response.status_code == 429
    
    def test_comprehensive_security_scan(self, app_with_security):
        """Test comprehensive security scan of the application."""
        client = TestClient(app_with_security)
        
        # Test various attack vectors
        attack_vectors = [
            {"test": "'; DROP TABLE users; --"},  # SQL injection
            {"test": "<script>alert('xss')</script>"},  # XSS
            {"test": "../../../etc/passwd"},  # Path traversal
            {"test": "test; rm -rf /"},  # Command injection
        ]
        
        for attack in attack_vectors:
            response = client.post("/api/test", json=attack)
            # All attacks should be blocked
            assert response.status_code in [400, 403, 422]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])