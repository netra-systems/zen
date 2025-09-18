#!/usr/bin/env python3
'''
'''
End-to-End Test Suite for Docker Compose Authentication Flow
Tests the complete authentication flow in Docker development environment
'''
'''

import json
import time
import requests
import subprocess
import sys
from typing import Dict, Optional, Tuple
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test configuration
BASE_URL_AUTH = "http://localhost:8081"
BASE_URL_FRONTEND = "http://localhost:3001"
BASE_URL_BACKEND = "http://localhost:8001"

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\33[92m' )
    RED = '\33[91m' )
    YELLOW = '\33[93m' )
    BLUE = '\33[94m' )
    RESET = '\33[0m' )
    BOLD = '\33[1m' )

    def print_test_header(test_name: str):
        """Print a formatted test header"""
        print("")
        print("")
        print("")

    def print_result(passed: bool, message: str):
        """Print test result with color"""
        pass
        if passed:
        print("")
        else:
        print("")

    def check_service_health(service_name: str, url: str, endpoint: str = "/health") -> bool:
        """Check if a service is healthy"""
        try:
        response = requests.get("formatted_string", timeout=5)
        return response.status_code == 200
        except Exception as e:
        print("")
        return False

    def test_services_running() -> bool:
        """Test 1: Verify all Docker services are running"""
        print_test_header("Docker Services Health Check")

        services = { }
        "Auth Service": (BASE_URL_AUTH, "/health"),
        "Frontend": (BASE_URL_FRONTEND, "/api/health"),
        "Backend": (BASE_URL_BACKEND, "/health"),
    

        all_healthy = True
        for service_name, (url, endpoint) in services.items():
        healthy = check_service_health(service_name, url, endpoint)
        print_result(healthy, "")
        if not healthy:
        all_healthy = False

        return all_healthy

    def test_auth_config() -> Tuple[bool, Optional[Dict]]:
        """Test 2: Verify auth config endpoint returns correct data"""
        print_test_header("Auth Configuration Check")

        try:
        response = requests.get("formatted_string", timeout=5)
        if response.status_code != 200:
        print_result(False, "")
        return False, None

        config = response.json()

            # Check required fields
        required_fields = ["development_mode", "endpoints", "google_client_id"]
        for field in required_fields:
        if field not in config:
        print_result(False, "")
        return False, None

                    # Check development mode
        dev_mode = config.get("development_mode", False)
        print_result(dev_mode, "")

                    # Check endpoints
        endpoints = config.get("endpoints", {})
        required_endpoints = ["login", "dev_login", "user", "token", "refresh"]
        for endpoint in required_endpoints:
        has_endpoint = endpoint in endpoints
        if has_endpoint:
        print_result(True, "")
        else:
        print_result(False, "")

        return dev_mode, config

        except Exception as e:
        print_result(False, "")
        return False, None

    def test_dev_login(auth_config: Dict) -> Tuple[bool, Optional[str]]:
        """Test 3: Test dev login flow"""
        print_test_header("Dev Login Flow")

        if not auth_config or not auth_config.get("development_mode"):
        print_result(False, "Not in development mode, skipping dev login test")
        return False, None

        dev_login_url = auth_config["endpoints"].get("dev_login")
        if not dev_login_url:
        print_result(False, "No dev_login endpoint in config")
        return False, None

        try:
                # Attempt dev login
        login_data = { }
        "email": "dev@example.com",
        "password": "dev"
                

        print("")
        response = requests.post(dev_login_url, json=login_data, timeout=10)

        if response.status_code != 200:
        print_result(False, "")
        print("")
        return False, None

        data = response.json()

                    # Check response structure
        required_fields = ["access_token", "refresh_token", "user"]
        for field in required_fields:
        if field not in data:
        print_result(False, "")
        return False, None

        token = data["access_token"]
        user = data["user"]

        print_result(True, "")
        print_result(True, "")

        return True, token

        except Exception as e:
        print_result(False, "")
        return False, None

    def test_token_verification(auth_config: Dict, token: str) -> bool:
        """Test 4: Verify the token works"""
        print_test_header("Token Verification")

        if not token:
        print_result(False, "No token to verify")
        return False

        verify_url = auth_config["endpoints"].get("user", "formatted_string")

        try:
        headers = {"Authorization": ""}
        response = requests.get(verify_url, headers=headers, timeout=5)

        if response.status_code == 200:
        user_data = response.json()
        print_result(True, "")
        return True
        else:
        print_result(False, "")
        return False

        except Exception as e:
        print_result(False, "")
        return False

    def test_frontend_redirect_logic() -> bool:
        """Test 5: Test frontend redirect logic"""
        print_test_header("Frontend Redirect Logic")

        try:
        # Test that unauthenticated access redirects to login
        response = requests.get(BASE_URL_FRONTEND, allow_redirects=False, timeout=5)

        # Next.js pages don't do server-side redirects, they do client-side'
        # So we should get a 200 with the page that will redirect
        if response.status_code == 200:
        print_result(True, "Frontend accessible")

            # Check if login page is accessible
        login_response = requests.get("formatted_string", timeout=5)
        if login_response.status_code == 200:
        print_result(True, "Login page accessible")
        return True
        else:
        print_result(False, "")
        return False
        else:
        print_result(False, "")
        return False

        except Exception as e:
        print_result(False, "")
        return False

    def test_cors_headers() -> bool:
        """Test 6: Test CORS configuration"""
        print_test_header("CORS Configuration")

        try:
        # Test preflight request
        headers = { }
        "Origin": BASE_URL_FRONTEND,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type"
        

        response = requests.options( )
        "",
        headers=headers,
        timeout=5
        

        cors_headers = { }
        "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
        "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
        "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
        "Access-Control-Allow-Credentials": response.headers.get("Access-Control-Allow-Credentials")
        

        # Check CORS headers
        has_cors = all([ ])
        cors_headers["Access-Control-Allow-Origin"],
        cors_headers["Access-Control-Allow-Methods"],
        cors_headers["Access-Control-Allow-Headers"]
        

        if has_cors:
        print_result(True, "CORS headers present")
        for header, value in cors_headers.items():
        if value:
        print("")
        return True
        else:
        print_result(False, "Missing CORS headers")
        return False

        except Exception as e:
        print_result(False, "")
        return False

    def test_complete_flow() -> bool:
        """Test 7: Complete authentication flow simulation"""
        print_test_header("Complete Authentication Flow")

        try:
        # Step 1: Get auth config
        print("  Step 1: Getting auth configuration...")
        response = requests.get("formatted_string", timeout=5)
        if response.status_code != 200:
        print_result(False, "Failed to get auth config")
        return False

        auth_config = response.json()
        print_result(True, "Auth config retrieved")

            # Step 2: Perform dev login
        print("  Step 2: Performing dev login...")
        login_response = requests.post( )
        auth_config["endpoints"]["dev_login"],
        json={"email": "dev@example.com", "password": "dev"},
        timeout=10
            

        if login_response.status_code != 200:
        print_result(False, "Dev login failed")
        return False

        login_data = login_response.json()
        token = login_data["access_token"]
        print_result(True, "Dev login successful")

                # Step 3: Verify token
        print("  Step 3: Verifying token...")
        headers = {"Authorization": ""}
        verify_response = requests.get( )
        auth_config["endpoints"]["user"],
        headers=headers,
        timeout=5
                

        if verify_response.status_code != 200:
        print_result(False, "Token verification failed")
        return False

        print_result(True, "Token verified successfully")

                    # Step 4: Test authenticated API call
        print("  Step 4: Testing authenticated API call...")
        api_response = requests.get( )
        "",
        headers=headers,
        timeout=5
                    

                    # Even if this endpoint doesn't exist, we should get 404 not 401'
        if api_response.status_code == 401:
        print_result(False, "Authentication not working with backend")
        return False
        else:
        print_result(True, "")

        return True

        except Exception as e:
        print_result(False, "")
        return False

    def check_docker_logs():
        """Check Docker logs for errors"""
        print_test_header("Docker Logs Analysis")

        containers = ["netra-dev-frontend", "netra-dev-auth", "netra-dev-backend"]

        for container in containers:
        try:
            # Get last 20 lines of logs
        result = subprocess.run( )
        ["docker", "logs", container, "--tail", "20"],
        capture_output=True,
        text=True,
        timeout=5
            

            # Check for error patterns
        error_patterns = ["ERROR", "CRITICAL", "FATAL", "Failed", "refused"]
        errors_found = []

        for line in result.stdout.split(" )"
        ') + result.stderr.split('
        "):"
        for pattern in error_patterns:
        if pattern in line and "No token received" not in line:  # Ignore expected errors
        errors_found.append(line[:100])
        break

        if errors_found:
        print_result(False, "")
        for error in errors_found[:3]:  # Show first 3 errors
        print("")
        else:
        print_result(True, "")

        except Exception as e:
        print("")

    def main():
        """Run all tests"""
        pass
        print("")
        print("")
        print("")

    # Check if services are running
        if not test_services_running():
        print("")
        print("  docker-compose -f docker-compose.dev.yml up -d")
        return 1

        # Run test suite
        test_results = []

        # Test auth config
        dev_mode, auth_config = test_auth_config()
        test_results.append(("Auth Config", dev_mode))

        if auth_config:
            # Test dev login
        login_success, token = test_dev_login(auth_config)
        test_results.append(("Dev Login", login_success))

        if token:
                # Test token verification
        verify_success = test_token_verification(auth_config, token)
        test_results.append(("Token Verification", verify_success))

                # Test frontend redirects
        frontend_success = test_frontend_redirect_logic()
        test_results.append(("Frontend Redirects", frontend_success))

                # Test CORS
        cors_success = test_cors_headers()
        test_results.append(("CORS Configuration", cors_success))

                # Test complete flow
        complete_success = test_complete_flow()
        test_results.append(("Complete Flow", complete_success))

                # Check Docker logs
        check_docker_logs()

                # Print summary
        print("")
        print("")
        print("")

        passed = sum(1 for _, result in test_results if result)
        total = len(test_results)

        for test_name, result in test_results:
        status = "" if result else ""
        print("")

        print("")

        if passed == total:
        print("")
        return 0
        else:
        print("")
        return 1

        if __name__ == "__main__":
        sys.exit(main())

]]]]]]