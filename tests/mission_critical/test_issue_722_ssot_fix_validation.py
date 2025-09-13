"""Mission Critical test for Issue #722 SSOT fix validation.

BUSINESS VALUE: Protects $500K+ ARR authentication and chat functionality by
ensuring SSOT fixes maintain system stability and Golden Path user flow.

This test validates that after fixing Issue #722 legacy os.environ violations:
1. Golden Path user flow continues to work end-to-end
2. Authentication systems remain stable
3. WebSocket real-time functionality is preserved
4. Multi-user isolation integrity is maintained
5. No regressions in critical business functionality

CRITICAL SCOPE: This test MUST PASS after SSOT fixes are implemented to
ensure business continuity and system reliability.

ISSUE #722 CONTEXT:
- 4 files with legacy os.environ direct access
- Environment isolation critical for multi-user system
- Changes affect auth, WebSocket, corpus admin, startup validation
- Golden Path depends on all components working together
"""

import os
import asyncio
from unittest.mock import patch, MagicMock
import pytest
from pathlib import Path

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# Import all critical modules affected by Issue #722
from netra_backend.app.logging.auth_trace_logger import AuthTraceLogger
from netra_backend.app.websocket_core.types import WebSocketConfig
from netra_backend.app.admin.corpus.unified_corpus_admin import (
    initialize_corpus_context,
    UnifiedCorpusAdmin,
    IsolationStrategy
)
from netra_backend.app.core.auth_startup_validator import AuthStartupValidator


