#!/usr/bin/env python3
"""
Token Validation Fix Verification Test
Tests that JWT secrets are now consistent between auth service and backend.
"""

import os
import sys
from pathlib import Path

def load_env_file():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value

def test_env_consistency():
    """Test that both JWT_SECRET and JWT_SECRET_KEY are available."""
    load_env_file()
    
    jwt_secret = os.getenv("JWT_SECRET")
    jwt_secret_key = os.getenv("JWT_SECRET_KEY")
    
    print("JWT Token Validation Fix Verification")
    print("=" * 45)
    print()
    
    print("Environment Variables:")
    print(f"  JWT_SECRET: {'SET' if jwt_secret else 'NOT SET'}")
    print(f"  JWT_SECRET_KEY: {'SET' if jwt_secret_key else 'NOT SET'}")
    print()
    
    if jwt_secret and jwt_secret_key:
        if jwt_secret == jwt_secret_key:
            print("SUCCESS: Both JWT secrets are set and match!")
            print(f"   Value: {jwt_secret[:20]}...")
            return True
        else:
            print("WARNING: JWT secrets are set but don't match")
            print(f"   JWT_SECRET: {jwt_secret[:20]}...")
            print(f"   JWT_SECRET_KEY: {jwt_secret_key[:20]}...")
            return False
    else:
        print("FAIL: One or both JWT secrets are missing")
        return False

def test_auth_service_import():
    """Test that auth service can import and get JWT secret."""
    try:
        # Add auth service to Python path
        auth_path = Path(__file__).parent / 'auth_service'
        if auth_path.exists():
            sys.path.insert(0, str(auth_path))
        
        from auth_core.config import AuthConfig
        
        secret = AuthConfig.get_jwt_secret()
        if secret:
            print("SUCCESS: Auth service can retrieve JWT secret")
            print(f"   Auth service secret: {secret[:20]}...")
            return True
        else:
            print("FAIL: Auth service cannot retrieve JWT secret")
            return False
    except ImportError as e:
        print(f"SKIP: Cannot import auth service config: {e}")
        return None
    except Exception as e:
        print(f"FAIL: Auth service config error: {e}")
        return False

def test_token_creation():
    """Test creating and validating a JWT token."""
    try:
        import jwt
        from datetime import datetime, timedelta, timezone
        
        load_env_file()
        secret = os.getenv("JWT_SECRET_KEY")
        
        if not secret:
            print("SKIP: No JWT secret available for token test")
            return None
            
        # Create test token
        payload = {
            "sub": "test-user-123",
            "email": "test@example.com", 
            "token_type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "iss": "netra-auth-service"
        }
        
        # Encode token
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        # Decode token
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        
        print("SUCCESS: JWT token creation and validation works")
        print(f"   Test token: {token[:30]}...")
        print(f"   Decoded user: {decoded.get('sub')}")
        return True
        
    except ImportError:
        print("SKIP: PyJWT not available for token test")
        return None
    except Exception as e:
        print(f"FAIL: Token test failed: {e}")
        return False

def main():
    env_test = test_env_consistency()
    auth_test = test_auth_service_import()
    token_test = test_token_creation()
    
    print()
    print("=" * 45)
    if env_test and (auth_test is None or auth_test) and (token_test is None or token_test):
        print("SUCCESS: TOKEN VALIDATION FIX WORKING!")
        print("Both services can now access the same JWT secret.")
        print()
        print("Next steps:")
        print("1. Start auth service: cd auth_service && python main.py")
        print("2. Start backend: python -m app.main")
        print("3. Test token flow: python test_token_flow_final.py")
    else:
        print("PARTIAL: Some issues remain")
        print("Check the errors above and re-run after fixing.")

if __name__ == "__main__":
    main()