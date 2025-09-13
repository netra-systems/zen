"""

Password Reset Test Helpers - E2E Test Infrastructure



BVJ (Business Value Justification):

1. Segment: All customer segments (password reset critical for user retention)

2. Business Goal: Validate password reset functionality prevents user churn

3. Value Impact: Ensures locked-out users can regain access (revenue protection)

4. Revenue Impact: Prevents lost customers due to forgotten passwords



REQUIREMENTS:

- Mock email service for testing

- Password reset flow validation helpers

- 450-line file limit, 25-line function limit

"""

import asyncio

import re

from typing import Dict, List, Optional

from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler

from netra_backend.app.db.database_manager import DatabaseManager

from netra_backend.app.clients.auth_client_core import AuthServiceClient

from shared.isolated_environment import get_env





class MockEmailService:

    """Mock email service for password reset testing."""

    

    def __init__(self):

        self.sent_emails: List[Dict] = []

        self.email_patterns = {}

        self.delivery_status = True

    

    async def send_password_reset_email(self, 

                                      email: str, 

                                      reset_token: str) -> bool:

        """Mock sending password reset email."""

        if not self.delivery_status:

            return False

        

        email_content = self._generate_reset_email_content(email, reset_token)

        self.sent_emails.append({

            "to": email,

            "subject": "Password Reset Request",

            "content": email_content,

            "reset_token": reset_token,

            "timestamp": asyncio.get_event_loop().time()

        })

        return True

    

    def _generate_reset_email_content(self, 

                                    email: str, 

                                    reset_token: str) -> str:

        """Generate password reset email content."""

        return f"""

        Dear User,

        

        You requested a password reset for {email}.

        

        Click the link below to reset your password:

        https://app.netra.com/reset-password?token={reset_token}

        

        This link expires in 1 hour.

        

        Best regards,

        Netra Team

        """

    

    def get_latest_email(self) -> Optional[Dict]:

        """Get the most recently sent email."""

        return self.sent_emails[-1] if self.sent_emails else None

    

    def get_emails_for_address(self, email: str) -> List[Dict]:

        """Get all emails sent to specific address."""

        return [e for e in self.sent_emails if e["to"] == email]

    

    def clear_sent_emails(self) -> None:

        """Clear all sent emails."""

        self.sent_emails.clear()

    

    def set_delivery_failure(self, fail: bool = True) -> None:

        """Simulate email delivery failure."""

        self.delivery_status = not fail





class PasswordResetFlowValidator:

    """Validates password reset flow security and functionality."""

    

    def __init__(self, email_service: MockEmailService):

        self.email_service = email_service

        self.reset_tokens: Dict[str, str] = {}

        self.old_passwords: Dict[str, str] = {}

    

    def extract_reset_token_from_email(self, email_content: str) -> Optional[str]:

        """Extract reset token from email content."""

        token_pattern = r"token=([a-zA-Z0-9_-]+)"

        match = re.search(token_pattern, email_content)

        return match.group(1) if match else None

    

    def validate_email_format(self, email_data: Dict) -> bool:

        """Validate email contains required elements."""

        required_fields = ["to", "subject", "content", "reset_token"]

        return all(field in email_data for field in required_fields)

    

    def validate_email_content(self, email_content: str) -> bool:

        """Validate email content contains required information."""

        required_elements = [

            "password reset",

            "click the link",

            "expires",

            "token="

        ]

        content_lower = email_content.lower()

        return all(element in content_lower for element in required_elements)

    

    def store_user_password(self, user_id: str, password: str) -> None:

        """Store user's current password for validation."""

        self.old_passwords[user_id] = password

    

    def get_stored_password(self, user_id: str) -> Optional[str]:

        """Get user's stored password."""

        return self.old_passwords.get(user_id)





class PasswordResetSecurityTester:

    """Tests password reset security aspects."""

    

    def __init__(self):

        self.token_attempts: Dict[str, int] = {}

        self.expired_tokens: List[str] = []

    

    def validate_token_format(self, token: str) -> bool:

        """Validate reset token format."""

        return (

            len(token) >= 20 and 

            token.isalnum() or 

            all(c in token for c in "-_")

        )

    

    def simulate_token_expiry(self, token: str) -> None:

        """Simulate token expiry for testing."""

        self.expired_tokens.append(token)

    

    def is_token_expired(self, token: str) -> bool:

        """Check if token is expired."""

        return token in self.expired_tokens

    

    def record_token_attempt(self, token: str) -> int:

        """Record token usage attempt."""

        self.token_attempts[token] = self.token_attempts.get(token, 0) + 1

        return self.token_attempts[token]

    

    def validate_single_use_token(self, token: str) -> bool:

        """Validate token can only be used once."""

        return self.token_attempts.get(token, 0) <= 1





class PasswordResetE2ETester:

    """Comprehensive E2E password reset tester."""

    

    def __init__(self):

        self.email_service = MockEmailService()

        self.flow_validator = PasswordResetFlowValidator(self.email_service)

        self.security_tester = PasswordResetSecurityTester()

        self.test_results: Dict = {}

    

    async def setup_test_environment(self) -> None:

        """Setup test environment for password reset flow."""

        self.email_service.clear_sent_emails()

        self.test_results.clear()

    

    async def test_cleanup_test_environment(self) -> None:

        """Cleanup test environment."""

        self.email_service.clear_sent_emails()

        self.flow_validator.reset_tokens.clear()

        self.flow_validator.old_passwords.clear()

        self.security_tester.token_attempts.clear()

        self.security_tester.expired_tokens.clear()

    

    def get_email_service(self) -> MockEmailService:

        """Get mock email service instance."""

        return self.email_service

    

    def get_flow_validator(self) -> PasswordResetFlowValidator:

        """Get flow validator instance."""

        return self.flow_validator

    

    def get_security_tester(self) -> PasswordResetSecurityTester:

        """Get security tester instance."""

        return self.security_tester

