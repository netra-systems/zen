#!/usr/bin/env python3
"""
Direct SessionMiddleware test - bypasses environment validation issues.
Tests for Issue #1127: SessionMiddleware Configuration Missing
"""
import sys
import os
sys.path.insert(0, '.')

# Set minimal environment variables to bypass validation using SSOT IsolatedEnvironment
from shared.isolated_environment import IsolatedEnvironment
env = IsolatedEnvironment()
env.set('ENVIRONMENT', 'development', 'test_session_middleware')
env.set('SECRET_KEY', 'test-secret-key-32-chars-minimum-req', 'test_session_middleware')
env.set('JWT_SECRET_KEY', 'test-jwt-secret-key-32-chars-minimum', 'test_session_middleware')

def test_middleware_stack():
    """Test SessionMiddleware installation without full environment validation."""
    try:
        # Import the setup function directly
        from netra_backend.app.core.middleware_setup import setup_middleware
        from fastapi import FastAPI

        print("Creating test FastAPI app...")
        app = FastAPI()

        print("Setting up middleware stack...")
        setup_middleware(app)

        print(f"\nMiddleware stack analysis:")
        print(f"Total middleware count: {len(app.user_middleware)}")

        session_middleware_found = False
        gcp_auth_middleware_found = False

        for i, middleware in enumerate(app.user_middleware):
            middleware_name = getattr(middleware.cls, '__name__', str(middleware.cls))
            print(f"{i+1}. {middleware_name}")

            if 'Session' in middleware_name:
                session_middleware_found = True
                print(f"   ✅ SessionMiddleware found at position {i+1}")

            if 'GCPAuth' in middleware_name or 'AuthContext' in middleware_name:
                gcp_auth_middleware_found = True
                print(f"   🔍 GCP Auth Context middleware found at position {i+1}")

        print(f"\nDiagnostic Results:")
        print(f"SessionMiddleware installed: {'✅ YES' if session_middleware_found else '❌ NO'}")
        print(f"GCP Auth Context middleware installed: {'✅ YES' if gcp_auth_middleware_found else '❌ NO'}")

        if not session_middleware_found:
            print(f"\n🚨 ISSUE CONFIRMED: SessionMiddleware not installed in middleware stack!")
            print(f"This explains the 100+ 'SessionMiddleware must be installed' errors per hour.")
            return False

        if session_middleware_found and gcp_auth_middleware_found:
            print(f"\n✅ Both SessionMiddleware and GCP Auth Context middleware are properly installed")
            return True

        return session_middleware_found

    except Exception as e:
        print(f"❌ Error testing middleware stack: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_session_access_simulation():
    """Simulate the session access that's failing in GCP Auth Context middleware."""
    try:
        from fastapi import Request
        from starlette.testclient import TestClient
        from starlette.middleware.sessions import SessionMiddleware
        from fastapi import FastAPI

        print(f"\n🧪 Testing session access simulation...")

        # Create app with minimal middleware
        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="test-secret-key")

        @app.get("/test")
        def test_endpoint(request: Request):
            try:
                # This is the line that fails in gcp_auth_context_middleware.py:353
                session = request.session
                return {"status": "success", "session_available": bool(session)}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        client = TestClient(app)
        response = client.get("/test")

        print(f"Session access test result: {response.json()}")

        if response.json().get("status") == "success":
            print(f"✅ Session access works when SessionMiddleware is properly installed")
            return True
        else:
            print(f"❌ Session access failed: {response.json().get('error')}")
            return False

    except Exception as e:
        print(f"❌ Error in session access simulation: {e}")
        return False

if __name__ == "__main__":
    print("=== SessionMiddleware Diagnostic Test (Issue #1127) ===\n")

    middleware_test_passed = test_middleware_stack()
    session_test_passed = test_session_access_simulation()

    print(f"\n=== Summary ===")
    print(f"Middleware installation test: {'✅ PASS' if middleware_test_passed else '❌ FAIL'}")
    print(f"Session access test: {'✅ PASS' if session_test_passed else '❌ FAIL'}")

    if not middleware_test_passed:
        print(f"\n🔧 IMMEDIATE FIX REQUIRED:")
        print(f"1. SessionMiddleware is not being installed in the middleware stack")
        print(f"2. This causes GCP Auth Context middleware to fail when accessing request.session")
        print(f"3. Results in 100+ 'SessionMiddleware must be installed' errors per hour")
        print(f"4. Need to fix middleware_setup.py to ensure SessionMiddleware is properly installed")