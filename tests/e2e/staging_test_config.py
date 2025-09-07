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
        
        CRITICAL FIX: Now uses isolated environment to match backend exactly.
        This fixes the WebSocket 403 authentication failures by ensuring the
        JWT secret resolution matches UserContextExtractor._get_jwt_secret() exactly.
        """
        try:
            import jwt
            from datetime import datetime, timedelta, timezone
            import uuid
            from shared.isolated_environment import get_env
            
            # CRITICAL FIX: Use isolated environment and match backend priority exactly
            env = get_env()
            
            # CRITICAL FIX: Priority order MUST match UserContextExtractor._get_jwt_secret() exactly
            # The backend uses this exact priority, so tests must match it perfectly:
            
            # Get current environment to determine which secret to use
            environment = env.get("ENVIRONMENT", "development").lower()
            
            # 1. Try environment-specific secret first (JWT_SECRET_STAGING for staging)
            env_specific_key = f"JWT_SECRET_{environment.upper()}"
            secret = env.get(env_specific_key)
            if secret:
                print(f"Using {env_specific_key} for test token (environment-specific)")
                secret = secret.strip()
            # 2. Try generic JWT_SECRET_KEY (this is what backend falls back to)
            elif env.get("JWT_SECRET_KEY"):
                secret = env.get("JWT_SECRET_KEY").strip()
                print(f"Using JWT_SECRET_KEY for test token (generic secret)")
            # 3. Try E2E bypass key
            elif env.get("E2E_BYPASS_KEY"):
                secret = env.get("E2E_BYPASS_KEY").strip()
                print(f"Using E2E_BYPASS_KEY for test token (bypass mechanism)")
            # 4. Try alternative staging secret
            elif env.get("STAGING_JWT_SECRET"):
                secret = env.get("STAGING_JWT_SECRET").strip()
                print(f"Using STAGING_JWT_SECRET for test token (alternative)")
            # 5. Environment-specific defaults (matches backend fallback logic)
            elif environment in ["testing", "development"]:
                secret = "test_jwt_secret_key_for_development_only"
                print(f"Using development default JWT secret for {environment}")
            else:
                # Final fallback - use the actual staging secret from config/staging.env
                # This should only be used in actual staging environment
                secret = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
                print("WARNING: Using hardcoded staging secret fallback - this should only happen in staging")
            
            # Create payload with required claims
            payload = {
                "sub": f"test-user-{uuid.uuid4().hex[:8]}",
                "email": "test@netrasystems.ai",
                "permissions": ["read", "write"],
                "iat": int(datetime.now(timezone.utc).timestamp()),
                "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
                "token_type": "access",
                "iss": "netra-auth-service",
                "jti": str(uuid.uuid4())  # Required JWT ID for replay protection
            }
            
            token = jwt.encode(payload, secret, algorithm="HS256")
            print(f"Created JWT token for staging authentication (user: {payload['sub']})")
            return token
            
        except Exception as e:
            print(f"CRITICAL: Failed to create test JWT token: {e}")
            print("This will cause WebSocket 403 authentication failures in staging tests")
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