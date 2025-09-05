"""Test OAuth login route fix"""

from fastapi.testclient import TestClient
from auth_service.main import app
from unittest.mock import patch
import sys

def test_oauth_login_route():
    """Test that GET /auth/login?provider=google works"""
    client = TestClient(app)
    
    # Test 1: Missing provider parameter
    response = client.get("/auth/login")
    print(f"Test 1 - Missing provider: Status {response.status_code}")
    assert response.status_code == 400, "Should return 400 for missing provider"
    
    # Test 2: Invalid provider
    response = client.get("/auth/login?provider=invalid")
    print(f"Test 2 - Invalid provider: Status {response.status_code}")
    assert response.status_code == 400, "Should return 400 for invalid provider"
    
    # Test 3: Valid Google provider (mocked)
    with patch('auth_service.auth_core.oauth_manager.OAuthManager') as mock_manager:
        mock_instance = mock_manager.return_value
        mock_instance.is_provider_configured.return_value = True
        
        # Mock the Google provider
        mock_provider = type('obj', (object,), {
            'get_authorization_url': lambda self, state: f"https://accounts.google.com/o/oauth2/auth?state={state}"
        })()
        mock_instance.get_provider.return_value = mock_provider
        
        response = client.get("/auth/login?provider=google", follow_redirects=False)
        print(f"Test 3 - Valid Google provider: Status {response.status_code}")
        
        # Should redirect to Google OAuth
        assert response.status_code in [302, 307], f"Should redirect, got {response.status_code}"
        if hasattr(response, 'headers'):
            location = response.headers.get('location', '')
            print(f"  Redirect URL: {location[:100]}...")
            assert "accounts.google.com" in location, "Should redirect to Google OAuth"
    
    print("\n✅ All OAuth login route tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_oauth_login_route()
        print("\n🎉 OAuth regression fix verified successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)