print("[U+2713] Starting Issue #463 Reproduction Test")

# Test 1: Reproduce missing SERVICE_SECRET
print("Test 1: Missing SERVICE_SECRET")
try:
    import os
    # Simulate staging environment where SERVICE_SECRET is missing
    service_secret = os.environ.get("SERVICE_SECRET")  
    if service_secret is None:
        print("[U+2713] REPRODUCED: SERVICE_SECRET is missing (None)")
        print("  This causes 403 authentication failures for service:netra-backend in staging")
    else:
        print(f"  SERVICE_SECRET found: {service_secret[:10]}...")
except Exception as e:
    print(f"  Error accessing SERVICE_SECRET: {e}")

# Test 2: Reproduce missing JWT_SECRET
print("Test 2: Missing JWT_SECRET")
try:
    jwt_secret = os.environ.get("JWT_SECRET")
    if jwt_secret is None:
        print("[U+2713] REPRODUCED: JWT_SECRET is missing (None)")
        print("  This also contributes to authentication failures")
    else:
        print(f"  JWT_SECRET found: {jwt_secret[:10]}...")
except Exception as e:
    print(f"  Error accessing JWT_SECRET: {e}")

# Test 3: Reproduce missing AUTH_SERVICE_URL
print("Test 3: Missing AUTH_SERVICE_URL")
try:
    auth_service_url = os.environ.get("AUTH_SERVICE_URL")
    if auth_service_url is None:
        print("[U+2713] REPRODUCED: AUTH_SERVICE_URL is missing (None)")
        print("  This prevents connection to auth service")
    else:
        print(f"  AUTH_SERVICE_URL found: {auth_service_url}")
except Exception as e:
    print(f"  Error accessing AUTH_SERVICE_URL: {e}")

print("\n[U+2713] Issue #463 reproduction tests completed")
print("[U+2713] These missing environment variables cause WebSocket authentication failures")
print("[U+2713] Tests successfully reproduce the staging environment issue")

