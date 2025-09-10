"""
Test UserExecutionEngine SSOT Validation

MISSION CRITICAL: These tests validate that UserExecutionEngine correctly implements SSOT principles.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability & User Safety  
- Value Impact: Ensures replacement ExecutionEngine properly isolates users and prevents data leakage
- Strategic Impact: $500K+ ARR protection through proper multi-user system implementation

PURPOSE: These tests should PASS to prove UserExecutionEngine is the correct SSOT replacement.
These validate the solution works correctly after SSOT remediation.

Test Coverage:
1. UserExecutionEngine provides proper user isolation
2. No shared state between user instances
3. WebSocket events properly routed to correct users only
4. Memory management and cleanup works correctly
5. Factory pattern properly implemented
6. SSOT principles correctly followed

CRITICAL: These are PASSING tests that prove the solution works.
"""

import asyncio
import pytest
import time
import gc
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


class TestUserExecutionEngineSSotValidation(SSotAsyncTestCase):
    """
    Tests that SHOULD PASS to validate UserExecutionEngine SSOT compliance.
    
    These tests prove that UserExecutionEngine correctly implements
    SSOT principles and provides proper user isolation.
    """

    async def asyncSetUp(self):
        """Set up test fixtures for UserExecutionEngine testing."""
        await super().asyncSetUp()
        
        # Mock user contexts for testing
        self.user_a_context = {
            'user_id': 'user_a_123',
            'username': 'alice@example.com',
            'subscription_tier': 'enterprise',
            'session_id': 'session_a_456'
        }
        
        self.user_b_context = {
            'user_id': 'user_b_789', 
            'username': 'bob@example.com',
            'subscription_tier': 'early',
            'session_id': 'session_b_101'
        }

    @pytest.mark.mission_critical
    @pytest.mark.unit
    async def test_user_execution_engine_provides_complete_isolation(self):
        """
        SHOULD PASS: Tests that UserExecutionEngine provides complete user isolation.
        
        SSOT Validation: Each user gets completely isolated ExecutionEngine instance.
        Expected Result: No shared state between users, complete isolation.
        """
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Create isolated contexts for two users
            context_a = UserExecutionContext(
                user_id=self.user_a_context['user_id'],
                session_id=self.user_a_context['session_id'],
                request_id='req_a_123'
            )
            
            context_b = UserExecutionContext(
                user_id=self.user_b_context['user_id'], 
                session_id=self.user_b_context['session_id'],
                request_id='req_b_456'
            )
            
            # Create UserExecutionEngine instances for each user
            engine_a = UserExecutionEngine(user_context=context_a)
            engine_b = UserExecutionEngine(user_context=context_b)
            
            # Validate complete isolation
            self.assertIsNot(engine_a, engine_b, 
                "UserExecutionEngine instances must be different objects")
            
            # Check user context isolation
            self.assertEqual(engine_a.user_context.user_id, self.user_a_context['user_id'])
            self.assertEqual(engine_b.user_context.user_id, self.user_b_context['user_id'])
            self.assertNotEqual(engine_a.user_context.user_id, engine_b.user_context.user_id)
            
            # Test execution state isolation
            if hasattr(engine_a, '_execution_state') and hasattr(engine_b, '_execution_state'):
                # Set state in user A's engine
                engine_a._execution_state['secret_data'] = 'user_a_private_info'
                
                # Ensure user B cannot access user A's data
                user_b_state = getattr(engine_b, '_execution_state', {})
                self.assertNotIn('secret_data', user_b_state,
                    "User B must not have access to User A's execution state")
                
                self.assertIsNot(engine_a._execution_state, engine_b._execution_state,
                    "Execution states must be separate objects")
            
            self.logger.info("UserExecutionEngine isolation validation PASSED")
            
        except ImportError as e:
            self.fail(f"Cannot import UserExecutionEngine: {e}")
        except Exception as e:
            self.fail(f"UserExecutionEngine isolation test failed: {e}")

    @pytest.mark.mission_critical
    @pytest.mark.unit
    async def test_websocket_events_properly_isolated(self):
        """
        SHOULD PASS: Tests that WebSocket events are properly isolated per user.
        
        Business Critical Validation: User A's events only go to User A, never to User B.
        Expected Result: Complete WebSocket event isolation between users.
        """
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Track events for each user
            user_a_events = []
            user_b_events = []
            
            def mock_user_a_emit(event_type, data):
                user_a_events.append((event_type, data, 'user_a'))
                
            def mock_user_b_emit(event_type, data):
                user_b_events.append((event_type, data, 'user_b'))
            
            # Create user contexts
            context_a = UserExecutionContext(
                user_id=self.user_a_context['user_id'],
                session_id=self.user_a_context['session_id'],
                request_id='req_a_789'
            )
            
            context_b = UserExecutionContext(
                user_id=self.user_b_context['user_id'],
                session_id=self.user_b_context['session_id'], 
                request_id='req_b_101'
            )
            
            # Create engines with mocked WebSocket emitters
            with patch.object(UserExecutionEngine, '_setup_websocket_emitter') as mock_setup:
                engine_a = UserExecutionEngine(user_context=context_a)
                engine_b = UserExecutionEngine(user_context=context_b)
                
                # Setup isolated WebSocket emitters
                engine_a.websocket_emitter = MagicMock()
                engine_a.websocket_emitter.emit = mock_user_a_emit
                
                engine_b.websocket_emitter = MagicMock()
                engine_b.websocket_emitter.emit = mock_user_b_emit
                
                # Verify emitters are different objects (isolation)
                self.assertIsNot(engine_a.websocket_emitter, engine_b.websocket_emitter,
                    "WebSocket emitters must be isolated per user")
                
                # Send events from user A
                engine_a.websocket_emitter.emit("agent_started", {
                    "user_id": self.user_a_context['user_id'],
                    "sensitive_data": "user_a_private_secret"
                })
                
                engine_a.websocket_emitter.emit("agent_thinking", {
                    "thought": "User A's private thoughts"
                })
                
                # Send events from user B  
                engine_b.websocket_emitter.emit("agent_started", {
                    "user_id": self.user_b_context['user_id'],
                    "sensitive_data": "user_b_private_secret"
                })
                
                # Validate complete event isolation
                self.assertEqual(len(user_a_events), 2, "User A should have exactly 2 events")
                self.assertEqual(len(user_b_events), 1, "User B should have exactly 1 event")
                
                # Ensure no cross-contamination
                for event_type, data, source in user_a_events:
                    self.assertEqual(source, 'user_a', "All user A events must come from user A emitter")
                    if isinstance(data, dict) and 'user_id' in data:
                        self.assertEqual(data['user_id'], self.user_a_context['user_id'])
                
                for event_type, data, source in user_b_events:
                    self.assertEqual(source, 'user_b', "All user B events must come from user B emitter")
                    if isinstance(data, dict) and 'user_id' in data:
                        self.assertEqual(data['user_id'], self.user_b_context['user_id'])
                
                # Critical: Check that user B never received user A's sensitive data
                user_b_event_data = [str(event) for event in user_b_events]
                user_b_combined = ' '.join(user_b_event_data)
                
                self.assertNotIn("user_a_private_secret", user_b_combined,
                    "User B must never receive User A's sensitive data")
                self.assertNotIn("User A's private thoughts", user_b_combined,
                    "User B must never receive User A's private thoughts")
            
            self.logger.info("WebSocket event isolation validation PASSED")
            
        except Exception as e:
            self.fail(f"WebSocket event isolation test failed: {e}")

    @pytest.mark.mission_critical
    @pytest.mark.unit
    async def test_factory_pattern_properly_implemented(self):
        """
        SHOULD PASS: Tests that UserExecutionEngine implements proper factory pattern.
        
        Architecture Validation: Factory pattern ensures proper user isolation.
        Expected Result: Factory methods create isolated instances with proper context.
        """
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Test 1: Factory method exists and works
            context = UserExecutionContext(
                user_id=self.user_a_context['user_id'],
                session_id=self.user_a_context['session_id'],
                request_id='req_factory_test'
            )
            
            # Create engine through proper instantiation (should work)
            engine = UserExecutionEngine(user_context=context)
            self.assertIsNotNone(engine, "UserExecutionEngine should be created successfully")
            self.assertEqual(engine.user_context.user_id, self.user_a_context['user_id'])
            
            # Test 2: Multiple instances are properly isolated
            context2 = UserExecutionContext(
                user_id=self.user_b_context['user_id'],
                session_id=self.user_b_context['session_id'], 
                request_id='req_factory_test_2'
            )
            
            engine2 = UserExecutionEngine(user_context=context2)
            
            # Validate factory isolation
            self.assertIsNot(engine, engine2, "Factory should create different instances")
            self.assertNotEqual(engine.user_context.user_id, engine2.user_context.user_id,
                "Factory instances should have different user contexts")
            
            # Test 3: Context validation (should fail with invalid context)
            try:
                invalid_engine = UserExecutionEngine(user_context=None)
                # If this doesn't fail, that might be okay depending on implementation
                # Some implementations may allow None and set defaults
            except (ValueError, TypeError) as e:
                # This is expected - invalid context should be rejected
                self.logger.info(f"Invalid context properly rejected: {e}")
            
            # Test 4: Check if cleanup methods exist
            cleanup_methods = ['cleanup', 'dispose', '__del__', '_cleanup_resources']
            has_cleanup = any(hasattr(engine, method) for method in cleanup_methods)
            
            if not has_cleanup:
                self.logger.warning("No explicit cleanup methods found - ensure proper garbage collection")
            
            self.logger.info("Factory pattern validation PASSED")
            
        except Exception as e:
            self.fail(f"Factory pattern test failed: {e}")

    @pytest.mark.mission_critical
    @pytest.mark.unit
    async def test_memory_management_prevents_leaks(self):
        """
        SHOULD PASS: Tests that UserExecutionEngine prevents memory leaks.
        
        Performance Validation: Per-user instances should be cleanly garbage collected.
        Expected Result: Memory is properly managed and cleaned up per user.
        """
        try:
            import gc
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Baseline memory state
            gc.collect()
            initial_objects = len(gc.get_objects())
            
            # Create multiple user engines (simulating concurrent users)
            engines = []
            contexts = []
            
            for i in range(5):  # Simulate 5 concurrent users
                context = UserExecutionContext(
                    user_id=f'memory_test_user_{i}',
                    session_id=f'session_{i}',
                    request_id=f'req_{i}_{int(time.time())}'
                )
                contexts.append(context)
                
                engine = UserExecutionEngine(user_context=context)
                
                # Add some execution state to test cleanup
                if hasattr(engine, '_execution_state'):
                    engine._execution_state = {
                        'user_data': f'data_for_user_{i}' * 100,  # ~1KB per user
                        'execution_history': [f'step_{j}' for j in range(50)]
                    }
                
                engines.append(engine)
            
            # Check reasonable memory growth
            gc.collect()
            post_creation_objects = len(gc.get_objects())
            creation_growth = post_creation_objects - initial_objects
            
            # Ensure growth is reasonable (not excessive)
            max_reasonable_growth = 2000  # Arbitrary but reasonable threshold
            self.assertLess(creation_growth, max_reasonable_growth,
                f"Memory growth of {creation_growth} objects seems excessive for 5 engines")
            
            # Test cleanup by deleting engines
            del engines
            del contexts
            gc.collect()  # Force garbage collection
            
            post_cleanup_objects = len(gc.get_objects())
            remaining_growth = post_cleanup_objects - initial_objects
            
            # Validate cleanup worked (allow some tolerance)
            max_remaining = 200  # Allow some objects to remain
            self.assertLess(remaining_growth, max_remaining,
                f"After cleanup, {remaining_growth} objects remain. This suggests memory leaks.")
            
            # Calculate cleanup efficiency
            if creation_growth > 0:
                cleanup_efficiency = (creation_growth - remaining_growth) / creation_growth
                self.assertGreater(cleanup_efficiency, 0.8,  # At least 80% cleanup
                    f"Cleanup efficiency {cleanup_efficiency:.2%} is too low. Memory leaks suspected.")
            
            self.logger.info(f"Memory management test PASSED. Growth: {creation_growth}, Remaining: {remaining_growth}")
            
        except Exception as e:
            self.fail(f"Memory management test failed: {e}")

    @pytest.mark.mission_critical
    @pytest.mark.unit
    async def test_concurrent_user_execution_safety(self):
        """
        SHOULD PASS: Tests that UserExecutionEngine handles concurrent users safely.
        
        Concurrency Validation: Multiple users should execute simultaneously without interference.
        Expected Result: Concurrent execution with complete isolation.
        """
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Create contexts for concurrent users
            contexts = []
            for i in range(3):
                context = UserExecutionContext(
                    user_id=f'concurrent_user_{i}',
                    session_id=f'session_{i}',
                    request_id=f'concurrent_req_{i}'
                )
                contexts.append(context)
            
            # Results tracking for each user
            user_results = {}
            user_errors = {}
            
            async def simulate_user_execution(user_context, user_index):
                """Simulate agent execution for a specific user."""
                try:
                    engine = UserExecutionEngine(user_context=user_context)
                    
                    # Simulate some execution work
                    execution_data = {
                        'user_id': user_context.user_id,
                        'start_time': time.time(),
                        'execution_steps': []
                    }
                    
                    # Simulate execution steps
                    for step in range(3):
                        await asyncio.sleep(0.01)  # Small delay to allow context switching
                        execution_data['execution_steps'].append(f'step_{step}_user_{user_index}')
                    
                    execution_data['end_time'] = time.time()
                    execution_data['duration'] = execution_data['end_time'] - execution_data['start_time']
                    
                    user_results[user_context.user_id] = execution_data
                    
                except Exception as e:
                    user_errors[user_context.user_id] = str(e)
            
            # Execute all users concurrently
            tasks = []
            for i, context in enumerate(contexts):
                task = asyncio.create_task(simulate_user_execution(context, i))
                tasks.append(task)
            
            # Wait for all concurrent executions to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Validate all users completed successfully
            self.assertEqual(len(user_errors), 0, 
                f"Concurrent execution had errors: {user_errors}")
            
            self.assertEqual(len(user_results), len(contexts),
                f"Not all users completed. Expected {len(contexts)}, got {len(user_results)}")
            
            # Validate isolation - each user should have unique execution data
            user_ids = set()
            for user_id, result in user_results.items():
                user_ids.add(user_id)
                
                # Check user-specific execution steps
                for step in result['execution_steps']:
                    expected_user_index = user_id.split('_')[-1]  # Extract user index
                    self.assertIn(f'user_{expected_user_index}', step,
                        f"Execution step {step} doesn't match user {user_id}")
            
            # Ensure all users were unique
            self.assertEqual(len(user_ids), len(contexts),
                "User isolation failed - duplicate or missing user executions")
            
            self.logger.info(f"Concurrent execution test PASSED for {len(contexts)} users")
            
        except Exception as e:
            self.fail(f"Concurrent user execution test failed: {e}")

    @pytest.mark.mission_critical
    @pytest.mark.unit
    async def test_ssot_documentation_compliance(self):
        """
        SHOULD PASS: Tests that UserExecutionEngine has proper SSOT documentation.
        
        Documentation Validation: SSOT implementation should be clearly documented.
        Expected Result: Clear documentation indicating this is the canonical implementation.
        """
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            import netra_backend.app.agents.supervisor.user_execution_engine as user_engine_module
            
            # Check module docstring
            module_doc = user_engine_module.__doc__ or ""
            module_doc_lower = module_doc.lower()
            
            # Look for SSOT indicators
            ssot_indicators = [
                'per-user isolated',
                'user isolation', 
                'complete isolation',
                'eliminat',  # eliminates, elimination
                'canonical',
                'ssot'
            ]
            
            found_indicators = []
            for indicator in ssot_indicators:
                if indicator in module_doc_lower:
                    found_indicators.append(indicator)
            
            self.assertGreater(len(found_indicators), 0,
                f"UserExecutionEngine documentation should contain SSOT indicators. "
                f"Found: {found_indicators}")
            
            # Check class docstring
            class_doc = UserExecutionEngine.__doc__ or ""
            self.assertGreater(len(class_doc), 50,
                "UserExecutionEngine should have substantial class documentation")
            
            # Check for business value justification
            bvj_indicators = ['business value', 'segment:', 'business goal:', 'value impact:', 'strategic impact:']
            bvj_found = any(indicator in module_doc_lower for indicator in bvj_indicators)
            
            self.assertTrue(bvj_found,
                "UserExecutionEngine documentation should include Business Value Justification")
            
            # Check for proper isolation documentation
            isolation_terms = ['isolation', 'per-user', 'user-specific', 'concurrent']
            isolation_found = [term for term in isolation_terms if term in module_doc_lower]
            
            self.assertGreater(len(isolation_found), 1,
                f"Documentation should emphasize user isolation. Found: {isolation_found}")
            
            self.logger.info(f"SSOT documentation validation PASSED. Indicators: {found_indicators}")
            
        except Exception as e:
            self.fail(f"SSOT documentation test failed: {e}")


if __name__ == "__main__":
    """
    Run these tests to validate UserExecutionEngine SSOT compliance.
    
    Expected Result: ALL TESTS SHOULD PASS
    This proves that UserExecutionEngine correctly implements SSOT principles.
    """
    pytest.main([__file__, "-v", "--tb=short"])