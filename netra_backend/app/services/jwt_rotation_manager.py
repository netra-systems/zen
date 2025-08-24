"""
JWT Key Rotation Manager

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Security & Compliance
- Value Impact: Ensures secure JWT token validation during key rotations
- Strategic Impact: Prevents authentication failures during security updates

Implements JWT key rotation with graceful key transition and race condition prevention.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
import uuid

from netra_backend.app.logging_config import central_logger
from netra_backend.app.config import get_config

logger = central_logger.get_logger(__name__)


@dataclass
class JWTKey:
    """JWT key with metadata."""
    key_id: str
    private_key: bytes
    public_key: bytes
    algorithm: str = "RS256"
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


@dataclass
class RotationConfig:
    """Configuration for JWT key rotation."""
    rotation_interval_hours: int = 24 * 7  # 1 week
    overlap_hours: int = 24  # 1 day overlap for graceful transition
    key_size_bits: int = 2048
    max_keys_stored: int = 5
    pregenerate_keys: bool = True
    validation_grace_period_minutes: int = 5


class JWTRotationManager:
    """Manages JWT key rotation with graceful transitions."""
    
    def __init__(self, config: Optional[RotationConfig] = None):
        """Initialize JWT rotation manager."""
        self.config = config or RotationConfig()
        self.keys: Dict[str, JWTKey] = {}
        self.current_signing_key_id: Optional[str] = None
        self.next_key_id: Optional[str] = None
        
        # Rotation task
        self._rotation_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Synchronization
        self._rotation_lock = asyncio.Lock()
        
        # Statistics
        self.stats = {
            'rotations_completed': 0,
            'keys_generated': 0,
            'validation_successes': 0,
            'validation_failures': 0,
            'race_conditions_prevented': 0
        }
    
    async def start(self) -> None:
        """Start JWT rotation manager."""
        # Generate initial key if none exists
        if not self.keys:
            await self._generate_initial_key()
        
        # Pre-generate next key if configured
        if self.config.pregenerate_keys and not self.next_key_id:
            await self._pregenerate_next_key()
        
        # Start rotation task
        if self._rotation_task is None:
            self._rotation_task = asyncio.create_task(self._rotation_loop())
        
        logger.info("JWT rotation manager started")
    
    async def stop(self) -> None:
        """Stop JWT rotation manager."""
        self._shutdown = True
        
        if self._rotation_task:
            self._rotation_task.cancel()
            try:
                await self._rotation_task
            except asyncio.CancelledError:
                pass
        
        logger.info("JWT rotation manager stopped")
    
    async def get_signing_key(self) -> Tuple[str, bytes]:
        """
        Get current signing key.
        
        Returns:
            Tuple of (key_id, private_key)
        """
        if not self.current_signing_key_id:
            await self._generate_initial_key()
        
        key = self.keys[self.current_signing_key_id]
        return key.key_id, key.private_key
    
    async def get_validation_keys(self) -> Dict[str, bytes]:
        """
        Get all public keys for token validation.
        
        Returns:
            Dict of key_id -> public_key
        """
        current_time = datetime.now(timezone.utc)
        validation_keys = {}
        
        for key_id, key in self.keys.items():
            # Include active keys and keys within grace period
            if key.is_active:
                validation_keys[key_id] = key.public_key
            elif key.expires_at and current_time < key.expires_at + timedelta(minutes=self.config.validation_grace_period_minutes):
                validation_keys[key_id] = key.public_key
        
        return validation_keys
    
    async def validate_token(self, token: str, verify_exp: bool = True) -> Optional[Dict[str, Any]]:
        """
        Validate JWT token with current keys.
        
        Args:
            token: JWT token to validate
            verify_exp: Whether to verify expiration
            
        Returns:
            Decoded token payload if valid, None if invalid
        """
        validation_keys = await self.get_validation_keys()
        
        # Try each validation key
        for key_id, public_key in validation_keys.items():
            try:
                # Decode and verify token
                payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=["RS256"],
                    options={"verify_exp": verify_exp}
                )
                
                self.stats['validation_successes'] += 1
                return payload
                
            except jwt.ExpiredSignatureError:
                logger.debug(f"Token expired for key {key_id}")
                continue
            except jwt.InvalidTokenError:
                logger.debug(f"Token invalid for key {key_id}")
                continue
            except Exception as e:
                logger.warning(f"Token validation error for key {key_id}: {e}")
                continue
        
        self.stats['validation_failures'] += 1
        return None
    
    async def create_token(self, payload: Dict[str, Any], expires_in_seconds: int = 3600) -> str:
        """
        Create JWT token with current signing key.
        
        Args:
            payload: Token payload
            expires_in_seconds: Token expiration time
            
        Returns:
            Encoded JWT token
        """
        key_id, private_key = await self.get_signing_key()
        
        # Add standard claims
        now = datetime.now(timezone.utc)
        payload.update({
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
            'kid': key_id
        })
        
        # Create token
        token = jwt.encode(payload, private_key, algorithm="RS256", headers={'kid': key_id})
        return token
    
    async def rotate_keys(self) -> bool:
        """
        Perform key rotation.
        
        Returns:
            True if rotation was successful
        """
        async with self._rotation_lock:
            try:
                logger.info("Starting JWT key rotation")
                
                # Generate new key if not pre-generated
                if not self.next_key_id:
                    await self._generate_next_key()
                
                # Perform the rotation
                old_key_id = self.current_signing_key_id
                self.current_signing_key_id = self.next_key_id
                self.next_key_id = None
                
                # Mark old key as inactive (but keep for validation)
                if old_key_id and old_key_id in self.keys:
                    old_key = self.keys[old_key_id]
                    old_key.is_active = False
                    old_key.expires_at = datetime.now(timezone.utc) + timedelta(hours=self.config.overlap_hours)
                
                # Pre-generate next key if configured
                if self.config.pregenerate_keys:
                    await self._pregenerate_next_key()
                
                # Clean up old keys
                await self._cleanup_old_keys()
                
                self.stats['rotations_completed'] += 1
                logger.info(f"JWT key rotation completed: {old_key_id} -> {self.current_signing_key_id}")
                return True
                
            except Exception as e:
                logger.error(f"JWT key rotation failed: {e}")
                return False
    
    async def _rotation_loop(self) -> None:
        """Main rotation loop."""
        while not self._shutdown:
            try:
                # Calculate next rotation time
                next_rotation = self._calculate_next_rotation_time()
                wait_seconds = (next_rotation - datetime.now(timezone.utc)).total_seconds()
                
                if wait_seconds > 0:
                    await asyncio.sleep(min(wait_seconds, 3600))  # Check hourly at minimum
                    
                if not self._shutdown and datetime.now(timezone.utc) >= next_rotation:
                    await self.rotate_keys()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in JWT rotation loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    def _calculate_next_rotation_time(self) -> datetime:
        """Calculate next key rotation time."""
        if not self.current_signing_key_id:
            return datetime.now(timezone.utc)
        
        current_key = self.keys[self.current_signing_key_id]
        return current_key.created_at + timedelta(hours=self.config.rotation_interval_hours)
    
    async def _generate_initial_key(self) -> None:
        """Generate initial signing key."""
        key = await self._generate_key()
        self.keys[key.key_id] = key
        self.current_signing_key_id = key.key_id
        logger.info(f"Generated initial JWT key: {key.key_id}")
    
    async def _generate_next_key(self) -> None:
        """Generate next signing key."""
        key = await self._generate_key()
        self.keys[key.key_id] = key
        self.next_key_id = key.key_id
        logger.info(f"Generated next JWT key: {key.key_id}")
    
    async def _pregenerate_next_key(self) -> None:
        """Pre-generate next key for seamless rotation."""
        if not self.next_key_id:
            await self._generate_next_key()
    
    async def _generate_key(self) -> JWTKey:
        """Generate new RSA key pair."""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.config.key_size_bits
        )
        
        # Serialize private key
        private_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key
        public_key_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Create key object
        key = JWTKey(
            key_id=str(uuid.uuid4()),
            private_key=private_key_bytes,
            public_key=public_key_bytes,
            created_at=datetime.now(timezone.utc)
        )
        
        self.stats['keys_generated'] += 1
        return key
    
    async def _cleanup_old_keys(self) -> None:
        """Clean up old expired keys."""
        current_time = datetime.now(timezone.utc)
        keys_to_remove = []
        
        for key_id, key in self.keys.items():
            # Don't remove current or next keys
            if key_id in [self.current_signing_key_id, self.next_key_id]:
                continue
            
            # Remove keys that are expired beyond grace period
            if (key.expires_at and 
                current_time > key.expires_at + timedelta(minutes=self.config.validation_grace_period_minutes)):
                keys_to_remove.append(key_id)
        
        # Keep only the most recent keys up to max limit
        if len(self.keys) - len(keys_to_remove) > self.config.max_keys_stored:
            # Sort keys by creation time and mark oldest for removal
            sorted_keys = sorted(
                [(k, v) for k, v in self.keys.items() if k not in keys_to_remove and k not in [self.current_signing_key_id, self.next_key_id]],
                key=lambda x: x[1].created_at
            )
            
            excess_count = len(self.keys) - len(keys_to_remove) - self.config.max_keys_stored
            for i in range(excess_count):
                keys_to_remove.append(sorted_keys[i][0])
        
        # Remove old keys
        for key_id in keys_to_remove:
            del self.keys[key_id]
            logger.debug(f"Removed old JWT key: {key_id}")
    
    def get_key_info(self) -> Dict[str, Any]:
        """Get information about current keys."""
        key_info = {}
        
        for key_id, key in self.keys.items():
            key_info[key_id] = {
                'created_at': key.created_at.isoformat(),
                'expires_at': key.expires_at.isoformat() if key.expires_at else None,
                'is_active': key.is_active,
                'algorithm': key.algorithm,
                'is_current': key_id == self.current_signing_key_id,
                'is_next': key_id == self.next_key_id
            }
        
        return {
            'current_signing_key': self.current_signing_key_id,
            'next_key': self.next_key_id,
            'total_keys': len(self.keys),
            'keys': key_info
        }
    
    def get_rotation_stats(self) -> Dict[str, Any]:
        """Get rotation statistics."""
        next_rotation = self._calculate_next_rotation_time()
        
        return {
            'next_rotation_time': next_rotation.isoformat(),
            'seconds_until_rotation': (next_rotation - datetime.now(timezone.utc)).total_seconds(),
            **self.stats
        }
    
    async def force_rotation(self) -> bool:
        """Force immediate key rotation (for testing/emergency)."""
        logger.warning("Forcing JWT key rotation")
        return await self.rotate_keys()
    
    async def export_public_keys_jwks(self) -> Dict[str, Any]:
        """
        Export public keys in JWKS format for external validation.
        
        Returns:
            JWKS-formatted public key set
        """
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import base64
        
        validation_keys = await self.get_validation_keys()
        jwks_keys = []
        
        for key_id, public_key_bytes in validation_keys.items():
            try:
                # Load public key
                public_key = serialization.load_pem_public_key(public_key_bytes)
                
                if isinstance(public_key, rsa.RSAPublicKey):
                    # Get RSA components
                    numbers = public_key.public_numbers()
                    
                    # Convert to JWK format
                    jwk = {
                        "kty": "RSA",
                        "kid": key_id,
                        "use": "sig",
                        "alg": "RS256",
                        "n": base64.urlsafe_b64encode(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, 'big')).decode('utf-8').rstrip('='),
                        "e": base64.urlsafe_b64encode(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, 'big')).decode('utf-8').rstrip('=')
                    }
                    
                    jwks_keys.append(jwk)
                    
            except Exception as e:
                logger.error(f"Failed to convert key {key_id} to JWKS format: {e}")
        
        return {"keys": jwks_keys}


# Global JWT rotation manager instance
_jwt_rotation_manager: Optional[JWTRotationManager] = None


def get_jwt_rotation_manager(config: Optional[RotationConfig] = None) -> JWTRotationManager:
    """Get global JWT rotation manager instance."""
    global _jwt_rotation_manager
    if _jwt_rotation_manager is None:
        _jwt_rotation_manager = JWTRotationManager(config)
    return _jwt_rotation_manager


async def validate_jwt_token(token: str, verify_exp: bool = True) -> Optional[Dict[str, Any]]:
    """Convenience function to validate JWT token."""
    manager = get_jwt_rotation_manager()
    return await manager.validate_token(token, verify_exp)


async def create_jwt_token(payload: Dict[str, Any], expires_in_seconds: int = 3600) -> str:
    """Convenience function to create JWT token."""
    manager = get_jwt_rotation_manager()
    return await manager.create_token(payload, expires_in_seconds)