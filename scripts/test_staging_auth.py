#!/usr/bin/env python3
"""
Test and diagnose staging authentication issues.
Checks JWT validation between auth service and backend.
"""

import jwt
import json
import sys
import os
import time
from typing import Dict, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def decode_token_no_verify(token: str) -> Optional[Dict]:
    """Decode JWT token without signature verification."""
    try:
        return jwt.decode(token, options={'verify_signature': False})
    except Exception as e:
        print(f"Error decoding token: {e}")
        return None


def test_token_with_secret(token: str, secret: str) -> bool:
    """Test if a token can be validated with a given secret."""
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_exp": False}  # Ignore expiration for testing
        )
        print(f"[OK] Token validated successfully with provided secret")
        return True
    except jwt.InvalidSignatureError:
        print(f"[X] Invalid signature with provided secret")
        return False
    except jwt.DecodeError as e:
        print(f"[X] Decode error: {e}")
        return False
    except Exception as e:
        print(f"[X] Unexpected error: {e}")
        return False


def analyze_staging_token():
    """Analyze the problematic staging token."""
    # The token from the staging error
    staging_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3YzVlMTAzMi1lZDIxLTRhZWEtYjEyYS1hZWRkZjM2MjJiZWMiLCJpYXQiOjE3NTY0NzIzNjYsImV4cCI6MTc1NjQ3MzI2NiwidG9rZW5fdHlwZSI6ImFjY2VzcyIsInR5cGUiOiJhY2VzcyIsImlzcyI6Im5ldHJhLWF1dGgtc2VydmljZSIsImF1ZCI6Im5ldHJhLXBsYXRmb3JtIiwianRpIjoiNjRmMjQ4MzQtNjdlMi00NjViLWFjNWQtOWY3NzIyZDdlYjgyIiwiZW52Ijoic3RhZ2luZyIsInN2Y19pZCI6Im5ldHJhLWF1dGgtc3RhZ2luZy0xNzU2NDY0NjkxIiwiZW1haWwiOiJ1c2VyQGV4YW1wbGUuY29tIiwicGVybWlzc2lvbnMiOltdfQ.abVn9LBJSqFp1yCglnWqXrQoMjCxUdvFIjGcxV0GbXA"
    
    print("=" * 80)
    print("STAGING TOKEN ANALYSIS")
    print("=" * 80)
    
    # Decode without verification
    payload = decode_token_no_verify(staging_token)
    if not payload:
        print("Failed to decode token")
        return
    
    print("\nToken Payload:")
    print(json.dumps(payload, indent=2))
    
    # Check expiration
    current_time = time.time()
    exp_time = payload.get('exp', 0)
    iat_time = payload.get('iat', 0)
    
    print(f"\nTime Analysis:")
    print(f"  Issued At: {time.ctime(iat_time)} (timestamp: {iat_time})")
    print(f"  Expires: {time.ctime(exp_time)} (timestamp: {exp_time})")
    print(f"  Current: {time.ctime(current_time)} (timestamp: {int(current_time)})")
    
    if exp_time < current_time:
        print(f"  [X] Token is EXPIRED (expired {int(current_time - exp_time)} seconds ago)")
    else:
        print(f"  [OK] Token is VALID (expires in {int(exp_time - current_time)} seconds)")
    
    # Check for typo
    print(f"\nField Analysis:")
    print(f"  token_type: '{payload.get('token_type')}' (correct field)")
    print(f"  type: '{payload.get('type')}' (compatibility field)")
    if payload.get('type') == 'acess':
        print(f"  WARNING: 'type' field has typo: 'acess' instead of 'access'")
    
    # Test with different secrets
    print(f"\nJWT Secret Testing:")
    
    # Test common development/staging secrets
    test_secrets = [
        # Common test secrets
        ("test-secret-key", "Common test secret"),
        ("super-secret-key-for-jwt-signing-do-not-share", "Common staging secret"),
        ("TEST-ONLY-SECRET-NOT-FOR-PRODUCTION-" + "x" * 32, "Default test secret from code"),
        
        # Secrets that might be in environment
        (os.environ.get("JWT_SECRET_KEY", ""), "From JWT_SECRET_KEY env var"),
        (os.environ.get("JWT_SECRET", ""), "From JWT_SECRET env var"),
    ]
    
    for secret, description in test_secrets:
        if secret:
            print(f"\n  Testing: {description}")
            print(f"    Secret length: {len(secret)} chars")
            if test_token_with_secret(staging_token, secret):
                print(f"    [SUCCESS] - Token was signed with this secret!")
                break
    else:
        print("\n  [ERROR] Could not validate token with any known secrets")
        print("     The auth service and backend are likely using different JWT secrets")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS:")
    print("=" * 80)
    print("""
1. Ensure JWT_SECRET_KEY environment variable is set consistently in staging:
   - Auth service should have the same JWT_SECRET_KEY as backend service
   - Check Cloud Run service configurations for both services
   
2. The token has a typo in the 'type' field ('acess' instead of 'access')
   - This appears to be from an older version of the code
   - Current code should generate 'type': 'access' correctly
   
3. To fix immediately:
   - Set the same JWT_SECRET_KEY in both services' environment variables
   - Restart both services to pick up the new configuration
   - Test authentication flow again
""")


