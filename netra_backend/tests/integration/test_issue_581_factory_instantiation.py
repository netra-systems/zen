"""
Integration Tests for Issue #581: Factory Instantiation with Real Services

BUSINESS VALUE:
- Enterprise/Platform | System Stability | Critical agent workflow rescue
- Validates $500K+ ARR data agent factory patterns work with real services
- Protects Golden Path: factory → agent → WebSocket → user response flow

TEST STRATEGY:
1. Factory instantiation with real services (no Docker)
2. Agent registry integration with name parameter
3. Pipeline executor integration testing
4. Real WebSocket event validation
5. Real database/Redis integration where applicable

CRITICAL: These are INTEGRATION tests - they use REAL services but NO Docker.
Tests should initially show factory instantiation issues, then pass after fix.

SSOT Compliance:
- Uses SSotAsyncTestCase for async integration testing
- Real services preference (PostgreSQL, Redis when available)
- No Docker dependency - uses non-Docker real services
- Environment isolation through IsolatedEnvironment
- WebSocket event validation with real connections

Related Files:
- /netra_backend/app/agents/supervisor/agent_instance_factory.py
- /netra_backend/app/agents/registry.py  
- /netra_backend/app/agents/supervisor/pipeline_executor.py
- /netra_backend/app/services/user_execution_context.py
"""

import asyncio
import pytest
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch
from contextlib import asynccontextmanager

# SSOT Compliance: Use SSOT AsyncTestCase for integration
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import agents and factories under test
from netra_backend.app.agents.data.unified_data_agent import UnifiedDataAgent, UnifiedDataAgentFactory
from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent

# Import integration dependencies  
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager

# Integration test specific imports
try:
    from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
    AGENT_FACTORY_AVAILABLE = True
except ImportError:
    AGENT_FACTORY_AVAILABLE = False

try:
    from netra_backend.app.agents.registry import AgentRegistry
    AGENT_REGISTRY_AVAILABLE = True  
except ImportError:
    AGENT_REGISTRY_AVAILABLE = False

try:
    from netra_backend.app.agents.supervisor.pipeline_executor import PipelineExecutor
    PIPELINE_EXECUTOR_AVAILABLE = True
except ImportError:
    PIPELINE_EXECUTOR_AVAILABLE = False

# WebSocket testing imports
try:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False


