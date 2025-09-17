#!/usr/bin/env python3
'''
Frontend Integration Tests with Auth Service
Test the complete authentication flow from frontend perspective
'''

import asyncio
import httpx
import json
import sys
from typing import Dict, Any

# Service URLs
AUTH_SERVICE_URL = "https://netra-auth-service-701982941522.us-central1.run.app"
FRONTEND_URL = "https://app.staging.netrasystems.ai"

class FrontendIntegrationTester:
    def __init__(self):
        self.results = []
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=False)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def log_result(self, test_name: str, success: bool, details: str, response_data: Dict = None):
        result = { )
        "test": test_name,
        "success": success,
        "details": details,
        "response_data": response_data or {}
    
        self.results.append(result)
        status = "PASS" if success else "FAIL"
        print("formatted_string")

    async def test_frontend_auth_config_endpoint(self):
        """Test frontend can fetch auth configuration"""
        try:
            # This endpoint should provide frontend with OAuth configuration
        response = await self.client.get("formatted_string")

        if response.status_code == 200:
        config = response.json()
        required_fields = ["client_id", "auth_url", "scopes"]
        missing_fields = [item for item in []]

        if not missing_fields:
        self.log_result( )
        "Frontend Auth Config",
        True,
        f"Auth config endpoint working with all required fields",
        config
                    
        else:
        self.log_result( )
        "Frontend Auth Config",
        False,
        "formatted_string",
        config
                        
        elif response.status_code == 404:
        self.log_result( )
        "Frontend Auth Config",
        False,
        "Auth config endpoint not implemented",
        {"status_code": response.status_code}
                            
        else:
        self.log_result( )
        "Frontend Auth Config",
        False,
        "formatted_string",
        {"status_code": response.status_code, "response": response.text}
                                
        except Exception as e:
        self.log_result("Frontend Auth Config", False, "formatted_string")

    async def test_oauth_flow_complete_simulation(self):
        """Simulate complete OAuth flow as frontend would do it"""
        try:
                                            # Step 1: Frontend initiates OAuth flow
        oauth_response = await self.client.get( )
        "formatted_string",
        params={"return_url": "formatted_string"},
        headers={"Origin": FRONTEND_URL}
                                            

        if oauth_response.status_code == 302:
        location = oauth_response.headers.get("location", "")
        if "accounts.google.com" in location:
                                                    Extract state from the OAuth URL for callback simulation
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(location)
        query_params = parse_qs(parsed.query)
        state = query_params.get("state", [""])[0]

        self.log_result( )
        "OAuth Initiation",
        True,
        "OAuth flow initiated successfully",
        {"redirect_location": location, "state": state}
                                                    

                                                    Step 2: Simulate callback (this would normally come from Google)
                                                    # Note: This will fail with actual validation, but tests the endpoint
        callback_response = await self.client.get( )
        "formatted_string",
        params={ )
        "code": "test_authorization_code",
        "state": state
        },
        headers={"Origin": FRONTEND_URL}
                                                    

                                                    # We expect this to fail with real validation, but should not crash
        if callback_response.status_code in [400, 401, 422]:
        self.log_result( )
        "OAuth Callback Handling",
        True,
        "formatted_string",
        {"status_code": callback_response.status_code}
                                                        
        else:
        self.log_result( )
        "OAuth Callback Handling",
        False,
        "formatted_string",
        {"status_code": callback_response.status_code, "text": callback_response.text[:200]}
                                                            
        else:
        self.log_result( )
        "OAuth Initiation",
        False,
        "formatted_string"
                                                                
        else:
        self.log_result( )
        "OAuth Initiation",
        False,
        "formatted_string"
                                                                    
        except Exception as e:
        self.log_result("OAuth Flow Simulation", False, "formatted_string")

    async def test_websocket_auth_compatibility(self):
        """Test WebSocket authentication endpoint compatibility"""
        try:
                                                                                # Test WebSocket auth endpoint (if exists)
        ws_auth_response = await self.client.get("formatted_string")

        if ws_auth_response.status_code == 401:
        self.log_result( )
        "WebSocket Auth Compatibility",
        True,
        "WebSocket auth endpoint correctly requires authentication",
        {"status_code": ws_auth_response.status_code}
                                                                                    
        elif ws_auth_response.status_code == 404:
                                                                                        # Check alternative WebSocket endpoints
        alt_response = await self.client.get("formatted_string")
        if alt_response.status_code in [401, 422]:
        self.log_result( )
        "WebSocket Auth Compatibility",
        True,
        "Alternative WebSocket auth endpoint found and secured",
        {"status_code": alt_response.status_code}
                                                                                            
        else:
        self.log_result( )
        "WebSocket Auth Compatibility",
        False,
        "No WebSocket auth endpoint found",
        {"main_status": ws_auth_response.status_code, "alt_status": alt_response.status_code}
                                                                                                
        else:
        self.log_result( )
        "WebSocket Auth Compatibility",
        False,
        "formatted_string",
        {"status_code": ws_auth_response.status_code}
                                                                                                    
        except Exception as e:
        self.log_result("WebSocket Auth Compatibility", False, "formatted_string")

    async def test_rate_limiting(self):
        """Test rate limiting on auth endpoints"""
        try:
                                                                                                                # Make multiple rapid requests to test rate limiting
        responses = []
        for i in range(5):
        response = await self.client.get( )
        "formatted_string",
        params={"return_url": "formatted_string"}
                                                                                                                    
        responses.append(response.status_code)

                                                                                                                    # Check if any requests were rate limited
        rate_limited = any(status == 429 for status in responses)
        all_successful = all(status == 302 for status in responses)

        if all_successful:
        self.log_result( )
        "Rate Limiting",
        True,
        "No rate limiting detected (acceptable for staging)",
        {"responses": responses}
                                                                                                                        
        elif rate_limited:
        self.log_result( )
        "Rate Limiting",
        True,
        "Rate limiting is active and working",
        {"responses": responses}
                                                                                                                            
        else:
        self.log_result( )
        "Rate Limiting",
        False,
        "formatted_string",
        {"responses": responses}
                                                                                                                                
        except Exception as e:
        self.log_result("Rate Limiting", False, "formatted_string")

    async def test_error_handling(self):
        """Test error handling for malformed requests"""
        try:
                                                                                                                                            # Test malformed OAuth request
        error_response = await self.client.get( )
        "formatted_string",
        params={"malformed": "parameter"}
                                                                                                                                            

        if error_response.status_code in [400, 422]:
        self.log_result( )
        "Error Handling - Malformed OAuth",
        True,
        "formatted_string",
        {"status_code": error_response.status_code}
                                                                                                                                                
        elif error_response.status_code == 302:
                                                                                                                                                    # Service might have default behavior - check if redirect is sensible
        location = error_response.headers.get("location", "")
        if "accounts.google.com" in location:
        self.log_result( )
        "Error Handling - Malformed OAuth",
        True,
        "Service provides default OAuth behavior for malformed requests",
        {"status_code": error_response.status_code, "location": location}
                                                                                                                                                        
        else:
        self.log_result( )
        "Error Handling - Malformed OAuth",
        False,
        "formatted_string",
        {"location": location}
                                                                                                                                                            
        else:
        self.log_result( )
        "Error Handling - Malformed OAuth",
        False,
        "formatted_string",
        {"status_code": error_response.status_code}
                                                                                                                                                                
        except Exception as e:
        self.log_result("Error Handling", False, "formatted_string")

    async def run_all_tests(self):
        """Run all frontend integration tests"""
        print("Starting Frontend Integration Tests with Auth Service")
        print("=" * 60)

        await self.test_frontend_auth_config_endpoint()
        await self.test_oauth_flow_complete_simulation()
        await self.test_websocket_auth_compatibility()
        await self.test_rate_limiting()
        await self.test_error_handling()

        print("=" * 60)

    # Summary
        passed = sum(1 for r in self.results if r["success"])
        total = len(self.results)
        success_rate = (passed / total * 100) if total > 0 else 0

        print("formatted_string")

        if passed >= total * 0.8:  # 80% pass rate acceptable for integration tests
        print("Integration tests mostly passed! Auth service integrates well with frontend.")
        else:
        print("Some critical integration issues found.")
        failed_tests = [item for item in []]]
        print("formatted_string")

        return success_rate >= 80

    async def main():
        """Main test runner"""
        async with FrontendIntegrationTester() as tester:
        success = await tester.run_all_tests()

        # Output detailed results
        with open("frontend_integration_results.json", "w") as f:
        json.dump({ ))
        "timestamp": "2025-08-26T04:35:00Z",
        "auth_service_url": AUTH_SERVICE_URL,
        "frontend_url": FRONTEND_URL,
        "overall_success": success,
        "results": tester.results
        }, f, indent=2)

        print(f" )
        Detailed results saved to: frontend_integration_results.json")
        return 0 if success else 1

        if __name__ == "__main__":
        sys.exit(asyncio.run(main()))
