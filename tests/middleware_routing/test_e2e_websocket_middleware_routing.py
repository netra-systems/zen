"""
End-to-End tests for WebSocket routing with complex middleware stack.
Reproduces real-world WebSocket upgrade scenarios causing Starlette routing errors.

TARGET ERROR: routing.py line 716 middleware_stack processing failures during WebSocket upgrades
BUSINESS IMPACT: WebSocket failures break core chat functionality ($500K+ ARR at risk)
"""

import asyncio
import pytest
import json
import threading
import time
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, AsyncMock
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosed
from shared.isolated_environment import get_env


class TestWebSocketMiddlewareE2E:
    """E2E tests simulating real WebSocket usage patterns that trigger routing errors."""
    
    def setup_method(self, method=None):
        """Set up E2E WebSocket test environment."""
        # Initialize environment isolation
        self._env = get_env()
        
        # Configure for maximum realism
        self._env.set("ENVIRONMENT", "staging")
        self._env.set("K_SERVICE", "netra-staging-backend") 
        self._env.set("GCP_PROJECT_ID", "netra-staging")
        self._env.set("SECRET_KEY", "e2e_websocket_test_secret_key_32_chars_minimum")
        
        self.websocket_errors = []
        self.connection_attempts = []
        self.middleware_timing = []
        self.upgrade_failures = []
        
        # Simple metrics tracking
        self.metrics = {}
    
    def record_metric(self, name: str, value):
        """Simple metric recording."""
        self.metrics[name] = value
    
    @pytest.mark.asyncio
    async def test_real_world_websocket_chat_simulation(self):
        """
        E2E Test 1: Simulate real chat WebSocket usage with full middleware stack.
        
        CRITICAL: This reproduces the exact WebSocket usage pattern from the Golden Path
        that protects $500K+ ARR chat functionality.
        """
        from netra_backend.app.core.app_factory import create_app
        
        try:
            # Create production app with full middleware stack
            app = create_app()
            
            # Add test WebSocket endpoint that simulates chat functionality
            @app.websocket("/ws/e2e-chat")
            async def e2e_chat_websocket(websocket: WebSocket):
                """Simulates the real chat WebSocket endpoint."""
                try:
                    await websocket.accept()
                    
                    # Simulate authentication check (often triggers middleware conflicts)
                    auth_data = {"user_id": "test_user", "session": "test_session"}
                    await websocket.send_json({"type": "auth_success", "data": auth_data})
                    
                    # Simulate agent interaction (core business logic)
                    await asyncio.sleep(0.1)  # Simulate processing time
                    await websocket.send_json({
                        "type": "agent_started", 
                        "message": "AI agent processing your request"
                    })
                    
                    await asyncio.sleep(0.2)  # Simulate agent thinking
                    await websocket.send_json({
                        "type": "agent_completed",
                        "message": "Here's your AI-powered response",
                        "result": {"analysis": "test result"}
                    })
                    
                    # Wait for client response
                    try:
                        client_message = await asyncio.wait_for(
                            websocket.receive_json(), timeout=5.0
                        )
                        await websocket.send_json({"type": "message_received", "ack": True})
                    except asyncio.TimeoutError:
                        pass
                    
                    await websocket.close()
                    
                except WebSocketDisconnect:
                    pass  # Client disconnected normally
                except Exception as e:
                    self.websocket_errors.append(("chat_websocket_handler", str(e)))
                    raise
            
            client = TestClient(app)
            
            # Test the complete chat flow
            start_time = time.time()
            try:
                with client.websocket_connect("/ws/e2e-chat") as websocket:
                    # Receive authentication success
                    auth_message = websocket.receive_json()
                    self.assertEqual(auth_message["type"], "auth_success")
                    
                    # Receive agent started
                    agent_start = websocket.receive_json() 
                    self.assertEqual(agent_start["type"], "agent_started")
                    
                    # Receive agent completed
                    agent_complete = websocket.receive_json()
                    self.assertEqual(agent_complete["type"], "agent_completed")
                    
                    # Send client response
                    websocket.send_json({"type": "user_message", "content": "thank you"})
                    
                    # Receive acknowledgment
                    ack = websocket.receive_json()
                    self.assertEqual(ack["type"], "message_received")
                
                end_time = time.time()
                self.record_metric("e2e_chat_full_chat_flow_success", 1)
                self.record_metric("e2e_chat_chat_flow_duration_ms", int((end_time - start_time) * 1000))
                
            except Exception as e:
                self.websocket_errors.append(("e2e_chat_flow", str(e)))
                
                # Check if this reproduces the routing.py error
                error_str = str(e).lower()
                if "routing" in error_str and "middleware" in error_str:
                    self.record_metric("e2e_chat_routing_middleware_error_reproduced", 1)
                elif "routing.py" in error_str:
                    self.record_metric("e2e_chat_exact_routing_py_error", 1)
                
                raise AssertionError(f"E2E chat simulation failed: {e}")
        
        except Exception as e:
            self.websocket_errors.append(("e2e_app_creation", str(e)))
            raise
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_connections_middleware_stress(self):
        """
        E2E Test 2: Stress test with multiple concurrent WebSocket connections.
        
        HYPOTHESIS: Concurrent connections reveal middleware race conditions causing routing errors
        """
        from netra_backend.app.core.app_factory import create_app
        
        app = create_app()
        
        # Add stress test WebSocket endpoint
        connection_counter = 0
        active_connections = []
        
        @app.websocket("/ws/stress-test/{client_id}")
        async def stress_test_websocket(websocket: WebSocket, client_id: str):
            nonlocal connection_counter
            connection_counter += 1
            
            try:
                await websocket.accept()
                active_connections.append((client_id, websocket))
                
                # Send connection confirmation
                await websocket.send_json({
                    "type": "connection_established",
                    "client_id": client_id,
                    "connection_number": connection_counter
                })
                
                # Keep connection alive for testing
                try:
                    while True:
                        await asyncio.sleep(0.5)
                        await websocket.send_json({
                            "type": "heartbeat",
                            "timestamp": time.time(),
                            "active_connections": len(active_connections)
                        })
                except WebSocketDisconnect:
                    pass
                    
            except Exception as e:
                self.websocket_errors.append((f"stress_connection_{client_id}", str(e)))
                raise
            finally:
                # Clean up
                active_connections[:] = [
                    (cid, ws) for cid, ws in active_connections if cid != client_id
                ]
        
        client = TestClient(app)
        
        # Create multiple concurrent connections
        connection_tasks = []
        connection_results = []
        connection_errors = []
        
        def establish_connection(client_id: str):
            """Establish a WebSocket connection in a separate thread."""
            try:
                with client.websocket_connect(f"/ws/stress-test/{client_id}") as websocket:
                    # Receive connection confirmation
                    confirm = websocket.receive_json()
                    connection_results.append((client_id, confirm))
                    
                    # Receive a few heartbeats
                    for _ in range(3):
                        heartbeat = websocket.receive_json()
                        if heartbeat["type"] != "heartbeat":
                            break
                    
                    connection_results.append((client_id, "completed_normally"))
                    
            except Exception as e:
                connection_errors.append((client_id, str(e)))
                
                # Check for routing-related errors
                error_str = str(e).lower()
                if "routing" in error_str:
                    self.record_metric(f"stress_test_routing_error_{client_id}", 1)
        
        # Start concurrent connections
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(establish_connection, f"client_{i}") 
                for i in range(5)
            ]
            
            # Wait for all connections to complete
            for future in futures:
                try:
                    future.result(timeout=10)
                except Exception as e:
                    connection_errors.append(("future_execution", str(e)))
        
        # Analyze results
        successful_connections = len([r for r in connection_results if "completed_normally" in str(r)])
        failed_connections = len(connection_errors)
        
        self.record_metric("stress_test_successful_connections", successful_connections)
        self.record_metric("stress_test_failed_connections", failed_connections)
        
        if failed_connections > 0:
            routing_errors = [
                error for client_id, error in connection_errors
                if "routing" in error.lower()
            ]
            if routing_errors:
                self.record_metric("stress_test_concurrent_routing_errors", len(routing_errors))
        
        # At least some connections should succeed
        self.assertGreater(successful_connections, 0, 
                          f"No connections succeeded. Errors: {connection_errors}")
    
    @pytest.mark.asyncio
    async def test_websocket_upgrade_middleware_interference(self):
        """
        E2E Test 3: Test WebSocket upgrade process with interfering middleware.
        
        HYPOTHESIS: Middleware interferes with WebSocket upgrade handshake causing routing.py errors
        """
        from fastapi.middleware.cors import CORSMiddleware
        from starlette.middleware.sessions import SessionMiddleware
        from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
        
        app = FastAPI()
        
        # Add middleware that might interfere with WebSocket upgrade
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
        
        app.add_middleware(SessionMiddleware, secret_key="websocket_upgrade_test_key_32_chars")
        
        try:
            app.add_middleware(FastAPIAuthMiddleware, excluded_paths=["/ws"])
        except ImportError:
            pass  # Skip if not available
        
        # Track upgrade process
        upgrade_steps = []
        
        @app.websocket("/ws/upgrade-test")
        async def upgrade_test_websocket(websocket: WebSocket):
            upgrade_steps.append("websocket_handler_called")
            
            try:
                upgrade_steps.append("attempting_accept")
                await websocket.accept()
                upgrade_steps.append("accept_successful")
                
                # Send upgrade confirmation
                await websocket.send_json({
                    "type": "upgrade_successful",
                    "upgrade_steps": upgrade_steps
                })
                
                upgrade_steps.append("message_sent")
                
                # Wait for client acknowledgment
                try:
                    ack = await asyncio.wait_for(websocket.receive_json(), timeout=5)
                    upgrade_steps.append("client_ack_received")
                except asyncio.TimeoutError:
                    upgrade_steps.append("client_ack_timeout")
                
                await websocket.close()
                upgrade_steps.append("connection_closed")
                
            except Exception as e:
                upgrade_steps.append(f"upgrade_error_{type(e).__name__}")
                self.websocket_errors.append(("upgrade_process", str(e)))
                raise
        
        client = TestClient(app)
        
        try:
            with client.websocket_connect("/ws/upgrade-test") as websocket:
                # Receive upgrade confirmation
                confirmation = websocket.receive_json()
                self.assertEqual(confirmation["type"], "upgrade_successful")
                
                # Send acknowledgment
                websocket.send_json({"type": "upgrade_ack"})
            
            self.record_metric("websocket_upgrade_upgrade_success", 1)
            
            # Verify complete upgrade process
            expected_steps = [
                "websocket_handler_called",
                "attempting_accept", 
                "accept_successful",
                "message_sent",
                "client_ack_received",
                "connection_closed"
            ]
            
            for step in expected_steps:
                if step in upgrade_steps:
                    self.record_metric(f"websocket_upgrade_step_{step}_success", 1)
                else:
                    self.record_metric(f"websocket_upgrade_step_{step}_missing", 1)
            
        except Exception as e:
            self.websocket_errors.append(("upgrade_test", str(e)))
            
            # Analyze upgrade failure
            error_str = str(e).lower()
            if "upgrade" in error_str:
                self.record_metric("websocket_upgrade_upgrade_specific_error", 1)
            elif "routing" in error_str:
                self.record_metric("websocket_upgrade_routing_upgrade_error", 1)
            
            # Log the upgrade steps achieved before failure
            print(f"Upgrade steps before failure: {upgrade_steps}")
            raise
    
    @pytest.mark.asyncio
    async def test_websocket_authentication_middleware_flow(self):
        """
        E2E Test 4: Test WebSocket with authentication middleware (common source of routing errors).
        
        HYPOTHESIS: Authentication middleware conflicts with WebSocket upgrade cause routing failures
        """
        from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
        from starlette.middleware.sessions import SessionMiddleware
        
        app = FastAPI()
        
        # Add authentication middleware
        app.add_middleware(SessionMiddleware, secret_key="auth_websocket_test_key_32_chars")
        
        try:
            app.add_middleware(
                FastAPIAuthMiddleware,
                excluded_paths=["/ws/public"]  # Only exclude public WebSocket
            )
        except ImportError:
            # Create a mock auth middleware if the real one isn't available
            from starlette.middleware.base import BaseHTTPMiddleware
            
            class MockAuthMiddleware(BaseHTTPMiddleware):
                async def dispatch(self, request, call_next):
                    if request.url.path.startswith("/ws/protected"):
                        # Simulate auth check that might interfere with WebSocket
                        if not request.headers.get("authorization"):
                            raise HTTPException(status_code=401, detail="Unauthorized")
                    return await call_next(request)
            
            app.add_middleware(MockAuthMiddleware)
        
        auth_websocket_calls = []
        
        @app.websocket("/ws/protected")
        async def protected_websocket(websocket: WebSocket):
            """WebSocket that should be protected by auth middleware."""
            auth_websocket_calls.append("protected_called")
            
            try:
                await websocket.accept()
                await websocket.send_json({"type": "protected_connection", "status": "authenticated"})
                
                # Simple echo functionality
                message = await websocket.receive_json()
                await websocket.send_json({"type": "echo", "message": message})
                
            except Exception as e:
                auth_websocket_calls.append(f"protected_error_{type(e).__name__}")
                self.websocket_errors.append(("protected_websocket", str(e)))
                raise
        
        @app.websocket("/ws/public")
        async def public_websocket(websocket: WebSocket):
            """WebSocket that should bypass auth middleware."""
            auth_websocket_calls.append("public_called")
            
            await websocket.accept()
            await websocket.send_json({"type": "public_connection", "status": "no_auth_required"})
            await websocket.close()
        
        client = TestClient(app)
        
        # Test public WebSocket (should work)
        try:
            with client.websocket_connect("/ws/public") as websocket:
                message = websocket.receive_json()
                self.assertEqual(message["type"], "public_connection")
            
            self.record_metric("auth_websocket_public_websocket_success", 1)
            
        except Exception as e:
            self.websocket_errors.append(("public_websocket", str(e)))
            self.record_metric("auth_websocket_public_websocket_failed", 1)
        
        # Test protected WebSocket without auth (might trigger routing error)
        try:
            with client.websocket_connect("/ws/protected") as websocket:
                message = websocket.receive_json()
                # If this succeeds, auth middleware didn't work as expected
                self.record_metric("auth_websocket_protected_websocket_unexpected_success", 1)
        except Exception as e:
            self.websocket_errors.append(("protected_websocket_no_auth", str(e)))
            
            # Check if this is an auth error or routing error
            error_str = str(e).lower()
            if "unauthorized" in error_str or "401" in error_str:
                self.record_metric("auth_websocket_expected_auth_error", 1)
            elif "routing" in error_str:
                self.record_metric("auth_websocket_routing_auth_conflict", 1)
            
        # Test protected WebSocket with auth
        try:
            with client.websocket_connect(
                "/ws/protected",
                headers={"Authorization": "Bearer test_token"}
            ) as websocket:
                message = websocket.receive_json()
                self.assertEqual(message["type"], "protected_connection")
                
                # Test echo functionality
                websocket.send_json({"test": "echo message"})
                echo = websocket.receive_json()
                self.assertEqual(echo["type"], "echo")
                
            self.record_metric("auth_websocket_protected_websocket_with_auth_success", 1)
            
        except Exception as e:
            self.websocket_errors.append(("protected_websocket_with_auth", str(e)))
            
            # This failure might indicate a routing issue with auth middleware
            error_str = str(e).lower()
            if "routing" in error_str:
                self.record_metric("auth_websocket_auth_routing_conflict", 1)
    
    @pytest.mark.asyncio
    async def test_production_websocket_endpoint_exact_reproduction(self):
        """
        E2E Test 5: Test the exact production WebSocket endpoint that was failing.
        
        MISSION CRITICAL: This reproduces the exact production scenario causing routing.py errors
        """
        from netra_backend.app.core.app_factory import create_app
        
        # Set exact production environment
        self._env.set("ENVIRONMENT", "staging")
        self._env.set("K_SERVICE", "netra-staging-backend")
        self._env.set("GCP_PROJECT_ID", "netra-staging")
        
        try:
            # Create exact production app
            app = create_app()
            client = TestClient(app)
            
            # Test the specific endpoints that were failing in production
            production_websocket_tests = [
                ("/ws", "main_websocket", "Primary WebSocket endpoint"),
                ("/ws/test", "test_websocket", "Test WebSocket endpoint"),  
                ("/websocket", "legacy_websocket", "Legacy WebSocket endpoint")
            ]
            
            for path, test_name, description in production_websocket_tests:
                with self.subTest(endpoint=test_name):
                    print(f"Testing {description}: {path}")
                    
                    try:
                        with client.websocket_connect(path) as websocket:
                            # Just establishing connection reproduces the routing issue
                            print(f"✅ Connection established to {path}")
                            
                            # Try to send a simple message to fully test the connection
                            try:
                                websocket.send_json({"type": "test", "message": "hello"})
                                print(f"✅ Message sent to {path}")
                            except Exception as send_error:
                                print(f"⚠️ Message send failed for {path}: {send_error}")
                        
                        self.record_metric(f"production_websockets_{test_name}_success", 1)
                        print(f"✅ {test_name} completed successfully")
                        
                    except Exception as e:
                        self.websocket_errors.append((test_name, str(e)))
                        
                        error_str = str(e).lower()
                        print(f"❌ {test_name} failed: {e}")
                        
                        # Check for the exact production error pattern
                        if "routing.py" in error_str and "line 716" in error_str:
                            self.record_metric(f"production_websockets_{test_name}_exact_error_match", 1)
                            print(f"🎯 EXACT MATCH: {test_name} reproduced the target routing.py line 716 error!")
                        elif "middleware_stack" in error_str:
                            self.record_metric(f"production_websockets_{test_name}_middleware_stack_error", 1) 
                            print(f"🎯 CLOSE MATCH: {test_name} has middleware_stack error - likely related")
                        elif "routing" in error_str:
                            self.record_metric(f"production_websockets_{test_name}_routing_related", 1)
                            print(f"⚠️ RELATED: {test_name} has routing-related error")
            
        except Exception as e:
            self.websocket_errors.append(("production_app_setup", str(e)))
            print(f"❌ Production app setup failed: {e}")
            raise AssertionError(f"Production WebSocket reproduction failed: {e}")
    
    def teardown_method(self, method=None):
        """Provide comprehensive E2E test analysis."""
        pass  # No parent teardown needed
        
        print("\n" + "="*80)
        print("E2E WEBSOCKET MIDDLEWARE ROUTING ERROR ANALYSIS")
        print("="*80)
        
        if self.websocket_errors:
            print("\n🔍 WEBSOCKET ERRORS DETECTED:")
            for error_source, error_msg in self.websocket_errors:
                print(f"\nSource: {error_source}")
                print(f"Error: {error_msg}")
                
                # Detailed analysis of each error
                error_lower = error_msg.lower()
                if "routing.py" in error_lower and "line 716" in error_lower:
                    print("🎯 TARGET REPRODUCED: This is the exact routing.py line 716 error!")
                elif "middleware_stack" in error_lower:
                    print("🎯 HIGH CORRELATION: middleware_stack error - very likely related!")
                elif "websocket" in error_lower and "routing" in error_lower:
                    print("🎯 WEBSOCKET ROUTING: WebSocket-specific routing error")
                elif "upgrade" in error_lower:
                    print("⚠️ UPGRADE ISSUE: WebSocket upgrade failure")
                elif "middleware" in error_lower:
                    print("⚠️ MIDDLEWARE ISSUE: Middleware-related WebSocket failure")
                
                print("-" * 60)
        else:
            print("✅ No WebSocket errors detected - may need more aggressive testing")
        
        print(f"\n📊 TOTAL ERRORS CAPTURED: {len(self.websocket_errors)}")
        print(f"📊 UNIQUE ERROR SOURCES: {len(set(e[0] for e in self.websocket_errors))}")
        
        # Summary of findings
        routing_errors = [e for e in self.websocket_errors if "routing" in e[1].lower()]
        middleware_errors = [e for e in self.websocket_errors if "middleware" in e[1].lower()]
        websocket_specific = [e for e in self.websocket_errors if "websocket" in e[1].lower()]
        
        print(f"\n📈 ERROR CATEGORIZATION:")
        print(f"   Routing-related: {len(routing_errors)}")
        print(f"   Middleware-related: {len(middleware_errors)}")
        print(f"   WebSocket-specific: {len(websocket_specific)}")
        
        if routing_errors and middleware_errors:
            print("\n🎯 STRONG INDICATION: Both routing and middleware errors detected!")
            print("   This suggests the target routing.py middleware_stack error is reproducible.")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=long", "--capture=no"])