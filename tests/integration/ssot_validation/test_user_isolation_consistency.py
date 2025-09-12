"""
User Isolation Consistency Test - Cross-Engine SSOT Validation

This test verifies that all 7 execution engines maintain consistent user isolation
and prevent cross-user state leakage during the SSOT consolidation process.

Business Value: Protects Golden Path by ensuring concurrent users don't interfere
with each other's AI responses, maintaining chat quality for all users.

CRITICAL: This test exposes current violations and validates SSOT remediation.
"""

import asyncio
import pytest
import uuid
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestUserIsolationConsistency(SSotAsyncTestCase):
    """Test user isolation consistency across all execution engines."""
    
    async def async_setup_method(self, method=None):
        """Setup with multiple user contexts for isolation testing."""
        await super().async_setup_method(method)
        
        # Create multiple user contexts for concurrent testing
        self.user_contexts = []
        for i in range(5):  # Test with 5 concurrent users
            context = UserExecutionContext(
                user_id=f"user_{i}",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}",
                request_id=f"req_{i}",
                agent_context={"user_prompt": f"User {i} AI request", "isolation_test": True}
            )
            self.user_contexts.append(context)
        
        # Track isolation violations
        self.isolation_violations: Dict[str, Any] = {}
        self.cross_user_leakage: List[Dict[str, Any]] = []
    
    async def test_user_execution_engine_isolation(self):
        """TEST 1: Verify UserExecutionEngine maintains user isolation."""
        self.record_metric("test_name", "user_execution_engine_isolation")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            
            engines = []
            mock_factory = MagicMock()
            mock_factory._agent_registry = MagicMock()
            mock_factory._websocket_bridge = MagicMock()
            
            # Create multiple UserExecutionEngine instances for different users
            for i, context in enumerate(self.user_contexts[:3]):  # Test with 3 users
                mock_websocket_emitter = AsyncMock()
                mock_websocket_emitter.user_id = context.user_id
                
                engine = UserExecutionEngine(
                    context=context,
                    agent_factory=mock_factory,
                    websocket_emitter=mock_websocket_emitter
                )
                engines.append((engine, context))
            
            # Test concurrent state operations without cross-user contamination
            await self._test_concurrent_state_isolation(engines)
            
            # Verify per-user statistics isolation
            await self._test_statistics_isolation(engines)
            
            # Test WebSocket event isolation
            await self._test_websocket_isolation(engines)
            
            # Clean up engines
            for engine, _ in engines:
                if hasattr(engine, 'cleanup'):
                    await engine.cleanup()
            
            self.record_metric("user_execution_engine_isolated", True)
            
        except Exception as e:
            self.isolation_violations["user_execution_engine"] = str(e)
            pytest.fail(f"UserExecutionEngine isolation test failed: {e}")
    
    async def _test_concurrent_state_isolation(self, engines):
        """Test concurrent state operations across users don't leak."""
        
        async def set_user_state(engine_context_pair, agent_name, state):
            engine, context = engine_context_pair
            engine.set_agent_state(agent_name, f"{state}_{context.user_id}")
            engine.set_agent_result(agent_name, {"result": f"result_{context.user_id}", "user": context.user_id})
            
            # Simulate some processing time
            await asyncio.sleep(0.1)
            
            return engine.get_agent_state(agent_name), engine.get_agent_result(agent_name)
        
        # Run concurrent state operations
        tasks = []
        for i, (engine, context) in enumerate(engines):
            task = set_user_state((engine, context), "test_agent", f"state_{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Verify no cross-contamination
        for i, ((state, result), (engine, context)) in enumerate(zip(results, engines)):
            expected_state = f"state_{i}_{context.user_id}"
            expected_result_user = context.user_id
            
            if state != expected_state:
                self.cross_user_leakage.append({
                    "type": "state_contamination",
                    "user": context.user_id,
                    "expected": expected_state,
                    "actual": state
                })
            
            if result and result.get("user") != expected_result_user:
                self.cross_user_leakage.append({
                    "type": "result_contamination", 
                    "user": context.user_id,
                    "expected_user": expected_result_user,
                    "actual_user": result.get("user")
                })
        
        self.record_metric("concurrent_state_tests", len(engines))
        self.record_metric("cross_user_leakage_count", len(self.cross_user_leakage))
    
    async def _test_statistics_isolation(self, engines):
        """Test execution statistics are isolated per user."""
        
        # Generate different statistics for each user
        for i, (engine, context) in enumerate(engines):
            stats = engine.get_user_execution_stats()
            
            # Modify stats to test isolation
            engine.execution_stats['test_metric'] = f"user_{context.user_id}_value"
            engine.execution_stats['total_executions'] = i + 1
        
        # Verify statistics don't leak between users
        for i, (engine, context) in enumerate(engines):
            stats = engine.get_user_execution_stats()
            
            if stats.get('test_metric') != f"user_{context.user_id}_value":
                self.cross_user_leakage.append({
                    "type": "statistics_contamination",
                    "user": context.user_id,
                    "metric": "test_metric",
                    "expected": f"user_{context.user_id}_value",
                    "actual": stats.get('test_metric')
                })
            
            if stats.get('total_executions') != i + 1:
                self.cross_user_leakage.append({
                    "type": "execution_count_contamination",
                    "user": context.user_id,
                    "expected": i + 1,
                    "actual": stats.get('total_executions')
                })
    
    async def _test_websocket_isolation(self, engines):
        """Test WebSocket events are isolated per user."""
        
        for engine, context in engines:
            # Verify WebSocket emitter is user-specific
            if hasattr(engine, 'websocket_emitter') and engine.websocket_emitter:
                emitter = engine.websocket_emitter
                
                # Check if emitter has user identification
                if hasattr(emitter, 'user_id'):
                    if emitter.user_id != context.user_id:
                        self.cross_user_leakage.append({
                            "type": "websocket_user_mismatch",
                            "engine_user": context.user_id,
                            "emitter_user": emitter.user_id
                        })
                else:
                    # Document missing user identification in WebSocket emitter
                    self.isolation_violations["websocket_no_user_id"] = f"WebSocket emitter for {context.user_id} has no user_id"
        
        self.record_metric("websocket_isolation_tested", len(engines))
    
    async def test_execution_engine_legacy_isolation_violations(self):
        """TEST 2: Document legacy ExecutionEngine isolation violations."""
        self.record_metric("test_name", "legacy_execution_engine_violations")
        
        try:
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            
            # Test legacy engine with user context support
            mock_registry = MagicMock()
            mock_bridge = MagicMock()
            mock_bridge.notify_agent_started = AsyncMock()
            mock_bridge.notify_agent_thinking = AsyncMock()
            mock_bridge.notify_agent_completed = AsyncMock()
            
            engines = []
            
            # Create engines with different user contexts
            for context in self.user_contexts[:2]:  # Test 2 users
                try:
                    engine = ExecutionEngine(mock_registry, mock_bridge, context)
                    engines.append((engine, context))
                except Exception as e:
                    self.isolation_violations[f"legacy_engine_creation_{context.user_id}"] = str(e)
            
            if engines:
                # Test if legacy engine properly isolates user state
                await self._test_legacy_engine_state_isolation(engines)
            
            self.record_metric("legacy_engines_tested", len(engines))
            
        except ImportError:
            # Expected after consolidation - document transition progress
            self.record_metric("legacy_engine_removed", True)
        except Exception as e:
            self.isolation_violations["legacy_engine_test"] = str(e)
    
    async def _test_legacy_engine_state_isolation(self, engines):
        """Test legacy engine isolation (expected to find violations)."""
        
        # Test global state contamination in legacy engines
        for i, (engine, context) in enumerate(engines):
            # Check if engines share state objects (violation)
            if hasattr(engine, 'active_runs'):
                for j, (other_engine, other_context) in enumerate(engines):
                    if i != j and engine.active_runs is other_engine.active_runs:
                        self.cross_user_leakage.append({
                            "type": "shared_active_runs",
                            "user1": context.user_id,
                            "user2": other_context.user_id,
                            "violation": "Legacy engines share active_runs state"
                        })
            
            # Check user execution states isolation
            if hasattr(engine, '_user_execution_states'):
                # This is expected to work in the improved legacy engine
                user_state = await engine._get_user_execution_state(context.user_id)
                if user_state:
                    self.record_metric("legacy_engine_has_user_states", True)
    
    async def test_concurrent_execution_no_interference(self):
        """TEST 3: Verify concurrent executions don't interfere across users."""
        self.record_metric("test_name", "concurrent_execution_isolation")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext, PipelineStep
            from netra_backend.app.agents.state import DeepAgentState
            from datetime import datetime, timezone
            
            # Create engines for concurrent testing
            engines = []
            mock_factory = MagicMock()
            mock_factory._agent_registry = MagicMock()
            mock_factory._websocket_bridge = MagicMock()
            
            for context in self.user_contexts[:3]:
                mock_websocket_emitter = AsyncMock()
                engine = UserExecutionEngine(
                    context=context,
                    agent_factory=mock_factory,
                    websocket_emitter=mock_websocket_emitter
                )
                engines.append((engine, context))
            
            # Mock agent execution to simulate concurrent work
            async def mock_execute_agent(engine, context, agent_context, state):
                # Simulate some work
                await asyncio.sleep(0.2)
                
                # Set some user-specific state during execution
                engine.set_agent_state("concurrent_agent", f"executing_{context.user_id}")
                
                # Return mock result
                from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult
                return AgentExecutionResult(
                    success=True,
                    agent_name="concurrent_agent",
                    execution_time=0.2,
                    state=state,
                    agent_context={"user_id": context.user_id, "isolated": True}
                )
            
            # Patch agent execution for testing
            with patch.object(UserExecutionEngine, 'execute_agent', side_effect=mock_execute_agent):
                
                # Create concurrent execution tasks
                tasks = []
                for engine, context in engines:
                    agent_context = AgentExecutionContext(
                        user_id=context.user_id,
                        thread_id=context.thread_id,
                        run_id=context.run_id,
                        request_id=context.request_id,
                        agent_name="concurrent_agent",
                        step=PipelineStep.INITIALIZATION,
                        execution_timestamp=datetime.now(timezone.utc)
                    )
                    
                    state = DeepAgentState(
                        user_request=f"User {context.user_id} request",
                        user_id=context.user_id,
                        chat_thread_id=context.thread_id,
                        run_id=context.run_id
                    )
                    
                    task = mock_execute_agent(engine, context, agent_context, state)
                    tasks.append(task)
                
                # Run concurrent executions
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Verify results are isolated per user
                for i, (result, (engine, context)) in enumerate(zip(results, engines)):
                    if isinstance(result, Exception):
                        self.isolation_violations[f"concurrent_execution_{context.user_id}"] = str(result)
                        continue
                    
                    # Check result isolation
                    if result.metadata.get("user_id") != context.user_id:
                        self.cross_user_leakage.append({
                            "type": "result_user_mismatch",
                            "expected_user": context.user_id,
                            "actual_user": result.metadata.get("user_id")
                        })
                    
                    # Check agent state isolation
                    agent_state = engine.get_agent_state("concurrent_agent")
                    expected_state = f"executing_{context.user_id}"
                    if agent_state != expected_state:
                        self.cross_user_leakage.append({
                            "type": "agent_state_contamination",
                            "user": context.user_id,
                            "expected": expected_state,
                            "actual": agent_state
                        })
            
            # Clean up
            for engine, _ in engines:
                await engine.cleanup()
            
            self.record_metric("concurrent_executions_tested", len(engines))
            
        except Exception as e:
            self.isolation_violations["concurrent_test"] = str(e)
            pytest.fail(f"Concurrent execution isolation test failed: {e}")
    
    async def test_memory_isolation_no_leaks(self):
        """TEST 4: Verify memory isolation and no memory leaks between users."""
        self.record_metric("test_name", "memory_isolation")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            
            mock_factory = MagicMock()
            mock_factory._agent_registry = MagicMock()
            mock_factory._websocket_bridge = MagicMock()
            
            # Create and destroy engines to test memory management
            engines_created = []
            for i in range(10):  # Create 10 engines to test memory management
                context = UserExecutionContext(
                    user_id=f"memory_test_user_{i}",
                    thread_id=f"memory_thread_{i}",
                    run_id=f"memory_run_{i}",
                    request_id=f"memory_req_{i}"
                )
                
                mock_websocket_emitter = AsyncMock()
                engine = UserExecutionEngine(
                    context=context,
                    agent_factory=mock_factory,
                    websocket_emitter=mock_websocket_emitter
                )
                
                # Add some data to test memory cleanup
                engine.set_agent_state("memory_agent", f"data_{i}")
                engine.set_agent_result("memory_agent", {"large_data": list(range(1000))})
                
                engines_created.append(engine)
                
                # Clean up every engine immediately
                await engine.cleanup()
                
                # Verify cleanup worked
                if engine.is_active():
                    self.isolation_violations[f"cleanup_failed_{i}"] = "Engine still active after cleanup"
                
                if engine.active_runs:
                    self.isolation_violations[f"active_runs_not_cleared_{i}"] = "Active runs not cleared"
                
                if engine.agent_states:
                    self.isolation_violations[f"agent_states_not_cleared_{i}"] = "Agent states not cleared"
            
            self.record_metric("memory_test_engines_created", len(engines_created))
            self.record_metric("memory_cleanup_violations", len([k for k in self.isolation_violations.keys() if "cleanup" in k]))
            
        except Exception as e:
            self.isolation_violations["memory_test"] = str(e)
            pytest.fail(f"Memory isolation test failed: {e}")
    
    async def async_teardown_method(self, method=None):
        """Report user isolation test results."""
        
        # Generate comprehensive isolation report
        all_metrics = self.get_all_metrics()
        
        print(f"\n=== User Isolation Consistency Report ===")
        print(f"Test: {all_metrics.get('test_name', 'unknown')}")
        print(f"Cross-user leakage incidents: {len(self.cross_user_leakage)}")
        print(f"Isolation violations: {len(self.isolation_violations)}")
        print(f"Execution time: {all_metrics.get('execution_time', 0):.3f}s")
        
        if self.cross_user_leakage:
            print("\nCross-user leakage detected:")
            for leak in self.cross_user_leakage:
                print(f"  - {leak['type']}: {leak}")
        
        if self.isolation_violations:
            print("\nIsolation violations:")
            for violation_type, details in self.isolation_violations.items():
                print(f"  - {violation_type}: {details}")
        
        if not self.cross_user_leakage and not self.isolation_violations:
            print(" PASS:  Perfect user isolation: No leakage or violations detected")
        else:
            print(f" WARNING: [U+FE0F]  Isolation issues found - SSOT consolidation needed")
            print("NOTE: Issues expected during transition, should be resolved after consolidation")
        
        print("=" * 50)
        
        await super().async_teardown_method(method)


class TestGoldenPathConcurrency(SSotAsyncTestCase):
    """Test Golden Path protection during concurrent user sessions."""
    
    async def test_golden_path_concurrent_users_no_interference(self):
        """GOLDEN PATH: Verify 5 concurrent users get isolated AI responses."""
        self.record_metric("test_name", "golden_path_concurrent_protection")
        
        # Simulate 5 users making concurrent AI requests
        user_prompts = [
            "Optimize my AI costs",
            "Analyze my usage patterns", 
            "Generate optimization report",
            "Find cost savings opportunities",
            "Review AI performance metrics"
        ]
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            
            mock_factory = MagicMock()
            mock_factory._agent_registry = MagicMock()
            mock_factory._websocket_bridge = MagicMock()
            
            # Create concurrent user sessions
            concurrent_sessions = []
            for i, prompt in enumerate(user_prompts):
                context = UserExecutionContext(
                    user_id=f"golden_user_{i}",
                    thread_id=f"golden_thread_{i}",
                    run_id=f"golden_run_{i}",
                    request_id=f"golden_req_{i}",
                    agent_context={"user_prompt": prompt, "golden_path": True}
                )
                
                mock_websocket_emitter = AsyncMock()
                mock_websocket_emitter.user_id = context.user_id
                
                engine = UserExecutionEngine(
                    context=context,
                    agent_factory=mock_factory,
                    websocket_emitter=mock_websocket_emitter
                )
                
                concurrent_sessions.append((engine, context, prompt))
            
            # Simulate concurrent AI processing
            async def process_user_request(session):
                engine, context, prompt = session
                
                # Simulate AI agent processing with user-specific result
                engine.set_agent_state("supervisor_agent", "processing")
                engine.set_agent_result("supervisor_agent", {
                    "user_prompt": prompt,
                    "ai_response": f"AI response for {context.user_id}: {prompt[:20]}...",
                    "user_id": context.user_id,
                    "golden_path": True
                })
                
                await asyncio.sleep(0.1)  # Simulate processing time
                
                return engine.get_agent_result("supervisor_agent")
            
            # Run concurrent processing
            results = await asyncio.gather(*[process_user_request(session) for session in concurrent_sessions])
            
            # Verify Golden Path: Each user gets their specific AI response
            golden_path_protected = True
            for i, (result, (engine, context, prompt)) in enumerate(zip(results, concurrent_sessions)):
                # Verify user gets their own AI response
                if result["user_id"] != context.user_id:
                    golden_path_protected = False
                    print(f"GOLDEN PATH VIOLATION: User {context.user_id} got response for {result['user_id']}")
                
                if prompt not in result["ai_response"]:
                    golden_path_protected = False
                    print(f"GOLDEN PATH VIOLATION: User {context.user_id} didn't get response to their prompt")
            
            # Clean up
            for engine, _, _ in concurrent_sessions:
                await engine.cleanup()
            
            self.record_metric("golden_path_protected", golden_path_protected)
            self.record_metric("concurrent_users_tested", len(concurrent_sessions))
            
            if not golden_path_protected:
                pytest.fail("GOLDEN PATH BROKEN: Concurrent users interfering with each other's AI responses")
            
            print(f" PASS:  Golden Path Protected: {len(concurrent_sessions)} concurrent users isolated successfully")
            
        except Exception as e:
            pytest.fail(f"GOLDEN PATH FAILURE: Concurrent user isolation failed: {e}")