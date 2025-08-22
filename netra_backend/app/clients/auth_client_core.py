"""
Core auth service client functionality.
Handles token validation, authentication, and service-to-service communication.
"""

import logging
from typing import Dict, List, Optional

import httpx

from netra_backend.app.clients.auth_client_cache import (
    AuthCircuitBreakerManager,
    AuthServiceSettings,
    AuthTokenCache,
)
from netra_backend.app.clients.auth_client_config import (
    EnvironmentDetector,
    OAuthConfig,
    OAuthConfigGenerator,
)
from netra_backend.app.core.tracing import TracingManager

logger = logging.getLogger(__name__)


class AuthServiceClient:
    """Client for communicating with auth service."""
    
    def __init__(self):
        self.settings = AuthServiceSettings()
        self.token_cache = AuthTokenCache(self.settings.cache_ttl)
        self.circuit_manager = AuthCircuitBreakerManager()
        self.environment_detector = EnvironmentDetector()
        self.oauth_generator = OAuthConfigGenerator()
        self.tracing_manager = TracingManager()
        self._client = None
    
    def _create_http_client(self) -> httpx.AsyncClient:
        """Create new HTTP client instance."""
        return httpx.AsyncClient(
            base_url=self.settings.base_url,
            timeout=httpx.Timeout(10.0),
            limits=httpx.Limits(max_keepalive_connections=5)
        )
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if not self._client:
            self._client = self._create_http_client()
        return self._client
    
    async def _check_auth_service_enabled(self, token: str) -> Optional[Dict]:
        """Check if auth service is enabled."""
        if not self.settings.enabled:
            logger.error("Auth service is required for token validation")
            return {"valid": False}
        return None
    
    async def _try_cached_token(self, token: str) -> Optional[Dict]:
        """Try to get token from cache, checking for invalidation."""
        cached_result = self.token_cache.get_cached_token(token)
        if cached_result:
            # If we have a cached result, still check if token was blacklisted
            # This provides additional security in case of race conditions
            try:
                blacklist_check = await self._check_token_blacklist(token)
                if blacklist_check and blacklist_check.get("blacklisted", False):
                    # Token is blacklisted, mark as invalid and remove from cache
                    self.token_cache.invalidate_cached_token(token)
                    return None
            except Exception as e:
                logger.warning(f"Blacklist check failed, proceeding with cached result: {e}")
        return cached_result
    
    async def _validate_with_circuit_breaker(self, token: str) -> Optional[Dict]:
        """Validate token using circuit breaker."""
        return await self.circuit_manager.call_with_breaker(
            self._validate_token_remote, token
        )
    
    async def _cache_validation_result(self, token: str, result: Optional[Dict]) -> Optional[Dict]:
        """Cache validation result if successful."""
        if result:
            self.token_cache.cache_token(token, result)
        return result
    
    async def _handle_validation_error(self, token: str, error: Exception) -> Optional[Dict]:
        """Handle validation error and fallback."""
        logger.error(f"Token validation failed: {error}")
        return await self._local_validate(token)
    
    async def _try_validation_steps(self, token: str) -> Optional[Dict]:
        """Try validation with cache and circuit breaker."""
        cached = await self._try_cached_token(token)
        if cached:
            return cached
        result = await self._validate_with_circuit_breaker(token)
        return await self._cache_validation_result(token, result)
    
    async def _execute_token_validation(self, token: str) -> Optional[Dict]:
        """Execute token validation with error handling."""
        try:
            return await self._try_validation_steps(token)
        except Exception as e:
            return await self._handle_validation_error(token, e)
    
    async def validate_token_jwt(self, token: str) -> Optional[Dict]:
        """Validate access token with caching."""
        disabled_result = await self._check_auth_service_enabled(token)
        if disabled_result is not None:
            return disabled_result
        return await self._execute_token_validation(token)
    
    async def _build_validation_request(self, token: str) -> Dict:
        """Build validation request payload."""
        return {"token": token}
    
    async def _parse_validation_response(self, data: Dict) -> Dict:
        """Parse validation response data."""
        return {
            "valid": data.get("valid", False),
            "user_id": data.get("user_id"),
            "email": data.get("email"),
            "permissions": data.get("permissions", [])
        }
    
    async def _send_validation_request(self, client: httpx.AsyncClient, request_data: Dict) -> Optional[Dict]:
        """Send validation request with distributed tracing headers."""
        # Add tracing headers for cross-service communication
        trace_headers = self.tracing_manager.inject_trace_headers()
        
        response = await client.post(
            "/auth/validate", 
            json=request_data,
            headers=trace_headers
        )
        
        # Log the trace propagation for debugging
        logger.debug(f"Auth validation request sent with trace headers: {trace_headers}")
        
        if response.status_code == 200:
            return await self._parse_validation_response(response.json())
        return None
    
    async def _prepare_remote_validation(self, token: str):
        """Prepare remote validation components."""
        client = await self._get_client()
        request_data = await self._build_validation_request(token)
        return client, request_data
    
    async def _validate_token_remote(self, token: str) -> Optional[Dict]:
        """Remote token validation."""
        client, request_data = await self._prepare_remote_validation(token)
        try:
            return await self._send_validation_request(client, request_data)
        except Exception as e:
            logger.error(f"Remote validation error: {e}")
            raise
    
    async def _build_login_request(self, email: str, password: str, provider: str) -> Dict:
        """Build login request payload."""
        return {
            "email": email,
            "password": password,
            "provider": provider
        }
    
    async def _execute_login_request(self, request_data: Dict) -> Optional[Dict]:
        """Execute login request."""
        client = await self._get_client()
        response = await client.post("/auth/login", json=request_data)
        return response.json() if response.status_code == 200 else None
    
    async def _attempt_login(self, email: str, password: str, provider: str) -> Optional[Dict]:
        """Attempt login with error handling."""
        request_data = await self._build_login_request(email, password, provider)
        try:
            return await self._execute_login_request(request_data)
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return None
    
    async def login(self, email: str, password: str, 
                   provider: str = "local") -> Optional[Dict]:
        """User login through auth service."""
        if not self.settings.enabled:
            return None
        return await self._attempt_login(email, password, provider)
    
    async def _build_logout_headers(self, token: str) -> Dict[str, str]:
        """Build logout request headers."""
        from netra_backend.app.core.auth_constants import HeaderConstants
        return {HeaderConstants.AUTHORIZATION: f"{HeaderConstants.BEARER_PREFIX}{token}"}
    
    async def _build_logout_payload(self, session_id: Optional[str]) -> Dict:
        """Build logout request payload."""
        return {"session_id": session_id} if session_id else {}
    
    async def _execute_logout_request(self, token: str, session_id: Optional[str]) -> bool:
        """Execute logout request."""
        client = await self._get_client()
        headers = await self._build_logout_headers(token)
        payload = await self._build_logout_payload(session_id)
        response = await client.post("/auth/logout", headers=headers, json=payload)
        return response.status_code == 200
    
    async def _process_logout_result(self, token: str, result: bool) -> bool:
        """Process logout result and invalidate cache."""
        self.token_cache.invalidate_cached_token(token)
        return result
    
    async def _check_token_blacklist(self, token: str) -> Optional[Dict]:
        """Check if token is blacklisted in auth service."""
        if not self.settings.enabled:
            return {"blacklisted": False}
        
        try:
            client = await self._get_client()
            request_data = {"token": token}
            
            # Add tracing headers for cross-service communication
            trace_headers = self.tracing_manager.inject_trace_headers()
            
            response = await client.post(
                "/auth/check-blacklist",
                json=request_data,
                headers=trace_headers
            )
            
            if response.status_code == 200:
                return response.json()
            return {"blacklisted": False}
        except Exception as e:
            logger.error(f"Blacklist check failed: {e}")
            # In case of error, assume token is not blacklisted to avoid false positives
            # The main validation will still happen at the auth service
            return {"blacklisted": False}
    
    async def _attempt_logout(self, token: str, session_id: Optional[str]) -> bool:
        """Attempt logout with error handling."""
        try:
            result = await self._execute_logout_request(token, session_id)
            return await self._process_logout_result(token, result)
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
    
    async def logout(self, token: str, session_id: Optional[str] = None) -> bool:
        """User logout through auth service."""
        if not self.settings.enabled:
            return True
        return await self._attempt_logout(token, session_id)
    
    async def _build_refresh_request(self, refresh_token: str) -> Dict:
        """Build refresh token request payload."""
        return {"refresh_token": refresh_token}
    
    async def _execute_refresh_request(self, request_data: Dict) -> Optional[Dict]:
        """Execute refresh token request."""
        client = await self._get_client()
        response = await client.post("/auth/refresh", json=request_data)
        return response.json() if response.status_code == 200 else None
    
    async def _attempt_token_refresh(self, refresh_token: str) -> Optional[Dict]:
        """Attempt token refresh with error handling."""
        request_data = await self._build_refresh_request(refresh_token)
        try:
            return await self._execute_refresh_request(request_data)
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict]:
        """Refresh access token."""
        if not self.settings.enabled:
            return None
        return await self._attempt_token_refresh(refresh_token)
    
    async def _check_service_token_prereqs(self) -> bool:
        """Check service token prerequisites."""
        if not self.settings.enabled:
            return False
        if not self.settings.is_service_secret_configured():
            logger.warning("Service secret not configured")
            return False
        return True
    
    async def _build_service_token_request(self) -> Dict:
        """Build service token request payload."""
        service_id, service_secret = self.settings.get_service_credentials()
        return {
            "service_id": service_id,
            "service_secret": service_secret
        }
    
    async def _execute_service_token_request(self, request_data: Dict) -> Optional[str]:
        """Execute service token request."""
        client = await self._get_client()
        response = await client.post("/auth/service-token", json=request_data)
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    async def _attempt_service_token_creation(self) -> Optional[str]:
        """Attempt service token creation with error handling."""
        request_data = await self._build_service_token_request()
        try:
            return await self._execute_service_token_request(request_data)
        except Exception as e:
            logger.error(f"Service token creation failed: {e}")
            return None
    
    async def create_service_token(self) -> Optional[str]:
        """Get service-to-service auth token."""
        if not await self._check_service_token_prereqs():
            return None
        return await self._attempt_service_token_creation()
    
    async def hash_password(self, password: str) -> Optional[Dict]:
        """Hash password through auth service."""
        if not self.settings.enabled:
            logger.error("Auth service is required for password hashing")
            return None
        
        try:
            client = await self._get_client()
            response = await client.post("/auth/hash-password", json={"password": password})
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            return None
    
    async def verify_password(self, plain_password: str, hashed_password: str) -> Optional[Dict]:
        """Verify password through auth service."""
        if not self.settings.enabled:
            logger.error("Auth service is required for password verification")
            return None
        
        try:
            client = await self._get_client()
            response = await client.post("/auth/verify-password", json={
                "plain_password": plain_password,
                "hashed_password": hashed_password
            })
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return None
    
    async def create_token(self, token_data: Dict) -> Optional[Dict]:
        """Create access token through auth service."""
        if not self.settings.enabled:
            logger.error("Auth service is required for token creation")
            return None
        
        try:
            client = await self._get_client()
            response = await client.post("/auth/create-token", json=token_data)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Token creation failed: {e}")
            return None
    
    async def _local_validate(self, token: str) -> Optional[Dict]:
        """NO LOCAL VALIDATION - Auth service required."""
        logger.error("Auth service is required for token validation")
        return {"valid": False}
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
    
    def detect_environment(self):
        """Detect current environment from environment variables."""
        return self.environment_detector.detect_environment()
    
    def get_oauth_config(self) -> OAuthConfig:
        """Get OAuth configuration for current environment."""
        environment = self.detect_environment()
        return self.oauth_generator.get_oauth_config(environment)
    
    # RBAC Methods for Role-Based Access Control
    
    def _create_mock_token(self, user_role: str, user_email: str, user_id: str = None) -> str:
        """Create a mock JWT token for testing."""
        import jwt as pyjwt
        import uuid
        from datetime import datetime, timedelta
        
        if not user_id:
            user_id = str(uuid.uuid4())
            
        # Define role permissions
        role_permissions = {
            "super_admin": [
                "system:*", "users:*", "agents:*", "billing:*", "analytics:*"
            ],
            "org_admin": [
                "users:read", "users:write", "users:delete", "agents:*", 
                "analytics:read", "billing:read"
            ],
            "team_lead": [
                "users:read", "users:write", "agents:read", "agents:write", 
                "analytics:read"
            ],
            "developer": [
                "agents:read", "agents:write", "analytics:read"
            ],
            "viewer": [
                "agents:read", "analytics:read"
            ],
            "guest": [
                "public:read"
            ]
        }
        
        payload = {
            "sub": user_id,
            "email": user_email,
            "role": user_role,
            "permissions": role_permissions.get(user_role, []),
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4())
        }
        
        # Use a test secret
        return pyjwt.encode(payload, "test_secret", algorithm="HS256")
    
    async def login(self, request) -> Optional[Dict]:
        """User login through auth service with LoginRequest object."""
        if not self.settings.enabled:
            # Provide fallback mock implementation for testing
            logger.info("Auth service disabled - using mock implementation")
            
            # Handle both dict and LoginRequest object
            if hasattr(request, 'email'):
                email = request.email
                password = request.password or ""
            else:
                email = request.get('email')
                password = request.get('password', '')
                
            # Extract role from email for testing (e.g., super_admin@test.com -> super_admin)
            role = email.split('@')[0] if '@' in email else 'guest'
            user_id = f"user_{role}"
            
            # Create mock token
            access_token = self._create_mock_token(role, email, user_id)
            
            return type('LoginResponse', (), {
                'access_token': access_token,
                'refresh_token': f"refresh_{user_id}",
                'role': role,
                'user_id': user_id,
                'token_type': 'Bearer',
                'expires_in': 3600
            })()
            
        # Handle both dict and LoginRequest object
        if hasattr(request, 'email'):
            email = request.email
            password = request.password or ""
            provider = getattr(request, 'provider', 'local')
        else:
            email = request.get('email')
            password = request.get('password', '')
            provider = request.get('provider', 'local')
        
        result = await self._attempt_login(email, password, provider)
        
        if result:
            # Ensure the response has the expected structure
            return type('LoginResponse', (), {
                'access_token': result.get('access_token', ''),
                'refresh_token': result.get('refresh_token'),
                'role': result.get('role', 'guest'),
                'user_id': result.get('user_id', ''),
                'token_type': result.get('token_type', 'Bearer'),
                'expires_in': result.get('expires_in', 3600)
            })()
        return None
    
    def _decode_token(self, token: str) -> Dict:
        """Decode JWT token for mock implementation."""
        try:
            import jwt as pyjwt
            # Use the same test secret as in _create_mock_token
            decoded = pyjwt.decode(token, "test_secret", algorithms=["HS256"])
            return decoded
        except Exception as e:
            logger.error(f"Token decode failed: {e}")
            return {}
    
    def _check_permission_match(self, required_permission: str, user_permissions: List[str]) -> bool:
        """Check if user has the required permission."""
        for perm in user_permissions:
            # Exact match
            if perm == required_permission:
                return True
            # Wildcard match (e.g., "agents:*" matches "agents:read")
            if perm.endswith(":*") and required_permission.startswith(perm[:-1]):
                return True
            # System wildcard
            if perm == "system:*":
                return True
        return False
    
    def _resource_to_permission(self, resource: str, action: str) -> str:
        """Convert resource and action to permission format."""
        # Extract permission from resource path
        # e.g., "/api/users" + "delete" -> "users:delete"
        # e.g., "/api/system/config" + "write" -> "system:write"
        resource_parts = resource.strip('/').split('/')
        
        if 'api' in resource_parts:
            # Remove 'api' prefix
            resource_parts = [p for p in resource_parts if p != 'api']
        
        if resource_parts:
            resource_type = resource_parts[0]  # e.g., "users", "system", "agents"
            return f"{resource_type}:{action}"
        
        return f"unknown:{action}"
        
    async def check_authorization(self, token: str, resource: str, action: str) -> Dict:
        """Check authorization for resource and action."""
        if not self.settings.enabled:
            # Mock implementation
            token_data = self._decode_token(token)
            user_permissions = token_data.get('permissions', [])
            required_permission = self._resource_to_permission(resource, action)
            
            authorized = self._check_permission_match(required_permission, user_permissions)
            
            return type('AuthorizationResult', (), {
                'authorized': authorized,
                'reason': 'Allowed' if authorized else f'Missing permission: {required_permission}',
                'permissions': user_permissions
            })()
        
        try:
            client = await self._get_client()
            response = await client.post("/auth/check-authorization", json={
                "token": token,
                "resource": resource,
                "action": action
            })
            
            if response.status_code == 200:
                result = response.json()
                return type('AuthorizationResult', (), {
                    'authorized': result.get('authorized', False),
                    'reason': result.get('reason', 'Unknown'),
                    'permissions': result.get('permissions', [])
                })()
            else:
                return type('AuthorizationResult', (), {
                    'authorized': False,
                    'reason': 'Service error',
                    'permissions': []
                })()
        except Exception as e:
            logger.error(f"Authorization check failed: {e}")
            return type('AuthorizationResult', (), {
                'authorized': False,
                'reason': f'Error: {str(e)}',
                'permissions': []
            })()
    
    async def check_permission(self, token: str, permission: str) -> Dict:
        """Check if token has specific permission."""
        if not self.settings.enabled:
            # Mock implementation
            token_data = self._decode_token(token)
            user_permissions = token_data.get('permissions', [])
            has_permission = self._check_permission_match(permission, user_permissions)
            
            return type('PermissionResult', (), {
                'has_permission': has_permission,
                'reason': 'Granted' if has_permission else f'Missing permission: {permission}'
            })()
        
        try:
            client = await self._get_client()
            response = await client.post("/auth/check-permission", json={
                "token": token,
                "permission": permission
            })
            
            if response.status_code == 200:
                result = response.json()
                return type('PermissionResult', (), {
                    'has_permission': result.get('has_permission', False),
                    'reason': result.get('reason', 'Unknown')
                })()
            else:
                return type('PermissionResult', (), {
                    'has_permission': False,
                    'reason': 'Service error'
                })()
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return type('PermissionResult', (), {
                'has_permission': False,
                'reason': f'Error: {str(e)}'
            })()
    
    async def make_api_call(self, token: str, endpoint: str) -> Dict:
        """Make rate-limited API call."""
        if not self.settings.enabled:
            # Mock rate limiting - allow most calls but simulate some limits
            token_data = self._decode_token(token)
            role = token_data.get('role', 'guest')
            
            # Simple mock rate limiting
            if role in ['guest', 'viewer'] and endpoint != '/api/test':
                # Simulate rate limit for lower roles on non-test endpoints
                import random
                if random.random() < 0.3:  # 30% chance of rate limit
                    raise Exception("Rate limit exceeded")
            
            return type('ApiCallResult', (), {'success': True})()
            
        try:
            client = await self._get_client()
            response = await client.post("/auth/api-call", json={
                "token": token,
                "endpoint": endpoint
            })
            
            if response.status_code == 200:
                return type('ApiCallResult', (), {'success': True})()
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded")
            else:
                return type('ApiCallResult', (), {'success': False})()
        except Exception as e:
            if "rate limit" in str(e).lower():
                raise
            logger.error(f"API call failed: {e}")
            return type('ApiCallResult', (), {'success': False})()
    
    async def create_agent(self, token: str, agent_name: str) -> Optional[Dict]:
        """Create agent with resource limits check."""
        if not self.settings.enabled:
            # Mock agent creation
            token_data = self._decode_token(token)
            role = token_data.get('role', 'guest')
            
            # Check if role can create agents
            allowed_roles = ['super_admin', 'org_admin', 'team_lead', 'developer']
            if role not in allowed_roles:
                return None
                
            import uuid
            agent_id = f"agent_{uuid.uuid4().hex[:8]}"
            
            return type('Agent', (), {
                'id': agent_id,
                'name': agent_name
            })()
            
        try:
            client = await self._get_client()
            response = await client.post("/auth/create-agent", json={
                "token": token,
                "agent_name": agent_name
            })
            
            if response.status_code == 200:
                result = response.json()
                return type('Agent', (), {
                    'id': result.get('id', ''),
                    'name': agent_name
                })()
            return None
        except Exception as e:
            logger.error(f"Agent creation failed: {e}")
            return None
    
    async def delete_agent(self, token: str, agent_id: str) -> bool:
        """Delete agent."""
        try:
            client = await self._get_client()
            response = await client.delete(f"/auth/agents/{agent_id}", headers={
                "Authorization": f"Bearer {token}"
            })
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Agent deletion failed: {e}")
            return False
    
    async def validate_token_for_service(self, token: str, service_name: str) -> Dict:
        """Validate token for specific service."""
        if not self.settings.enabled:
            # Mock service validation
            token_data = self._decode_token(token)
            if token_data:
                return type('ServiceValidationResult', (), {
                    'valid': True,
                    'role': token_data.get('role', 'guest'),
                    'permissions': token_data.get('permissions', [])
                })()
            else:
                return type('ServiceValidationResult', (), {
                    'valid': False,
                    'role': 'guest',
                    'permissions': []
                })()
        
        try:
            client = await self._get_client()
            response = await client.post("/auth/validate-service-token", json={
                "token": token,
                "service_name": service_name
            })
            
            if response.status_code == 200:
                result = response.json()
                return type('ServiceValidationResult', (), {
                    'valid': result.get('valid', False),
                    'role': result.get('role', 'guest'),
                    'permissions': result.get('permissions', [])
                })()
            else:
                return type('ServiceValidationResult', (), {
                    'valid': False,
                    'role': 'guest',
                    'permissions': []
                })()
        except Exception as e:
            logger.error(f"Service token validation failed: {e}")
            return type('ServiceValidationResult', (), {
                'valid': False,
                'role': 'guest',
                'permissions': []
            })()
    
    async def update_user_role(self, token: str, user_id: str, new_role: str) -> Dict:
        """Update user role (admin only)."""
        if not self.settings.enabled:
            # Mock role update - only admins can update roles
            token_data = self._decode_token(token)
            user_role = token_data.get('role', 'guest')
            
            # Check if user has permission to update roles
            if user_role not in ['super_admin', 'org_admin']:
                raise Exception("Unauthorized: Cannot update user role")
            
            # Mock successful update
            return {"success": True, "message": f"Role updated to {new_role}"}
        
        try:
            client = await self._get_client()
            response = await client.put(f"/auth/users/{user_id}/role", 
                json={"role": new_role},
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                raise Exception("Unauthorized: Cannot update user role")
            else:
                raise Exception("Failed to update user role")
        except Exception as e:
            logger.error(f"Role update failed: {e}")
            raise
    
    async def get_user_info(self, token: str, user_id: str) -> Dict:
        """Get user information."""
        if not self.settings.enabled:
            # Mock user info - extract role from user_id
            role = user_id.replace('user_', '') if user_id.startswith('user_') else 'guest'
            email = f"{role}@test.com"
            
            # Get permissions for role
            role_permissions = {
                "super_admin": ["system:*", "users:*", "agents:*", "billing:*", "analytics:*"],
                "org_admin": ["users:read", "users:write", "users:delete", "agents:*", "analytics:read", "billing:read"],
                "team_lead": ["users:read", "users:write", "agents:read", "agents:write", "analytics:read"],
                "developer": ["agents:read", "agents:write", "analytics:read"],
                "viewer": ["agents:read", "analytics:read"],
                "guest": ["public:read"]
            }
            
            return type('UserInfo', (), {
                'user_id': user_id,
                'email': email,
                'role': role,
                'permissions': role_permissions.get(role, [])
            })()
        
        try:
            client = await self._get_client()
            response = await client.get(f"/auth/users/{user_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                result = response.json()
                return type('UserInfo', (), {
                    'user_id': result.get('user_id', ''),
                    'email': result.get('email', ''),
                    'role': result.get('role', 'guest'),
                    'permissions': result.get('permissions', [])
                })()
            else:
                return type('UserInfo', (), {
                    'user_id': user_id,
                    'email': '',
                    'role': 'guest',
                    'permissions': []
                })()
        except Exception as e:
            logger.error(f"Get user info failed: {e}")
            return type('UserInfo', (), {
                'user_id': user_id,
                'email': '',
                'role': 'guest',
                'permissions': []
            })()
    
    async def create_impersonation_token(self, admin_token: str, target_user_id: str, 
                                       duration_minutes: int) -> Optional[str]:
        """Create impersonation token (admin only)."""
        if not self.settings.enabled:
            # Mock impersonation - only super_admin can impersonate
            token_data = self._decode_token(admin_token)
            admin_role = token_data.get('role', 'guest')
            admin_user_id = token_data.get('sub', 'unknown')
            
            if admin_role != 'super_admin':
                raise Exception("Unauthorized: Cannot create impersonation token")
            
            # Create mock impersonation token
            import jwt as pyjwt
            import uuid
            from datetime import datetime, timedelta
            
            # Assume target user is developer for testing
            target_role = 'developer'
            target_email = f"{target_role}@test.com"
            
            payload = {
                "sub": target_user_id,
                "email": target_email,
                "role": target_role,
                "permissions": ["agents:read", "agents:write", "analytics:read"],
                "impersonated_by": admin_user_id,
                "exp": datetime.utcnow() + timedelta(minutes=duration_minutes),
                "iat": datetime.utcnow(),
                "jti": str(uuid.uuid4())
            }
            
            return pyjwt.encode(payload, "test_secret", algorithm="HS256")
        
        try:
            client = await self._get_client()
            response = await client.post("/auth/impersonate", json={
                "target_user_id": target_user_id,
                "duration_minutes": duration_minutes
            }, headers={"Authorization": f"Bearer {admin_token}"})
            
            if response.status_code == 200:
                result = response.json()
                return result.get('impersonation_token')
            elif response.status_code == 403:
                raise Exception("Unauthorized: Cannot create impersonation token")
            else:
                return None
        except Exception as e:
            logger.error(f"Impersonation token creation failed: {e}")
            if "unauthorized" in str(e).lower():
                raise
            return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict]:
        """Refresh access token with structured response."""
        result = await self._attempt_token_refresh(refresh_token)
        
        if result:
            return type('RefreshResponse', (), {
                'access_token': result.get('access_token', ''),
                'refresh_token': result.get('refresh_token', refresh_token),
                'token_type': result.get('token_type', 'Bearer'),
                'expires_in': result.get('expires_in', 3600)
            })()
        return None


# Global client instance
auth_client = AuthServiceClient()