"""
Integration tests for SECRET_KEY loading chain failures - Issue #169.

CRITICAL: These tests SHOULD FAIL initially to reproduce the exact SECRET_KEY
loading and validation failures causing SessionMiddleware installation issues.

ERROR PATTERNS TO REPRODUCE:
- SECRET_KEY loading failures in GCP staging environment
- Configuration chain breakdowns leading to middleware installation failures  
- Environment-specific SECRET_KEY validation bypasses
- Middleware setup timing issues with configuration loading

BUSINESS IMPACT: $500K+ ARR authentication flows failing due to SECRET_KEY issues
ESCALATION: From 15-30 seconds to 40+ occurrences per day
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, Mock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestSecretKeyLoadingChainFailure(SSotAsyncTestCase):
    """Integration tests designed to FAIL and reproduce SECRET_KEY loading chain issues."""
    
    def setup_method(self, method=None):
        """Set up test environment with clean state."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        
        # Store original values for cleanup
        self.original_values = {}
        env_vars = ["SECRET_KEY", "ENV", "GCP_PROJECT", "DATABASE_URL", "REDIS_URL"]
        for var in env_vars:
            self.original_values[var] = self.env.get(var)
            
    def teardown_method(self, method=None):
        """Restore original environment state."""
        # Restore all original values
        for var, value in self.original_values.items():
            if value is not None:
                self.env.set(var, value)
            else:
                self.env.unset(var)
                
        super().teardown_method(method)

    def test_gcp_staging_environment_secret_key_detection(self):
        """
        TEST DESIGNED TO FAIL: SECRET_KEY detection in GCP staging environment.
        
        REPRODUCES: Configuration loading failures in GCP Cloud Run staging
        BUSINESS IMPACT: Complete authentication system failure in staging
        """
        # Simulate GCP staging environment (where failures are occurring)
        self.env.set("ENV", "staging")
        self.env.set("GCP_PROJECT", "netra-staging")
        
        # FAILING SCENARIO: SECRET_KEY not properly configured in GCP staging
        self.env.unset("SECRET_KEY")  # Simulate missing SECRET_KEY in GCP
        
        try:
            # Try to load configuration using the real configuration system
            from netra_backend.app.core.configuration.base import get_unified_config
            from netra_backend.app.core.middleware_setup import setup_middleware
            
            # EXPECTED TO FAIL: Configuration should detect missing SECRET_KEY
            config = get_unified_config(environment="staging", isolated_env=self.env)
            
            # Check if SECRET_KEY is properly loaded
            secret_key = getattr(config, 'secret_key', None)
            
            if secret_key is None or len(str(secret_key)) < 32:
                raise ValueError(
                    f"GCP STAGING FAILURE: SECRET_KEY not properly configured. "
                    f"Got: {secret_key} (length: {len(str(secret_key)) if secret_key else 0}). "
                    f"Required: 32+ characters for SessionMiddleware in staging environment."
                )
            
            # If we get here, SECRET_KEY was loaded - test might need adjustment
            print(f" WARNING: [U+FE0F]  SECRET_KEY LOADED: {secret_key[:8]}... (length: {len(secret_key)})")
            
            # EXPECTED TO FAIL: Try to use this config with middleware
            app = FastAPI()
            setup_middleware(app, config=config)
            
            @app.get("/test")
            async def test_endpoint(request: Request):
                request.session["test"] = "gcp-staging-test"
                return {"message": "success"}
            
            # Test if middleware actually works
            with TestClient(app) as client:
                response = client.get("/test")
                
                # If this succeeds, the SECRET_KEY loading is working
                if response.status_code != 200:
                    raise RuntimeError(
                        f"GCP STAGING MIDDLEWARE FAILURE: Setup succeeded but request failed. "
                        f"Status: {response.status_code}"
                    )
            
            # If we reach here, the test didn't reproduce the issue
            print(" WARNING: [U+FE0F]  GCP STAGING SECRET_KEY LOADING: Working properly, issue not reproduced")
            
        except (ValueError, RuntimeError, ImportError, AttributeError) as e:
            # EXPECTED: These errors reproduce the actual issue
            self._track_metric("secret_key_failures", "gcp_staging_config_error", 1)
            print(f" PASS:  REPRODUCED: GCP staging SECRET_KEY failure - {str(e)}")
            
            # Re-raise to make test fail as expected
            raise AssertionError(
                f"GCP STAGING SECRET_KEY CHAIN FAILURE: {str(e)}. "
                f"This reproduces the $500K+ ARR authentication failures in staging."
            )

    def test_middleware_setup_with_gcp_staging_config(self):
        """
        TEST DESIGNED TO FAIL: Middleware setup with real GCP staging configuration.
        
        REPRODUCES: Middleware installation failures with staging environment config
        BUSINESS IMPACT: Authentication middleware not properly initialized
        """
        # Simulate exact GCP staging environment
        self.env.set("ENV", "staging") 
        self.env.set("GCP_PROJECT", "netra-staging")
        
        # Test different SECRET_KEY scenarios that cause failures
        test_scenarios = [
            # Scenario 1: Too short SECRET_KEY 
            {
                "name": "short_secret_key",
                "secret_key": "short_key",
                "expected_error": "at least 32 characters"
            },
            # Scenario 2: Empty SECRET_KEY
            {
                "name": "empty_secret_key", 
                "secret_key": "",
                "expected_error": "SECRET_KEY"
            },
            # Scenario 3: None SECRET_KEY
            {
                "name": "none_secret_key",
                "secret_key": None,
                "expected_error": "SECRET_KEY"
            },
            # Scenario 4: Whitespace-only SECRET_KEY
            {
                "name": "whitespace_secret_key",
                "secret_key": "   \n\t   ",
                "expected_error": "SECRET_KEY"
            }
        ]
        
        failed_scenarios = []
        
        for scenario in test_scenarios:
            try:
                # Set up the failing SECRET_KEY
                if scenario["secret_key"] is None:
                    self.env.unset("SECRET_KEY")
                else:
                    self.env.set("SECRET_KEY", scenario["secret_key"])
                
                # Try to create app with middleware using real setup
                from netra_backend.app.core.app_factory import create_app
                
                # EXPECTED TO FAIL: App creation should fail with bad SECRET_KEY
                app = create_app(isolated_env=self.env)
                
                # If app creation succeeded, try to use it
                @app.get("/test")
                async def test_endpoint(request: Request):
                    request.session["test"] = f"test_{scenario['name']}"
                    return {"message": "success"}
                
                with TestClient(app) as client:
                    response = client.get("/test")
                    
                    # If we get here, the scenario didn't fail as expected
                    print(f" WARNING: [U+FE0F]  SCENARIO NOT REPRODUCED: {scenario['name']} - Response: {response.status_code}")
                    
            except Exception as e:
                error_message = str(e)
                
                # Check if we got the expected error
                if scenario["expected_error"].lower() in error_message.lower():
                    failed_scenarios.append({
                        "scenario": scenario["name"],
                        "error": error_message,
                        "expected": scenario["expected_error"]
                    })
                    print(f" PASS:  REPRODUCED: {scenario['name']} - {error_message}")
                else:
                    print(f" WARNING: [U+FE0F]  DIFFERENT ERROR: {scenario['name']} - {error_message}")
                    failed_scenarios.append({
                        "scenario": scenario["name"], 
                        "error": error_message,
                        "expected": scenario["expected_error"],
                        "unexpected": True
                    })
        
        # Track metrics
        self._track_metric("secret_key_failures", "gcp_middleware_setup_failures", len(failed_scenarios))
        
        # Test should fail if we reproduced the expected failures
        if failed_scenarios:
            error_details = "\n".join([
                f"- {s['scenario']}: {s['error']}"
                for s in failed_scenarios
            ])
            
            raise AssertionError(
                f"GCP STAGING MIDDLEWARE SETUP FAILURES REPRODUCED ({len(failed_scenarios)} scenarios):\n"
                f"{error_details}\n"
                f"These failures reproduce the SessionMiddleware installation issues blocking $500K+ ARR."
            )
        else:
            print(" WARNING: [U+FE0F]  NO FAILURES REPRODUCED: All scenarios passed unexpectedly")

    def test_auth_context_middleware_session_access(self):
        """
        TEST DESIGNED TO FAIL: Auth context middleware accessing session data.
        
        REPRODUCES: GCPAuthContextMiddleware trying to access request.session
        before SessionMiddleware is properly installed.
        
        BUSINESS IMPACT: Authentication context lost, breaking user isolation
        """
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        
        # Set up GCP staging environment
        self.env.set("ENV", "staging")
        self.env.set("SECRET_KEY", "valid-32-character-secret-key-for-testing-auth-context-middleware")
        
        app = FastAPI()
        
        # WRONG SETUP: Install GCP auth middleware first (before SessionMiddleware)
        app.add_middleware(GCPAuthContextMiddleware, enable_user_isolation=True)
        
        # Install SessionMiddleware AFTER (too late for GCP middleware to use)
        app.add_middleware(
            SessionMiddleware,
            secret_key=self.env.get("SECRET_KEY"),
            same_site="lax", 
            https_only=True
        )
        
        session_access_error = None
        auth_context_captured = None
        
        @app.middleware("http")
        async def capture_auth_context(request: Request, call_next):
            nonlocal session_access_error, auth_context_captured
            
            try:
                # Simulate what GCPAuthContextMiddleware does - access session data
                if hasattr(request, 'session'):
                    # Try to access session to capture auth context
                    user_id = request.session.get("user_id")
                    session_id = request.session.get("session_id")
                    
                    auth_context_captured = {
                        "user_id": user_id,
                        "session_id": session_id,
                        "has_session": True
                    }
                else:
                    auth_context_captured = {
                        "has_session": False,
                        "error": "request.session not available"
                    }
                
            except Exception as e:
                session_access_error = str(e)
                auth_context_captured = {
                    "error": session_access_error,
                    "has_session": False
                }
            
            response = await call_next(request)
            return response
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            # Set session data (this should work since SessionMiddleware is installed)
            request.session["user_id"] = "staging-user-123"
            request.session["session_id"] = "staging-session-456"
            
            return {
                "message": "session_set",
                "auth_context": auth_context_captured,
                "session_error": session_access_error
            }
        
        # EXPECTED TO FAIL: Session access timing should cause issues
        with TestClient(app) as client:
            response = client.get("/test")
            data = response.json()
            
            # Check if we reproduced the session access timing issue
            if session_access_error:
                self._track_metric("secret_key_failures", "auth_context_session_timing_error", 1)
                print(f" PASS:  REPRODUCED: Auth context session access error - {session_access_error}")
                
                raise AssertionError(
                    f"AUTH CONTEXT SESSION ACCESS FAILURE: {session_access_error}. "
                    f"This reproduces the middleware order issue causing authentication context loss. "
                    f"Full response: {data}"
                )
                
            elif auth_context_captured and not auth_context_captured.get("has_session", True):
                self._track_metric("secret_key_failures", "auth_context_no_session_access", 1) 
                print(f" PASS:  REPRODUCED: Auth context missing session access - {auth_context_captured}")
                
                raise AssertionError(
                    f"AUTH CONTEXT SESSION MISSING: GCP middleware cannot access session data. "
                    f"Context: {auth_context_captured}. This reproduces the user isolation failure."
                )
                
            else:
                print(f" WARNING: [U+FE0F]  SESSION ACCESS WORKED: {data}")
                print(" WARNING: [U+FE0F]  Auth context session access issue not reproduced")

    def test_configuration_chain_secret_key_precedence(self):
        """
        TEST DESIGNED TO FAIL: Configuration chain SECRET_KEY precedence issues.
        
        REPRODUCES: Configuration system loading wrong SECRET_KEY or ignoring environment
        BUSINESS IMPACT: Production systems using development keys, security vulnerabilities
        """
        # Test configuration precedence chain failures
        precedence_scenarios = [
            {
                "name": "env_override_ignored",
                "env_secret": "environment-secret-key-32-chars-minimum-length-required",
                "config_secret": "config-secret-short",
                "expected_source": "environment",
                "should_fail_on": "config precedence"
            },
            {
                "name": "production_using_dev_key", 
                "env_secret": "dev-secret-key",  # Too short for production
                "environment": "production",
                "should_fail_on": "length validation"
            },
            {
                "name": "staging_fallback_failure",
                "env_secret": None,  # No env var
                "config_secret": None,  # No config
                "environment": "staging", 
                "should_fail_on": "missing key"
            }
        ]
        
        configuration_failures = []
        
        for scenario in precedence_scenarios:
            try:
                # Set up scenario environment
                if scenario.get("env_secret"):
                    self.env.set("SECRET_KEY", scenario["env_secret"])
                else:
                    self.env.unset("SECRET_KEY")
                
                env_name = scenario.get("environment", "staging")
                self.env.set("ENV", env_name)
                
                # Try to load configuration
                from netra_backend.app.core.configuration.base import get_unified_config
                
                # EXPECTED TO FAIL: Configuration chain should detect issues
                config = get_unified_config(environment=env_name, isolated_env=self.env)
                
                # Check the loaded SECRET_KEY
                actual_secret = getattr(config, 'secret_key', None)
                
                # Validate according to scenario expectations
                if scenario["name"] == "env_override_ignored":
                    # Environment should override config
                    if actual_secret != scenario["env_secret"]:
                        raise ValueError(
                            f"CONFIGURATION PRECEDENCE FAILURE: Environment SECRET_KEY ignored. "
                            f"Expected: {scenario['env_secret']}, Got: {actual_secret}"
                        )
                        
                elif scenario["name"] == "production_using_dev_key":
                    # Production should reject short keys
                    if actual_secret and len(actual_secret) < 32:
                        raise ValueError(
                            f"PRODUCTION SECURITY FAILURE: Short SECRET_KEY accepted in production. "
                            f"Key length: {len(actual_secret)}, Required: 32+"
                        )
                        
                elif scenario["name"] == "staging_fallback_failure":
                    # Should fail when no key available
                    if actual_secret is None:
                        raise ValueError(
                            f"STAGING FALLBACK FAILURE: No SECRET_KEY available and no fallback generated. "
                            f"Environment: {env_name}"
                        )
                
                # If we get here without error, scenario didn't fail as expected
                print(f" WARNING: [U+FE0F]  SCENARIO NOT REPRODUCED: {scenario['name']} - Key loaded: {actual_secret[:8] if actual_secret else None}...")
                
            except Exception as e:
                error_message = str(e)
                configuration_failures.append({
                    "scenario": scenario["name"],
                    "error": error_message,
                    "should_fail_on": scenario["should_fail_on"]
                })
                
                print(f" PASS:  REPRODUCED: {scenario['name']} - {error_message}")
        
        # Track metrics and fail test if issues were reproduced
        if configuration_failures:
            self._track_metric("secret_key_failures", "configuration_chain_failures", len(configuration_failures))
            
            error_details = "\n".join([
                f"- {f['scenario']}: {f['error']}"
                for f in configuration_failures
            ])
            
            raise AssertionError(
                f"CONFIGURATION CHAIN FAILURES REPRODUCED ({len(configuration_failures)} scenarios):\n"
                f"{error_details}\n"
                f"These configuration chain failures reproduce SECRET_KEY loading issues in production."
            )
        else:
            print(" WARNING: [U+FE0F]  CONFIGURATION CHAIN: All scenarios passed, issues not reproduced")

    @pytest.mark.asyncio
    async def test_async_middleware_secret_key_loading_race(self):
        """
        TEST DESIGNED TO FAIL: Async middleware SECRET_KEY loading race conditions.
        
        REPRODUCES: Race conditions in async middleware initialization
        BUSINESS IMPACT: Intermittent authentication failures under load
        """
        # Set up race condition scenario
        self.env.set("ENV", "staging")
        
        # Use a SECRET_KEY that might cause timing issues during initialization
        race_secret = "async-race-condition-test-secret-key-32-chars-minimum-length-required"
        self.env.set("SECRET_KEY", race_secret)
        
        initialization_errors = []
        successful_initializations = 0
        
        async def create_app_with_middleware():
            """Create app with middleware - might race with other instances."""
            try:
                from netra_backend.app.core.app_factory import create_app
                
                # Add small delay to increase race condition chances
                await asyncio.sleep(0.001)
                
                app = create_app(isolated_env=self.env)
                
                # Test the middleware immediately
                @app.get("/race-test")
                async def test_endpoint(request: Request):
                    request.session["race_test"] = "success"
                    return {"message": "success"}
                
                # Verify middleware works
                with TestClient(app) as client:
                    response = client.get("/race-test")
                    if response.status_code == 200:
                        return {"status": "success", "response": response.json()}
                    else:
                        raise RuntimeError(f"Middleware test failed: {response.status_code}")
                        
            except Exception as e:
                initialization_errors.append(str(e))
                return {"status": "error", "error": str(e)}
        
        # EXPECTED TO FAIL: Concurrent initialization should reveal race conditions
        tasks = [create_app_with_middleware() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results for race conditions
        for result in results:
            if isinstance(result, dict) and result.get("status") == "success":
                successful_initializations += 1
            elif isinstance(result, Exception):
                initialization_errors.append(str(result))
        
        # Check if we reproduced race conditions
        if initialization_errors:
            self._track_metric("secret_key_failures", "async_middleware_race_conditions", len(initialization_errors))
            
            error_summary = "\n".join([f"- {error}" for error in initialization_errors[:3]])
            print(f" PASS:  REPRODUCED: Async middleware race conditions - {len(initialization_errors)} errors")
            
            raise AssertionError(
                f"ASYNC MIDDLEWARE RACE CONDITIONS REPRODUCED:\n"
                f"Successful: {successful_initializations}, Failed: {len(initialization_errors)}\n"
                f"Sample errors:\n{error_summary}\n"
                f"These race conditions reproduce authentication failures under concurrent load."
            )
        else:
            print(f" WARNING: [U+FE0F]  RACE CONDITIONS NOT REPRODUCED: All {successful_initializations} initializations succeeded")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])