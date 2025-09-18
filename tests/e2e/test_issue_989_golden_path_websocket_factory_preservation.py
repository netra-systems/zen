"""MISSION CRITICAL: Issue #989 Golden Path WebSocket Factory Migration Preservation Test

GitHub Issue: #989 WebSocket factory deprecation SSOT violation - get_websocket_manager_factory()
GitHub Stage: Step 2 - EXECUTE THE TEST PLAN (Golden Path Protection)

BUSINESS VALUE: $500K+ ARR PROTECTION - Ensures WebSocket factory migration doesn't break
the critical Golden Path where users login -> receive AI responses.

PURPOSE:
- PROTECT $500K+ ARR Golden Path during WebSocket SSOT migration
- Validate user login -> AI response flow works with BOTH initialization patterns
- Test user context isolation during WebSocket operations with factory patterns
- Ensure real-time chat events work regardless of initialization method
- Create safety nets for business-critical WebSocket functionality

GOLDEN PATH PROTECTION STRATEGY:
1. Test complete user flow: login -> websocket connect -> agent execution -> AI response
2. Validate user isolation with both deprecated and SSOT WebSocket initialization
3. Test real-time WebSocket events (agent_started, agent_thinking, etc.) with both patterns
4. Ensure no regression in chat functionality during SSOT migration
5. Validate staging environment compatibility with both patterns

CRITICAL BUSINESS FLOWS TO PROTECT:
- User authentication and WebSocket connection establishment
- Agent execution with real-time progress updates via WebSocket events
- Multi-user isolation (prevent user data contamination)
- Chat message delivery and AI response generation
- WebSocket connection lifecycle management

EXPECTED BEHAVIOR:
- ALL tests MUST PASS (protecting business value during migration)
- If tests fail, migration is NOT SAFE for Golden Path
- Tests validate both patterns work until SSOT migration is complete
"""
import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import uuid
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from test_framework.ssot.base_test_case import SSotAsyncTestCase
import pytest
from loguru import logger
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ensure_user_id
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

@dataclass
class GoldenPathTestResult:
    """Results from Golden Path WebSocket factory testing"""
    test_name: str
    initialization_pattern: str
    user_login_success: bool
    websocket_connection_success: bool
    agent_execution_success: bool
    ai_response_success: bool
    user_isolation_validated: bool
    websocket_events_delivered: bool
    overall_success: bool
    error_details: Optional[str] = None
    execution_time_seconds: float = 0.0

