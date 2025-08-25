"""
Fix Authentication Test Tokens

This script fixes the authentication integration tests by replacing invalid
token strings with properly formatted JWT tokens.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Fix authentication tests to pass with proper JWT tokens
- Value Impact: Enables authentication system validation and reliability
- Strategic Impact: Prevents authentication regressions
"""

import os
import re
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_framework.jwt_test_utils import JWTTestHelper


def fix_authentication_test_file():
    """Fix the authentication integration test file tokens."""
    
    test_file_path = project_root / "netra_backend" / "tests" / "integration" / "backend-authentication-integration-failures.py"
    
    if not test_file_path.exists():
        print(f"Test file not found: {test_file_path}")
        return
    
    # Use a consistent test secret that matches the middleware initialization
    test_secret = "test-secret"
    
    # Create JWT helper with the test secret
    jwt_helper = JWTTestHelper(secret=test_secret)
    
    # Generate proper JWT tokens using the same secret as the middleware
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
    
    print(f"Generated tokens:")
    print(f"Frontend token: {frontend_token[:50]}...")
    print(f"Service token: {service_token[:50]}...")
    print(f"Valid test token: {valid_test_token[:50]}...")
    
    # Read the test file
    with open(test_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Track changes
    changes_made = 0
    
    # Replace invalid tokens with proper JWT tokens
    replacements = [
        # Frontend token
        (
            r'"eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9\.frontend-token-payload\.signature"',
            f'"{frontend_token}"'
        ),
        # Service account token 
        (
            r'"service-account-token"',
            f'"{service_token}"'
        ),
        # Generic test tokens
        (
            r'"test-token"',
            f'"{valid_test_token}"'
        ),
        (
            r'"retry-token"',
            f'"{valid_test_token}"'
        ),
        # Bearer tokens in headers
        (
            r'"Authorization": "Bearer service-account-token"',
            f'"Authorization": "Bearer {service_token}"'
        ),
        (
            r'"Authorization": "Bearer valid-token"',
            f'"Authorization": "Bearer {valid_test_token}"'
        )
    ]
    
    # Apply replacements
    for pattern, replacement in replacements:
        old_content = content
        content = re.sub(pattern, replacement, content)
        if content != old_content:
            changes_made += 1
            print(f"Replaced pattern: {pattern[:50]}...")
    
    # Write the updated content back
    if changes_made > 0:
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[OK] Fixed {changes_made} token replacements in {test_file_path}")
    else:
        print(f"[INFO] No token replacements needed in {test_file_path}")
    
    return changes_made


def validate_jwt_environment():
    """Validate that JWT environment is properly configured."""
    
    print("\nValidating JWT Environment Configuration:")
    
    # Check environment variables
    from netra_backend.app.core.isolated_environment import get_env
    env = get_env()
    
    jwt_secret = env.get("JWT_SECRET_KEY")
    print(f"JWT_SECRET_KEY: {'[OK] Set' if jwt_secret else '[ERROR] Missing'}")
    if jwt_secret:
        print(f"  Length: {len(jwt_secret)} characters ({'[OK] Good' if len(jwt_secret) >= 32 else '[ERROR] Too short'})")
    
    auth_service_url = env.get("AUTH_SERVICE_URL")
    print(f"AUTH_SERVICE_URL: {'[OK] Set' if auth_service_url else '[ERROR] Missing'} ({auth_service_url})")
    
    # Test JWT token generation
    try:
        jwt_helper = JWTTestHelper()
        test_token = jwt_helper.create_user_token()
        is_valid = jwt_helper.validate_token_structure(test_token)
        print(f"JWT Token Generation: {'[OK] Working' if is_valid else '[ERROR] Failed'}")
        
        # Test token decoding
        decoded = jwt_helper.decode_token(test_token)
        print(f"JWT Token Decoding: {'[OK] Working' if decoded else '[ERROR] Failed'}")
        
    except Exception as e:
        print(f"JWT Token Testing: [ERROR] Failed - {e}")


def main():
    """Main function to fix authentication test tokens."""
    
    print("Fixing Authentication Test Tokens")
    print("=" * 50)
    
    # Validate environment
    validate_jwt_environment()
    
    print("\nFixing Test Files:")
    
    # Fix the test file
    changes = fix_authentication_test_file()
    
    print("\nSummary:")
    print(f"Total changes made: {changes}")
    print("Authentication test token fixes completed!")
    
    if changes > 0:
        print("\nNext steps:")
        print("1. Run the authentication tests to verify fixes")
        print("2. Check that JWT tokens are properly validated")
        print("3. Verify service-to-service authentication works")


if __name__ == "__main__":
    main()