#!/usr/bin/env python3
# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Comprehensive Auth Service Staging Tests
# REMOVED_SYNTAX_ERROR: Manual testing script for staging environment validation
# REMOVED_SYNTAX_ERROR: '''

import asyncio
import httpx
import json
import sys
from typing import Dict, List, Any
from urllib.parse import urlparse, parse_qs

# Staging URLs
AUTH_SERVICE_URL = "https://auth.staging.netrasystems.ai"

# REMOVED_SYNTAX_ERROR: class StagingAuthTester:
# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: self.results = []
    # REMOVED_SYNTAX_ERROR: self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=False)

# REMOVED_SYNTAX_ERROR: async def __aenter__(self):
    # REMOVED_SYNTAX_ERROR: return self

# REMOVED_SYNTAX_ERROR: async def __aexit__(self, exc_type, exc_val, exc_tb):
    # REMOVED_SYNTAX_ERROR: await self.client.aclose()

# REMOVED_SYNTAX_ERROR: def log_result(self, test_name: str, success: bool, details: str, response_data: Dict = None):
    # REMOVED_SYNTAX_ERROR: result = { )
    # REMOVED_SYNTAX_ERROR: "test": test_name,
    # REMOVED_SYNTAX_ERROR: "success": success,
    # REMOVED_SYNTAX_ERROR: "details": details,
    # REMOVED_SYNTAX_ERROR: "response_data": response_data or {}
    
    # REMOVED_SYNTAX_ERROR: self.results.append(result)
    # REMOVED_SYNTAX_ERROR: status = "PASS" if success else "FAIL"
    # REMOVED_SYNTAX_ERROR: print("formatted_string")

    # Removed problematic line: async def test_health_endpoints(self):
        # REMOVED_SYNTAX_ERROR: """Test health check endpoints"""
        # REMOVED_SYNTAX_ERROR: try:
            # Test ready endpoint
            # REMOVED_SYNTAX_ERROR: response = await self.client.get("formatted_string")
            # REMOVED_SYNTAX_ERROR: if response.status_code == 200:
                # REMOVED_SYNTAX_ERROR: data = response.json()
                # REMOVED_SYNTAX_ERROR: self.log_result( )
                # REMOVED_SYNTAX_ERROR: "Health Check - Ready",
                # REMOVED_SYNTAX_ERROR: True,
                # REMOVED_SYNTAX_ERROR: "formatted_string",
                # REMOVED_SYNTAX_ERROR: data
                
                # REMOVED_SYNTAX_ERROR: else:
                    # REMOVED_SYNTAX_ERROR: self.log_result( )
                    # REMOVED_SYNTAX_ERROR: "Health Check - Ready",
                    # REMOVED_SYNTAX_ERROR: False,
                    # REMOVED_SYNTAX_ERROR: "formatted_string"
                    
                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                        # REMOVED_SYNTAX_ERROR: self.log_result("Health Check - Ready", False, "formatted_string")

                        # Removed problematic line: async def test_oauth_flow_initiation(self):
                            # REMOVED_SYNTAX_ERROR: """Test OAuth flow initiation"""
                            # REMOVED_SYNTAX_ERROR: try:
                                # REMOVED_SYNTAX_ERROR: response = await self.client.get( )
                                # REMOVED_SYNTAX_ERROR: "formatted_string"
                                

                                # REMOVED_SYNTAX_ERROR: if response.status_code == 302:
                                    # REMOVED_SYNTAX_ERROR: location = response.headers.get("location", "")
                                    # REMOVED_SYNTAX_ERROR: if "accounts.google.com" in location:
                                        # Parse the redirect URL to check parameters
                                        # REMOVED_SYNTAX_ERROR: parsed = urlparse(location)
                                        # REMOVED_SYNTAX_ERROR: query_params = parse_qs(parsed.query)

                                        # Check required OAuth parameters
                                        # REMOVED_SYNTAX_ERROR: required_params = ["client_id", "redirect_uri", "response_type", "scope", "state"]
                                        # REMOVED_SYNTAX_ERROR: missing_params = [item for item in []]

                                        # REMOVED_SYNTAX_ERROR: if not missing_params:
                                            # REMOVED_SYNTAX_ERROR: redirect_uri = query_params.get("redirect_uri", [""])[0]
                                            # REMOVED_SYNTAX_ERROR: if "auth.staging.netrasystems.ai" in redirect_uri:
                                                # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                # REMOVED_SYNTAX_ERROR: "OAuth Flow Initiation",
                                                # REMOVED_SYNTAX_ERROR: True,
                                                # REMOVED_SYNTAX_ERROR: f"Correct redirect to Google OAuth with proper callback URL",
                                                # REMOVED_SYNTAX_ERROR: {"redirect_uri": redirect_uri, "location": location}
                                                
                                                # REMOVED_SYNTAX_ERROR: else:
                                                    # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                    # REMOVED_SYNTAX_ERROR: "OAuth Flow Initiation",
                                                    # REMOVED_SYNTAX_ERROR: False,
                                                    # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                    # REMOVED_SYNTAX_ERROR: {"redirect_uri": redirect_uri}
                                                    
                                                    # REMOVED_SYNTAX_ERROR: else:
                                                        # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                        # REMOVED_SYNTAX_ERROR: "OAuth Flow Initiation",
                                                        # REMOVED_SYNTAX_ERROR: False,
                                                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                                                        
                                                        # REMOVED_SYNTAX_ERROR: else:
                                                            # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                            # REMOVED_SYNTAX_ERROR: "OAuth Flow Initiation",
                                                            # REMOVED_SYNTAX_ERROR: False,
                                                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                                                            
                                                            # REMOVED_SYNTAX_ERROR: else:
                                                                # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                                # REMOVED_SYNTAX_ERROR: "OAuth Flow Initiation",
                                                                # REMOVED_SYNTAX_ERROR: False,
                                                                # REMOVED_SYNTAX_ERROR: "formatted_string"
                                                                
                                                                # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                                    # REMOVED_SYNTAX_ERROR: self.log_result("OAuth Flow Initiation", False, "formatted_string")

                                                                    # Removed problematic line: async def test_token_validation(self):
                                                                        # REMOVED_SYNTAX_ERROR: """Test JWT token validation"""
                                                                        # Test with invalid token
                                                                        # REMOVED_SYNTAX_ERROR: try:
                                                                            # REMOVED_SYNTAX_ERROR: response = await self.client.post( )
                                                                            # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                                            # REMOVED_SYNTAX_ERROR: json={"token": "invalid-test-token-12345"}
                                                                            

                                                                            # REMOVED_SYNTAX_ERROR: if response.status_code == 401 or response.status_code == 422:
                                                                                # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                                                # REMOVED_SYNTAX_ERROR: "Token Validation - Invalid Token",
                                                                                # REMOVED_SYNTAX_ERROR: True,
                                                                                # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                                                # REMOVED_SYNTAX_ERROR: {"status_code": response.status_code, "response": response.text}
                                                                                
                                                                                # REMOVED_SYNTAX_ERROR: else:
                                                                                    # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                                                    # REMOVED_SYNTAX_ERROR: "Token Validation - Invalid Token",
                                                                                    # REMOVED_SYNTAX_ERROR: False,
                                                                                    # REMOVED_SYNTAX_ERROR: "formatted_string"
                                                                                    
                                                                                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                                                        # REMOVED_SYNTAX_ERROR: self.log_result("Token Validation - Invalid Token", False, "formatted_string")

                                                                                        # Test with malformed request
                                                                                        # REMOVED_SYNTAX_ERROR: try:
                                                                                            # REMOVED_SYNTAX_ERROR: response = await self.client.post( )
                                                                                            # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                                                            # REMOVED_SYNTAX_ERROR: json={"not_token": "malformed"}
                                                                                            

                                                                                            # REMOVED_SYNTAX_ERROR: if response.status_code == 422:  # Validation error
                                                                                            # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                                                            # REMOVED_SYNTAX_ERROR: "Token Validation - Malformed Request",
                                                                                            # REMOVED_SYNTAX_ERROR: True,
                                                                                            # REMOVED_SYNTAX_ERROR: "Correctly rejected malformed request",
                                                                                            # REMOVED_SYNTAX_ERROR: {"status_code": response.status_code}
                                                                                            
                                                                                            # REMOVED_SYNTAX_ERROR: else:
                                                                                                # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                                                                # REMOVED_SYNTAX_ERROR: "Token Validation - Malformed Request",
                                                                                                # REMOVED_SYNTAX_ERROR: False,
                                                                                                # REMOVED_SYNTAX_ERROR: "formatted_string"
                                                                                                
                                                                                                # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                                                                    # REMOVED_SYNTAX_ERROR: self.log_result("Token Validation - Malformed Request", False, "formatted_string")

                                                                                                    # Removed problematic line: async def test_cors_configuration(self):
                                                                                                        # REMOVED_SYNTAX_ERROR: """Test CORS configuration for staging domains"""
                                                                                                        # REMOVED_SYNTAX_ERROR: staging_origins = [ )
                                                                                                        # REMOVED_SYNTAX_ERROR: "https://app.staging.netrasystems.ai",
                                                                                                        # REMOVED_SYNTAX_ERROR: "https://auth.staging.netrasystems.ai",
                                                                                                        # REMOVED_SYNTAX_ERROR: "https://api.staging.netrasystems.ai"
                                                                                                        

                                                                                                        # REMOVED_SYNTAX_ERROR: for origin in staging_origins:
                                                                                                            # REMOVED_SYNTAX_ERROR: try:
                                                                                                                # REMOVED_SYNTAX_ERROR: response = await self.client.options( )
                                                                                                                # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                                                                                # REMOVED_SYNTAX_ERROR: headers={ )
                                                                                                                # REMOVED_SYNTAX_ERROR: "Origin": origin,
                                                                                                                # REMOVED_SYNTAX_ERROR: "Access-Control-Request-Method": "GET",
                                                                                                                # REMOVED_SYNTAX_ERROR: "Access-Control-Request-Headers": "Content-Type"
                                                                                                                
                                                                                                                

                                                                                                                # REMOVED_SYNTAX_ERROR: if response.status_code in [200, 204]:
                                                                                                                    # REMOVED_SYNTAX_ERROR: allowed_origins = response.headers.get("Access-Control-Allow-Origin", "")
                                                                                                                    # REMOVED_SYNTAX_ERROR: if origin in allowed_origins or "*" in allowed_origins:
                                                                                                                        # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                                                                                        # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                                                                                        # REMOVED_SYNTAX_ERROR: True,
                                                                                                                        # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                                                                                        # REMOVED_SYNTAX_ERROR: {"allowed_origin": allowed_origins}
                                                                                                                        
                                                                                                                        # REMOVED_SYNTAX_ERROR: else:
                                                                                                                            # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                                                                                            # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                                                                                            # REMOVED_SYNTAX_ERROR: False,
                                                                                                                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                                                                                                                            
                                                                                                                            # REMOVED_SYNTAX_ERROR: else:
                                                                                                                                # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                                                                                                # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                                                                                                # REMOVED_SYNTAX_ERROR: False,
                                                                                                                                # REMOVED_SYNTAX_ERROR: "formatted_string"
                                                                                                                                
                                                                                                                                # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                                                                                                    # REMOVED_SYNTAX_ERROR: self.log_result("formatted_string", False, "formatted_string")

                                                                                                                                    # Removed problematic line: async def test_security_headers(self):
                                                                                                                                        # REMOVED_SYNTAX_ERROR: """Test security headers"""
                                                                                                                                        # REMOVED_SYNTAX_ERROR: try:
                                                                                                                                            # REMOVED_SYNTAX_ERROR: response = await self.client.get("formatted_string")

                                                                                                                                            # REMOVED_SYNTAX_ERROR: security_headers = { )
                                                                                                                                            # REMOVED_SYNTAX_ERROR: "X-Content-Type-Options": "nosniff",
                                                                                                                                            # REMOVED_SYNTAX_ERROR: "X-Frame-Options": "DENY",
                                                                                                                                            # REMOVED_SYNTAX_ERROR: "X-XSS-Protection": "1; mode=block"
                                                                                                                                            

                                                                                                                                            # REMOVED_SYNTAX_ERROR: missing_headers = []
                                                                                                                                            # REMOVED_SYNTAX_ERROR: present_headers = {}

                                                                                                                                            # REMOVED_SYNTAX_ERROR: for header, expected_value in security_headers.items():
                                                                                                                                                # REMOVED_SYNTAX_ERROR: actual_value = response.headers.get(header)
                                                                                                                                                # REMOVED_SYNTAX_ERROR: if actual_value:
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: present_headers[header] = actual_value
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: if expected_value.lower() not in actual_value.lower():
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: missing_headers.append("formatted_string")
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: else:
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: missing_headers.append(header)

                                                                                                                                                            # REMOVED_SYNTAX_ERROR: if not missing_headers:
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "Security Headers",
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: True,
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "All security headers present and correct",
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: present_headers
                                                                                                                                                                
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: else:
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: "Security Headers",
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: False,
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: present_headers
                                                                                                                                                                    
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: self.log_result("Security Headers", False, "formatted_string")

                                                                                                                                                                        # Removed problematic line: async def test_database_connectivity(self):
                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: """Test database connectivity through health endpoint"""
                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: try:
                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: response = await self.client.get("formatted_string")

                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: if response.status_code == 200:
                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: data = response.json()
                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: db_status = data.get("database_status", "unknown")

                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: if db_status == "connected":
                                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: "Database Connectivity",
                                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: True,
                                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: "Database is connected and ready",
                                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: {"database_status": db_status}
                                                                                                                                                                                        
                                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: else:
                                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: "Database Connectivity",
                                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: False,
                                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: data
                                                                                                                                                                                            
                                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: else:
                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "Database Connectivity",
                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: False,
                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "formatted_string"
                                                                                                                                                                                                
                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: self.log_result("Database Connectivity", False, "formatted_string")

                                                                                                                                                                                                    # Removed problematic line: async def test_service_metadata(self):
                                                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: """Test service metadata and environment detection"""
                                                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: try:
                                                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: response = await self.client.get("formatted_string")

                                                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: if response.status_code == 200:
                                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: data = response.json()
                                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: environment = data.get("environment")
                                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: service = data.get("service")
                                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: version = data.get("version")

                                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: issues = []
                                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: if environment != "staging":
                                                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: issues.append("formatted_string")
                                                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: if service != "auth-service":
                                                                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: issues.append("formatted_string")
                                                                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: if not version:
                                                                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: issues.append("Version not specified")

                                                                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: if not issues:
                                                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "Service Metadata",
                                                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: True,
                                                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: data
                                                                                                                                                                                                                                
                                                                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: else:
                                                                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: "Service Metadata",
                                                                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: False,
                                                                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: data
                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: else:
                                                                                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: self.log_result( )
                                                                                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: "Service Metadata",
                                                                                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: False,
                                                                                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                                                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: self.log_result("Service Metadata", False, "formatted_string")

