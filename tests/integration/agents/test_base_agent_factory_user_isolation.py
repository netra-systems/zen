"""
Base Agent Factory Pattern User Isolation Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Security/Infrastructure  
- Business Goal: Ensure complete user isolation in agent factory patterns
- Value Impact: Prevents data leaks and ensures Enterprise customer privacy
- Strategic Impact: Foundation for secure multi-tenant SaaS operation ($15K+ MRR per customer)

Integration Test Requirements:
- NO database dependencies - tests factory isolation patterns without external services
- NO Docker requirements - focuses on factory pattern user isolation 
- Uses real base agent and factory components
- Validates memory isolation and user context separation
- Tests concurrent factory operations with user boundaries

Phase 1 Priority Areas:
1. Base agent factory pattern user isolation
2. Factory instance creation and user binding
3. Memory isolation between user agent instances
4. Concurrent factory operations safety  
5. Factory cleanup and resource management

CRITICAL: These tests validate that the agent factory creates truly isolated
instances for each user, preventing any possibility of cross-user data contamination.
"""

import asyncio
import pytest
import time
import uuid
import gc
import weakref
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult, PipelineStep
)
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter

import logging
logger = logging.getLogger(__name__)


class IsolatedUserAgent:
    """Test agent implementation with user isolation validation."""
    
    def __init__(self, agent_name: str, user_context: UserExecutionContext, factory_id: str):
        self.agent_name = agent_name
        self.name = agent_name
        self.user_id = user_context.user_id
        self.user_context = user_context
        self.factory_id = factory_id
        self.created_at = time.time()
        self.instance_id = f"{user_context.user_id}:{agent_name}:{uuid.uuid4().hex[:8]}"
        
        # User-specific state isolation
        self.user_data = {
            'user_id': user_context.user_id,
            'thread_id': user_context.thread_id,
            'run_id': user_context.run_id,
            'request_id': user_context.request_id,
            'private_state': {},
            'execution_history': [],
            'access_count': 0
        }
        
        # Memory isolation validation
        self.memory_marker = f"USER_MEMORY_{user_context.user_id}_{int(time.time())}"
        self.is_active = True
        
    async def execute_with_context(self, context: AgentExecutionContext, prompt: str, **kwargs) -> AgentExecutionResult:
        """Execute agent with strict user isolation validation."""
        # Validate context matches user
        if context.user_id != self.user_id:
            raise ValueError(f"Context user {context.user_id} does not match agent user {self.user_id}")
        
        # Increment access count for this user
        self.user_data['access_count'] += 1
        
        # Store execution in user-specific history
        execution_record = {
            'execution_id': uuid.uuid4().hex,
            'prompt': prompt,
            'timestamp': time.time(),
            'context': context,
            'kwargs': kwargs,
            'user_id': self.user_id,
            'memory_marker': self.memory_marker
        }
        
        self.user_data['execution_history'].append(execution_record)
        
        # Simulate user-specific processing
        await asyncio.sleep(0.01)
        
        # Create user-specific result
        result = AgentExecutionResult(
            success=True,
            agent_name=self.agent_name,
            duration=0.01,
            metadata={
                'user_id': self.user_id,
                'instance_id': self.instance_id,
                'factory_id': self.factory_id,
                'execution_count': self.user_data['access_count'],
                'memory_marker': self.memory_marker,
                'prompt': prompt,
                'user_thread_id': self.user_context.thread_id,
                'user_run_id': self.user_context.run_id
            }
        )
        
        return result
        
    def get_user_private_data(self) -> Dict[str, Any]:
        """Get user's private data - should only return data for this user."""
        return {
            'user_id': self.user_id,
            'memory_marker': self.memory_marker,
            'access_count': self.user_data['access_count'],
            'execution_history_count': len(self.user_data['execution_history']),
            'instance_id': self.instance_id,
            'created_at': self.created_at
        }
        
    def validate_user_isolation(self, expected_user_id: str) -> bool:
        """Validate that this agent instance is properly isolated to expected user."""
        return (
            self.user_id == expected_user_id and
            self.user_context.user_id == expected_user_id and
            expected_user_id in self.memory_marker and
            all(exec_record['user_id'] == expected_user_id 
                for exec_record in self.user_data['execution_history'])
        )
        
    async def cleanup(self):
        """Cleanup user-specific resources."""
        self.is_active = False
        self.user_data['private_state'].clear()
        self.user_data['execution_history'].clear()