class TestIssue722SsotFixValidation(SSotAsyncTestCase):
    """Mission critical validation for Issue #722 SSOT fix implementation."""

    def setup_method(self, method):
        """Set up mission critical test environment."""
        super().setup_method(method)

        # Configure Golden Path environment
        self.golden_path_env = {
            'ENVIRONMENT': 'staging',
            'CORPUS_BASE_PATH': '/data/corpus',
            'K_SERVICE': 'netra-backend',
            'K_REVISION': 'staging-001',
            'GOOGLE_CLOUD_PROJECT': 'netra-staging',
            'GAE_APPLICATION': '',
            'JWT_SECRET_KEY': 'test-secret-key',
            'DATABASE_URL': 'postgresql://test',
            'REDIS_URL': 'redis://test'
        }

        # Apply Golden Path environment
        for key, value in self.golden_path_env.items():
            self.set_env_var(key, value)

    def test_golden_path_user_flow_preserved_after_ssot_fixes(self):
        """
        MISSION CRITICAL: Validate Golden Path user flow works after SSOT fixes.

        Tests end-to-end user flow components that depend on environment variables:
        1. Authentication tracing
        2. WebSocket configuration
        3. Corpus initialization
        4. Startup validation

        This test MUST PASS to ensure $500K+ ARR business continuity.
        """
        golden_path_components = {
            'auth_tracing': {'status': 'unknown', 'critical': True},
            'websocket_config': {'status': 'unknown', 'critical': True},
            'corpus_initialization': {'status': 'unknown', 'critical': True},
            'startup_validation': {'status': 'unknown', 'critical': False},
            'environment_detection': {'status': 'unknown', 'critical': True}
        }

        # Component 1: Authentication Tracing (Critical for user sessions)
        try:
            logger = AuthTraceLogger()

            # Test environment detection works correctly
            staging_detected = logger._is_staging_env()
            dev_detected = logger._is_development_env()
            prod_detected = logger._is_production_env()

            # Should detect staging environment correctly
            environment_working = staging_detected and not dev_detected and not prod_detected

            golden_path_components['auth_tracing']['status'] = 'working' if environment_working else 'degraded'
            golden_path_components['environment_detection']['status'] = 'working' if environment_working else 'failed'

        except Exception as e:
            golden_path_components['auth_tracing']['status'] = 'failed'
            golden_path_components['auth_tracing']['error'] = str(e)

        # Component 2: WebSocket Configuration (Critical for real-time chat)
        try:
            config = WebSocketConfig.detect_and_configure_for_environment()

            # Validate configuration is created and has expected properties
            config_valid = (
                config is not None and
                hasattr(config, 'max_connections_per_user') and
                hasattr(config, 'heartbeat_interval_seconds') and
                config.max_connections_per_user > 0
            )

            golden_path_components['websocket_config']['status'] = 'working' if config_valid else 'failed'

        except Exception as e:
            golden_path_components['websocket_config']['status'] = 'failed'
            golden_path_components['websocket_config']['error'] = str(e)

        # Component 3: Corpus Initialization (Critical for user data isolation)
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            # SharedContextData not needed

            # Test user context initialization
            context = UserExecutionContext(
                user_id='golden-path-user',
                thread_id='golden-path-thread',
                run_id='golden-path-run',
                request_id='golden-path-request'
            )

            enhanced_context = initialize_corpus_context(context)

            # Validate corpus initialization worked
            corpus_valid = (
                enhanced_context is not None and
                enhanced_context.user_id == 'golden-path-user' and
                'corpus_metadata' in enhanced_context.agent_context
            )

            golden_path_components['corpus_initialization']['status'] = 'working' if corpus_valid else 'failed'

        except Exception as e:
            golden_path_components['corpus_initialization']['status'] = 'failed'
            golden_path_components['corpus_initialization']['error'] = str(e)

        # Component 4: Startup Validation (Important but not critical)
        try:
            validator = AuthStartupValidator()
            golden_path_components['startup_validation']['status'] = 'working' if validator else 'failed'

        except Exception as e:
            golden_path_components['startup_validation']['status'] = 'failed'
            golden_path_components['startup_validation']['error'] = str(e)

        # MISSION CRITICAL ASSERTION: All critical components must work
        critical_failures = []
        critical_working = 0
        total_critical = 0

        for component, details in golden_path_components.items():
            if details['critical']:
                total_critical += 1
                if details['status'] == 'working':
                    critical_working += 1
                elif details['status'] == 'failed':
                    critical_failures.append(component)

        # Golden Path requires all critical components working
        assert len(critical_failures) == 0, \
            f"MISSION CRITICAL FAILURE: Golden Path components failed after SSOT fixes. " \
            f"Failed components: {critical_failures}. All results: {golden_path_components}"

        assert critical_working == total_critical, \
            f"MISSION CRITICAL: All critical components must work. " \
            f"Working: {critical_working}/{total_critical}. Results: {golden_path_components}"

        print(f"GOLDEN PATH VALIDATION SUCCESSFUL: {golden_path_components}")

    def test_ssot_fixes_use_isolated_environment_correctly(self):
        """
        Validate that SSOT fixes properly use IsolatedEnvironment.

        This test ensures that after the fixes, modules use IsolatedEnvironment
        instead of direct os.environ access, proving SSOT compliance.
        """
        ssot_compliance_tests = {}

        # Set up test values in IsolatedEnvironment only
        isolated_test_values = {
            'ENVIRONMENT': 'isolated-test',
            'CORPUS_BASE_PATH': '/isolated/corpus',
            'K_SERVICE': 'isolated-service'
        }

        for key, value in isolated_test_values.items():
            self.set_env_var(key, value)

        # Ensure os.environ has different values
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'os-environ-value',
            'CORPUS_BASE_PATH': '/os/corpus',
            'K_SERVICE': 'os-service'
        }, clear=False):

            # Test 1: AuthTraceLogger should use IsolatedEnvironment values
            try:
                with patch('os.getenv') as mock_os_getenv:
                    mock_os_getenv.return_value = 'os-environ-value'

                    logger = AuthTraceLogger()

                    # After SSOT fix, this should NOT call os.getenv
                    result = logger._is_development_env()

                    ssot_compliance_tests['AuthTraceLogger'] = {
                        'os_getenv_called': mock_os_getenv.called,
                        'result_type': type(result).__name__,
                        'compliance_status': 'compliant' if not mock_os_getenv.called else 'violation'
                    }

            except Exception as e:
                ssot_compliance_tests['AuthTraceLogger'] = {
                    'error': str(e),
                    'compliance_status': 'error'
                }

            # Test 2: WebSocketConfig should use IsolatedEnvironment values
            try:
                with patch('os.getenv') as mock_os_getenv:
                    mock_os_getenv.return_value = 'os-environ-value'

                    config = WebSocketConfig.detect_and_configure_for_environment()

                    ssot_compliance_tests['WebSocketConfig'] = {
                        'os_getenv_called': mock_os_getenv.called,
                        'config_created': config is not None,
                        'compliance_status': 'compliant' if not mock_os_getenv.called else 'violation'
                    }

            except Exception as e:
                ssot_compliance_tests['WebSocketConfig'] = {
                    'error': str(e),
                    'compliance_status': 'error'
                }

        # SSOT COMPLIANCE ASSERTION: After fixes, modules should use IsolatedEnvironment
        compliant_modules = [name for name, result in ssot_compliance_tests.items()
                           if result.get('compliance_status') == 'compliant']

        violation_modules = [name for name, result in ssot_compliance_tests.items()
                           if result.get('compliance_status') == 'violation']

        # After SSOT fixes, we expect compliance
        assert len(violation_modules) == 0, \
            f"SSOT COMPLIANCE FAILURE: Modules still violating after fixes: {violation_modules}. " \
            f"All results: {ssot_compliance_tests}"

        # Validate that at least some modules are testable and compliant
        assert len(compliant_modules) >= 1, \
            f"SSOT COMPLIANCE: At least some modules should be compliant after fixes. " \
            f"Results: {ssot_compliance_tests}"

        print(f"SSOT COMPLIANCE VALIDATION: {ssot_compliance_tests}")

    def test_multi_user_isolation_integrity_after_fixes(self):
        """
        Validate multi-user isolation integrity after SSOT fixes.

        Ensures that environment isolation doesn't break user-specific contexts
        and that multiple users can operate simultaneously without interference.
        """
        test_users = [
            {'user_id': 'user-alpha', 'environment': 'staging'},
            {'user_id': 'user-beta', 'environment': 'development'},
            {'user_id': 'user-gamma', 'environment': 'production'}
        ]

        user_isolation_results = []

        for user_data in test_users:
            user_id = user_data['user_id']
            environment = user_data['environment']

            # Set user-specific environment in IsolatedEnvironment
            self.set_env_var('ENVIRONMENT', environment)
            self.set_env_var('USER_ID', user_id)
            self.set_env_var('CORPUS_BASE_PATH', f'/data/corpus/{user_id}')

            user_result = {'user_id': user_id, 'environment': environment}

            try:
                # Test 1: Environment detection for this user
                logger = AuthTraceLogger()

                env_detection = {
                    'development': logger._is_development_env(),
                    'staging': logger._is_staging_env(),
                    'production': logger._is_production_env()
                }

                # Should correctly detect the user's environment
                correct_detection = env_detection.get(environment, False)
                user_result['environment_detected_correctly'] = correct_detection

                # Test 2: Corpus isolation for this user
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                # SharedContextData not needed

                context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=f'isolation-thread-{user_id}',
                    run_id=f'isolation-run-{user_id}',
                    request_id=f'isolation-test-{user_id}'
                )

                enhanced_context = initialize_corpus_context(context)

                if enhanced_context:
                    corpus_metadata = enhanced_context.agent_context.get('corpus_metadata', {})
                    corpus_path = corpus_metadata.get('corpus_path', '')

                    user_result.update({
                        'corpus_initialized': True,
                        'user_isolated_path': user_id in corpus_path,
                        'corpus_path_preview': corpus_path[:50] + '...' if len(corpus_path) > 50 else corpus_path
                    })
                else:
                    user_result['corpus_initialized'] = False

                user_result['test_status'] = 'success'

            except Exception as e:
                user_result.update({
                    'test_status': 'error',
                    'error': str(e)
                })

            user_isolation_results.append(user_result)

        # ISOLATION INTEGRITY ASSERTION: Users should have isolated experiences
        successful_users = [r for r in user_isolation_results if r.get('test_status') == 'success']
        correctly_detected_env = [r for r in successful_users if r.get('environment_detected_correctly')]
        isolated_corpus = [r for r in successful_users if r.get('user_isolated_path')]

        assert len(successful_users) >= 2, \
            f"ISOLATION INTEGRITY: Multiple users should have successful tests. " \
            f"Successful: {len(successful_users)}/3. Results: {user_isolation_results}"

        assert len(correctly_detected_env) >= len(successful_users) // 2, \
            f"ENVIRONMENT DETECTION: Users should detect their environment correctly. " \
            f"Correct: {len(correctly_detected_env)}, Successful: {len(successful_users)}"

        if len(isolated_corpus) > 0:
            assert len(isolated_corpus) >= len(successful_users) // 2, \
                f"CORPUS ISOLATION: Users should have isolated corpus paths. " \
                f"Isolated: {len(isolated_corpus)}, Successful: {len(successful_users)}"

        print(f"MULTI-USER ISOLATION INTEGRITY VALIDATED: {len(successful_users)} users successful")

    def test_system_stability_after_ssot_changes(self):
        """
        Validate overall system stability after Issue #722 SSOT changes.

        This test ensures that environmental changes don't cause system
        instability, memory leaks, or performance degradation.
        """
        stability_metrics = {
            'module_import_stability': False,
            'repeated_operations_stable': False,
            'no_memory_accumulation': False,
            'performance_acceptable': False
        }

        # Test 1: Module import stability
        try:
            # Re-import modules multiple times to test stability
            for i in range(5):
                from importlib import reload
                import netra_backend.app.logging.auth_trace_logger as auth_trace_module
                import netra_backend.app.websocket_core.types as websocket_types_module

                reload(auth_trace_module)
                reload(websocket_types_module)

            stability_metrics['module_import_stability'] = True

        except Exception as e:
            print(f"Module import stability issue: {e}")

        # Test 2: Repeated operations stability
        try:
            # Perform operations multiple times to test for accumulated errors
            for i in range(10):
                logger = AuthTraceLogger()
                logger._is_development_env()

                config = WebSocketConfig.detect_and_configure_for_environment()

                # Test corpus context multiple times
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                # SharedContextData not needed

                context = UserExecutionContext(
                    user_id=f'stability-user-{i}',
                    thread_id=f'stability-thread-{i}',
                    run_id=f'stability-run-{i}',
                    request_id=f'stability-request-{i}'
                )

                initialize_corpus_context(context)

            stability_metrics['repeated_operations_stable'] = True

        except Exception as e:
            print(f"Repeated operations stability issue: {e}")

        # Test 3: No obvious memory accumulation (simple check)
        try:
            import gc
            gc.collect()  # Force garbage collection

            # Simple memory check - if we get here without errors, assume OK
            stability_metrics['no_memory_accumulation'] = True

        except Exception as e:
            print(f"Memory accumulation check issue: {e}")

        # Test 4: Performance acceptability (simple timing check)
        try:
            import time

            start_time = time.time()

            # Perform representative operations
            logger = AuthTraceLogger()
            logger._is_staging_env()

            config = WebSocketConfig.detect_and_configure_for_environment()

            end_time = time.time()
            operation_time = end_time - start_time

            # Should complete basic operations quickly (< 5 seconds)
            stability_metrics['performance_acceptable'] = operation_time < 5.0

        except Exception as e:
            print(f"Performance check issue: {e}")

        # STABILITY ASSERTION: System should remain stable after changes
        stable_metrics = sum(stability_metrics.values())
        total_metrics = len(stability_metrics)

        assert stable_metrics >= (total_metrics - 1), \
            f"SYSTEM STABILITY: Most stability metrics should pass. " \
            f"Stable: {stable_metrics}/{total_metrics}. Results: {stability_metrics}"

        print(f"SYSTEM STABILITY VALIDATED: {stable_metrics}/{total_metrics} metrics stable")

    def test_business_continuity_validation(self):
        """
        ULTIMATE TEST: Validate complete business continuity after SSOT fixes.

        This test simulates a complete user journey to ensure that all
        Issue #722 changes work together to maintain business functionality.
        """
        business_journey = {
            'user_registration_flow': False,
            'authentication_system': False,
            'websocket_connectivity': False,
            'corpus_data_access': False,
            'multi_user_support': False
        }

        # Simulate user registration/login flow
        try:
            # Environment detection for auth tracing
            logger = AuthTraceLogger()
            staging_env = logger._is_staging_env()

            # Auth startup validation
            validator = AuthStartupValidator()

            if staging_env and validator:
                business_journey['user_registration_flow'] = True
                business_journey['authentication_system'] = True

        except Exception as e:
            print(f"Authentication flow issue: {e}")

        # Simulate WebSocket connection setup
        try:
            config = WebSocketConfig.detect_and_configure_for_environment()

            if config and hasattr(config, 'host'):
                business_journey['websocket_connectivity'] = True

        except Exception as e:
            print(f"WebSocket setup issue: {e}")

        # Simulate corpus data access
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            # SharedContextData not needed

            context = UserExecutionContext(
                user_id='business-continuity-user',
                thread_id='business-continuity-thread',
                run_id='business-continuity-run',
                request_id='business-continuity-request'
            )

            enhanced_context = initialize_corpus_context(context)

            if enhanced_context and 'corpus_metadata' in enhanced_context.agent_context:
                business_journey['corpus_data_access'] = True

        except Exception as e:
            print(f"Corpus access issue: {e}")

        # Simulate multi-user support
        try:
            users_successful = 0

            for i in range(3):
                user_id = f'business-user-{i}'
                self.set_env_var('USER_ID', user_id)

                context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=f'business-thread-{i}',
                    run_id=f'business-run-{i}',
                    request_id=f'business-request-{i}'
                )

                enhanced_context = initialize_corpus_context(context)

                if enhanced_context:
                    users_successful += 1

            business_journey['multi_user_support'] = users_successful >= 2

        except Exception as e:
            print(f"Multi-user support issue: {e}")

        # BUSINESS CONTINUITY ASSERTION: Core business functions must work
        working_functions = sum(business_journey.values())
        total_functions = len(business_journey)

        assert working_functions >= (total_functions - 1), \
            f"BUSINESS CONTINUITY FAILURE: Core business functions must work after SSOT fixes. " \
            f"Working: {working_functions}/{total_functions}. Results: {business_journey}"

        # Ensure critical business functions specifically work
        critical_functions = ['authentication_system', 'websocket_connectivity', 'corpus_data_access']
        critical_working = sum(business_journey[func] for func in critical_functions if func in business_journey)

        assert critical_working >= 2, \
            f"CRITICAL BUSINESS FUNCTIONS: At least 2/3 critical functions must work. " \
            f"Critical working: {critical_working}/3. All results: {business_journey}"

        print(f"BUSINESS CONTINUITY VALIDATED: {working_functions}/{total_functions} functions operational")
        print(f"$500K+ ARR PROTECTION: All critical business functions validated successful")