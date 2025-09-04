"""
Integration tests for Agent Architecture Consolidation.

Tests the unified agent registry and DataSubAgent SSOT implementation.
Validates proper execution order and concurrent request handling.
"""

import pytest
import asyncio
import time
from typing import Dict, List, Any
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import threading

# Test framework imports
import unittest
from unittest.mock import MagicMock

# Mock Factory replacement
class MockFactory:
    def create_llm_manager(self):
        mock = MagicMock()
        mock.name = "MockLLMManager"
        return mock
    
    def create_tool_dispatcher(self):
        mock = MagicMock()
        mock.name = "MockToolDispatcher"
        return mock

# Use unittest base class
BaseTestCase = unittest.TestCase

# Core imports to test
from netra_backend.app.agents.supervisor.unified_agent_registry import (
    UnifiedAgentRegistry,
    get_unified_agent_registry,
    AgentMetadata
)
from netra_backend.app.agents.data_sub_agent import DataSubAgent
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestUnifiedAgentRegistry(BaseTestCase):
    """Test the UnifiedAgentRegistry SSOT implementation."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.registry = UnifiedAgentRegistry()
        self.mock_factory = MockFactory()
    
    def test_agent_class_registration(self):
        """Test agent class registration with metadata."""
        # Create mock agent class
        class MockAgent(BaseAgent):
            pass
        
        # Register agent
        self.registry.register_agent_class(
            agent_type='mock',
            agent_class=MockAgent,
            description='Mock agent for testing',
            category='test',
            execution_order=25
        )
        
        # Verify registration
        agent_class = self.registry.get_agent_class('mock')
        self.assertEqual(agent_class, MockAgent)
        
        # Check metadata
        metadata = self.registry.get_agent_metadata('mock')
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.name, 'mock')
        self.assertEqual(metadata.category, 'test')
        self.assertEqual(metadata.execution_order, 25)
    
    def test_execution_order_enforcement(self):
        """Test that Data agents execute before Optimization agents."""
        # Register agents with different orders
        class DataAgent(BaseAgent):
            pass
        
        class OptimizationAgent(BaseAgent):
            pass
        
        self.registry.register_agent_class('data', DataAgent)
        self.registry.register_agent_class('optimization', OptimizationAgent)
        
        # Get execution order
        order = self.registry.get_execution_order()
        
        # Data should come before optimization
        data_index = order.index('data')
        opt_index = order.index('optimization')
        self.assertLess(data_index, opt_index, "Data must execute before Optimization")
    
    def test_validate_execution_order(self):
        """Test execution order validation."""
        # Valid order (Data before Optimization)
        valid_sequence = ['triage', 'data', 'optimization', 'actions']
        self.assertTrue(self.registry.validate_execution_order(valid_sequence))
        
        # Invalid order (Optimization before Data)
        invalid_sequence = ['triage', 'optimization', 'data', 'actions']
        self.assertFalse(self.registry.validate_execution_order(invalid_sequence))
    
    def test_agent_discovery(self):
        """Test agent discovery functionality."""
        # Register multiple agents
        class TriageAgent(BaseAgent):
            pass
        class DataAgent(BaseAgent):
            pass
        class ReportingAgent(BaseAgent):
            pass
        
        self.registry.register_agent_class('triage', TriageAgent)
        self.registry.register_agent_class('data', DataAgent) 
        self.registry.register_agent_class('reporting', ReportingAgent)
        
        # Discover agents
        agents = self.registry.discover_agents()
        
        # Should be sorted by execution order
        self.assertEqual(len(agents), 3)
        self.assertIn('triage', agents)
        self.assertIn('data', agents)
        self.assertIn('reporting', agents)
    
    def test_category_filtering(self):
        """Test getting agents by category."""
        # Register agents in different categories
        class DataAgent1(BaseAgent):
            pass
        class DataAgent2(BaseAgent):
            pass
        class OptAgent(BaseAgent):
            pass
        
        self.registry.register_agent_class('data1', DataAgent1, category='data')
        self.registry.register_agent_class('data2', DataAgent2, category='data')
        self.registry.register_agent_class('opt1', OptAgent, category='optimization')
        
        # Get by category
        data_agents = self.registry.get_agents_by_category('data')
        self.assertEqual(len(data_agents), 2)
        self.assertIn('data1', data_agents)
        self.assertIn('data2', data_agents)
    
    def test_registry_freeze(self):
        """Test registry immutability after freeze."""
        class TestAgent(BaseAgent):
            pass
        
        # Register before freeze
        self.registry.register_agent_class('test1', TestAgent)
        
        # Freeze registry
        self.registry.freeze()
        self.assertTrue(self.registry.is_frozen())
        
        # Attempt to register after freeze should fail
        with self.assertRaises(RuntimeError) as context:
            self.registry.register_agent_class('test2', TestAgent)
        self.assertIn("frozen", str(context.exception).lower())
    
    def test_create_agent_instance(self):
        """Test agent instance creation."""
        # Register agent
        self.registry.register_agent_class('data', DataSubAgent)
        
        # Create mocks
        mock_llm = self.mock_factory.create_llm_manager()
        mock_dispatcher = self.mock_factory.create_tool_dispatcher()
        
        # Create instance
        instance = self.registry.create_agent_instance(
            'data',
            llm_manager=mock_llm,
            tool_dispatcher=mock_dispatcher
        )
        
        self.assertIsNotNone(instance)
        self.assertIsInstance(instance, DataSubAgent)
    
    def test_thread_safety(self):
        """Test concurrent access to registry."""
        results = {'errors': []}
        
        class TestAgent(BaseAgent):
            pass
        
        # Register agents
        for i in range(10):
            self.registry.register_agent_class(f'agent{i}', TestAgent)
        
        self.registry.freeze()
        
        def read_registry(thread_id):
            """Read from registry concurrently."""
            try:
                for _ in range(100):
                    # Multiple read operations
                    agents = self.registry.discover_agents()
                    for agent in agents:
                        cls = self.registry.get_agent_class(agent)
                        meta = self.registry.get_agent_metadata(agent)
                    order = self.registry.get_execution_order()
                    time.sleep(0.001)  # Small delay to increase contention
            except Exception as e:
                results['errors'].append(f"Thread {thread_id}: {e}")
        
        # Run concurrent reads
        threads = []
        for i in range(10):
            t = threading.Thread(target=read_registry, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # No errors should occur
        self.assertEqual(len(results['errors']), 0, f"Thread errors: {results['errors']}")
    
    def test_global_singleton(self):
        """Test global registry singleton pattern."""
        registry1 = get_unified_agent_registry()
        registry2 = get_unified_agent_registry()
        
        # Should be same instance
        self.assertIs(registry1, registry2)
        
        # Should be frozen after initialization
        self.assertTrue(registry1.is_frozen())
        
        # Should have default agents registered
        agents = registry1.discover_agents()
        self.assertIn('data', agents)
        self.assertIn('triage', agents)


class TestDataSubAgentConsolidation(BaseTestCase):
    """Test DataSubAgent SSOT implementation."""
    
    @pytest.mark.asyncio
    async def test_data_sub_agent_imports(self):
        """Test that DataSubAgent imports correctly from SSOT."""
        # Import should work without legacy files
        from netra_backend.app.agents.data_sub_agent import DataSubAgent
        
        # Should inherit from BaseAgent
        self.assertTrue(issubclass(DataSubAgent, BaseAgent))
    
    @pytest.mark.asyncio
    async def test_no_legacy_imports(self):
        """Test that legacy files are deleted and not importable."""
        # These imports should fail
        with self.assertRaises(ImportError):
            from netra_backend.app.agents.data_sub_agent.agent_core_legacy import DataSubAgent
        
        with self.assertRaises(ImportError):
            from netra_backend.app.agents.data_sub_agent.agent_legacy_massive import DataSubAgent
    
    @pytest.mark.asyncio  
    async def test_data_sub_agent_execution(self):
        """Test DataSubAgent execute with UserExecutionContext."""
        # Create mocks
        mock_factory = MockFactory()
        llm_manager = mock_factory.create_llm_manager()
        tool_dispatcher = mock_factory.create_tool_dispatcher()
        
        # Create agent
        agent = DataSubAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        # Create context
        context = UserExecutionContext(
            user_id="test_user",
            run_id="test_run",
            metadata={"user_request": "Analyze my data"}
        )
        
        # Mock execute
        with patch.object(agent, '_execute_core', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"success": True}
            
            result = await agent.execute(context, stream_updates=False)
            
            # Should have called _execute_core
            mock_execute.assert_called_once()
            self.assertEqual(result, {"success": True})


class TestAgentOrchestration(BaseTestCase):
    """Test agent orchestration with proper execution order."""
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_requests(self):
        """Test handling 50+ concurrent agent requests."""
        registry = get_unified_agent_registry()
        mock_factory = MockFactory()
        
        # Create shared resources
        llm_manager = mock_factory.create_llm_manager()
        
        async def create_and_execute_agent(user_id: str, agent_type: str):
            """Create and execute an agent for a user."""
            try:
                # Create per-request tool dispatcher
                tool_dispatcher = mock_factory.create_tool_dispatcher()
                
                # Create context
                context = UserExecutionContext(
                    user_id=user_id,
                    run_id=f"run_{user_id}_{agent_type}",
                    metadata={"agent_type": agent_type}
                )
                
                # Create agent instance
                agent = registry.create_agent_instance(
                    agent_type,
                    llm_manager=llm_manager,
                    tool_dispatcher=tool_dispatcher,
                    context=context
                )
                
                if agent:
                    # Mock execution
                    with patch.object(agent, 'execute', new_callable=AsyncMock) as mock_exec:
                        mock_exec.return_value = {"user": user_id, "agent": agent_type}
                        result = await agent.execute(context, stream_updates=False)
                        return result
                
                return None
                
            except Exception as e:
                logger.error(f"Error in concurrent test: {e}")
                return None
        
        # Create tasks for concurrent execution
        tasks = []
        for i in range(50):
            user_id = f"user_{i}"
            # Rotate through different agent types
            agent_types = ['triage', 'data', 'optimizations', 'actions']
            agent_type = agent_types[i % len(agent_types)]
            
            task = create_and_execute_agent(user_id, agent_type)
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results
        successful = [r for r in results if r and not isinstance(r, Exception)]
        errors = [r for r in results if isinstance(r, Exception)]
        
        # Most should succeed
        self.assertGreater(len(successful), 40, f"Too many failures: {len(errors)} errors")
        
        # Check user isolation
        user_ids = [r['user'] for r in successful if r]
        self.assertEqual(len(user_ids), len(set(user_ids)), "User ID collision detected")
    
    @pytest.mark.asyncio
    async def test_execution_order_in_workflow(self):
        """Test that agents execute in correct order during workflow."""
        execution_log = []
        
        # Create mock agents that log their execution
        class LoggingDataAgent(BaseAgent):
            async def _execute_core(self, context, **kwargs):
                execution_log.append('data')
                return {"data": "collected"}
        
        class LoggingOptimizationAgent(BaseAgent):
            async def _execute_core(self, context, **kwargs):
                execution_log.append('optimization')
                return {"optimization": "computed"}
        
        # Register agents
        registry = UnifiedAgentRegistry()
        registry.register_agent_class('data', LoggingDataAgent)
        registry.register_agent_class('optimization', LoggingOptimizationAgent)
        
        # Create instances
        mock_factory = MockFactory()
        llm = mock_factory.create_llm_manager()
        dispatcher = mock_factory.create_tool_dispatcher()
        
        data_agent = registry.create_agent_instance('data', llm, dispatcher)
        opt_agent = registry.create_agent_instance('optimization', llm, dispatcher)
        
        # Execute in workflow order
        context = UserExecutionContext("user1", "run1", {})
        
        # Execute according to proper order
        order = registry.get_execution_order()
        for agent_type in order:
            if agent_type == 'data':
                await data_agent.execute(context, stream_updates=False)
            elif agent_type == 'optimization':
                await opt_agent.execute(context, stream_updates=False)
        
        # Verify execution order
        self.assertEqual(execution_log, ['data', 'optimization'])


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])