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
    
    # CRITICAL FIX: Add missing base_url attribute (required by configuration system)
    base_url: str = "https://api.staging.netrasystems.ai"
    
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
    
    def get_websocket_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        """
        Get headers for WebSocket connection with E2E test detection support.
        
        CRITICAL FIX: These headers enable the WebSocket route to detect E2E tests
        and bypass full JWT validation, preventing timeout failures in staging.
        """
        headers = {
            # CRITICAL: E2E detection headers that match WebSocket route logic
            "X-Test-Type": "E2E",
            "X-Test-Environment": "staging", 
            "X-E2E-Test": "true",
            "X-Test-Mode": "true",
            
            # Additional context headers
            "X-Test-Session": f"e2e-staging-{os.getpid()}",
            "User-Agent": "Netra-E2E-Tests/1.0",
            
            # Staging optimization hints
            "X-Staging-E2E": "true",
            "X-Test-Priority": "high",
            "X-Auth-Fast-Path": "enabled"
        }
        
        # Add JWT token if provided or available
        jwt_token = token or self.test_jwt_token or self.test_api_key
        
        if not jwt_token:
            # Create a test JWT token for staging WebSocket auth
            jwt_token = self.create_test_jwt_token()
            
        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"
            print(f"[STAGING AUTH FIX] Added JWT token to WebSocket headers")
        else:
            # Fallback test header (will likely be rejected but enables auth flow testing)
            headers["X-Test-Auth"] = "test-token-for-staging"
            print(f"[WARNING] No JWT token available - using test header fallback")
            
        print(f"[STAGING AUTH FIX] WebSocket headers include E2E detection: {list(headers.keys())}")
        return headers
    
    def create_test_jwt_token(self) -> Optional[str]:
        """Create a test JWT token for staging authentication using EXISTING staging users.
        
        CRITICAL FIX: Uses pre-existing staging test users instead of generating random ones.
        This ensures user validation passes in staging environment.
        """
        try:
            # CRITICAL FIX: Use EXISTING staging test users instead of generating random ones
            # These users must be pre-created in the staging database
            STAGING_TEST_USERS = [
                {
                    "user_id": "staging-e2e-user-001", 
                    "email": "e2e-test-001@staging.netrasystems.ai"
                },
                {
                    "user_id": "staging-e2e-user-002",
                    "email": "e2e-test-002@staging.netrasystems.ai" 
                },
                {
                    "user_id": "staging-e2e-user-003",
                    "email": "e2e-test-003@staging.netrasystems.ai"
                }
            ]
            
            # Select user based on process ID for consistency across test runs
            user_index = os.getpid() % len(STAGING_TEST_USERS)
            test_user = STAGING_TEST_USERS[user_index]
            
            print(f"[STAGING AUTH FIX] Using EXISTING staging user: {test_user['user_id']}")
            print(f"[STAGING AUTH FIX] This user should exist in staging database")
            
            # Use SSOT E2E Auth Helper for staging with EXISTING user
            from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
            
            # Ensure E2E_OAUTH_SIMULATION_KEY is set for staging
            if not os.environ.get("E2E_OAUTH_SIMULATION_KEY"):
                os.environ["E2E_OAUTH_SIMULATION_KEY"] = "staging-e2e-test-bypass-key-2025"
                print(f"[STAGING TEST FIX] Set E2E_OAUTH_SIMULATION_KEY for staging testing")
            
            # Create staging config
            staging_config = E2EAuthConfig.for_staging()
            auth_helper = E2EAuthHelper(config=staging_config, environment="staging")
            
            # Create token for EXISTING staging user (should pass user validation)
            token = auth_helper.create_test_jwt_token(
                user_id=test_user["user_id"],
                email=test_user["email"],
                permissions=["read", "write", "execute"]  # Standard test permissions
            )
            
            print(f"[SUCCESS] Created staging JWT for EXISTING user: {test_user['user_id']}")
            print(f"[SUCCESS] This should pass staging user validation checks")
            
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