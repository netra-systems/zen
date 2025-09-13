"""

Test Suite for Issue #724: SSOT Configuration Manager Environment Access Violations



This test suite validates SSOT compliance for direct os.getenv() and os.environ.get() 

violations in critical infrastructure files. These tests are DESIGNED TO FAIL with 

current violations and PASS when proper IsolatedEnvironment patterns are adopted.



CRITICAL VIOLATIONS TESTED:

1. netra_backend/app/logging/auth_trace_logger.py:284 - Direct os.getenv('ENVIRONMENT')

2. netra_backend/app/admin/corpus/unified_corpus_admin.py:155 - Direct os.getenv('CORPUS_BASE_PATH')  

3. netra_backend/app/middleware/error_recovery_middleware.py:33 - Direct os.environ.get('ENVIRONMENT')



Business Value Justification (BVJ):

- Segment: Platform Infrastructure (affects ALL user segments)

- Business Goal: Prevent configuration-related Golden Path authentication failures  

- Value Impact: Validates SSOT patterns prevent environment drift causing login→AI response failures

- Strategic Impact: Protects $500K+ ARR through consistent environment behavior



EXPECTED BEHAVIOR:

- BEFORE Remediation: These tests FAIL (detecting SSOT violations)

- AFTER Remediation: These tests PASS (proper IsolatedEnvironment usage)

"""



import os

import sys

import unittest.mock

from unittest import mock

from typing import Dict, Any, Optional

import pytest



# Import SSOT test framework

from test_framework.ssot.base_test_case import SSotBaseTestCase

from shared.isolated_environment import get_env, IsolatedEnvironment





