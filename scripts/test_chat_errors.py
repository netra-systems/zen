"""Test chat interface for errors"""

import requests
import json
from datetime import datetime

def log_error(category, error, details=None):
    """Log an error with timestamp and category"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {category}: {error}")
    if details:
        print(f"  Details: {json.dumps(details, indent=2)}")
    print()

def test_chat_interface():
    """Test the chat interface and log errors"""
    errors_found = []
    
    # Test 1: Frontend availability
    try:
        response = requests.get("http://127.0.0.1:3000/chat", timeout=5)
        if response.status_code != 200:
            error = f"Frontend returned status {response.status_code}"
            log_error("FRONTEND", error)
            errors_found.append(("FRONTEND", error))
        else:
            print("[OK] Frontend is accessible")
    except requests.RequestException as e:
        error = f"Failed to connect to frontend: {e}"
        log_error("FRONTEND", error)
        errors_found.append(("FRONTEND", error))
    
    # Test 2: Backend API availability
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code != 200:
            error = f"Backend health check failed with status {response.status_code}"
            log_error("BACKEND", error)
            errors_found.append(("BACKEND", error))
        else:
            print("[OK] Backend is healthy")
    except requests.RequestException as e:
        error = f"Failed to connect to backend: {e}"
        log_error("BACKEND", error)
        errors_found.append(("BACKEND", error))
    
    # Test 3: Auth service availability
    try:
        response = requests.get("http://127.0.0.1:8081/health", timeout=5)
        if response.status_code != 200:
            error = f"Auth service health check failed with status {response.status_code}"
            log_error("AUTH", error)
            errors_found.append(("AUTH", error))
        else:
            print("[OK] Auth service is healthy")
    except requests.RequestException as e:
        error = f"Failed to connect to auth service: {e}"
        log_error("AUTH", error)
        errors_found.append(("AUTH", error))
    
    # Test 4: Check for authentication requirement on protected endpoints
    try:
        response = requests.get("http://127.0.0.1:8000/api/threads", timeout=5)
        if response.status_code == 401:
            print("[OK] Protected endpoints require authentication (expected)")
        elif response.status_code == 200:
            error = "Protected endpoint accessible without authentication"
            log_error("SECURITY", error)
            errors_found.append(("SECURITY", error))
        else:
            error = f"Unexpected status {response.status_code} from protected endpoint"
            log_error("API", error, {"response": response.text[:500]})
            errors_found.append(("API", error))
    except requests.RequestException as e:
        error = f"Failed to test protected endpoint: {e}"
        log_error("API", error)
        errors_found.append(("API", error))
    
    # Test 5: Check CORS headers
    try:
        response = requests.options(
            "http://127.0.0.1:8000/api/threads",
            headers={"Origin": "http://127.0.0.1:3000"},
            timeout=5
        )
        if "Access-Control-Allow-Origin" not in response.headers:
            error = "CORS headers missing from backend"
            log_error("CORS", error)
            errors_found.append(("CORS", error))
        else:
            print("[OK] CORS headers present")
    except requests.RequestException as e:
        error = f"Failed to test CORS: {e}"
        log_error("CORS", error)
        errors_found.append(("CORS", error))
    
    # Test 6: Check WebSocket endpoint (note: regular HTTP request won't work for WS)
    ws_endpoints = ["/websocket", "/ws", "/api/ws"]
    ws_found = False
    for endpoint in ws_endpoints:
        try:
            response = requests.get(f"http://127.0.0.1:8000{endpoint}", timeout=2)
            # 404 is expected for WebSocket endpoints with regular HTTP
            # 426 (Upgrade Required) would indicate a WebSocket endpoint
            if response.status_code == 426 or "websocket" in response.headers.get("upgrade", "").lower():
                print(f"[OK] WebSocket endpoint found at {endpoint}")
                ws_found = True
                break
        except:
            pass
    
    if not ws_found:
        error = "WebSocket endpoint not detected (may require authentication)"
        log_error("WEBSOCKET", error, {"tested_endpoints": ws_endpoints})
        errors_found.append(("WEBSOCKET", error))
    
    # Summary
    print("\n" + "="*50)
    if errors_found:
        print(f"ERRORS FOUND: {len(errors_found)}")
        print("\nSummary of errors:")
        for category, error in errors_found:
            print(f"  [{category}] {error}")
    else:
        print("No critical errors found!")
        print("Note: WebSocket connections require authentication and cannot be fully tested without credentials")
    
    return errors_found

if __name__ == "__main__":
    test_chat_interface()