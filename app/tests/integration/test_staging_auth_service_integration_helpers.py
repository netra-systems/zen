"""Utilities Tests - Split from test_staging_auth_service_integration.py

    BVJ: Secures 100% of $7K MRR by validating authentication that gates paid features.
    Priority: P0 - Authentication failures block all revenue-generating features.
"""

import asyncio
import pytest
import time
import httpx
import jwt
import os
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
import json
import hashlib

    def __init__(self):
        """Initialize auth integration validator."""
        self.is_staging = os.getenv("ENVIRONMENT", "local") == "staging"
        
        # Service URLs - must match deployment names exactly
        if self.is_staging:
            self.backend_url = os.getenv("BACKEND_URL", "https://netra-backend-staging-xyz.run.app")
            self.auth_url = os.getenv("AUTH_SERVICE_URL", "https://netra-auth-service-xyz.run.app")
            self.frontend_url = os.getenv("FRONTEND_URL", "https://netra-frontend-staging-xyz.run.app")
        else:
            self.backend_url = "http://localhost:8000"
            self.auth_url = "http://localhost:8080"  # Auth on 8080, not 8001
            self.frontend_url = "http://localhost:3000"
        
        # JWT configuration - CRITICAL: Must be consistent across services
        self.jwt_secret = os.getenv("JWT_SECRET", "test-secret-key-for-local-development")
        self.jwt_algorithm = "HS256"
        
        # Test user credentials
        self.test_user = {
            "email": f"staging_test_{int(time.time())}@netra.ai",
            "password": "StrongTestPassword123!",
            "tier": "early"  # Test with paid tier
        }

    def create_test_jwt(self, user_id: str, email: str, tier: str = "free") -> str:
        """
        Create a test JWT token matching production format.
        
        Critical: Token format must match exactly what auth service produces.
        """
        now = datetime.utcnow()
        payload = {
            "sub": user_id,  # Subject (user ID)
            "email": email,
            "tier": tier,
            "iat": now,
            "exp": now + timedelta(hours=24),
            "type": "access",
            "jti": hashlib.sha256(f"{user_id}{now.timestamp()}".encode()).hexdigest()[:16]
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def decode_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate a JWT token."""
        try:
            return jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
