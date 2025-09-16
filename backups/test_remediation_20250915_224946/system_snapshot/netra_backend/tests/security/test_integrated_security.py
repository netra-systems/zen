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

class IntegratedSecurityTests:
    """Test integrated security across all components."""

    @pytest.fixture
    def app_with_security(self):
        """Create FastAPI app with all security middleware."""
        app = FastAPI()
        app.add_middleware(SecurityMiddleware)
        app.add_middleware(SecurityHeadersMiddleware, environment='development')

        @app.post('/api/test')
        @pytest.mark.asyncio
        async def test_endpoint(data: dict):
            return {'status': 'success', 'data': data}
        return app

    def test_end_to_end_security(self, app_with_security):
        """Test end-to-end security with all middleware."""
        client = TestClient(app_with_security)
        response = client.post('/api/test', json={'test': 'data'})
        assert response.status_code == 200
        assert 'X-Content-Type-Options' in response.headers
        assert 'X-Frame-Options' in response.headers
        with pytest.raises(Exception):
            client.post('/api/test', json={'query': "'; DROP TABLE users; --"})

    @pytest.mark.asyncio
    async def test_performance_under_load(self, app_with_security):
        """Test security performance under load."""
        client = TestClient(app_with_security)

        async def make_request():
            return client.post('/api/test', json={'test': 'data'})
        start_time = time.time()
        tasks = [make_request() for _ in range(100)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        assert end_time - start_time < 10
        successful_responses = [r for r in responses if hasattr(r, 'status_code') and r.status_code == 200]
        assert len(successful_responses) > 90

    def test_security_chain_validation(self, app_with_security):
        """Test that security checks work in proper chain."""
        client = TestClient(app_with_security)
        large_data = {'data': 'x' * (10 * 1024 * 1024)}
        response = client.post('/api/test', json=large_data)
        assert response.status_code == 413
        malicious_data = {'query': "<script>alert('xss')</script>"}
        response = client.post('/api/test', json=malicious_data)
        assert response.status_code == 400

    def test_security_headers_integration(self, app_with_security):
        """Test security headers are properly integrated."""
        client = TestClient(app_with_security)
        response = client.get('/')
        required_headers = ['X-Content-Type-Options', 'X-Frame-Options', 'X-XSS-Protection', 'Content-Security-Policy', 'Referrer-Policy']
        for header in required_headers:
            assert header in response.headers

    def test_rate_limiting_integration(self, app_with_security):
        """Test rate limiting works with other security measures."""
        client = TestClient(app_with_security)
        for i in range(100):
            response = client.post('/api/test', json={'test': f'data_{i}'})
            if i < 99:
                assert response.status_code == 200
            else:
                assert response.status_code == 429

    def test_comprehensive_security_scan(self, app_with_security):
        """Test comprehensive security scan of the application."""
        client = TestClient(app_with_security)
        attack_vectors = [{'test': "'; DROP TABLE users; --"}, {'test': "<script>alert('xss')</script>"}, {'test': '../../../etc/passwd'}, {'test': 'test; rm -rf /'}]
        for attack in attack_vectors:
            response = client.post('/api/test', json=attack)
            assert response.status_code in [400, 403, 422]
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')