# REMOVED_SYNTAX_ERROR: async def run_all_tests(self):
    # REMOVED_SYNTAX_ERROR: """Run all staging tests"""
    # REMOVED_SYNTAX_ERROR: print("Starting Auth Service Staging Tests")
    # REMOVED_SYNTAX_ERROR: print("=" * 60)

    # REMOVED_SYNTAX_ERROR: await self.test_health_endpoints()
    # REMOVED_SYNTAX_ERROR: await self.test_service_metadata()
    # REMOVED_SYNTAX_ERROR: await self.test_database_connectivity()
    # REMOVED_SYNTAX_ERROR: await self.test_oauth_flow_initiation()
    # REMOVED_SYNTAX_ERROR: await self.test_token_validation()
    # REMOVED_SYNTAX_ERROR: await self.test_cors_configuration()
    # REMOVED_SYNTAX_ERROR: await self.test_security_headers()

    # REMOVED_SYNTAX_ERROR: print("=" * 60)

    # Summary
    # REMOVED_SYNTAX_ERROR: passed = sum(1 for r in self.results if r["success"])
    # REMOVED_SYNTAX_ERROR: total = len(self.results)
    # REMOVED_SYNTAX_ERROR: success_rate = (passed / total * 100) if total > 0 else 0

    # REMOVED_SYNTAX_ERROR: print("formatted_string")

    # REMOVED_SYNTAX_ERROR: if passed == total:
        # REMOVED_SYNTAX_ERROR: print("All tests passed! Auth service is ready for staging use.")
        # REMOVED_SYNTAX_ERROR: else:
            # REMOVED_SYNTAX_ERROR: print("Some tests failed. Check the detailed results above.")
            # REMOVED_SYNTAX_ERROR: failed_tests = [item for item in []]]
            # REMOVED_SYNTAX_ERROR: print("formatted_string")

            # REMOVED_SYNTAX_ERROR: return success_rate >= 90  # 90% pass rate required

