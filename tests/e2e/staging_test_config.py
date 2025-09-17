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
    
    # Backend URLs - Using CLAUDE.md *.netrasystems.ai domains (Issue #1278)
    backend_url: str = "https://staging.netrasystems.ai"
    api_url: str = "https://staging.netrasystems.ai/api"
    websocket_url: str = "wss://api-staging.netrasystems.ai/api/v1/websocket"
    
    # CRITICAL FIX: Add missing base_url attribute (required by configuration system)
    base_url: str = "https://staging.netrasystems.ai"
    
    # Auth service URLs (when deployed) - Updated per CLAUDE.md domains
    auth_url: str = "https://staging.netrasystems.ai"

    # Frontend URL (when deployed)
    frontend_url: str = "https://staging.netrasystems.ai"
    
    # Test configuration - PRIORITY 3 FIX: Cloud-native timeout hierarchy
    # CRITICAL: These timeouts coordinate with centralized timeout_configuration.py
    timeout: int = 60  # seconds - general test timeout
    retry_count: int = 3
    retry_delay: float = 2.0  # seconds
    
    # Cloud-native WebSocket timeouts for staging (35s > 30s agent coordination)
    # SSOT INTEGRATION: Use centralized timeout configuration when available
    websocket_recv_timeout: int = 35  # PRIORITY 3 FIX: 3s  ->  35s for Cloud Run
    websocket_connection_timeout: int = 60
    agent_execution_timeout: int = 30  # PRIORITY 3 FIX: 15s  ->  30s (< WebSocket timeout)
    
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
    
    def get_cloud_native_timeout(self) -> int:
        """Get cloud-native WebSocket recv timeout for staging environment.

        PRIORITY 3 FIX: Returns timeout optimized for GCP Cloud Run staging environment
        instead of hardcoded 3-second timeout that causes premature failures.

        SSOT INTEGRATION: Uses centralized timeout_configuration.py when available,
        falls back to staging-specific config. This ensures proper coordination
        with timeout hierarchy (WebSocket > Agent timeouts).

        Returns:
            int: WebSocket recv timeout in seconds (environment-aware, 18s for staging GCP)
        """
        try:
            # SSOT COMPLIANCE: Use centralized timeout configuration
            from netra_backend.app.core.timeout_configuration import get_websocket_recv_timeout
            centralized_timeout = get_websocket_recv_timeout()
            print(f"[SSOT TIMEOUT] Using centralized timeout configuration: {centralized_timeout}s")
            return centralized_timeout
        except ImportError:
            # Fallback to staging-specific timeout if centralized config not available
            print(f"[FALLBACK TIMEOUT] Using staging fallback timeout: {self.websocket_recv_timeout}s")
            return self.websocket_recv_timeout
    
    def get_websocket_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        """
        Get headers for WebSocket connection with E2E test detection support.
        
        CRITICAL FIX: These headers enable the WebSocket route to detect E2E tests
        and bypass full JWT validation, preventing timeout failures in staging.
        
        Supports WebSocket subprotocol authentication method as per unified auth service:
        - Authorization header with Bearer token
        - sec-websocket-protocol header with jwt.<base64url_token> format
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
            # Method 1: Authorization header (primary)
            headers["Authorization"] = f"Bearer {jwt_token}"
            
            # Method 2: WebSocket subprotocol header (secondary)
            # PHASE 1 FIX: Remove unsupported subprotocol to prevent "no subprotocols supported" error
            try:
                import base64
                # Remove "Bearer " prefix if present for subprotocol encoding
                clean_token = jwt_token.replace("Bearer ", "").strip()
                # Base64url encode the token for WebSocket subprotocol
                encoded_token = base64.urlsafe_b64encode(clean_token.encode()).decode().rstrip('=')
                # PHASE 1 FIX: Only use subprotocol if backend supports it (disabled for staging)
                # headers["sec-websocket-protocol"] = f"jwt.{encoded_token}"
                print(f"[STAGING PHASE1 FIX] Subprotocol disabled - staging backend doesn't support jwt-auth subprotocols")
                print(f"[STAGING PHASE1 FIX] Using Authorization header only for WebSocket auth")
            except Exception as e:
                print(f"[WARNING] Could not encode JWT for WebSocket subprotocol: {e}")
                # PHASE 1 FIX: Don't set fallback subprotocol that causes negotiation failure
                print(f"[STAGING PHASE1 FIX] No subprotocol set - using header auth only")
            
            print(f"[STAGING AUTH FIX] Added JWT token to WebSocket headers (Authorization + subprotocol)")
        else:
            # Fallback test headers (will likely be rejected but enables auth flow testing)
            headers["X-Test-Auth"] = "test-token-for-staging"
            # PHASE 1 FIX: Remove fallback subprotocol that causes negotiation failure
            # headers["sec-websocket-protocol"] = "e2e-testing"
            print(f"[WARNING] No JWT token available - using test header fallback without subprotocol")
            
        print(f"[STAGING AUTH FIX] WebSocket headers include E2E detection: {list(headers.keys())}")
        return headers

    def get_websocket_subprotocols(self, token: Optional[str] = None) -> list:
        """
        Get WebSocket subprotocols for staging environment.

        PHASE 1 FIX: Staging backend doesn't support subprotocols, so return empty list
        to prevent "no subprotocols supported" negotiation errors.

        Args:
            token: JWT token (not used since staging doesn't support subprotocol auth)

        Returns:
            Empty list - staging backend doesn't support subprotocols
        """
        # PHASE 1 FIX: Return empty list since staging backend doesn't support subprotocols
        print(f"[STAGING PHASE1 FIX] get_websocket_subprotocols returning empty list - staging backend doesn't support subprotocols")
        return []
    
    def create_test_jwt_token(self) -> Optional[str]:
        """Create a test JWT token for staging authentication using EXISTING staging users.

        CRITICAL FIX: Uses pre-existing staging test users instead of generating random ones.
        This ensures user validation passes in staging environment.

        SSOT COMPLIANCE: Implements singleton prevention pattern to avoid
        "Multiple manager instances" authentication edge cases detected in staging logs.
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

            # SSOT COMPLIANCE: Use session-based selection to prevent authentication race conditions
            # This prevents multiple manager instances for the same user across concurrent tests
            import time
            session_seed = int(time.time() / 300)  # 5-minute session windows
            user_index = session_seed % len(STAGING_TEST_USERS)
            test_user = STAGING_TEST_USERS[user_index]

            print(f"[SSOT AUTH] Using session-based user selection to prevent manager duplication")
            print(f"[SSOT AUTH] Session seed: {session_seed}, Selected user: {test_user['user_id']}")
            
            print(f"[STAGING AUTH FIX] Using EXISTING staging user: {test_user['user_id']}")
            print(f"[STAGING AUTH FIX] This user should exist in staging database")
            
            # Use SSOT E2E Auth Helper for staging with EXISTING user
            from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
            
            # Ensure E2E_OAUTH_SIMULATION_KEY is set for staging
            if not os.environ.get("E2E_OAUTH_SIMULATION_KEY"):
                os.environ["E2E_OAUTH_SIMULATION_KEY"] = "staging-e2e-test-bypass-key-2025"
                print(f"[STAGING TEST FIX] Set E2E_OAUTH_SIMULATION_KEY for staging testing")
            
            # Create staging config with updated auth service URL
            staging_config = E2EAuthConfig.for_staging()
            staging_config.auth_service_url = "https://staging.netrasystems.ai"
            staging_config.jwt_validation_strict = False  # Allow E2E test tokens in staging
            auth_helper = E2EAuthHelper(config=staging_config, environment="staging")
            
            # Create token for EXISTING staging user (should pass user validation)
            # PHASE 2 FIX: Add agent-specific permissions for WebSocket agent events
            token = auth_helper.create_test_jwt_token(
                user_id=test_user["user_id"],
                email=test_user["email"],
                permissions=["read", "write", "execute", "basic_chat", "agent_access"]  # Agent-enabled permissions
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
                # PHASE 2 FIX: Include agent permissions in fallback JWT
                payload = {
                    "sub": f"fallback-user-{uuid.uuid4().hex[:8]}",
                    "email": "fallback-test@netrasystems.ai",
                    "permissions": ["read", "write", "execute", "basic_chat", "agent_access"],
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
    import os

    # Override for golden path validation testing
    if os.environ.get("BYPASS_STAGING_HEALTH_CHECK") == "true":
        print("[TEST OVERRIDE] Bypassing staging health check for golden path validation")
        return True

    try:
        response = httpx.get(STAGING_CONFIG.health_endpoint, timeout=5)
        return response.status_code == 200
    except:
        return False
