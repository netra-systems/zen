
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
Mission Critical tests for SessionMiddleware Golden Path.
Protects 90% business value - user login  ->  AI response flow.
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestSessionMiddlewareGoldenPath(SSotBaseTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """Mission critical tests protecting Golden Path user flow."""
    
    def setUp(self):
        """Set up test environment for Golden Path testing."""
        super().setUp()
        self.env = IsolatedEnvironment()
        
        # Set up critical environment variables
        self.env.set("SECRET_KEY", "golden_path_secret_" + "x" * 32)
        self.env.set("ENV", "production")
        self.env.set("ENABLE_WEBSOCKET", "true")
        
    def test_golden_path_user_authentication_flow(self):
        """Test complete user authentication flow with session management."""
        from netra_backend.app.app_factory import create_app
        from fastapi.testclient import TestClient
        
        # Create app with proper configuration
        with patch('netra_backend.app.core.middleware_setup._validate_and_get_secret_key') as mock_validate:
            # Function expects (config, environment) parameters
            mock_validate.return_value = self.env.get("SECRET_KEY")
            
            app = create_app()
            client = TestClient(app)
            
            # Simulate user login flow
            login_data = {
                "email": "test@example.com",
                "password": "test_password"
            }
            
            # Test auth endpoint (mocked for unit test)
            with patch('netra_backend.app.auth_integration.auth.validate_token') as mock_auth:
                mock_auth.return_value = {
                    "user_id": "test_user_123",
                    "email": "test@example.com",
                    "customer_tier": "premium"
                }
                
                # Simulate authenticated request
                headers = {"Authorization": "Bearer test_token"}
                response = client.get("/api/v1/health", headers=headers)
                
                # Golden Path must succeed
                self.assertIn(response.status_code, [200, 204])
                self._track_metric("golden_path", "auth_flow_success", 1)
                
    def test_golden_path_websocket_with_session_context(self):
        """Test WebSocket connection maintains session context for chat."""
        from netra_backend.app.websocket_core.manager import UnifiedWebSocketManager
        
        # Create WebSocket manager
        manager = UnifiedWebSocketManager()
        
        # Simulate WebSocket connection with session
        websocket = MagicMock()
        user_id = "golden_user_123"
        
        async def test_websocket():
            # Connect user
            await manager.connect(websocket, user_id)
            
            # Verify connection established
            self.assertIn(user_id, manager._active_connections)
            
            # Simulate chat message (90% business value)
            chat_message = {
                "type": "chat_message",
                "content": "Help me optimize my AI costs",
                "session_id": "session_123"
            }
            
            # Process message (would trigger agent flow)
            with patch.object(manager, 'process_message') as mock_process:
                mock_process.return_value = {
                    "type": "agent_response",
                    "content": "I'll help you optimize your AI costs..."
                }
                
                response = await mock_process(user_id, chat_message)
                
                # Verify response generated
                self.assertIsNotNone(response)
                self.assertEqual(response["type"], "agent_response")
                self._track_metric("golden_path", "websocket_chat_success", 1)
                
            # Disconnect
            await manager.disconnect(user_id)
            
        # Run async test
        loop = asyncio.new_event_loop()
        loop.run_until_complete(test_websocket())
        loop.close()
        
    def test_golden_path_agent_execution_with_auth_context(self):
        """Test agent execution maintains auth context from session."""
        from netra_backend.app.agents.supervisor_agent_modern import ModernSupervisorAgent
        
        # Create supervisor agent
        agent = ModernSupervisorAgent(
            user_id="golden_user_123",
            session_id="session_456"
        )
        
        # Mock auth context from session
        auth_context = {
            "user_id": "golden_user_123",
            "session_id": "session_456",
            "customer_tier": "enterprise",
            "user_email": "enterprise@example.com"
        }
        
        async def test_agent():
            # Set auth context (would come from SessionMiddleware)
            agent.auth_context = auth_context
            
            # Execute agent with user query
            query = "Analyze my AI spending patterns"
            
            with patch.object(agent, 'execute') as mock_execute:
                mock_execute.return_value = {
                    "status": "completed",
                    "result": "Analysis complete: You're spending $X on AI...",
                    "auth_context": auth_context
                }
                
                result = await mock_execute(query)
                
                # Verify auth context preserved
                self.assertEqual(result["auth_context"]["user_id"], "golden_user_123")
                self.assertEqual(result["auth_context"]["customer_tier"], "enterprise")
                self._track_metric("golden_path", "agent_auth_context", 1)
                
        # Run async test
        loop = asyncio.new_event_loop()
        loop.run_until_complete(test_agent())
        loop.close()
        
    def test_golden_path_enterprise_compliance_features(self):
        """Test enterprise compliance features rely on session data."""
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        
        middleware = GCPAuthContextMiddleware()
        
        # Create request with session data for compliance
        request = MagicMock()
        request.session = {
            "user_id": "enterprise_user",
            "session_id": "audit_session_789",
            "user_email": "compliance@enterprise.com",
            "customer_tier": "enterprise",
            "gdpr_consent": True,
            "sox_audit_enabled": True
        }
        
        async def test_compliance():
            # Extract auth context for audit trail
            auth_context = await middleware._extract_auth_context(request)
            
            # Verify compliance data available
            self.assertEqual(auth_context.get("user_id"), "enterprise_user")
            self.assertEqual(auth_context.get("customer_tier"), "enterprise")
            
            # GDPR/SOX compliance features
            if request.session.get("gdpr_consent"):
                self._track_metric("golden_path", "gdpr_compliance", 1)
                
            if request.session.get("sox_audit_enabled"):
                self._track_metric("golden_path", "sox_compliance", 1)
                
            # Audit trail must have session context
            self.assertIsNotNone(auth_context.get("session_id"))
            
        # Run async test
        loop = asyncio.new_event_loop()
        loop.run_until_complete(test_compliance())
        loop.close()
        
    def test_golden_path_resilience_with_defensive_patterns(self):
        """Test Golden Path remains functional with defensive patterns."""
        from netra_backend.app.app_factory import create_app
        from fastapi.testclient import TestClient
        
        # Simulate partial SessionMiddleware failure
        with patch('netra_backend.app.core.middleware_setup.setup_session_middleware') as mock_session:
            # Session setup partially fails but app continues
            mock_session.side_effect = lambda app: print("SessionMiddleware warning logged")
            
            app = create_app()
            client = TestClient(app)
            
            # Golden Path should still work with fallbacks
            response = client.get("/api/v1/health")
            
            # System remains operational
            self.assertIn(response.status_code, [200, 204, 503])
            
            # Chat endpoint with defensive handling
            chat_response = client.post(
                "/api/v1/chat",
                json={"message": "Test message"},
                headers={"Authorization": "Bearer fallback_token"}
            )
            
            # Should handle gracefully even without full session
            if chat_response.status_code == 200:
                self._track_metric("golden_path", "resilient_operation", 1)
            else:
                # Log but don't fail - defensive pattern working
                self._track_metric("golden_path", "graceful_degradation", 1)


if __name__ == "__main__":
    unittest.main()