# REMOVED_SYNTAX_ERROR: async def main():
    # REMOVED_SYNTAX_ERROR: """Main test runner"""
    # REMOVED_SYNTAX_ERROR: async with StagingAuthTester() as tester:
        # REMOVED_SYNTAX_ERROR: success = await tester.run_all_tests()

        # Output detailed results as JSON for further analysis
        # REMOVED_SYNTAX_ERROR: with open("staging_auth_test_results.json", "w") as f:
            # REMOVED_SYNTAX_ERROR: json.dump({ ))
            # REMOVED_SYNTAX_ERROR: "timestamp": "2025-08-26T04:30:00Z",
            # REMOVED_SYNTAX_ERROR: "service_url": AUTH_SERVICE_URL,
            # REMOVED_SYNTAX_ERROR: "overall_success": success,
            # REMOVED_SYNTAX_ERROR: "results": tester.results
            # REMOVED_SYNTAX_ERROR: }, f, indent=2)

            # REMOVED_SYNTAX_ERROR: print(f" )
            # REMOVED_SYNTAX_ERROR: Detailed results saved to: staging_auth_test_results.json")

            # REMOVED_SYNTAX_ERROR: return 0 if success else 1

            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                # REMOVED_SYNTAX_ERROR: sys.exit(asyncio.run(main()))