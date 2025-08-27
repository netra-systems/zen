"""
Token validation functionality for auth service.
Minimal implementation to support test collection.
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from auth_service.auth_core.models.auth_models import User


class TokenValidator:
    """Token validator for JWT token operations."""
    
    def __init__(self):
        """Initialize token validator."""
        self.secret_key = "test-secret-key"
        self.algorithm = "HS256"
    
    def initialize(self):
        """Initialize the token validator."""
        pass
    
    def create_token(self, user_data: Dict[str, Any]) -> str:
        """Create a JWT token with the given user data."""
        payload = user_data.copy()
        if isinstance(payload.get('exp'), datetime):
            # Convert naive datetime to UTC timestamp
            exp_dt = payload['exp']
            if exp_dt.tzinfo is None:
                # If naive datetime, assume it's UTC
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            payload['exp'] = exp_dt.timestamp()
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a JWT token and return its payload."""
        # JWT decode will automatically check expiration and raise ExpiredSignatureError
        # when verify_exp=True (which is the default)
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm], verify_exp=True)