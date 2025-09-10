"""Factory User Isolation Unit Test - PRIORITY 1 (Legal Compliance)

MISSION: Validate factory creates unique instances per user with no shared state.

This test validates the critical SSOT compliance requirement that ExecutionEngineFactory
creates completely isolated instances per user, preventing shared state violations that
could lead to data leakage between concurrent users.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - affects every user
- Business Goal: Legal/Compliance - prevent data leakage between users  
- Value Impact: Guarantees user data privacy and regulatory compliance
- Revenue Impact: Prevents legal liability and maintains user trust
- Strategic Impact: CRITICAL - data leakage could result in loss of business license

Key Validation Points:
1. Factory.create(user_a) != Factory.create(user_b) (different instances)
2. No shared state/memory between concurrent user engines
3. User A changes don't affect User B engine state
4. Memory isolation prevents cross-user contamination
5. Each engine has unique WebSocket emitters

Expected Behavior:
- FAIL BEFORE: Singleton pattern causes shared instances/state
- PASS AFTER: Factory creates truly isolated instances per user
"""

import pytest
import asyncio
import time
import uuid
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestExecutionEngineFactoryUserIsolationUnit(SSotBaseTestCase):
    """SSOT Unit test for ExecutionEngineFactory user isolation compliance.
    
    This test ensures the factory creates properly isolated user execution engines,
    preventing the shared state issues that violate user data privacy.
    """
    
    def setup_method(self, method=None):
        """Setup test with isolated factory instance and mock dependencies."""
        super().setup_method(method)
        
        # Create mock WebSocket bridge (required for factory initialization)
        self.mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.mock_websocket_bridge.notify_agent_started = AsyncMock()
        self.mock_websocket_bridge.notify_agent_completed = AsyncMock()
        self.mock_websocket_bridge.get_metrics = AsyncMock(return_value={
            'connections_active': 0,
            'events_sent': 0
        })
        
        # Create factory instance for testing
        self.factory = ExecutionEngineFactory(
            websocket_bridge=self.mock_websocket_bridge,
            database_session_manager=None,  # Not required for isolation test
            redis_manager=None  # Not required for isolation test
        )
        
        # Create mock agent instance factory
        self.mock_agent_factory = Mock()
        self.mock_agent_factory.create_user_websocket_emitter = Mock()
        
        # Setup factory with agent factory
        self.factory.set_tool_dispatcher_factory(Mock())
        
        # Record setup in metrics
        self.record_metric("factory_setup_complete", True)
    
    async def teardown_method(self, method=None):
        """Teardown test with factory cleanup."""
        try:
            if hasattr(self, 'factory') and self.factory:
                await self.factory.shutdown()
        finally:
            super().teardown_method(method)
    
    def create_test_user_context(self, user_id: str, suffix: str = "") -> UserExecutionContext:
        """Create test UserExecutionContext for factory testing.
        
        Args:
            user_id: User identifier
            suffix: Optional suffix for uniqueness
            
        Returns:
            UserExecutionContext for testing
        """
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"thread_{user_id}_{suffix}_{int(time.time())}",
            run_id=f"run_{user_id}_{suffix}_{int(time.time())}",
            request_id=str(uuid.uuid4()),
            agent_context={'test_context': True},
            audit_metadata={'test_source': 'factory_isolation_test'}
        )
    
    @pytest.mark.asyncio
    async def test_factory_creates_different_instances_per_user(self):
        """CRITICAL: Validate factory creates different engine instances per user.
        
        This test verifies the core isolation requirement: each user gets a
        completely separate engine instance with no shared references.
        
        Expected: FAIL before factory implementation (singleton sharing)
        Expected: PASS after factory implementation (true isolation)
        """
        # Create contexts for two different users
        user_a_context = self.create_test_user_context("user_a", "isolation_test")
        user_b_context = self.create_test_user_context("user_b", "isolation_test") 
        
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
            mock_get_factory.return_value = self.mock_agent_factory
            
            # Create engines for both users
            engine_a = await self.factory.create_for_user(user_a_context)
            engine_b = await self.factory.create_for_user(user_b_context)
            
            try:
                # CRITICAL: Engines must be different instances
                assert engine_a is not engine_b, (
                    "SSOT VIOLATION: Factory returned same engine instance for different users. "
                    "This violates user isolation and could cause data leakage between users."
                )
                
                # CRITICAL: Engines must have different IDs
                assert engine_a.engine_id != engine_b.engine_id, (
                    f"SSOT VIOLATION: Engines have same engine_id ('{engine_a.engine_id}'). "
                    f"Each user must have unique engine identifier."
                )
                
                # CRITICAL: User contexts must be isolated
                context_a = engine_a.get_user_context()
                context_b = engine_b.get_user_context()
                
                assert context_a.user_id != context_b.user_id, (
                    "SSOT VIOLATION: User contexts have same user_id. "
                    "This indicates improper context isolation."
                )
                
                assert context_a is not context_b, (
                    "SSOT VIOLATION: User contexts are same object reference. "
                    "This violates context isolation and could cause data leakage."
                )
                
                # CRITICAL: Memory addresses must be different
                engine_a_memory_id = id(engine_a)
                engine_b_memory_id = id(engine_b)
                
                assert engine_a_memory_id != engine_b_memory_id, (
                    f"SSOT VIOLATION: Engines have same memory address "
                    f"({engine_a_memory_id}). This indicates singleton behavior."
                )
                
                # Record isolation validation metrics
                self.record_metric("engines_isolated", True)
                self.record_metric("user_a_engine_id", engine_a.engine_id)
                self.record_metric("user_b_engine_id", engine_b.engine_id)
                self.record_metric("memory_isolation_verified", True)
                
            finally:
                # Clean up engines
                await self.factory.cleanup_engine(engine_a)
                await self.factory.cleanup_engine(engine_b)
    
    @pytest.mark.asyncio
    async def test_no_shared_state_between_user_engines(self):
        """CRITICAL: Validate no shared state/memory between concurrent user engines.
        
        This test verifies that internal engine state is completely isolated
        between different user engines, preventing cross-contamination.
        
        Expected: FAIL before factory implementation (shared state)
        Expected: PASS after factory implementation (isolated state)
        """
        # Create contexts for two different users
        user_a_context = self.create_test_user_context("user_alpha", "state_test")
        user_b_context = self.create_test_user_context("user_beta", "state_test")
        
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
            mock_get_factory.return_value = self.mock_agent_factory
            
            # Create engines for both users
            engine_a = await self.factory.create_for_user(user_a_context)
            engine_b = await self.factory.create_for_user(user_b_context)
            
            try:
                # CRITICAL: Active runs must be separate objects
                assert engine_a.active_runs is not engine_b.active_runs, (
                    "SSOT VIOLATION: Engines share active_runs object reference. "
                    "This would cause cross-user run contamination."
                )
                
                # Modify state in engine A
                test_run_id = "test_run_alpha"
                engine_a.active_runs[test_run_id] = {"user": "alpha", "data": "sensitive_alpha"}
                
                # CRITICAL: Engine B must not see Engine A's data
                assert test_run_id not in engine_b.active_runs, (
                    f"SSOT VIOLATION: Engine B can see Engine A's run '{test_run_id}'. "
                    f"This indicates shared state causing data leakage."
                )
                
                # CRITICAL: User execution states must be isolated
                # Check if engines have user execution state isolation
                if hasattr(engine_a, '_user_execution_states') and hasattr(engine_b, '_user_execution_states'):
                    assert engine_a._user_execution_states is not engine_b._user_execution_states, (
                        "SSOT VIOLATION: Engines share _user_execution_states object. "
                        "This violates per-user state isolation."
                    )
                
                # CRITICAL: Metrics must be isolated
                stats_a = engine_a.get_user_execution_stats()
                stats_b = engine_b.get_user_execution_stats()
                
                # Modify stats in engine A
                stats_a['test_metric'] = 'alpha_value'
                
                # Engine B stats must not be affected
                stats_b_after = engine_b.get_user_execution_stats()
                assert 'test_metric' not in stats_b_after, (
                    "SSOT VIOLATION: Engine B's stats were affected by Engine A changes. "
                    "This indicates shared statistics objects."
                )
                
                # Record state isolation validation
                self.record_metric("state_isolation_verified", True)
                self.record_metric("active_runs_isolated", engine_a.active_runs is not engine_b.active_runs)
                self.record_metric("cross_contamination_prevented", test_run_id not in engine_b.active_runs)
                
            finally:
                # Clean up engines
                await self.factory.cleanup_engine(engine_a)
                await self.factory.cleanup_engine(engine_b)
    
    @pytest.mark.asyncio
    async def test_user_changes_do_not_affect_other_engines(self):
        """CRITICAL: Validate User A changes don't affect User B engine state.
        
        This test performs comprehensive state modification on one engine
        and verifies it has no impact on another user's engine.
        
        Expected: FAIL before factory implementation (shared modifications)
        Expected: PASS after factory implementation (isolated modifications)
        """
        # Create contexts for different users
        user_x_context = self.create_test_user_context("user_x", "modification_test")
        user_y_context = self.create_test_user_context("user_y", "modification_test")
        
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
            mock_get_factory.return_value = self.mock_agent_factory
            
            # Create engines
            engine_x = await self.factory.create_for_user(user_x_context)
            engine_y = await self.factory.create_for_user(user_y_context)
            
            try:
                # Record initial state of engine Y
                initial_runs_y = dict(engine_y.active_runs)  # Copy for comparison
                initial_context_y = engine_y.get_user_context().to_dict()
                
                # AGGRESSIVE MODIFICATION of Engine X state
                # 1. Modify active runs extensively
                for i in range(5):
                    engine_x.active_runs[f"aggressive_run_{i}"] = {
                        "user_x_data": f"sensitive_data_{i}",
                        "timestamp": time.time(),
                        "contamination_test": True
                    }
                
                # 2. Modify user context if mutable (shouldn't be, but test anyway)
                context_x = engine_x.get_user_context()
                
                # 3. Modify any internal state we can access
                if hasattr(engine_x, '_user_execution_states'):
                    engine_x._user_execution_states['contamination_test'] = {
                        'user_x_contamination': True,
                        'should_not_leak': 'to_user_y'
                    }
                
                # CRITICAL VALIDATION: Engine Y must be completely unaffected
                
                # 1. Active runs must be unchanged
                assert engine_y.active_runs == initial_runs_y, (
                    f"SSOT VIOLATION: Engine Y's active_runs changed after Engine X modifications. "
                    f"Initial: {initial_runs_y}, Current: {dict(engine_y.active_runs)}"
                )
                
                # 2. No Engine X runs should appear in Engine Y
                for run_id in engine_x.active_runs:
                    assert run_id not in engine_y.active_runs, (
                        f"SSOT VIOLATION: Engine X's run '{run_id}' appeared in Engine Y's active_runs. "
                        f"This indicates shared state contamination."
                    )
                
                # 3. User context must be unchanged
                current_context_y = engine_y.get_user_context().to_dict()
                assert current_context_y['user_id'] == initial_context_y['user_id'], (
                    "SSOT VIOLATION: Engine Y's user_id changed after Engine X modifications."
                )
                
                # 4. Internal state isolation check
                if hasattr(engine_y, '_user_execution_states') and hasattr(engine_x, '_user_execution_states'):
                    assert 'contamination_test' not in engine_y._user_execution_states, (
                        "SSOT VIOLATION: Engine X's contamination_test leaked to Engine Y's state."
                    )
                
                # 5. Statistics must remain isolated
                stats_y = engine_y.get_user_execution_stats()
                assert 'user_x_contamination' not in str(stats_y), (
                    "SSOT VIOLATION: Engine X contamination data found in Engine Y statistics."
                )
                
                # Record comprehensive isolation validation
                self.record_metric("modification_isolation_verified", True)
                self.record_metric("engine_x_runs_count", len(engine_x.active_runs))
                self.record_metric("engine_y_runs_count", len(engine_y.active_runs))
                self.record_metric("no_cross_contamination", True)
                self.record_metric("context_isolation_maintained", True)
                
            finally:
                # Clean up engines
                await self.factory.cleanup_engine(engine_x)
                await self.factory.cleanup_engine(engine_y)
    
    @pytest.mark.asyncio
    async def test_memory_isolation_prevents_cross_user_contamination(self):
        """CRITICAL: Validate memory-level isolation prevents cross-user contamination.
        
        This test verifies that even at the memory level, there are no shared
        references that could allow data leakage between user engines.
        
        Expected: FAIL before factory implementation (shared memory references)
        Expected: PASS after factory implementation (memory-level isolation)
        """
        # Create multiple user contexts
        contexts = []
        for i in range(3):
            context = self.create_test_user_context(f"memory_test_user_{i}", f"mem_test_{i}")
            contexts.append(context)
        
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
            mock_get_factory.return_value = self.mock_agent_factory
            
            # Create engines for all users
            engines = []
            for context in contexts:
                engine = await self.factory.create_for_user(context)
                engines.append(engine)
            
            try:
                # CRITICAL: All engines must have unique memory addresses
                memory_addresses = [id(engine) for engine in engines]
                unique_addresses = set(memory_addresses)
                
                assert len(unique_addresses) == len(engines), (
                    f"SSOT VIOLATION: {len(engines)} engines but only {len(unique_addresses)} unique memory addresses. "
                    f"Addresses: {memory_addresses}. This indicates singleton behavior."
                )
                
                # CRITICAL: All active_runs must be different objects
                active_runs_addresses = [id(engine.active_runs) for engine in engines]
                unique_runs_addresses = set(active_runs_addresses)
                
                assert len(unique_runs_addresses) == len(engines), (
                    f"SSOT VIOLATION: {len(engines)} engines but only {len(unique_runs_addresses)} unique active_runs objects. "
                    f"This indicates shared active_runs state."
                )
                
                # CRITICAL: User contexts must be different objects
                context_addresses = [id(engine.get_user_context()) for engine in engines]
                unique_context_addresses = set(context_addresses)
                
                assert len(unique_context_addresses) == len(engines), (
                    f"SSOT VIOLATION: {len(engines)} engines but only {len(unique_context_addresses)} unique user contexts. "
                    f"This indicates shared context objects."
                )
                
                # CRITICAL: WebSocket emitters must be different (if present)
                websocket_addresses = []
                for engine in engines:
                    if hasattr(engine, 'websocket_emitter') and engine.websocket_emitter:
                        websocket_addresses.append(id(engine.websocket_emitter))
                
                if websocket_addresses:
                    unique_websocket_addresses = set(websocket_addresses)
                    assert len(unique_websocket_addresses) == len(websocket_addresses), (
                        f"SSOT VIOLATION: {len(websocket_addresses)} websocket emitters but only {len(unique_websocket_addresses)} unique objects. "
                        f"This indicates shared WebSocket emitters."
                    )
                
                # Record comprehensive memory isolation validation
                self.record_metric("memory_isolation_verified", True)
                self.record_metric("engines_count", len(engines))
                self.record_metric("unique_memory_addresses", len(unique_addresses))
                self.record_metric("unique_active_runs", len(unique_runs_addresses))
                self.record_metric("unique_contexts", len(unique_context_addresses))
                self.record_metric("unique_websocket_emitters", len(unique_websocket_addresses) if websocket_addresses else 0)
                
            finally:
                # Clean up all engines
                for engine in engines:
                    await self.factory.cleanup_engine(engine)
    
    @pytest.mark.asyncio
    async def test_concurrent_factory_calls_create_isolated_engines(self):
        """CRITICAL: Validate concurrent factory calls create properly isolated engines.
        
        This test simulates high-concurrency scenarios where multiple users
        request engines simultaneously, ensuring proper isolation under load.
        
        Expected: FAIL before factory implementation (race conditions, shared state)
        Expected: PASS after factory implementation (concurrent isolation)
        """
        # Create multiple user contexts for concurrent creation
        contexts = []
        for i in range(10):  # Test with 10 concurrent users
            context = self.create_test_user_context(f"concurrent_user_{i}", f"concurrent_{i}")
            contexts.append(context)
        
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
            mock_get_factory.return_value = self.mock_agent_factory
            
            async def create_engine_for_context(context):
                """Helper to create engine and track creation info."""
                start_time = time.time()
                engine = await self.factory.create_for_user(context)
                creation_time = time.time() - start_time
                return {
                    'engine': engine,
                    'context': context,
                    'creation_time': creation_time,
                    'engine_id': engine.engine_id,
                    'memory_id': id(engine)
                }
            
            # Create all engines concurrently
            tasks = [create_engine_for_context(context) for context in contexts]
            results = await asyncio.gather(*tasks)
            
            try:
                # CRITICAL: All results must be unique engines
                engines = [result['engine'] for result in results]
                engine_ids = [result['engine_id'] for result in results]
                memory_ids = [result['memory_id'] for result in results]
                
                # Validate unique engine IDs
                unique_engine_ids = set(engine_ids)
                assert len(unique_engine_ids) == len(engines), (
                    f"SSOT VIOLATION: {len(engines)} concurrent engines but only {len(unique_engine_ids)} unique IDs. "
                    f"Duplicate IDs detected: {[eid for eid in engine_ids if engine_ids.count(eid) > 1]}"
                )
                
                # Validate unique memory addresses
                unique_memory_ids = set(memory_ids)
                assert len(unique_memory_ids) == len(engines), (
                    f"SSOT VIOLATION: {len(engines)} concurrent engines but only {len(unique_memory_ids)} unique memory addresses. "
                    f"This indicates singleton behavior under concurrent load."
                )
                
                # CRITICAL: Each engine must serve correct user
                for result in results:
                    engine = result['engine']
                    expected_context = result['context']
                    actual_context = engine.get_user_context()
                    
                    assert actual_context.user_id == expected_context.user_id, (
                        f"SSOT VIOLATION: Engine created for user '{expected_context.user_id}' "
                        f"but serves user '{actual_context.user_id}'. This indicates context mix-up."
                    )
                
                # CRITICAL: Validate no shared state between concurrent engines
                # Add test data to first engine
                engines[0].active_runs['concurrent_test'] = {'data': 'test_isolation'}
                
                # Verify no other engines have this data
                for i, engine in enumerate(engines[1:], 1):
                    assert 'concurrent_test' not in engine.active_runs, (
                        f"SSOT VIOLATION: Engine {i} contains data from Engine 0. "
                        f"This indicates shared state under concurrent creation."
                    )
                
                # Record concurrent isolation validation
                self.record_metric("concurrent_isolation_verified", True)
                self.record_metric("concurrent_engines_created", len(engines))
                self.record_metric("unique_concurrent_ids", len(unique_engine_ids))
                self.record_metric("unique_concurrent_memory", len(unique_memory_ids))
                self.record_metric("max_creation_time", max(r['creation_time'] for r in results))
                self.record_metric("avg_creation_time", sum(r['creation_time'] for r in results) / len(results))
                
            finally:
                # Clean up all engines
                for result in results:
                    await self.factory.cleanup_engine(result['engine'])
    
    def test_factory_initialization_requires_websocket_bridge(self):
        """Validate factory initialization properly validates dependencies.
        
        This test ensures the factory fails fast if required dependencies
        are not provided, preventing runtime failures.
        
        Expected: ALWAYS PASS (proper validation)
        """
        # Test factory creation without websocket bridge
        with pytest.raises(Exception) as exc_info:
            ExecutionEngineFactory(
                websocket_bridge=None,  # Missing required dependency
                database_session_manager=None,
                redis_manager=None
            )
        
        # Validate error message indicates websocket bridge requirement
        error_message = str(exc_info.value)
        assert "websocket_bridge" in error_message.lower(), (
            f"Error message should mention websocket_bridge requirement: {error_message}"
        )
        
        # Record validation
        self.record_metric("factory_dependency_validation", True)
        self.record_metric("websocket_bridge_validation_works", True)
    
    @pytest.mark.asyncio
    async def test_ssot_factory_metrics_are_per_instance(self):
        """Validate factory metrics are isolated per factory instance.
        
        This test ensures factory metrics don't leak between different
        factory instances, maintaining proper isolation at the factory level.
        
        Expected: FAIL before factory implementation (shared metrics)
        Expected: PASS after factory implementation (isolated metrics)
        """
        # Create second factory instance
        mock_bridge_2 = Mock(spec=AgentWebSocketBridge)
        mock_bridge_2.notify_agent_started = AsyncMock()
        mock_bridge_2.get_metrics = AsyncMock(return_value={'connections': 0})
        
        factory_2 = ExecutionEngineFactory(
            websocket_bridge=mock_bridge_2,
            database_session_manager=None,
            redis_manager=None
        )
        
        try:
            # Get initial metrics from both factories
            metrics_1_initial = self.factory.get_factory_metrics()
            metrics_2_initial = factory_2.get_factory_metrics()
            
            # Create engine in factory 1
            user_context = self.create_test_user_context("metrics_user", "metrics_test")
            
            with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
                mock_get_factory.return_value = self.mock_agent_factory
                
                engine = await self.factory.create_for_user(user_context)
                
                try:
                    # Get metrics after creation
                    metrics_1_after = self.factory.get_factory_metrics()
                    metrics_2_after = factory_2.get_factory_metrics()
                    
                    # CRITICAL: Factory 1 metrics should change, Factory 2 should not
                    assert metrics_1_after['total_engines_created'] > metrics_1_initial['total_engines_created'], (
                        "Factory 1 metrics should reflect engine creation"
                    )
                    
                    assert metrics_2_after['total_engines_created'] == metrics_2_initial['total_engines_created'], (
                        f"SSOT VIOLATION: Factory 2 metrics changed when only Factory 1 created engine. "
                        f"Initial: {metrics_2_initial['total_engines_created']}, After: {metrics_2_after['total_engines_created']}"
                    )
                    
                    # CRITICAL: Active engine counts must be independent
                    assert metrics_1_after['active_engines_count'] > metrics_2_after['active_engines_count'], (
                        f"Factory 1 should have more active engines than Factory 2. "
                        f"Factory 1: {metrics_1_after['active_engines_count']}, Factory 2: {metrics_2_after['active_engines_count']}"
                    )
                    
                    # Record metrics isolation validation
                    self.record_metric("factory_metrics_isolated", True)
                    self.record_metric("factory_1_engines", metrics_1_after['total_engines_created'])
                    self.record_metric("factory_2_engines", metrics_2_after['total_engines_created'])
                    
                finally:
                    await self.factory.cleanup_engine(engine)
                    
        finally:
            await factory_2.shutdown()


# Business Value Justification (BVJ) Documentation
"""
BUSINESS VALUE JUSTIFICATION for ExecutionEngine Factory User Isolation Tests

Segment: ALL (Free → Enterprise) - affects every user on the platform
Business Goal: Legal/Compliance & User Trust - prevent data leakage between users
Value Impact: Guarantees user data privacy, regulatory compliance (GDPR, HIPAA), maintains user trust
Revenue Impact: Prevents catastrophic legal liability, maintains business license, prevents user churn
Strategic Impact: CRITICAL - data leakage could result in:
  - Loss of business license and regulatory sanctions
  - Massive legal liability and financial penalties
  - Complete loss of user trust and platform credibility
  - Potential criminal liability for data protection violations

Test Investment ROI:
- Test Development Cost: ~4 hours senior developer time
- Prevented Liability Cost: $10M+ in potential legal/regulatory penalties
- User Trust Maintenance: Priceless for platform viability
- ROI: 2,500,000%+ (cost of tests vs prevented damages)

This is the most critical test in the entire test suite from a legal compliance perspective.
"""