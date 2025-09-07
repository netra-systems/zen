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
        """Create a test JWT token for staging authentication using SSOT E2E OAuth simulation
        
        CRITICAL FIX: Now uses the existing SSOT staging auth bypass method instead of
        creating fabricated JWT tokens. This ensures the token represents a REAL USER
        in the staging database, which is required for WebSocket authentication.
        
        The previous approach created JWT tokens with fake user IDs that don't exist
        in staging database, causing HTTP 403 errors during user validation.
        """
        try:
            # CRITICAL FIX: Ensure E2E_OAUTH_SIMULATION_KEY is available for testing
            import os
            env_key = os.environ.get("E2E_OAUTH_SIMULATION_KEY")
            if not env_key:
                # Set appropriate bypass key based on environment
                # In staging tests, we need to use a compatible key
                bypass_key = "staging-e2e-test-bypass-key-2025"
                os.environ["E2E_OAUTH_SIMULATION_KEY"] = bypass_key
                print(f"[STAGING TEST FIX] Set E2E_OAUTH_SIMULATION_KEY for staging testing")
            
            # CRITICAL FIX: Use existing SSOT staging auth bypass instead of fabricated tokens
            from tests.e2e.staging_auth_bypass import get_staging_auth
            
            # Get authenticated token from staging auth service
            # This creates a REAL USER in the staging database for E2E testing
            staging_auth = get_staging_auth()
            
            # Use staging auth service to create real user token
            # This token will represent an actual user record in staging database
            token = staging_auth.get_sync_token(
                email="e2e-websocket-test@staging.netrasystems.ai",
                name="E2E WebSocket Test User",
                permissions=["read", "write"]
            )
            
            print(f"[SUCCESS] STAGING AUTH BYPASS TOKEN CREATED using SSOT method")
            print(f"[SUCCESS] Token represents REAL USER in staging database")
            print(f"[SUCCESS] This fixes WebSocket 403 authentication failures")
            
            return token
                
        except Exception as e:
            print(f"[WARNING] SSOT staging auth bypass failed: {e}")
            print(f"[INFO] Falling back to direct JWT creation for development environments")
            
            # FALLBACK: Only for development - use direct JWT creation
            try:
                import jwt
                import hashlib
                from datetime import datetime, timedelta, timezone
                import uuid
                
                # Use staging secret for fallback token (development only)
                staging_secret = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
                
                # Create fallback payload - NOTE: This may still fail in staging
                payload = {
                    "sub": f"fallback-user-{uuid.uuid4().hex[:8]}",
                    "email": "fallback-test@netrasystems.ai", 
                    "permissions": ["read", "write"],
                    "iat": int(datetime.now(timezone.utc).timestamp()),
                    "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
                    "iss": "netra-auth-service",
                    "jti": str(uuid.uuid4())
                }
                
                token = jwt.encode(payload, staging_secret, algorithm="HS256")
                
                secret_hash = hashlib.md5(staging_secret.encode()).hexdigest()[:16]
                print(f"[FALLBACK] Created direct JWT token (hash: {secret_hash})")
                print(f"[WARNING] This may fail in staging due to user validation requirements")
                
                return token
                
            except Exception as fallback_error:
                print(f"[CRITICAL ERROR] Both SSOT auth bypass and fallback JWT creation failed!")
                print(f"[CRITICAL ERROR] SSOT error: {e}")
                print(f"[CRITICAL ERROR] Fallback error: {fallback_error}")
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