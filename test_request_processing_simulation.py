#!/usr/bin/env python3
"""
Test request processing simulation to reproduce Issue #169.

This simulates the actual request flow that causes the SessionMiddleware errors in GCP staging.
"""

import os
import sys
import traceback

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def simulate_request_processing():
    """Simulate the request processing flow that causes Issue #169."""
    print("=== Request Processing Simulation ===")
    
    try:
        from fastapi import FastAPI, Request
        from fastapi.testclient import TestClient
        from netra_backend.app.core.middleware_setup import setup_middleware
        
        # Setup staging environment (where the issue occurs)
        os.environ['ENVIRONMENT'] = 'staging'
        os.environ['GCP_PROJECT_ID'] = 'netra-staging'
        
        # Test without SECRET_KEY first (issue condition)
        print("\n--- Test 1: Full middleware stack without SECRET_KEY ---")
        if 'SECRET_KEY' in os.environ:
            del os.environ['SECRET_KEY']
        
        app = FastAPI()
        
        try:
            setup_middleware(app)
            print("SUCCESS: Middleware setup completed")
            
            # Check what middleware were installed
            middleware_classes = [str(middleware.cls) for middleware in app.user_middleware]
            print(f"Installed middleware: {len(middleware_classes)} total")
            for i, cls in enumerate(middleware_classes):
                print(f"  {i}: {cls}")
                
            # Test endpoint that accesses session
            @app.get("/test-session")
            async def test_session(request: Request):
                try:
                    session = request.session
                    session['test'] = 'value'
                    return {"status": "success", "session_working": True}
                except Exception as e:
                    return {"status": "error", "error": str(e)}
                    
            @app.get("/test-gcp-auth")
            async def test_gcp_auth(request: Request):
                # This would trigger GCPAuthContextMiddleware to access request.session
                return {"status": "checking_auth"}
            
            # Test with TestClient
            client = TestClient(app)
            
            print("\n--- Testing session access endpoint ---")
            response = client.get("/test-session")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.json().get('status') == 'error':
                error_msg = response.json().get('error', '')
                if 'SessionMiddleware must be installed' in error_msg:
                    print("REPRODUCED: SessionMiddleware error in request processing!")
                else:
                    print(f"Different error: {error_msg}")
                    
            print("\n--- Testing GCP auth endpoint ---")
            response2 = client.get("/test-gcp-auth")
            print(f"Status: {response2.status_code}")
            print(f"Response: {response2.json()}")
            
        except Exception as e:
            print(f"FAILED: Middleware setup failed: {e}")
            traceback.print_exc()
            
        # Test with valid SECRET_KEY
        print("\n--- Test 2: Full middleware stack with valid SECRET_KEY ---")
        os.environ['SECRET_KEY'] = 'a' * 32 + 'valid_secret_for_full_test'
        
        app2 = FastAPI()
        setup_middleware(app2)
        
        @app2.get("/test-session2")
        async def test_session2(request: Request):
            try:
                session = request.session
                session['test'] = 'value'
                return {"status": "success", "session_working": True}
            except Exception as e:
                return {"status": "error", "error": str(e)}
        
        client2 = TestClient(app2)
        response3 = client2.get("/test-session2")
        print(f"With SECRET_KEY - Status: {response3.status_code}")
        print(f"With SECRET_KEY - Response: {response3.json()}")
        
    except Exception as e:
        print(f"FAILED: Request processing simulation failed: {e}")
        traceback.print_exc()

def test_direct_gcp_auth_middleware():
    """Test GCPAuthContextMiddleware directly."""
    print("\n=== Direct GCPAuthContextMiddleware Test ===")
    
    try:
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        from unittest.mock import MagicMock
        
        # Create a request mock that simulates missing SessionMiddleware
        request = MagicMock()
        
        # Mock session property to raise the specific error
        def raise_session_error():
            raise RuntimeError("SessionMiddleware must be installed to access request.session")
        
        # This is the key - create a property that raises on access
        type(request).session = property(lambda self: raise_session_error())
        
        # Test the middleware directly
        print("Testing GCPAuthContextMiddleware with missing SessionMiddleware...")
        
        # Note: Need to check the actual signature
        try:
            middleware = GCPAuthContextMiddleware(app=MagicMock())
        except Exception as e:
            print(f"FAILED: Could not instantiate middleware: {e}")
            return
            
        # Test the auth context extraction
        import asyncio
        
        async def test_extraction():
            try:
                # Look for the method that extracts auth context
                if hasattr(middleware, '_extract_auth_context'):
                    result = await middleware._extract_auth_context(request)
                    print(f"SUCCESS: Defensive handling worked: {result}")
                elif hasattr(middleware, 'extract_auth_context'):
                    result = await middleware.extract_auth_context(request)
                    print(f"SUCCESS: Defensive handling worked: {result}")
                else:
                    print("FAILED: No auth context extraction method found")
                    
            except RuntimeError as e:
                if "SessionMiddleware must be installed" in str(e):
                    print(f"REPRODUCED: SessionMiddleware error not handled defensively: {e}")
                    return False
                else:
                    print(f"Other runtime error: {e}")
                    
            except Exception as e:
                print(f"Other exception: {e}")
                
            return True
                
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(test_extraction())
        loop.close()
        
    except ImportError as e:
        print(f"FAILED: Could not import GCPAuthContextMiddleware: {e}")
    except Exception as e:
        print(f"FAILED: Error testing GCPAuthContextMiddleware: {e}")
        traceback.print_exc()

def main():
    """Run the request processing simulation."""
    print("Issue #169 Request Processing Simulation")
    print("=" * 50)
    
    simulate_request_processing()
    test_direct_gcp_auth_middleware()
    
    print("\n" + "=" * 50)
    print("Simulation complete. Check output above for Issue #169 reproduction.")

if __name__ == "__main__":
    main()