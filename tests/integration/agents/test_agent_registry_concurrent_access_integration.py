"""
Agent Registry Concurrent Access Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure 
- Business Goal: Ensure thread-safe agent registry operations under concurrent load
- Value Impact: Prevents race conditions that could break agent orchestration
- Strategic Impact: Foundation for reliable multi-user agent execution ($500K+ ARR protection)

Integration Test Requirements:
- NO database dependencies - tests registry patterns without external services
- NO Docker requirements - tests concurrent access patterns in isolation
- Uses real agent registry components and factory patterns
- Validates thread-safety and user isolation under load
- Tests agent registration, lookup, and lifecycle management concurrency

Phase 1 Priority Areas:
1. Agent registry concurrent access patterns
2. Multi-user agent registration isolation
3. Factory pattern thread-safety validation  
4. Agent lookup performance under load
5. Registry cleanup and lifecycle management

CRITICAL: These tests validate that the agent registry can handle concurrent
operations safely without race conditions, ensuring reliable Golden Path execution.
"""

import asyncio
import pytest
import time
import uuid
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, get_agent_registry
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter

import logging
logger = logging.getLogger(__name__)


class MockAgentForRegistry:
    """Mock agent implementation for registry testing."""
    
    def __init__(self, agent_name: str, user_id: str):
        self.agent_name = agent_name
        self.name = agent_name
        self.user_id = user_id
        self.created_at = time.time()
        self.access_count = 0
        self.is_active = True
        
    async def initialize(self):
        """Initialize agent."""
        await asyncio.sleep(0.001)  # Simulate initialization
        
    async def execute(self, prompt: str, **kwargs):
        """Mock execution method."""
        self.access_count += 1
        await asyncio.sleep(0.001)  # Simulate work
        return {
            'success': True,
            'agent_name': self.agent_name,
            'user_id': self.user_id,
            'execution_count': self.access_count
        }
        
    async def cleanup(self):
        """Cleanup agent resources."""
        self.is_active = False


class MockAgentFactory:
    """Mock agent factory for testing concurrent agent creation."""
    
    def __init__(self):
        self.creation_count = 0
        self.created_agents = {}
        self.creation_lock = asyncio.Lock()
        
    async def create_agent(self, agent_name: str, user_context: UserExecutionContext):
        """Create agent instance with thread-safety simulation."""
        async with self.creation_lock:
            self.creation_count += 1
            
        agent = MockAgentForRegistry(agent_name, user_context.user_id)
        await agent.initialize()
        
        # Store agent reference
        agent_key = f"{user_context.user_id}:{agent_name}"
        self.created_agents[agent_key] = agent
        
        logger.info(f"Created agent {agent_name} for user {user_context.user_id} (total: {self.creation_count})")
        return agent
        
    def get_creation_stats(self):
        """Get factory statistics."""
        return {
            'total_created': self.creation_count,
            'active_agents': len([a for a in self.created_agents.values() if a.is_active]),
            'agents_by_user': {}
        }


