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
        self.original_values = {}
        env_vars = ['SECRET_KEY', 'ENV', 'GCP_PROJECT', 'DATABASE_URL', 'REDIS_URL']
        for var in env_vars:
            self.original_values[var] = self.env.get(var)

    def teardown_method(self, method=None):
        """Restore original environment state."""
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
        self.env.set('ENV', 'staging')
        self.env.set('GCP_PROJECT', 'netra-staging')
        self.env.unset('SECRET_KEY')
        try:
            from netra_backend.app.core.configuration.base import get_unified_config
            from netra_backend.app.core.middleware_setup import setup_middleware
            config = get_unified_config(environment='staging', isolated_env=self.env)
            secret_key = getattr(config, 'secret_key', None)
            if secret_key is None or len(str(secret_key)) < 32:
                raise ValueError(f'GCP STAGING FAILURE: SECRET_KEY not properly configured. Got: {secret_key} (length: {(len(str(secret_key)) if secret_key else 0)}). Required: 32+ characters for SessionMiddleware in staging environment.')
            print(f' WARNING: [U+FE0F]  SECRET_KEY LOADED: {secret_key[:8]}... (length: {len(secret_key)})')
            app = FastAPI()
            setup_middleware(app, config=config)

            @app.get('/test')
            async def test_endpoint(request: Request):
                request.session['test'] = 'gcp-staging-test'
                return {'message': 'success'}
            with TestClient(app) as client:
                response = client.get('/test')
                if response.status_code != 200:
                    raise RuntimeError(f'GCP STAGING MIDDLEWARE FAILURE: Setup succeeded but request failed. Status: {response.status_code}')
            print(' WARNING: [U+FE0F]  GCP STAGING SECRET_KEY LOADING: Working properly, issue not reproduced')
        except (ValueError, RuntimeError, ImportError, AttributeError) as e:
            self._track_metric('secret_key_failures', 'gcp_staging_config_error', 1)
            print(f' PASS:  REPRODUCED: GCP staging SECRET_KEY failure - {str(e)}')
            raise AssertionError(f'GCP STAGING SECRET_KEY CHAIN FAILURE: {str(e)}. This reproduces the $500K+ ARR authentication failures in staging.')

    def test_middleware_setup_with_gcp_staging_config(self):
        """
        TEST DESIGNED TO FAIL: Middleware setup with real GCP staging configuration.
        
        REPRODUCES: Middleware installation failures with staging environment config
        BUSINESS IMPACT: Authentication middleware not properly initialized
        """
        self.env.set('ENV', 'staging')
        self.env.set('GCP_PROJECT', 'netra-staging')
        test_scenarios = [{'name': 'short_secret_key', 'secret_key': 'short_key', 'expected_error': 'at least 32 characters'}, {'name': 'empty_secret_key', 'secret_key': '', 'expected_error': 'SECRET_KEY'}, {'name': 'none_secret_key', 'secret_key': None, 'expected_error': 'SECRET_KEY'}, {'name': 'whitespace_secret_key', 'secret_key': '   \n\t   ', 'expected_error': 'SECRET_KEY'}]
        failed_scenarios = []
        for scenario in test_scenarios:
            try:
                if scenario['secret_key'] is None:
                    self.env.unset('SECRET_KEY')
                else:
                    self.env.set('SECRET_KEY', scenario['secret_key'])
                from netra_backend.app.core.app_factory import create_app
                app = create_app(isolated_env=self.env)

                @app.get('/test')
                async def test_endpoint(request: Request):
                    request.session['test'] = f"test_{scenario['name']}"
                    return {'message': 'success'}
                with TestClient(app) as client:
                    response = client.get('/test')
                    print(f" WARNING: [U+FE0F]  SCENARIO NOT REPRODUCED: {scenario['name']} - Response: {response.status_code}")
            except Exception as e:
                error_message = str(e)
                if scenario['expected_error'].lower() in error_message.lower():
                    failed_scenarios.append({'scenario': scenario['name'], 'error': error_message, 'expected': scenario['expected_error']})
                    print(f" PASS:  REPRODUCED: {scenario['name']} - {error_message}")
                else:
                    print(f" WARNING: [U+FE0F]  DIFFERENT ERROR: {scenario['name']} - {error_message}")
                    failed_scenarios.append({'scenario': scenario['name'], 'error': error_message, 'expected': scenario['expected_error'], 'unexpected': True})
        self._track_metric('secret_key_failures', 'gcp_middleware_setup_failures', len(failed_scenarios))
        if failed_scenarios:
            error_details = '\n'.join([f"- {s['scenario']}: {s['error']}" for s in failed_scenarios])
            raise AssertionError(f'GCP STAGING MIDDLEWARE SETUP FAILURES REPRODUCED ({len(failed_scenarios)} scenarios):\n{error_details}\nThese failures reproduce the SessionMiddleware installation issues blocking $500K+ ARR.')
        else:
            print(' WARNING: [U+FE0F]  NO FAILURES REPRODUCED: All scenarios passed unexpectedly')

    def test_auth_context_middleware_session_access(self):
        """
        TEST DESIGNED TO FAIL: Auth context middleware accessing session data.
        
        REPRODUCES: GCPAuthContextMiddleware trying to access request.session
        before SessionMiddleware is properly installed.
        
        BUSINESS IMPACT: Authentication context lost, breaking user isolation
        """
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        self.env.set('ENV', 'staging')
        self.env.set('SECRET_KEY', 'valid-32-character-secret-key-for-testing-auth-context-middleware')
        app = FastAPI()
        app.add_middleware(GCPAuthContextMiddleware, enable_user_isolation=True)
        app.add_middleware(SessionMiddleware, secret_key=self.env.get('SECRET_KEY'), same_site='lax', https_only=True)
        session_access_error = None
        auth_context_captured = None

        @app.middleware('http')
        async def capture_auth_context(request: Request, call_next):
            nonlocal session_access_error, auth_context_captured
            try:
                if hasattr(request, 'session'):
                    user_id = request.session.get('user_id')
                    session_id = request.session.get('session_id')
                    auth_context_captured = {'user_id': user_id, 'session_id': session_id, 'has_session': True}
                else:
                    auth_context_captured = {'has_session': False, 'error': 'request.session not available'}
            except Exception as e:
                session_access_error = str(e)
                auth_context_captured = {'error': session_access_error, 'has_session': False}
            response = await call_next(request)
            return response

        @app.get('/test')
        async def test_endpoint(request: Request):
            request.session['user_id'] = 'staging-user-123'
            request.session['session_id'] = 'staging-session-456'
            return {'message': 'session_set', 'auth_context': auth_context_captured, 'session_error': session_access_error}
        with TestClient(app) as client:
            response = client.get('/test')
            data = response.json()
            if session_access_error:
                self._track_metric('secret_key_failures', 'auth_context_session_timing_error', 1)
                print(f' PASS:  REPRODUCED: Auth context session access error - {session_access_error}')
                raise AssertionError(f'AUTH CONTEXT SESSION ACCESS FAILURE: {session_access_error}. This reproduces the middleware order issue causing authentication context loss. Full response: {data}')
            elif auth_context_captured and (not auth_context_captured.get('has_session', True)):
                self._track_metric('secret_key_failures', 'auth_context_no_session_access', 1)
                print(f' PASS:  REPRODUCED: Auth context missing session access - {auth_context_captured}')
                raise AssertionError(f'AUTH CONTEXT SESSION MISSING: GCP middleware cannot access session data. Context: {auth_context_captured}. This reproduces the user isolation failure.')
            else:
                print(f' WARNING: [U+FE0F]  SESSION ACCESS WORKED: {data}')
                print(' WARNING: [U+FE0F]  Auth context session access issue not reproduced')

    def test_configuration_chain_secret_key_precedence(self):
        """
        TEST DESIGNED TO FAIL: Configuration chain SECRET_KEY precedence issues.
        
        REPRODUCES: Configuration system loading wrong SECRET_KEY or ignoring environment
        BUSINESS IMPACT: Production systems using development keys, security vulnerabilities
        """
        precedence_scenarios = [{'name': 'env_override_ignored', 'env_secret': 'environment-secret-key-32-chars-minimum-length-required', 'config_secret': 'config-secret-short', 'expected_source': 'environment', 'should_fail_on': 'config precedence'}, {'name': 'production_using_dev_key', 'env_secret': 'dev-secret-key', 'environment': 'production', 'should_fail_on': 'length validation'}, {'name': 'staging_fallback_failure', 'env_secret': None, 'config_secret': None, 'environment': 'staging', 'should_fail_on': 'missing key'}]
        configuration_failures = []
        for scenario in precedence_scenarios:
            try:
                if scenario.get('env_secret'):
                    self.env.set('SECRET_KEY', scenario['env_secret'])
                else:
                    self.env.unset('SECRET_KEY')
                env_name = scenario.get('environment', 'staging')
                self.env.set('ENV', env_name)
                from netra_backend.app.core.configuration.base import get_unified_config
                config = get_unified_config(environment=env_name, isolated_env=self.env)
                actual_secret = getattr(config, 'secret_key', None)
                if scenario['name'] == 'env_override_ignored':
                    if actual_secret != scenario['env_secret']:
                        raise ValueError(f"CONFIGURATION PRECEDENCE FAILURE: Environment SECRET_KEY ignored. Expected: {scenario['env_secret']}, Got: {actual_secret}")
                elif scenario['name'] == 'production_using_dev_key':
                    if actual_secret and len(actual_secret) < 32:
                        raise ValueError(f'PRODUCTION SECURITY FAILURE: Short SECRET_KEY accepted in production. Key length: {len(actual_secret)}, Required: 32+')
                elif scenario['name'] == 'staging_fallback_failure':
                    if actual_secret is None:
                        raise ValueError(f'STAGING FALLBACK FAILURE: No SECRET_KEY available and no fallback generated. Environment: {env_name}')
                print(f" WARNING: [U+FE0F]  SCENARIO NOT REPRODUCED: {scenario['name']} - Key loaded: {(actual_secret[:8] if actual_secret else None)}...")
            except Exception as e:
                error_message = str(e)
                configuration_failures.append({'scenario': scenario['name'], 'error': error_message, 'should_fail_on': scenario['should_fail_on']})
                print(f" PASS:  REPRODUCED: {scenario['name']} - {error_message}")
        if configuration_failures:
            self._track_metric('secret_key_failures', 'configuration_chain_failures', len(configuration_failures))
            error_details = '\n'.join([f"- {f['scenario']}: {f['error']}" for f in configuration_failures])
            raise AssertionError(f'CONFIGURATION CHAIN FAILURES REPRODUCED ({len(configuration_failures)} scenarios):\n{error_details}\nThese configuration chain failures reproduce SECRET_KEY loading issues in production.')
        else:
            print(' WARNING: [U+FE0F]  CONFIGURATION CHAIN: All scenarios passed, issues not reproduced')

    @pytest.mark.asyncio
    async def test_async_middleware_secret_key_loading_race(self):
        """
        TEST DESIGNED TO FAIL: Async middleware SECRET_KEY loading race conditions.
        
        REPRODUCES: Race conditions in async middleware initialization
        BUSINESS IMPACT: Intermittent authentication failures under load
        """
        self.env.set('ENV', 'staging')
        race_secret = 'async-race-condition-test-secret-key-32-chars-minimum-length-required'
        self.env.set('SECRET_KEY', race_secret)
        initialization_errors = []
        successful_initializations = 0

        async def create_app_with_middleware():
            """Create app with middleware - might race with other instances."""
            try:
                from netra_backend.app.core.app_factory import create_app
                await asyncio.sleep(0.001)
                app = create_app(isolated_env=self.env)

                @app.get('/race-test')
                async def test_endpoint(request: Request):
                    request.session['race_test'] = 'success'
                    return {'message': 'success'}
                with TestClient(app) as client:
                    response = client.get('/race-test')
                    if response.status_code == 200:
                        return {'status': 'success', 'response': response.json()}
                    else:
                        raise RuntimeError(f'Middleware test failed: {response.status_code}')
            except Exception as e:
                initialization_errors.append(str(e))
                return {'status': 'error', 'error': str(e)}
        tasks = [create_app_with_middleware() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, dict) and result.get('status') == 'success':
                successful_initializations += 1
            elif isinstance(result, Exception):
                initialization_errors.append(str(result))
        if initialization_errors:
            self._track_metric('secret_key_failures', 'async_middleware_race_conditions', len(initialization_errors))
            error_summary = '\n'.join([f'- {error}' for error in initialization_errors[:3]])
            print(f' PASS:  REPRODUCED: Async middleware race conditions - {len(initialization_errors)} errors')
            raise AssertionError(f'ASYNC MIDDLEWARE RACE CONDITIONS REPRODUCED:\nSuccessful: {successful_initializations}, Failed: {len(initialization_errors)}\nSample errors:\n{error_summary}\nThese race conditions reproduce authentication failures under concurrent load.')
        else:
            print(f' WARNING: [U+FE0F]  RACE CONDITIONS NOT REPRODUCED: All {successful_initializations} initializations succeeded')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')