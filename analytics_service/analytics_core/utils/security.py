"""Analytics Service Security Utilities

Business Value Justification (BVJ):
- Segment: Enterprise (security and compliance)
- Business Goal: Data Protection and Regulatory Compliance
- Value Impact: Ensures secure handling of analytics data and meets enterprise security requirements
- Strategic Impact: Enables enterprise customer adoption and prevents security breaches

Provides comprehensive security utilities for:
- API key validation and management
- IP address hashing for privacy
- Data encryption helpers for sensitive information
- CORS configuration for secure cross-origin requests
"""

import hashlib
import hmac
import ipaddress
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from .logging_config import get_logger

logger = get_logger(__name__)


class SecurityError(Exception):
    """Custom exception for security-related errors."""
    pass


@dataclass
class APIKeyValidationResult:
    """Result of API key validation."""
    is_valid: bool
    key_id: Optional[str] = None
    permissions: Optional[Set[str]] = None
    rate_limit: Optional[int] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None


class APIKeyManager:
    """Manages API key validation and permissions."""
    
    # Default permissions for different key types
    PERMISSION_LEVELS = {
        'read_only': {'read_events', 'read_analytics'},
        'read_write': {'read_events', 'read_analytics', 'write_events'},
        'admin': {'read_events', 'read_analytics', 'write_events', 'delete_data', 'manage_keys'}
    }
    
    def __init__(self):
        self._valid_keys: Dict[str, Dict] = {}
        self._load_api_keys()
    
    def _load_api_keys(self) -> None:
        """Load valid API keys from environment or configuration."""
        # In production, this would load from a secure key store
        # For now, support environment-based configuration
        
        # Load master API key from environment
        master_key = os.getenv('ANALYTICS_MASTER_API_KEY')
        if master_key:
            self._valid_keys[master_key] = {
                'key_id': 'master',
                'permissions': self.PERMISSION_LEVELS['admin'],
                'rate_limit': 10000,  # High rate limit for master key
                'created_at': datetime.now(timezone.utc),
                'expires_at': None,  # No expiration for master key
            }
        
        # Load additional keys from environment (format: KEY_ID:API_KEY:PERMISSIONS:RATE_LIMIT)
        additional_keys = os.getenv('ANALYTICS_API_KEYS', '').strip()
        if additional_keys:
            for key_config in additional_keys.split(','):
                parts = key_config.strip().split(':')
                if len(parts) >= 3:
                    key_id, api_key, permissions = parts[0], parts[1], parts[2]
                    rate_limit = int(parts[3]) if len(parts) > 3 else 1000
                    
                    permission_set = self.PERMISSION_LEVELS.get(permissions, set())
                    if permissions == 'custom' and len(parts) > 4:
                        permission_set = set(parts[4].split(';'))
                    
                    self._valid_keys[api_key] = {
                        'key_id': key_id,
                        'permissions': permission_set,
                        'rate_limit': rate_limit,
                        'created_at': datetime.now(timezone.utc),
                        'expires_at': None,
                    }
    
    def validate_api_key(self, api_key: str) -> APIKeyValidationResult:
        """Validate an API key and return its properties."""
        if not api_key or not isinstance(api_key, str):
            return APIKeyValidationResult(
                is_valid=False,
                error_message="API key is required"
            )
        
        # Remove common prefixes
        clean_key = api_key.replace('Bearer ', '').replace('ApiKey ', '').strip()
        
        if clean_key in self._valid_keys:
            key_info = self._valid_keys[clean_key]
            
            # Check if key has expired
            if key_info.get('expires_at') and key_info['expires_at'] < datetime.now(timezone.utc):
                logger.warning("Expired API key used", key_id=key_info.get('key_id'))
                return APIKeyValidationResult(
                    is_valid=False,
                    error_message="API key has expired"
                )
            
            logger.debug("API key validated successfully", key_id=key_info.get('key_id'))
            return APIKeyValidationResult(
                is_valid=True,
                key_id=key_info.get('key_id'),
                permissions=key_info.get('permissions', set()),
                rate_limit=key_info.get('rate_limit', 1000),
                expires_at=key_info.get('expires_at')
            )
        
        logger.warning("Invalid API key attempted", key_prefix=clean_key[:8] if len(clean_key) >= 8 else "short")
        return APIKeyValidationResult(
            is_valid=False,
            error_message="Invalid API key"
        )
    
    def has_permission(self, api_key: str, required_permission: str) -> bool:
        """Check if an API key has a specific permission."""
        validation_result = self.validate_api_key(api_key)
        if not validation_result.is_valid:
            return False
        
        return required_permission in (validation_result.permissions or set())
    
    @staticmethod
    def generate_api_key(key_id: str, length: int = 32) -> str:
        """Generate a secure API key."""
        # Generate random bytes
        random_bytes = secrets.token_bytes(length)
        
        # Create a hash with key_id for uniqueness
        hasher = hashlib.sha256()
        hasher.update(key_id.encode())
        hasher.update(random_bytes)
        
        # Return base64 encoded key
        return base64.b64encode(hasher.digest()).decode('ascii')[:length]


