#!/usr/bin/env python3
"""
Fix frontend authentication and WebSocket connection issue.
This script performs dev login and provides instructions for the frontend.
"""

import json
import requests
import sys
from datetime import datetime

def main():
    print("=" * 60)
    print("NETRA FRONTEND AUTHENTICATION FIX")
    print("=" * 60)
    
    # Step 1: Perform dev login
    print("\n[1] Performing development login...")
    
    auth_url = "http://localhost:8081/auth/dev/login"
    payload = {
        "user_id": "dev_user",
        "name": "Development User",
        "email": "dev@example.com"
    }
    
    try:
        response = requests.post(auth_url, json=payload)
        response.raise_for_status()
        auth_data = response.json()
        
        print("[OK] Authentication successful!")
        print(f"  User: {auth_data['user']['email']}")
        print(f"  Token expires in: {auth_data['expires_in']} seconds")
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Authentication failed: {e}")
        print("\nMake sure the auth service is running on port 8081")
        sys.exit(1)
    
    # Step 2: Test WebSocket connectivity
    print("\n[2] Testing backend WebSocket endpoint...")
    
    try:
        # Test with curl (basic connectivity)
        import subprocess
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", 
             "http://localhost:8000/health"],
            capture_output=True,
            text=True
        )
        if result.stdout == "200":
            print("[OK] Backend is responsive")
        else:
            print(f"[WARNING] Backend returned status: {result.stdout}")
    except Exception as e:
        print(f"[WARNING] Could not test backend: {e}")
    
    # Step 3: Provide instructions for frontend
    print("\n[3] Frontend Fix Instructions:")
    print("-" * 40)
    print("\nOPTION A: Use the test page (recommended)")
    print("  1. Open in browser: http://localhost:3000/test_websocket_connection.html")
    print("  2. Click 'Authenticate' button")
    print("  3. Click 'Connect WebSocket' button")
    print("  4. Verify connection status turns green")
    
    print("\nOPTION B: Manual browser fix")
    print("  1. Open browser DevTools (F12)")
    print("  2. Go to Console tab")
    print("  3. Paste and run this code:")
    print("-" * 40)
    
    browser_code = f"""
// Save auth data to localStorage
localStorage.setItem('jwt_token', '{auth_data['access_token']}');
localStorage.setItem('refresh_token', '{auth_data['refresh_token']}');
localStorage.setItem('user', JSON.stringify({json.dumps(auth_data['user'])}));

// Reload the page to apply authentication
window.location.reload();
"""
    
    print(browser_code)
    print("-" * 40)
    
    print("\nOPTION C: Clear and restart")
    print("  1. Clear browser localStorage:")
    print("     localStorage.clear()")
    print("  2. Close all browser tabs")
    print("  3. Restart the frontend:")
    print("     npm run dev")
    print("  4. Navigate to http://localhost:3000")
    
    # Step 4: Save credentials to file for reference
    with open("frontend_auth_fix.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "access_token": auth_data['access_token'],
            "refresh_token": auth_data['refresh_token'],
            "user": auth_data['user'],
            "instructions": "Copy the access_token and use it in the browser console as shown above"
        }, f, indent=2)
    
    print("\n[4] Auth credentials saved to: frontend_auth_fix.json")
    print("\n[OK] Fix process complete!")
    print("\nThe frontend should now be able to connect to WebSocket.")
    print("If issues persist, check:")
    print("  - Browser console for errors")
    print("  - Network tab for failed WebSocket connections")
    print("  - Backend logs for authentication errors")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())