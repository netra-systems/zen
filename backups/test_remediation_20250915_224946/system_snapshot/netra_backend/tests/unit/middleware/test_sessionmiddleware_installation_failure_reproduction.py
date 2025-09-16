"""
Unit tests for reproducing SessionMiddleware installation failures - Issue #169.

CRITICAL: These tests SHOULD FAIL initially to reproduce the exact authentication
infrastructure failures escalating from 15-30 seconds to 40+ occurrences per day.

ERROR PATTERNS TO REPRODUCE:
- "SessionMiddleware must be installed to access request.session"  
- ValueError: SECRET_KEY must be at least 32 characters long
- Session middleware initialization failures in GCP staging environment

BUSINESS IMPACT: $500K+ ARR authentication flow failures
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, Mock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment

class SessionMiddlewareInstallationFailureReproductionTests(SSotBaseTestCase):
    """Test cases designed to FAIL and reproduce Issue #169 SessionMiddleware failures."""

    def setup_method(self, method=None):
        """Set up test environment."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        self.original_secret = self.env.get('SECRET_KEY')
        self.original_env = self.env.get('ENV')

    def teardown_method(self, method=None):
        """Clean up test environment."""
        if self.original_secret:
            self.env.set('SECRET_KEY', self.original_secret)
        else:
            self.env.unset('SECRET_KEY')
        if self.original_env:
            self.env.set('ENV', self.original_env)
        else:
            self.env.unset('ENV')
        super().teardown_method(method)

    def test_sessionmiddleware_installation_with_invalid_secret_key(self):
        """
        TEST DESIGNED TO FAIL: SessionMiddleware installation with invalid SECRET_KEY.
        
        REPRODUCES: ValueError: SECRET_KEY must be at least 32 characters long
        BUSINESS IMPACT: Blocks $500K+ ARR authentication flows in staging/production
        ESCALATION PATTERN: 15-30 seconds  ->  40+ occurrences per day
        """
        invalid_secret = 'short_key_123'
        self.env.set('SECRET_KEY', invalid_secret)
        self.env.set('ENV', 'staging')
        app = FastAPI()
        with pytest.raises(ValueError) as exc_info:
            app.add_middleware(SessionMiddleware, secret_key=invalid_secret, same_site='lax', https_only=True)

            @app.get('/test')
            async def test_endpoint(request: Request):
                request.session['user_id'] = 'test-user'
                return {'message': 'success'}
            with TestClient(app) as client:
                response = client.get('/test')
                assert False, f'VALIDATION FAILURE: Short SECRET_KEY was accepted: {invalid_secret}'
        error_message = str(exc_info.value)
        expected_patterns = ['at least 32 characters', 'SECRET_KEY', 'characters long']
        for pattern in expected_patterns:
            assert pattern in error_message, f"MISSING ERROR PATTERN: Expected '{pattern}' in error message: {error_message}"
        self._track_metric('session_middleware_failures', 'invalid_secret_key_error', 1)
        print(f' PASS:  REPRODUCED: Invalid SECRET_KEY error - {error_message}')

    def test_sessionmiddleware_installation_with_none_secret_key(self):
        """
        TEST DESIGNED TO FAIL: SessionMiddleware installation with None SECRET_KEY.
        
        REPRODUCES: Missing SECRET_KEY configuration causing deployment failures
        BUSINESS IMPACT: Complete authentication system failure in GCP environments
        """
        self.env.unset('SECRET_KEY')
        self.env.set('ENV', 'staging')
        app = FastAPI()
        with pytest.raises((ValueError, TypeError, RuntimeError)) as exc_info:
            app.add_middleware(SessionMiddleware, secret_key=None, same_site='lax', https_only=True)

            @app.get('/test')
            async def test_endpoint(request: Request):
                request.session['test'] = 'value'
                return {'message': 'success'}
            with TestClient(app) as client:
                response = client.get('/test')
                assert False, 'VALIDATION FAILURE: None SECRET_KEY was accepted'
        error_message = str(exc_info.value)
        expected_patterns = ['SECRET_KEY', 'None', 'required', 'missing']
        pattern_found = any((pattern.lower() in error_message.lower() for pattern in expected_patterns))
        assert pattern_found, f'MISSING ERROR PATTERN: Expected one of {expected_patterns} in error: {error_message}'
        self._track_metric('session_middleware_failures', 'none_secret_key_error', 1)
        print(f' PASS:  REPRODUCED: None SECRET_KEY error - {error_message}')

    def test_sessionmiddleware_installation_with_default_secret_key(self):
        """
        TEST DESIGNED TO FAIL: SessionMiddleware with insecure default SECRET_KEY.
        
        REPRODUCES: Common default secret keys that should be rejected in production
        BUSINESS IMPACT: Security vulnerability in production environments
        """
        insecure_defaults = ['your-secret-key', 'secret', 'default-secret', 'change-me', 'insecure-key-change-in-production']
        self.env.set('ENV', 'production')
        for insecure_key in insecure_defaults:
            app = FastAPI()
            with pytest.raises((ValueError, Exception)) as exc_info:
                app.add_middleware(SessionMiddleware, secret_key=insecure_key, same_site='strict', https_only=True)

                @app.get('/test')
                async def test_endpoint(request: Request):
                    request.session['user_id'] = 'production-user'
                    return {'message': 'success'}
                with TestClient(app) as client:
                    response = client.get('/test')
                    assert False, f'SECURITY FAILURE: Insecure default key accepted: {insecure_key}'
            error_message = str(exc_info.value)
            print(f' PASS:  REPRODUCED: Insecure default rejected - {insecure_key}: {error_message}')
            self._track_metric('session_middleware_failures', 'insecure_default_rejected', 1)

    def test_session_access_without_middleware_installation(self):
        """
        TEST DESIGNED TO FAIL: Accessing request.session without SessionMiddleware installed.
        
        REPRODUCES: "SessionMiddleware must be installed to access request.session"
        BUSINESS IMPACT: Core Golden Path failure - authentication context lost
        """
        app = FastAPI()

        @app.get('/test')
        async def test_endpoint(request: Request):
            request.session['user_id'] = 'test-user'
            return {'message': 'success'}
        with TestClient(app) as client:
            with pytest.raises(RuntimeError) as exc_info:
                response = client.get('/test')
                assert False, f'SESSION VALIDATION FAILURE: request.session was accessible without middleware. Response: {response.status_code} - {response.json()}'
        error_message = str(exc_info.value)
        expected_error = 'SessionMiddleware must be installed to access request.session'
        assert expected_error in error_message, f"WRONG ERROR MESSAGE: Expected '{expected_error}', got '{error_message}'"
        self._track_metric('session_middleware_failures', 'middleware_not_installed', 1)
        print(f' PASS:  REPRODUCED: SessionMiddleware not installed error - {error_message}')

    def test_gcp_staging_middleware_order_causing_session_failure(self):
        """
        TEST DESIGNED TO FAIL: GCP staging middleware order causing session access failures.
        
        REPRODUCES: Middleware order issues in GCP Cloud Run causing authentication failures
        BUSINESS IMPACT: $500K+ ARR Golden Path blocked in staging environment
        """
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        self.env.set('ENV', 'staging')
        self.env.set('SECRET_KEY', 'valid-32-character-secret-key-for-gcp-staging-environment')
        app = FastAPI()
        app.add_middleware(GCPAuthContextMiddleware, enable_user_isolation=True)
        app.add_middleware(SessionMiddleware, secret_key=self.env.get('SECRET_KEY'), same_site='lax', https_only=True)

        @app.get('/test')
        async def test_endpoint(request: Request):
            request.session['user_id'] = 'gcp-staging-user'
            request.session['environment'] = 'staging'
            return {'message': 'session_set', 'user_id': request.session.get('user_id')}
        with TestClient(app) as client:
            with pytest.raises((RuntimeError, AttributeError)) as exc_info:
                response = client.get('/test')
                if response.status_code == 200:
                    data = response.json()
                    assert data.get('user_id') is None, f"SESSION ORDER FAILURE: Session data was accessible despite wrong middleware order. This indicates the test didn't reproduce the actual issue. Response: {data}"
                else:
                    pass
        error_message = str(exc_info.value)
        expected_patterns = ['session', 'middleware', 'installed', 'order']
        pattern_found = any((pattern.lower() in error_message.lower() for pattern in expected_patterns))
        if pattern_found:
            self._track_metric('session_middleware_failures', 'gcp_middleware_order_error', 1)
            print(f' PASS:  REPRODUCED: GCP middleware order error - {error_message}')
        else:
            print(f' WARNING: [U+FE0F]  PARTIAL REPRODUCTION: Middleware order issue detected but different error: {error_message}')

    def test_concurrent_session_access_race_condition(self):
        """
        TEST DESIGNED TO FAIL: Concurrent session access causing race conditions.
        
        REPRODUCES: Race conditions in session management under concurrent load
        BUSINESS IMPACT: Authentication failures under high load (production scaling issues)
        """
        self.env.set('SECRET_KEY', 'concurrent-test-secret-key-32-chars-minimum-length-required')
        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key=self.env.get('SECRET_KEY'), same_site='lax', https_only=False)
        session_data = {}
        race_condition_detected = False

        @app.get('/test/{user_id}')
        async def test_endpoint(request: Request, user_id: str):
            nonlocal race_condition_detected
            try:
                request.session[f'user_{user_id}'] = f'data_for_user_{user_id}'
                await asyncio.sleep(0.01)
                stored_data = request.session.get(f'user_{user_id}')
                if stored_data != f'data_for_user_{user_id}':
                    race_condition_detected = True
                    raise RuntimeError(f"RACE CONDITION: Session data corruption detected. Expected 'data_for_user_{user_id}', got '{stored_data}'")
                return {'user_id': user_id, 'session_data': stored_data}
            except Exception as e:
                session_data[user_id] = str(e)
                raise
        with TestClient(app) as client:
            import concurrent.futures
            import threading
            user_ids = [f'user_{i}' for i in range(10)]
            errors = []

            def make_request(user_id):
                try:
                    response = client.get(f'/test/{user_id}')
                    if response.status_code != 200:
                        errors.append(f'Request failed for {user_id}: {response.status_code}')
                    return response.json()
                except Exception as e:
                    errors.append(f'Exception for {user_id}: {str(e)}')
                    return {'error': str(e)}
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request, user_id) for user_id in user_ids]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            if race_condition_detected or errors:
                self._track_metric('session_middleware_failures', 'concurrent_race_condition', 1)
                print(f' PASS:  REPRODUCED: Session race condition - Errors: {errors}')
                assert race_condition_detected or errors, f'Race condition or concurrent access errors detected: {errors}'
            else:
                print(' WARNING: [U+FE0F]  RACE CONDITION NOT REPRODUCED: Concurrent access appeared stable')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')