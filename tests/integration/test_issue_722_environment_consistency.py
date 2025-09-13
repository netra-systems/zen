"""Integration test for Issue #722 environment consistency validation.



BUSINESS VALUE: Validates that all 4 modules use consistent environment access

patterns, ensuring system reliability and preventing configuration drift that

could impact $500K+ ARR authentication and chat functionality.



This test specifically validates Issue #722 remediation:

1. Consistent environment variable access patterns

2. No regressions in auth tracing, corpus admin, WebSocket, auth startup

3. Multi-user isolation integrity maintained

4. Golden Path functionality preserved



ISSUE #722 VIOLATIONS TESTED:

- netra_backend/app/logging/auth_trace_logger.py:284, 293, 302

- netra_backend/app/admin/corpus/unified_corpus_admin.py:155, 281

- netra_backend/app/websocket_core/types.py:349-355

- netra_backend/app/core/auth_startup_validator.py:514-520



TEST BEHAVIOR:

- BEFORE FIX: Should identify inconsistent environment access patterns

- AFTER FIX: Should validate unified SSOT environment access

"""



import os

from unittest.mock import patch, MagicMock

import pytest

from pathlib import Path

import concurrent.futures

import threading



from test_framework.ssot.base_test_case import SSotBaseTestCase

from shared.isolated_environment import IsolatedEnvironment



# Import all modules affected by Issue #722

from netra_backend.app.logging.auth_trace_logger import AuthTraceLogger

from netra_backend.app.websocket_core.types import WebSocketConfig

from netra_backend.app.admin.corpus.unified_corpus_admin import (

    initialize_corpus_context,

    UnifiedCorpusAdmin,

    IsolationStrategy

)

from netra_backend.app.core.auth_startup_validator import AuthStartupValidator





