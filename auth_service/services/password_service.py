"""
Password Service - Single Source of Truth for Password Management

This service provides a unified interface for password operations,
following SSOT principles and maintaining service independence.

Business Value: Enables secure password management with proper hashing,
validation, and security policies that protect user accounts.
"""

import bcrypt
import logging
import secrets
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, UTC

from auth_service.auth_core.config import AuthConfig
from auth_service.services.redis_service import RedisService

logger = logging.getLogger(__name__)


class PasswordPolicyError(Exception):
    """Raised when password does not meet policy requirements."""
    pass


class PasswordService:
    """
    Single Source of Truth for password management operations.
    
    This service provides a unified interface for password hashing, validation,
    policy enforcement, and reset functionality.
    """
    
    def __init__(self, auth_config: AuthConfig, redis_service: Optional[RedisService] = None):
        """
        Initialize PasswordService with configuration.
        
        Args:
            auth_config: Authentication configuration
            redis_service: Optional Redis service instance for reset tokens
        """
        self.auth_config = auth_config
        self.redis_service = redis_service or RedisService(auth_config)
        self.reset_token_prefix = "password_reset:"
        
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
            
        Raises:
            ValueError: If password is empty or invalid
        """
        try:
            if not password:
                raise ValueError("Password cannot be empty")
            
            # Validate password meets policy
            self.validate_password_policy(password)
            
            # Hash password with bcrypt
            password_hash = bcrypt.hashpw(
                password.encode('utf-8'), 
                bcrypt.gensalt(rounds=self.auth_config.get_bcrypt_rounds())
            ).decode('utf-8')
            
            logger.debug("Password hashed successfully")
            return password_hash
            
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            raise
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password to verify
            password_hash: Stored password hash
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            if not password or not password_hash:
                return False
            
            return bcrypt.checkpw(
                password.encode('utf-8'), 
                password_hash.encode('utf-8')
            )
            
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    def validate_password_policy(self, password: str) -> bool:
        """
        Validate password against security policy.
        
        Args:
            password: Password to validate
            
        Returns:
            True if password meets policy
            
        Raises:
            PasswordPolicyError: If password doesn't meet policy requirements
        """
        try:
            if not password:
                raise PasswordPolicyError("Password cannot be empty")
            
            # Minimum length check
            min_length = self.auth_config.get_password_min_length()
            if len(password) < min_length:
                raise PasswordPolicyError(f"Password must be at least {min_length} characters long")
            
            # Maximum length check (prevent DoS)
            max_length = 128
            if len(password) > max_length:
                raise PasswordPolicyError(f"Password must not exceed {max_length} characters")
            
            # Character requirements
            has_upper = bool(re.search(r'[A-Z]', password))
            has_lower = bool(re.search(r'[a-z]', password))
            has_digit = bool(re.search(r'\d', password))
            has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
            
            requirements_met = sum([has_upper, has_lower, has_digit, has_special])
            
            # Require at least 3 out of 4 character types for flexibility
            if requirements_met < 3:
                raise PasswordPolicyError(
                    "Password must contain at least 3 of the following: "
                    "uppercase letters, lowercase letters, numbers, special characters"
                )
            
            # Check for common weak patterns
            weak_patterns = [
                r'(.)\1{2,}',  # 3+ repeated characters
                r'123|abc|qwe|password|admin|user',  # Common sequences/words
                r'^(.{1,2})\1+$'  # Short repeated patterns
            ]
            
            for pattern in weak_patterns:
                if re.search(pattern, password.lower()):
                    raise PasswordPolicyError("Password contains weak patterns and is not secure")
            
            return True
            
        except PasswordPolicyError:
            raise
        except Exception as e:
            logger.error(f"Password policy validation failed: {e}")
            raise PasswordPolicyError("Password validation failed")
    
    def generate_secure_password(self, length: int = 16) -> str:
        """
        Generate a secure random password.
        
        Args:
            length: Desired password length (default 16)
            
        Returns:
            Secure randomly generated password
        """
        try:
            if length < 8:
                length = 8
            if length > 128:
                length = 128
                
            # Character sets
            lowercase = 'abcdefghijklmnopqrstuvwxyz'
            uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            digits = '0123456789'
            special = '!@#$%^&*(),.?":{}|<>'
            
            # Ensure at least one character from each set
            password_chars = [
                secrets.choice(lowercase),
                secrets.choice(uppercase),
                secrets.choice(digits),
                secrets.choice(special)
            ]
            
            # Fill remaining length with random characters from all sets
            all_chars = lowercase + uppercase + digits + special
            for _ in range(length - 4):
                password_chars.append(secrets.choice(all_chars))
            
            # Shuffle the characters
            secrets.SystemRandom().shuffle(password_chars)
            
            password = ''.join(password_chars)
            
            # Validate the generated password
            self.validate_password_policy(password)
            
            return password
            
        except Exception as e:
            logger.error(f"Secure password generation failed: {e}")
            raise
    
    async def create_reset_token(self, user_id: str, expires_in: int = 3600) -> str:
        """
        Create a password reset token.
        
        Args:
            user_id: User ID for the reset token
            expires_in: Token expiration time in seconds (default 1 hour)
            
        Returns:
            Reset token string
        """
        try:
            # Generate secure token
            reset_token = secrets.token_urlsafe(32)
            
            # Store token in Redis with user ID and expiration
            token_data = {
                "user_id": user_id,
                "created_at": datetime.now(UTC).isoformat(),
                "expires_at": (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat()
            }
            
            token_key = f"{self.reset_token_prefix}{reset_token}"
            await self.redis_service.set(
                token_key,
                str(token_data),  # Convert to string for Redis
                ex=expires_in
            )
            
            logger.info(f"Created password reset token for user {user_id}")
            return reset_token
            
        except Exception as e:
            logger.error(f"Failed to create reset token for user {user_id}: {e}")
            raise
    
    async def validate_reset_token(self, reset_token: str) -> Optional[str]:
        """
        Validate a password reset token and return user ID if valid.
        
        Args:
            reset_token: Reset token to validate
            
        Returns:
            User ID if token is valid, None otherwise
        """
        try:
            token_key = f"{self.reset_token_prefix}{reset_token}"
            token_data = await self.redis_service.get(token_key)
            
            if not token_data:
                return None
            
            # Parse token data (simplified - in production would use JSON)
            if "user_id" not in str(token_data):
                return None
                
            # Extract user ID (simplified extraction)
            # In production, would properly parse JSON
            user_id = str(token_data).split("'user_id': '")[1].split("'")[0] if "'user_id': '" in str(token_data) else None
            
            return user_id
            
        except Exception as e:
            logger.error(f"Reset token validation failed: {e}")
            return None
    
    async def consume_reset_token(self, reset_token: str) -> Optional[str]:
        """
        Consume a password reset token (validate and delete).
        
        Args:
            reset_token: Reset token to consume
            
        Returns:
            User ID if token was valid, None otherwise
        """
        try:
            user_id = await self.validate_reset_token(reset_token)
            if not user_id:
                return None
            
            # Delete the token after validation
            token_key = f"{self.reset_token_prefix}{reset_token}"
            await self.redis_service.delete(token_key)
            
            logger.info(f"Consumed password reset token for user {user_id}")
            return user_id
            
        except Exception as e:
            logger.error(f"Failed to consume reset token: {e}")
            return None
    
    def check_password_strength(self, password: str) -> Dict[str, Any]:
        """
        Check password strength and provide feedback.
        
        Args:
            password: Password to analyze
            
        Returns:
            Dictionary with strength analysis
        """
        try:
            strength_score = 0
            feedback = []
            
            # Length check
            if len(password) >= 8:
                strength_score += 2
            elif len(password) >= 6:
                strength_score += 1
                feedback.append("Consider using a longer password (8+ characters)")
            else:
                feedback.append("Password is too short (minimum 6 characters)")
            
            # Character diversity
            has_upper = bool(re.search(r'[A-Z]', password))
            has_lower = bool(re.search(r'[a-z]', password))
            has_digit = bool(re.search(r'\d', password))
            has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
            
            char_types = sum([has_upper, has_lower, has_digit, has_special])
            strength_score += char_types
            
            if not has_upper:
                feedback.append("Add uppercase letters for better security")
            if not has_lower:
                feedback.append("Add lowercase letters for better security")
            if not has_digit:
                feedback.append("Add numbers for better security")
            if not has_special:
                feedback.append("Add special characters for better security")
            
            # Common patterns check
            if re.search(r'(.)\1{2,}', password):
                strength_score -= 1
                feedback.append("Avoid repeated characters")
            
            if re.search(r'123|abc|password|admin', password.lower()):
                strength_score -= 2
                feedback.append("Avoid common patterns and dictionary words")
            
            # Determine strength level
            if strength_score >= 6:
                strength_level = "strong"
            elif strength_score >= 4:
                strength_level = "medium"
            elif strength_score >= 2:
                strength_level = "weak"
            else:
                strength_level = "very_weak"
            
            return {
                "strength_level": strength_level,
                "score": max(0, strength_score),
                "max_score": 8,
                "feedback": feedback,
                "meets_policy": strength_score >= 4
            }
            
        except Exception as e:
            logger.error(f"Password strength check failed: {e}")
            return {
                "strength_level": "unknown",
                "score": 0,
                "max_score": 8,
                "feedback": ["Unable to analyze password"],
                "meets_policy": False
            }


__all__ = ["PasswordService", "PasswordPolicyError"]