"""Test JWT token generation with correct secret."""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_framework.jwt_test_utils import JWTTestHelper

# Use the same secret as the test middleware
test_secret = "test-secret"

# Create JWT helper with the test secret
jwt_helper = JWTTestHelper(secret=test_secret)

# Generate tokens
frontend_token = jwt_helper.create_user_token(
    user_id="frontend-user",
    email="frontend@netra.com",
    permissions=["read", "write"]
)

service_token = jwt_helper.create_service_token(
    service_name="netra-frontend"
)

valid_test_token = jwt_helper.create_user_token(
    user_id="test-user",
    email="test@example.com"
)

print("Tokens generated with 'test-secret':")
print(f"Frontend token: {frontend_token}")
print(f"Service token: {service_token}")
print(f"Valid test token: {valid_test_token}")

# Verify they can be decoded
try:
    decoded = jwt_helper.decode_token(service_token)
    print(f"\nService token decoded successfully: {decoded}")
except Exception as e:
    print(f"Error decoding service token: {e}")