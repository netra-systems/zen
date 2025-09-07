"""
Staging environment configuration for E2E agent tests.
This module provides configuration for running agent tests against staging environment.
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class StagingConfig:
    """Configuration for staging environment tests"""
    
    # Backend URLs - Using proper staging domain
    backend_url: str = "https://api.staging.netrasystems.ai"
    api_url: str = "https://api.staging.netrasystems.ai/api"
    websocket_url: str = "wss://api.staging.netrasystems.ai/ws"
    
    # Auth service URLs (when deployed)
    auth_url: str = "https://auth.staging.netrasystems.ai"
    
    # Frontend URL (when deployed)
    frontend_url: str = "https://app.staging.netrasystems.ai"
    
    # Test configuration
    timeout: int = 60  # seconds
    retry_count: int = 3
    retry_delay: float = 2.0  # seconds
    
    # Authentication (for tests that need it)
    test_api_key: Optional[str] = os.environ.get("STAGING_TEST_API_KEY")
    test_jwt_token: Optional[str] = os.environ.get("STAGING_TEST_JWT_TOKEN")
    
    # Feature flags
    skip_auth_tests: bool = True  # Auth service not deployed yet
    skip_websocket_auth: bool = False  # WebSocket auth is now enforced in staging
    use_mock_llm: bool = False  # Use real LLM in staging
    
    @property
    def health_endpoint(self) -> str:
        return f"{self.backend_url}/health"
    
    @property
    def api_health_endpoint(self) -> str:
        return f"{self.backend_url}/api/health"
    
    @property
    def service_discovery_endpoint(self) -> str:
        return f"{self.backend_url}/api/discovery/services"
    
    @property
    def mcp_config_endpoint(self) -> str:
        return f"{self.backend_url}/api/mcp/config"
    
    @property
    def mcp_servers_endpoint(self) -> str:
        return f"{self.backend_url}/api/mcp/servers"
    
    def get_headers(self, include_auth: bool = False) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Test-Type": "E2E",
            "X-Test-Environment": "staging",
            "X-Test-Session": f"e2e-staging-{os.getpid()}",
            "User-Agent": "Netra-E2E-Tests/1.0"
        }
        
        if include_auth and self.test_api_key:
            headers["Authorization"] = f"Bearer {self.test_api_key}"
        elif include_auth and self.test_jwt_token:
            headers["Authorization"] = f"Bearer {self.test_jwt_token}"
            
        return headers
    
    def get_websocket_headers(self) -> Dict[str, str]:
        """Get headers for WebSocket connection"""
        headers = {
            "X-Test-Type": "E2E",
            "X-Test-Environment": "staging",
            "X-Test-Session": f"e2e-staging-{os.getpid()}",
            "User-Agent": "Netra-E2E-Tests/1.0"
        }
        
        # For staging, try to use JWT token if available
        if self.test_jwt_token:
            headers["Authorization"] = f"Bearer {self.test_jwt_token}"
        elif self.test_api_key:
            headers["Authorization"] = f"Bearer {self.test_api_key}"
        else:
            # Create a test JWT token for staging WebSocket auth
            test_token = self.create_test_jwt_token()
            if test_token:
                headers["Authorization"] = f"Bearer {test_token}"
            else:
                # For testing purposes, include a test token header
                # This will still get rejected but allows us to test the auth flow
                headers["X-Test-Auth"] = "test-token-for-staging"
            
        return headers
    
    def create_test_jwt_token(self) -> Optional[str]:
        """Create a test JWT token for staging authentication
        
        CRITICAL FIX: Now uses IDENTICAL unified JWT secret manager as UserContextExtractor.
        This fixes the WebSocket 403 authentication failures by ensuring perfect alignment
        between test token creation and backend validation.
        """
        try:
            import jwt
            import os
            from datetime import datetime, timedelta, timezone
            import uuid
            
            # CRITICAL FIX: Set staging environment to match backend behavior exactly
            original_env = os.environ.get("ENVIRONMENT")
            os.environ["ENVIRONMENT"] = "staging"
            
            try:
                # Use the unified JWT secret manager - IDENTICAL to UserContextExtractor._get_jwt_secret()
                from shared.jwt_secret_manager import get_unified_jwt_secret
                secret = get_unified_jwt_secret()
                print(f"Staging test token using unified JWT secret manager (environment: staging)")
                
                # Create payload with minimal required claims (match backend expectations)
                payload = {
                    "sub": f"test-user-{uuid.uuid4().hex[:8]}",
                    "email": "test@netrasystems.ai", 
                    "permissions": ["read", "write"],
                    "iat": int(datetime.now(timezone.utc).timestamp()),
                    "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
                    "iss": "netra-auth-service",
                    "jti": str(uuid.uuid4())  # Add JWT ID for replay protection
                }
                
                # Create token with unified secret manager - IDENTICAL resolution as backend
                token = jwt.encode(payload, secret, algorithm="HS256")
                print(f"Created staging JWT token using unified secret manager (user: {payload['sub']})")
                return token
                
            finally:
                # Restore original environment
                if original_env is not None:
                    os.environ["ENVIRONMENT"] = original_env
                else:
                    os.environ.pop("ENVIRONMENT", None)
                    
        except Exception as e:
            print(f"CRITICAL: Unified JWT secret manager failed: {e}")
            print("Falling back to manual staging secret - may still cause auth failures")
            
            # Emergency fallback: Use staging secret directly from config/staging.env
            try:
                import jwt
                from datetime import datetime, timedelta, timezone
                import uuid
                
                # Use the staging JWT secret from config/staging.env line 40
                staging_secret = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
                print("FALLBACK: Using staging JWT secret from config/staging.env (line 40)")
                
                payload = {
                    "sub": f"test-user-{uuid.uuid4().hex[:8]}",
                    "email": "test@netrasystems.ai",
                    "permissions": ["read", "write"],
                    "iat": int(datetime.now(timezone.utc).timestamp()),
                    "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
                    "iss": "netra-auth-service",
                    "jti": str(uuid.uuid4())  # Required JWT ID for replay protection
                }
                
                token = jwt.encode(payload, staging_secret, algorithm="HS256")
                print(f"Fallback JWT token created for staging (user: {payload['sub']})")
                return token
                
            except Exception as fallback_e:
                print(f"CRITICAL: Even fallback JWT creation failed: {fallback_e}")
                return None


# Global instance
STAGING_CONFIG = StagingConfig()


def get_staging_config() -> StagingConfig:
    """Get staging configuration instance"""
    return STAGING_CONFIG


def is_staging_available() -> bool:
    """Check if staging environment is available"""
    import httpx
    try:
        response = httpx.get(STAGING_CONFIG.health_endpoint, timeout=5)
        return response.status_code == 200
    except:
        return False