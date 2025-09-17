#!/usr/bin/env python3
"""
GCP Staging Environment Simulation for Issue #1127
Simulates the exact conditions in GCP Cloud Run where SessionMiddleware errors occur
"""
import sys
import os
sys.path.insert(0, '.')

# Simulate GCP Cloud Run staging environment
os.environ['ENVIRONMENT'] = 'staging'
os.environ['GCP_PROJECT_ID'] = 'netra-staging'  # This should trigger GCP Auth Context middleware installation
os.environ['SECRET_KEY'] = 'test-secret-key-32-chars-minimum-req'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-key-32-chars-minimum'

def test_gcp_staging_middleware_order():
    """Test middleware installation order in simulated GCP staging environment."""
    try:
        from netra_backend.app.core.middleware_setup import setup_middleware
        from fastapi import FastAPI

        print("🏗️ Creating test FastAPI app for GCP staging simulation...")
        app = FastAPI()

        print("🔧 Setting up middleware stack (simulating GCP Cloud Run staging)...")
        setup_middleware(app)

        print(f"\n📊 Middleware stack analysis (GCP staging simulation):")
        print(f"Total middleware count: {len(app.user_middleware)}")

        session_middleware_position = None
        gcp_auth_middleware_position = None

        for i, middleware in enumerate(app.user_middleware):
            middleware_name = getattr(middleware.cls, '__name__', str(middleware.cls))
            print(f"{i+1}. {middleware_name}")

            if 'Session' in middleware_name:
                session_middleware_position = i + 1
                print(f"   ✅ SessionMiddleware found at position {i+1}")

            if 'GCPAuth' in middleware_name or 'AuthContext' in middleware_name:
                gcp_auth_middleware_position = i + 1
                print(f"   🔍 GCP Auth Context middleware found at position {i+1}")

        print(f"\n📋 Middleware Installation Analysis:")
        print(f"SessionMiddleware installed: {'✅ YES at position ' + str(session_middleware_position) if session_middleware_position else '❌ NO'}")
        print(f"GCP Auth Context middleware installed: {'✅ YES at position ' + str(gcp_auth_middleware_position) if gcp_auth_middleware_position else '❌ NO'}")

        # Check middleware order - CRITICAL for preventing session access errors
        if session_middleware_position and gcp_auth_middleware_position:
            if session_middleware_position < gcp_auth_middleware_position:
                print(f"✅ CORRECT ORDER: SessionMiddleware ({session_middleware_position}) comes BEFORE GCP Auth Context ({gcp_auth_middleware_position})")
                return True
            else:
                print(f"❌ INCORRECT ORDER: GCP Auth Context ({gcp_auth_middleware_position}) comes BEFORE SessionMiddleware ({session_middleware_position})")
                print(f"   This causes 'SessionMiddleware must be installed' errors!")
                return False
        elif gcp_auth_middleware_position and not session_middleware_position:
            print(f"❌ CRITICAL ISSUE: GCP Auth Context middleware installed but SessionMiddleware missing!")
            return False
        elif session_middleware_position and not gcp_auth_middleware_position:
            print(f"ℹ️ INFO: Only SessionMiddleware installed (GCP Auth Context middleware not installed in this environment)")
            return True
        else:
            print(f"❌ Both middleware missing!")
            return False

    except Exception as e:
        print(f"❌ Error in GCP staging simulation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_session_access_with_gcp_middleware():
    """Test session access when both SessionMiddleware and GCP Auth Context middleware are installed."""
    try:
        from fastapi import Request, FastAPI
        from starlette.testclient import TestClient
        from starlette.middleware.sessions import SessionMiddleware
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware

        print(f"\n🧪 Testing session access with both middleware installed...")

        # Create app with both middleware in CORRECT order
        app = FastAPI()

        # SessionMiddleware FIRST
        app.add_middleware(SessionMiddleware, secret_key="test-secret-key")

        # GCP Auth Context middleware SECOND (AFTER SessionMiddleware)
        app.add_middleware(GCPAuthContextMiddleware, enable_user_isolation=True)

        @app.get("/test-session")
        def test_endpoint(request: Request):
            try:
                # This is the line that fails in gcp_auth_context_middleware.py:353
                session = request.session
                return {"status": "success", "session_available": bool(session)}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        client = TestClient(app)
        response = client.get("/test-session")

        print(f"Session access test result: {response.json()}")

        if response.json().get("status") == "success":
            print(f"✅ Session access works with correct middleware order")
            return True
        else:
            print(f"❌ Session access failed even with correct order: {response.json().get('error')}")
            return False

    except Exception as e:
        print(f"❌ Error in session access test with GCP middleware: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_gcp_environment_detection():
    """Analyze environment detection logic to see why GCP Auth Context middleware might not be installed."""
    try:
        from shared.isolated_environment import get_env

        print(f"\n🔍 Environment Detection Analysis:")

        env_manager = get_env()
        environment = env_manager.get('ENVIRONMENT', '').lower()
        project_id = env_manager.get('GCP_PROJECT_ID') or env_manager.get('GOOGLE_CLOUD_PROJECT')

        print(f"ENVIRONMENT: {environment}")
        print(f"GCP_PROJECT_ID: {project_id}")
        print(f"GOOGLE_CLOUD_PROJECT: {env_manager.get('GOOGLE_CLOUD_PROJECT')}")

        # Check the condition that determines middleware installation
        should_install = project_id and environment in ['staging', 'production']
        print(f"\nMiddleware installation condition: project_id={bool(project_id)} AND environment in ['staging', 'production']={environment in ['staging', 'production']}")
        print(f"Should install GCP Auth Context middleware: {'✅ YES' if should_install else '❌ NO'}")

        if not should_install:
            if not project_id:
                print(f"⚠️ Issue: No GCP project ID found")
            if environment not in ['staging', 'production']:
                print(f"⚠️ Issue: Environment '{environment}' is not staging or production")

        return should_install

    except Exception as e:
        print(f"❌ Error in environment detection analysis: {e}")
        return False

if __name__ == "__main__":
    print("=== GCP Cloud Run Staging Environment Simulation (Issue #1127) ===\n")

    env_detection_ok = analyze_gcp_environment_detection()
    middleware_order_ok = test_gcp_staging_middleware_order()
    session_access_ok = test_session_access_with_gcp_middleware()

    print(f"\n=== Simulation Results ===")
    print(f"Environment detection: {'✅ PASS' if env_detection_ok else '❌ FAIL'}")
    print(f"Middleware order test: {'✅ PASS' if middleware_order_ok else '❌ FAIL'}")
    print(f"Session access test: {'✅ PASS' if session_access_ok else '❌ FAIL'}")

    # Provide specific fix recommendations
    if not env_detection_ok:
        print(f"\n🔧 ENVIRONMENT DETECTION FIX:")
        print(f"The GCP Auth Context middleware is not being installed because:")
        print(f"1. Environment detection is failing in GCP Cloud Run")
        print(f"2. GCP_PROJECT_ID environment variable might be missing")
        print(f"3. Need to verify GCP Cloud Run environment variables")

    if not middleware_order_ok:
        print(f"\n🔧 MIDDLEWARE ORDER FIX:")
        print(f"The middleware order is incorrect in the setup_middleware() function:")
        print(f"1. SessionMiddleware must be installed BEFORE GCP Auth Context middleware")
        print(f"2. Check lines 814-849 in middleware_setup.py for correct ordering")
        print(f"3. The current order causes request.session access to fail")

    if not session_access_ok:
        print(f"\n🔧 SESSION ACCESS FIX:")
        print(f"Session access is failing even with correct middleware order:")
        print(f"1. Check for additional middleware conflicts")
        print(f"2. Verify SessionMiddleware secret key configuration")
        print(f"3. Look for WebSocket/HTTP middleware conflicts")