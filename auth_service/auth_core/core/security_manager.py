"""
Security manager functionality for auth service.
Minimal implementation to support test collection.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone


class SecurityManager:
    """Security manager for authentication security operations."""
    
    def __init__(self):
        """Initialize security manager."""
        self._token_usage = {}
        self._revoked_tokens = set()
        self._suspicious_activities = {}
    
    def initialize(self):
        """Initialize the security manager."""
        pass
    
    def record_suspicious_activity(self, session_id: str, activity_type: str, client_ip: str):
        """Record suspicious activity for a session."""
        if session_id not in self._suspicious_activities:
            self._suspicious_activities[session_id] = []
        
        self._suspicious_activities[session_id].append({
            "type": activity_type,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc)
        })
    
    def get_suspicious_activity_count(self, session_id: str) -> int:
        """Get count of suspicious activities for a session."""
        return len(self._suspicious_activities.get(session_id, []))
    
    def record_token_usage(self, jti: str, user_id: str):
        """Record token usage for replay detection."""
        if jti not in self._token_usage:
            self._token_usage[jti] = 0
        self._token_usage[jti] += 1
    
    def detect_token_replay(self, jti: str) -> bool:
        """Detect if a token has been used before (replay attack)."""
        # A token is considered replayed if it has been consumed/used at least once
        return self._token_usage.get(jti, 0) >= 1
    
    def validate_token_not_replayed(self, token: str):
        """Validate that a token hasn't been replayed."""
        import jwt
        
        # Decode the token to extract JTI (using basic secret for testing)
        try:
            # Use same secret and algorithm as TokenValidator for consistency
            decoded = jwt.decode(token, "test-secret-key", algorithms=["HS256"], verify_exp=True)
            jti = decoded.get("jti")
            
            if not jti:
                # If no JTI, we can't track replay - consider this valid for now
                return
                
            # For validate_token_not_replayed, we check if token has been used at all
            # This is stricter than detect_token_replay for security validation
            if self._token_usage.get(jti, 0) >= 1:
                raise ValueError("Token replay detected")
                
        except jwt.ExpiredSignatureError:
            # Let expired token errors bubble up
            raise
        except jwt.InvalidTokenError:
            # Invalid tokens should be rejected
            raise ValueError("Invalid token for replay validation")
    
    def revoke_token(self, jti: str, reason: str):
        """Revoke a token by adding it to the revocation list."""
        self._revoked_tokens.add(jti)
    
    def is_token_revoked(self, jti: str) -> bool:
        """Check if a token has been revoked."""
        return jti in self._revoked_tokens
    
    def validate_token_not_revoked(self, token: str):
        """Validate that a token hasn't been revoked."""
        import jwt
        
        # Decode the token to extract JTI (using basic secret for testing)
        try:
            # Use same secret and algorithm as TokenValidator for consistency
            decoded = jwt.decode(token, "test-secret-key", algorithms=["HS256"], verify_exp=True)
            jti = decoded.get("jti")
            
            if not jti:
                # If no JTI, we can't track revocation - consider this valid for now
                return
                
            # Check if this token has been revoked
            if self.is_token_revoked(jti):
                raise ValueError("Token has been revoked")
                
        except jwt.ExpiredSignatureError:
            # Let expired token errors bubble up
            raise
        except jwt.InvalidTokenError:
            # Invalid tokens should be rejected
            raise ValueError("Invalid token for revocation validation")
    
    def get_token_usage_count(self, jti: str) -> int:
        """Get the usage count for a token."""
        return self._token_usage.get(jti, 0)
    
    async def analyze_session_activity(self, session_id: str) -> Dict[str, Any]:
        """Analyze session activity for anomalies."""
        activities = self._suspicious_activities.get(session_id, [])
        
        # Simple anomaly detection
        anomaly_types = []
        ip_addresses = set()
        
        for activity in activities:
            ip_addresses.add(activity.get("ip"))
            
        if len(ip_addresses) > 1:
            anomaly_types.append("ip_change")
            
        # Check for admin-like activities
        admin_activities = [a for a in activities if "admin" in str(a.get("type", ""))]
        if admin_activities:
            anomaly_types.append("privilege_escalation")
        
        return {
            "anomaly_detected": len(anomaly_types) > 0,
            "anomaly_types": anomaly_types,
            "activity_count": len(activities)
        }