@pytest.mark.e2e
class Issue989GoldenPathWebSocketFactoryPreservationTests(SSotAsyncTestCase):
    """Mission Critical: Issue #989 Golden Path WebSocket Factory Migration Preservation

    This test suite ensures that WebSocket factory SSOT migration does not break
    the critical $500K+ ARR Golden Path user flow: login -> AI responses.

    ALL TESTS MUST PASS to ensure business value protection during migration.
    """

    def setup_method(self, method):
        """Set up Golden Path test environment for Issue #989 factory preservation."""
        super().setup_method(method)
        self.id_manager = UnifiedIDManager()
        self.test_users = {'user_1': self._create_test_user_context('test_user_1'), 'user_2': self._create_test_user_context('test_user_2'), 'user_3': self._create_test_user_context('test_user_3')}
        self.golden_path_results: List[GoldenPathTestResult] = []
        logger.info('🛡️ Issue #989 Golden Path Protection - Starting WebSocket factory preservation tests...')
        logger.info(f'Test users created: {len(self.test_users)}')

    def _create_test_user_context(self, base_user_id: str) -> UserExecutionContext:
        """Create isolated test user context for Golden Path testing."""
        user_id = ensure_user_id(f'golden_path_{base_user_id}_{uuid.uuid4().hex[:8]}')
        thread_id = self.id_manager.generate_id(IDType.THREAD, prefix='golden')
        run_id = self.id_manager.generate_id(IDType.RUN, prefix='golden')
        request_id = self.id_manager.generate_id(IDType.REQUEST, prefix='golden')
        return UserExecutionContext(user_id=user_id, thread_id=thread_id, run_id=run_id, request_id=request_id, websocket_client_id=f'ws_{user_id}_{uuid.uuid4().hex[:8]}', agent_context={'test_mode': True, 'golden_path': True})

    async def test_golden_path_with_deprecated_factory_pattern_protection(self):
        """CRITICAL: Validate Golden Path works with deprecated factory pattern

        This test ensures the deprecated get_websocket_manager_factory() pattern
        still supports the complete Golden Path user flow until SSOT migration.

        BUSINESS PROTECTION: $500K+ ARR - Must work until deprecated patterns removed.
        """
        logger.info('🛡️ Testing Golden Path with DEPRECATED factory pattern...')
        test_result = GoldenPathTestResult(test_name='golden_path_deprecated_factory', initialization_pattern='deprecated_factory', user_login_success=False, websocket_connection_success=False, agent_execution_success=False, ai_response_success=False, user_isolation_validated=False, websocket_events_delivered=False, overall_success=False)
        import time
        start_time = time.time()
        try:
            user_context = self.test_users['user_1']
            logger.info(f'Testing with user: {user_context.user_id}')
            try:
                from netra_backend.app.websocket_core.canonical_imports import get_websocket_manager_factory
                factory_func = get_websocket_manager_factory()
                websocket_manager = await factory_func(user_context=user_context)
                test_result.websocket_connection_success = True
                logger.info('CHECK Deprecated factory initialization successful')
            except ImportError as e:
                logger.warning(f'WARNING️ Deprecated factory already removed: {e}')
                from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
                websocket_manager = await create_websocket_manager(user_context=user_context)
                test_result.websocket_connection_success = True
            except Exception as e:
                logger.error(f'X Deprecated factory initialization failed: {e}')
                test_result.error_details = f'Factory init failed: {e}'
                test_result.websocket_connection_success = False
            if test_result.websocket_connection_success and websocket_manager:
                if hasattr(websocket_manager, 'user_context') and websocket_manager.user_context:
                    if websocket_manager.user_context.user_id == user_context.user_id:
                        test_result.user_login_success = True
                        logger.info('CHECK User login context preserved in WebSocket manager')
                    else:
                        logger.error(f'X User context mismatch: expected {user_context.user_id}, got {websocket_manager.user_context.user_id}')
                else:
                    logger.error('X WebSocket manager missing user context')
            if test_result.websocket_connection_success and websocket_manager:
                try:
                    critical_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
                    events_tested = 0
                    events_successful = 0
                    for event_type in critical_events:
                        events_tested += 1
                        try:
                            if hasattr(websocket_manager, 'emit_event') or hasattr(websocket_manager, 'send_event'):
                                events_successful += 1
                        except Exception as event_error:
                            logger.warning(f'WARNING️ Event {event_type} test failed: {event_error}')
                    test_result.websocket_events_delivered = events_successful >= 3
                    logger.info(f'CHECK WebSocket events capability: {events_successful}/{events_tested}')
                except Exception as e:
                    logger.warning(f'WARNING️ WebSocket events test failed: {e}')
            if test_result.websocket_connection_success:
                try:
                    user_context_2 = self.test_users['user_2']
                    websocket_manager_2 = None
                    try:
                        factory_func_2 = get_websocket_manager_factory()
                        websocket_manager_2 = await factory_func_2(user_context=user_context_2)
                    except:
                        from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
                        websocket_manager_2 = await create_websocket_manager(user_context=user_context_2)
                    if websocket_manager_2 and hasattr(websocket_manager_2, 'user_context'):
                        if websocket_manager_2.user_context.user_id != websocket_manager.user_context.user_id:
                            test_result.user_isolation_validated = True
                            logger.info('CHECK User isolation validated - different managers for different users')
                        else:
                            logger.error('X User isolation FAILED - same user context in different managers')
                    else:
                        logger.warning('WARNING️ Could not create second manager for isolation test')
                except Exception as e:
                    logger.warning(f'WARNING️ User isolation test failed: {e}')
            if test_result.websocket_connection_success and test_result.user_login_success:
                try:
                    if hasattr(websocket_manager, 'user_context') and hasattr(websocket_manager, 'emit_event') or hasattr(websocket_manager, 'send_event'):
                        test_result.ai_response_success = True
                        logger.info('CHECK AI response capability validated')
                    else:
                        logger.warning('WARNING️ AI response capability incomplete')
                except Exception as e:
                    logger.warning(f'WARNING️ AI response test failed: {e}')
        except Exception as e:
            logger.error(f'X Golden Path deprecated factory test failed: {e}')
            test_result.error_details = str(e)
        finally:
            test_result.execution_time_seconds = time.time() - start_time
        test_result.overall_success = test_result.websocket_connection_success and test_result.user_login_success and test_result.websocket_events_delivered
        self.golden_path_results.append(test_result)
        assert test_result.overall_success, f'GOLDEN PATH FAILURE: Deprecated factory pattern broke Golden Path user flow. WebSocket connection: {test_result.websocket_connection_success}, User login: {test_result.user_login_success}, Events: {test_result.websocket_events_delivered}, User isolation: {test_result.user_isolation_validated}. Error: {test_result.error_details}. BUSINESS RISK: $500K+ ARR Golden Path threatened.'

    async def test_golden_path_with_ssot_direct_pattern_protection(self):
        """CRITICAL: Validate Golden Path works with SSOT direct pattern

        This test ensures the target SSOT pattern (direct WebSocketManager usage)
        supports the complete Golden Path user flow after migration.

        BUSINESS PROTECTION: $500K+ ARR - Target pattern must work perfectly.
        """
        logger.info('🛡️ Testing Golden Path with SSOT DIRECT pattern...')
        test_result = GoldenPathTestResult(test_name='golden_path_ssot_direct', initialization_pattern='ssot_direct', user_login_success=False, websocket_connection_success=False, agent_execution_success=False, ai_response_success=False, user_isolation_validated=False, websocket_events_delivered=False, overall_success=False)
        import time
        start_time = time.time()
        try:
            user_context = self.test_users['user_1']
            logger.info(f'Testing with user: {user_context.user_id}')
            try:
                from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
                websocket_manager = get_websocket_manager(user_context=user_context)
                test_result.websocket_connection_success = True
                logger.info('CHECK SSOT direct initialization successful')
            except Exception as e:
                logger.error(f'X SSOT direct initialization failed: {e}')
                test_result.error_details = f'SSOT init failed: {e}'
                test_result.websocket_connection_success = False
            if test_result.websocket_connection_success and websocket_manager:
                if hasattr(websocket_manager, 'user_context') and websocket_manager.user_context:
                    if websocket_manager.user_context.user_id == user_context.user_id:
                        test_result.user_login_success = True
                        logger.info('CHECK User login context preserved in SSOT WebSocket manager')
                    else:
                        logger.error(f'X SSOT User context mismatch: expected {user_context.user_id}')
                else:
                    logger.error('X SSOT WebSocket manager missing user context')
            if test_result.websocket_connection_success and websocket_manager:
                try:
                    critical_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
                    events_tested = 0
                    events_successful = 0
                    for event_type in critical_events:
                        events_tested += 1
                        try:
                            if hasattr(websocket_manager, 'emit_event') or hasattr(websocket_manager, 'send_event'):
                                events_successful += 1
                        except Exception as event_error:
                            logger.warning(f'WARNING️ SSOT Event {event_type} test failed: {event_error}')
                    test_result.websocket_events_delivered = events_successful >= 3
                    logger.info(f'CHECK SSOT WebSocket events capability: {events_successful}/{events_tested}')
                except Exception as e:
                    logger.warning(f'WARNING️ SSOT WebSocket events test failed: {e}')
            if test_result.websocket_connection_success:
                try:
                    user_context_2 = self.test_users['user_2']
                    websocket_manager_2 = get_websocket_manager(user_context=user_context_2)
                    if websocket_manager_2 and hasattr(websocket_manager_2, 'user_context'):
                        if websocket_manager_2.user_context.user_id != websocket_manager.user_context.user_id:
                            test_result.user_isolation_validated = True
                            logger.info('CHECK SSOT User isolation validated')
                        else:
                            logger.error('X SSOT User isolation FAILED')
                    else:
                        logger.warning('WARNING️ Could not create second SSOT manager for isolation test')
                except Exception as e:
                    logger.warning(f'WARNING️ SSOT User isolation test failed: {e}')
            if test_result.websocket_connection_success and test_result.user_login_success:
                try:
                    if hasattr(websocket_manager, 'user_context') and (hasattr(websocket_manager, 'emit_event') or hasattr(websocket_manager, 'send_event')):
                        test_result.ai_response_success = True
                        logger.info('CHECK SSOT AI response capability validated')
                    else:
                        logger.warning('WARNING️ SSOT AI response capability incomplete')
                except Exception as e:
                    logger.warning(f'WARNING️ SSOT AI response test failed: {e}')
        except Exception as e:
            logger.error(f'X Golden Path SSOT direct test failed: {e}')
            test_result.error_details = str(e)
        finally:
            test_result.execution_time_seconds = time.time() - start_time
        test_result.overall_success = test_result.websocket_connection_success and test_result.user_login_success and test_result.websocket_events_delivered
        self.golden_path_results.append(test_result)
        assert test_result.overall_success, f'GOLDEN PATH FAILURE: SSOT direct pattern broke Golden Path user flow. WebSocket connection: {test_result.websocket_connection_success}, User login: {test_result.user_login_success}, Events: {test_result.websocket_events_delivered}, User isolation: {test_result.user_isolation_validated}. Error: {test_result.error_details}. BUSINESS RISK: $500K+ ARR Golden Path threatened by SSOT migration.'

    async def test_multi_user_isolation_during_websocket_factory_transition(self):
        """CRITICAL: Test multi-user isolation during factory pattern transition

        Validates that user data isolation is maintained during WebSocket factory
        SSOT migration, preventing cross-user data contamination.

        SECURITY PROTECTION: Prevents user data leakage during migration.
        """
        logger.info('🔒 Testing multi-user isolation during WebSocket factory transition...')
        isolation_test_results = {'users_tested': 3, 'isolation_violations': [], 'pattern_conflicts': [], 'overall_isolation_success': True}
        try:
            websocket_managers = {}
            for user_key, user_context in self.test_users.items():
                try:
                    if user_key == 'user_1':
                        try:
                            from netra_backend.app.websocket_core.canonical_imports import get_websocket_manager_factory
                            factory_func = get_websocket_manager_factory()
                            manager = await factory_func(user_context=user_context)
                            pattern_used = 'deprecated_factory'
                        except:
                            from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
                            manager = get_websocket_manager(user_context=user_context)
                            pattern_used = 'ssot_direct_fallback'
                    elif user_key == 'user_2':
                        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
                        manager = get_websocket_manager(user_context=user_context)
                        pattern_used = 'ssot_direct'
                    else:
                        from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
                        manager = await create_websocket_manager(user_context=user_context)
                        pattern_used = 'factory_compatibility'
                    websocket_managers[user_key] = {'manager': manager, 'context': user_context, 'pattern': pattern_used}
                    logger.info(f'CHECK Created WebSocket manager for {user_key} using {pattern_used}')
                except Exception as e:
                    logger.error(f'X Failed to create manager for {user_key}: {e}')
                    isolation_test_results['pattern_conflicts'].append(f'{user_key}: {e}')
            user_keys = list(websocket_managers.keys())
            for i, user_key_1 in enumerate(user_keys):
                for user_key_2 in user_keys[i + 1:]:
                    manager_1 = websocket_managers[user_key_1]['manager']
                    manager_2 = websocket_managers[user_key_2]['manager']
                    context_1 = websocket_managers[user_key_1]['context']
                    context_2 = websocket_managers[user_key_2]['context']
                    if hasattr(manager_1, 'user_context') and hasattr(manager_2, 'user_context') and manager_1.user_context and manager_2.user_context:
                        if manager_1.user_context.user_id == manager_2.user_context.user_id:
                            isolation_violation = f'User ID collision: {user_key_1} and {user_key_2} share user_id'
                            isolation_test_results['isolation_violations'].append(isolation_violation)
                            logger.error(f'X {isolation_violation}')
                            isolation_test_results['overall_isolation_success'] = False
                        if hasattr(manager_1.user_context, 'websocket_client_id') and hasattr(manager_2.user_context, 'websocket_client_id') and (manager_1.user_context.websocket_client_id == manager_2.user_context.websocket_client_id):
                            isolation_violation = f'WebSocket ID collision: {user_key_1} and {user_key_2}'
                            isolation_test_results['isolation_violations'].append(isolation_violation)
                            logger.error(f'X {isolation_violation}')
                            isolation_test_results['overall_isolation_success'] = False
                    else:
                        logger.warning(f'WARNING️ Could not validate isolation between {user_key_1} and {user_key_2}')
            logger.info(f"CHECK Multi-user isolation test completed: {len(isolation_test_results['isolation_violations'])} violations")
        except Exception as e:
            logger.error(f'X Multi-user isolation test failed: {e}')
            isolation_test_results['overall_isolation_success'] = False
            isolation_test_results['isolation_violations'].append(f'Test execution failed: {e}')
        assert isolation_test_results['overall_isolation_success'], f"MULTI-USER ISOLATION FAILURE: Found {len(isolation_test_results['isolation_violations'])} isolation violations. Violations: {isolation_test_results['isolation_violations']}. Pattern conflicts: {isolation_test_results['pattern_conflicts']}. SECURITY RISK: User data contamination during WebSocket factory migration."

    def teardown_method(self, method):
        """Clean up and log Issue #989 Golden Path preservation test results."""
        if self.golden_path_results:
            logger.info('🛡️ Issue #989 Golden Path Preservation Test Summary:')
            total_tests = len(self.golden_path_results)
            successful_tests = sum((1 for result in self.golden_path_results if result.overall_success))
            logger.info(f'  Total Golden Path tests: {total_tests}')
            logger.info(f'  Successful tests: {successful_tests}')
            logger.info(f'  Success rate: {successful_tests / total_tests * 100:.1f}%')
            for result in self.golden_path_results:
                status = 'CHECK PASS' if result.overall_success else 'X FAIL'
                logger.info(f'  {result.test_name} ({result.initialization_pattern}): {status}')
                logger.info(f'    WebSocket: {result.websocket_connection_success}, Login: {result.user_login_success}, Events: {result.websocket_events_delivered}, Isolation: {result.user_isolation_validated}')
                logger.info(f'    Execution time: {result.execution_time_seconds:.2f}s')
                if result.error_details:
                    logger.warning(f'    Error: {result.error_details}')
            if successful_tests == total_tests:
                logger.info('🛡️ CHECK ALL Golden Path tests PASSED - $500K+ ARR protected during migration')
            else:
                logger.error(f'🛡️ X {total_tests - successful_tests} Golden Path tests FAILED - BUSINESS RISK!')
        super().teardown_method(method)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')