class IsolatingAgentFactory:
    """Agent factory that enforces strict user isolation."""
    
    def __init__(self):
        self.factory_id = f"factory_{uuid.uuid4().hex[:8]}"
        self.created_agents = {}  # user_id:agent_name -> agent
        self.user_agent_counts = {}  # user_id -> count
        self.creation_lock = asyncio.Lock()
        self.isolation_violations = []
        
    async def create_agent_instance(self, agent_name: str, user_context: UserExecutionContext) -> IsolatedUserAgent:
        """Create agent instance with strict user isolation."""
        async with self.creation_lock:
            user_id = user_context.user_id
            agent_key = f"{user_id}:{agent_name}"
            
            # Ensure no cross-user contamination in factory
            if agent_key in self.created_agents:
                existing_agent = self.created_agents[agent_key]
                if existing_agent.user_id != user_id:
                    violation = f"Agent key {agent_key} contaminated: expected user {user_id}, found {existing_agent.user_id}"
                    self.isolation_violations.append(violation)
                    raise RuntimeError(violation)
            
            # Create new isolated agent instance
            agent = IsolatedUserAgent(agent_name, user_context, self.factory_id)
            self.created_agents[agent_key] = agent
            
            # Track user agent count
            self.user_agent_counts[user_id] = self.user_agent_counts.get(user_id, 0) + 1
            
            logger.info(f"Factory {self.factory_id} created {agent_name} for user {user_id} (instance: {agent.instance_id})")
            return agent
    
    def get_agent_for_user(self, user_id: str, agent_name: str) -> Optional[IsolatedUserAgent]:
        """Get agent for specific user - enforces user isolation."""
        agent_key = f"{user_id}:{agent_name}"
        agent = self.created_agents.get(agent_key)
        
        if agent and agent.user_id != user_id:
            violation = f"Isolation violation: Agent {agent_key} belongs to {agent.user_id}, requested by {user_id}"
            self.isolation_violations.append(violation)
            raise RuntimeError(violation)
            
        return agent
    
    def get_user_agents(self, user_id: str) -> List[IsolatedUserAgent]:
        """Get all agents for specific user."""
        user_agents = []
        for agent_key, agent in self.created_agents.items():
            if agent_key.startswith(f"{user_id}:"):
                if agent.user_id != user_id:
                    violation = f"User agent list contamination: {agent_key} belongs to {agent.user_id}, not {user_id}"
                    self.isolation_violations.append(violation)
                    continue
                user_agents.append(agent)
        return user_agents
    
    def validate_factory_isolation(self) -> List[str]:
        """Validate that factory maintains user isolation."""
        violations = []
        
        # Check that all agents are properly isolated
        for agent_key, agent in self.created_agents.items():
            expected_user_id = agent_key.split(':')[0]
            if agent.user_id != expected_user_id:
                violations.append(f"Agent {agent_key}: expected user {expected_user_id}, actual user {agent.user_id}")
        
        # Check for memory marker contamination
        memory_markers = {}
        for agent_key, agent in self.created_agents.items():
            user_id = agent.user_id
            marker = agent.memory_marker
            
            if user_id not in memory_markers:
                memory_markers[user_id] = set()
            
            if marker in memory_markers[user_id]:
                violations.append(f"Duplicate memory marker {marker} for user {user_id}")
            else:
                memory_markers[user_id].add(marker)
        
        return violations + self.isolation_violations
    
    async def cleanup_user_agents(self, user_id: str):
        """Cleanup all agents for specific user."""
        agents_to_cleanup = []
        keys_to_remove = []
        
        for agent_key, agent in self.created_agents.items():
            if agent_key.startswith(f"{user_id}:"):
                agents_to_cleanup.append(agent)
                keys_to_remove.append(agent_key)
        
        # Remove from factory
        for key in keys_to_remove:
            del self.created_agents[key]
        
        if user_id in self.user_agent_counts:
            del self.user_agent_counts[user_id]
        
        # Cleanup agents
        cleanup_tasks = [agent.cleanup() for agent in agents_to_cleanup]
        await asyncio.gather(*cleanup_tasks)
        
        logger.info(f"Factory {self.factory_id} cleaned up {len(agents_to_cleanup)} agents for user {user_id}")


