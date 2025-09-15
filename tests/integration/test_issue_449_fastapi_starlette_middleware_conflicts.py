"""
Issue #449 - WebSocket uvicorn middleware stack failures - Integration Tests

PURPOSE: Test FastAPI/Starlette middleware conflicts that cause WebSocket failures
         when uvicorn processes requests through the middleware stack.

BUSINESS IMPACT: $500K+ ARR WebSocket functionality failing due to middleware
                conflicts between FastAPI, Starlette, and uvicorn in production.

INTEGRATION SCOPE:
- FastAPI middleware registration conflicts
- Starlette middleware ordering issues  
- ASGI application middleware stack processing
- WebSocket vs HTTP middleware routing conflicts
- Session middleware installation ordering

TEST STRATEGY:
These tests should INITIALLY FAIL to demonstrate the real integration issues.
Tests use actual FastAPI/Starlette components to reproduce the failures.
"""
import asyncio
import json
import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.websockets import WebSocketState
from starlette.routing import Route, WebSocketRoute
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.testclient import TestClient as StarletteTestClient
import uvicorn
from test_framework.ssot.base_test_case import SSotBaseTestCase

class ProblematicSessionMiddleware(BaseHTTPMiddleware):
    """
    Simulates session middleware that causes WebSocket conflicts.
    
    CRITICAL: This replicates the "SessionMiddleware must be installed" error
    that occurs when middleware ordering is incorrect in uvicorn.
    """

    async def dispatch(self, request, call_next):
        if not hasattr(request, 'session'):
            raise RuntimeError('SessionMiddleware must be installed to access request.session')
        response = await call_next(request)
        return response

class ConflictingCORSMiddleware(BaseHTTPMiddleware):
    """
    Simulates CORS middleware that conflicts with WebSocket upgrades.
    
    CRITICAL: This replicates CORS middleware that intercepts WebSocket
    upgrade requests and causes protocol negotiation failures.
    """

    async def dispatch(self, request, call_next):
        if request.headers.get('upgrade') == 'websocket':
            response = await call_next(request)
            if hasattr(response, 'headers'):
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            return response
        return await call_next(request)

class AuthMiddlewareWebSocketConflict(BaseHTTPMiddleware):
    """
    Simulates auth middleware that conflicts with WebSocket authentication.
    
    CRITICAL: This replicates auth middleware that applies HTTP auth
    to WebSocket connections, causing authentication failures.
    """

    async def dispatch(self, request, call_next):
        auth_header = request.headers.get('authorization')
        if not auth_header and request.url.path.startswith('/ws'):
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail='Unauthorized')
        return await call_next(request)

