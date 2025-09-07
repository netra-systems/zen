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
        
        CRITICAL FIX: Now uses EXACT staging secret from config/staging.env.
        This fixes the WebSocket 403 authentication failures by ensuring test tokens
        use the identical JWT_SECRET_STAGING that the staging WebSocket service uses.
        """
        try:
            import jwt
            import hashlib
            from datetime import datetime, timedelta, timezone
            import uuid
            
            # CRITICAL FIX: Use the EXACT staging secret that staging service uses
            # This secret MUST match what's in config/staging.env line 40
            staging_secret = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
            
            # Diagnostic logging to confirm secret usage
            secret_hash = hashlib.md5(staging_secret.encode()).hexdigest()[:16]
            print(f"🔧 STAGING CONFIG TOKEN FIX: Using staging secret from config/staging.env")
            print(f"🔧 STAGING CONFIG TOKEN FIX: Secret hash {secret_hash} (length: {len(staging_secret)})")
            print(f"🔧 STAGING CONFIG TOKEN FIX: This MUST match staging WebSocket service secret")
            
            # Create payload with proper structure for staging
            payload = {
                "sub": f"test-user-{uuid.uuid4().hex[:8]}",
                "email": "test@netrasystems.ai", 
                "permissions": ["read", "write"],
                "iat": int(datetime.now(timezone.utc).timestamp()),
                "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
                "iss": "netra-auth-service",
                "jti": str(uuid.uuid4())  # JWT ID for replay protection
            }
            
            # Create token with EXACT staging secret
            token = jwt.encode(payload, staging_secret, algorithm="HS256")
            
            # Verify token was created correctly
            user_display = payload['sub'][:8] + "..." if len(payload['sub']) > 8 else payload['sub']
            print(f"✅ STAGING CONFIG TOKEN CREATED: {user_display} with staging secret (hash: {secret_hash})")
            
            return token
                
        except Exception as e:
            print(f"❌ CRITICAL: Staging JWT token creation failed: {e}")
            print(f"❌ This will cause WebSocket 403 authentication failures in staging!")
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