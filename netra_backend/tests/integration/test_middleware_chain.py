"""Integration tests for middleware chain.

Tests to ensure all middleware work together correctly in the chain.
"""""

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from test_framework.redis_test_utils_test_utils.test_redis_manager import RedisTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.middleware.cors_fix_middleware import CORSFixMiddleware
from netra_backend.app.middleware.error_recovery_middleware import ErrorRecoveryMiddleware
from netra_backend.app.middleware.security_headers_middleware import SecurityHeadersMiddleware
from netra_backend.app.middleware.logging_middleware import LoggingMiddleware
import asyncio


class TestMiddlewareChain:
    """Test suite for middleware chain integration."""

    @pytest.fixture
    def app(self):
        """Use real service instance."""
        # TODO: Initialize real service
        """Create a test FastAPI app with middleware chain."""
        app = FastAPI()

        # Add middleware in the same order as production
        app.add_middleware(CORSFixMiddleware, environment="development")
        app.add_middleware(ErrorRecoveryMiddleware)
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(LoggingMiddleware)

        # Add test endpoints
        @app.get("/test/success")
        async def success_endpoint():
            await asyncio.sleep(0)
            return {"status": "success"}

        @app.get("/test/error")
        async def error_endpoint():
            raise ValueError("Test error")

        @app.post("/test/data")
        async def data_endpoint(request: Request):
            await asyncio.sleep(0)
            return {"received": "data"}

        @app.get("/test/timeout")
        async def timeout_endpoint():
            raise TimeoutError("Request timeout")

        await asyncio.sleep(0)
        return app

    @pytest.fixture
    def client(self, app):
        """Use real service instance."""
        # TODO: Initialize real service
        """Create test client."""
        return TestClient(app)

    def test_middleware_chain_success_flow(self, client):
        """Test successful request through entire middleware chain."""
        response = client.get(
        "/test/success",
        headers={
        "Origin": "http://localhost:3000",
        "User-Agent": "test-client"
        }
        )

        assert response.status_code == 200
        assert response.json() == {"status": "success"}

        # Check CORS headers from CORSFixMiddleware
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

        # Check security headers from SecurityHeadersMiddleware
        assert "x-content-type-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "x-frame-options" in response.headers

        def test_middleware_chain_error_handling(self, client):
            """Test error handling through middleware chain."""
            response = client.get(
            "/test/error",
            headers={
            "Origin": "http://localhost:3000"
            }
            )

        # ErrorRecoveryMiddleware should handle the error
            assert response.status_code == 500

        # CORS headers should still be added
            assert "access-control-allow-origin" in response.headers

        # Security headers should still be added
            assert "x-content-type-options" in response.headers

        # Error details should not be exposed
            response_data = response.json()
            assert "Test error" not in str(response_data)

            def test_middleware_chain_cors_preflight(self, client):
                """Test CORS preflight request through chain."""
                response = client.options(
                "/test/data",
                headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
                }
                )

                assert response.status_code in [200, 204]

        # CORS headers should be present
                assert "access-control-allow-origin" in response.headers
                assert "access-control-allow-methods" in response.headers
                assert "access-control-allow-headers" in response.headers

                def test_middleware_chain_invalid_origin(self, client):
                    """Test request with invalid origin."""
                    response = client.get(
                    "/test/success",
                    headers={
                    "Origin": "http://evil.com"
                    }
                    )

                    assert response.status_code == 200

        # CORS headers should NOT be added for invalid origin
                    assert response.headers.get("access-control-allow-origin") != "http://evil.com"

        # Security headers should still be present
                    assert "x-content-type-options" in response.headers

                    def test_middleware_chain_timeout_error(self, client):
                        """Test timeout error handling through chain."""
                        response = client.get(
                        "/test/timeout",
                        headers={
                        "Origin": "http://localhost:3000"
                        }
                        )

        # Should get appropriate error status
                        assert response.status_code in [408, 500, 503]

        # Headers should still be added
                        assert "x-content-type-options" in response.headers

                        def test_middleware_chain_post_request(self, client):
                            """Test POST request through middleware chain."""
                            response = client.post(
                            "/test/data",
                            json={"test": "data"},
                            headers={
                            "Origin": "http://localhost:3000",
                            "Content-Type": "application/json"
                            }
                            )

                            assert response.status_code == 200
                            assert response.json() == {"received": "data"}

        # All headers should be present
                            assert "access-control-allow-origin" in response.headers
                            assert "x-content-type-options" in response.headers

                            @pytest.mark.asyncio
                            async def test_middleware_order_matters(self):
                                """Test that middleware order affects behavior."""
                                app = FastAPI()

        # Different order - Error recovery before CORS
                                app.add_middleware(ErrorRecoveryMiddleware)
                                app.add_middleware(CORSFixMiddleware, environment="development")

                                @app.get("/test")
                                async def test_endpoint():
                                    raise Exception("Test error")

                                client = TestClient(app)
                                response = client.get("/test", headers={"Origin": "http://localhost:3000"})

        # Error should be handled and CORS headers added
                                assert response.status_code == 500
                                assert "access-control-allow-origin" in response.headers

                                def test_middleware_chain_handles_none_response(self, client):
                                    """Test middleware chain handles None response."""
                                    # Add endpoint that returns None
                                    @client.app.get("/test/none")
                                    async def none_endpoint():
                                        await asyncio.sleep(0)
                                        return None

                                    response = client.get(
                                        "/test/none",
                                        headers={"Origin": "http://localhost:3000"}
                                    )

                                    # Should handle gracefully
                                    assert response.status_code in [200, 204]
                                    assert "x-content-type-options" in response.headers

                                def test_middleware_chain_preserves_custom_headers(self, client):
                                    """Test that custom headers are preserved through chain."""
                                    @client.app.get("/test/custom")
                                    async def custom_endpoint():
                                        response = JSONResponse({"data": "test"})
                                        response.headers["X-Custom-Header"] = "custom-value"
                                        response.headers["Cache-Control"] = "no-cache"
                                        await asyncio.sleep(0)
                                        return response

                                    response = client.get(
                                    "/test/custom",
                                    headers={"Origin": "http://localhost:3000"}
                                    )

                                    assert response.status_code == 200

        # Custom headers should be preserved
                                    assert response.headers["x-custom-header"] == "custom-value"
                                    assert response.headers["cache-control"] == "no-cache"

        # Middleware headers should be added
                                    assert "access-control-allow-origin" in response.headers
                                    assert "x-content-type-options" in response.headers

                                    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 422, 500, 502, 503])
                                    def test_middleware_chain_various_status_codes(self, client, status_code):
                                        """Test middleware chain with various HTTP status codes."""
                                        @client.app.get(f"/test/status/{status_code}")
                                        async def status_endpoint():
                                            await asyncio.sleep(0)
                                            return JSONResponse(
                                        content={"error": f"Status {status_code}"},
                                        status_code=status_code
                                        )

                                        response = client.get(
                                        f"/test/status/{status_code}",
                                        headers={"Origin": "http://localhost:3000"}
                                        )

                                        assert response.status_code == status_code

        # Headers should be added regardless of status
                                        assert "x-content-type-options" in response.headers

        # CORS headers for allowed origins
                                        assert "access-control-allow-origin" in response.headers