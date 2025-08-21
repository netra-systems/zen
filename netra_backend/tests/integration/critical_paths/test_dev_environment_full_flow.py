#!/usr/bin/env python3
"""
Comprehensive test to verify the complete dev environment flow:
1. Dev launcher starts successfully
2. User can log in via auth service
3. WebSocket authenticates properly
4. Data flows correctly through WebSocket connection

This test runs against the actual dev environment to ensure everything works end-to-end.
"""

import asyncio
import json
import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import aiohttp
import websockets
import pytest
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configuration
DEV_BACKEND_URL = "http://localhost:8000"
DEV_FRONTEND_URL = "http://localhost:3000"
DEV_WEBSOCKET_URL = "ws://localhost:8000/websocket"
AUTH_SERVICE_URL = "http://localhost:8081"

# Test credentials
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpassword123"


class DevEnvironmentTester:
    """Test the complete dev environment flow."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.ws_connection = None
        self.launcher_process = None
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        if self.ws_connection:
            await self.ws_connection.close()
        if self.session:
            await self.session.close()
        if self.launcher_process:
            self.launcher_process.terminate()
            
    def start_dev_launcher(self) -> bool:
        """Start the dev launcher and verify it's running."""
        print("\n[LAUNCH] STEP 1: Checking dev environment...")
        
        # First check if services are already running
        try:
            import requests
            response = requests.get(f"{DEV_BACKEND_URL}/api/v1/health", timeout=2)
            if response.status_code == 200:
                print("[OK] Backend service is already running")
                print("[INFO] Using existing dev environment")
                return True
        except:
            print("[INFO] Services not running, starting dev launcher...")
        
        try:
            # Start dev launcher in background
            self.launcher_process = subprocess.Popen(
                [sys.executable, "-m", "dev_launcher", "--no-browser", "--non-interactive"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=project_root
            )
            
            # Wait for services to start (check for specific startup messages)
            start_time = time.time()
            timeout = 60  # 60 seconds timeout
            
            while time.time() - start_time < timeout:
                # Check if launcher is still running
                if self.launcher_process.poll() is not None:
                    stdout, stderr = self.launcher_process.communicate()
                    print(f"[ERROR] Launcher exited unexpectedly")
                    print(f"STDOUT: {stdout}")
                    print(f"STDERR: {stderr}")
                    return False
                    
                # Try to check if services are up
                try:
                    import requests
                    response = requests.get(f"{DEV_BACKEND_URL}/api/v1/health", timeout=1)
                    if response.status_code == 200:
                        print("[OK] Backend service is running")
                        return True
                except:
                    pass
                    
                time.sleep(2)
                
            print("[ERROR] Timeout waiting for services to start")
            return False
            
        except Exception as e:
            print(f"[ERROR] Failed to start dev launcher: {e}")
            return False
            
    async def test_backend_health(self) -> bool:
        """Test that backend health endpoint responds."""
        print("\n[HEALTH] STEP 2: Testing backend health...")
        
        try:
            async with self.session.get(f"{DEV_BACKEND_URL}/api/v1/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[OK] Backend healthy: {data}")
                    return True
                else:
                    print(f"[ERROR] Backend unhealthy: {response.status}")
                    return False
        except Exception as e:
            print(f"[ERROR] Backend health check failed: {e}")
            return False
            
    async def test_auth_service(self) -> bool:
        """Test that auth service is running."""
        print("\n[AUTH] STEP 3: Testing auth service...")
        
        try:
            async with self.session.get(f"{AUTH_SERVICE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[OK] Auth service healthy: {data}")
                    return True
                else:
                    print(f"[ERROR] Auth service unhealthy: {response.status}")
                    return False
        except Exception as e:
            print(f"[ERROR] Auth service check failed: {e}")
            return False
            
    async def register_test_user(self) -> bool:
        """Register a test user."""
        print("\n[USER] STEP 4: Registering test user...")
        
        try:
            register_data = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
                "name": "Test User"
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/register",
                json=register_data
            ) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    print(f"[OK] User registered: {data.get('email')}")
                    return True
                elif response.status == 409:
                    print("[INFO] User already exists (this is fine)")
                    return True
                else:
                    text = await response.text()
                    print(f"[ERROR] Registration failed: {response.status} - {text}")
                    return False
        except Exception as e:
            print(f"[ERROR] Registration error: {e}")
            return False
            
    async def login_user(self) -> bool:
        """Login the test user and get auth token."""
        print("\n[LOGIN] STEP 5: Logging in user...")
        
        try:
            login_data = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/login",
                json=login_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    if self.auth_token:
                        print(f"[OK] Login successful, token: {self.auth_token[:20]}...")
                        return True
                    else:
                        print("[ERROR] No token in response")
                        return False
                else:
                    text = await response.text()
                    print(f"[ERROR] Login failed: {response.status} - {text}")
                    return False
        except Exception as e:
            print(f"[ERROR] Login error: {e}")
            return False
            
    async def test_authenticated_api(self) -> bool:
        """Test an authenticated API endpoint."""
        print("\n[API] STEP 6: Testing authenticated API access...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Try to get user profile
            async with self.session.get(
                f"{DEV_BACKEND_URL}/api/v1/user/profile",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[OK] Authenticated API works: {data}")
                    return True
                elif response.status == 401:
                    print("[ERROR] Authentication failed")
                    return False
                else:
                    text = await response.text()
                    print(f"[ERROR] API call failed: {response.status} - {text}")
                    return False
        except Exception as e:
            print(f"[ERROR] API error: {e}")
            return False
            
    async def test_websocket_connection(self) -> bool:
        """Test WebSocket connection with authentication."""
        print("\n[WS] STEP 7: Testing WebSocket connection...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            # Connect with auth token in headers
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            self.ws_connection = await websockets.connect(
                DEV_WEBSOCKET_URL,
                extra_headers=headers
            )
            
            print("[OK] WebSocket connected")
            
            # Send auth message
            auth_message = {
                "type": "auth",
                "token": self.auth_token
            }
            await self.ws_connection.send(json.dumps(auth_message))
            
            # Wait for auth response
            response = await asyncio.wait_for(
                self.ws_connection.recv(),
                timeout=5.0
            )
            
            data = json.loads(response)
            if data.get("type") == "auth_success":
                print(f"[OK] WebSocket authenticated: {data}")
                return True
            else:
                print(f"[ERROR] WebSocket auth failed: {data}")
                return False
                
        except asyncio.TimeoutError:
            print("[ERROR] WebSocket auth timeout")
            return False
        except Exception as e:
            print(f"[ERROR] WebSocket error: {e}")
            return False
            
    async def test_websocket_data_flow(self) -> bool:
        """Test that data flows properly through WebSocket."""
        print("\n[DATA] STEP 8: Testing WebSocket data flow...")
        
        if not self.ws_connection:
            print("[ERROR] No WebSocket connection")
            return False
            
        try:
            # Send a test message
            test_message = {
                "type": "test_message",
                "content": "Hello from test",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.ws_connection.send(json.dumps(test_message))
            print(f"[SEND] Sent: {test_message}")
            
            # Wait for echo or response
            response = await asyncio.wait_for(
                self.ws_connection.recv(),
                timeout=5.0
            )
            
            data = json.loads(response)
            print(f"[RECV] Received: {data}")
            
            # Verify we got some response
            if data:
                print("[OK] WebSocket data flow works")
                return True
            else:
                print("[ERROR] No data received")
                return False
                
        except asyncio.TimeoutError:
            print("[ERROR] WebSocket data timeout")
            return False
        except Exception as e:
            print(f"[ERROR] WebSocket data error: {e}")
            return False
            
    async def test_thread_creation(self) -> bool:
        """Test creating a thread through WebSocket."""
        print("\n[THREAD] STEP 9: Testing thread creation...")
        
        if not self.ws_connection:
            print("[ERROR] No WebSocket connection")
            return False
            
        try:
            # Create a thread
            create_message = {
                "type": "thread_create",
                "data": {
                    "title": "Test Thread",
                    "description": "Testing thread creation in dev environment"
                }
            }
            
            await self.ws_connection.send(json.dumps(create_message))
            print(f"[CREATE] Creating thread: {create_message}")
            
            # Wait for response
            response = await asyncio.wait_for(
                self.ws_connection.recv(),
                timeout=10.0
            )
            
            data = json.loads(response)
            print(f"[RESPONSE] Thread response: {data}")
            
            if data.get("type") == "thread_created" or data.get("thread_id"):
                print(f"[OK] Thread created successfully: {data.get('thread_id')}")
                return True
            else:
                print(f"[ERROR] Thread creation failed: {data}")
                return False
                
        except asyncio.TimeoutError:
            print("[ERROR] Thread creation timeout")
            return False
        except Exception as e:
            print(f"[ERROR] Thread creation error: {e}")
            return False
            
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests in sequence."""
        results = {}
        
        # Start dev launcher (sync operation)
        results["launcher_start"] = self.start_dev_launcher()
        if not results["launcher_start"]:
            print("\n[CRITICAL] Dev launcher failed to start. Aborting tests.")
            return results
            
        # Give services time to fully initialize
        print("\n[WAIT] Waiting for services to stabilize...")
        await asyncio.sleep(5)
        
        # Run async tests
        results["backend_health"] = await self.test_backend_health()
        results["auth_service"] = await self.test_auth_service()
        results["user_registration"] = await self.register_test_user()
        results["user_login"] = await self.login_user()
        results["authenticated_api"] = await self.test_authenticated_api()
        results["websocket_connection"] = await self.test_websocket_connection()
        results["websocket_data_flow"] = await self.test_websocket_data_flow()
        results["thread_creation"] = await self.test_thread_creation()
        
        return results


@pytest.mark.asyncio
@pytest.mark.integration
async def test_dev_environment_full_flow():
    """Test the complete dev environment flow."""
    async with DevEnvironmentTester() as tester:
        results = await tester.run_all_tests()
        
        # Print summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        for test_name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {test_name:25} : {status}")
            
        print("="*60)
        
        # Calculate overall result
        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n[SUCCESS] All tests passed! Dev environment is fully functional.")
        else:
            print(f"\n[WARNING] {total_tests - passed_tests} tests failed.")
            
        # Assert all tests passed
        assert all(results.values()), f"Some tests failed: {results}"


async def main():
    """Run the test standalone."""
    # Set UTF-8 encoding for Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("="*60)
    print("DEV ENVIRONMENT FULL FLOW TEST")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Backend URL: {DEV_BACKEND_URL}")
    print(f"Auth Service URL: {AUTH_SERVICE_URL}")
    print(f"WebSocket URL: {DEV_WEBSOCKET_URL}")
    print("="*60)
    
    async with DevEnvironmentTester() as tester:
        results = await tester.run_all_tests()
        
        # Return exit code based on results
        if all(results.values()):
            return 0
        else:
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)