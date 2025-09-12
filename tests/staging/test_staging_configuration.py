"""
Test 8: Staging Configuration Validation

CRITICAL: Validate staging configuration across all services.
This ensures environment-specific settings are correctly configured for staging.

Business Value: Platform/Internal - System Stability & Configuration Integrity
Incorrect configuration causes service failures and blocks all user functionality.
"""

import pytest
import httpx
import asyncio
import json
from typing import Dict, Any, List, Optional, Set
from shared.isolated_environment import IsolatedEnvironment
from tests.staging.staging_config import StagingConfig

# Expected Configuration Values for Staging
EXPECTED_STAGING_CONFIG = {
    "environment": "staging",
    "cors_origins": [
        "https://netra-frontend-staging-701982941522.us-central1.run.app",
        "https://app.staging.netrasystems.ai"
    ],
    "redis_ip_prefix": "10.107.0.",  # Should start with this for staging VPC
    "database_ssl": True,
    "default_llm_model": "gemini-2.5-flash"
}

class StagingConfigurationTestRunner:
    """Test runner for staging configuration validation."""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.environment = StagingConfig.get_environment()  # Now defaults to 'staging'
        self.urls = {
            "backend": StagingConfig.get_service_url("NETRA_BACKEND"),
            "auth": StagingConfig.get_service_url("AUTH_SERVICE"),
            "frontend": StagingConfig.get_service_url("FRONTEND")
        }
        self.timeout = StagingConfig.TIMEOUTS["default"]
        self.access_token = None
        
    def get_base_headers(self) -> Dict[str, str]:
        """Get base headers for API requests."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Netra-Staging-Config-Test/1.0"
        }
        
    async def get_test_token(self) -> Optional[str]:
        """Get test token for authenticated endpoints."""
        try:
            simulation_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
            if not simulation_key:
                return None
                
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.urls['auth']}/api/auth/simulate",
                    headers=self.get_base_headers(),
                    json={
                        "simulation_key": simulation_key,
                        "user_id": "staging-config-test-user",
                        "email": "staging-config-test@netrasystems.ai"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("access_token")
                    
        except Exception as e:
            print(f"Token generation failed: {e}")
            
        return None
        
    async def test_environment_configuration(self) -> Dict[str, Any]:
        """Test 8.1: Environment-specific configuration validation."""
        print("8.1 Testing environment configuration...")
        
        results = {}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test backend environment config
                backend_config_response = await client.get(
                    f"{self.urls['backend']}/api/system/config",
                    headers=self.get_base_headers()
                )
                
                backend_config_success = backend_config_response.status_code == 200
                backend_config = {}
                
                if backend_config_success:
                    try:
                        backend_config = backend_config_response.json()
                    except:
                        pass
                        
                # Validate backend environment settings
                backend_env_correct = (
                    backend_config.get("environment") == "staging" if self.environment == "staging" 
                    else backend_config.get("environment") in ["development", "local"]
                )
                
                results["backend_environment"] = {
                    "success": backend_config_success and backend_env_correct,
                    "status_code": backend_config_response.status_code,
                    "environment_value": backend_config.get("environment", "unknown"),
                    "environment_correct": backend_env_correct,
                    "config_data": backend_config
                }
                
                # Test auth service environment config
                auth_config_response = await client.get(
                    f"{self.urls['auth']}/api/system/config",
                    headers=self.get_base_headers()
                )
                
                auth_config_success = auth_config_response.status_code == 200
                auth_config = {}
                
                if auth_config_success:
                    try:
                        auth_config = auth_config_response.json()
                    except:
                        pass
                        
                # Validate auth environment settings
                auth_env_correct = (
                    auth_config.get("environment") == "staging" if self.environment == "staging"
                    else auth_config.get("environment") in ["development", "local"]
                )
                
                results["auth_environment"] = {
                    "success": auth_config_success and auth_env_correct,
                    "status_code": auth_config_response.status_code,
                    "environment_value": auth_config.get("environment", "unknown"),
                    "environment_correct": auth_env_correct,
                    "config_data": auth_config
                }
                
        except Exception as e:
            results["backend_environment"] = {
                "success": False,
                "error": f"Backend config test failed: {str(e)}"
            }
            results["auth_environment"] = {
                "success": False,
                "error": f"Auth config test failed: {str(e)}"
            }
            
        return results
        
    async def test_cors_configuration(self) -> Dict[str, Any]:
        """Test 8.2: CORS configuration validation.""" 
        print("8.2 Testing CORS configuration...")
        
        results = {}
        
        try:
            frontend_origin = self.urls["frontend"]
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test CORS preflight for backend
                backend_cors_response = await client.options(
                    f"{self.urls['backend']}/api/user/profile",
                    headers={
                        "Origin": frontend_origin,
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "Content-Type,Authorization"
                    }
                )
                
                backend_cors_headers = {
                    "allow_origin": backend_cors_response.headers.get("access-control-allow-origin"),
                    "allow_methods": backend_cors_response.headers.get("access-control-allow-methods"),
                    "allow_headers": backend_cors_response.headers.get("access-control-allow-headers"),
                    "allow_credentials": backend_cors_response.headers.get("access-control-allow-credentials")
                }
                
                backend_cors_working = (
                    backend_cors_response.status_code in [200, 204] and
                    backend_cors_headers["allow_origin"] in [frontend_origin, "*"]
                )
                
                results["backend_cors"] = {
                    "success": backend_cors_working,
                    "status_code": backend_cors_response.status_code,
                    "cors_headers": backend_cors_headers,
                    "frontend_origin": frontend_origin,
                    "origin_allowed": backend_cors_headers["allow_origin"] in [frontend_origin, "*"]
                }
                
                # Test CORS preflight for auth service
                auth_cors_response = await client.options(
                    f"{self.urls['auth']}/api/auth/simulate",
                    headers={
                        "Origin": frontend_origin,
                        "Access-Control-Request-Method": "POST",
                        "Access-Control-Request-Headers": "Content-Type,Authorization"
                    }
                )
                
                auth_cors_headers = {
                    "allow_origin": auth_cors_response.headers.get("access-control-allow-origin"),
                    "allow_methods": auth_cors_response.headers.get("access-control-allow-methods"),
                    "allow_headers": auth_cors_response.headers.get("access-control-allow-headers"),
                    "allow_credentials": auth_cors_response.headers.get("access-control-allow-credentials")
                }
                
                auth_cors_working = (
                    auth_cors_response.status_code in [200, 204] and
                    auth_cors_headers["allow_origin"] in [frontend_origin, "*"]
                )
                
                results["auth_cors"] = {
                    "success": auth_cors_working,
                    "status_code": auth_cors_response.status_code,
                    "cors_headers": auth_cors_headers,
                    "frontend_origin": frontend_origin,
                    "origin_allowed": auth_cors_headers["allow_origin"] in [frontend_origin, "*"]
                }
                
        except Exception as e:
            results["backend_cors"] = {
                "success": False,
                "error": f"Backend CORS test failed: {str(e)}"
            }
            results["auth_cors"] = {
                "success": False,
                "error": f"Auth CORS test failed: {str(e)}"
            }
            
        return results
        
    async def test_database_configuration(self) -> Dict[str, Any]:
        """Test 8.3: Database configuration validation."""
        print("8.3 Testing database configuration...")
        
        results = {}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test database configuration endpoint
                db_config_response = await client.get(
                    f"{self.urls['backend']}/api/system/database/config",
                    headers=self.get_base_headers()
                )
                
                db_config_success = db_config_response.status_code == 200
                db_config = {}
                
                if db_config_success:
                    try:
                        db_config = db_config_response.json()
                    except:
                        pass
                        
                # Validate database configuration for staging
                redis_config = db_config.get("redis", {})
                postgres_config = db_config.get("postgres", {})
                clickhouse_config = db_config.get("clickhouse", {})
                
                # For staging, Redis should use VPC IP (10.107.0.x)
                redis_host = redis_config.get("host", "")
                redis_ip_correct = (
                    redis_host.startswith("10.107.0.") if self.environment == "staging"
                    else redis_host in ["localhost", "127.0.0.1", "redis"]
                )
                
                # SSL should be enabled for staging
                postgres_ssl = postgres_config.get("ssl_enabled", False)
                postgres_ssl_correct = (
                    postgres_ssl == True if self.environment == "staging"
                    else postgres_ssl in [True, False]  # Either is ok for local
                )
                
                results["database_config"] = {
                    "success": db_config_success and redis_ip_correct and postgres_ssl_correct,
                    "status_code": db_config_response.status_code,
                    "redis_host": redis_host,
                    "redis_ip_correct": redis_ip_correct,
                    "postgres_ssl_enabled": postgres_ssl,
                    "postgres_ssl_correct": postgres_ssl_correct,
                    "clickhouse_configured": bool(clickhouse_config),
                    "config_summary": {
                        "redis": redis_config,
                        "postgres": postgres_config,
                        "clickhouse": clickhouse_config
                    }
                }
                
        except Exception as e:
            results["database_config"] = {
                "success": False,
                "error": f"Database config test failed: {str(e)}"
            }
            
        return results
        
    async def test_llm_configuration(self) -> Dict[str, Any]:
        """Test 8.4: LLM configuration validation."""
        print("8.4 Testing LLM configuration...")
        
        results = {}
        
        if not self.access_token:
            return {
                "llm_config": {
                    "success": False,
                    "error": "No access token available",
                    "skipped": True
                }
            }
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test LLM configuration endpoint
                llm_config_response = await client.get(
                    f"{self.urls['backend']}/api/system/llm/config",
                    headers={
                        **self.get_base_headers(),
                        "Authorization": f"Bearer {self.access_token}"
                    }
                )
                
                llm_config_success = llm_config_response.status_code == 200
                llm_config = {}
                
                if llm_config_success:
                    try:
                        llm_config = llm_config_response.json()
                    except:
                        pass
                        
                # Validate LLM configuration
                default_model = llm_config.get("default_model", "")
                available_models = llm_config.get("available_models", [])
                
                # Should be using Gemini models in staging
                default_model_correct = "gemini" in default_model.lower()
                has_gemini_models = any("gemini" in model.lower() for model in available_models)
                
                results["llm_config"] = {
                    "success": llm_config_success and default_model_correct,
                    "status_code": llm_config_response.status_code,
                    "default_model": default_model,
                    "default_model_correct": default_model_correct,
                    "available_models": available_models,
                    "has_gemini_models": has_gemini_models,
                    "config_data": llm_config
                }
                
        except Exception as e:
            results["llm_config"] = {
                "success": False,
                "error": f"LLM config test failed: {str(e)}"
            }
            
        return results
        
    async def test_secrets_configuration(self) -> Dict[str, Any]:
        """Test 8.5: Secrets and environment variables validation."""
        print("8.5 Testing secrets configuration...")
        
        results = {}
        
        try:
            # Test required environment variables through API
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test secrets status endpoint
                secrets_response = await client.get(
                    f"{self.urls['backend']}/api/system/secrets/status",
                    headers=self.get_base_headers()
                )
                
                secrets_success = secrets_response.status_code == 200
                secrets_status = {}
                
                if secrets_success:
                    try:
                        secrets_status = secrets_response.json()
                    except:
                        pass
                        
                # Check critical secrets status
                jwt_secret_configured = secrets_status.get("jwt_secret", {}).get("configured", False)
                google_api_key_configured = secrets_status.get("google_api_key", {}).get("configured", False)
                database_url_configured = secrets_status.get("database_url", {}).get("configured", False)
                redis_url_configured = secrets_status.get("redis_url", {}).get("configured", False)
                
                all_secrets_configured = all([
                    jwt_secret_configured,
                    google_api_key_configured,
                    database_url_configured,
                    redis_url_configured
                ])
                
                results["secrets_status"] = {
                    "success": secrets_success and all_secrets_configured,
                    "status_code": secrets_response.status_code,
                    "jwt_secret_configured": jwt_secret_configured,
                    "google_api_key_configured": google_api_key_configured,
                    "database_url_configured": database_url_configured,
                    "redis_url_configured": redis_url_configured,
                    "all_secrets_configured": all_secrets_configured,
                    "secrets_detail": secrets_status
                }
                
                # Test E2E OAuth simulation key
                simulation_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
                
                results["e2e_oauth_key"] = {
                    "success": bool(simulation_key),
                    "configured": bool(simulation_key),
                    "description": "E2E_OAUTH_SIMULATION_KEY for staging testing"
                }
                
        except Exception as e:
            results["secrets_status"] = {
                "success": False,
                "error": f"Secrets status test failed: {str(e)}"
            }
            results["e2e_oauth_key"] = {
                "success": False,
                "error": f"E2E OAuth key check failed: {str(e)}"
            }
            
        return results
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all staging configuration tests."""
        print(f"[U+2699][U+FE0F]  Running Staging Configuration Tests")
        print(f"Environment: {self.environment}")
        print(f"Backend URL: {self.urls['backend']}")
        print(f"Auth URL: {self.urls['auth']}")
        print(f"Frontend URL: {self.urls['frontend']}")
        print()
        
        # Get test token first
        print("[U+1F511] Getting test token...")
        self.access_token = await self.get_test_token()
        print(f"     Token obtained: {bool(self.access_token)}")
        print()
        
        results = {}
        
        # Test 8.1: Environment configuration
        env_results = await self.test_environment_configuration()
        results.update(env_results)
        
        # Test 8.2: CORS configuration
        cors_results = await self.test_cors_configuration()
        results.update(cors_results)
        
        # Test 8.3: Database configuration
        db_results = await self.test_database_configuration()
        results.update(db_results)
        
        # Test 8.4: LLM configuration
        llm_results = await self.test_llm_configuration()
        results.update(llm_results)
        
        # Test 8.5: Secrets configuration
        secrets_results = await self.test_secrets_configuration()
        results.update(secrets_results)
        
        # Calculate summary
        all_tests = {k: v for k, v in results.items() if isinstance(v, dict) and "success" in v}
        total_tests = len(all_tests)
        passed_tests = sum(1 for result in all_tests.values() if result["success"])
        skipped_tests = sum(1 for result in all_tests.values() if result.get("skipped", False))
        
        # Check critical configuration areas
        environment_config_correct = (
            results.get("backend_environment", {}).get("environment_correct", False) and
            results.get("auth_environment", {}).get("environment_correct", False)
        )
        
        cors_config_working = (
            results.get("backend_cors", {}).get("success", False) and
            results.get("auth_cors", {}).get("success", False)
        )
        
        database_config_correct = results.get("database_config", {}).get("success", False)
        secrets_all_configured = results.get("secrets_status", {}).get("all_secrets_configured", False)
        
        results["summary"] = {
            "environment_config_correct": environment_config_correct,
            "cors_config_working": cors_config_working,
            "database_config_correct": database_config_correct,
            "secrets_all_configured": secrets_all_configured,
            "configuration_valid": all([environment_config_correct, cors_config_working, database_config_correct, secrets_all_configured]),
            "environment": self.environment,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "skipped_tests": skipped_tests,
            "critical_config_issues": not all([environment_config_correct, cors_config_working, secrets_all_configured])
        }
        
        print()
        print(f" CHART:  Summary: {results['summary']['passed_tests']}/{results['summary']['total_tests']} tests passed ({results['summary']['skipped_tests']} skipped)")
        print(f"[U+1F30D] Environment config: {' PASS:  Correct' if environment_config_correct else ' FAIL:  Issues'}")
        print(f"[U+1F517] CORS config: {' PASS:  Working' if cors_config_working else ' FAIL:  Issues'}")
        print(f"[U+1F5C3][U+FE0F]  Database config: {' PASS:  Correct' if database_config_correct else ' FAIL:  Issues'}")
        print(f"[U+1F510] Secrets config: {' PASS:  All configured' if secrets_all_configured else ' FAIL:  Missing secrets'}")
        
        if results["summary"]["critical_config_issues"]:
            print(" ALERT:  CRITICAL: Configuration issues detected!")
            
        return results


@pytest.mark.asyncio
@pytest.mark.staging
async def test_staging_configuration():
    """Main test entry point for staging configuration validation."""
    runner = StagingConfigurationTestRunner()
    results = await runner.run_all_tests()
    
    # Assert critical conditions
    assert results["summary"]["configuration_valid"], "Staging configuration is invalid"
    assert not results["summary"]["critical_config_issues"], "Critical configuration issues detected"
    assert results["summary"]["secrets_all_configured"], "Not all required secrets are configured"


if __name__ == "__main__":
    async def main():
        runner = StagingConfigurationTestRunner()
        results = await runner.run_all_tests()
        
        if results["summary"]["critical_config_issues"]:
            exit(1)
            
    asyncio.run(main())