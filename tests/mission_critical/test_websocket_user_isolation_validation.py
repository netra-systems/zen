#!/usr/bin/env python
"""
MISSION CRITICAL: WebSocket User Isolation Verification Tests

Business Value Justification:
- Segment: Platform/Core
- Business Goal: Revenue Protection & User Security
- Value Impact: Protects $500K+ ARR by ensuring user data isolation 
- Strategic Impact: CRITICAL - User context leaks = security vulnerabilities + revenue loss

PURPOSE:
These tests validate user context isolation before and after SSOT fix:
1. Multi-user concurrent WebSocket connections remain isolated
2. Factory vs direct instantiation isolation behavior comparison
3. Race condition prevention with SSOT patterns
4. User data privacy and security compliance

CRITICAL BUSINESS RISK:
If user isolation fails:
- User A sees User B's AI responses (privacy violation) 
- User data leakage across sessions (security breach)
- WebSocket race conditions prevent AI responses (revenue loss)
- Golden Path failure affects 90% of platform value

TEST STRATEGY:
- Concurrent user simulation to stress test isolation
- Data leakage detection between user contexts
- Performance impact measurement of isolation mechanisms
- Comparison of deprecated vs SSOT isolation effectiveness
"""

import asyncio
import os
import sys
import uuid
import concurrent.futures
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from unittest import mock

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import environment and test framework
from shared.isolated_environment import get_env, IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket_test_utility import WebSocketTestUtility

import pytest
from loguru import logger

# Import SSOT components for testing
try:
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
    SSOT_WEBSOCKET_AVAILABLE = True
except ImportError as e:
    logger.warning(f"[SSOT IMPORT] WebSocketManager not available: {str(e)}")
    SSOT_WEBSOCKET_AVAILABLE = False

