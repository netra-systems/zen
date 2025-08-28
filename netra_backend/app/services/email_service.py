"""
Email Service for User Verification and Notifications

Business Value Justification (BVJ):
- Segment: Free, Early, Mid, Enterprise
- Business Goal: User activation and retention (30% drop-off prevention)
- Value Impact: Email verification enables user onboarding completion
- Revenue Impact: Prevents $15K+ MRR loss from incomplete signups

This service handles email verification tokens and user notification emails.
"""
import asyncio
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone

from netra_backend.app.core.unified_logging import get_logger

logger = get_logger(__name__)


class EmailService:
    """
    Handles email verification and notification sending.
    
    In production, this would integrate with email providers like SendGrid, SES, etc.
    For now, it provides a basic interface for testing email flows.
    """
    
    def __init__(self):
        self.verification_tokens: Dict[str, Dict[str, Any]] = {}
        self.sent_emails: Dict[str, Dict[str, Any]] = {}
    
    async def send_verification(self, email: str, verification_token: str) -> bool:
        """
        Send verification email to user.
        
        Args:
            email: User's email address
            verification_token: Token for email verification
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            # Store verification token with expiration
            expiration = datetime.now(timezone.utc) + timedelta(hours=24)
            self.verification_tokens[verification_token] = {
                "email": email,
                "created_at": datetime.now(timezone.utc),
                "expires_at": expiration,
                "used": False
            }
            
            # Log the verification email (in production, would send via email provider)
            logger.info(f"Verification email sent to {email} with token {verification_token}")
            
            # Store sent email record
            self.sent_emails[email] = {
                "type": "verification",
                "token": verification_token,
                "sent_at": datetime.now(timezone.utc)
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {str(e)}")
            return False
    
    async def verify_token(self, verification_token: str) -> bool:
        """
        Verify an email verification token.
        
        Args:
            verification_token: Token to verify
            
        Returns:
            bool: True if token is valid and not expired
        """
        try:
            if verification_token not in self.verification_tokens:
                logger.warning(f"Verification token not found: {verification_token}")
                return False
            
            token_data = self.verification_tokens[verification_token]
            
            # Check if token is already used
            if token_data["used"]:
                logger.warning(f"Verification token already used: {verification_token}")
                return False
            
            # Check if token is expired
            if datetime.now(timezone.utc) > token_data["expires_at"]:
                logger.warning(f"Verification token expired: {verification_token}")
                return False
            
            # Mark token as used
            token_data["used"] = True
            token_data["verified_at"] = datetime.now(timezone.utc)
            
            logger.info(f"Email verification successful for token: {verification_token}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying token {verification_token}: {str(e)}")
            return False
    
    async def send_welcome_email(self, email: str, user_name: str) -> bool:
        """
        Send welcome email to newly verified user.
        
        Args:
            email: User's email address
            user_name: User's display name
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            logger.info(f"Welcome email sent to {email} for user {user_name}")
            
            # Store sent email record
            self.sent_emails[email] = {
                "type": "welcome",
                "user_name": user_name,
                "sent_at": datetime.now(timezone.utc)
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {str(e)}")
            return False
    
    def get_verification_status(self, verification_token: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a verification token.
        
        Args:
            verification_token: Token to check
            
        Returns:
            Dict with token status or None if not found
        """
        return self.verification_tokens.get(verification_token)
    
    def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired verification tokens.
        
        Returns:
            int: Number of tokens cleaned up
        """
        now = datetime.now(timezone.utc)
        expired_tokens = [
            token for token, data in self.verification_tokens.items()
            if data["expires_at"] < now
        ]
        
        for token in expired_tokens:
            del self.verification_tokens[token]
        
        logger.info(f"Cleaned up {len(expired_tokens)} expired verification tokens")
        return len(expired_tokens)