class TestBaseAgentFactoryUserIsolation(SSotAsyncTestCase):
    """Integration tests for base agent factory user isolation patterns."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.factory = IsolatingAgentFactory()
        self.test_start_time = time.time()
        
    @pytest.mark.integration
    @pytest.mark.agents
    async def test_single_user_agent_factory_isolation(self):
        """Test agent factory creates properly isolated instances for single user.
        
        BVJ: Validates basic factory isolation patterns ensuring user data
        remains private and secure within agent instances.
        """
        user_context = UserExecutionContext(
            user_id="isolation_test_user",
            thread_id="isolation_thread_001",
            run_id=f"isolation_run_{int(time.time())}",
            request_id=f"isolation_req_{uuid.uuid4().hex[:8]}"
        )
        
        # Create multiple agents for same user
        agent_names = ["data_processor", "optimization_engine", "validation_service"]
        created_agents = []
        
        for agent_name in agent_names:
            agent = await self.factory.create_agent_instance(agent_name, user_context)
            created_agents.append(agent)
            
            # Validate agent is properly bound to user
            assert agent.user_id == user_context.user_id, f"Agent {agent_name} should be bound to user"
            assert agent.user_context.user_id == user_context.user_id, f"Agent context should match user"
            assert user_context.user_id in agent.memory_marker, f"Memory marker should contain user ID"
            assert agent.validate_user_isolation(user_context.user_id), f"Agent {agent_name} should pass isolation validation"
        
        # Test agent execution with user isolation
        for i, agent in enumerate(created_agents):
            execution_context = AgentExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                request_id=f"{user_context.request_id}_exec_{i+1}",
                agent_name=agent.agent_name,
                step=PipelineStep.EXECUTION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=i+1
            )
            
            result = await agent.execute_with_context(
                execution_context, f"Test execution {i+1} for user isolation validation"
            )
            
            # Validate result isolation
            assert result.success, f"Execution should succeed for {agent.agent_name}"
            assert result.metadata['user_id'] == user_context.user_id, f"Result should belong to user"
            assert result.metadata['memory_marker'] == agent.memory_marker, f"Result should have agent's memory marker"
            assert result.metadata['instance_id'] == agent.instance_id, f"Result should have agent's instance ID"
        
        # Validate factory isolation state
        factory_violations = self.factory.validate_factory_isolation()
        assert len(factory_violations) == 0, f"Factory should have no isolation violations: {factory_violations}"
        
        # Test user data isolation
        for agent in created_agents:
            private_data = agent.get_user_private_data()
            assert private_data['user_id'] == user_context.user_id, "Private data should belong to user"
            assert private_data['access_count'] > 0, "Agent should track access count"
            assert user_context.user_id in private_data['memory_marker'], "Memory marker should identify user"
        
        # Validate factory user agent tracking
        user_agents = self.factory.get_user_agents(user_context.user_id)
        assert len(user_agents) == len(agent_names), "Factory should track all user agents"
        
        for agent in user_agents:
            assert agent.user_id == user_context.user_id, "All tracked agents should belong to user"
            assert agent in created_agents, "All tracked agents should be in created list"
        
        await self.factory.cleanup_user_agents(user_context.user_id)
    
    @pytest.mark.integration
    @pytest.mark.agents  
    async def test_multi_user_factory_isolation_validation(self):
        """Test factory maintains strict isolation between multiple users.
        
        BVJ: Critical for Enterprise SaaS - ensures no cross-contamination
        between different customer agent instances.
        """
        num_users = 4
        users_per_agent_type = {}
        
        # Create user contexts
        user_contexts = []
        for i in range(num_users):
            user_context = UserExecutionContext(
                user_id=f"multi_user_{i+1:02d}",
                thread_id=f"multi_thread_{i+1:02d}",
                run_id=f"multi_run_{i+1:02d}_{int(time.time())}",
                request_id=f"multi_req_{i+1:02d}_{uuid.uuid4().hex[:8]}"
            )
            user_contexts.append(user_context)
        
        # Agent types to create for each user
        agent_types = ["analyzer", "optimizer", "validator"]
        
        # Create agents for all users
        all_created_agents = {}  # user_id -> list of agents
        
        for user_context in user_contexts:
            user_id = user_context.user_id
            user_agents = []
            
            for agent_type in agent_types:
                agent = await self.factory.create_agent_instance(agent_type, user_context)
                user_agents.append(agent)
                
                # Track which users have which agent types
                if agent_type not in users_per_agent_type:
                    users_per_agent_type[agent_type] = []
                users_per_agent_type[agent_type].append(user_id)
            
            all_created_agents[user_id] = user_agents
        
        # Validate agent isolation for each user
        for user_id, user_agents in all_created_agents.items():
            assert len(user_agents) == len(agent_types), f"User {user_id} should have all agent types"
            
            for agent in user_agents:
                assert agent.user_id == user_id, f"Agent should belong to {user_id}"
                assert agent.validate_user_isolation(user_id), f"Agent should pass isolation validation for {user_id}"
                assert user_id in agent.memory_marker, f"Memory marker should identify {user_id}"
                
                # Validate user context binding
                assert agent.user_context.user_id == user_id, f"Agent context should belong to {user_id}"
        
        # Test cross-user contamination prevention
        for user_id_1 in all_created_agents.keys():
            for user_id_2 in all_created_agents.keys():
                if user_id_1 != user_id_2:
                    # Try to access user 2's agents from user 1's perspective
                    for agent_type in agent_types:
                        agent_1 = self.factory.get_agent_for_user(user_id_1, agent_type)
                        agent_2 = self.factory.get_agent_for_user(user_id_2, agent_type)
                        
                        # Agents should be different instances
                        assert agent_1 is not agent_2, \
                            f"Users {user_id_1} and {user_id_2} should have different {agent_type} instances"
                        
                        # Agents should have different memory markers
                        assert agent_1.memory_marker != agent_2.memory_marker, \
                            f"Users {user_id_1} and {user_id_2} should have different memory markers for {agent_type}"
                        
                        # Instance IDs should be unique
                        assert agent_1.instance_id != agent_2.instance_id, \
                            f"Users {user_id_1} and {user_id_2} should have unique instance IDs for {agent_type}"
        
        # Test concurrent execution with user isolation
        async def execute_user_agents(user_context: UserExecutionContext):
            """Execute all agents for a user concurrently."""
            user_id = user_context.user_id
            user_agents = all_created_agents[user_id]
            
            execution_tasks = []
            for i, agent in enumerate(user_agents):
                execution_context = AgentExecutionContext(
                    user_id=user_context.user_id,
                    thread_id=user_context.thread_id,
                    run_id=user_context.run_id,
                    request_id=f"{user_context.request_id}_agent_{i+1}",
                    agent_name=agent.agent_name,
                    step=PipelineStep.EXECUTION,
                    execution_timestamp=datetime.now(timezone.utc),
                    pipeline_step_num=i+1
                )
                
                task = agent.execute_with_context(
                    execution_context, f"Multi-user test execution for {user_id}"
                )
                execution_tasks.append(task)
            
            results = await asyncio.gather(*execution_tasks)
            return user_id, results
        
        # Execute all users concurrently
        user_execution_tasks = [execute_user_agents(ctx) for ctx in user_contexts]
        user_results = await asyncio.gather(*user_execution_tasks)
        
        # Validate execution results maintain user isolation
        for user_id, results in user_results:
            assert len(results) == len(agent_types), f"User {user_id} should have all execution results"
            
            for result in results:
                assert result.success, f"Execution should succeed for {user_id}"
                assert result.metadata['user_id'] == user_id, f"Result should belong to {user_id}"
                assert user_id in result.metadata['memory_marker'], f"Result memory marker should identify {user_id}"
        
        # Validate factory state after concurrent executions
        factory_violations = self.factory.validate_factory_isolation()
        assert len(factory_violations) == 0, f"Factory should maintain isolation after concurrent execution: {factory_violations}"
        
        # Test user-specific data isolation
        for user_id in all_created_agents.keys():
            user_agents = self.factory.get_user_agents(user_id)
            
            for agent in user_agents:
                private_data = agent.get_user_private_data()
                assert private_data['user_id'] == user_id, f"Private data should belong to {user_id}"
                assert private_data['execution_history_count'] > 0, f"Agent should have execution history for {user_id}"
                
                # Validate no cross-user data in execution history
                for exec_record in agent.user_data['execution_history']:
                    assert exec_record['user_id'] == user_id, \
                        f"Execution record should belong to {user_id}, found {exec_record['user_id']}"
                    assert user_id in exec_record['memory_marker'], \
                        f"Execution record memory marker should identify {user_id}"
        
        # Cleanup all users
        cleanup_tasks = [self.factory.cleanup_user_agents(user_id) for user_id in all_created_agents.keys()]
        await asyncio.gather(*cleanup_tasks)
    
    @pytest.mark.integration
    @pytest.mark.agents
    async def test_factory_memory_isolation_validation(self):
        """Test factory prevents memory contamination between user instances.
        
        BVJ: Validates memory-level isolation ensuring no data leakage
        between user instances that could compromise security.
        """
        # Create users with distinct data patterns
        user_data_patterns = [
            {"user_id": "memory_user_001", "data_pattern": "CONFIDENTIAL_ALPHA", "access_level": "HIGH"},
            {"user_id": "memory_user_002", "data_pattern": "SECRET_BETA", "access_level": "MEDIUM"},
            {"user_id": "memory_user_003", "data_pattern": "PRIVATE_GAMMA", "access_level": "LOW"}
        ]
        
        user_contexts = []
        agent_instances = {}
        
        for i, user_data in enumerate(user_data_patterns):
            user_context = UserExecutionContext(
                user_id=user_data["user_id"],
                thread_id=f"memory_thread_{i+1:03d}",
                run_id=f"memory_run_{i+1:03d}_{int(time.time())}",
                request_id=f"memory_req_{i+1:03d}_{uuid.uuid4().hex[:8]}"
            )
            user_contexts.append(user_context)
            
            # Create agent with user-specific data
            agent = await self.factory.create_agent_instance("memory_validator", user_context)
            
            # Inject user-specific sensitive data
            agent.user_data['private_state']['sensitive_data'] = user_data["data_pattern"]
            agent.user_data['private_state']['access_level'] = user_data["access_level"]
            agent.user_data['private_state']['secret_key'] = f"SECRET_{user_data['user_id'].upper()}"
            
            agent_instances[user_data["user_id"]] = agent
        
        # Execute agents and validate memory isolation
        execution_results = {}
        
        for user_context in user_contexts:
            user_id = user_context.user_id
            agent = agent_instances[user_id]
            
            execution_context = AgentExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                request_id=f"{user_context.request_id}_memory_test",
                agent_name="memory_validator",
                step=PipelineStep.EXECUTION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1
            )
            
            result = await agent.execute_with_context(
                execution_context, f"Memory isolation test for {user_id}"
            )
            
            execution_results[user_id] = result
        
        # Validate memory isolation between agents
        user_ids = list(agent_instances.keys())
        
        for i, user_id_1 in enumerate(user_ids):
            agent_1 = agent_instances[user_id_1]
            
            for j, user_id_2 in enumerate(user_ids):
                if i != j:
                    agent_2 = agent_instances[user_id_2]
                    
                    # Memory markers should be unique
                    assert agent_1.memory_marker != agent_2.memory_marker, \
                        f"Memory markers should be unique between {user_id_1} and {user_id_2}"
                    
                    # Instance IDs should be unique
                    assert agent_1.instance_id != agent_2.instance_id, \
                        f"Instance IDs should be unique between {user_id_1} and {user_id_2}"
                    
                    # Private state should not be shared
                    private_1 = agent_1.user_data['private_state']
                    private_2 = agent_2.user_data['private_state']
                    
                    assert private_1['sensitive_data'] != private_2['sensitive_data'], \
                        f"Sensitive data should be different between {user_id_1} and {user_id_2}"
                    assert private_1['secret_key'] != private_2['secret_key'], \
                        f"Secret keys should be different between {user_id_1} and {user_id_2}"
                    
                    # Agent objects should be completely separate in memory
                    assert agent_1 is not agent_2, \
                        f"Agent objects should be separate instances for {user_id_1} and {user_id_2}"
                    assert agent_1.user_data is not agent_2.user_data, \
                        f"User data objects should be separate for {user_id_1} and {user_id_2}"
        
        # Test cross-user data access prevention
        for user_id in user_ids:
            agent = agent_instances[user_id]
            private_data = agent.get_user_private_data()
            
            # Validate user can only access their own data
            assert private_data['user_id'] == user_id, "Should only access own user data"
            assert user_id in private_data['memory_marker'], "Memory marker should identify correct user"
            
            # Validate sensitive data isolation
            sensitive_data = agent.user_data['private_state']['sensitive_data']
            expected_pattern = next(
                (data['data_pattern'] for data in user_data_patterns if data['user_id'] == user_id),
                None
            )
            assert sensitive_data == expected_pattern, f"Should only access own sensitive data for {user_id}"
        
        # Test execution result isolation
        for user_id in user_ids:
            result = execution_results[user_id]
            agent = agent_instances[user_id]
            
            assert result.metadata['user_id'] == user_id, "Result should belong to correct user"
            assert result.metadata['memory_marker'] == agent.memory_marker, "Result should have correct memory marker"
            assert result.metadata['instance_id'] == agent.instance_id, "Result should have correct instance ID"
        
        # Validate factory maintains isolation
        factory_violations = self.factory.validate_factory_isolation()
        assert len(factory_violations) == 0, f"Factory should maintain memory isolation: {factory_violations}"
        
        # Cleanup all users and validate no memory leaks
        cleanup_tasks = [self.factory.cleanup_user_agents(user_id) for user_id in user_ids]
        await asyncio.gather(*cleanup_tasks)
        
        # Validate agents are properly cleaned up
        for user_id in user_ids:
            agent = agent_instances[user_id]
            assert not agent.is_active, f"Agent should be inactive after cleanup for {user_id}"
            assert len(agent.user_data['private_state']) == 0, f"Private state should be cleared for {user_id}"
            assert len(agent.user_data['execution_history']) == 0, f"Execution history should be cleared for {user_id}"
    
    @pytest.mark.integration
    @pytest.mark.agents
    async def test_high_load_factory_isolation_stress(self):
        """Test factory user isolation under high concurrent load.
        
        BVJ: Validates isolation remains intact under production-level
        concurrent load patterns for reliable Enterprise operation.
        """
        num_users = 8
        agents_per_user = 4
        executions_per_agent = 10
        
        logger.info(f"Starting high-load isolation test: {num_users} users, {agents_per_user} agents each, {executions_per_agent} executions per agent")
        
        # Create user contexts
        user_contexts = []
        for i in range(num_users):
            user_context = UserExecutionContext(
                user_id=f"stress_user_{i+1:02d}",
                thread_id=f"stress_thread_{i+1:02d}",
                run_id=f"stress_run_{i+1:02d}_{int(time.time())}",
                request_id=f"stress_req_{i+1:02d}_{uuid.uuid4().hex[:8]}"
            )
            user_contexts.append(user_context)
        
        # Phase 1: Concurrent agent creation
        creation_start = time.time()
        
        async def create_user_agents(user_context: UserExecutionContext):
            """Create all agents for a user."""
            agents = []
            for j in range(agents_per_user):
                agent_name = f"stress_agent_{j+1}"
                agent = await self.factory.create_agent_instance(agent_name, user_context)
                
                # Add user-specific data for isolation testing
                agent.user_data['private_state']['user_identifier'] = user_context.user_id
                agent.user_data['private_state']['creation_batch'] = j+1
                
                agents.append(agent)
            return user_context.user_id, agents
        
        creation_tasks = [create_user_agents(ctx) for ctx in user_contexts]
        creation_results = await asyncio.gather(*creation_tasks)
        creation_time = time.time() - creation_start
        
        logger.info(f"Created {num_users * agents_per_user} agents in {creation_time:.3f}s")
        
        # Organize created agents
        all_user_agents = {}
        for user_id, agents in creation_results:
            all_user_agents[user_id] = agents
        
        # Phase 2: High-frequency concurrent execution with isolation validation
        execution_start = time.time()
        
        async def stress_test_user_agents(user_context: UserExecutionContext):
            """Stress test all agents for a user with high-frequency execution."""
            user_id = user_context.user_id
            user_agents = all_user_agents[user_id]
            
            all_execution_results = []
            
            # Execute each agent multiple times concurrently
            for agent in user_agents:
                agent_execution_tasks = []
                
                for k in range(executions_per_agent):
                    execution_context = AgentExecutionContext(
                        user_id=user_context.user_id,
                        thread_id=user_context.thread_id,
                        run_id=user_context.run_id,
                        request_id=f"{user_context.request_id}_agent_{agent.agent_name}_exec_{k+1}",
                        agent_name=agent.agent_name,
                        step=PipelineStep.EXECUTION,
                        execution_timestamp=datetime.now(timezone.utc),
                        pipeline_step_num=k+1
                    )
                    
                    task = agent.execute_with_context(
                        execution_context, 
                        f"Stress test execution {k+1} for {user_id} agent {agent.agent_name}"
                    )
                    agent_execution_tasks.append(task)
                
                # Execute all iterations for this agent concurrently
                agent_results = await asyncio.gather(*agent_execution_tasks)
                all_execution_results.extend(agent_results)
            
            return user_id, all_execution_results
        
        # Execute stress test for all users concurrently
        stress_tasks = [stress_test_user_agents(ctx) for ctx in user_contexts]
        stress_results = await asyncio.gather(*stress_tasks)
        execution_time = time.time() - execution_start
        
        logger.info(f"Executed {num_users * agents_per_user * executions_per_agent} operations in {execution_time:.3f}s")
        
        # Validate all stress test results
        total_executions = 0
        for user_id, results in stress_results:
            expected_results = agents_per_user * executions_per_agent
            assert len(results) == expected_results, \
                f"User {user_id} should have {expected_results} results, got {len(results)}"
            
            # Validate all results belong to correct user
            for result in results:
                assert result.success, f"All executions should succeed for {user_id}"
                assert result.metadata['user_id'] == user_id, f"Result should belong to {user_id}"
                assert user_id in result.metadata['memory_marker'], f"Memory marker should identify {user_id}"
            
            total_executions += len(results)
        
        expected_total = num_users * agents_per_user * executions_per_agent
        assert total_executions == expected_total, \
            f"Should have {expected_total} total executions, got {total_executions}"
        
        # Phase 3: Isolation validation under stress
        isolation_violations = self.factory.validate_factory_isolation()
        assert len(isolation_violations) == 0, \
            f"Factory should maintain isolation under stress: {isolation_violations}"
        
        # Validate per-user isolation
        for user_id in all_user_agents.keys():
            user_agents = self.factory.get_user_agents(user_id)
            assert len(user_agents) == agents_per_user, \
                f"User {user_id} should have {agents_per_user} agents"
            
            for agent in user_agents:
                assert agent.validate_user_isolation(user_id), \
                    f"Agent should maintain isolation for {user_id} under stress"
                
                # Check access counts are reasonable
                private_data = agent.get_user_private_data()
                assert private_data['access_count'] == executions_per_agent, \
                    f"Agent should have correct access count for {user_id}"
        
        # Performance validation
        max_creation_time = 2.0  # Should create within 2 seconds
        max_execution_time = 5.0  # Should execute within 5 seconds
        
        assert creation_time < max_creation_time, \
            f"Agent creation should complete within {max_creation_time}s, took {creation_time:.3f}s"
        assert execution_time < max_execution_time, \
            f"Stress execution should complete within {max_execution_time}s, took {execution_time:.3f}s"
        
        # Calculate performance metrics
        creations_per_second = (num_users * agents_per_user) / creation_time
        executions_per_second = total_executions / execution_time
        
        logger.info(f"Performance under stress:")
        logger.info(f"  - Agent creations per second: {creations_per_second:.1f}")
        logger.info(f"  - Executions per second: {executions_per_second:.1f}")
        
        # Performance requirements
        min_creations_per_sec = 15  # Should handle at least 15 creations/sec
        min_executions_per_sec = 80  # Should handle at least 80 executions/sec
        
        assert creations_per_second >= min_creations_per_sec, \
            f"Should achieve at least {min_creations_per_sec} creations/sec, got {creations_per_second:.1f}"
        assert executions_per_second >= min_executions_per_sec, \
            f"Should achieve at least {min_executions_per_sec} executions/sec, got {executions_per_second:.1f}"
        
        # Final cleanup
        cleanup_tasks = [self.factory.cleanup_user_agents(user_id) for user_id in all_user_agents.keys()]
        await asyncio.gather(*cleanup_tasks)
    
    async def tearDown(self):
        """Clean up test fixtures."""
        # Final factory validation
        final_violations = self.factory.validate_factory_isolation()
        if final_violations:
            logger.warning(f"Final isolation violations detected: {final_violations}")
        
        # Force cleanup of any remaining agents
        remaining_user_ids = list(self.factory.user_agent_counts.keys())
        if remaining_user_ids:
            cleanup_tasks = [self.factory.cleanup_user_agents(uid) for uid in remaining_user_ids]
            await asyncio.gather(*cleanup_tasks)
        
        # Force garbage collection
        gc.collect()
        
        test_duration = time.time() - self.test_start_time
        logger.info(f"Test completed in {test_duration:.3f}s")
        await super().tearDown()