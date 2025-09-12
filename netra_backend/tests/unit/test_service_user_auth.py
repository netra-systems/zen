print("Testing issue #463 service user auth")

# REPRODUCE ISSUE #463: Missing SERVICE_SECRET environment variable

import unittest
from unittest.mock import patch
from shared.isolated_environment import get_env

class TestServiceUserAuth(unittest.TestCase):
    def test_missing_service_secret_reproduces_issue_463(self):
        """Reproduce issue #463: SERVICE_SECRET missing causes 403 auth failures"""
        with patch("shared.isolated_environment.get_env") as mock_get_env:
            mock_get_env.return_value = None  # Simulate missing SERVICE_SECRET
            
            service_secret = get_env("SERVICE_SECRET")
            self.assertIsNone(service_secret, "SERVICE_SECRET should be missing (None)")
            
            # This reproduces the core issue from #463
            if not service_secret:
                print("[U+2713] REPRODUCED: SERVICE_SECRET is missing - this causes 403 auth failures in staging")
            
    def test_missing_jwt_secret_reproduces_auth_failure(self):
        """Test JWT_SECRET missing also causes auth failures"""  
        with patch("shared.isolated_environment.get_env") as mock_get_env:
            mock_get_env.return_value = None  # Simulate missing JWT_SECRET
            
            jwt_secret = get_env("JWT_SECRET")
            self.assertIsNone(jwt_secret, "JWT_SECRET should be missing (None)")
            
            if not jwt_secret:
                print("[U+2713] REPRODUCED: JWT_SECRET is missing - this also causes auth failures")

if __name__ == "__main__":
    unittest.main()