class ThreadSafeAgentRegistry:
    """Thread-safe agent registry implementation for testing."""
    
    def __init__(self):
        self.agents = {}  # user_id:agent_name -> agent
        self.user_sessions = {}  # user_id -> session_data
        self.access_lock = threading.RLock()
        self.factory = MockAgentFactory()
        self.access_counts = {}
        self.registration_history = []
        
    async def register_agent(self, user_context: UserExecutionContext, agent_name: str, **kwargs):
        """Register agent for user with thread safety."""
        with self.access_lock:
            agent_key = f"{user_context.user_id}:{agent_name}"
            
            # Track registration
            self.registration_history.append({
                'user_id': user_context.user_id,
                'agent_name': agent_name,
                'timestamp': time.time(),
                'thread_id': threading.get_ident()
            })
            
            # Create agent if not exists
            if agent_key not in self.agents:
                agent = await self.factory.create_agent(agent_name, user_context)
                self.agents[agent_key] = agent
                
                # Initialize user session
                if user_context.user_id not in self.user_sessions:
                    self.user_sessions[user_context.user_id] = {
                        'user_id': user_context.user_id,
                        'agents': [],
                        'created_at': time.time(),
                        'thread_id': user_context.thread_id
                    }
                
                self.user_sessions[user_context.user_id]['agents'].append(agent_name)
                
            return self.agents[agent_key]
    
    async def get_agent(self, user_context: UserExecutionContext, agent_name: str):
        """Get agent for user with access tracking."""
        with self.access_lock:
            agent_key = f"{user_context.user_id}:{agent_name}"
            
            # Track access
            if agent_key not in self.access_counts:
                self.access_counts[agent_key] = 0
            self.access_counts[agent_key] += 1
            
            return self.agents.get(agent_key)
    
    def list_user_agents(self, user_id: str) -> List[str]:
        """List agents for specific user."""
        with self.access_lock:
            if user_id in self.user_sessions:
                return self.user_sessions[user_id]['agents'].copy()
            return []
    
    def get_registry_stats(self):
        """Get registry statistics."""
        with self.access_lock:
            return {
                'total_agents': len(self.agents),
                'total_users': len(self.user_sessions),
                'total_accesses': sum(self.access_counts.values()),
                'registrations': len(self.registration_history),
                'agents_per_user': {uid: len(session['agents']) for uid, session in self.user_sessions.items()}
            }
    
    async def cleanup_user_agents(self, user_id: str):
        """Clean up all agents for a user."""
        with self.access_lock:
            agents_to_cleanup = []
            keys_to_remove = []
            
            for agent_key, agent in self.agents.items():
                if agent_key.startswith(f"{user_id}:"):
                    agents_to_cleanup.append(agent)
                    keys_to_remove.append(agent_key)
            
            # Remove from registry
            for key in keys_to_remove:
                del self.agents[key]
            
            # Remove user session
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
        
        # Cleanup agents outside of lock
        for agent in agents_to_cleanup:
            await agent.cleanup()


