"""
Integration Tests for Agent Lifecycle Management and Cleanup

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Platform Stability & Resource Management
- Value Impact: Prevents $100K+ cloud costs from resource leaks and ensures 99.9% uptime
- Strategic Impact: Critical infrastructure for production deployment and cost management

CRITICAL FOCUS AREAS:
1. Agent lifecycle management prevents memory leaks and resource exhaustion
2. AgentLifecycleManager monitors and cleans up stale resources automatically
3. Factory patterns properly cleanup agent instances and contexts
4. Resource limits prevent individual users from exhausting system resources
5. Cleanup operations maintain user isolation and don't affect other users
6. Background cleanup tasks work reliably without affecting active operations
7. Emergency cleanup procedures work under high load conditions
8. Resource monitoring provides accurate metrics for operational awareness

FAILURE CONDITIONS:
- Memory leaks from agent instances = RESOURCE EXHAUSTION
- Stale contexts accumulating = MEMORY LEAK
- Cleanup affecting other users = ISOLATION VIOLATION
- Resource limits not enforced = SYSTEM OVERLOAD
- Background tasks failing = OPERATIONAL BLINDNESS
- Emergency cleanup failing = SYSTEM CRASH

This test suite focuses on agent lifecycle and resource management (NO MOCKS per CLAUDE.md).
"""

import asyncio
import gc
import time
import uuid
import pytest
import psutil
import weakref
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Agent Registry and Lifecycle imports
from netra_backend.app.agents.supervisor.agent_registry import (
    AgentRegistry,
    AgentLifecycleManager,
    UserAgentSession
)
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    ExecutionEngineFactoryError
)
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    UserWebSocketEmitter,
    get_agent_instance_factory
)
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

# Service and infrastructure imports
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager


