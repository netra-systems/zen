#!/usr/bin/env python3
"""
Test JWT validation flow on staging - reproducing the 401 error
"""
import asyncio
import httpx
import json
from datetime import datetime
from shared.isolated_environment import IsolatedEnvironment

async def test_jwt_validation():
    """Test the exact JWT validation flow that's failing"""
    
    # The JWT token from the failing request
    jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3YzVlMTAzMi1lZDIxLTRhZWEtYjEyYS1hZWRkZjM2MjJiZWMiLCJpYXQiOjE3NTY0MTQxMDMsImV4cCI6MTc1NjQxNTAwMywidG9rZW5fdHlwZSI6ImFjY2VzcyIsInR5cGUiOiJhY2Nlc3MiLCJpc3MiOiJuZXRyYS1hdXRoLXNlcnZpY2UiLCJhdWQiOiJuZXRyYS1wbGF0Zm9ybSIsImp0aSI6Ijc2ZmZiYTg4LWJjNDctNDkyNS04MWJkLTRlMWQxMDlhMjRjYiIsImVudiI6InN0YWdpbmciLCJzdmNfaWQiOiJuZXRyYS1hdXRoLXN0YWdpbmctMTc1NjQwOTIxMyIsImVtYWlsIjoidXNlckBleGFtcGxlLmNvbSIsInBlcm1pc3Npb25zIjpbXX0.KNIAy-aqKIyPy3rv69zMbCGqpmwNOm78KfX9ThRBUFE"
    
    print("=" * 60)
    print("JWT VALIDATION TEST - STAGING")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Parse the JWT payload (without validation) to inspect
    import base64
    parts = jwt_token.split('.')
    if len(parts) == 3:
        payload_raw = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_raw) % 4
        if padding != 4:
            payload_raw += '=' * padding
        try:
            payload_decoded = base64.urlsafe_b64decode(payload_raw)
            payload = json.loads(payload_decoded)
            print("JWT Payload:")
            for key, value in payload.items():
                print(f"  {key}: {value}")
            print()
            
            # Check expiry
            import time
            current_time = time.time()
            if 'exp' in payload:
                exp_time = payload['exp']
                if exp_time < current_time:
                    print(f"[WARNING] Token is expired!")
                    print(f"  Expired at: {datetime.fromtimestamp(exp_time)}")
                    print(f"  Current time: {datetime.fromtimestamp(current_time)}")
                else:
                    print(f"[OK] Token valid until: {datetime.fromtimestamp(exp_time)}")
            print()
        except Exception as e:
            print(f"[ERROR] Failed to decode JWT payload: {e}")
            print()
    
    # Test 1: Direct validation with auth service
    print("1. Testing direct token validation with auth service...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://netra-auth-service-701982941522.us-central1.run.app/auth/validate",
                json={"token": jwt_token},
                headers={
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print(f"  [OK] Token validated successfully")
                result = response.json()
                print(f"  Result: {json.dumps(result, indent=2)}")
            else:
                print(f"  [FAIL] Validation failed")
                print(f"  Response: {response.text}")
    except Exception as e:
        print(f"  [ERROR] {e}")
    print()
    
    # Test 2: Validate through backend service 
    print("2. Testing token validation through backend service...")
    try:
        async with httpx.AsyncClient() as client:
            # First test if backend can validate the token internally
            response = await client.get(
                "https://netra-backend-staging-701982941522.us-central1.run.app/api/threads?limit=20&offset=0",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/json"
                },
                timeout=10.0
            )
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print(f"  [OK] Backend accepted token")
            elif response.status_code == 401:
                print(f"  [FAIL] Backend rejected token (401)")
                print(f"  Response: {response.text}")
                print(f"  Headers: {dict(response.headers)}")
            else:
                print(f"  [FAIL] Unexpected status code")
                print(f"  Response: {response.text}")
    except Exception as e:
        print(f"  [ERROR] {e}")
    print()
    
    # Test 3: Check if backend is using service authentication
    print("3. Testing if backend requires service authentication...")
    try:
        async with httpx.AsyncClient() as client:
            # Try to call auth service validate endpoint with service credentials
            # This would normally require the actual service secret
            response = await client.post(
                "https://netra-auth-service-701982941522.us-central1.run.app/auth/validate",
                json={"token": jwt_token},
                headers={
                    "Content-Type": "application/json",
                    "X-Service-ID": "netra-backend",
                    # Service secret would go here: "X-Service-Secret": "..."
                },
                timeout=10.0
            )
            print(f"  Status: {response.status_code}")
            if response.status_code == 401 or response.status_code == 403:
                print(f"  [INFO] Auth service may require service authentication")
                print(f"  Response: {response.text}")
            elif response.status_code == 200:
                print(f"  [OK] Validation successful without service secret")
            else:
                print(f"  Response: {response.text}")
    except Exception as e:
        print(f"  [ERROR] {e}")
    print()
    
    print("=" * 60)
    print("ANALYSIS")
    print("=" * 60)
    print("""
The 401 error is likely caused by one of these issues:

1. Token Expiry: The token has a 15-minute expiry and may be expired
2. Service Authentication: Backend may not have proper service credentials
   to validate tokens with the auth service
3. Cross-Service Validation: The token may be issued for a different
   environment or service context
4. Blacklisting: The token or user may have been blacklisted

Recommended fixes:
1. Ensure backend has correct SERVICE_SECRET configured for staging
2. Check that auth service URL is correctly configured in backend
3. Verify token is being validated with correct environment context
4. Check Redis/cache for any blacklist entries
""")

if __name__ == "__main__":
    asyncio.run(test_jwt_validation())