class IPHasher:
    """Handles IP address hashing for privacy compliance."""
    
    def __init__(self):
        # Get salt from environment or generate a consistent one
        self._salt = os.getenv('ANALYTICS_IP_SALT', 'default_analytics_salt').encode()
    
    def hash_ip(self, ip_address: str) -> str:
        """Hash an IP address for privacy while maintaining uniqueness."""
        if not ip_address:
            return "unknown"
        
        try:
            # Validate IP address format
            ip_obj = ipaddress.ip_address(ip_address)
            
            # For IPv4, mask last octet for additional privacy
            if isinstance(ip_obj, ipaddress.IPv4Address):
                # Convert to network address with /24 mask for additional anonymization
                network = ipaddress.IPv4Network(f"{ip_address}/24", strict=False)
                masked_ip = str(network.network_address)
            else:
                # For IPv6, use full address but still hash
                masked_ip = ip_address
            
            # Create hash with salt
            hasher = hashlib.sha256()
            hasher.update(self._salt)
            hasher.update(masked_ip.encode())
            
            # Return truncated hash for storage efficiency
            return f"ip_{hasher.hexdigest()[:16]}"
            
        except ValueError:
            # Invalid IP address format
            logger.warning("Invalid IP address format", ip_address=ip_address[:10])
            return "invalid_ip"
    
    def hash_user_agent(self, user_agent: str) -> str:
        """Hash user agent string while preserving some utility."""
        if not user_agent:
            return "unknown"
        
        # Extract general browser/OS info without version details for analytics utility
        ua_lower = user_agent.lower()
        browser = "other"
        os_info = "other"
        
        # Simple browser detection
        if "chrome" in ua_lower:
            browser = "chrome"
        elif "firefox" in ua_lower:
            browser = "firefox"
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            browser = "safari"
        elif "edge" in ua_lower:
            browser = "edge"
        
        # Simple OS detection  
        if "windows" in ua_lower:
            os_info = "windows"
        elif "mac" in ua_lower:
            os_info = "mac"
        elif "linux" in ua_lower:
            os_info = "linux"
        elif "android" in ua_lower:
            os_info = "android"
        elif "ios" in ua_lower:
            os_info = "ios"
        
        # Create hash of full user agent
        hasher = hashlib.sha256()
        hasher.update(self._salt)
        hasher.update(user_agent.encode())
        ua_hash = hasher.hexdigest()[:12]
        
        # Return combination of general info and hash
        return f"{browser}_{os_info}_{ua_hash}"


class DataEncryption:
    """Handles encryption of sensitive data."""
    
    def __init__(self):
        self._encryption_key = self._get_encryption_key()
        self._fernet = Fernet(self._encryption_key)
    
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key."""
        # Try to get key from environment
        env_key = os.getenv('ANALYTICS_ENCRYPTION_KEY')
        if env_key:
            try:
                return base64.urlsafe_b64decode(env_key)
            except Exception:
                logger.warning("Invalid encryption key in environment, generating new one")
        
        # Generate key from password and salt (for development)
        password = os.getenv('ANALYTICS_ENCRYPTION_PASSWORD', 'development_password').encode()
        salt = os.getenv('ANALYTICS_ENCRYPTION_SALT', 'development_salt').encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        return base64.urlsafe_b64encode(kdf.derive(password))
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data."""
        if not isinstance(data, str):
            data = str(data)
        
        try:
            encrypted = self._fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error("Encryption failed", error=str(e))
            raise SecurityError(f"Failed to encrypt data: {e}")
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self._fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error("Decryption failed", error=str(e))
            raise SecurityError(f"Failed to decrypt data: {e}")
    
    def encrypt_dict_fields(self, data: Dict, fields_to_encrypt: Set[str]) -> Dict:
        """Encrypt specific fields in a dictionary."""
        encrypted_data = data.copy()
        
        for field in fields_to_encrypt:
            if field in encrypted_data and encrypted_data[field] is not None:
                try:
                    encrypted_data[field] = self.encrypt(str(encrypted_data[field]))
                    encrypted_data[f"{field}_encrypted"] = True
                except Exception as e:
                    logger.error("Field encryption failed", field=field, error=str(e))
                    # Remove the field if encryption fails for security
                    encrypted_data.pop(field, None)
        
        return encrypted_data