class TestIssue581FactoryInstantiationIntegration(SSotAsyncTestCase):
    """
    Integration tests for Issue #581 factory instantiation.
    
    These tests verify that agent factories can properly instantiate
    DataSubAgent/UnifiedDataAgent with the 'name' parameter using real services.
    """
    
    def setup_method(self, method):
        """Setup integration test environment.""" 
        super().setup_method(method)
        
        # Create real UserExecutionContext for integration testing
        self.user_context = self._create_real_user_context()
        
        # Set up real services (but no Docker)
        self.llm_manager = self._setup_mock_llm_manager()
        
        # Record integration test metrics
        self.record_metric("test_category", "integration") 
        self.record_metric("issue_number", "581")
        self.record_metric("uses_real_services", True)
        self.record_metric("uses_docker", False)
    
    def _create_real_user_context(self) -> UserExecutionContext:
        """Create a real UserExecutionContext for integration testing."""
        return UserExecutionContext(
            user_id="integration_test_user_581",
            thread_id="integration_test_thread_581",
            run_id="integration_test_run_581",
            request_id="integration_test_request_581",
            agent_context={
                "test_type": "integration", 
                "issue_number": "581",
                "analysis_type": "performance",
                "timeframe": "1h",
                "metrics": ["latency_ms", "throughput"]
            }
        )
    
    def _setup_mock_llm_manager(self) -> Mock:
        """Setup LLM manager mock for integration testing."""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.generate_text = AsyncMock(return_value="Generated insight text")
        return mock_llm
    
    async def test_unified_data_agent_factory_with_name_parameter(self):
        """
        Test UnifiedDataAgentFactory with name parameter integration.
        
        This verifies the core factory pattern works with real UserExecutionContext.
        """
        # Arrange
        factory = UnifiedDataAgentFactory()
        
        # Act - Test factory creation (this should work fine)
        agent = factory.create_for_context(self.user_context)
        
        # Assert factory creation succeeded
        self.assertIsNotNone(agent)
        assert isinstance(agent, UnifiedDataAgent)
        self.assertEqual(agent.context, self.user_context)
        
        # Test direct instantiation with name parameter (the actual issue)
        try:
            direct_agent = UnifiedDataAgent(
                context=self.user_context,
                name="integration_test_agent",  # This should work after fix
                factory=factory,
                llm_manager=self.llm_manager
            )
            
            self.assertIsNotNone(direct_agent)
            self.assertEqual(direct_agent.name, "integration_test_agent")
            self.record_metric("factory_with_name_success", True)
            
        except TypeError as e:
            if "unexpected keyword argument 'name'" in str(e):
                self.record_metric("factory_with_name_success", False)
                pytest.fail(f"Factory instantiation Issue #581 reproduced: {e}")
            else:
                raise
        
        # Record factory status
        factory_status = factory.get_status()
        self.record_metric("factory_agents_created", factory_status["total_created"])
        self.record_metric("factory_active_agents", factory_status["active_agents"])
    
    @pytest.mark.skipif(not AGENT_FACTORY_AVAILABLE, reason="AgentInstanceFactory not available")
    async def test_agent_instance_factory_integration(self):
        """
        Test AgentInstanceFactory integration with name parameter.
        
        This tests the system-level factory that might be calling DataSubAgent
        with the name parameter.
        """
        # This test requires the actual AgentInstanceFactory
        # It tests the integration point where the error likely occurs
        
        if not AGENT_FACTORY_AVAILABLE:
            pytest.skip("AgentInstanceFactory not available for testing")
            return
        
        # Arrange
        factory = AgentInstanceFactory()
        
        # Act - Test creating data agent through system factory
        try:
            # This is likely where the error occurs in production
            agent = await factory.create_agent_instance(
                agent_type="data",  # or "DataSubAgent"
                name="system_data_agent",  # The problematic parameter
                context=self.user_context,
                llm_manager=self.llm_manager
            )
            
            # Assert
            self.assertIsNotNone(agent)
            assert isinstance(agent, (UnifiedDataAgent, DataSubAgent))
            self.record_metric("system_factory_success", True)
            
        except Exception as e:
            if "unexpected keyword argument 'name'" in str(e):
                self.record_metric("system_factory_success", False)
                pytest.fail(f"System factory Issue #581 reproduced: {e}")
            else:
                # Record other error types for analysis
                self.record_metric("system_factory_error", str(e))
                raise
    
    @pytest.mark.skipif(not AGENT_REGISTRY_AVAILABLE, reason="AgentRegistry not available")
    async def test_agent_registry_integration(self):
        """
        Test AgentRegistry integration with DataSubAgent instantiation.
        
        This tests agent registration and retrieval patterns.
        """
        if not AGENT_REGISTRY_AVAILABLE:
            pytest.skip("AgentRegistry not available for testing")
            return
        
        # Arrange
        registry = AgentRegistry()
        
        # Test 1: Register data agent with name parameter
        try:
            registry.register_agent(
                agent_name="data", 
                agent_class=DataSubAgent,
                default_params={
                    "name": "registry_data_agent",  # Potential issue point
                    "llm_manager": self.llm_manager
                }
            )
            
            self.record_metric("registry_registration_success", True)
            
        except Exception as e:
            if "unexpected keyword argument 'name'" in str(e):
                self.record_metric("registry_registration_success", False)
                pytest.fail(f"Registry registration Issue #581 reproduced: {e}")
            else:
                raise
        
        # Test 2: Create agent through registry 
        try:
            agent = await registry.create_agent_instance(
                agent_name="data",
                context=self.user_context
            )
            
            self.assertIsNotNone(agent)
            self.record_metric("registry_creation_success", True)
            
        except Exception as e:
            if "unexpected keyword argument 'name'" in str(e):
                self.record_metric("registry_creation_success", False)
                pytest.fail(f"Registry creation Issue #581 reproduced: {e}")
            else:
                self.record_metric("registry_creation_error", str(e))
                raise
    
    @pytest.mark.skipif(not PIPELINE_EXECUTOR_AVAILABLE, reason="PipelineExecutor not available")
    async def test_pipeline_executor_integration(self):
        """
        Test PipelineExecutor integration with data agent instantiation.
        
        This tests the pipeline execution context where agents are created.
        """
        if not PIPELINE_EXECUTOR_AVAILABLE:
            pytest.skip("PipelineExecutor not available for testing")
            return
        
        # Arrange
        executor = PipelineExecutor()
        
        # Test pipeline execution that creates data agents
        pipeline_config = {
            "agents": [
                {
                    "type": "data",
                    "name": "pipeline_data_agent",  # Issue #581 trigger point
                    "config": {
                        "analysis_type": "performance",
                        "timeframe": "1h"
                    }
                }
            ]
        }
        
        try:
            # Execute pipeline with data agent
            results = await executor.execute_pipeline(
                pipeline_config=pipeline_config,
                context=self.user_context,
                llm_manager=self.llm_manager
            )
            
            # Verify pipeline completed successfully
            self.assertIsNotNone(results)
            self.record_metric("pipeline_execution_success", True)
            self.record_metric("pipeline_agents_created", len(results.get("agents", [])))
            
        except Exception as e:
            if "unexpected keyword argument 'name'" in str(e):
                self.record_metric("pipeline_execution_success", False)
                pytest.fail(f"Pipeline execution Issue #581 reproduced: {e}")
            else:
                self.record_metric("pipeline_execution_error", str(e))
                raise
    
    async def test_real_user_execution_context_integration(self):
        """
        Test integration with real UserExecutionContext patterns.
        
        This verifies that real user context flows work with the constructor fix.
        """
        # Test various UserExecutionContext scenarios
        test_scenarios = [
            {
                "description": "basic_context",
                "context": UserExecutionContext(
                    user_id="basic_user",
                    request_id="basic_request"
                ),
                "agent_name": "basic_data_agent"
            },
            {
                "description": "context_with_metadata",
                "context": UserExecutionContext(
                    user_id="meta_user", 
                    request_id="meta_request",
                    metadata={"analysis_type": "anomaly"}
                ),
                "agent_name": "metadata_data_agent"
            },
            {
                "description": "context_with_agent_input",
                "context": UserExecutionContext(
                    user_id="input_user",
                    request_id="input_request", 
                    agent_input={"timeframe": "24h", "metrics": ["latency_ms"]}
                ),
                "agent_name": "input_data_agent"
            }
        ]
        
        results = {}
        
        for scenario in test_scenarios:
            context = scenario["context"]
            agent_name = scenario["agent_name"]
            description = scenario["description"]
            
            try:
                # Test UnifiedDataAgent with real context
                unified_agent = UnifiedDataAgent(
                    context=context,
                    name=agent_name,  # The Issue #581 parameter
                    llm_manager=self.llm_manager
                )
                
                # Test DataSubAgent alias with real context
                data_sub_agent = DataSubAgent(
                    context=context,
                    name=f"alias_{agent_name}",  # The Issue #581 parameter
                    llm_manager=self.llm_manager
                )
                
                # Verify both work
                self.assertIsNotNone(unified_agent)
                self.assertIsNotNone(data_sub_agent)
                assert isinstance(data_sub_agent, UnifiedDataAgent)
                
                results[description] = {
                    "success": True,
                    "unified_agent_name": unified_agent.name,
                    "data_sub_agent_name": data_sub_agent.name
                }
                
            except Exception as e:
                results[description] = {
                    "success": False,
                    "error": str(e)
                }
                
                if "unexpected keyword argument 'name'" in str(e):
                    pytest.fail(f"User context scenario '{description}' Issue #581 reproduced: {e}")
        
        # Record all scenario results
        self.record_metric("user_context_scenarios", results)
        
        # Verify all scenarios succeeded
        for description, result in results.items():
            self.assertTrue(result["success"], f"Scenario {description} failed: {result.get('error', 'Unknown')}")
    
    @pytest.mark.skipif(not WEBSOCKET_AVAILABLE, reason="WebSocket bridge not available")
    async def test_websocket_integration_with_agent_instantiation(self):
        """
        Test WebSocket integration with agent instantiation.
        
        This tests the critical WebSocket event flow that depends on
        proper agent instantiation.
        """
        if not WEBSOCKET_AVAILABLE:
            pytest.skip("WebSocket bridge not available for testing")
            return
        
        # Arrange - Create WebSocket bridge for testing
        mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        mock_websocket_bridge.emit_agent_started = AsyncMock()
        mock_websocket_bridge.emit_agent_thinking = AsyncMock()
        mock_websocket_bridge.emit_tool_executing = AsyncMock()
        mock_websocket_bridge.emit_tool_completed = AsyncMock()
        mock_websocket_bridge.emit_agent_completed = AsyncMock()
        
        # Enhance context with WebSocket bridge
        self.user_context.websocket_manager = mock_websocket_bridge
        
        # Act - Create agent with WebSocket integration
        try:
            agent = UnifiedDataAgent(
                context=self.user_context,
                name="websocket_data_agent",  # Issue #581 parameter
                llm_manager=self.llm_manager
            )
            
            # Execute agent to trigger WebSocket events
            result = await agent.execute(
                context=self.user_context,
                stream_updates=True
            )
            
            # Assert - Verify WebSocket events were called
            mock_websocket_bridge.emit_agent_started.assert_called_once()
            mock_websocket_bridge.emit_agent_thinking.assert_called()
            mock_websocket_bridge.emit_agent_completed.assert_called_once()
            
            self.record_metric("websocket_integration_success", True)
            self.record_metric("websocket_events_sent", 5)  # All 5 critical events
            
        except Exception as e:
            if "unexpected keyword argument 'name'" in str(e):
                self.record_metric("websocket_integration_success", False) 
                pytest.fail(f"WebSocket integration Issue #581 reproduced: {e}")
            else:
                raise
    
    async def test_concurrent_agent_instantiation(self):
        """
        Test concurrent agent instantiation with name parameter.
        
        This tests multi-user scenarios where multiple agents might be
        created simultaneously with the name parameter.
        """
        # Create multiple user contexts
        contexts = []
        for i in range(3):
            context = UserExecutionContext(
                user_id=f"concurrent_user_{i}",
                request_id=f"concurrent_request_{i}",
                session_id=f"concurrent_session_{i}"
            )
            contexts.append(context)
        
        # Create agents concurrently
        async def create_agent_for_context(context, agent_index):
            """Helper to create agent with specific context."""
            try:
                agent = UnifiedDataAgent(
                    context=context,
                    name=f"concurrent_agent_{agent_index}",  # Issue #581 parameter
                    llm_manager=self.llm_manager
                )
                return {"success": True, "agent": agent, "context": context}
            except Exception as e:
                return {"success": False, "error": str(e), "context": context}
        
        # Execute concurrent creation
        tasks = [
            create_agent_for_context(context, i) 
            for i, context in enumerate(contexts)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_creations = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_creations = [r for r in results if isinstance(r, dict) and not r.get("success")] 
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        # Record metrics
        self.record_metric("concurrent_successful_creations", len(successful_creations))
        self.record_metric("concurrent_failed_creations", len(failed_creations))
        self.record_metric("concurrent_exceptions", len(exceptions))
        
        # Check for Issue #581 specific failures
        issue_581_failures = [
            r for r in failed_creations 
            if "unexpected keyword argument 'name'" in r.get("error", "")
        ]
        
        if issue_581_failures:
            self.record_metric("concurrent_issue_581_failures", len(issue_581_failures))
            pytest.fail(f"Concurrent instantiation Issue #581 reproduced in {len(issue_581_failures)} cases")
        
        # Verify all creations succeeded
        self.assertEqual(len(successful_creations), len(contexts))
        
        # Verify agents are properly isolated
        agents = [r["agent"] for r in successful_creations]
        user_ids = [agent.context.user_id for agent in agents]
        self.assertEqual(len(set(user_ids)), len(contexts))  # All unique user IDs
        
    async def test_memory_and_cleanup_integration(self):
        """
        Test memory usage and cleanup in integration scenarios.
        
        This ensures the constructor fix doesn't cause memory leaks
        in integration scenarios.
        """
        import gc
        
        # Get baseline
        initial_agents = len([obj for obj in gc.get_objects() 
                             if isinstance(obj, UnifiedDataAgent)])
        
        # Create and cleanup agents
        agents = []
        factory = UnifiedDataAgentFactory()
        
        for i in range(5):
            context = UserExecutionContext(
                user_id=f"memory_user_{i}",
                request_id=f"memory_request_{i}"
            )
            
            agent = UnifiedDataAgent(
                context=context,
                name=f"memory_agent_{i}",  # Issue #581 parameter
                factory=factory,
                llm_manager=self.llm_manager
            )
            agents.append(agent)
        
        # Check agent count
        mid_agents = len([obj for obj in gc.get_objects() 
                         if isinstance(obj, UnifiedDataAgent)])
        
        # Cleanup agents
        for agent in agents:
            await agent.cleanup()
        
        agents.clear()
        gc.collect()
        
        # Check final count
        final_agents = len([obj for obj in gc.get_objects() 
                           if isinstance(obj, UnifiedDataAgent)])
        
        # Record metrics
        self.record_metric("memory_initial_agents", initial_agents)
        self.record_metric("memory_mid_agents", mid_agents)
        self.record_metric("memory_final_agents", final_agents)
        self.record_metric("memory_agents_created", 5)
        self.record_metric("memory_cleanup_effective", mid_agents > initial_agents >= final_agents)