@pytest.mark.integration
class Issue449FastAPIStarletteMiddlewareConflictsTests(SSotBaseTestCase):
    """
    Integration tests for Issue #449 - FastAPI/Starlette middleware conflicts.
    
    EXPECTED BEHAVIOR: These tests should FAIL initially to demonstrate
    the middleware conflicts that cause WebSocket failures in production.
    """

    def setup_method(self, method=None):
        super().setup_method(method)
        self.fastapi_app = None
        self.starlette_app = None

    def teardown_method(self, method=None):
        super().teardown_method(method)
        if hasattr(self, 'test_client'):
            self.test_client.close()

    def create_problematic_fastapi_app(self) -> FastAPI:
        """
        Create FastAPI app with middleware configuration that causes Issue #449.
        
        This replicates the exact middleware setup that fails in production.
        """
        app = FastAPI()
        app.add_middleware(ProblematicSessionMiddleware)
        app.add_middleware(ConflictingCORSMiddleware)
        app.add_middleware(AuthMiddlewareWebSocketConflict)

        @app.get('/test')
        async def test_route():
            return {'message': 'test'}

        @app.websocket('/ws')
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text('Hello WebSocket')
            await websocket.close()
        return app

    def create_conflicting_starlette_app(self) -> Starlette:
        """
        Create Starlette app with middleware stack that conflicts with WebSocket.
        
        This replicates Starlette-level middleware conflicts.
        """
        middleware = [Middleware(ProblematicSessionMiddleware), Middleware(ConflictingCORSMiddleware)]

        async def homepage(request):
            return PlainTextResponse('Hello Starlette')

        async def websocket_endpoint(websocket):
            await websocket.accept()
            await websocket.send_text('Hello Starlette WebSocket')
            await websocket.close()
        routes = [Route('/', homepage), WebSocketRoute('/ws', websocket_endpoint)]
        app = Starlette(routes=routes, middleware=middleware)
        return app

    def test_fastapi_session_middleware_websocket_conflict(self):
        """
        Test FastAPI session middleware causing WebSocket failures.
        
        EXPECTED: This test should FAIL, demonstrating SessionMiddleware
        conflicts with WebSocket connections in FastAPI middleware stack.
        """
        app = self.create_problematic_fastapi_app()
        app.add_middleware(SessionMiddleware, secret_key='test-secret')
        client = TestClient(app)
        self.test_client = client
        http_response = client.get('/test')
        self.assertEqual(http_response.status_code, 200)
        try:
            with client.websocket_connect('/ws') as websocket:
                data = websocket.receive_text()
                self.assertEqual(data, 'Hello WebSocket')
            assert False, 'WebSocket should fail due to session middleware conflict'
        except Exception as e:
            error_msg = str(e)
            assert 'SessionMiddleware must be installed' in error_msg or 'RuntimeError' in error_msg, f'Expected session middleware error, got: {error_msg}'

    def test_fastapi_cors_middleware_websocket_upgrade_conflict(self):
        """
        Test FastAPI CORS middleware interfering with WebSocket upgrades.
        
        EXPECTED: This test should FAIL, demonstrating CORS middleware
        incorrectly processes WebSocket upgrade requests.
        """
        app = self.create_problematic_fastapi_app()
        client = TestClient(app)
        self.test_client = client
        try:
            with client.websocket_connect('/ws') as websocket:
                data = websocket.receive_text()
                if hasattr(websocket, 'response'):
                    headers = getattr(websocket.response, 'headers', {})
                    assert 'Access-Control-Allow-Origin' not in headers, 'WebSocket responses should not have CORS headers'
            assert False, 'WebSocket should fail due to CORS middleware conflict'
        except Exception as e:
            error_msg = str(e).lower()
            assert 'websocket' in error_msg or 'upgrade' in error_msg or 'cors' in error_msg, f'Error should be WebSocket-related: {e}'

    def test_fastapi_auth_middleware_websocket_auth_conflict(self):
        """
        Test FastAPI auth middleware causing WebSocket authentication failures.
        
        EXPECTED: This test should FAIL, demonstrating auth middleware
        incorrectly applies HTTP auth to WebSocket connections.
        """
        app = self.create_problematic_fastapi_app()
        client = TestClient(app)
        self.test_client = client
        try:
            with client.websocket_connect('/ws') as websocket:
                data = websocket.receive_text()
                self.assertEqual(data, 'Hello WebSocket')
            assert False, 'WebSocket should fail due to auth middleware conflict'
        except Exception as e:
            error_msg = str(e)
            assert '401' in error_msg or 'Unauthorized' in error_msg, f'Should get 401 from auth middleware conflict: {error_msg}'

    def test_starlette_middleware_stack_ordering_conflict(self):
        """
        Test Starlette middleware stack ordering causing WebSocket conflicts.
        
        EXPECTED: This test should FAIL, demonstrating middleware ordering
        in Starlette causes WebSocket processing failures.
        """
        app = self.create_conflicting_starlette_app()
        client = StarletteTestClient(app)
        http_response = client.get('/')
        self.assertEqual(http_response.status_code, 200)
        with self.assertRaises(Exception) as context:
            with client.websocket_connect('/ws') as websocket:
                data = websocket.receive_text()
                self.assertEqual(data, 'Hello Starlette WebSocket')
        error_msg = str(context.exception)
        self.assertTrue('middleware' in error_msg.lower() or 'websocket' in error_msg.lower(), f'Error should be middleware-related: {error_msg}')

    def test_fastapi_middleware_registration_order_impact(self):
        """
        Test how FastAPI middleware registration order impacts WebSocket.
        
        EXPECTED: This test should FAIL, demonstrating middleware registration
        order in FastAPI causes WebSocket failures.
        """
        app = FastAPI()
        middleware_orders = [[SessionMiddleware, ConflictingCORSMiddleware, AuthMiddlewareWebSocketConflict], [ConflictingCORSMiddleware, AuthMiddlewareWebSocketConflict, SessionMiddleware]]
        for order_index, middleware_order in enumerate(middleware_orders):
            with self.subTest(order=order_index):
                test_app = FastAPI()
                for middleware_class in middleware_order:
                    if middleware_class == SessionMiddleware:
                        test_app.add_middleware(middleware_class, secret_key='test-secret')
                    else:
                        test_app.add_middleware(middleware_class)

                @test_app.websocket('/ws')
                async def websocket_endpoint(websocket: WebSocket):
                    await websocket.accept()
                    await websocket.send_text('Hello WebSocket')
                    await websocket.close()
                client = TestClient(test_app)
                if order_index == 1:
                    with self.assertRaises(RuntimeError):
                        with client.websocket_connect('/ws') as websocket:
                            data = websocket.receive_text()
                            self.assertEqual(data, 'Hello WebSocket')
                else:
                    with self.assertRaises(Exception):
                        with client.websocket_connect('/ws') as websocket:
                            data = websocket.receive_text()
                client.close()

    def test_fastapi_asgi_middleware_scope_handling_conflict(self):
        """
        Test FastAPI ASGI middleware scope handling conflicts with WebSocket.
        
        EXPECTED: This test should FAIL, demonstrating ASGI middleware
        incorrectly handles WebSocket scopes in FastAPI.
        """
        app = FastAPI()

        class ASGIScopeConflictMiddleware(BaseHTTPMiddleware):

            async def dispatch(self, request, call_next):
                if hasattr(request, 'scope'):
                    scope = request.scope
                    if scope.get('type') != 'http':
                        from fastapi import HTTPException
                        raise HTTPException(status_code=400, detail='Invalid scope type')
                return await call_next(request)
        app.add_middleware(ASGIScopeConflictMiddleware)

        @app.websocket('/ws')
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text('Hello WebSocket')
            await websocket.close()
        client = TestClient(app)
        self.test_client = client
        with self.assertRaises(Exception) as context:
            with client.websocket_connect('/ws') as websocket:
                data = websocket.receive_text()
                self.assertEqual(data, 'Hello WebSocket')
        error_msg = str(context.exception)
        self.assertIn('scope', error_msg.lower(), 'Error should be scope-related')

    def test_multiple_websocket_middleware_conflicts(self):
        """
        Test multiple middleware simultaneously conflicting with WebSocket.
        
        EXPECTED: This test should FAIL, demonstrating how multiple middleware
        conflicts compound to completely break WebSocket functionality.
        """
        app = FastAPI()
        app.add_middleware(ProblematicSessionMiddleware)
        app.add_middleware(ConflictingCORSMiddleware)
        app.add_middleware(AuthMiddlewareWebSocketConflict)
        app.add_middleware(SessionMiddleware, secret_key='test-secret')

        @app.websocket('/ws')
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text('Hello WebSocket')
            await websocket.close()
        client = TestClient(app)
        self.test_client = client
        multiple_errors = []
        try:
            with client.websocket_connect('/ws') as websocket:
                data = websocket.receive_text()
                self.assertEqual(data, 'Hello WebSocket')
        except Exception as e:
            multiple_errors.append(str(e))
        self.assertGreater(len(multiple_errors), 0, 'Multiple middleware should cause WebSocket failures')
        error_text = ' '.join(multiple_errors).lower()
        expected_error_indicators = ['session', 'cors', 'auth', 'middleware', 'websocket']
        found_indicators = [indicator for indicator in expected_error_indicators if indicator in error_text]
        self.assertGreater(len(found_indicators), 1, f'Should have multiple middleware conflict indicators: {found_indicators}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')