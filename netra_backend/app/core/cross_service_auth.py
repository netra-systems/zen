"""Cross-Service Authentication Module

Provides authentication and authorization mechanisms for inter-service communication
within the Netra Apex platform. Handles JWT tokens, service roles, and auth contexts.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Security, Service Communication 
- Value Impact: Enables secure authenticated communication between microservices
- Strategic Impact: Foundation for zero-trust architecture and service mesh security
"""

import asyncio
import time
from datetime import datetime, UTC, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import jwt
from netra_backend.app.core.config import get_config


class AuthTokenType(Enum):
    """Types of authentication tokens."""
    USER = "user"
    SERVICE = "service"
    ADMIN = "admin"
    SYSTEM = "system"


class ServiceRole(Enum):
    """Service roles for authorization."""
    BACKEND = "backend"
    AUTH_SERVICE = "auth_service"  
    FRONTEND = "frontend"
    WEBSOCKET = "websocket"
    ANALYTICS = "analytics"


@dataclass
class AuthToken:
    """Authentication token with metadata."""
    token: str
    token_type: AuthTokenType
    user_id: Optional[str]
    service_role: Optional[ServiceRole]
    permissions: List[str]
    expires_at: datetime
    issued_at: datetime
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now(UTC) > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if token is valid."""
        return not self.is_expired and bool(self.token)


@dataclass
class AuthContext:
    """Authentication context for requests."""
    token: Optional[AuthToken]
    user_id: Optional[str] 
    service_role: Optional[ServiceRole]
    permissions: List[str]
    request_id: str
    timestamp: datetime
    
    @property
    def is_authenticated(self) -> bool:
        """Check if context is authenticated."""
        return self.token is not None and self.token.is_valid


class CrossServiceAuthManager:
    """Manages cross-service authentication and authorization."""
    
    def __init__(self):
        self.config = get_config()
        self.secret_key = getattr(self.config, 'JWT_SECRET_KEY', 'test-secret-key')
        self.algorithm = 'HS256'
        self.default_expiry = timedelta(hours=24)
        
    async def create_service_token(self, service_role: ServiceRole, 
                                 permissions: List[str] = None) -> AuthToken:
        """Create authentication token for service."""
        if permissions is None:
            permissions = self._get_default_service_permissions(service_role)
            
        issued_at = datetime.now(UTC)
        expires_at = issued_at + self.default_expiry
        
        payload = {
            'type': AuthTokenType.SERVICE.value,
            'service_role': service_role.value,
            'permissions': permissions,
            'iat': issued_at.timestamp(),
            'exp': expires_at.timestamp()
        }
        
        token_str = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        return AuthToken(
            token=token_str,
            token_type=AuthTokenType.SERVICE,
            user_id=None,
            service_role=service_role,
            permissions=permissions,
            expires_at=expires_at,
            issued_at=issued_at
        )
    
    async def create_user_token(self, user_id: str, 
                              permissions: List[str] = None) -> AuthToken:
        """Create authentication token for user."""
        if permissions is None:
            permissions = ['read', 'write', 'agent_access']
            
        issued_at = datetime.now(UTC)
        expires_at = issued_at + self.default_expiry
        
        payload = {
            'type': AuthTokenType.USER.value,
            'user_id': user_id,
            'permissions': permissions,
            'iat': issued_at.timestamp(),
            'exp': expires_at.timestamp()
        }
        
        token_str = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        return AuthToken(
            token=token_str,
            token_type=AuthTokenType.USER,
            user_id=user_id,
            service_role=None,
            permissions=permissions,
            expires_at=expires_at,
            issued_at=issued_at
        )
    
    async def validate_token(self, token_str: str) -> Optional[AuthToken]:
        """Validate and decode authentication token."""
        try:
            payload = jwt.decode(token_str, self.secret_key, algorithms=[self.algorithm])
            
            token_type = AuthTokenType(payload.get('type', 'user'))
            expires_at = datetime.fromtimestamp(payload['exp'], UTC)
            issued_at = datetime.fromtimestamp(payload['iat'], UTC)
            
            service_role = None
            if payload.get('service_role'):
                service_role = ServiceRole(payload['service_role'])
            
            return AuthToken(
                token=token_str,
                token_type=token_type,
                user_id=payload.get('user_id'),
                service_role=service_role,
                permissions=payload.get('permissions', []),
                expires_at=expires_at,
                issued_at=issued_at
            )
            
        except jwt.InvalidTokenError:
            return None
        except Exception:
            return None
    
    async def create_auth_context(self, token_str: Optional[str], 
                                request_id: str) -> AuthContext:
        """Create authentication context from token."""
        token = None
        user_id = None
        service_role = None
        permissions = []
        
        if token_str:
            token = await self.validate_token(token_str)
            if token:
                user_id = token.user_id
                service_role = token.service_role
                permissions = token.permissions
        
        return AuthContext(
            token=token,
            user_id=user_id,
            service_role=service_role,
            permissions=permissions,
            request_id=request_id,
            timestamp=datetime.now(UTC)
        )
    
    async def authorize_request(self, context: AuthContext, 
                              required_permissions: List[str]) -> bool:
        """Check if context has required permissions."""
        if not context.is_authenticated:
            return False
        
        user_permissions = set(context.permissions)
        required_perms = set(required_permissions)
        
        return required_perms.issubset(user_permissions)
    
    def _get_default_service_permissions(self, service_role: ServiceRole) -> List[str]:
        """Get default permissions for service role."""
        permission_map = {
            ServiceRole.BACKEND: ['read', 'write', 'admin', 'service_access'],
            ServiceRole.AUTH_SERVICE: ['read', 'write', 'auth_admin', 'user_management'],
            ServiceRole.FRONTEND: ['read', 'ui_access'],
            ServiceRole.WEBSOCKET: ['read', 'write', 'websocket_access'],
            ServiceRole.ANALYTICS: ['read', 'analytics_access', 'metrics_write']
        }
        
        return permission_map.get(service_role, ['read'])