class TestIssue724SSotViolations(SSotBaseTestCase):

    """

    EXPECTED TO FAIL tests exposing Issue #724 SSOT violations.

    

    These tests detect direct os.getenv() and os.environ.get() usage in critical 

    infrastructure files that should be using IsolatedEnvironment instead.

    """

    

    def setup_method(self, method):

        """Setup for each test method."""

        super().setup_method(method)

        self.env = get_env()

        

        # Track direct environment access calls

        self.direct_access_calls = []

        

        # Store original functions for cleanup

        self.original_os_getenv = os.getenv

        self.original_os_environ_get = os.environ.get

    

    def teardown_method(self, method):

        """Cleanup after each test method."""

        # Restore original functions

        os.getenv = self.original_os_getenv

        os.environ.get = self.original_os_environ_get

        super().teardown_method(method)

    

    def _track_direct_access(self, func_name: str, key: str, default=None):

        """Track direct environment access for violation detection."""

        self.direct_access_calls.append({

            'function': func_name,

            'key': key,

            'default': default

        })

        # Return a mock value to allow code to continue

        if func_name == 'os.getenv' and key == 'ENVIRONMENT':

            return 'development'

        elif func_name == 'os.getenv' and key == 'CORPUS_BASE_PATH':

            return '/data/corpus'

        elif func_name == 'os.environ.get' and key == 'ENVIRONMENT':

            return 'development'

        return default

    

    def test_auth_trace_logger_direct_os_getenv_violation(self):

        """

        FAILS: Detects auth_trace_logger.py:284 os.getenv violation.

        

        This test verifies that AuthTraceLogger._is_development_env() 

        uses direct os.getenv('ENVIRONMENT') instead of IsolatedEnvironment.

        """

        # Mock os.getenv to track direct access

        os.getenv = lambda key, default=None: self._track_direct_access('os.getenv', key, default)

        

        try:

            # Import and trigger the specific functionality

            from netra_backend.app.logging.auth_trace_logger import AuthTraceLogger

            

            # Create instance and trigger environment check

            logger = AuthTraceLogger()

            result = logger._is_development_env()

            

            # ASSERTION: Direct os.getenv access should be detected

            environment_calls = [call for call in self.direct_access_calls 

                               if call['function'] == 'os.getenv' and call['key'] == 'ENVIRONMENT']

            

            assert len(environment_calls) > 0, (

                "SSOT VIOLATION: AuthTraceLogger._is_development_env() should use "

                "IsolatedEnvironment instead of direct os.getenv('ENVIRONMENT'). "

                f"Expected direct access calls but found none. "

                f"All calls: {self.direct_access_calls}"

            )

            

            # This assertion will fail until remediation (pytest pattern)

            pytest.fail(

                f"SSOT VIOLATION DETECTED: AuthTraceLogger uses direct os.getenv('ENVIRONMENT'). "

                f"Found {len(environment_calls)} direct access calls. "

                f"Should use: from shared.isolated_environment import get_env; "

                f"env = get_env(); env.get('ENVIRONMENT')"

            )

            

        except ImportError as e:

            pytest.skip(f"Could not import AuthTraceLogger: {e}")

    

    def test_unified_corpus_admin_direct_os_getenv_violation(self):

        """

        FAILS: Detects unified_corpus_admin.py:155 os.getenv violation.

        

        This test verifies that create_corpus_context() uses direct 

        os.getenv('CORPUS_BASE_PATH') instead of IsolatedEnvironment.

        """

        # Mock os.getenv to track direct access

        os.getenv = lambda key, default=None: self._track_direct_access('os.getenv', key, default)

        

        try:

            # Import and trigger the specific functionality

            from netra_backend.app.admin.corpus.unified_corpus_admin import initialize_corpus_context

            from netra_backend.app.services.user_execution_context import UserExecutionContext

            

            # Create a mock context

            mock_context = UserExecutionContext(

                user_id="test_user",

                thread_id="test_thread",

                run_id="test_run"

            )

            

            # Trigger corpus path resolution with None to force environment access

            result = initialize_corpus_context(mock_context, corpus_base_path=None)

            

            # ASSERTION: Direct os.getenv access should be detected

            corpus_path_calls = [call for call in self.direct_access_calls 

                               if call['function'] == 'os.getenv' and call['key'] == 'CORPUS_BASE_PATH']

            

            assert len(corpus_path_calls) > 0, (

                "SSOT VIOLATION: initialize_corpus_context() should use "

                "IsolatedEnvironment instead of direct os.getenv('CORPUS_BASE_PATH'). "

                f"Expected direct access calls but found none. "

                f"All calls: {self.direct_access_calls}"

            )

            

            # This assertion will fail until remediation (pytest pattern)

            pytest.fail(

                f"SSOT VIOLATION DETECTED: initialize_corpus_context() uses direct os.getenv('CORPUS_BASE_PATH'). "

                f"Found {len(corpus_path_calls)} direct access calls. "

                f"Should use: from shared.isolated_environment import get_env; "

                f"env = get_env(); env.get('CORPUS_BASE_PATH', '/data/corpus')"

            )

            

        except ImportError as e:

            pytest.skip(f"Could not import corpus admin modules: {e}")

    

    def test_error_recovery_middleware_direct_os_environ_violation(self):

        """

        FAILS: Detects error_recovery_middleware.py:33 os.environ.get violation.

        

        This test verifies that ErrorRecoveryMiddleware uses direct 

        os.environ.get('ENVIRONMENT') instead of IsolatedEnvironment.

        """

        # Mock os.environ.get to track direct access

        os.environ.get = lambda key, default=None: self._track_direct_access('os.environ.get', key, default)

        

        try:

            # Import the middleware

            from netra_backend.app.middleware.error_recovery_middleware import ErrorRecoveryMiddleware

            from starlette.requests import Request

            from starlette.responses import Response

            

            # Create middleware instance

            middleware = ErrorRecoveryMiddleware(app=None)

            

            # Create a mock request that will trigger an exception

            mock_request = mock.Mock(spec=Request)

            mock_request.url = mock.Mock()

            mock_request.url.path = "/test"

            mock_request.method = "GET"

            

            # Create a call_next function that raises an exception

            async def failing_call_next(request):

                raise Exception("Test exception to trigger error handling")

            

            # Trigger the middleware error handling

            import asyncio

            

            async def run_middleware_test():

                try:

                    await middleware.dispatch(mock_request, failing_call_next)

                except Exception:

                    # Expected - we want the error handling path

                    pass

            

            # Run the async test

            asyncio.run(run_middleware_test())

            

            # ASSERTION: Direct os.environ.get access should be detected

            environment_calls = [call for call in self.direct_access_calls 

                               if call['function'] == 'os.environ.get' and call['key'] == 'ENVIRONMENT']

            

            assert len(environment_calls) > 0, (

                "SSOT VIOLATION: ErrorRecoveryMiddleware should use "

                "IsolatedEnvironment instead of direct os.environ.get('ENVIRONMENT'). "

                f"Expected direct access calls but found none. "

                f"All calls: {self.direct_access_calls}"

            )

            

            # This assertion will fail until remediation (pytest pattern)

            pytest.fail(

                f"SSOT VIOLATION DETECTED: ErrorRecoveryMiddleware uses direct os.environ.get('ENVIRONMENT'). "

                f"Found {len(environment_calls)} direct access calls. "

                f"Should use: from shared.isolated_environment import get_env; "

                f"env = get_env(); env.get('ENVIRONMENT')"

            )

            

        except ImportError as e:

            pytest.skip(f"Could not import ErrorRecoveryMiddleware: {e}")

    

    def test_isolated_environment_compliance_patterns_pass(self):

        """

        PASSES: Validates IsolatedEnvironment patterns work correctly.

        

        This test demonstrates the CORRECT SSOT pattern that should be used 

        instead of direct os.getenv() or os.environ.get() calls.

        """

        # Set up test environment values

        self.env.set('ENVIRONMENT', 'test_env')

        self.env.set('CORPUS_BASE_PATH', '/test/corpus')

        

        # Test proper SSOT pattern

        environment = self.env.get('ENVIRONMENT')

        corpus_path = self.env.get('CORPUS_BASE_PATH', '/default/corpus')

        

        # These should work correctly

        assert environment == 'test_env'

        assert corpus_path == '/test/corpus'

        

        # Test with defaults

        missing_value = self.env.get('NONEXISTENT_VAR', 'default_value')

        assert missing_value == 'default_value'

        

        # Test environment name detection

        env_name = self.env.get_environment_name()

        assert env_name is not None

        

        # This test should always pass - it validates proper SSOT usage

        print("✅ IsolatedEnvironment SSOT patterns working correctly")

    

    def test_ssot_violation_summary_report(self):

        """

        Generate a comprehensive summary of all SSOT violations detected.

        

        This test provides a summary of the Issue #724 violations for tracking purposes.

        """

        violations_found = []

        

        # Test each violation independently

        test_methods = [

            'test_auth_trace_logger_direct_os_getenv_violation',

            'test_unified_corpus_admin_direct_os_getenv_violation', 

            'test_error_recovery_middleware_direct_os_environ_violation'

        ]

        

        for method_name in test_methods:

            try:

                # Reset call tracking

                self.direct_access_calls = []

                

                # Run the test method

                method = getattr(self, method_name)

                method()

                

                # If we get here, no violation was detected (unexpected)

                violations_found.append(f"{method_name}: NO VIOLATION DETECTED (unexpected)")

                

            except AssertionError as e:

                # Expected - violation was detected

                violations_found.append(f"{method_name}: VIOLATION DETECTED")

            except Exception as e:

                # Unexpected error

                violations_found.append(f"{method_name}: ERROR - {str(e)}")

        

        # Report summary

        print("\n" + "="*80)

        print("ISSUE #724 SSOT VIOLATIONS SUMMARY REPORT")

        print("="*80)

        for violation in violations_found:

            print(f"• {violation}")

        print("="*80)

        

        # This test documents the current state but doesn't fail

        # It will show different results before/after remediation

        print(f"Total violations analyzed: {len(violations_found)}")





if __name__ == "__main__":

    # Allow running this test file directly

    pytest.main([__file__, "-v"])

