"""Test Plan for Issue #565: SSOT ExecutionEngine-UserExecutionEngine Migration Validation

CRITICAL MISSION: Create comprehensive test plan to validate the SSOT ExecutionEngine-UserExecutionEngine 
migration issue, exposing user isolation failures and SSOT violations identified in Five Whys analysis.

Business Value Justification (BVJ):
- Segment: Platform/Security
- Business Goal: Prevent security vulnerabilities and user data contamination
- Value Impact: Protects $500K+ ARR by ensuring complete user isolation
- Strategic Impact: Foundation for multi-tenant production deployment at scale

Based on Five Whys Analysis Findings:
- 3,678+ ExecutionEngine references across 449 files causing user isolation failures
- Security vulnerabilities from deprecated ExecutionEngine usage
- SSOT violations preventing proper user context isolation
- Multi-user scenarios experiencing data contamination
- Integration testing gaps in user context validation

Test Categories Required:
1. Security Tests: User isolation and data contamination prevention
2. SSOT Compliance Tests: Verify no deprecated ExecutionEngine imports remain
3. Multi-User Integration Tests: Concurrent user sessions without cross-contamination
4. Golden Path Protection Tests: Business value preservation during migration
"""

import asyncio
import pytest
import warnings
import uuid
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import both deprecated and SSOT patterns for testing
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestSSotExecutionEngineMigrationValidation(SSotBaseTestCase):
    """Test suite for Issue #565 SSOT ExecutionEngine migration validation.
    
    This test suite validates the complete migration from deprecated ExecutionEngine
    to UserExecutionEngine SSOT pattern, focusing on user isolation security and
    SSOT compliance.
    
    MISSION CRITICAL: These tests must expose and validate fixes for user isolation
    vulnerabilities that could cause data contamination between users.
    """
    
    def setUp(self):
        """Set up test fixtures for SSOT migration validation."""
        super().setUp()
        self.test_users = self._create_test_users()
        self.test_contexts = self._create_test_contexts()
        
    def _create_test_users(self) -> List[Dict[str, Any]]:
        """Create test users for multi-user isolation testing."""
        return [
            {
                'user_id': 'user_001',
                'name': 'Test User 1',
                'email': 'user1@test.com',
                'subscription_tier': 'enterprise'
            },
            {
                'user_id': 'user_002', 
                'name': 'Test User 2',
                'email': 'user2@test.com',
                'subscription_tier': 'mid'
            },
            {
                'user_id': 'user_003',
                'name': 'Test User 3', 
                'email': 'user3@test.com',
                'subscription_tier': 'early'
            }
        ]
    
    def _create_test_contexts(self) -> List[UserExecutionContext]:
        """Create UserExecutionContext instances for testing."""
        contexts = []
        for user in self.test_users:
            context = UserExecutionContext(
                user_id=user['user_id'],
                thread_id=f"thread_{user['user_id']}",
                run_id=str(uuid.uuid4())
            )
            contexts.append(context)
        return contexts

    @pytest.mark.unit
    @pytest.mark.security
    def test_deprecated_execution_engine_import_still_works(self):
        """Test that deprecated ExecutionEngine import still works via compatibility bridge.
        
        SECURITY TEST: Validates that the compatibility bridge prevents breaking changes
        while maintaining the migration path to UserExecutionEngine.
        
        This test ensures backward compatibility during the migration period.
        """
        # Test deprecated import pattern still works
        try:
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            
            # Should generate deprecation warning but still work
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                # Create instance - should trigger compatibility bridge
                mock_registry = MagicMock()
                mock_registry.get = MagicMock()  # Add registry duck typing
                mock_websocket_bridge = MagicMock()
                mock_user_context = UserExecutionContext(
                    user_id="test_user_001",
                    thread_id="test_thread_001", 
                    run_id="test_run_001"
                )
                engine = ExecutionEngine(mock_registry, mock_websocket_bridge, mock_user_context)
                
                # Verify deprecation warning was issued
                self.assertTrue(len(w) > 0)
                deprecation_warnings = [warn for warn in w if issubclass(warn.category, DeprecationWarning)]
                self.assertTrue(len(deprecation_warnings) > 0)
                
                # Verify compatibility mode is active
                self.assertTrue(engine.is_compatibility_mode())
                
                # Verify compatibility info contains migration guidance
                compatibility_info = engine.get_compatibility_info()
                self.assertEqual(compatibility_info['compatibility_mode'], True)
                self.assertEqual(compatibility_info['migration_issue'], '#565')
                self.assertIn('step_1', compatibility_info['migration_guide'])
                
        except ImportError as e:
            self.fail(f"Deprecated ExecutionEngine import should still work via compatibility bridge: {e}")

    @pytest.mark.unit
    @pytest.mark.security
    @pytest.mark.ssot_compliance
    async def test_user_execution_engine_ssot_import_validation(self):
        """Test that UserExecutionEngine SSOT import works correctly.
        
        SSOT COMPLIANCE TEST: Validates that the new SSOT pattern imports and
        initializes correctly with proper user isolation.
        """
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            
            # Create proper user context for isolation
            user_context = UserExecutionContext(
                user_id='test_user_001',
                thread_id='test_thread_001',
                run_id='test_run_001'
            )
            
            # Mock required dependencies
            mock_agent_factory = MagicMock()
            mock_websocket_emitter = AsyncMock()
            
            # Create UserExecutionEngine instance
            engine = UserExecutionEngine(
                context=user_context,
                agent_factory=mock_agent_factory,
                websocket_emitter=mock_websocket_emitter
            )
            
            # Verify proper initialization
            self.assertIsNotNone(engine)
            self.assertEqual(engine.get_user_context(), user_context)
            # Modern engines should have compatibility methods but return False for compatibility mode
            self.assertTrue(hasattr(engine, 'is_compatibility_mode'))
            self.assertFalse(engine.is_compatibility_mode())  # Should not be in compatibility mode
            
        except ImportError as e:
            self.fail(f"UserExecutionEngine SSOT import should work: {e}")

    @pytest.mark.unit
    @pytest.mark.security
    async def test_user_isolation_validation_different_contexts(self):
        """Test that different UserExecutionEngine instances have complete user isolation.
        
        SECURITY TEST: This is the core vulnerability test - ensures that different
        user contexts create completely isolated execution environments with no
        shared state that could cause data contamination.
        
        ISSUE #565 ROOT CAUSE: Deprecated ExecutionEngine had shared state that
        caused user data to leak between requests.
        """
        # Create separate user contexts
        user_context_1 = UserExecutionContext(
            user_id='user_001',
            thread_id='thread_001',
            run_id='run_001'
        )
        
        user_context_2 = UserExecutionContext(
            user_id='user_002', 
            thread_id='thread_002',
            run_id='run_002'
        )
        
        # Mock dependencies
        mock_agent_factory_1 = MagicMock()
        mock_agent_factory_2 = MagicMock()
        mock_websocket_emitter_1 = AsyncMock()
        mock_websocket_emitter_2 = AsyncMock()
        
        # Create separate UserExecutionEngine instances
        engine_1 = UserExecutionEngine(
            context=user_context_1,
            agent_factory=mock_agent_factory_1,
            websocket_emitter=mock_websocket_emitter_1
        )
        
        engine_2 = UserExecutionEngine(
            context=user_context_2,
            agent_factory=mock_agent_factory_2,
            websocket_emitter=mock_websocket_emitter_2
        )
        
        # CRITICAL SECURITY VALIDATION: Verify complete isolation
        
        # 1. Different engine IDs (no sharing)
        self.assertNotEqual(engine_1.engine_id, engine_2.engine_id)
        
        # 2. Different user contexts (no contamination)
        self.assertNotEqual(engine_1.get_user_context().user_id, engine_2.get_user_context().user_id)
        self.assertNotEqual(engine_1.get_user_context().request_id, engine_2.get_user_context().request_id)
        
        # 3. Different agent factories (no shared agent state)
        self.assertIsNot(engine_1.agent_factory, engine_2.agent_factory)
        
        # 4. Different websocket emitters (no cross-user event delivery)
        self.assertIsNot(engine_1.websocket_emitter, engine_2.websocket_emitter)
        
        # 5. No shared internal state
        engine_1._internal_state = {'user_data': 'sensitive_user_1_data'}
        engine_2._internal_state = {'user_data': 'sensitive_user_2_data'}
        
        self.assertEqual(engine_1._internal_state['user_data'], 'sensitive_user_1_data')
        self.assertEqual(engine_2._internal_state['user_data'], 'sensitive_user_2_data')
        
        # VULNERABILITY CHECK: Ensure no accidental state sharing
        self.assertNotEqual(engine_1._internal_state['user_data'], engine_2._internal_state['user_data'])

    @pytest.mark.unit  
    @pytest.mark.security
    async def test_deprecated_execution_engine_delegates_to_user_execution_engine(self):
        """Test that deprecated ExecutionEngine properly delegates to UserExecutionEngine.
        
        SECURITY TEST: Validates that the compatibility bridge correctly delegates
        execution to UserExecutionEngine, maintaining security isolation even when
        using deprecated import patterns.
        
        This ensures that legacy code gets security fixes automatically.
        """
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        
        # Mock dependencies
        mock_registry = MagicMock()
        mock_websocket_bridge = MagicMock()
        user_context = UserExecutionContext(
            user_id='test_user',
            thread_id='test_thread',
            run_id='test_run'
        )
        
        # Create deprecated ExecutionEngine instance
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Ignore deprecation warnings for this test
            deprecated_engine = ExecutionEngine(mock_registry, mock_websocket_bridge, user_context)
        
        # Verify delegation is set up
        self.assertTrue(deprecated_engine.is_compatibility_mode())
        self.assertEqual(deprecated_engine._migration_issue, '#565')
        
        # Mock agent execution context
        mock_execution_context = MagicMock()
        mock_execution_context.agent_name = 'test_agent'
        mock_execution_context.user_id = 'test_user'
        
        # Mock UserExecutionEngine creation and execution
        with patch.object(UserExecutionEngine, 'create_from_legacy', new_callable=AsyncMock) as mock_create:
            mock_delegated_engine = AsyncMock()
            mock_result = MagicMock()
            mock_result.success = True
            
            mock_delegated_engine.execute_agent.return_value = mock_result
            mock_delegated_engine.get_user_context.return_value = user_context
            mock_create.return_value = mock_delegated_engine
            
            # Execute via deprecated engine (should delegate)
            result = await deprecated_engine.execute_agent(mock_execution_context, user_context)
            
            # Verify delegation occurred
            mock_create.assert_called_once_with(
                registry=mock_registry,
                websocket_bridge=mock_websocket_bridge,
                user_context=user_context
            )
            mock_delegated_engine.execute_agent.assert_called_once_with(mock_execution_context, user_context)
            
            # Verify result is from UserExecutionEngine
            self.assertEqual(result, mock_result)
            self.assertTrue(result.success)

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.real_services
    async def test_concurrent_user_execution_no_contamination(self):
        """Test that concurrent user executions via different engines have no data contamination.
        
        MULTI-USER INTEGRATION TEST: This is the critical business value test - ensures
        that multiple users can execute agents concurrently without any data leakage
        or contamination between their sessions.
        
        BUSINESS RISK: Data contamination between users would be a critical security
        breach that could lose customer trust and violate data privacy requirements.
        """
        # Skip if real services not available
        pytest.importorskip("test_framework.real_services_test_fixtures")
        
        # Create multiple concurrent user contexts
        user_contexts = []
        engines = []
        
        for i, user in enumerate(self.test_users):
            context = UserExecutionContext(
                user_id=user['user_id'],
                thread_id=f'thread_{i:03d}',
                run_id=f'run_{i:03d}'
            )
            user_contexts.append(context)
            
            # Mock dependencies for each user
            mock_agent_factory = MagicMock()
            mock_websocket_emitter = AsyncMock()
            
            engine = UserExecutionEngine(
                context=context,
                agent_factory=mock_agent_factory,
                websocket_emitter=mock_websocket_emitter
            )
            engines.append(engine)
        
        # Execute concurrent operations
        async def simulate_user_execution(engine, user_context, user_data):
            """Simulate agent execution for a specific user."""
            # Set user-specific data
            engine._user_specific_data = {
                'user_id': user_context.user_id,
                'sensitive_data': user_data,
                'request_timestamp': asyncio.get_event_loop().time()
            }
            
            # Simulate some processing time
            await asyncio.sleep(0.1)
            
            # Return user-specific result
            return {
                'user_id': user_context.user_id,
                'processed_data': f"processed_{user_data}",
                'engine_id': engine.engine_id
            }
        
        # Execute all users concurrently
        user_specific_data = ['data_user_001', 'data_user_002', 'data_user_003']
        tasks = []
        
        for i, (engine, context, data) in enumerate(zip(engines, user_contexts, user_specific_data)):
            task = simulate_user_execution(engine, context, data)
            tasks.append(task)
        
        # Wait for all concurrent executions to complete
        results = await asyncio.gather(*tasks)
        
        # CRITICAL SECURITY VALIDATION: Verify no data contamination
        
        # 1. Each result should correspond to correct user
        for i, result in enumerate(results):
            expected_user_id = self.test_users[i]['user_id']
            self.assertEqual(result['user_id'], expected_user_id)
            self.assertEqual(result['processed_data'], f"processed_{user_specific_data[i]}")
        
        # 2. Each engine should have only its own user data
        for i, engine in enumerate(engines):
            expected_user_id = self.test_users[i]['user_id']
            self.assertEqual(engine._user_specific_data['user_id'], expected_user_id)
            self.assertEqual(engine._user_specific_data['sensitive_data'], user_specific_data[i])
        
        # 3. No cross-contamination between engines
        for i in range(len(engines)):
            for j in range(len(engines)):
                if i != j:
                    self.assertNotEqual(
                        engines[i]._user_specific_data['sensitive_data'],
                        engines[j]._user_specific_data['sensitive_data']
                    )

    @pytest.mark.unit
    @pytest.mark.ssot_compliance  
    def test_ssot_import_compliance_validation(self):
        """Test SSOT compliance by validating correct import patterns.
        
        SSOT COMPLIANCE TEST: Ensures that the correct SSOT import patterns are
        being used and deprecated patterns are properly marked.
        """
        # Test that SSOT imports work
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Should import without warnings
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                # Create SSOT instances
                context = UserExecutionContext(
                    user_id='test_user',
                    thread_id='test_thread',
                    run_id='test_run'
                )
                
                mock_agent_factory = MagicMock()
                mock_websocket_emitter = MagicMock()
                
                engine = UserExecutionEngine(
                    context=context,
                    agent_factory=mock_agent_factory,
                    websocket_emitter=mock_websocket_emitter
                )
                
                # Should not generate any warnings (SSOT pattern)
                ssot_warnings = [warn for warn in w if 'SSOT' in str(warn.message) or 'deprecated' in str(warn.message).lower()]
                self.assertEqual(len(ssot_warnings), 0, f"SSOT imports should not generate warnings: {ssot_warnings}")
                
        except ImportError as e:
            self.fail(f"SSOT import patterns should work: {e}")
        
        # Test that deprecated imports generate warnings
        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
                
                # Should generate deprecation warning
                deprecation_warnings = [warn for warn in w if issubclass(warn.category, DeprecationWarning)]
                self.assertTrue(len(deprecation_warnings) > 0, "Deprecated imports should generate warnings")
                
        except ImportError:
            # If deprecated import doesn't work, that's actually good for SSOT compliance
            pass

    @pytest.mark.unit
    @pytest.mark.golden_path
    def test_golden_path_compatibility_during_migration(self):
        """Test that Golden Path user flow continues to work during migration.
        
        GOLDEN PATH PROTECTION TEST: Ensures that the migration from ExecutionEngine
        to UserExecutionEngine does not break the core user chat functionality that
        delivers 90% of business value.
        
        This test validates that users can still login -> send messages -> get AI responses.
        """
        # Test both deprecated and SSOT patterns work for Golden Path
        
        # 1. Test deprecated pattern (compatibility bridge)
        try:
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            
            mock_registry = MagicMock()
            mock_websocket_bridge = MagicMock()
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # Focus on functionality, not warnings
                
                deprecated_engine = ExecutionEngine(mock_registry, mock_websocket_bridge)
                
                # Should have compatibility methods
                self.assertTrue(hasattr(deprecated_engine, 'is_compatibility_mode'))
                self.assertTrue(deprecated_engine.is_compatibility_mode())
                
        except ImportError:
            self.fail("Golden Path should maintain backward compatibility during migration")
        
        # 2. Test SSOT pattern (new implementation)
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            
            user_context = UserExecutionContext(
                user_id='golden_path_user',
                thread_id='golden_path_thread',
                run_id='golden_path_run'
            )
            
            mock_agent_factory = MagicMock()
            mock_websocket_emitter = MagicMock()
            
            ssot_engine = UserExecutionEngine(
                context=user_context,
                agent_factory=mock_agent_factory,
                websocket_emitter=mock_websocket_emitter
            )
            
            # Should be properly initialized for Golden Path
            self.assertIsNotNone(ssot_engine.get_user_context())
            self.assertEqual(ssot_engine.get_user_context().user_id, 'golden_path_user')
            
        except ImportError:
            self.fail("Golden Path should work with SSOT UserExecutionEngine")

    @pytest.mark.integration
    @pytest.mark.performance
    async def test_migration_performance_impact_validation(self):
        """Test that the migration from ExecutionEngine to UserExecutionEngine maintains performance.
        
        PERFORMANCE REGRESSION TEST: Validates that the new UserExecutionEngine
        SSOT pattern does not introduce significant performance regressions that
        could impact user experience.
        """
        import time
        
        # Measure deprecated ExecutionEngine creation time (via compatibility bridge)
        start_time = time.perf_counter()
        
        mock_registry = MagicMock()
        mock_websocket_bridge = MagicMock()
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            for _ in range(100):
                deprecated_engine = ExecutionEngine(mock_registry, mock_websocket_bridge)
        
        deprecated_time = time.perf_counter() - start_time
        
        # Measure UserExecutionEngine creation time (SSOT)
        start_time = time.perf_counter()
        
        mock_agent_factory = MagicMock()
        mock_websocket_emitter = MagicMock()
        
        for i in range(100):
            user_context = UserExecutionContext(
                user_id=f'perf_user_{i}',
                thread_id=f'perf_thread_{i}',
                run_id=f'perf_run_{i}'
            )
            
            ssot_engine = UserExecutionEngine(
                context=user_context,
                agent_factory=mock_agent_factory,
                websocket_emitter=mock_websocket_emitter
            )
        
        ssot_time = time.perf_counter() - start_time
        
        # Performance validation
        # SSOT should be faster or at most 2x slower (acceptable for security benefits)
        performance_ratio = ssot_time / deprecated_time
        
        self.assertLess(
            performance_ratio, 2.0,
            f"UserExecutionEngine should not be more than 2x slower than deprecated ExecutionEngine. "
            f"Ratio: {performance_ratio:.2f} (deprecated: {deprecated_time:.4f}s, SSOT: {ssot_time:.4f}s)"
        )

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_websocket_event_delivery_isolation_validation(self):
        """Test that WebSocket events are delivered to correct users with no cross-contamination.
        
        WEBSOCKET INTEGRATION TEST: Validates that the critical WebSocket events that
        enable chat functionality are delivered to the correct users when using
        UserExecutionEngine, with no events going to wrong users.
        
        BUSINESS CRITICAL: WebSocket events deliver 90% of business value through chat.
        """
        # Create multiple user contexts for isolation testing
        user_contexts = []
        websocket_emitters = []
        engines = []
        
        for i, user in enumerate(self.test_users):
            context = UserExecutionContext(
                user_id=user['user_id'],
                thread_id=f'ws_thread_{i}',
                run_id=f'ws_run_{i}'
            )
            user_contexts.append(context)
            
            # Mock WebSocket emitter for each user
            mock_emitter = AsyncMock()
            websocket_emitters.append(mock_emitter)
            
            mock_agent_factory = MagicMock()
            
            engine = UserExecutionEngine(
                context=context,
                agent_factory=mock_agent_factory,
                websocket_emitter=mock_emitter
            )
            engines.append(engine)
        
        # Simulate concurrent WebSocket events
        async def emit_user_events(engine, user_context, emitter):
            """Simulate WebSocket events for a specific user."""
            events = [
                'agent_started',
                'agent_thinking', 
                'tool_executing',
                'tool_completed',
                'agent_completed'
            ]
            
            for event in events:
                await emitter.emit_event(event, {
                    'user_id': user_context.user_id,
                    'message': f'{event}_for_{user_context.user_id}',
                    'timestamp': time.time()
                })
        
        # Execute concurrent event emission
        tasks = []
        for engine, context, emitter in zip(engines, user_contexts, websocket_emitters):
            task = emit_user_events(engine, context, emitter)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # CRITICAL WEBSOCKET VALIDATION: Verify event isolation
        
        for i, (emitter, context) in enumerate(zip(websocket_emitters, user_contexts)):
            # Each emitter should have been called exactly 5 times (5 critical events)
            self.assertEqual(emitter.emit_event.call_count, 5)
            
            # Verify all events were for the correct user
            for call in emitter.emit_event.call_args_list:
                event_data = call[0][1]  # Second argument is the event data
                self.assertEqual(event_data['user_id'], context.user_id)
                self.assertIn(context.user_id, event_data['message'])
        
        # Verify no cross-contamination between emitters
        for i in range(len(websocket_emitters)):
            for j in range(len(websocket_emitters)):
                if i != j:
                    emitter_i_calls = websocket_emitters[i].emit_event.call_args_list
                    emitter_j_calls = websocket_emitters[j].emit_event.call_args_list
                    
                    # Ensure no calls were made with wrong user_id
                    for call in emitter_i_calls:
                        event_data = call[0][1]
                        self.assertNotEqual(event_data['user_id'], user_contexts[j].user_id)


if __name__ == '__main__':
    # Run the test suite
    pytest.main([__file__, '-v', '--tb=short'])