def check_environment_config():
    """Check current environment configuration."""
    print("\n" + "=" * 80)
    print("ENVIRONMENT CONFIGURATION CHECK")
    print("=" * 80)
    
    # Check for JWT configuration
    jwt_configs = [
        "JWT_SECRET_KEY",
        "JWT_SECRET",
        "AUTH_SERVICE_URL",
        "ENVIRONMENT",
        "SERVICE_ID",
        "SERVICE_SECRET"
    ]
    
    print("\nCurrent Environment Variables:")
    for key in jwt_configs:
        value = os.environ.get(key)
        if value:
            if "SECRET" in key or "KEY" in key:
                # Mask sensitive values
                masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
                print(f"  {key}: {masked} (length: {len(value)})")
            else:
                print(f"  {key}: {value}")
        else:
            print(f"  {key}: <not set>")
    
    # Try to load backend config
    try:
        from netra_backend.app.core.config import get_settings
        settings = get_settings()
        print("\nBackend Configuration:")
        print(f"  Environment: {settings.environment}")
        print(f"  Auth Service URL: {settings.auth_service_url}")
        jwt_secret = getattr(settings, 'jwt_secret_key', None) or getattr(settings, 'jwt_secret', None)
        if jwt_secret:
            masked = jwt_secret[:4] + "..." + jwt_secret[-4:] if len(jwt_secret) > 8 else "***"
            print(f"  JWT Secret: {masked} (length: {len(jwt_secret)})")
        else:
            print(f"  JWT Secret: <not configured>")
    except Exception as e:
        print(f"\nWARNING: Could not load backend configuration: {e}")
    
    # Try to load auth service config
    try:
        from auth_service.auth_core.config import AuthConfig
        print("\nAuth Service Configuration:")
        print(f"  Environment: {AuthConfig.get_environment()}")
        jwt_secret = AuthConfig.get_jwt_secret()
        if jwt_secret:
            masked = jwt_secret[:4] + "..." + jwt_secret[-4:] if len(jwt_secret) > 8 else "***"
            print(f"  JWT Secret: {masked} (length: {len(jwt_secret)})")
        else:
            print(f"  JWT Secret: <not configured>")
    except Exception as e:
        print(f"\nWARNING: Could not load auth service configuration: {e}")


if __name__ == "__main__":
    print("Staging Authentication Diagnostic Tool\n")
    
    # Analyze the problematic token
    analyze_staging_token()
    
    # Check environment configuration
    check_environment_config()
    
    print("\nDiagnostic complete!")