class CORSManager:
    """Manages CORS configuration for secure cross-origin requests."""
    
    def __init__(self):
        self._allowed_origins = self._load_allowed_origins()
        self._allowed_methods = {'GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'}
        self._allowed_headers = {
            'Authorization', 'Content-Type', 'X-API-Key', 
            'X-Request-ID', 'Accept', 'Origin'
        }
        self._max_age = 86400  # 24 hours
    
    def _load_allowed_origins(self) -> Set[str]:
        """Load allowed origins from environment."""
        # Default allowed origins
        origins = set()
        
        # Add environment-specified origins
        env_origins = os.getenv('ANALYTICS_CORS_ORIGINS', '').strip()
        if env_origins:
            origins.update(origin.strip() for origin in env_origins.split(','))
        
        # Add common development origins if in development
        if os.getenv('ANALYTICS_ENV', 'development').lower() == 'development':
            origins.update([
                'http://localhost:3000',
                'http://localhost:8000', 
                'http://localhost:8080',
                'http://127.0.0.1:3000',
                'http://127.0.0.1:8000',
                'http://127.0.0.1:8080'
            ])
        
        return origins
    
    def is_origin_allowed(self, origin: str) -> bool:
        """Check if an origin is allowed for CORS requests."""
        if not origin:
            return False
        
        # Check exact match first
        if origin in self._allowed_origins:
            return True
        
        # Check wildcard patterns
        for allowed in self._allowed_origins:
            if allowed == '*':
                return True
            if allowed.endswith('*') and origin.startswith(allowed[:-1]):
                return True
        
        return False
    
    def get_cors_headers(self, origin: Optional[str] = None, 
                        method: Optional[str] = None) -> Dict[str, str]:
        """Get appropriate CORS headers for a request."""
        headers = {}
        
        # Handle origin
        if origin and self.is_origin_allowed(origin):
            headers['Access-Control-Allow-Origin'] = origin
        elif '*' in self._allowed_origins:
            headers['Access-Control-Allow-Origin'] = '*'
        
        # Handle preflight requests
        if method == 'OPTIONS':
            headers.update({
                'Access-Control-Allow-Methods': ', '.join(self._allowed_methods),
                'Access-Control-Allow-Headers': ', '.join(self._allowed_headers),
                'Access-Control-Max-Age': str(self._max_age)
            })
        
        # Always include credentials header if not wildcard
        if headers.get('Access-Control-Allow-Origin') != '*':
            headers['Access-Control-Allow-Credentials'] = 'true'
        
        return headers


class SecurityAuditLogger:
    """Logs security events for audit purposes."""
    
    @staticmethod
    def log_api_key_usage(key_id: str, endpoint: str, ip_address: str, 
                         success: bool = True, error: str = None):
        """Log API key usage for audit."""
        ip_hasher = IPHasher()
        hashed_ip = ip_hasher.hash_ip(ip_address)
        
        logger.info(
            "api_key_usage",
            key_id=key_id,
            endpoint=endpoint,
            ip_hash=hashed_ip,
            success=success,
            error=error,
            event_type="security_audit"
        )
    
    @staticmethod
    def log_security_event(event_type: str, details: Dict, ip_address: str = None):
        """Log general security events."""
        log_data = {
            "security_event": event_type,
            "details": details,
            "event_type": "security_audit"
        }
        
        if ip_address:
            ip_hasher = IPHasher()
            log_data["ip_hash"] = ip_hasher.hash_ip(ip_address)
        
        logger.warning("security_event", **log_data)


# Global instances for convenience
api_key_manager = APIKeyManager()
ip_hasher = IPHasher()
data_encryption = DataEncryption()
cors_manager = CORSManager()


# Convenience functions
def validate_api_key(api_key: str) -> APIKeyValidationResult:
    """Convenience function for API key validation."""
    return api_key_manager.validate_api_key(api_key)


def hash_ip_address(ip_address: str) -> str:
    """Convenience function for IP address hashing."""
    return ip_hasher.hash_ip(ip_address)


def encrypt_sensitive_data(data: str) -> str:
    """Convenience function for data encryption."""
    return data_encryption.encrypt(data)


def get_cors_headers(origin: str = None, method: str = None) -> Dict[str, str]:
    """Convenience function for CORS headers."""
    return cors_manager.get_cors_headers(origin, method)


# Export main interfaces
__all__ = [
    'SecurityError',
    'APIKeyValidationResult',
    'APIKeyManager',
    'IPHasher', 
    'DataEncryption',
    'CORSManager',
    'SecurityAuditLogger',
    'api_key_manager',
    'ip_hasher',
    'data_encryption',
    'cors_manager',
    'validate_api_key',
    'hash_ip_address',
    'encrypt_sensitive_data',
    'get_cors_headers'
]