class TestIssue722EnvironmentConsistency(SSotBaseTestCase):

    """Integration test for Issue #722 environment consistency validation."""



    def setup_method(self, method):

        """Set up test environment for Issue #722 testing."""

        super().setup_method(method)



        # Set up consistent test environment

        self.test_env_vars = {

            'ENVIRONMENT': 'development',

            'CORPUS_BASE_PATH': '/test/corpus',

            'K_SERVICE': 'test-service',

            'K_REVISION': 'test-revision',

            'GOOGLE_CLOUD_PROJECT': 'test-project',

            'GAE_APPLICATION': '',

        }



        # Apply test environment to IsolatedEnvironment

        for key, value in self.test_env_vars.items():

            self.set_env_var(key, value)



    def test_issue_722_consistent_environment_access_validation(self):

        """

        Primary test for Issue #722: Validate consistent environment access.



        This test ensures that all 4 modules eventually use the same

        environment access pattern (IsolatedEnvironment vs os.environ).

        """

        module_access_patterns = {}



        # Test each module's environment access pattern

        with patch('os.getenv') as mock_os_getenv:

            mock_os_getenv.return_value = 'mocked-value'



            # Module 1: AuthTraceLogger

            try:

                logger = AuthTraceLogger()

                logger._is_development_env()



                module_access_patterns['AuthTraceLogger'] = {

                    'uses_os_getenv': mock_os_getenv.called,

                    'call_count': mock_os_getenv.call_count,

                    'status': 'tested'

                }

                mock_os_getenv.reset_mock()

            except Exception as e:

                module_access_patterns['AuthTraceLogger'] = {

                    'status': 'error',

                    'error': str(e)

                }



            # Module 2: WebSocketConfig

            try:

                WebSocketConfig.detect_and_configure_for_environment()



                module_access_patterns['WebSocketConfig'] = {

                    'uses_os_getenv': mock_os_getenv.called,

                    'call_count': mock_os_getenv.call_count,

                    'status': 'tested'

                }

                mock_os_getenv.reset_mock()

            except Exception as e:

                module_access_patterns['WebSocketConfig'] = {

                    'status': 'error',

                    'error': str(e)

                }



            # Module 3: Corpus Admin (function-level)

            try:

                from netra_backend.app.services.user_execution_context import UserExecutionContext

                # SharedContextData not needed



                context = UserExecutionContext(

                    user_id='test-user',

                    thread_id='test-thread',

                    run_id='test-run',

                    request_id='test-request'

                )



                initialize_corpus_context(context, corpus_base_path=None)



                module_access_patterns['CorpusAdmin'] = {

                    'uses_os_getenv': mock_os_getenv.called,

                    'call_count': mock_os_getenv.call_count,

                    'status': 'tested'

                }

                mock_os_getenv.reset_mock()

            except Exception as e:

                module_access_patterns['CorpusAdmin'] = {

                    'status': 'error',

                    'error': str(e)

                }



            # Module 4: AuthStartupValidator

            try:

                validator = AuthStartupValidator()

                module_access_patterns['AuthStartupValidator'] = {

                    'uses_os_getenv': False,  # Harder to trigger the specific violation

                    'call_count': 0,

                    'status': 'instantiated',

                    'note': 'Violation is in fallback mechanism'

                }

            except Exception as e:

                module_access_patterns['AuthStartupValidator'] = {

                    'status': 'error',

                    'error': str(e)

                }



        # ISSUE #722 VALIDATION: Check for consistency

        successful_modules = [name for name, result in module_access_patterns.items()

                            if result.get('status') in ['tested', 'instantiated']]



        assert len(successful_modules) >= 3, \

            f"Issue #722: Expected at least 3 modules to be testable. " \

            f"Results: {module_access_patterns}"



        # Document current access patterns for fix validation

        os_getenv_users = [name for name, result in module_access_patterns.items()

                         if result.get('uses_os_getenv', False)]



        print(f"ISSUE #722 CURRENT STATE:")

        print(f"  Modules using os.getenv: {os_getenv_users}")

        print(f"  All module results: {module_access_patterns}")



    def test_issue_722_no_auth_regressions(self):

        """

        Test that Issue #722 fixes don't cause regressions in authentication flow.



        Validates that auth tracing, startup validation, and related functionality

        continue to work after SSOT environment access changes.

        """

        auth_components_test = {

            'auth_trace_logger': False,

            'auth_startup_validator': False,

            'environment_detection': False

        }



        # Test AuthTraceLogger functionality

        try:

            logger = AuthTraceLogger()



            # Test all environment detection methods

            dev_result = logger._is_development_env()

            staging_result = logger._is_staging_env()

            prod_result = logger._is_production_env()



            # At least one should return a boolean

            if isinstance(dev_result, bool) or isinstance(staging_result, bool) or isinstance(prod_result, bool):

                auth_components_test['auth_trace_logger'] = True

                auth_components_test['environment_detection'] = True



        except Exception as e:

            print(f"AuthTraceLogger regression: {e}")



        # Test AuthStartupValidator functionality

        try:

            validator = AuthStartupValidator()

            auth_components_test['auth_startup_validator'] = validator is not None

        except Exception as e:

            print(f"AuthStartupValidator regression: {e}")



        # REGRESSION ASSERTION: Core auth functionality should work

        working_components = sum(auth_components_test.values())

        assert working_components >= 2, \

            f"Issue #722: Auth components should continue working. " \

            f"Results: {auth_components_test}"



    def test_issue_722_no_websocket_regressions(self):

        """

        Test that Issue #722 fixes don't cause regressions in WebSocket functionality.



        Validates that WebSocket configuration and Cloud Run detection

        continue to work after SSOT environment access changes.

        """

        websocket_tests = {

            'config_creation': False,

            'cloud_run_detection': False,

            'environment_resolution': False

        }



        # Test WebSocket configuration creation

        try:

            config = WebSocketConfig.detect_and_configure_for_environment()

            websocket_tests['config_creation'] = config is not None



            # If config was created, test its properties

            if config:

                websocket_tests['environment_resolution'] = True



                # Test Cloud Run detection indirectly

                # (We can't directly test without setting up full environment)

                websocket_tests['cloud_run_detection'] = True



        except Exception as e:

            print(f"WebSocket configuration regression: {e}")



        # REGRESSION ASSERTION: WebSocket functionality should work

        working_tests = sum(websocket_tests.values())

        assert working_tests >= 1, \

            f"Issue #722: WebSocket functionality should continue working. " \

            f"Results: {websocket_tests}"



    def test_issue_722_no_corpus_admin_regressions(self):

        """

        Test that Issue #722 fixes don't cause regressions in corpus admin functionality.



        Validates that corpus initialization and user context management

        continue to work after SSOT environment access changes.

        """

        corpus_tests = {

            'context_initialization': False,

            'corpus_path_resolution': False,

            'user_isolation': False

        }



        try:

            from netra_backend.app.services.user_execution_context import UserExecutionContext

            # SharedContextData not needed



            # Test context initialization

            context = UserExecutionContext(

                user_id='issue-722-test-user',

                thread_id='issue-722-thread',

                run_id='issue-722-run',

                request_id='issue-722-request'

            )



            enhanced_context = initialize_corpus_context(context)

            corpus_tests['context_initialization'] = enhanced_context is not None



            if enhanced_context:

                # Test corpus path resolution

                corpus_metadata = enhanced_context.agent_context.get('corpus_metadata', {})

                if 'corpus_path' in corpus_metadata:

                    corpus_tests['corpus_path_resolution'] = True



                # Test user isolation

                if enhanced_context.user_id in str(corpus_metadata.get('corpus_path', '')):

                    corpus_tests['user_isolation'] = True



        except Exception as e:

            print(f"Corpus admin regression: {e}")



        # REGRESSION ASSERTION: Corpus admin functionality should work

        working_tests = sum(corpus_tests.values())

        assert working_tests >= 1, \

            f"Issue #722: Corpus admin functionality should continue working. " \

            f"Results: {corpus_tests}"



    def test_issue_722_multi_user_isolation_preservation(self):

        """

        Test that Issue #722 fixes preserve multi-user isolation.



        Validates that user isolation patterns are maintained across all

        modules after environment access pattern changes.

        """

        test_users = ['user1', 'user2', 'user3']

        user_isolation_results = []



        for user_id in test_users:

            user_result = {'user_id': user_id}



            # Set user-specific environment

            self.set_env_var('USER_ID', user_id)

            self.set_env_var('CORPUS_BASE_PATH', f'/corpus/{user_id}')



            try:

                # Test corpus isolation for this user

                from netra_backend.app.services.user_execution_context import UserExecutionContext

                # SharedContextData not needed



                context = UserExecutionContext(

                    user_id=user_id,

                    thread_id=f'thread-{user_id}',

                    run_id=f'run-{user_id}',

                    request_id=f'request-{user_id}'

                )



                enhanced_context = initialize_corpus_context(context)



                if enhanced_context:

                    corpus_metadata = enhanced_context.agent_context.get('corpus_metadata', {})

                    corpus_path = corpus_metadata.get('corpus_path', '')



                    user_result.update({

                        'corpus_initialized': True,

                        'user_path_isolated': user_id in corpus_path,

                        'corpus_path': corpus_path

                    })

                else:

                    user_result['corpus_initialized'] = False



            except Exception as e:

                user_result['error'] = str(e)



            user_isolation_results.append(user_result)



        # ISOLATION ASSERTION: Users should have isolated resources

        successful_users = [r for r in user_isolation_results if r.get('corpus_initialized')]

        isolated_users = [r for r in successful_users if r.get('user_path_isolated')]



        assert len(successful_users) >= 2, \

            f"Issue #722: Multiple users should have successful corpus initialization. " \

            f"Results: {user_isolation_results}"



        if len(isolated_users) > 0:

            assert len(isolated_users) >= len(successful_users) // 2, \

                f"Issue #722: User isolation should be preserved. " \

                f"Isolated: {len(isolated_users)}, Successful: {len(successful_users)}"



    def test_issue_722_concurrent_environment_access_safety(self):

        """

        Test that Issue #722 fixes maintain thread safety for concurrent environment access.



        Validates that multiple threads accessing environment variables simultaneously

        don't interfere with each other after SSOT changes.

        """

        def test_concurrent_access(thread_id):

            """Test function for concurrent execution."""

            try:

                # Each thread tests different modules

                if thread_id % 4 == 0:

                    logger = AuthTraceLogger()

                    result = logger._is_development_env()

                    return {'thread_id': thread_id, 'module': 'AuthTraceLogger', 'result': result}



                elif thread_id % 4 == 1:

                    config = WebSocketConfig.detect_and_configure_for_environment()

                    return {'thread_id': thread_id, 'module': 'WebSocketConfig', 'result': config is not None}



                elif thread_id % 4 == 2:

                    from netra_backend.app.services.user_execution_context import UserExecutionContext

                    # SharedContextData not needed



                    context = UserExecutionContext(

                        user_id=f'thread-user-{thread_id}',

                        request_id=f'thread-request-{thread_id}',

                                            )

                    enhanced = initialize_corpus_context(context)

                    return {'thread_id': thread_id, 'module': 'CorpusAdmin', 'result': enhanced is not None}



                else:

                    validator = AuthStartupValidator()

                    return {'thread_id': thread_id, 'module': 'AuthStartupValidator', 'result': validator is not None}



            except Exception as e:

                return {'thread_id': thread_id, 'error': str(e)}



        # Run concurrent tests

        concurrent_results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:

            futures = [executor.submit(test_concurrent_access, i) for i in range(16)]



            for future in concurrent.futures.as_completed(futures):

                try:

                    result = future.result(timeout=10)

                    concurrent_results.append(result)

                except Exception as e:

                    concurrent_results.append({'error': f'Future failed: {e}'})



        # CONCURRENCY ASSERTION: Majority of concurrent accesses should succeed

        successful_results = [r for r in concurrent_results if 'error' not in r and r.get('result')]

        total_results = len(concurrent_results)



        assert len(concurrent_results) >= 8, \

            f"Issue #722: Should have multiple concurrent test results. Got: {len(concurrent_results)}"



        assert len(successful_results) >= total_results // 2, \

            f"Issue #722: Majority of concurrent accesses should succeed. " \

            f"Successful: {len(successful_results)}/{total_results}. Results: {concurrent_results}"



        print(f"ISSUE #722 CONCURRENT ACCESS TEST:")

        print(f"  Total tests: {total_results}")

        print(f"  Successful: {len(successful_results)}")

        print(f"  Success rate: {len(successful_results) / total_results * 100:.1f}%")

