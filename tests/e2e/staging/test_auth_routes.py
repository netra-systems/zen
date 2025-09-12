from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""Test auth service route availability issues found in staging.

These tests reproduce the 404 errors for missing authentication routes,
particularly the /auth/google/login route that should be available but
returns 404 Not Found in staging.

Based on staging audit findings:
- Auth service missing /auth/google/login route (404)
- OAuth authentication endpoints not properly registered
- Route configuration incomplete in staging deployment
"""

import pytest
import asyncio
import aiohttp
import requests
from typing import Dict, List, Optional, Tuple
from test_framework.environment_markers import staging_only, env_requires


env = get_env()

# Import staging configuration for SSOT compliance
from tests.e2e.staging_test_config import get_staging_config

class TestAuthRoutes:
    """Test authentication service route availability issues in staging."""

    @staging_only
    @env_requires(services=["auth_service"])
    @pytest.mark.auth
    @pytest.mark.e2e
    async def test_auth_google_login_route_returns_404(self):
        """Test that /auth/google/login route returns 404 Not Found.
        
        This test SHOULD FAIL, demonstrating the exact 404 error for the
        Google OAuth login route that should be available in the auth service.
        
        Expected failure: 404 Not Found for /auth/google/login
        """
        # Get auth service URL from SSOT staging configuration
        staging_config = get_staging_config()
        auth_service_base = staging_config.auth_url
        google_login_route = f"{auth_service_base}/auth/google/login"
        
        route_test_failures = []
        
        try:
            # Test the specific route mentioned in audit as returning 404
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5.0)
            ) as session:
                async with session.get(google_login_route) as response:
                    status_code = response.status
                    response_text = await response.text()
                    
                    # This assertion SHOULD FAIL - expecting 404
                    if status_code == 404:
                        route_test_failures.append({
                            "route": "/auth/google/login",
                            "status_code": 404,
                            "response": response_text[:200],
                            "issue": "Route not found - OAuth login endpoint missing",
                            "expected": "This is the EXACT issue found in staging audit"
                        })
                    elif status_code >= 500:
                        route_test_failures.append({
                            "route": "/auth/google/login", 
                            "status_code": status_code,
                            "response": response_text[:200],
                            "issue": "Server error - route may exist but failing"
                        })
                    else:
                        # Route exists and responds (unexpected if staging is broken)
                        route_test_failures.append({
                            "route": "/auth/google/login",
                            "status_code": status_code,
                            "unexpected": "Route responded successfully",
                            "analysis": "Either route was fixed or staging configuration changed"
                        })
                        
        except aiohttp.ClientConnectorError as e:
            route_test_failures.append({
                "route": "/auth/google/login",
                "error": str(e),
                "issue": "Auth service not reachable",
                "root_cause": "Service connectivity issue prevents route testing"
            })
        except asyncio.TimeoutError:
            route_test_failures.append({
                "route": "/auth/google/login",
                "error": "Request timeout",
                "issue": "Auth service not responding within timeout"
            })
        
        # This test SHOULD FAIL - expecting 404 route failure
        assert len(route_test_failures) > 0, (
            f"Expected /auth/google/login route to return 404 (matching staging audit), "
            f"but route appears to be working correctly. "
            f"This suggests the missing route issue has been resolved."
        )
        
        # Verify we got the specific 404 error from the audit
        not_found_errors = [
            f for f in route_test_failures 
            if f.get("status_code") == 404
        ]
        
        assert len(not_found_errors) >= 1, (
            f"Expected /auth/google/login to return 404 (exact staging issue), "
            f"but got different route failures: {route_test_failures}. "
            f"The 404 error is the specific problem identified in staging."
        )

    @staging_only
    @env_requires(services=["auth_service"])
    @pytest.mark.auth
    @pytest.mark.e2e
    async def test_multiple_oauth_routes_missing_404_pattern(self):
        """Test multiple OAuth-related routes return 404 errors.
        
        This test should FAIL, showing a pattern of missing OAuth routes
        in the auth service, not just the Google login route.
        """
        import os
        
        # Auth service base URL
        
        # Get auth service URL from SSOT staging configuration
        staging_config = get_staging_config()
        auth_service_base = staging_config.auth_url
        
        # OAuth routes that should exist but may be missing
        expected_oauth_routes = [
            "/auth/google/login",      # Primary route from audit
            "/auth/google/callback",   # OAuth callback route
            "/auth/google/logout",     # OAuth logout route
            "/oauth/google/authorize", # Alternative OAuth path
            "/oauth/login",            # Generic OAuth login
            "/auth/oauth/google"       # Another possible OAuth path
        ]
        
        missing_routes = []
        working_routes = []
        error_routes = []
        
        for route_path in expected_oauth_routes:
            full_url = f"{auth_service_base}{route_path}"
            
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=3.0)
                ) as session:
                    async with session.get(full_url) as response:
                        status_code = response.status
                        response_text = await response.text()
                        
                        if status_code == 404:
                            missing_routes.append({
                                "route": route_path,
                                "url": full_url,
                                "status": 404,
                                "issue": "Route not found"
                            })
                        elif status_code >= 500:
                            error_routes.append({
                                "route": route_path,
                                "status": status_code,
                                "response": response_text[:100]
                            })
                        else:
                            working_routes.append({
                                "route": route_path,
                                "status": status_code
                            })
                            
            except aiohttp.ClientConnectorError:
                # Auth service not reachable - separate issue
                continue
            except asyncio.TimeoutError:
                # Route timeout - separate issue  
                continue
        
        # This test SHOULD FAIL - expecting multiple missing routes
        assert len(missing_routes) >= 2, (
            f"Expected multiple OAuth routes to be missing (404 errors), "
            f"but only {len(missing_routes)} routes returned 404. "
            f"Missing: {missing_routes}, Working: {working_routes}, "
            f"Errors: {error_routes}. "
            f"A pattern of missing OAuth routes indicates incomplete OAuth setup."
        )
        
        # Verify the primary route from audit is among missing routes
        primary_route_missing = any(
            route["route"] == "/auth/google/login" 
            for route in missing_routes
        )
        
        assert primary_route_missing, (
            f"Expected /auth/google/login (from audit) to be among missing routes, "
            f"but it's not in the 404 list: {missing_routes}. "
            f"This is the specific route identified as problematic in staging."
        )

    @staging_only
    @env_requires(services=["auth_service"])
    @pytest.mark.auth
    @pytest.mark.e2e
    def test_auth_service_route_registration_incomplete(self):
        """Test that auth service route registration is incomplete.
        
        This test should FAIL, demonstrating that the auth service is running
        but has not properly registered all required OAuth routes.
        """
        import os
        
        # Get auth service URL from SSOT staging configuration
        staging_config = get_staging_config()
        auth_service_base = staging_config.auth_url
        
        # Test basic auth service health vs missing OAuth routes
        route_registration_issues = []
        
        # Test 1: Auth service should be reachable for health check
        try:
            health_response = requests.get(f"{auth_service_base}/health", timeout=3.0)
            if health_response.status_code == 200:
                # Auth service is running - good for testing route registration
                pass
            else:
                route_registration_issues.append({
                    "issue": "Auth service health check failed",
                    "status_code": health_response.status_code,
                    "impact": "Cannot test route registration on non-functional service"
                })
        except requests.exceptions.RequestException as e:
            route_registration_issues.append({
                "issue": "Auth service not reachable",
                "error": str(e),
                "impact": "Cannot test route registration - service connectivity issue"
            })
        
        # Test 2: Core auth routes should exist
        core_auth_routes = [
            "/health",     # Should work
            "/auth/login", # Should work  
            "/auth/status" # Should work
        ]
        
        working_core_routes = []
        for route in core_auth_routes:
            try:
                response = requests.get(f"{auth_service_base}{route}", timeout=2.0)
                if response.status_code < 500:  # Any non-server-error response
                    working_core_routes.append(route)
            except requests.exceptions.RequestException:
                pass
        
        # Test 3: OAuth routes should be missing
        oauth_routes = ["/auth/google/login", "/auth/google/callback"]
        missing_oauth_routes = []
        
        for route in oauth_routes:
            try:
                response = requests.get(f"{auth_service_base}{route}", timeout=2.0)
                if response.status_code == 404:
                    missing_oauth_routes.append(route)
            except requests.exceptions.RequestException:
                pass
        
        # Analyze route registration completeness
        if len(working_core_routes) > 0 and len(missing_oauth_routes) > 0:
            route_registration_issues.append({
                "issue": "Selective route registration failure",
                "working_routes": working_core_routes,
                "missing_routes": missing_oauth_routes,
                "analysis": "Auth service running but OAuth routes not registered"
            })
        elif len(working_core_routes) == 0:
            route_registration_issues.append({
                "issue": "Complete route registration failure",
                "impact": "Auth service may be running but no routes responding"
            })
        
        # This test SHOULD FAIL - expecting route registration issues
        assert len(route_registration_issues) > 0, (
            f"Expected auth service route registration to be incomplete "
            f"(explaining 404s for OAuth routes), but route registration appears complete. "
            f"Working core routes: {working_core_routes}, "
            f"Missing OAuth routes: {missing_oauth_routes}. "
            f"This suggests route registration issues have been resolved."
        )
        
        # Verify we found the specific OAuth route registration issue
        oauth_registration_issues = [
            issue for issue in route_registration_issues
            if "OAuth" in issue.get("analysis", "") or "google" in str(issue)
        ]
        
        assert len(oauth_registration_issues) >= 1, (
            f"Expected OAuth route registration to be the specific issue "
            f"(matching /auth/google/login 404 from audit), but got other "
            f"route registration problems: {route_registration_issues}. "
            f"OAuth route registration is the core staging problem."
        )

    @staging_only
    @env_requires(services=["auth_service"])
    @pytest.mark.auth
    @pytest.mark.e2e
    async def test_auth_service_route_mapping_configuration_error(self):
        """Test auth service route mapping configuration errors.
        
        This test should FAIL, demonstrating that route mapping configuration
        is incorrect, causing OAuth routes to not be properly mapped.
        """
        import os
        
        # Get auth service URL from SSOT staging configuration
        staging_config = get_staging_config()
        auth_service_base = staging_config.auth_url
        
        # Test different possible OAuth route patterns to find configuration issue
        oauth_route_patterns = [
            # Standard patterns
            "/auth/google/login",
            "/auth/oauth/google/login",
            "/oauth/google/login",
            
            # Alternative patterns that might be configured instead
            "/api/auth/google/login",
            "/v1/auth/google/login",
            "/google/auth/login",
            
            # Case sensitivity issues
            "/auth/Google/login",
            "/auth/google/Login",
            "/Auth/Google/Login"
        ]
        
        route_mapping_results = []
        
        for route_pattern in oauth_route_patterns:
            full_url = f"{auth_service_base}{route_pattern}"
            
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=2.0)
                ) as session:
                    async with session.get(full_url) as response:
                        status_code = response.status
                        
                        route_mapping_results.append({
                            "pattern": route_pattern,
                            "status_code": status_code,
                            "url": full_url,
                            "result": "found" if status_code != 404 else "not_found"
                        })
                        
            except Exception as e:
                route_mapping_results.append({
                    "pattern": route_pattern,
                    "error": str(e)[:50],
                    "result": "error"
                })
        
        # Analyze route mapping issues
        not_found_routes = [r for r in route_mapping_results if r.get("result") == "not_found"]
        found_routes = [r for r in route_mapping_results if r.get("result") == "found"]
        
        route_mapping_failures = []
        
        # Test expectation: Standard OAuth routes should be missing (404)
        standard_routes_missing = [
            r for r in not_found_routes 
            if r["pattern"] in ["/auth/google/login", "/auth/google/callback"]
        ]
        
        if len(standard_routes_missing) > 0:
            route_mapping_failures.append({
                "issue": "Standard OAuth routes missing",
                "missing_routes": [r["pattern"] for r in standard_routes_missing],
                "impact": "OAuth authentication cannot proceed"
            })
        
        # Check if routes exist under alternative patterns (configuration mismatch)
        if len(found_routes) > 0:
            alternative_patterns = [r["pattern"] for r in found_routes]
            route_mapping_failures.append({
                "issue": "OAuth routes exist under alternative patterns",
                "alternative_patterns": alternative_patterns,
                "impact": "Route mapping configuration mismatch"
            })
        
        # This test SHOULD FAIL - expecting route mapping configuration errors
        assert len(route_mapping_failures) > 0, (
            f"Expected OAuth route mapping configuration errors "
            f"(explaining 404s for standard OAuth routes), but route mapping "
            f"appears correct. Found routes: {[r['pattern'] for r in found_routes]}, "
            f"Missing routes: {[r['pattern'] for r in not_found_routes]}. "
            f"This suggests route mapping configuration is working."
        )
        
        # Verify standard OAuth routes are specifically missing
        standard_route_issues = [
            failure for failure in route_mapping_failures
            if "Standard OAuth routes missing" in failure.get("issue", "")
        ]
        
        assert len(standard_route_issues) >= 1, (
            f"Expected standard OAuth routes (/auth/google/login) to be missing "
            f"(matching staging audit findings), but got other route mapping issues: "
            f"{route_mapping_failures}. The missing standard routes are the core issue."
        )

    @staging_only
    @env_requires(services=["auth_service"])
    @pytest.mark.auth
    @pytest.mark.e2e
    def test_auth_service_oauth_blueprint_not_registered(self):
        """Test that OAuth blueprint/router is not registered in auth service.
        
        This test should FAIL, showing that the OAuth functionality is not
        properly integrated into the auth service application instance.
        """
        import os
        
        # Get auth service URL from SSOT staging configuration
        staging_config = get_staging_config()
        auth_service_base = staging_config.auth_url
        
        # Test route discovery to understand what blueprints/routers are registered
        blueprint_discovery_failures = []
        
        # Test 1: Check if any OAuth-related routes exist
        oauth_test_routes = [
            "/auth/google/login",
            "/auth/google/callback", 
            "/auth/oauth/",
            "/oauth/"
        ]
        
        oauth_routes_found = 0
        for route in oauth_test_routes:
            try:
                response = requests.get(f"{auth_service_base}{route}", timeout=2.0)
                if response.status_code != 404:
                    oauth_routes_found += 1
            except requests.exceptions.RequestException:
                pass
        
        if oauth_routes_found == 0:
            blueprint_discovery_failures.append({
                "issue": "No OAuth routes found",
                "tested_routes": oauth_test_routes,
                "impact": "OAuth blueprint likely not registered"
            })
        
        # Test 2: Check if base auth routes work (indicating service is functional)
        base_auth_routes = ["/health", "/auth/status", "/auth/info"]
        working_base_routes = []
        
        for route in base_auth_routes:
            try:
                response = requests.get(f"{auth_service_base}{route}", timeout=2.0)
                if response.status_code < 500:
                    working_base_routes.append(route)
            except requests.exceptions.RequestException:
                pass
        
        # Test 3: Analyze service functionality vs OAuth integration
        if len(working_base_routes) > 0 and oauth_routes_found == 0:
            blueprint_discovery_failures.append({
                "issue": "Auth service functional but OAuth blueprint missing",
                "working_routes": working_base_routes,
                "missing_oauth_routes": oauth_test_routes,
                "diagnosis": "OAuth blueprint/router not registered with app instance"
            })
        elif len(working_base_routes) == 0:
            blueprint_discovery_failures.append({
                "issue": "Auth service completely non-functional",
                "impact": "Cannot test OAuth blueprint registration"
            })
        
        # Test 4: Check for route enumeration endpoint (if available)
        route_enumeration_endpoints = ["/routes", "/_routes", "/debug/routes", "/api/routes"]
        for endpoint in route_enumeration_endpoints:
            try:
                response = requests.get(f"{auth_service_base}{endpoint}", timeout=2.0)
                if response.status_code == 200:
                    routes_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                    
                    # Check if OAuth routes are in the enumerated routes
                    if "google" not in str(routes_data).lower():
                        blueprint_discovery_failures.append({
                            "issue": "OAuth routes not in service route enumeration",
                            "endpoint": endpoint,
                            "evidence": "No 'google' routes found in route listing"
                        })
                    break
            except Exception:
                continue
        
        # This test SHOULD FAIL - expecting OAuth blueprint registration issues
        assert len(blueprint_discovery_failures) > 0, (
            f"Expected OAuth blueprint to be missing from auth service "
            f"(explaining 404 for /auth/google/login), but OAuth integration "
            f"appears to be working. Working base routes: {working_base_routes}, "
            f"OAuth routes found: {oauth_routes_found}. "
            f"This suggests OAuth blueprint registration is complete."
        )
        
        # Verify we found the specific blueprint registration issue
        blueprint_missing_issues = [
            failure for failure in blueprint_discovery_failures
            if "blueprint" in failure.get("issue", "").lower() or "blueprint" in failure.get("diagnosis", "").lower()
        ]
        
        assert len(blueprint_missing_issues) >= 1, (
            f"Expected OAuth blueprint registration to be the specific issue "
            f"(causing /auth/google/login 404), but got other discovery failures: "
            f"{blueprint_discovery_failures}. Blueprint registration is the most "
            f"likely cause of systematic OAuth route unavailability."
        )

    @staging_only
    @env_requires(services=["auth_service"])
    @pytest.mark.auth
    @pytest.mark.e2e
    async def test_oauth_route_handler_import_or_dependency_missing(self):
        """Test that OAuth route handlers have missing imports or dependencies.
        
        This test should FAIL, showing that OAuth routes are not available
        due to missing dependencies or import failures during service startup.
        """
        import os
        
        # Get auth service URL from SSOT staging configuration
        staging_config = get_staging_config()
        auth_service_base = staging_config.auth_url
        
        # Test OAuth route availability and service error responses
        oauth_dependency_failures = []
        
        # Primary OAuth route from audit
        google_login_url = f"{auth_service_base}/auth/google/login"
        
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=3.0)
            ) as session:
                async with session.get(google_login_url) as response:
                    status_code = response.status
                    response_text = await response.text()
                    
                    if status_code == 404:
                        oauth_dependency_failures.append({
                            "route": "/auth/google/login",
                            "status_code": 404,
                            "issue": "Route not found - likely import/dependency failure",
                            "response_preview": response_text[:100]
                        })
                    elif status_code == 500:
                        oauth_dependency_failures.append({
                            "route": "/auth/google/login",
                            "status_code": 500,
                            "issue": "Server error - possible dependency missing at runtime",
                            "response_preview": response_text[:150]
                        })
                    elif "ImportError" in response_text or "ModuleNotFoundError" in response_text:
                        oauth_dependency_failures.append({
                            "route": "/auth/google/login",
                            "status_code": status_code,
                            "issue": "Import error detected in response",
                            "error_type": "DEPENDENCY_MISSING"
                        })
                    
        except aiohttp.ClientConnectorError as e:
            oauth_dependency_failures.append({
                "route": "/auth/google/login",
                "error": str(e),
                "issue": "Service connectivity failure"
            })
        
        # Test alternative OAuth endpoints for pattern analysis
        alternative_oauth_endpoints = [
            "/auth/oauth/providers",   # OAuth provider listing
            "/auth/providers",         # Alternative provider endpoint
            "/oauth/providers"         # Another common pattern
        ]
        
        for endpoint in alternative_oauth_endpoints:
            try:
                full_url = f"{auth_service_base}{endpoint}"
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=2.0)
                ) as session:
                    async with session.get(full_url) as response:
                        if response.status == 404:
                            oauth_dependency_failures.append({
                                "route": endpoint,
                                "status_code": 404,
                                "pattern": "OAuth provider endpoints missing"
                            })
            except Exception:
                pass
        
        # Test service logs endpoint for dependency error information
        logs_endpoints = ["/logs", "/debug/logs", "/health/detailed"]
        for logs_endpoint in logs_endpoints:
            try:
                logs_url = f"{auth_service_base}{logs_endpoint}"
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=2.0)
                ) as session:
                    async with session.get(logs_url) as response:
                        if response.status == 200:
                            logs_text = await response.text()
                            
                            # Check for import/dependency errors in logs
                            dependency_error_indicators = [
                                "ImportError", "ModuleNotFoundError", 
                                "oauth", "google-auth", "google-oauth"
                            ]
                            
                            for indicator in dependency_error_indicators:
                                if indicator.lower() in logs_text.lower():
                                    oauth_dependency_failures.append({
                                        "source": logs_endpoint,
                                        "issue": f"Dependency error indicator found: {indicator}",
                                        "evidence": "Service logs contain OAuth dependency issues"
                                    })
                                    break
            except Exception:
                continue
        
        # This test SHOULD FAIL - expecting OAuth dependency/import failures
        assert len(oauth_dependency_failures) > 0, (
            f"Expected OAuth dependency or import failures "
            f"(explaining /auth/google/login 404 in staging), but no dependency "
            f"issues detected. This suggests OAuth dependencies are properly "
            f"installed and imported."
        )
        
        # Verify we found the specific 404 route issue
        route_not_found_issues = [
            failure for failure in oauth_dependency_failures
            if failure.get("status_code") == 404 or "not found" in failure.get("issue", "").lower()
        ]
        
        assert len(route_not_found_issues) >= 1, (
            f"Expected /auth/google/login to return 404 (from staging audit), "
            f"but got other OAuth dependency failures: {oauth_dependency_failures}. "
            f"The 404 error is the specific staging issue that needs reproduction."
        )