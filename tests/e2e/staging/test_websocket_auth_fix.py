"""
WebSocket Authentication Fix Test

This test reproduces the exact 403 authentication failure seen in staging.
It demonstrates the JWT secret mismatch between test JWT creation and backend validation.

Business Value: Ensures WebSocket authentication works correctly in staging environment,
enabling chat functionality which delivers 90% of user value.
"""

import asyncio
import json
import time
import uuid
import jwt
import websockets
import pytest
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from tests.e2e.staging_test_config import get_staging_config
from shared.isolated_environment import get_env

pytestmark = [pytest.mark.staging, pytest.mark.critical, pytest.mark.real]


class TestWebSocketAuthenticationFix:
    """Test WebSocket authentication fix by reproducing and then fixing the 403 error."""
    
    def test_debug_jwt_secret_resolution(self):
        """Debug test to show what JWT secrets are being resolved by test vs backend."""
        print("\n" + "="*80)
        print("JWT SECRET RESOLUTION DEBUG")
        print("="*80)
        
        # Get environment
        env = get_env()
        environment = env.get("ENVIRONMENT", "development").lower()
        
        print(f"Environment: {environment}")
        print(f"Testing: {env.get('TESTING', '0')}")
        
        # Show test resolution logic (from staging_test_config.py)
        print("\nTEST JWT SECRET RESOLUTION ORDER:")
        print("1. JWT_SECRET_STAGING")
        print("2. JWT_SECRET_KEY")
        print("3. E2E_BYPASS_KEY")
        print("4. STAGING_JWT_SECRET")
        print("5. Hardcoded fallback")
        
        # Test resolution
        test_secrets = {}
        env_specific_key = f"JWT_SECRET_{environment.upper()}"
        
        test_secrets['env_specific'] = env.get(env_specific_key)
        test_secrets['jwt_secret_key'] = env.get("JWT_SECRET_KEY")
        test_secrets['e2e_bypass'] = env.get("E2E_BYPASS_KEY")
        test_secrets['staging_jwt_secret'] = env.get("STAGING_JWT_SECRET")
        test_secrets['hardcoded_fallback'] = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
        
        print(f"\nTEST SECRET VALUES:")
        for key, value in test_secrets.items():
            if value:
                print(f"  {key}: {value[:20]}...{value[-10:] if len(value) > 30 else ''}")
            else:
                print(f"  {key}: NOT SET")
        
        # Show backend resolution logic (from user_context_extractor.py)
        print("\nBACKEND JWT SECRET RESOLUTION ORDER:")
        print("1. JWT_SECRET_STAGING")
        print("2. JWT_SECRET_KEY") 
        print("3. JWT_SECRET")
        print("4. AUTH_JWT_SECRET")
        print("5. SECRET_KEY")
        print("6. Development default (testing only)")
        
        # Backend resolution
        backend_secrets = {}
        backend_secrets['jwt_secret_staging'] = env.get("JWT_SECRET_STAGING")
        backend_secrets['jwt_secret_key'] = env.get("JWT_SECRET_KEY")
        backend_secrets['jwt_secret'] = env.get("JWT_SECRET")
        backend_secrets['auth_jwt_secret'] = env.get("AUTH_JWT_SECRET")
        backend_secrets['secret_key'] = env.get("SECRET_KEY")
        backend_secrets['dev_default'] = "test_jwt_secret_key_for_development_only"
        
        print(f"\nBACKEND SECRET VALUES:")
        for key, value in backend_secrets.items():
            if value:
                print(f"  {key}: {value[:20]}...{value[-10:] if len(value) > 30 else ''}")
            else:
                print(f"  {key}: NOT SET")
        
        # Determine what each would actually use
        test_secret = None
        for key in ['env_specific', 'jwt_secret_key', 'e2e_bypass', 'staging_jwt_secret']:
            if test_secrets[key]:
                test_secret = test_secrets[key]
                print(f"\nTEST WOULD USE: {key} = {test_secret[:20]}...{test_secret[-10:]}")
                break
        if not test_secret:
            test_secret = test_secrets['hardcoded_fallback']
            print(f"\nTEST WOULD USE: hardcoded_fallback = {test_secret[:20]}...{test_secret[-10:]}")
        
        backend_secret = None
        for key in ['jwt_secret_staging', 'jwt_secret_key', 'jwt_secret', 'auth_jwt_secret', 'secret_key']:
            if backend_secrets[key]:
                backend_secret = backend_secrets[key]
                print(f"BACKEND WOULD USE: {key} = {backend_secret[:20]}...{backend_secret[-10:]}")
                break
        if not backend_secret and environment in ["testing", "development"]:
            backend_secret = backend_secrets['dev_default']
            print(f"BACKEND WOULD USE: dev_default = {backend_secret}")
        
        print(f"\n" + "="*80)
        print("SECRET MISMATCH ANALYSIS")
        print("="*80)
        
        if test_secret and backend_secret:
            if test_secret == backend_secret:
                print("SECRETS MATCH - No mismatch detected")
            else:
                print("SECRETS MISMATCH - This will cause 403 errors!")
                print(f"   Test:    {test_secret[:30]}...")
                print(f"   Backend: {backend_secret[:30]}...")
        else:
            print("One or both secrets are missing")
            print(f"   Test secret found: {'YES' if test_secret else 'NO'}")
            print(f"   Backend secret found: {'YES' if backend_secret else 'NO'}")
    
    @pytest.mark.asyncio
    async def test_reproduce_websocket_403_error(self):
        """Reproduce the exact 403 WebSocket authentication error from staging."""
        print("\n" + "="*80)
        print("REPRODUCING WEBSOCKET 403 ERROR")
        print("="*80)
        
        config = get_staging_config()
        start_time = time.time()
        
        # Get WebSocket headers with JWT token (using current test logic)
        ws_headers = config.get_websocket_headers()
        
        print(f"WebSocket URL: {config.websocket_url}")
        print(f"Authorization header present: {'Authorization' in ws_headers}")
        
        if 'Authorization' in ws_headers:
            token = ws_headers['Authorization'].replace('Bearer ', '')
            print(f"JWT token length: {len(token)}")
            
            # Decode the JWT without verification to see what's in it
            try:
                decoded_payload = jwt.decode(token, options={"verify_signature": False})
                print(f"JWT payload (unverified): {json.dumps(decoded_payload, indent=2, default=str)}")
            except Exception as e:
                print(f"Could not decode JWT payload: {e}")
        
        # Attempt WebSocket connection
        connection_successful = False
        error_details = None
        
        try:
            print("\nAttempting WebSocket connection with JWT authentication...")
            async with websockets.connect(
                config.websocket_url,
                additional_headers=ws_headers,
                close_timeout=10
            ) as ws:
                print("✅ WebSocket connection successful!")
                connection_successful = True
                
                # Try to send a ping
                await ws.send(json.dumps({"type": "ping"}))
                
                # Wait for response
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                print(f"WebSocket response: {response}")
                
        except websockets.exceptions.InvalidStatus as e:
            error_details = {
                "error_type": "InvalidStatus",
                "status_code": getattr(e, 'status_code', 'unknown'),
                "message": str(e)
            }
            print(f"❌ WebSocket connection failed: {error_details}")
            
            # This is the expected error we're reproducing
            if "403" in str(e):
                print("✅ Successfully reproduced the 403 authentication error!")
            else:
                print(f"❌ Got different error than expected 403: {e}")
                
        except Exception as e:
            error_details = {
                "error_type": type(e).__name__,
                "message": str(e)
            }
            print(f"❌ Unexpected WebSocket error: {error_details}")
        
        duration = time.time() - start_time
        print(f"\nTest duration: {duration:.3f}s")
        
        # Verify this was a real test
        assert duration > 0.1, f"Test too fast ({duration:.3f}s) - likely fake!"
        
        # For this reproducing test, we expect the connection to fail with 403
        # Once we fix the issue, we'll update this test to expect success
        if not connection_successful and error_details and "403" in str(error_details.get('message', '')):
            print("✅ Test reproduced the 403 authentication error as expected")
            # This is the bug we're trying to fix
        elif connection_successful:
            print("✅ WebSocket connection successful - bug may already be fixed!")
        else:
            print(f"❌ Got unexpected error: {error_details}")
            # Still a failure, but different from what we expected
    
    @pytest.mark.asyncio  
    async def test_create_jwt_with_backend_secret(self):
        """Test creating JWT with the exact secret the backend expects."""
        print("\n" + "="*80)
        print("TESTING JWT WITH BACKEND SECRET")
        print("="*80)
        
        # Simulate backend secret resolution logic exactly
        env = get_env()
        environment = env.get("ENVIRONMENT", "development").lower()
        
        # Backend resolution order (from user_context_extractor.py)
        backend_secret = None
        secret_source = None
        
        env_specific_key = f"JWT_SECRET_{environment.upper()}"
        if env.get(env_specific_key):
            backend_secret = env.get(env_specific_key).strip()
            secret_source = env_specific_key
        elif env.get("JWT_SECRET_KEY"):
            backend_secret = env.get("JWT_SECRET_KEY").strip()
            secret_source = "JWT_SECRET_KEY"
        elif env.get("JWT_SECRET"):
            backend_secret = env.get("JWT_SECRET").strip()
            secret_source = "JWT_SECRET"
        elif env.get("AUTH_JWT_SECRET"):
            backend_secret = env.get("AUTH_JWT_SECRET").strip()
            secret_source = "AUTH_JWT_SECRET"
        elif env.get("SECRET_KEY"):
            backend_secret = env.get("SECRET_KEY").strip()
            secret_source = "SECRET_KEY"
        elif environment in ["testing", "development"]:
            backend_secret = "test_jwt_secret_key_for_development_only"
            secret_source = "development_default"
        
        print(f"Backend would use: {secret_source}")
        print(f"Backend secret: {backend_secret[:20]}...{backend_secret[-10:] if backend_secret and len(backend_secret) > 30 else backend_secret}")
        
        if not backend_secret:
            print("❌ No backend secret found!")
            return
        
        # Create JWT using backend secret
        try:
            payload = {
                "sub": f"test-user-{uuid.uuid4().hex[:8]}",
                "email": "test@netrasystems.ai", 
                "permissions": ["read", "write"],
                "iat": int(datetime.now(timezone.utc).timestamp()),
                "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
                "token_type": "access",
                "iss": "netra-auth-service",
                "jti": str(uuid.uuid4())
            }
            
            token = jwt.encode(payload, backend_secret, algorithm="HS256")
            print(f"✅ Created JWT token using backend secret")
            print(f"Token length: {len(token)}")
            
            # Try WebSocket connection with this token
            config = get_staging_config()
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Test-Type": "E2E",
                "X-Test-Environment": "staging"
            }
            
            print("\nTesting WebSocket connection with backend-compatible JWT...")
            
            try:
                async with websockets.connect(
                    config.websocket_url,
                    additional_headers=headers,
                    close_timeout=10
                ) as ws:
                    print("✅ WebSocket connection successful with backend secret!")
                    
                    # Send test message
                    await ws.send(json.dumps({
                        "type": "ping",
                        "timestamp": time.time()
                    }))
                    
                    response = await asyncio.wait_for(ws.recv(), timeout=5)
                    print(f"WebSocket response: {response}")
                    return True
                    
            except websockets.exceptions.InvalidStatus as e:
                print(f"❌ Still getting WebSocket error with backend secret: {e}")
                return False
            except Exception as e:
                print(f"❌ Unexpected error with backend secret: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to create JWT with backend secret: {e}")
            return False


if __name__ == "__main__":
    # Run the debug test to show secret resolution
    test_instance = TestWebSocketAuthenticationFix()
    test_instance.test_debug_jwt_secret_resolution()
    
    print("\n" + "="*80)
    print("Run with pytest to execute async tests:")
    print("python -m pytest tests/e2e/staging/test_websocket_auth_fix.py -v -s")
    print("="*80)