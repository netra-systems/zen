"""
Mock classes and utilities for security service tests.
All functions ≤8 lines per requirements.
"""

from datetime import datetime, UTC, timedelta
from typing import Dict, List, Any, Optional
from app.services.security_service import SecurityService
from app.services.key_manager import KeyManager


class MockUser:
    """Mock user model for testing"""
    
    def __init__(self, id: str, email: str, full_name: str = None, hashed_password: str = None):
        self.id = id
        self.email = email
        self.full_name = full_name
        self.hashed_password = hashed_password
        self._init_basic_fields()
        self._init_permission_fields()
        
    def _init_basic_fields(self) -> None:
        """Initialize basic user fields"""
        self.picture = None
        self.is_active = True
        self.is_verified = True
        self.created_at = datetime.now(UTC)
        self.last_login = None
        self._init_security_fields()
    
    def _init_security_fields(self) -> None:
        """Initialize security-related fields"""
        self.failed_login_attempts = 0
        self.account_locked_until = None
    
    def _init_permission_fields(self) -> None:
        """Initialize permission-related fields"""
        self.roles = ['user']  # Default role
        self.permissions = []
        self.groups = []
        self.tool_permissions = {}
        self.feature_flags = {}
    
    def add_role(self, role: str) -> None:
        """Add role to user"""
        if role not in self.roles:
            self.roles.append(role)
    
    def add_permission(self, permission: str) -> None:
        """Add permission to user"""
        if permission not in self.permissions:
            self.permissions.append(permission)
    
    def set_tool_permission(self, tool: str, permission: bool) -> None:
        """Set tool permission for user"""
        self.tool_permissions[tool] = permission
    
    def lock_account(self, duration_minutes: int = 30) -> None:
        """Lock user account for specified duration"""
        self.account_locked_until = datetime.now(UTC) + timedelta(minutes=duration_minutes)
    
    def unlock_account(self) -> None:
        """Unlock user account"""
        self.account_locked_until = None
        self.failed_login_attempts = 0
    
    def is_account_locked(self) -> bool:
        """Check if account is currently locked"""
        if not self.account_locked_until:
            return False
        return datetime.now(UTC) < self.account_locked_until


class EnhancedSecurityService(SecurityService):
    """Enhanced security service with additional features"""
    
    def __init__(self, key_manager: KeyManager):
        super().__init__(key_manager)
        self._init_enhanced_features()
        
    def _init_enhanced_features(self) -> None:
        """Initialize enhanced security features"""
        self.session_cache = {}
        self.failed_attempts_cache = {}
        self.rate_limit_cache = {}
        self.audit_log = []
        self._init_security_policies()
    
    def _init_security_policies(self) -> None:
        """Initialize security policies"""
        self.max_failed_attempts = 5
        self.lockout_duration = 30  # minutes
        self.session_timeout = 24  # hours
        self.password_complexity_enabled = True
    
    async def enhanced_authenticate_user(self, email: str, password: str, **kwargs) -> Dict[str, Any]:
        """Enhanced authentication with additional checks"""
        result = await self.authenticate_user(email, password)
        self._log_authentication_attempt(email, result.get('success', False))
        
        return result
    
    def _log_authentication_attempt(self, email: str, success: bool) -> None:
        """Log authentication attempt"""
        log_entry = {
            'timestamp': datetime.now(UTC),
            'email': email,
            'success': success,
            'ip_address': 'test_ip'
        }
        self.audit_log.append(log_entry)
    
    async def validate_session_with_cache(self, token: str) -> Dict[str, Any]:
        """Validate session with caching"""
        cached_result = self._get_cached_session_if_valid(token)
        if cached_result:
            return cached_result
        
        result = await self.validate_token(token)
        self._cache_session(token, result)
        return result
    
    def _get_cached_session_if_valid(self, token: str) -> Dict[str, Any]:
        """Get cached session if valid, otherwise None"""
        if token in self.session_cache:
            cached_session = self.session_cache[token]
            if self._is_cache_valid(cached_session):
                return cached_session
        return None
    
    def _is_cache_valid(self, cached_session: Dict[str, Any]) -> bool:
        """Check if cached session is still valid"""
        if 'cached_at' not in cached_session:
            return False
        
        cache_age = datetime.now(UTC) - cached_session['cached_at']
        return cache_age.total_seconds() < 300  # 5 minutes cache
    
    def _cache_session(self, token: str, session_data: Dict[str, Any]) -> None:
        """Cache session data"""
        session_data['cached_at'] = datetime.now(UTC)
        self.session_cache[token] = session_data
    
    async def check_rate_limit(self, identifier: str, limit: int = 10, window: int = 60) -> bool:
        """Check if identifier has exceeded rate limit"""
        current_time = datetime.now(UTC)
        
        self._ensure_rate_limit_cache_exists(identifier)
        self._clean_rate_limit_cache(identifier, current_time, window)
        
        # Check current rate
        return len(self.rate_limit_cache[identifier]) < limit
    
    def _ensure_rate_limit_cache_exists(self, identifier: str) -> None:
        """Ensure rate limit cache exists for identifier"""
        if identifier not in self.rate_limit_cache:
            self.rate_limit_cache[identifier] = []
    
    def _clean_rate_limit_cache(self, identifier: str, current_time: datetime, window: int) -> None:
        """Clean old entries from rate limit cache"""
        cutoff_time = current_time - timedelta(seconds=window)
        self.rate_limit_cache[identifier] = [
            timestamp for timestamp in self.rate_limit_cache[identifier]
            if timestamp > cutoff_time
        ]
    
    def record_rate_limit_attempt(self, identifier: str) -> None:
        """Record rate limit attempt"""
        if identifier not in self.rate_limit_cache:
            self.rate_limit_cache[identifier] = []
        
        self.rate_limit_cache[identifier].append(datetime.now(UTC))


def create_test_user(user_id: str = "test_user", email: str = "test@example.com") -> MockUser:
    """Create test user with default values"""
    return MockUser(
        id=user_id,
        email=email,
        full_name="Test User",
        hashed_password="hashed_test_password"
    )


def create_admin_user(user_id: str = "admin_user", email: str = "admin@example.com") -> MockUser:
    """Create admin user with admin role"""
    user = create_test_user(user_id, email)
    user.add_role("admin")
    user.add_permission("admin_access")
    user.add_permission("user_management")
    return user


def create_locked_user(user_id: str = "locked_user", email: str = "locked@example.com") -> MockUser:
    """Create locked user account"""
    user = create_test_user(user_id, email)
    user.lock_account(30)
    user.failed_login_attempts = 5
    return user


def create_oauth_user(user_id: str = "oauth_user", email: str = "oauth@example.com") -> MockUser:
    """Create OAuth user"""
    user = create_test_user(user_id, email)
    user.picture = "https://example.com/avatar.jpg"
    user.add_role("oauth_user")
    return user


def assert_authentication_success(result: Dict[str, Any]) -> None:
    """Assert authentication was successful"""
    assert result.get('success') is True
    assert 'token' in result
    assert 'user' in result


def assert_authentication_failure(result: Dict[str, Any]) -> None:
    """Assert authentication failed"""
    assert result.get('success') is False
    assert 'error' in result


def create_test_token_payload(user_id: str, exp_minutes: int = 60) -> Dict[str, Any]:
    """Create test token payload"""
    return {
        'user_id': user_id,
        'email': f'{user_id}@example.com',
        'exp': datetime.now(UTC) + timedelta(minutes=exp_minutes),
        'iat': datetime.now(UTC),
        'type': 'access'
    }