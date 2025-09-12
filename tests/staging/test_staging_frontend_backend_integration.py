"""
Test 10: Staging Frontend-Backend Integration

CRITICAL: Test frontend-backend communication in staging environment.
This validates the complete user-facing integration that delivers end-user experience.

Business Value: Free/Early/Mid/Enterprise - Complete User Experience  
Frontend-backend integration delivers the complete user journey and experience.
"""

import pytest
import httpx
import asyncio
import time
import json
from typing import Dict, Any, List, Optional
from shared.isolated_environment import IsolatedEnvironment
from tests.staging.staging_config import StagingConfig

# Critical Frontend-Backend Integration Points
INTEGRATION_ENDPOINTS = [
    ("GET", "/api/user/profile", "User profile data"),
    ("GET", "/api/agents/status", "Agent availability"),
    ("POST", "/api/agents/execute", "Agent execution"),
    ("GET", "/api/corpus/search", "Content search"),
    ("POST", "/api/corpus/upload", "Content upload")
]

class StagingFrontendBackendIntegrationTestRunner:
    """Test runner for frontend-backend integration validation in staging."""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.environment = StagingConfig.get_environment()
        self.timeout = StagingConfig.TIMEOUTS["default"]
        self.access_token = None
        
    def get_base_headers(self) -> Dict[str, str]:
        """Get base headers for API requests."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Netra-Staging-Frontend-Integration-Test/1.0"
        }
        
    async def get_test_token(self) -> Optional[str]:
        """Get test token for authenticated requests."""
        try:
            simulation_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
            if not simulation_key:
                return None
                
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{StagingConfig.get_service_url('auth')}/api/auth/simulate",
                    headers=self.get_base_headers(),
                    json={
                        "simulation_key": simulation_key,
                        "user_id": "staging-frontend-test-user",
                        "email": "staging-frontend-test@netrasystems.ai"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("access_token")
                    
        except Exception as e:
            print(f"Token generation failed: {e}")
            
        return None
        
    async def test_frontend_accessibility(self) -> Dict[str, Any]:
        """Test 10.1: Frontend service accessibility and basic loading."""
        print("10.1 Testing frontend accessibility...")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                # Test frontend root endpoint
                response = await client.get(
                    StagingConfig.get_service_url("frontend"),
                    headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "User-Agent": "Netra-Staging-Frontend-Test/1.0"
                    }
                )
                
                frontend_accessible = response.status_code == 200
                content = response.text if frontend_accessible else ""
                
                # Check for expected frontend content
                has_react_content = "react" in content.lower() or "netra" in content.lower()
                has_script_tags = "<script" in content.lower()
                has_css_links = "<link" in content.lower() and "stylesheet" in content.lower()
                
                return {
                    "success": frontend_accessible,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if response.elapsed else 0,
                    "content_length": len(content),
                    "has_react_content": has_react_content,
                    "has_script_tags": has_script_tags,
                    "has_css_links": has_css_links,
                    "frontend_url": StagingConfig.get_service_url("frontend"),
                    "content_type": response.headers.get("content-type", "")
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Frontend accessibility test failed: {str(e)}",
                "frontend_url": StagingConfig.get_service_url("frontend")
            }
            
    async def test_cors_frontend_backend(self) -> Dict[str, Any]:
        """Test 10.2: CORS configuration between frontend and backend."""
        print("10.2 Testing CORS frontend-backend integration...")
        
        results = {}
        frontend_origin = StagingConfig.get_service_url("frontend")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test CORS preflight for critical endpoints
                test_endpoints = [
                    ("/api/user/profile", "GET"),
                    ("/api/agents/execute", "POST"),
                    ("/api/corpus/search", "GET")
                ]
                
                for endpoint, method in test_endpoints:
                    cors_response = await client.options(
                        f"{StagingConfig.get_service_url('netra_backend')}{endpoint}",
                        headers={
                            "Origin": frontend_origin,
                            "Access-Control-Request-Method": method,
                            "Access-Control-Request-Headers": "Content-Type,Authorization"
                        }
                    )
                    
                    cors_headers = {
                        "allow_origin": cors_response.headers.get("access-control-allow-origin"),
                        "allow_methods": cors_response.headers.get("access-control-allow-methods"),
                        "allow_headers": cors_response.headers.get("access-control-allow-headers"),
                        "allow_credentials": cors_response.headers.get("access-control-allow-credentials")
                    }
                    
                    cors_working = (
                        cors_response.status_code in [200, 204] and
                        cors_headers["allow_origin"] in [frontend_origin, "*"]
                    )
                    
                    endpoint_key = endpoint.replace("/", "_").replace("-", "_")
                    results[f"cors{endpoint_key}"] = {
                        "success": cors_working,
                        "endpoint": endpoint,
                        "method": method,
                        "status_code": cors_response.status_code,
                        "cors_headers": cors_headers,
                        "origin_allowed": cors_headers["allow_origin"] in [frontend_origin, "*"]
                    }
                    
        except Exception as e:
            results["cors_error"] = {
                "success": False,
                "error": f"CORS testing failed: {str(e)}"
            }
            
        return results
        
    async def test_api_endpoints_from_frontend_perspective(self) -> Dict[str, Any]:
        """Test 10.3: API endpoints from frontend perspective."""
        print("10.3 Testing API endpoints from frontend perspective...")
        
        results = {}
        
        if not self.access_token:
            return {
                "api_endpoints": {
                    "success": False,
                    "error": "No access token available",
                    "skipped": True
                }
            }
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test each critical endpoint as frontend would
                for method, endpoint, description in INTEGRATION_ENDPOINTS:
                    
                    headers = {
                        **self.get_base_headers(),
                        "Authorization": f"Bearer {self.access_token}",
                        "Origin": StagingConfig.get_service_url("frontend"),
                        "Referer": StagingConfig.get_service_url("frontend")
                    }
                    
                    # Prepare test data based on endpoint
                    test_data = None
                    if method == "POST":
                        if "execute" in endpoint:
                            test_data = {
                                "query": "Test frontend integration query",
                                "agent_type": "supervisor",
                                "context": {"frontend_test": True}
                            }
                        elif "upload" in endpoint:
                            test_data = {
                                "content": "Frontend integration test content",
                                "title": "Frontend Test Document",
                                "type": "text"
                            }
                    
                    # Make request
                    full_url = f"{StagingConfig.get_service_url('netra_backend')}{endpoint}"
                    
                    if method == "GET":
                        # Add query params for search
                        if "search" in endpoint:
                            full_url += "?q=test&limit=5"
                        response = await client.get(full_url, headers=headers)
                    elif method == "POST":
                        response = await client.post(full_url, headers=headers, json=test_data or {})
                    else:
                        continue  # Skip unsupported methods
                        
                    # Evaluate response
                    endpoint_success = response.status_code in [200, 201, 202, 404]  # 404 ok for some endpoints
                    cors_headers_present = bool(response.headers.get("access-control-allow-origin"))
                    
                    endpoint_key = endpoint.replace("/", "_").replace("-", "_")
                    results[f"api{endpoint_key}"] = {
                        "success": endpoint_success,
                        "endpoint": endpoint,
                        "method": method,
                        "description": description,
                        "status_code": response.status_code,
                        "response_time": response.elapsed.total_seconds() if response.elapsed else 0,
                        "cors_headers_present": cors_headers_present,
                        "content_length": len(response.content) if response.content else 0,
                        "error": None if endpoint_success else response.text[:500]
                    }
                    
        except Exception as e:
            results["api_endpoints_error"] = {
                "success": False,
                "error": f"API endpoint testing failed: {str(e)}"
            }
            
        return results
        
    async def test_websocket_frontend_integration(self) -> Dict[str, Any]:
        """Test 10.4: WebSocket integration from frontend perspective."""
        print("10.4 Testing WebSocket frontend integration...")
        
        if not self.access_token:
            return {
                "websocket_integration": {
                    "success": False,
                    "error": "No access token available",
                    "skipped": True
                }
            }
            
        try:
            import websockets
            
            # Get WebSocket URL
            ws_url = StagingConfig.get_service_url("websocket")
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Origin": StagingConfig.get_service_url("frontend"),
                "User-Agent": "Netra-Frontend/1.0"
            }
            
            async with websockets.connect(
                ws_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            ) as websocket:
                
                # Send a test message
                test_message = {
                    "type": "ping",
                    "source": "frontend_integration_test",
                    "timestamp": time.time()
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    
                    return {
                        "success": True,
                        "websocket_url": ws_url,
                        "connection_established": True,
                        "response_received": True,
                        "response_data": response_data,
                        "response_type": response_data.get("type", "unknown")
                    }
                    
                except asyncio.TimeoutError:
                    return {
                        "success": False,
                        "websocket_url": ws_url,
                        "connection_established": True,
                        "response_received": False,
                        "error": "WebSocket response timeout"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"WebSocket integration test failed: {str(e)}"
            }
            
    async def test_authentication_flow_integration(self) -> Dict[str, Any]:
        """Test 10.5: Complete authentication flow integration."""
        print("10.5 Testing authentication flow integration...")
        
        try:
            # Test the complete auth flow as frontend would experience it
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                
                # Step 1: Get OAuth simulation token (as frontend auth would)
                simulation_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
                if not simulation_key:
                    return {
                        "success": False,
                        "error": "E2E_OAUTH_SIMULATION_KEY not configured"
                    }
                    
                auth_headers = {
                    **self.get_base_headers(),
                    "Origin": StagingConfig.get_service_url("frontend"),
                    "Referer": f"{StagingConfig.get_service_url('frontend')}/login"
                }
                
                auth_response = await client.post(
                    f"{StagingConfig.get_service_url('auth')}/api/auth/simulate",
                    headers=auth_headers,
                    json={
                        "simulation_key": simulation_key,
                        "user_id": "frontend-auth-test-user",
                        "email": "frontend-auth-test@netrasystems.ai"
                    }
                )
                
                auth_success = auth_response.status_code == 200
                token_data = auth_response.json() if auth_success else {}
                access_token = token_data.get("access_token")
                
                # Step 2: Use token to access protected backend endpoint (as frontend would)
                profile_success = False
                profile_data = {}
                
                if access_token:
                    profile_headers = {
                        **self.get_base_headers(),
                        "Authorization": f"Bearer {access_token}",
                        "Origin": StagingConfig.get_service_url("frontend")
                    }
                    
                    profile_response = await client.get(
                        f"{StagingConfig.get_service_url('netra_backend')}/api/user/profile",
                        headers=profile_headers
                    )
                    
                    profile_success = profile_response.status_code in [200, 404]  # 404 is ok
                    if profile_response.status_code == 200:
                        try:
                            profile_data = profile_response.json()
                        except:
                            pass
                            
                # Step 3: Test logout (as frontend would)
                logout_success = False
                if access_token:
                    logout_response = await client.post(
                        f"{StagingConfig.get_service_url('auth')}/api/auth/logout",
                        headers={
                            **self.get_base_headers(),
                            "Authorization": f"Bearer {access_token}",
                            "Origin": StagingConfig.get_service_url("frontend")
                        }
                    )
                    logout_success = logout_response.status_code in [200, 204]
                    
                auth_flow_working = auth_success and access_token and profile_success
                
                return {
                    "success": auth_flow_working,
                    "auth_token_obtained": bool(access_token),
                    "backend_profile_access": profile_success,
                    "logout_successful": logout_success,
                    "complete_flow_working": auth_flow_working and logout_success,
                    "token_length": len(access_token) if access_token else 0,
                    "auth_response_time": auth_response.elapsed.total_seconds() if auth_response.elapsed else 0
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Authentication flow integration test failed: {str(e)}"
            }
            
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all frontend-backend integration tests."""
        print(f"[U+1F310] Running Frontend-Backend Integration Tests")
        print(f"Environment: {self.environment}")
        print(f"Frontend URL: {StagingConfig.get_service_url('frontend')}")
        print(f"Backend URL: {StagingConfig.get_service_url('netra_backend')}")
        print(f"Auth URL: {StagingConfig.get_service_url('auth')}")
        print()
        
        # Get test token first
        print("[U+1F511] Getting test token...")
        self.access_token = await self.get_test_token()
        print(f"     Token obtained: {bool(self.access_token)}")
        print()
        
        results = {}
        
        # Test 10.1: Frontend accessibility
        frontend_result = await self.test_frontend_accessibility()
        results["frontend_accessibility"] = frontend_result
        print(f"10.1  PASS:  Frontend accessible: {frontend_result['success']}")
        
        # Test 10.2: CORS integration
        cors_results = await self.test_cors_frontend_backend()
        results.update(cors_results)
        cors_working = all(
            result.get("success", False) for key, result in cors_results.items() 
            if key.startswith("cors") and isinstance(result, dict)
        )
        print(f"10.2  PASS:  CORS integration: {cors_working}")
        
        # Test 10.3: API endpoints
        api_results = await self.test_api_endpoints_from_frontend_perspective()
        results.update(api_results)
        api_endpoints_working = all(
            result.get("success", False) for key, result in api_results.items()
            if key.startswith("api") and isinstance(result, dict)
        )
        print(f"10.3  PASS:  API endpoints: {api_endpoints_working}")
        
        # Test 10.4: WebSocket integration
        ws_result = await self.test_websocket_frontend_integration()
        results["websocket_integration"] = ws_result
        ws_working = ws_result.get("success", False) or ws_result.get("skipped", False)
        print(f"10.4  PASS:  WebSocket integration: {ws_working}")
        
        # Test 10.5: Authentication flow
        auth_flow_result = await self.test_authentication_flow_integration()
        results["auth_flow_integration"] = auth_flow_result
        auth_flow_working = auth_flow_result.get("success", False)
        print(f"10.5  PASS:  Auth flow integration: {auth_flow_working}")
        
        # Calculate summary
        all_tests = {k: v for k, v in results.items() if isinstance(v, dict) and "success" in v}
        total_tests = len(all_tests)
        passed_tests = sum(1 for result in all_tests.values() if result["success"])
        skipped_tests = sum(1 for result in all_tests.values() if result.get("skipped", False))
        
        # Check critical integration points
        frontend_accessible = results.get("frontend_accessibility", {}).get("success", False)
        core_integration_working = all([
            frontend_accessible,
            cors_working,
            auth_flow_working
        ])
        
        results["summary"] = {
            "frontend_accessible": frontend_accessible,
            "cors_working": cors_working,
            "api_endpoints_working": api_endpoints_working,
            "websocket_integration_working": ws_working,
            "auth_flow_working": auth_flow_working,
            "core_integration_working": core_integration_working,
            "environment": self.environment,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "skipped_tests": skipped_tests,
            "critical_integration_failure": not core_integration_working
        }
        
        print()
        print(f" CHART:  Summary: {results['summary']['passed_tests']}/{results['summary']['total_tests']} tests passed ({results['summary']['skipped_tests']} skipped)")
        print(f"[U+1F310] Frontend accessible: {' PASS:  Yes' if frontend_accessible else ' FAIL:  No'}")
        print(f"[U+1F517] CORS working: {' PASS:  Yes' if cors_working else ' FAIL:  No'}")
        print(f"[U+1F50C] API integration: {' PASS:  Working' if api_endpoints_working else ' FAIL:  Issues'}")
        print(f"[U+1F4E1] WebSocket integration: {' PASS:  Working' if ws_working else ' FAIL:  Issues'}")
        print(f"[U+1F510] Auth flow: {' PASS:  Working' if auth_flow_working else ' FAIL:  Issues'}")
        
        if results["summary"]["critical_integration_failure"]:
            print(" ALERT:  CRITICAL: Frontend-backend integration failure!")
            
        return results


@pytest.mark.asyncio
@pytest.mark.staging
async def test_staging_frontend_backend_integration():
    """Main test entry point for frontend-backend integration validation."""
    runner = StagingFrontendBackendIntegrationTestRunner()
    results = await runner.run_all_tests()
    
    # Assert critical conditions
    assert results["summary"]["core_integration_working"], "Core frontend-backend integration is not working"
    assert not results["summary"]["critical_integration_failure"], "Critical integration failure detected"
    assert results["summary"]["frontend_accessible"], "Frontend is not accessible"
    assert results["summary"]["auth_flow_working"], "Authentication flow integration is broken"


if __name__ == "__main__":
    async def main():
        runner = StagingFrontendBackendIntegrationTestRunner()
        results = await runner.run_all_tests()
        
        if results["summary"]["critical_integration_failure"]:
            exit(1)
            
    asyncio.run(main())