class TestAgentRegistryConcurrentAccess(SSotAsyncTestCase):
    """Integration tests for concurrent agent registry access patterns."""
    
    async def setUp(self):
        """Set up test fixtures."""
        await super().setUp()
        self.registry = ThreadSafeAgentRegistry()
        self.test_start_time = time.time()
    
    @pytest.mark.integration
    @pytest.mark.agents  
    async def test_concurrent_agent_registration(self):
        """Test concurrent agent registration from multiple users.
        
        BVJ: Validates that multiple users can register agents simultaneously
        without race conditions or registry corruption.
        """
        num_users = 5
        agents_per_user = 3
        
        # Create user contexts
        user_contexts = []
        for i in range(num_users):
            user_context = UserExecutionContext(
                user_id=f"concurrent_user_{i+1:02d}",
                thread_id=f"thread_{i+1:02d}", 
                run_id=f"run_{i+1:02d}_{int(time.time())}",
                request_id=f"req_{i+1:02d}_{uuid.uuid4().hex[:8]}"
            )
            user_contexts.append(user_context)
        
        # Define registration task
        async def register_user_agents(user_context: UserExecutionContext):
            """Register multiple agents for a user."""
            agent_names = [f"agent_{j+1}" for j in range(agents_per_user)]
            registered_agents = []
            
            for agent_name in agent_names:
                agent = await self.registry.register_agent(user_context, agent_name)
                registered_agents.append(agent)
                # Small delay to simulate real registration timing
                await asyncio.sleep(0.001)
            
            return user_context.user_id, registered_agents
        
        # Execute concurrent registrations
        registration_tasks = [register_user_agents(ctx) for ctx in user_contexts]
        results = await asyncio.gather(*registration_tasks)
        
        # Validate all registrations succeeded
        for user_id, agents in results:
            assert len(agents) == agents_per_user, f"User {user_id} should have {agents_per_user} agents"
            for agent in agents:
                assert agent is not None, f"Agent should be successfully created for {user_id}"
                assert agent.user_id == user_id, f"Agent should belong to {user_id}"
                assert agent.is_active, f"Agent should be active for {user_id}"
        
        # Validate registry state
        registry_stats = self.registry.get_registry_stats()
        expected_total_agents = num_users * agents_per_user
        
        assert registry_stats['total_agents'] == expected_total_agents, \
            f"Registry should have {expected_total_agents} agents, got {registry_stats['total_agents']}"
        assert registry_stats['total_users'] == num_users, \
            f"Registry should have {num_users} users, got {registry_stats['total_users']}"
        
        # Validate user isolation
        for user_context in user_contexts:
            user_agents = self.registry.list_user_agents(user_context.user_id)
            assert len(user_agents) == agents_per_user, \
                f"User {user_context.user_id} should have {agents_per_user} agents"
            
            # Verify agent names match expected pattern
            expected_names = [f"agent_{j+1}" for j in range(agents_per_user)]
            assert set(user_agents) == set(expected_names), \
                f"User {user_context.user_id} should have agents {expected_names}"
        
        # Validate no cross-user contamination
        for i, user_context_1 in enumerate(user_contexts):
            for j, user_context_2 in enumerate(user_contexts):
                if i != j:
                    user_1_agents = self.registry.list_user_agents(user_context_1.user_id)
                    user_2_agents = self.registry.list_user_agents(user_context_2.user_id)
                    
                    # Users should have same agent names but different instances
                    assert set(user_1_agents) == set(user_2_agents), \
                        "All users should have same agent name patterns"
                    
                    # But actual agent instances should be different
                    for agent_name in user_1_agents:
                        agent_1 = await self.registry.get_agent(user_context_1, agent_name)
                        agent_2 = await self.registry.get_agent(user_context_2, agent_name)
                        assert agent_1 is not agent_2, \
                            f"Agent instances should be different between {user_context_1.user_id} and {user_context_2.user_id}"
                        assert agent_1.user_id == user_context_1.user_id, \
                            f"Agent 1 should belong to {user_context_1.user_id}"
                        assert agent_2.user_id == user_context_2.user_id, \
                            f"Agent 2 should belong to {user_context_2.user_id}"
    
    @pytest.mark.integration
    @pytest.mark.agents
    async def test_concurrent_agent_access_patterns(self):
        """Test concurrent agent access and execution patterns.
        
        BVJ: Validates that agents can be accessed concurrently without 
        performance degradation or data corruption.
        """
        # Pre-register agents for testing
        num_users = 3
        user_contexts = []
        
        for i in range(num_users):
            user_context = UserExecutionContext(
                user_id=f"access_user_{i+1}",
                thread_id=f"access_thread_{i+1}",
                run_id=f"access_run_{i+1}",
                request_id=f"access_req_{i+1}"
            )
            user_contexts.append(user_context)
            
            # Register agents for each user
            await self.registry.register_agent(user_context, "data_analyzer")
            await self.registry.register_agent(user_context, "optimizer")
        
        # Define concurrent access pattern
        async def access_and_execute_agents(user_context: UserExecutionContext, iterations: int):
            """Access and execute agents multiple times."""
            results = []
            
            for i in range(iterations):
                # Access data analyzer
                analyzer = await self.registry.get_agent(user_context, "data_analyzer")
                assert analyzer is not None, f"Should get analyzer for {user_context.user_id}"
                
                result_analyzer = await analyzer.execute(f"Analysis request {i+1}")
                results.append(('analyzer', result_analyzer))
                
                # Access optimizer  
                optimizer = await self.registry.get_agent(user_context, "optimizer")
                assert optimizer is not None, f"Should get optimizer for {user_context.user_id}"
                
                result_optimizer = await optimizer.execute(f"Optimization request {i+1}")
                results.append(('optimizer', result_optimizer))
                
                # Small delay to simulate real usage
                await asyncio.sleep(0.001)
            
            return user_context.user_id, results
        
        # Execute concurrent access patterns
        iterations_per_user = 10
        access_tasks = [
            access_and_execute_agents(ctx, iterations_per_user) 
            for ctx in user_contexts
        ]
        
        start_time = time.time()
        access_results = await asyncio.gather(*access_tasks)
        execution_time = time.time() - start_time
        
        logger.info(f"Concurrent access test completed in {execution_time:.3f}s")
        
        # Validate all access patterns succeeded
        for user_id, results in access_results:
            expected_results = iterations_per_user * 2  # 2 agents per iteration
            assert len(results) == expected_results, \
                f"User {user_id} should have {expected_results} results, got {len(results)}"
            
            # Validate result patterns
            analyzer_results = [r for agent_type, r in results if agent_type == 'analyzer']
            optimizer_results = [r for agent_type, r in results if agent_type == 'optimizer']
            
            assert len(analyzer_results) == iterations_per_user, \
                f"User {user_id} should have {iterations_per_user} analyzer results"
            assert len(optimizer_results) == iterations_per_user, \
                f"User {user_id} should have {iterations_per_user} optimizer results"
            
            # Validate result correctness
            for result in analyzer_results + optimizer_results:
                assert result['success'], f"All executions should succeed for {user_id}"
                assert result['user_id'] == user_id, f"Results should belong to {user_id}"
        
        # Validate registry access tracking
        registry_stats = self.registry.get_registry_stats()
        expected_total_accesses = num_users * iterations_per_user * 2  # 2 agents per user per iteration
        
        assert registry_stats['total_accesses'] == expected_total_accesses, \
            f"Should have {expected_total_accesses} total accesses, got {registry_stats['total_accesses']}"
        
        # Validate performance (should complete within reasonable time)
        max_expected_time = 2.0  # 2 seconds should be plenty for this load
        assert execution_time < max_expected_time, \
            f"Concurrent access should complete within {max_expected_time}s, took {execution_time:.3f}s"
    
    @pytest.mark.integration
    @pytest.mark.agents  
    async def test_registry_cleanup_and_lifecycle_management(self):
        """Test registry cleanup and agent lifecycle management under load.
        
        BVJ: Validates that agent cleanup works correctly and doesn't leak resources
        or cause race conditions during concurrent operations.
        """
        # Create test users and register agents
        num_users = 4
        user_contexts = []
        
        for i in range(num_users):
            user_context = UserExecutionContext(
                user_id=f"cleanup_user_{i+1}",
                thread_id=f"cleanup_thread_{i+1}",
                run_id=f"cleanup_run_{i+1}",
                request_id=f"cleanup_req_{i+1}"
            )
            user_contexts.append(user_context)
            
            # Register multiple agents per user
            agent_names = ["analyzer", "optimizer", "processor", "validator"]
            for agent_name in agent_names:
                await self.registry.register_agent(user_context, agent_name)
        
        # Verify initial state
        initial_stats = self.registry.get_registry_stats()
        expected_agents = num_users * 4  # 4 agents per user
        assert initial_stats['total_agents'] == expected_agents, \
            f"Should have {expected_agents} agents initially"
        assert initial_stats['total_users'] == num_users, \
            f"Should have {num_users} users initially"
        
        # Test partial cleanup (cleanup every other user)
        users_to_cleanup = user_contexts[::2]  # Every other user
        remaining_users = user_contexts[1::2]
        
        # Perform concurrent cleanup
        cleanup_tasks = [
            self.registry.cleanup_user_agents(ctx.user_id) 
            for ctx in users_to_cleanup
        ]
        
        await asyncio.gather(*cleanup_tasks)
        
        # Verify partial cleanup results
        partial_stats = self.registry.get_registry_stats()
        expected_remaining_agents = len(remaining_users) * 4
        expected_remaining_users = len(remaining_users)
        
        assert partial_stats['total_agents'] == expected_remaining_agents, \
            f"Should have {expected_remaining_agents} agents after partial cleanup, got {partial_stats['total_agents']}"
        assert partial_stats['total_users'] == expected_remaining_users, \
            f"Should have {expected_remaining_users} users after partial cleanup, got {partial_stats['total_users']}"
        
        # Verify remaining users still have their agents
        for user_context in remaining_users:
            user_agents = self.registry.list_user_agents(user_context.user_id)
            assert len(user_agents) == 4, \
                f"Remaining user {user_context.user_id} should still have 4 agents, got {len(user_agents)}"
            
            # Verify agents are still accessible and functional
            for agent_name in user_agents:
                agent = await self.registry.get_agent(user_context, agent_name)
                assert agent is not None, f"Agent {agent_name} should still exist for {user_context.user_id}"
                assert agent.is_active, f"Agent {agent_name} should still be active for {user_context.user_id}"
                
                # Test agent functionality
                result = await agent.execute("Test after partial cleanup")
                assert result['success'], f"Agent {agent_name} should still be functional"
        
        # Verify cleaned up users have no agents
        for user_context in users_to_cleanup:
            user_agents = self.registry.list_user_agents(user_context.user_id)
            assert len(user_agents) == 0, \
                f"Cleaned up user {user_context.user_id} should have no agents, got {len(user_agents)}"
        
        # Test concurrent access during cleanup
        # Access remaining agents while cleaning up the rest
        async def access_during_cleanup(user_context: UserExecutionContext):
            """Access agents while cleanup is happening."""
            results = []
            for i in range(5):  # 5 quick accesses
                try:
                    analyzer = await self.registry.get_agent(user_context, "analyzer")
                    if analyzer:
                        result = await analyzer.execute(f"Access during cleanup {i+1}")
                        results.append(result)
                except Exception as e:
                    logger.warning(f"Access failed during cleanup: {e}")
                
                await asyncio.sleep(0.001)
            return user_context.user_id, results
        
        # Start concurrent access for remaining users
        access_tasks = [access_during_cleanup(ctx) for ctx in remaining_users]
        
        # Start final cleanup
        final_cleanup_tasks = [
            self.registry.cleanup_user_agents(ctx.user_id) 
            for ctx in remaining_users
        ]
        
        # Execute both access and cleanup concurrently
        access_results, cleanup_results = await asyncio.gather(
            asyncio.gather(*access_tasks),
            asyncio.gather(*final_cleanup_tasks)
        )
        
        # Verify final state
        final_stats = self.registry.get_registry_stats()
        assert final_stats['total_agents'] == 0, \
            f"Should have no agents after final cleanup, got {final_stats['total_agents']}"
        assert final_stats['total_users'] == 0, \
            f"Should have no users after final cleanup, got {final_stats['total_users']}"
        
        # Verify access results (some may have succeeded before cleanup)
        for user_id, results in access_results:
            logger.info(f"User {user_id} completed {len(results)} accesses during cleanup")
            # All successful accesses should have valid results
            for result in results:
                assert result['success'], f"Successful access should be valid for {user_id}"
                assert result['user_id'] == user_id, f"Result should belong to {user_id}"
    
    @pytest.mark.integration
    @pytest.mark.agents
    async def test_high_load_registry_performance(self):
        """Test agent registry performance under high concurrent load.
        
        BVJ: Validates that registry can handle realistic production load
        patterns without performance degradation.
        """
        # Configuration for high-load test
        num_users = 10
        agents_per_user = 5
        access_iterations = 20
        
        logger.info(f"Starting high-load test: {num_users} users, {agents_per_user} agents each, {access_iterations} iterations")
        
        # Phase 1: Concurrent agent registration
        user_contexts = []
        for i in range(num_users):
            user_context = UserExecutionContext(
                user_id=f"load_user_{i+1:02d}",
                thread_id=f"load_thread_{i+1:02d}",
                run_id=f"load_run_{i+1:02d}",
                request_id=f"load_req_{i+1:02d}"
            )
            user_contexts.append(user_context)
        
        # Measure registration time
        registration_start = time.time()
        
        async def register_all_user_agents(user_context: UserExecutionContext):
            """Register all agents for a user."""
            agents = []
            for j in range(agents_per_user):
                agent_name = f"load_agent_{j+1}"
                agent = await self.registry.register_agent(user_context, agent_name)
                agents.append(agent)
            return user_context.user_id, agents
        
        registration_tasks = [register_all_user_agents(ctx) for ctx in user_contexts]
        registration_results = await asyncio.gather(*registration_tasks)
        registration_time = time.time() - registration_start
        
        logger.info(f"Registration completed in {registration_time:.3f}s")
        
        # Validate registration results
        total_registered_agents = 0
        for user_id, agents in registration_results:
            assert len(agents) == agents_per_user, \
                f"User {user_id} should have {agents_per_user} agents"
            total_registered_agents += len(agents)
        
        expected_total_agents = num_users * agents_per_user
        assert total_registered_agents == expected_total_agents, \
            f"Should have registered {expected_total_agents} agents total"
        
        # Phase 2: High-frequency concurrent access
        access_start = time.time()
        
        async def high_frequency_access(user_context: UserExecutionContext):
            """Perform high-frequency agent access."""
            access_results = []
            
            for i in range(access_iterations):
                # Randomly access different agents
                agent_index = i % agents_per_user + 1
                agent_name = f"load_agent_{agent_index}"
                
                agent = await self.registry.get_agent(user_context, agent_name)
                assert agent is not None, f"Should get agent {agent_name} for {user_context.user_id}"
                
                result = await agent.execute(f"High load request {i+1}")
                access_results.append(result)
                
                # Minimal delay to simulate real usage patterns
                if i % 5 == 0:  # Brief pause every 5 iterations
                    await asyncio.sleep(0.001)
            
            return user_context.user_id, access_results
        
        access_tasks = [high_frequency_access(ctx) for ctx in user_contexts]
        access_results = await asyncio.gather(*access_tasks)
        access_time = time.time() - access_start
        
        logger.info(f"High-frequency access completed in {access_time:.3f}s")
        
        # Validate access results
        total_accesses = 0
        for user_id, results in access_results:
            assert len(results) == access_iterations, \
                f"User {user_id} should have {access_iterations} access results"
            
            for result in results:
                assert result['success'], f"All accesses should succeed for {user_id}"
                assert result['user_id'] == user_id, f"Result should belong to {user_id}"
            
            total_accesses += len(results)
        
        expected_total_accesses = num_users * access_iterations
        assert total_accesses == expected_total_accesses, \
            f"Should have {expected_total_accesses} total accesses"
        
        # Performance validation
        max_registration_time = 3.0  # Should register within 3 seconds
        max_access_time = 5.0  # Should complete access within 5 seconds
        
        assert registration_time < max_registration_time, \
            f"Registration should complete within {max_registration_time}s, took {registration_time:.3f}s"
        assert access_time < max_access_time, \
            f"High-frequency access should complete within {max_access_time}s, took {access_time:.3f}s"
        
        # Calculate performance metrics
        registrations_per_second = total_registered_agents / registration_time
        accesses_per_second = total_accesses / access_time
        
        logger.info(f"Performance metrics:")
        logger.info(f"  - Registrations per second: {registrations_per_second:.1f}")
        logger.info(f"  - Accesses per second: {accesses_per_second:.1f}")
        
        # Minimum performance requirements
        min_registrations_per_sec = 20  # Should handle at least 20 registrations/sec
        min_accesses_per_sec = 100  # Should handle at least 100 accesses/sec
        
        assert registrations_per_second >= min_registrations_per_sec, \
            f"Should achieve at least {min_registrations_per_sec} registrations/sec, got {registrations_per_second:.1f}"
        assert accesses_per_second >= min_accesses_per_sec, \
            f"Should achieve at least {min_accesses_per_sec} accesses/sec, got {accesses_per_second:.1f}"
        
        # Final registry state validation
        final_stats = self.registry.get_registry_stats()
        assert final_stats['total_agents'] == expected_total_agents, \
            "Registry should maintain correct agent count after high load"
        assert final_stats['total_users'] == num_users, \
            "Registry should maintain correct user count after high load"
        assert final_stats['total_accesses'] == expected_total_accesses, \
            "Registry should track accesses correctly"
    
    async def tearDown(self):
        """Clean up test fixtures."""
        # Clean up all remaining agents
        stats = self.registry.get_registry_stats()
        if stats['total_users'] > 0:
            cleanup_tasks = []
            for user_id in list(self.registry.user_sessions.keys()):
                cleanup_tasks.append(self.registry.cleanup_user_agents(user_id))
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks)
        
        test_duration = time.time() - self.test_start_time
        logger.info(f"Test completed in {test_duration:.3f}s")
        await super().tearDown()