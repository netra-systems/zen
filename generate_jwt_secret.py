#!/usr/bin/env python3
"""Generate a secure JWT secret for staging environment"""

import secrets
import string

def generate_jwt_secret(length=64):
    """Generate a secure JWT secret of specified length"""
    alphabet = string.ascii_letters + string.digits + '-_'
    return ''.join(secrets.choice(alphabet) for i in range(length))

if __name__ == "__main__":
    jwt_secret = generate_jwt_secret(64)
    print(f"Generated JWT_SECRET_STAGING: {jwt_secret}")
    print(f"Length: {len(jwt_secret)} characters")

    # Validate it meets requirements
    if len(jwt_secret) >= 32:
        print("✅ Secret meets minimum 32-character requirement")
    else:
        print("❌ Secret too short")

    print(f"\nTo configure in GCP:")
    print(f"JWT_SECRET_STAGING={jwt_secret}")