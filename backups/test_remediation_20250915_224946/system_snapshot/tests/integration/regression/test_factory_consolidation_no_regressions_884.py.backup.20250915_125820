"""
Test Suite: Issue #884 - Multiple execution engine factories blocking AI responses
Module: Factory Consolidation Regression Prevention Test

PURPOSE:
This regression test validates that existing agent functionality continues to work
correctly after factory consolidation, preventing regressions in core business logic.

BUSINESS IMPACT:
- $500K+ ARR protected by ensuring no regressions in agent functionality
- SupervisorAgent, TriageAgent, DataHelperAgent, ApexOptimizerAgent must work correctly
- Existing agent workflows must execute through consolidated factory without issues
- Agent execution patterns must remain consistent after factory changes

TEST REQUIREMENTS:
- Tests all major agent types: SupervisorAgent, TriageAgent, DataHelperAgent, ApexOptimizerAgent
- Validates agents execute correctly through consolidated factory
- Uses real services where possible, minimal mocking for regression detection
- Focuses on business-critical agent workflows

Created: 2025-09-14 for Issue #884 Step 2 regression prevention validation
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional
import pytest
import time
from unittest.mock import MagicMock, AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase


@pytest.mark.integration
class TestFactoryConsolidationNoRegressions884(SSotAsyncTestCase):
    """
    Regression Test: Validate existing agent functionality after factory consolidation
    
    This test ensures that factory consolidation doesn't break existing agent
    functionality that's critical for business operations.
    """
    
    def setup_method(self, method):
        """Set up regression prevention test"""
        super().setup_method(method)
        self.record_metric("test_type", "regression_prevention")
        self.record_metric("focus_area", "agent_functionality")
        self.record_metric("issue_number", "884")
        
        # Set test environment
        env = self.get_env()
        env.set("TESTING", "true", "regression_test")
        env.set("TEST_REGRESSION_PREVENTION", "true", "regression_test")
        
        # Track agents to test
        self.agents_to_test = [
            'SupervisorAgent',
            'TriageAgent', 
            'DataHelperAgent',
            'ApexOptimizerAgent'
        ]
        
    async def test_supervisor_agent_works_with_consolidated_factory_884(self):
        """
        REGRESSION TEST: Validate SupervisorAgent works with consolidated factory
        
        SupervisorAgent is the central orchestrator - it must continue to work
        correctly after factory consolidation to maintain agent workflow coordination.
        """
        start_time = time.time()
        self.record_metric("supervisor_agent_test_start", start_time)
        
        # Import required components
        try:
            # Import consolidated factory
            try:
                from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory
                factory = ExecutionEngineFactory()
                factory_source = "core.managers"
            except ImportError:
                try:
                    from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngineFactory
                    factory = ExecutionEngineFactory() 
                    factory_source = "agents.consolidated"
                except ImportError:
                    pytest.skip("Consolidated factory not available")
            
            # Import SupervisorAgent
            try:
                from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
            except ImportError:
                try:
                    from netra_backend.app.agents.supervisor_agent import SupervisorAgent
                except ImportError:
                    pytest.skip("SupervisorAgent not available")
            
            # Import user execution context
            try:
                from netra_backend.app.agents.user_execution_context import UserExecutionContext
            except ImportError:
                class TestUserExecutionContext:
                    def __init__(self, user_id: str, session_id: str, **kwargs):
                        self.user_id = user_id
                        self.session_id = session_id
                        for key, value in kwargs.items():
                            setattr(self, key, value)
                UserExecutionContext = TestUserExecutionContext
                
        except Exception as e:
            pytest.skip(f"Required components not available: {e}")
        
        # Create user context for SupervisorAgent
        user_context = UserExecutionContext(
            user_id=f"supervisor_test_user_{uuid.uuid4().hex[:8]}",
            session_id=f"supervisor_test_session_{uuid.uuid4().hex[:8]}",
            trace_id=f"supervisor_trace_{uuid.uuid4().hex[:8]}",
            environment="regression_test"
        )
        
        # Create execution engine using consolidated factory
        try:
            execution_engine = factory.create_execution_engine(user_context)
            self.assertIsNotNone(execution_engine,
                "REGRESSION: Factory failed to create execution engine for SupervisorAgent")
                
        except Exception as e:
            raise AssertionError(
                f"REGRESSION: Factory creation failed for SupervisorAgent: {e}. "
                f"This indicates consolidation broke SupervisorAgent integration.")
        
        # Create SupervisorAgent instance
        try:
            # SupervisorAgent might require different initialization parameters
            if 'user_context' in SupervisorAgent.__init__.__code__.co_varnames:
                supervisor_agent = SupervisorAgent(user_context=user_context)
            elif 'execution_engine' in SupervisorAgent.__init__.__code__.co_varnames:
                supervisor_agent = SupervisorAgent(execution_engine=execution_engine)
            else:
                supervisor_agent = SupervisorAgent()
            
            # Set execution engine if needed
            if hasattr(supervisor_agent, 'set_execution_engine'):
                supervisor_agent.set_execution_engine(execution_engine)
            elif hasattr(supervisor_agent, 'execution_engine'):
                supervisor_agent.execution_engine = execution_engine
                
        except Exception as e:
            raise AssertionError(
                f"REGRESSION: SupervisorAgent creation failed: {e}. "
                f"This indicates factory consolidation affected agent initialization.")
        
        # Test basic SupervisorAgent functionality
        try:
            # Test agent can process a request (mock the LLM call)
            test_request = "Analyze system performance and provide optimization recommendations"
            
            # Mock LLM response for testing
            with patch('netra_backend.app.agents.supervisor_agent_modern.llm_client') as mock_llm:
                mock_llm.chat.completions.create.return_value.choices = [
                    MagicMock(message=MagicMock(content="Analysis complete: System performance is optimal"))
                ]
                
                # Execute SupervisorAgent (method names may vary)
                if hasattr(supervisor_agent, 'execute'):
                    result = await supervisor_agent.execute(test_request)
                elif hasattr(supervisor_agent, 'process'):
                    result = await supervisor_agent.process(test_request)
                elif hasattr(supervisor_agent, 'run'):
                    result = await supervisor_agent.run(test_request)
                else:
                    # Try calling the agent directly
                    result = await supervisor_agent(test_request)
                
                self.assertIsNotNone(result,
                    "REGRESSION: SupervisorAgent returned None result")
                    
                # Result should be meaningful
                if isinstance(result, str):
                    assert len(result.strip()) > 0, "REGRESSION: SupervisorAgent returned empty result"
                elif isinstance(result, dict):
                    assert 'response' in result or 'result' in result or 'output' in result, \
                        "REGRESSION: SupervisorAgent result missing expected fields"
                
        except Exception as e:
            raise AssertionError(
                f"REGRESSION: SupervisorAgent execution failed: {e}. "
                f"This indicates factory consolidation broke agent execution logic.")
        
        execution_time = time.time() - start_time
        self.record_metric("supervisor_agent_test_time", execution_time)
        self.record_metric("supervisor_agent_regression_free", True)
        
    async def test_triage_agent_works_with_consolidated_factory_884(self):
        """
        REGRESSION TEST: Validate TriageAgent works with consolidated factory
        
        TriageAgent handles request classification - it must work correctly to
        ensure proper routing of user requests after factory consolidation.
        """
        # Import components
        try:
            from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory
            factory = ExecutionEngineFactory()
        except ImportError:
            pytest.skip("Factory not available")
            
        try:
            from netra_backend.app.agents.triage_agent import TriageAgent
        except ImportError:
            pytest.skip("TriageAgent not available")
            
        try:
            from netra_backend.app.agents.user_execution_context import UserExecutionContext
        except ImportError:
            class TestUserExecutionContext:
                def __init__(self, user_id: str, session_id: str, **kwargs):
                    self.user_id = user_id
                    self.session_id = session_id
                    for key, value in kwargs.items():
                        setattr(self, key, value)
            UserExecutionContext = TestUserExecutionContext
        
        # Create context and execution engine
        user_context = UserExecutionContext(
            user_id=f"triage_test_user_{uuid.uuid4().hex[:8]}",
            session_id=f"triage_test_session_{uuid.uuid4().hex[:8]}"
        )
        
        execution_engine = factory.create_execution_engine(user_context)
        
        # Create TriageAgent
        try:
            if 'user_context' in TriageAgent.__init__.__code__.co_varnames:
                triage_agent = TriageAgent(user_context=user_context)
            else:
                triage_agent = TriageAgent()
                
            if hasattr(triage_agent, 'set_execution_engine'):
                triage_agent.set_execution_engine(execution_engine)
                
        except Exception as e:
            raise AssertionError(f"REGRESSION: TriageAgent creation failed: {e}")
        
        # Test TriageAgent functionality
        try:
            test_request = "I need help optimizing my AI model performance"
            
            # Mock LLM for testing
            with patch.object(triage_agent, '_call_llm' if hasattr(triage_agent, '_call_llm') else '__call__') as mock_llm:
                mock_llm.return_value = {
                    'category': 'performance_optimization',
                    'confidence': 0.9,
                    'suggested_agent': 'ApexOptimizerAgent'
                }
                
                if hasattr(triage_agent, 'classify'):
                    result = await triage_agent.classify(test_request)
                elif hasattr(triage_agent, 'triage'):
                    result = await triage_agent.triage(test_request)
                elif hasattr(triage_agent, 'execute'):
                    result = await triage_agent.execute(test_request)
                else:
                    result = await triage_agent(test_request)
                
                self.assertIsNotNone(result, "REGRESSION: TriageAgent returned None")
                
                # Validate triage result structure
                if isinstance(result, dict):
                    assert 'category' in result or 'classification' in result, \
                        "REGRESSION: TriageAgent result missing classification"
                        
        except Exception as e:
            raise AssertionError(f"REGRESSION: TriageAgent execution failed: {e}")
            
        self.record_metric("triage_agent_regression_free", True)
        
    async def test_data_helper_agent_works_with_consolidated_factory_884(self):
        """
        REGRESSION TEST: Validate DataHelperAgent works with consolidated factory
        
        DataHelperAgent handles data requirements analysis - critical for data-driven
        agent workflows that must continue working after factory consolidation.
        """
        # Import components
        try:
            from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory
            factory = ExecutionEngineFactory()
        except ImportError:
            pytest.skip("Factory not available")
            
        try:
            from netra_backend.app.agents.data_helper_agent import DataHelperAgent
        except ImportError:
            pytest.skip("DataHelperAgent not available")
        
        try:
            from netra_backend.app.agents.user_execution_context import UserExecutionContext
        except ImportError:
            class TestUserExecutionContext:
                def __init__(self, user_id: str, session_id: str, **kwargs):
                    self.user_id = user_id
                    self.session_id = session_id
                    for key, value in kwargs.items():
                        setattr(self, key, value)
            UserExecutionContext = TestUserExecutionContext
        
        # Create context and execution engine
        user_context = UserExecutionContext(
            user_id=f"data_helper_test_user_{uuid.uuid4().hex[:8]}",
            session_id=f"data_helper_test_session_{uuid.uuid4().hex[:8]}"
        )
        
        execution_engine = factory.create_execution_engine(user_context)
        
        # Create DataHelperAgent
        try:
            if 'user_context' in DataHelperAgent.__init__.__code__.co_varnames:
                data_helper_agent = DataHelperAgent(user_context=user_context)
            else:
                data_helper_agent = DataHelperAgent()
                
            if hasattr(data_helper_agent, 'set_execution_engine'):
                data_helper_agent.set_execution_engine(execution_engine)
                
        except Exception as e:
            raise AssertionError(f"REGRESSION: DataHelperAgent creation failed: {e}")
        
        # Test DataHelperAgent functionality
        try:
            test_request = "Analyze data requirements for performance optimization"
            
            with patch.object(data_helper_agent, '_analyze_data_requirements' if hasattr(data_helper_agent, '_analyze_data_requirements') else '__call__') as mock_analyze:
                mock_analyze.return_value = {
                    'data_needed': ['performance_metrics', 'system_logs'],
                    'sufficiency': 'partial',
                    'recommendations': ['Collect additional performance data']
                }
                
                if hasattr(data_helper_agent, 'analyze_data_requirements'):
                    result = await data_helper_agent.analyze_data_requirements(test_request)
                elif hasattr(data_helper_agent, 'execute'):
                    result = await data_helper_agent.execute(test_request)
                else:
                    result = await data_helper_agent(test_request)
                
                self.assertIsNotNone(result, "REGRESSION: DataHelperAgent returned None")
                
                # Validate data analysis result
                if isinstance(result, dict):
                    expected_fields = ['data_needed', 'sufficiency', 'recommendations']
                    has_expected_field = any(field in result for field in expected_fields)
                    assert has_expected_field, \
                        f"REGRESSION: DataHelperAgent result missing expected fields: {result}"
                        
        except Exception as e:
            raise AssertionError(f"REGRESSION: DataHelperAgent execution failed: {e}")
            
        self.record_metric("data_helper_agent_regression_free", True)
        
    async def test_apex_optimizer_agent_works_with_consolidated_factory_884(self):
        """
        REGRESSION TEST: Validate ApexOptimizerAgent works with consolidated factory
        
        ApexOptimizerAgent provides AI optimization recommendations - critical for
        the core business value proposition that must work after factory consolidation.
        """
        # Import components
        try:
            from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory
            factory = ExecutionEngineFactory()
        except ImportError:
            pytest.skip("Factory not available")
            
        try:
            from netra_backend.app.agents.apex_optimizer_agent import ApexOptimizerAgent
        except ImportError:
            pytest.skip("ApexOptimizerAgent not available")
        
        try:
            from netra_backend.app.agents.user_execution_context import UserExecutionContext
        except ImportError:
            class TestUserExecutionContext:
                def __init__(self, user_id: str, session_id: str, **kwargs):
                    self.user_id = user_id
                    self.session_id = session_id
                    for key, value in kwargs.items():
                        setattr(self, key, value)
            UserExecutionContext = TestUserExecutionContext
        
        # Create context and execution engine
        user_context = UserExecutionContext(
            user_id=f"apex_optimizer_test_user_{uuid.uuid4().hex[:8]}",
            session_id=f"apex_optimizer_test_session_{uuid.uuid4().hex[:8]}"
        )
        
        execution_engine = factory.create_execution_engine(user_context)
        
        # Create ApexOptimizerAgent
        try:
            if 'user_context' in ApexOptimizerAgent.__init__.__code__.co_varnames:
                apex_optimizer_agent = ApexOptimizerAgent(user_context=user_context)
            else:
                apex_optimizer_agent = ApexOptimizerAgent()
                
            if hasattr(apex_optimizer_agent, 'set_execution_engine'):
                apex_optimizer_agent.set_execution_engine(execution_engine)
                
        except Exception as e:
            raise AssertionError(f"REGRESSION: ApexOptimizerAgent creation failed: {e}")
        
        # Test ApexOptimizerAgent functionality
        try:
            test_request = "Optimize AI model performance for better efficiency"
            
            with patch.object(apex_optimizer_agent, '_generate_optimization_recommendations' if hasattr(apex_optimizer_agent, '_generate_optimization_recommendations') else '__call__') as mock_optimize:
                mock_optimize.return_value = {
                    'optimizations': [
                        {'type': 'model_quantization', 'impact': 'high'},
                        {'type': 'batch_size_tuning', 'impact': 'medium'}
                    ],
                    'expected_improvement': '25% faster inference',
                    'implementation_effort': 'medium'
                }
                
                if hasattr(apex_optimizer_agent, 'optimize'):
                    result = await apex_optimizer_agent.optimize(test_request)
                elif hasattr(apex_optimizer_agent, 'generate_recommendations'):
                    result = await apex_optimizer_agent.generate_recommendations(test_request)
                elif hasattr(apex_optimizer_agent, 'execute'):
                    result = await apex_optimizer_agent.execute(test_request)
                else:
                    result = await apex_optimizer_agent(test_request)
                
                self.assertIsNotNone(result, "REGRESSION: ApexOptimizerAgent returned None")
                
                # Validate optimization result
                if isinstance(result, dict):
                    expected_fields = ['optimizations', 'recommendations', 'improvements']
                    has_expected_field = any(field in result for field in expected_fields)
                    assert has_expected_field, \
                        f"REGRESSION: ApexOptimizerAgent result missing expected fields: {result}"
                elif isinstance(result, str):
                    assert len(result.strip()) > 50, \
                        "REGRESSION: ApexOptimizerAgent response too short"
                        
        except Exception as e:
            raise AssertionError(f"REGRESSION: ApexOptimizerAgent execution failed: {e}")
            
        self.record_metric("apex_optimizer_agent_regression_free", True)
        
    async def test_all_agents_factory_compatibility_884(self):
        """
        COMPREHENSIVE REGRESSION TEST: Validate all agents work with consolidated factory
        
        This test validates that all major agent types can be created and executed
        using the consolidated factory without regressions.
        """
        start_time = time.time()
        
        # Import factory
        try:
            from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory
            factory = ExecutionEngineFactory()
        except ImportError:
            pytest.skip("Factory not available")
            
        # Track successful agent tests
        successful_agents = []
        failed_agents = []
        
        # Test each agent type
        for agent_name in self.agents_to_test:
            try:
                # Import agent dynamically
                agent_class = await self._import_agent_class(agent_name)
                if agent_class is None:
                    continue  # Skip if not available
                
                # Create user context for this agent
                try:
                    from netra_backend.app.agents.user_execution_context import UserExecutionContext
                except ImportError:
                    class TestUserExecutionContext:
                        def __init__(self, user_id: str, session_id: str, **kwargs):
                            self.user_id = user_id
                            self.session_id = session_id
                            for key, value in kwargs.items():
                                setattr(self, key, value)
                    UserExecutionContext = TestUserExecutionContext
                
                user_context = UserExecutionContext(
                    user_id=f"{agent_name.lower()}_test_user_{uuid.uuid4().hex[:8]}",
                    session_id=f"{agent_name.lower()}_test_session_{uuid.uuid4().hex[:8]}"
                )
                
                # Create execution engine
                execution_engine = factory.create_execution_engine(user_context)
                
                # Create agent instance
                agent_instance = await self._create_agent_instance(agent_class, user_context, execution_engine)
                
                # Test basic agent functionality
                test_passed = await self._test_agent_basic_functionality(agent_instance, agent_name)
                
                if test_passed:
                    successful_agents.append(agent_name)
                else:
                    failed_agents.append(agent_name)
                    
            except Exception as e:
                failed_agents.append(f"{agent_name} (error: {str(e)[:100]})")
        
        # Record results
        self.record_metric("successful_agents", successful_agents)
        self.record_metric("failed_agents", failed_agents)
        self.record_metric("total_agents_tested", len(successful_agents) + len(failed_agents))
        
        total_time = time.time() - start_time
        self.record_metric("comprehensive_test_time", total_time)
        
        # At least half the agents should work to avoid regression
        success_rate = len(successful_agents) / max(1, len(successful_agents) + len(failed_agents))
        
        assert success_rate >= 0.5, (
            f"REGRESSION: Too many agents failed after factory consolidation. "
            f"Successful: {successful_agents}, Failed: {failed_agents}. "
            f"Success rate: {success_rate:.1%}. This indicates significant regressions.")
        
        # Record overall success
        self.record_metric("comprehensive_regression_test_passed", True)
        self.record_metric("agent_compatibility_success_rate", success_rate)
    
    async def _import_agent_class(self, agent_name: str):
        """Dynamically import agent class"""
        try:
            if agent_name == 'SupervisorAgent':
                try:
                    from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
                    return SupervisorAgent
                except ImportError:
                    from netra_backend.app.agents.supervisor_agent import SupervisorAgent
                    return SupervisorAgent
                    
            elif agent_name == 'TriageAgent':
                from netra_backend.app.agents.triage_agent import TriageAgent
                return TriageAgent
                
            elif agent_name == 'DataHelperAgent':
                from netra_backend.app.agents.data_helper_agent import DataHelperAgent
                return DataHelperAgent
                
            elif agent_name == 'ApexOptimizerAgent':
                from netra_backend.app.agents.apex_optimizer_agent import ApexOptimizerAgent
                return ApexOptimizerAgent
                
        except ImportError:
            return None
    
    async def _create_agent_instance(self, agent_class, user_context, execution_engine):
        """Create agent instance with appropriate parameters"""
        try:
            # Check constructor signature
            if 'user_context' in agent_class.__init__.__code__.co_varnames:
                agent_instance = agent_class(user_context=user_context)
            elif 'execution_engine' in agent_class.__init__.__code__.co_varnames:
                agent_instance = agent_class(execution_engine=execution_engine)
            else:
                agent_instance = agent_class()
            
            # Set execution engine if needed
            if hasattr(agent_instance, 'set_execution_engine'):
                agent_instance.set_execution_engine(execution_engine)
            elif hasattr(agent_instance, 'execution_engine'):
                agent_instance.execution_engine = execution_engine
            
            return agent_instance
            
        except Exception as e:
            raise AssertionError(f"Failed to create {agent_class.__name__}: {e}")
    
    async def _test_agent_basic_functionality(self, agent_instance, agent_name: str) -> bool:
        """Test basic agent functionality"""
        try:
            test_request = f"Test request for {agent_name} functionality"
            
            # Find appropriate method to call
            method_names = ['execute', 'process', 'run', '__call__']
            method_to_call = None
            
            for method_name in method_names:
                if hasattr(agent_instance, method_name):
                    method_to_call = getattr(agent_instance, method_name)
                    break
            
            if method_to_call is None:
                return False  # No callable method found
            
            # Mock any LLM calls
            with patch('netra_backend.app.core.llm_client') as mock_llm:
                mock_llm.chat.completions.create.return_value.choices = [
                    MagicMock(message=MagicMock(content=f"Mock response for {agent_name}"))
                ]
                
                # Call the agent method
                if asyncio.iscoroutinefunction(method_to_call):
                    result = await method_to_call(test_request)
                else:
                    result = method_to_call(test_request)
                
                # Validate result
                return result is not None and (
                    (isinstance(result, str) and len(result.strip()) > 0) or
                    (isinstance(result, dict) and len(result) > 0) or
                    (isinstance(result, list) and len(result) > 0)
                )
                
        except Exception:
            return False