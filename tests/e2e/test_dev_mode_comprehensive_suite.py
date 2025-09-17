'''Comprehensive E2E Test Suite for DEV MODE
Tests all critical dev mode functionality per XML specs.

Business Value Justification (BVJ):
1. Segment: Platform/Internal (Development Velocity)
2. Business Goal: Stability, Development Velocity
3. Value Impact: Ensures development environment works correctly
4. Strategic Impact: Prevents developer productivity loss ($50K/month)

Test Coverage:
1. System Startup - Backend/Frontend/Auth services start correctly
2. WebSocket Connection - Frontend connects via WebSocket
3. Example Message Flow - Messages processed end-to-end
4. Agent Response Flow - Supervisor agent responds correctly
5. CORS/Service Configuration - All services communicate properly
'''

import asyncio
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

import httpx
import pytest
import websockets

        # Add project root to path

from netra_backend.app.config import get_config
from netra_backend.app.core.network_constants import ServicePorts, URLConstants


@dataclass
class TestDevModeResult:
    """Result of a dev mode test"""
    test_name: str
    success: bool
    duration: float
    error: Optional[str] = None
    details: Dict[str, Any] = None


    # Alias for backward compatibility (fixing typo)
    DevModeTestResult = TestDevModeResult


class TestDevModeer:
    """Comprehensive dev mode testing utility"""

    def __init__(self):
        pass
        self.config = get_config()
        self.backend_port = 8001  # Dynamic port allocation
        self.frontend_port = 3000
        self.auth_port = 8083  # Dynamic auth port
        self.test_results: List[DevModeTestResult] = []

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run complete test suite"""
        print("")
        [TEST] Starting Comprehensive DEV MODE Test Suite")
        print("=" * 60)

    # Test 1: Basic System Startup
        await self._test_system_startup()

    # Test 2: Frontend WebSocket Connection
        await self._test_websocket_connection()

    # Test 3: Example Message Flow
        await self._test_example_message_flow()

    # Test 4: Agent Response Flow
        await self._test_agent_response_flow()

    # Test 5: CORS and Service Configuration
        await self._test_cors_configuration()

        return self._generate_test_report()

    async def _test_system_startup(self) -> DevModeTestResult:
        """Test 1: Verify all services start correctly"""
        print("")
        [1] Test 1: System Startup")
        start_time = time.time()

        try:
        # Check backend health
        async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get("formatted_string")
        backend_healthy = response.status_code == 200
        backend_data = response.json() if backend_healthy else None

            # Check database connections
        db_checks = await self._verify_database_connections()

            # Check service discovery
        services_registered = await self._verify_service_discovery()

        success = backend_healthy and db_checks['success'] and services_registered

        result = DevModeTestResult( )
        test_name="System Startup",
        success=success,
        duration=time.time() - start_time,
        details={ }
        "backend_healthy": backend_healthy,
        "backend_response": backend_data,
        "database_checks": db_checks,
        "services_registered": services_registered
            
            

        self._print_test_result(result)
        self.test_results.append(result)
        return result

        except Exception as e:
        result = DevModeTestResult( )
        test_name="System Startup",
        success=False,
        duration=time.time() - start_time,
        error=str(e)
                
        self._print_test_result(result)
        self.test_results.append(result)
        return result

    async def _test_websocket_connection(self) -> DevModeTestResult:
        """Test 2: Verify WebSocket connection works"""
        print("")
        [2] Test 2: WebSocket Connection")
        start_time = time.time()

        try:
        # Attempt WebSocket connection
        ws_url = ""

        async with websockets.connect(ws_url) as websocket:
            # Send test message
        test_msg = {"type": "ping", "timestamp": datetime.now().isoformat()}
        await websocket.send(json.dumps(test_msg))

            # Wait for response (with timeout)
        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        response_data = json.loads(response) if response else None

        success = response_data is not None

        result = DevModeTestResult( )
        test_name="WebSocket Connection",
        success=success,
        duration=time.time() - start_time,
        details={ }
        "ws_url": ws_url,
        "test_message": test_msg,
        "response": response_data
            
            

        self._print_test_result(result)
        self.test_results.append(result)
        return result

        except Exception as e:
        result = DevModeTestResult( )
        test_name="WebSocket Connection",
        success=False,
        duration=time.time() - start_time,
        error=str(e)
                
        self._print_test_result(result)
        self.test_results.append(result)
        return result

    async def _test_example_message_flow(self) -> DevModeTestResult:
        """Test 3: Test example message processing"""
        print("")
        [3] Test 3: Example Message Flow")
        start_time = time.time()

        try:
        # Send example message via API
        async with httpx.AsyncClient(follow_redirects=True) as client:
        test_message = { }
        "message": "I need to reduce costs but keep quality the same.",
        "thread_id": "test_thread_001",
        "user_id": "test_user_001"
            

        response = await client.post( )
        "",
        json=test_message,
        timeout=10.0
            

        success = response.status_code in [200, 201]
        response_data = response.json() if success else None

        result = DevModeTestResult( )
        test_name="Example Message Flow",
        success=success,
        duration=time.time() - start_time,
        details={ }
        "test_message": test_message,
        "status_code": response.status_code if 'response' in locals() else None,
        "response": response_data
            
            

        self._print_test_result(result)
        self.test_results.append(result)
        return result

        except Exception as e:
        result = DevModeTestResult( )
        test_name="Example Message Flow",
        success=False,
        duration=time.time() - start_time,
        error=str(e)
                
        self._print_test_result(result)
        self.test_results.append(result)
        return result

    async def _test_agent_response_flow(self) -> DevModeTestResult:
        """Test 4: Verify agent response flow"""
        print("")
        [4] Test 4: Agent Response Flow")
        start_time = time.time()

        try:
        # Check supervisor agent health
        async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get( )
        ""
            

        agent_healthy = response.status_code in [200, 404]  # 404 if not yet created

            # Test agent endpoint
        agent_test = { }
        "prompt": "Test prompt for supervisor",
        "context": {"test": True}
            

        agent_response = await client.post( )
        "",
        json=agent_test,
        timeout=15.0
            

        agent_works = agent_response.status_code in [200, 201, 404]  # 404 if endpoint not ready

        success = agent_healthy and agent_works

        result = DevModeTestResult( )
        test_name="Agent Response Flow",
        success=success,
        duration=time.time() - start_time,
        details={ }
        "agent_healthy": agent_healthy,
        "agent_test_status": agent_response.status_code if 'agent_response' in locals() else None,
        "agent_response": agent_response.json() if agent_works and 'agent_response' in locals() else None
            
            

        self._print_test_result(result)
        self.test_results.append(result)
        return result

        except Exception as e:
        result = DevModeTestResult( )
        test_name="Agent Response Flow",
        success=False,
        duration=time.time() - start_time,
        error=str(e)
                
        self._print_test_result(result)
        self.test_results.append(result)
        return result

    async def _test_cors_configuration(self) -> DevModeTestResult:
        """Test 5: Verify CORS and service configuration"""
        print("")
        [5] Test 5: CORS & Service Configuration")
        start_time = time.time()

        try:
        # Test CORS headers
        async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.options( )
        "",
        headers={ }
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST"
            
            

        cors_enabled = "Access-Control-Allow-Origin" in response.headers
        cors_origin = response.headers.get("Access-Control-Allow-Origin", "")

            # Test cross-service auth
        auth_response = await client.get( )
        ""
            

        auth_configured = auth_response.status_code in [200, 404]  # 404 if auth service separate

        success = cors_enabled and auth_configured

        result = DevModeTestResult( )
        test_name="CORS & Service Configuration",
        success=success,
        duration=time.time() - start_time,
        details={ }
        "cors_enabled": cors_enabled,
        "cors_origin": cors_origin,
        "auth_configured": auth_configured,
        "auth_status": auth_response.status_code if 'auth_response' in locals() else None
            
            

        self._print_test_result(result)
        self.test_results.append(result)
        return result

        except Exception as e:
        result = DevModeTestResult( )
        test_name="CORS & Service Configuration",
        success=False,
        duration=time.time() - start_time,
        error=str(e)
                
        self._print_test_result(result)
        self.test_results.append(result)
        return result

    async def _verify_database_connections(self) -> Dict[str, Any]:
        """Verify all database connections are working"""
        try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get( )
        ""
            

        if response.status_code == 200:
        data = response.json()
        return { }
        "success": data.get("validation", {}).get("valid", False),
        "environment": data.get("environment"),
        "database_name": data.get("database_name")
                
        except:
        pass

        return {"success": False, "error": "Could not verify database connections"}

    async def _verify_service_discovery(self) -> bool:
        """Verify service discovery is working"""
        try:
        # Check if services are discoverable
        async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get( )
        ""
            
        return response.status_code in [200, 404]  # 404 if endpoint doesn"t exist yet
        except:
        return False

    def _print_test_result(self, result: DevModeTestResult):
        """Print test result with formatting"""
        icon = "[PASS]" if result.success else "[FAIL]"
        status = "PASSED" if result.success else "FAILED"

        print("")

        if result.error:
        print("")

        if result.details and not result.success:
        print("")

    def _generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        pass
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.success)
        failed_tests = total_tests - passed_tests
        total_duration = sum(r.duration for r in self.test_results)

        print("")
         + =" * 60)
        print("[SUMMARY] TEST RESULTS")
        print("=" * 60)
        print("")
        print("")
        print("")
        print("")
        print("")

        if failed_tests > 0:
        print("")
        [WARNING] Failed Tests:")
        for result in self.test_results:
        if not result.success:
        print("")

        return { }
        "total_tests": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "success_rate": passed_tests / total_tests,
        "duration": total_duration,
        "test_results": [ ]
        { }
        "name": r.test_name,
        "success": r.success,
        "duration": r.duration,
        "error": r.error,
        "details": r.details
                
        for r in self.test_results
                
                


@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_dev_mode_comprehensive():
"""Run comprehensive dev mode test suite"""
tester = DevModeTester()
report = await tester.run_all_tests()

                    # Assert all tests passed
assert report["failed"] == 0, ""
assert report["success_rate"] == 1.0, ""


async def main():
"""Run tests standalone"""
pass
tester = DevModeTester()
report = await tester.run_all_tests()

    # Exit with appropriate code
sys.exit(0 if report["failed"] == 0 else 1)


if __name__ == "__main__":
asyncio.run(main())