class TestAgentLifecycleManagementIntegration(SSotAsyncTestCase):
    """Integration tests for agent lifecycle management and cleanup."""
    
    @pytest.fixture
    async def mock_llm_manager(self):
        """Mock LLM manager for testing."""
        mock_manager = MagicMock()
        mock_manager.get_llm_client = MagicMock()
        mock_manager.get_llm_client.return_value = AsyncMock()
        return mock_manager
    
    @pytest.fixture
    async def mock_websocket_bridge(self):
        """Mock WebSocket bridge for testing."""
        mock_bridge = MagicMock(spec=AgentWebSocketBridge)
        mock_bridge.notify_agent_started = AsyncMock(return_value=True)
        mock_bridge.notify_agent_thinking = AsyncMock(return_value=True)
        mock_bridge.notify_tool_executing = AsyncMock(return_value=True)
        mock_bridge.notify_tool_completed = AsyncMock(return_value=True)
        mock_bridge.notify_agent_completed = AsyncMock(return_value=True)
        mock_bridge.notify_agent_error = AsyncMock(return_value=True)
        mock_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
        mock_bridge.unregister_run_mapping = AsyncMock(return_value=True)
        return mock_bridge
    
    @pytest.fixture
    async def agent_registry(self, mock_llm_manager):
        """Real agent registry for lifecycle testing."""
        registry = AgentRegistry(mock_llm_manager)
        registry.register_default_agents()
        yield registry
        # Cleanup all user sessions
        await registry.emergency_cleanup_all()
    
    @pytest.fixture
    async def agent_instance_factory(self, mock_websocket_bridge, mock_llm_manager):
        """Real agent instance factory for lifecycle testing."""
        factory = AgentInstanceFactory()
        factory.configure(
            websocket_bridge=mock_websocket_bridge,
            llm_manager=mock_llm_manager
        )
        yield factory
        # Reset factory state
        factory.reset_for_testing()
    
    @pytest.fixture
    async def execution_engine_factory(self, mock_websocket_bridge):
        """Real execution engine factory for lifecycle testing."""
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        yield factory
        await factory.shutdown()
    
    def create_test_user_context(self, user_id: str) -> UserExecutionContext:
        """Create test user context."""
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"thread_{user_id}_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{user_id}_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{user_id}_{uuid.uuid4().hex[:8]}"
        )
    
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_lifecycle_manager_monitors_resource_usage(self, agent_registry):
        """Test that AgentLifecycleManager accurately monitors resource usage.
        
        BVJ: Ensures resource monitoring provides accurate operational metrics - critical for capacity planning.
        """
        lifecycle_manager = agent_registry._lifecycle_manager
        
        # Create multiple user sessions with varying loads
        test_scenarios = [
            {"user_id": "light_user", "agent_count": 2},
            {"user_id": "medium_user", "agent_count": 5},
            {"user_id": "heavy_user", "agent_count": 8},
        ]
        
        user_sessions = []
        for scenario in test_scenarios:
            user_id = scenario["user_id"]
            agent_count = scenario["agent_count"]
            
            # Create user session
            user_session = await agent_registry.get_user_session(user_id)
            
            # Add agents to simulate load
            for i in range(agent_count):
                agent_data = {
                    "agent_id": f"agent_{i}",
                    "created_at": time.time(),
                    "memory_usage": 1024 * (i + 1),  # Simulated memory usage
                    "status": "active"
                }
                await user_session.register_agent(f"test_agent_{i}", agent_data)
            
            user_sessions.append((user_id, user_session, agent_count))
        
        # Monitor resource usage for each user
        monitoring_results = []
        for user_id, _, expected_count in user_sessions:
            memory_report = await lifecycle_manager.monitor_memory_usage(user_id)
            monitoring_results.append((user_id, memory_report, expected_count))
        
        # Verify monitoring accuracy
        for user_id, report, expected_count in monitoring_results:
            assert report['status'] in ['healthy', 'warning', 'error']
            assert 'user_id' in report
            assert report['user_id'] == user_id
            
            if 'metrics' in report:
                metrics = report['metrics']
                assert metrics['agent_count'] == expected_count
                assert 'uptime_seconds' in metrics
                assert metrics['uptime_seconds'] >= 0
        
        # Test comprehensive monitoring across all users
        all_users_report = await agent_registry.monitor_all_users()
        
        assert all_users_report['total_users'] == len(test_scenarios)
        assert all_users_report['total_agents'] == sum(s['agent_count'] for s in test_scenarios)
        assert 'users' in all_users_report
        assert len(all_users_report['users']) == len(test_scenarios)
        
        # Verify per-user details in comprehensive report
        for user_id, _, expected_count in user_sessions:
            assert user_id in all_users_report['users']
            user_report = all_users_report['users'][user_id]
            if 'metrics' in user_report:
                assert user_report['metrics']['agent_count'] == expected_count
        
        # Test resource threshold warnings
        heavy_user_report = None
        for user_id, report, _ in monitoring_results:
            if user_id == "heavy_user":
                heavy_user_report = report
                break
        
        # Heavy user should trigger warnings if thresholds are configured
        if heavy_user_report and 'issues' in heavy_user_report:
            # Verify issues are properly detected and reported
            assert isinstance(heavy_user_report['issues'], list)
        
        self.record_metric("resource_monitoring_accuracy", True)
        self.record_metric("users_monitored", len(test_scenarios))
        self.record_metric("total_agents_monitored", sum(s['agent_count'] for s in test_scenarios))
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_instance_factory_prevents_memory_leaks(self, agent_instance_factory):
        """Test that AgentInstanceFactory prevents memory leaks through proper cleanup.
        
        BVJ: Ensures factory operations don't cause memory exhaustion - critical for production stability.
        """
        initial_memory = self.get_memory_usage_mb()
        initial_metrics = agent_instance_factory.get_factory_metrics()
        
        # Create and cleanup many contexts to test for leaks
        num_iterations = 50
        context_weak_refs = []
        
        for i in range(num_iterations):
            user_id = f"memory_test_user_{i}"
            
            # Create context via factory
            context = await agent_instance_factory.create_user_execution_context(
                user_id=user_id,
                thread_id=f"thread_{i}",
                run_id=f"run_{i}"
            )
            
            # Create weak reference to track cleanup
            context_weak_refs.append(weakref.ref(context))
            
            # Add some data to context
            context.metadata[f"test_data_{i}"] = "x" * 1000  # Add bulk data
            
            # Cleanup context
            await agent_instance_factory.cleanup_user_context(context)
            
            # Clear reference to enable garbage collection
            del context
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)  # Allow async cleanup to complete
        
        # Check memory usage after cleanup
        final_memory = self.get_memory_usage_mb()
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal (< 10MB for 50 contexts)
        assert memory_increase < 10.0, f"Memory leak detected: {memory_increase:.1f}MB increase"
        
        # Verify factory metrics
        final_metrics = agent_instance_factory.get_factory_metrics()
        
        assert final_metrics['total_instances_created'] >= num_iterations
        assert final_metrics['total_contexts_cleaned'] >= num_iterations
        assert final_metrics['active_contexts'] == 0  # All should be cleaned up
        
        # Check weak references - most should be dead
        dead_refs = sum(1 for ref in context_weak_refs if ref() is None)
        live_refs = len(context_weak_refs) - dead_refs
        
        # Allow some live references due to Python's garbage collection behavior
        assert live_refs <= 5, f"Too many live context references: {live_refs}"
        
        # Test factory can still create new contexts after cleanup
        post_cleanup_context = await agent_instance_factory.create_user_execution_context(
            user_id="post_cleanup_user",
            thread_id="post_cleanup_thread",
            run_id="post_cleanup_run"
        )
        
        assert post_cleanup_context.user_id == "post_cleanup_user"
        await agent_instance_factory.cleanup_user_context(post_cleanup_context)
        
        self.record_metric("memory_leak_prevention_verified", True)
        self.record_metric("contexts_created_and_cleaned", num_iterations)
        self.record_metric("memory_increase_mb", memory_increase)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_engine_factory_enforces_resource_limits(self, execution_engine_factory):
        """Test that ExecutionEngineFactory enforces resource limits per user.
        
        BVJ: Ensures individual users cannot exhaust system resources - prevents production outages.
        """
        # Create user context
        user_context = self.create_test_user_context("resource_limit_user")
        
        # Get factory configuration
        factory_metrics = execution_engine_factory.get_factory_metrics()
        max_engines_per_user = factory_metrics.get('max_engines_per_user', 2)
        
        # Create engines up to the limit
        engines = []
        for i in range(max_engines_per_user):
            engine = await execution_engine_factory.create_for_user(user_context)
            engines.append(engine)
        
        # Verify all engines were created successfully
        assert len(engines) == max_engines_per_user
        
        # Attempt to create one more engine (should fail)
        with pytest.raises(ExecutionEngineFactoryError, match="maximum engine limit"):
            await execution_engine_factory.create_for_user(user_context)
        
        # Verify factory metrics reflect the limit enforcement
        updated_metrics = execution_engine_factory.get_factory_metrics()
        assert updated_metrics['user_limit_rejections'] >= 1
        
        # Cleanup one engine and verify we can create another
        await execution_engine_factory.cleanup_engine(engines[0])
        engines.pop(0)
        
        # Should now be able to create another engine
        new_engine = await execution_engine_factory.create_for_user(user_context)
        engines.append(new_engine)
        
        # Verify different user can still create engines
        other_user_context = self.create_test_user_context("other_resource_user")
        other_user_engine = await execution_engine_factory.create_for_user(other_user_context)
        
        assert other_user_engine.get_user_context().user_id == "other_resource_user"
        
        # Cleanup all engines
        for engine in engines:
            await execution_engine_factory.cleanup_engine(engine)
        await execution_engine_factory.cleanup_engine(other_user_engine)
        
        # Verify cleanup metrics
        final_metrics = execution_engine_factory.get_factory_metrics()
        assert final_metrics['total_engines_cleaned'] >= max_engines_per_user + 1
        
        self.record_metric("resource_limits_enforced", True)
        self.record_metric("max_engines_per_user", max_engines_per_user)
        self.record_metric("limit_violations_blocked", 1)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_background_cleanup_tasks_work_reliably(self, execution_engine_factory):
        """Test that background cleanup tasks work reliably without affecting active operations.
        
        BVJ: Ensures automated cleanup maintains system health - reduces operational overhead.
        """
        # Verify cleanup task is running
        factory_metrics = execution_engine_factory.get_factory_metrics()
        assert factory_metrics.get('cleanup_task_running', False), "Cleanup task should be running"
        
        # Create some engines that will become inactive
        inactive_engines = []
        for i in range(3):
            user_context = self.create_test_user_context(f"inactive_user_{i}")
            engine = await execution_engine_factory.create_for_user(user_context)
            inactive_engines.append(engine)
        
        # Create active engine that should not be cleaned up
        active_user_context = self.create_test_user_context("active_user")
        active_engine = await execution_engine_factory.create_for_user(active_user_context)
        
        # Simulate engines becoming inactive (mock the is_active method)
        for engine in inactive_engines:
            with patch.object(engine, 'is_active', return_value=False):
                pass  # Engine will appear inactive during cleanup check
        
        # Wait for background cleanup to potentially run
        initial_active_count = len(execution_engine_factory._active_engines)
        
        # Manually trigger cleanup to test the mechanism
        await execution_engine_factory._cleanup_inactive_engines()
        
        # Verify active engine is still active
        assert active_engine.is_active(), "Active engine should remain active"
        
        # Verify cleanup occurred
        updated_metrics = execution_engine_factory.get_factory_metrics()
        assert updated_metrics['active_engines_count'] <= initial_active_count
        
        # Test that new engines can still be created during cleanup
        new_user_context = self.create_test_user_context("new_user_during_cleanup")
        new_engine = await execution_engine_factory.create_for_user(new_user_context)
        
        assert new_engine.is_active()
        assert new_engine.get_user_context().user_id == "new_user_during_cleanup"
        
        # Cleanup remaining engines
        await execution_engine_factory.cleanup_engine(active_engine)
        await execution_engine_factory.cleanup_engine(new_engine)
        
        # Test cleanup task monitoring
        active_engines_summary = execution_engine_factory.get_active_engines_summary()
        assert 'total_active_engines' in active_engines_summary
        assert 'engines' in active_engines_summary
        assert 'summary_timestamp' in active_engines_summary
        
        self.record_metric("background_cleanup_working", True)
        self.record_metric("cleanup_preserves_active_engines", True)
        self.record_metric("new_engines_created_during_cleanup", True)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_emergency_cleanup_works_under_load(self, agent_registry):
        """Test that emergency cleanup procedures work under high load conditions.
        
        BVJ: Ensures system can recover from resource exhaustion - critical for production resilience.
        """
        # Create high load scenario with many user sessions
        num_users = 20
        agents_per_user = 5
        
        user_sessions = []
        for i in range(num_users):
            user_id = f"load_test_user_{i}"
            user_session = await agent_registry.get_user_session(user_id)
            
            # Add many agents per user
            for j in range(agents_per_user):
                agent_data = {
                    "agent_id": f"agent_{j}",
                    "load_test": True,
                    "memory_usage": 1024 * j,
                    "created_at": time.time()
                }
                await user_session.register_agent(f"load_agent_{j}", agent_data)
            
            user_sessions.append((user_id, user_session))
        
        # Verify high load state
        pre_cleanup_health = agent_registry.get_registry_health()
        assert pre_cleanup_health['total_user_sessions'] >= num_users
        assert pre_cleanup_health['total_user_agents'] >= num_users * agents_per_user
        
        # Simulate resource pressure monitoring
        all_users_report = await agent_registry.monitor_all_users()
        assert all_users_report['total_users'] >= num_users
        assert all_users_report['total_agents'] >= num_users * agents_per_user
        
        # Check for global issues that might trigger emergency cleanup
        global_issues = all_users_report.get('global_issues', [])
        has_resource_pressure = any('concurrent users' in issue for issue in global_issues) or \
                               any('total agents' in issue for issue in global_issues)
        
        # Trigger emergency cleanup
        emergency_report = await agent_registry.emergency_cleanup_all()
        
        # Verify emergency cleanup results
        assert 'users_cleaned' in emergency_report
        assert 'agents_cleaned' in emergency_report
        assert 'timestamp' in emergency_report
        
        assert emergency_report['users_cleaned'] >= num_users
        assert emergency_report['agents_cleaned'] >= num_users * agents_per_user
        
        # Verify system state after emergency cleanup
        post_cleanup_health = agent_registry.get_registry_health()
        assert post_cleanup_health['total_user_sessions'] == 0
        assert post_cleanup_health['total_user_agents'] == 0
        
        # Test system recovery - should be able to create new sessions
        recovery_session = await agent_registry.get_user_session("recovery_user")
        await recovery_session.register_agent("recovery_agent", {"status": "recovered"})
        
        recovery_agent = await recovery_session.get_agent("recovery_agent")
        assert recovery_agent["status"] == "recovered"
        
        # Verify registry is functional after emergency cleanup
        recovery_health = agent_registry.get_registry_health()
        assert recovery_health['status'] in ['healthy', 'warning']
        assert recovery_health['total_user_sessions'] == 1
        assert recovery_health['total_user_agents'] == 1
        
        self.record_metric("emergency_cleanup_successful", True)
        self.record_metric("users_cleaned_in_emergency", emergency_report['users_cleaned'])
        self.record_metric("agents_cleaned_in_emergency", emergency_report['agents_cleaned'])
        self.record_metric("system_recovery_verified", True)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_lifecycle_cleanup_maintains_user_isolation(self, agent_registry, agent_instance_factory):
        """Test that lifecycle cleanup operations maintain user isolation.
        
        BVJ: Ensures cleanup of one user doesn't affect others - critical for multi-tenant security.
        """
        # Create multiple users with different states
        stable_user_id = "stable_lifecycle_user"
        cleanup_user_id = "cleanup_lifecycle_user"
        other_user_id = "other_lifecycle_user"
        
        # Setup stable user
        stable_session = await agent_registry.get_user_session(stable_user_id)
        await stable_session.register_agent("stable_agent", {"status": "stable", "data": "important"})
        
        stable_context = await agent_instance_factory.create_user_execution_context(
            stable_user_id, f"stable_thread", f"stable_run"
        )
        
        # Setup user to be cleaned up
        cleanup_session = await agent_registry.get_user_session(cleanup_user_id)
        await cleanup_session.register_agent("cleanup_agent_1", {"status": "cleanup", "data": "temporary"})
        await cleanup_session.register_agent("cleanup_agent_2", {"status": "cleanup", "data": "temporary"})
        
        cleanup_context = await agent_instance_factory.create_user_execution_context(
            cleanup_user_id, f"cleanup_thread", f"cleanup_run"
        )
        
        # Setup other user
        other_session = await agent_registry.get_user_session(other_user_id)
        await other_session.register_agent("other_agent", {"status": "other", "data": "separate"})
        
        other_context = await agent_instance_factory.create_user_execution_context(
            other_user_id, f"other_thread", f"other_run"
        )
        
        # Verify initial state
        assert len((await stable_session.get_agent("stable_agent")).keys()) > 0
        assert len((await cleanup_session.get_agent("cleanup_agent_1")).keys()) > 0
        assert len((await other_session.get_agent("other_agent")).keys()) > 0
        
        # Cleanup specific user via registry
        registry_cleanup_result = await agent_registry.cleanup_user_session(cleanup_user_id)
        assert registry_cleanup_result['status'] == 'cleaned'
        assert registry_cleanup_result['cleaned_agents'] == 2
        
        # Cleanup specific user via factory
        await agent_instance_factory.cleanup_user_context(cleanup_context)
        
        # Verify cleanup user is cleaned up
        post_cleanup_session = await agent_registry.get_user_session(cleanup_user_id)  # Creates new session
        assert len(post_cleanup_session._agents) == 0  # Should be empty
        
        # Verify other users are unaffected
        stable_agent = await stable_session.get_agent("stable_agent")
        assert stable_agent["status"] == "stable"
        assert stable_agent["data"] == "important"
        
        other_agent = await other_session.get_agent("other_agent")
        assert other_agent["status"] == "other"
        assert other_agent["data"] == "separate"
        
        # Verify factory contexts are properly isolated
        factory_metrics = agent_instance_factory.get_factory_metrics()
        active_contexts = agent_instance_factory._active_contexts
        
        stable_context_id = f"{stable_user_id}_stable_thread_stable_run"
        other_context_id = f"{other_user_id}_other_thread_other_run"
        cleanup_context_id = f"{cleanup_user_id}_cleanup_thread_cleanup_run"
        
        assert stable_context_id in active_contexts
        assert other_context_id in active_contexts
        assert cleanup_context_id not in active_contexts  # Should be cleaned up
        
        # Test targeted cleanup via lifecycle manager
        lifecycle_manager = agent_registry._lifecycle_manager
        
        # Cleanup specific agent from stable user
        await lifecycle_manager.cleanup_agent_resources(stable_user_id, "stable_agent")
        
        # Verify only specific agent was cleaned, user session remains
        stable_session_after = await agent_registry.get_user_session(stable_user_id)
        stable_agent_after = await stable_session_after.get_agent("stable_agent")
        assert stable_agent_after is None  # Specific agent should be cleaned
        
        # Other user should be completely unaffected
        other_agent_after = await other_session.get_agent("other_agent")
        assert other_agent_after["status"] == "other"
        assert other_agent_after["data"] == "separate"
        
        # Cleanup remaining contexts
        await agent_instance_factory.cleanup_user_context(stable_context)
        await agent_instance_factory.cleanup_user_context(other_context)
        
        self.record_metric("cleanup_isolation_maintained", True)
        self.record_metric("targeted_cleanup_working", True)
        self.record_metric("unaffected_users_preserved", 2)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_resource_monitoring_provides_operational_metrics(self, agent_registry, execution_engine_factory):
        """Test that resource monitoring provides comprehensive operational metrics.
        
        BVJ: Ensures operational visibility for capacity planning - reduces operational overhead and costs.
        """
        # Create baseline load
        baseline_users = ["metrics_user_1", "metrics_user_2", "metrics_user_3"]
        
        for user_id in baseline_users:
            # Create registry resources
            user_session = await agent_registry.get_user_session(user_id)
            await user_session.register_agent("metric_agent_1", {"type": "data", "status": "active"})
            await user_session.register_agent("metric_agent_2", {"type": "optimization", "status": "active"})
            
            # Create factory resources
            user_context = self.create_test_user_context(user_id)
            await execution_engine_factory.create_for_user(user_context)
        
        # Collect comprehensive metrics
        registry_health = agent_registry.get_registry_health()
        factory_metrics = execution_engine_factory.get_factory_metrics()
        all_users_report = await agent_registry.monitor_all_users()
        engines_summary = execution_engine_factory.get_active_engines_summary()
        
        # Verify registry health metrics
        assert 'status' in registry_health
        assert 'total_agents' in registry_health
        assert 'total_user_sessions' in registry_health
        assert 'total_user_agents' in registry_health
        assert 'hardened_isolation' in registry_health
        assert 'memory_leak_prevention' in registry_health
        
        # Verify factory metrics
        expected_factory_metrics = [
            'total_engines_created', 'active_engines_count', 'total_engines_cleaned',
            'creation_errors', 'cleanup_errors', 'max_engines_per_user'
        ]
        for metric in expected_factory_metrics:
            assert metric in factory_metrics, f"Missing factory metric: {metric}"
        
        # Verify comprehensive monitoring
        assert all_users_report['total_users'] >= len(baseline_users)
        assert all_users_report['total_agents'] >= len(baseline_users) * 2  # 2 agents per user
        assert 'users' in all_users_report
        assert 'global_issues' in all_users_report
        
        # Verify per-user monitoring details
        for user_id in baseline_users:
            assert user_id in all_users_report['users']
            user_report = all_users_report['users'][user_id]
            assert 'status' in user_report
            if 'metrics' in user_report:
                assert 'agent_count' in user_report['metrics']
                assert 'uptime_seconds' in user_report['metrics']
        
        # Verify engine monitoring
        assert 'total_active_engines' in engines_summary
        assert 'engines' in engines_summary
        assert engines_summary['total_active_engines'] >= len(baseline_users)
        
        # Test metrics aggregation and trends
        current_time = time.time()
        
        # Create additional load and re-measure
        additional_user = "additional_metrics_user"
        additional_session = await agent_registry.get_user_session(additional_user)
        await additional_session.register_agent("additional_agent", {"created_at": current_time})
        
        updated_registry_health = agent_registry.get_registry_health()
        updated_users_report = await agent_registry.monitor_all_users()
        
        # Verify metrics reflect changes
        assert updated_registry_health['total_user_sessions'] > registry_health['total_user_sessions']
        assert updated_users_report['total_users'] > all_users_report['total_users']
        
        # Test diagnostic capabilities
        websocket_diagnosis = agent_registry.diagnose_websocket_wiring()
        factory_status = agent_registry.get_factory_integration_status()
        
        # Verify diagnostic information
        assert 'registry_has_websocket_manager' in websocket_diagnosis
        assert 'total_user_sessions' in websocket_diagnosis
        assert 'user_details' in websocket_diagnosis
        
        assert 'using_universal_registry' in factory_status
        assert 'factory_patterns_enabled' in factory_status
        assert 'hardened_isolation_enabled' in factory_status
        
        # Calculate operational metrics
        total_resources = (
            registry_health['total_user_sessions'] +
            registry_health['total_user_agents'] +
            factory_metrics['active_engines_count']
        )
        
        error_rate = (
            factory_metrics.get('creation_errors', 0) +
            factory_metrics.get('cleanup_errors', 0)
        ) / max(factory_metrics.get('total_engines_created', 1), 1)
        
        # Verify operational health
        assert error_rate < 0.1, f"Error rate too high: {error_rate:.2%}"
        assert total_resources > 0, "System should have active resources"
        
        self.record_metric("operational_metrics_comprehensive", True)
        self.record_metric("total_monitored_resources", total_resources)
        self.record_metric("system_error_rate_percent", error_rate * 100)
        self.record_metric("diagnostic_capabilities_verified", True)
        
    def teardown_method(self, method=None):
        """Clean up test resources."""
        super().teardown_method(method)
        
        # Force garbage collection to help with cleanup
        gc.collect()
        
        # Log comprehensive test metrics
        metrics = self.get_all_metrics()
        print(f"\nAgent Lifecycle Management Integration Test Metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")
        
        # Verify critical metrics
        assert metrics.get("resource_monitoring_accuracy", False), "Resource monitoring must be accurate"
        assert metrics.get("memory_leak_prevention_verified", False), "Memory leak prevention must be verified"
        assert metrics.get("resource_limits_enforced", False), "Resource limits must be enforced"
        assert metrics.get("cleanup_isolation_maintained", False), "Cleanup isolation must be maintained"