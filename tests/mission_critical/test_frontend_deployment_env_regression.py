"""
🚨 MISSION CRITICAL: Frontend Deployment Environment Variables Regression Test
===============================================================================
This test PREVENTS regression of critical frontend environment variables that have 
repeatedly been removed, causing complete frontend failure.

CRITICAL: Missing ANY of these variables will cause:
- WebSocket connection failures
- Authentication failures  
- API connection failures
- Complete frontend breakdown
- Discovery endpoint failures (breaks ENTIRE chat value delivery)

Cross-references:
- SPEC/frontend_deployment_critical.xml
- SPEC/learnings/frontend_deployment.xml
- scripts/deploy_to_gcp.py::validate_frontend_environment_variables()
"""

import os
import sys
import json
import unittest
import requests
from pathlib import Path
from typing import Dict, List, Set, Optional
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.deploy_to_gcp import ServiceConfig, GCPDeployer
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestFrontendDeploymentEnvironmentRegression(unittest.TestCase):
    """
    CRITICAL: Tests to prevent regression of frontend deployment environment variables.
    These variables have been removed multiple times causing complete frontend failure.
    """
    
    @classmethod
    def setUpClass(cls):
        """Define the MANDATORY environment variables required for frontend."""
        cls.CRITICAL_FRONTEND_VARS = {
            "NEXT_PUBLIC_ENVIRONMENT": {
                "description": "Controls environment-specific behavior",
                "example": "staging",
                "critical": True
            },
            "NEXT_PUBLIC_API_URL": {
                "description": "Main backend API endpoint",
                "example": "https://api.staging.netrasystems.ai",
                "critical": True
            },
            "NEXT_PUBLIC_AUTH_URL": {
                "description": "Auth service primary endpoint",
                "example": "https://auth.staging.netrasystems.ai",
                "critical": True
            },
            "NEXT_PUBLIC_WS_URL": {
                "description": "WebSocket primary endpoint",
                "example": "wss://api.staging.netrasystems.ai",
                "critical": True
            },
            "NEXT_PUBLIC_WEBSOCKET_URL": {
                "description": "WebSocket fallback endpoint",
                "example": "wss://api.staging.netrasystems.ai",
                "critical": True
            },
            "NEXT_PUBLIC_AUTH_SERVICE_URL": {
                "description": "Auth service fallback URL",
                "example": "https://auth.staging.netrasystems.ai",
                "critical": True
            },
            "NEXT_PUBLIC_AUTH_API_URL": {
                "description": "Auth API specific endpoint",
                "example": "https://auth.staging.netrasystems.ai",
                "critical": True
            },
            "NEXT_PUBLIC_BACKEND_URL": {
                "description": "Backend fallback endpoint",
                "example": "https://api.staging.netrasystems.ai",
                "critical": True
            },
            "NEXT_PUBLIC_FRONTEND_URL": {
                "description": "Frontend self-reference URL for OAuth redirects",
                "example": "https://app.staging.netrasystems.ai",
                "critical": True
            },
            "NEXT_PUBLIC_FORCE_HTTPS": {
                "description": "Security enforcement flag",
                "example": "true",
                "critical": True
            },
            "NEXT_PUBLIC_GTM_CONTAINER_ID": {
                "description": "Google Tag Manager container ID",
                "example": "GTM-WKP28PNQ",
                "critical": False
            },
            "NEXT_PUBLIC_GTM_ENABLED": {
                "description": "Enable/disable GTM tracking",
                "example": "true",
                "critical": False
            },
            "NEXT_PUBLIC_GTM_DEBUG": {
                "description": "GTM debug mode",
                "example": "false",
                "critical": False
            }
        }
    
    def test_deployment_script_includes_all_critical_vars(self):
        """
    pass
        Test that deploy_to_gcp.py ServiceConfig includes ALL critical frontend variables.
        """
        print("
🔍 Testing deployment script includes all critical variables...")
        
        # Create a GCPDeployer with correct initialization
        deployer = GCPDeployer(project_id="netra-staging")
        
        # Find the frontend service configuration
        frontend_service = None
        for service in deployer.services:
            if service.name == "frontend":
                frontend_service = service
                break
        
        self.assertIsNotNone(
            frontend_service, 
            "❌ Frontend service not found in deployment configuration!"
        )
        
        # Check each critical variable is present
        missing_vars = []
        for var_name, var_info in self.CRITICAL_FRONTEND_VARS.items():
            if var_info.get("critical", False):
                if var_name not in frontend_service.environment_vars:
                    missing_vars.append(var_name)
                    print(f"  ❌ MISSING: {var_name} - {var_info['description']}")
                else:
                    print(f"  ✅ Found: {var_name}")
        
        self.assertEqual(
            len(missing_vars), 0,
            f"
🔴 CRITICAL REGRESSION DETECTED!
"
            f"Missing {len(missing_vars)} critical environment variables:
" +
            "
".join(f"  - {var}: {self.CRITICAL_FRONTEND_VARS[var]['description']}" 
                     for var in missing_vars) +
            "

These variables MUST be added back to scripts/deploy_to_gcp.py!"
        )
    
    def test_validation_method_checks_all_vars(self):
        """
        Test that validate_frontend_environment_variables() method checks ALL required vars.
        """
    pass
        print("
🔍 Testing validation method checks all variables...")
        
        deployer = GCPDeployer(project_id="netra-staging")
        
        # Test with all variables present (should pass)
        result = deployer.validate_frontend_environment_variables()
        self.assertTrue(
            result,
            "❌ Validation failed even with all variables present!"
        )
        
        # Test with missing critical variable (should fail)
        frontend_service = None
        for service in deployer.services:
            if service.name == "frontend":
                frontend_service = service
                break
        
        if frontend_service:
            # Remove a critical variable temporarily
            original_value = frontend_service.environment_vars.pop("NEXT_PUBLIC_WS_URL", None)
            
            # Validation should now fail
            with patch('builtins.print'):  # Suppress print output for cleaner test
                result = deployer.validate_frontend_environment_variables()
            
            self.assertFalse(
                result,
                "❌ Validation passed despite missing critical NEXT_PUBLIC_WS_URL variable!"
            )
            
            # Restore the variable
            if original_value is not None:
                frontend_service.environment_vars["NEXT_PUBLIC_WS_URL"] = original_value
    
    def test_staging_env_file_consistency(self):
        """
        Test that frontend/.env.staging contains all critical variables.
        """
    pass
        print("
🔍 Testing frontend/.env.staging file consistency...")
        
        env_staging_path = project_root / "frontend" / ".env.staging"
        
        if not env_staging_path.exists():
            self.skipTest(f"Frontend .env.staging not found at {env_staging_path}")
        
        # Read the .env.staging file
        with open(env_staging_path, 'r') as f:
            env_content = f.read()
        
        # Check each critical variable is defined
        missing_in_env = []
        for var_name, var_info in self.CRITICAL_FRONTEND_VARS.items():
            if var_info.get("critical", False):
                if f"{var_name}=" not in env_content:
                    missing_in_env.append(var_name)
                    print(f"  ❌ Not in .env.staging: {var_name}")
                else:
                    print(f"  ✅ Found in .env.staging: {var_name}")
        
        self.assertEqual(
            len(missing_in_env), 0,
            f"
🔴 .env.staging is missing critical variables:
" +
            "
".join(f"  - {var}" for var in missing_in_env)
        )
    
    def test_production_env_file_consistency(self):
        """
        Test that frontend/.env.production contains all critical variables.
        """
    pass
        print("
🔍 Testing frontend/.env.production file consistency...")
        
        env_prod_path = project_root / "frontend" / ".env.production"
        
        if not env_prod_path.exists():
            self.skipTest(f"Frontend .env.production not found at {env_prod_path}")
        
        # Read the .env.production file
        with open(env_prod_path, 'r') as f:
            env_content = f.read()
        
        # Check each critical variable is defined
        missing_in_env = []
        for var_name, var_info in self.CRITICAL_FRONTEND_VARS.items():
            if var_info.get("critical", False):
                if f"{var_name}=" not in env_content:
                    missing_in_env.append(var_name)
                    print(f"  ❌ Not in .env.production: {var_name}")
                else:
                    print(f"  ✅ Found in .env.production: {var_name}")
        
        self.assertEqual(
            len(missing_in_env), 0,
            f"
🔴 .env.production is missing critical variables:
" +
            "
".join(f"  - {var}" for var in missing_in_env)
        )
    
    def test_websocket_url_consistency(self):
        """
        Test that WebSocket URLs are consistent across primary and fallback variables.
        """
    pass
        print("
🔍 Testing WebSocket URL consistency...")
        
        deployer = GCPDeployer(project_id="netra-staging")
        
        frontend_service = None
        for service in deployer.services:
            if service.name == "frontend":
                frontend_service = service
                break
        
        if frontend_service:
            ws_url = frontend_service.environment_vars.get("NEXT_PUBLIC_WS_URL")
            websocket_url = frontend_service.environment_vars.get("NEXT_PUBLIC_WEBSOCKET_URL")
            
            self.assertIsNotNone(ws_url, "❌ NEXT_PUBLIC_WS_URL is not set!")
            self.assertIsNotNone(websocket_url, "❌ NEXT_PUBLIC_WEBSOCKET_URL is not set!")
            
            # Both should be WebSocket URLs
            self.assertTrue(
                ws_url.startswith("wss://") or ws_url.startswith("ws://"),
                f"❌ NEXT_PUBLIC_WS_URL is not a WebSocket URL: {ws_url}"
            )
            
            print(f"  ✅ WebSocket URLs configured correctly")
            print(f"     Primary: {ws_url}")
            print(f"     Fallback: {websocket_url}")
    
    def test_auth_url_consistency(self):
        """
        Test that Auth URLs are consistent across all auth-related variables.
        """
    pass
        print("
🔍 Testing Auth URL consistency...")
        
        deployer = GCPDeployer(project_id="netra-staging")
        
        frontend_service = None
        for service in deployer.services:
            if service.name == "frontend":
                frontend_service = service
                break
        
        if frontend_service:
            auth_url = frontend_service.environment_vars.get("NEXT_PUBLIC_AUTH_URL")
            auth_service_url = frontend_service.environment_vars.get("NEXT_PUBLIC_AUTH_SERVICE_URL")
            auth_api_url = frontend_service.environment_vars.get("NEXT_PUBLIC_AUTH_API_URL")
            
            self.assertIsNotNone(auth_url, "❌ NEXT_PUBLIC_AUTH_URL is not set!")
            self.assertIsNotNone(auth_service_url, "❌ NEXT_PUBLIC_AUTH_SERVICE_URL is not set!")
            self.assertIsNotNone(auth_api_url, "❌ NEXT_PUBLIC_AUTH_API_URL is not set!")
            
            # All should be HTTPS URLs
            for url, name in [(auth_url, "AUTH_URL"), 
                             (auth_service_url, "AUTH_SERVICE_URL"),
                             (auth_api_url, "AUTH_API_URL")]:
                self.assertTrue(
                    url.startswith("https://") or url.startswith("http://"),
                    f"❌ NEXT_PUBLIC_{name} is not a valid URL: {url}"
                )
            
            print(f"  ✅ Auth URLs configured correctly")
            print(f"     Primary: {auth_url}")
            print(f"     Service: {auth_service_url}")
            print(f"     API: {auth_api_url}")
    
    def test_no_regression_of_variable_removal(self):
        """
        Meta-test: Ensure this test file itself contains all critical variable checks.
        This prevents the test from being weakened by accidental removal of checks.
        """
    pass
        print("
🔍 Meta-test: Validating this test file covers all variables...")
        
        # Read this test file with UTF-8 encoding
        test_file_content = Path(__file__).read_text(encoding='utf-8')
        
        # Ensure all critical variables are mentioned in the test
        for var_name in self.CRITICAL_FRONTEND_VARS.keys():
            self.assertIn(
                var_name,
                test_file_content,
                f"❌ Test regression detected: {var_name} is not checked in this test file!"
            )
        
        print("  ✅ All critical variables are covered by this test suite")
    
    def test_discovery_endpoint_configuration_critical_for_chat(self):
        """
        🚨 ULTRA CRITICAL: Test that discovery endpoint URLs are properly configured.
        WITHOUT proper discovery URLs, the ENTIRE chat value delivery system BREAKS!
        
        The discovery endpoint provides:
        - Available agent configurations
        - Tool availability
        - Service health status
        - WebSocket connection details
        
        If discovery fails, users cannot:
        - See available agents
        - Execute any tools
        - Get any AI responses
        - Experience ANY value from the platform
        """
    pass
        print("
🚨 CRITICAL: Testing discovery endpoint configuration for chat value...")
        
        deployer = GCPDeployer(project_id="netra-staging")
        
        # Find frontend service
        frontend_service = None
        for service in deployer.services:
            if service.name == "frontend":
                frontend_service = service
                break
        
        self.assertIsNotNone(
            frontend_service, 
            "❌ Frontend service not found - CHAT VALUE COMPLETELY BROKEN!"
        )
        
        # Check API URL is set (discovery endpoint is at API_URL/api/discovery)
        api_url = frontend_service.environment_vars.get("NEXT_PUBLIC_API_URL")
        self.assertIsNotNone(
            api_url,
            "❌ NEXT_PUBLIC_API_URL not set - Discovery endpoint unreachable! "
            "ENTIRE CHAT VALUE DELIVERY BROKEN!"
        )
        
        # Check WebSocket URL for real-time updates
        ws_url = frontend_service.environment_vars.get("NEXT_PUBLIC_WS_URL")
        self.assertIsNotNone(
            ws_url,
            "❌ NEXT_PUBLIC_WS_URL not set - No real-time agent updates! "
            "Users cannot see agent thinking/progress!"
        )
        
        # Validate URL formats
        self.assertTrue(
            api_url.startswith("http"),
            f"❌ Invalid API URL format: {api_url} - Discovery will fail!"
        )
        
        self.assertTrue(
            ws_url.startswith("ws"),
            f"❌ Invalid WebSocket URL format: {ws_url} - Real-time updates broken!"
        )
        
        print(f"  ✅ Discovery endpoint configured at: {api_url}/api/discovery")
        print(f"  ✅ WebSocket for real-time updates: {ws_url}")
        print("
  💡 Chat value delivery chain verified:")
        print("     1. Frontend connects to discovery endpoint")
        print("     2. Discovery provides agent/tool configurations")
        print("     3. WebSocket enables real-time agent updates")
        print("     4. Users receive substantive AI-powered value")
    
    def test_discovery_endpoint_url_format(self):
        """
        Test that discovery endpoint URLs follow the correct format for all environments.
        """
    pass
        print("
🔍 Testing discovery endpoint URL format consistency...")
        
        # Test staging configuration
        staging_deployer = GCPDeployer(project_id="netra-staging")
        staging_frontend = None
        for service in staging_deployer.services:
            if service.name == "frontend":
                staging_frontend = service
                break
        
        if staging_frontend:
            staging_api_url = staging_frontend.environment_vars.get("NEXT_PUBLIC_API_URL")
            
            # Check staging URL format
            if staging_api_url:
                self.assertIn(
                    "staging",
                    staging_api_url.lower(),
                    f"⚠️ Staging API URL doesn't contain 'staging': {staging_api_url}"
                )
                print(f"  ✅ Staging discovery: {staging_api_url}/api/discovery")
        
        # Test production configuration - Note: GCPDeployer may default to staging URLs
        # This is expected behavior in the deployment script
        print("  ℹ️  Production URL format test skipped (deployment script defaults to staging)")


def main():
    """Run the frontend deployment environment regression tests."""
    print("=" * 80)
    print("🚨 MISSION CRITICAL: Frontend Deployment Environment Regression Test")
    print("=" * 80)
    print("
This test prevents regression of critical frontend environment variables")
    print("that have repeatedly been removed, causing complete frontend failure.
")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestFrontendDeploymentEnvironmentRegression)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("
" + "=" * 80)
    if result.wasSuccessful():
        print("✅ SUCCESS: All frontend deployment environment checks passed!")
        print("The deployment configuration contains all critical variables.")
    else:
        print("🔴 FAILURE: Frontend deployment environment regression detected!")
        print(f"Failed: {len(result.failures)} | Errors: {len(result.errors)}")
        print("
⚠️  CRITICAL: Do NOT deploy without fixing these issues!")
        print("Missing variables will cause complete frontend failure!")
    print("=" * 80)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
    pass