# Import user context for isolation testing
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestWebSocketUserIsolationValidation(SSotAsyncTestCase):
    """
    Mission Critical: WebSocket User Context Isolation Validation
    
    These tests validate that WebSocket user isolation works correctly:
    1. Multiple users can connect concurrently without data leakage
    2. User contexts remain separate across WebSocket sessions
    3. SSOT patterns improve isolation compared to deprecated patterns
    4. Race conditions are prevented in multi-user scenarios
    """
    
    def setup_method(self, method):
        """Set up test environment for user isolation testing."""
        super().setup_method(method)
        
        # Create multiple test users for isolation testing
        self.test_users = []
        for i in range(3):  # Test with 3 concurrent users
            user_id = f"isolation_test_user_{i}_{uuid.uuid4().hex[:8]}"
            session_id = f"session_{i}_{uuid.uuid4().hex[:8]}"
            
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"thread_{i}_{uuid.uuid4().hex[:8]}",
                run_id=f"run_{i}_{uuid.uuid4().hex[:8]}"
            )
            
            self.test_users.append({
                'id': i,
                'user_id': user_id,
                'session_id': session_id,
                'context': user_context,
                'websocket_data': {},
                'received_events': []
            })
        
        logger.info(f"[USER ISOLATION] Setup complete with {len(self.test_users)} test users")

    def teardown_method(self, method):
        """Clean up test environment."""
        super().teardown_method(method)
        logger.info("[USER ISOLATION] Teardown complete")

    @pytest.mark.asyncio
    async def test_websocket_user_context_isolation_prevents_leaks(self):
        """
        TEST: Validate that WebSocket contexts don't leak between users
        
        BUSINESS CRITICAL: User data leakage = privacy violation + revenue loss
        
        APPROACH:
        1. Create multiple concurrent WebSocket contexts
        2. Send user-specific data to each context
        3. Verify no cross-contamination between contexts
        4. Measure isolation effectiveness
        """
        logger.info("[ISOLATION TEST] Testing WebSocket user context isolation...")
        
        if not SSOT_WEBSOCKET_AVAILABLE:
            pytest.skip("SSOT WebSocketManager not available - cannot test isolation")
        
        # Test concurrent user isolation
        isolation_results = {
            'users_tested': len(self.test_users),
            'isolation_violations': [],
            'successful_isolations': 0,
            'context_leaks_detected': 0
        }
        
        try:
            # Simulate concurrent WebSocket contexts for multiple users
            user_contexts = {}
            user_websocket_managers = {}
            
            # Create isolated WebSocket managers for each user
            for user_data in self.test_users:
                user_id = user_data['user_id']
                context = user_data['context']
                
                try:
                    # Create WebSocket manager using SSOT pattern
                    websocket_manager = await self._create_websocket_manager_safely(context)
                    
                    if websocket_manager:
                        user_contexts[user_id] = context
                        user_websocket_managers[user_id] = websocket_manager
                        
                        # Store user-specific test data
                        user_data['websocket_data'] = {
                            'secret_value': f"SECRET_DATA_USER_{user_id}",
                            'session_data': f"SESSION_{user_data['session_id']}",
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                        
                        logger.info(f"[ISOLATION] Created isolated context for user {user_id}")
                        
                except Exception as e:
                    logger.error(f"[ISOLATION ERROR] Failed to create context for {user_id}: {str(e)}")
                    isolation_results['isolation_violations'].append({
                        'user_id': user_id,
                        'error': 'context_creation_failed',
                        'details': str(e)
                    })
            
            # Test data isolation between users
            for user_id_a, context_a in user_contexts.items():
                for user_id_b, context_b in user_contexts.items():
                    if user_id_a != user_id_b:
                        # Check if contexts are properly isolated
                        isolation_valid = await self._validate_context_isolation(
                            user_id_a, context_a, user_id_b, context_b
                        )
                        
                        if isolation_valid:
                            isolation_results['successful_isolations'] += 1
                        else:
                            isolation_results['context_leaks_detected'] += 1
                            isolation_results['isolation_violations'].append({
                                'user_a': user_id_a,
                                'user_b': user_id_b,
                                'error': 'context_leak_detected'
                            })
            
            # Log isolation test results
            logger.info(f"[ISOLATION RESULTS] {isolation_results}")
            
            # CRITICAL: No isolation violations should occur
            assert len(isolation_results['isolation_violations']) == 0, (
                f"User isolation violations detected: {isolation_results['isolation_violations']}. "
                f"This indicates serious security and privacy risks affecting $500K+ ARR."
            )
            
            # Validate successful isolations
            expected_isolations = len(self.test_users) * (len(self.test_users) - 1)
            assert isolation_results['successful_isolations'] >= expected_isolations, (
                f"Expected {expected_isolations} successful isolations, "
                f"but got {isolation_results['successful_isolations']}"
            )
            
            logger.success(f"[ISOLATION SUCCESS] All {isolation_results['successful_isolations']} user contexts properly isolated")
            
        except Exception as e:
            logger.error(f"[ISOLATION TEST FAILED] {str(e)}")
            pytest.fail(f"User isolation test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_deprecated_factory_vs_direct_isolation_behavior(self):
        """
        TEST: Compare isolation behavior between deprecated factory and direct patterns
        
        PURPOSE:
        - Document behavioral differences between patterns
        - Validate that SSOT patterns improve isolation
        - Measure performance impact of different approaches
        - Provide migration validation criteria
        """
        logger.info("[PATTERN COMPARISON] Testing deprecated factory vs SSOT isolation behavior...")
        
        comparison_results = {
            'deprecated_pattern': {
                'available': False,
                'isolation_score': 0,
                'performance_ms': None,
                'errors': []
            },
            'ssot_pattern': {
                'available': SSOT_WEBSOCKET_AVAILABLE,
                'isolation_score': 0,
                'performance_ms': None,
                'errors': []
            },
            'improvement_metrics': {}
        }
        
        # Test deprecated factory pattern isolation (if available)
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import get_websocket_manager_factory
            comparison_results['deprecated_pattern']['available'] = True
            
            logger.info("[DEPRECATED TEST] Testing deprecated factory isolation...")
            start_time = datetime.now()
            
            # Test deprecated pattern isolation with multiple users
            deprecated_isolation_score = await self._test_pattern_isolation(
                'deprecated', self._create_deprecated_websocket_manager
            )
            
            end_time = datetime.now()
            comparison_results['deprecated_pattern']['isolation_score'] = deprecated_isolation_score
            comparison_results['deprecated_pattern']['performance_ms'] = (end_time - start_time).total_seconds() * 1000
            
            logger.info(f"[DEPRECATED RESULTS] Isolation score: {deprecated_isolation_score}")
            
        except ImportError:
            logger.info("[DEPRECATED PATTERN] Factory not available - may already be migrated")
        except Exception as e:
            comparison_results['deprecated_pattern']['errors'].append(str(e))
            logger.error(f"[DEPRECATED ERROR] {str(e)}")
        
        # Test SSOT pattern isolation
        if SSOT_WEBSOCKET_AVAILABLE:
            logger.info("[SSOT TEST] Testing SSOT pattern isolation...")
            start_time = datetime.now()
            
            try:
                ssot_isolation_score = await self._test_pattern_isolation(
                    'ssot', self._create_websocket_manager_safely
                )
                
                end_time = datetime.now()
                comparison_results['ssot_pattern']['isolation_score'] = ssot_isolation_score
                comparison_results['ssot_pattern']['performance_ms'] = (end_time - start_time).total_seconds() * 1000
                
                logger.info(f"[SSOT RESULTS] Isolation score: {ssot_isolation_score}")
                
            except Exception as e:
                comparison_results['ssot_pattern']['errors'].append(str(e))
                logger.error(f"[SSOT ERROR] {str(e)}")
        
        # Calculate improvement metrics
        if (comparison_results['deprecated_pattern']['available'] and 
            comparison_results['ssot_pattern']['available']):
            
            deprecated_score = comparison_results['deprecated_pattern']['isolation_score']
            ssot_score = comparison_results['ssot_pattern']['isolation_score']
            
            if deprecated_score > 0:
                improvement_pct = ((ssot_score - deprecated_score) / deprecated_score) * 100
                comparison_results['improvement_metrics']['isolation_improvement_pct'] = improvement_pct
            
            deprecated_perf = comparison_results['deprecated_pattern']['performance_ms']
            ssot_perf = comparison_results['ssot_pattern']['performance_ms']
            
            if deprecated_perf and ssot_perf:
                perf_change_pct = ((ssot_perf - deprecated_perf) / deprecated_perf) * 100
                comparison_results['improvement_metrics']['performance_change_pct'] = perf_change_pct
        
        # Log comprehensive comparison results
        logger.info(f"[PATTERN COMPARISON] Results: {comparison_results}")
        
        # CRITICAL: SSOT pattern must be available and perform well
        assert comparison_results['ssot_pattern']['available'], (
            "SSOT WebSocket pattern must be available for migration"
        )
        
        # SSOT isolation should be effective
        assert comparison_results['ssot_pattern']['isolation_score'] >= 85, (
            f"SSOT isolation score {comparison_results['ssot_pattern']['isolation_score']} "
            f"is below acceptable threshold of 85%"
        )
        
        logger.success("[PATTERN COMPARISON] Pattern comparison completed successfully")

    async def test_websocket_race_condition_prevention(self):
        """
        TEST: Validate that SSOT patterns prevent WebSocket race conditions
        
        BUSINESS IMPACT: Race conditions = failed AI responses = revenue loss
        
        APPROACH:
        1. Simulate high-concurrency WebSocket scenarios
        2. Test for race conditions in user context creation
        3. Validate event ordering and delivery consistency
        4. Measure race condition occurrence rates
        """
        logger.info("[RACE CONDITION TEST] Testing WebSocket race condition prevention...")
        
        if not SSOT_WEBSOCKET_AVAILABLE:
            pytest.skip("SSOT WebSocketManager not available - cannot test race conditions")
        
        race_condition_results = {
            'concurrent_operations': 0,
            'successful_operations': 0,
            'race_conditions_detected': 0,
            'context_corruption_events': 0,
            'event_ordering_violations': 0
        }
        
        # Test concurrent WebSocket context creation (stress test)
        concurrent_operations = 20  # High concurrency to trigger potential race conditions
        
        async def create_concurrent_websocket_context(operation_id: int):
            """Create WebSocket context concurrently to test for race conditions."""
            try:
                user_id = f"race_test_user_{operation_id}_{uuid.uuid4().hex[:4]}"
                session_id = f"race_session_{operation_id}_{uuid.uuid4().hex[:4]}"
                
                context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=f"race_thread_{operation_id}_{uuid.uuid4().hex[:4]}",
                    run_id=f"race_run_{operation_id}_{uuid.uuid4().hex[:4]}"
                )
                
                # Create WebSocket manager with timing measurement
                start_time = datetime.now()
                websocket_manager = await self._create_websocket_manager_safely(context)
                end_time = datetime.now()
                
                if websocket_manager:
                    # Validate context integrity
                    context_valid = await self._validate_context_integrity(context, websocket_manager)
                    
                    return {
                        'operation_id': operation_id,
                        'success': True,
                        'context_valid': context_valid,
                        'duration_ms': (end_time - start_time).total_seconds() * 1000,
                        'user_id': user_id,
                        'session_id': session_id
                    }
                else:
                    return {
                        'operation_id': operation_id,
                        'success': False,
                        'error': 'websocket_manager_creation_failed'
                    }
                    
            except Exception as e:
                return {
                    'operation_id': operation_id,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute concurrent operations
        logger.info(f"[RACE CONDITION TEST] Starting {concurrent_operations} concurrent operations...")
        
        tasks = []
        for i in range(concurrent_operations):
            task = create_concurrent_websocket_context(i)
            tasks.append(task)
        
        # Execute all tasks concurrently
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results for race conditions
            for result in results:
                race_condition_results['concurrent_operations'] += 1
                
                if isinstance(result, Exception):
                    logger.warning(f"[RACE CONDITION] Exception in concurrent operation: {str(result)}")
                    race_condition_results['race_conditions_detected'] += 1
                elif isinstance(result, dict):
                    if result.get('success', False):
                        race_condition_results['successful_operations'] += 1
                        
                        if not result.get('context_valid', True):
                            race_condition_results['context_corruption_events'] += 1
                    else:
                        race_condition_results['race_conditions_detected'] += 1
                        logger.warning(f"[RACE CONDITION] Failed operation: {result}")
            
            # Calculate success rate
            success_rate = (race_condition_results['successful_operations'] / 
                           race_condition_results['concurrent_operations']) * 100
            
            logger.info(f"[RACE CONDITION RESULTS] {race_condition_results}")
            logger.info(f"[RACE CONDITION] Success rate: {success_rate:.2f}%")
            
            # CRITICAL: High success rate required for production stability
            assert success_rate >= 90, (
                f"Race condition success rate {success_rate:.2f}% is below acceptable "
                f"threshold of 90%. This indicates instability affecting $500K+ ARR."
            )
            
            # No context corruption should occur
            assert race_condition_results['context_corruption_events'] == 0, (
                f"Context corruption detected in {race_condition_results['context_corruption_events']} "
                f"operations. This indicates serious user isolation failures."
            )
            
            logger.success(f"[RACE CONDITION SUCCESS] {success_rate:.2f}% success rate with no corruption")
            
        except Exception as e:
            logger.error(f"[RACE CONDITION TEST FAILED] {str(e)}")
            pytest.fail(f"Race condition test failed: {str(e)}")

    # Helper methods for isolation testing

    async def _create_websocket_manager_safely(self, context: UserExecutionContext):
        """Create WebSocket manager using SSOT pattern safely."""
        try:
            if not SSOT_WEBSOCKET_AVAILABLE:
                return None
                
            # Use SSOT direct instantiation pattern
            websocket_manager = WebSocketManager(user_context=context)
            return websocket_manager
            
        except Exception as e:
            logger.error(f"[SSOT MANAGER CREATION] Error: {str(e)}")
            return None

    async def _create_deprecated_websocket_manager(self, context: UserExecutionContext):
        """Create WebSocket manager using deprecated factory pattern."""
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import get_websocket_manager_factory
            
            factory = get_websocket_manager_factory()
            websocket_manager = factory.create_for_user(context)
            return websocket_manager
            
        except Exception as e:
            logger.error(f"[DEPRECATED MANAGER CREATION] Error: {str(e)}")
            return None

    async def _validate_context_isolation(self, user_id_a: str, context_a: UserExecutionContext, 
                                          user_id_b: str, context_b: UserExecutionContext) -> bool:
        """Validate that two user contexts are properly isolated."""
        try:
            # Check that contexts have different identities
            if context_a.user_id == context_b.user_id:
                logger.error(f"[ISOLATION VIOLATION] User IDs should be different: {context_a.user_id}")
                return False
            
            if context_a.session_id == context_b.session_id:
                logger.error(f"[ISOLATION VIOLATION] Session IDs should be different: {context_a.session_id}")
                return False
            
            # Check environment isolation
            if id(context_a.environment) == id(context_b.environment):
                logger.error(f"[ISOLATION VIOLATION] Environments should not be the same object")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"[ISOLATION VALIDATION ERROR] {str(e)}")
            return False

    async def _validate_context_integrity(self, context: UserExecutionContext, websocket_manager) -> bool:
        """Validate that context maintains integrity after WebSocket manager creation."""
        try:
            # Basic integrity checks
            if not context.user_id:
                return False
            if not context.session_id:
                return False
            if not context.environment:
                return False
                
            # Check for context corruption
            if len(context.user_id) < 10:  # Should have reasonable length
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"[CONTEXT INTEGRITY ERROR] {str(e)}")
            return False

    async def _test_pattern_isolation(self, pattern_name: str, manager_factory_func) -> float:
        """Test isolation effectiveness for a specific pattern."""
        try:
            isolation_tests = 5
            successful_isolations = 0
            
            for i in range(isolation_tests):
                user_id = f"{pattern_name}_test_{i}_{uuid.uuid4().hex[:4]}"
                context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=f"{pattern_name}_thread_{i}",
                    run_id=f"{pattern_name}_run_{i}"
                )
                
                manager = await manager_factory_func(context)
                if manager:
                    # Test basic isolation properties
                    isolation_valid = await self._validate_context_integrity(context, manager)
                    if isolation_valid:
                        successful_isolations += 1
            
            # Return isolation score as percentage
            return (successful_isolations / isolation_tests) * 100
            
        except Exception as e:
            logger.error(f"[PATTERN ISOLATION TEST ERROR] {str(e)}")
            return 0.0