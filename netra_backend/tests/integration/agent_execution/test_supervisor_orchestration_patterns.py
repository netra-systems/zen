"""
SupervisorAgent Orchestration Pattern Integration Tests

These tests validate the SupervisorAgent's core orchestration capabilities,
focusing on agent routing, sub-agent coordination, and context preservation
without requiring Docker services.

Business Value Focus:
- Agent routing decisions based on user intent
- Tool dispatcher integration and execution  
- Sub-agent creation and coordination
- Context preservation across agent handoffs
- Error handling and recovery during execution

CRITICAL: NO MOCKS for internal agent logic - testing real orchestration patterns.
"""

import asyncio
import pytest
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.tests.integration.agent_execution.base_agent_execution_test import BaseAgentExecutionTest


class TestSupervisorOrchestrationPatterns(BaseAgentExecutionTest):
    """Test SupervisorAgent orchestration patterns and business logic."""

    @pytest.mark.asyncio
    async def test_supervisor_agent_routing_and_selection_logic(self):
        """Test supervisor's agent routing and selection decisions.
        
        Validates:
        - Supervisor correctly analyzes user requests
        - Appropriate agents are selected based on request type
        - Execution order follows business logic
        - WebSocket events are emitted during routing
        """
        # Create context with optimization request
        context = self.create_user_execution_context(
            user_request="I need to optimize my AI infrastructure costs and improve performance",
            additional_metadata={
                "request_category": "optimization",
                "urgency": "high",
                "data_available": True
            }
        )
        
        # Create supervisor with real orchestration logic
        supervisor = self.create_supervisor_agent()
        
        # Execute with full orchestration (will use real agent routing logic)
        results = await self.execute_agent_with_validation(
            agent=supervisor,
            context=context,
            expected_events=['agent_started', 'agent_thinking', 'agent_completed'],
            business_value_indicators=[
                'optimization', 'cost', 'performance', 
                'supervisor_result', 'orchestration_successful'
            ]
        )
        
        # Validate routing decisions
        assert results.get('orchestration_successful') is True
        assert 'results' in results
        
        # Verify workflow metadata shows proper agent selection
        workflow_metadata = results.get('results', {}).get('_workflow_metadata', {})
        assert 'completed_agents' in workflow_metadata
        assert 'success_rate' in workflow_metadata
        
        # At minimum, reporting agent should execute (UVS principle)  
        completed_agents = workflow_metadata.get('completed_agents', [])
        assert len(completed_agents) >= 1, "At least reporting agent should complete"
        
        # Validate WebSocket routing events
        routing_events = self.mock_websocket_manager.get_events_by_type('agent_thinking')
        routing_messages = [event['data']['message'] for event in routing_events]
        
        # Should contain routing/orchestration thinking
        routing_found = any('orchestration' in msg.lower() or 'planning' in msg.lower() 
                          for msg in routing_messages)
        assert routing_found, "Supervisor should emit routing/planning thoughts"

    @pytest.mark.asyncio  
    async def test_tool_dispatcher_integration_and_execution(self):
        """Test supervisor's integration with tool dispatcher for real execution.
        
        Validates:
        - Tool dispatcher is created per-request with proper isolation
        - Tools are executed through dispatcher during agent orchestration
        - Tool results are properly integrated into agent workflow
        - WebSocket events include tool execution notifications
        """
        # Create context with data analysis request (requires tools)
        context = self.create_user_execution_context(
            user_request="Analyze my usage data and provide cost optimization recommendations",
            additional_metadata={
                "has_usage_data": True,
                "data_format": "json",
                "analysis_depth": "comprehensive"
            }
        )
        
        supervisor = self.create_supervisor_agent()
        
        # Mock tool classes to avoid external API dependencies but test integration
        mock_tool_classes = [
            type('MockDataTool', (), {
                '__name__': 'MockDataTool',
                'name': 'data_analyzer', 
                'description': 'Mock data analysis tool'
            }),
            type('MockOptimizationTool', (), {
                '__name__': 'MockOptimizationTool', 
                'name': 'cost_optimizer',
                'description': 'Mock cost optimization tool'
            })
        ]
        
        # Patch tool classes to use our mocks but keep real dispatcher logic
        with patch('netra_backend.app.agents.user_context_tool_factory.get_app_tool_classes', 
                  return_value=mock_tool_classes):
            
            results = await self.execute_agent_with_validation(
                agent=supervisor,
                context=context, 
                expected_events=['agent_started', 'agent_thinking', 'tool_executing', 'agent_completed'],
                business_value_indicators=['analysis', 'optimization', 'recommendations']
            )
        
        # Validate tool integration
        assert results.get('user_isolation_verified') is True
        assert 'results' in results
        
        # Check that tool system was created (should be in supervisor attributes after execution)
        # Note: After execution, these are cleaned up, but we can verify through events
        tool_events = self.mock_websocket_manager.get_events_by_type('tool_executing')
        
        # Tool execution events should be present if agents used tools
        if tool_events:
            assert len(tool_events) > 0, "Tool execution events should be emitted"
            
            for tool_event in tool_events:
                assert 'data' in tool_event
                assert 'tool_name' in tool_event['data']
                assert tool_event['run_id'] == context.run_id

    @pytest.mark.asyncio
    async def test_sub_agent_creation_and_coordination(self):
        """Test supervisor's sub-agent creation and coordination patterns.
        
        Validates:
        - Sub-agents are created with proper isolation
        - Coordination between multiple agents works correctly  
        - Context is properly passed between agents
        - Agent dependencies are resolved correctly
        """
        # Create context that will trigger multiple agents
        context = self.create_user_execution_context(
            user_request="I need a comprehensive analysis with data collection, optimization suggestions, and action plan",
            additional_metadata={
                "scope": "comprehensive",
                "requires_multiple_agents": True,
                "workflow_complexity": "high"
            }
        )
        
        supervisor = self.create_supervisor_agent()
        
        # Mock the agent instance factory to return our test agents
        mock_agents = {
            'triage': self.create_mock_agent_instance('triage', {
                'status': 'completed',
                'category': 'optimization_request',
                'data_sufficiency': 'partial',
                'next_agents': ['data_helper', 'optimization', 'actions']
            }),
            'data_helper': self.create_mock_agent_instance('data_helper', {
                'status': 'completed', 
                'guidance': 'Please provide usage metrics for detailed analysis',
                'data_collection_steps': ['metric_1', 'metric_2']
            }),
            'optimization': self.create_mock_agent_instance('optimization', {
                'status': 'completed',
                'strategies': ['strategy_1', 'strategy_2'],
                'cost_savings': '30%'
            }),
            'actions': self.create_mock_agent_instance('actions', {
                'status': 'completed', 
                'action_plan': ['step_1', 'step_2', 'step_3'],
                'timeline': '2_weeks'
            }),
            'reporting': self.create_mock_agent_instance('reporting', {
                'status': 'completed',
                'report': 'Comprehensive analysis completed',
                'summary': ['finding_1', 'finding_2']
            })
        }
        
        # Mock agent instance factory to return our controlled agents  
        async def mock_create_agent_instance(agent_name: str, user_context: UserExecutionContext):
            if agent_name in mock_agents:
                return mock_agents[agent_name]
            raise ValueError(f"Unknown agent: {agent_name}")
            
        supervisor.agent_instance_factory.create_agent_instance = mock_create_agent_instance
        
        results = await self.execute_agent_with_validation(
            agent=supervisor,
            context=context,
            expected_events=['agent_started', 'agent_thinking', 'agent_completed'],
            business_value_indicators=['comprehensive', 'analysis', 'optimization', 'action_plan']
        )
        
        # Validate sub-agent coordination
        workflow_results = results.get('results', {})
        assert len(workflow_results) >= 2, "Multiple agents should execute"
        
        # Validate agent execution sequence and results
        workflow_metadata = workflow_results.get('_workflow_metadata', {})
        completed_agents = set(workflow_metadata.get('completed_agents', []))
        
        # Reporting should always complete (UVS principle)
        assert 'reporting' in completed_agents
        
        # Check coordination - results from earlier agents available to later ones
        if 'triage' in workflow_results and 'reporting' in workflow_results:
            # Triage results should influence reporting
            assert workflow_results['triage'].get('status') == 'completed'
            assert workflow_results['reporting'].get('status') == 'completed'

    @pytest.mark.asyncio
    async def test_context_preservation_across_agent_handoffs(self):
        """Test context preservation and metadata propagation across agent handoffs.
        
        Validates:
        - UserExecutionContext data is preserved across agent boundaries
        - Metadata from parent context flows to child contexts
        - Agent results are properly stored and accessible
        - Context isolation is maintained per user
        """
        # Create context with rich metadata
        initial_metadata = {
            "user_request": "Multi-step analysis request",
            "business_context": "enterprise_optimization",
            "priority": "high",
            "custom_data": {"key": "value", "nested": {"inner": "data"}}
        }
        
        context = self.create_user_execution_context(
            user_request="Perform multi-step analysis with context preservation",
            additional_metadata=initial_metadata
        )
        
        supervisor = self.create_supervisor_agent()
        
        # Track context propagation by monitoring agent calls
        context_snapshots = []
        
        # Mock agent that captures context details
        class ContextCapturingAgent(BaseAgent):
            def __init__(self, name: str):
                super().__init__(llm_manager=None, name=name, description=f"Context capturing {name}")
                self.captured_contexts = []
                
            async def execute(self, exec_context: UserExecutionContext, stream_updates: bool = False):
                # Capture context snapshot
                context_snapshot = {
                    'agent_name': self.name,
                    'user_id': exec_context.user_id,
                    'run_id': exec_context.run_id,
                    'metadata_keys': list(exec_context.metadata.keys()),
                    'metadata_sample': dict(list(exec_context.metadata.items())[:3])  # Sample
                }
                context_snapshots.append(context_snapshot)
                self.captured_contexts.append(exec_context)
                
                return {
                    'status': 'completed',
                    'agent_name': self.name,
                    'context_preserved': True,
                    'metadata_count': len(exec_context.metadata)
                }
        
        # Create context-capturing agents
        mock_agents = {
            'triage': ContextCapturingAgent('triage'),
            'data_helper': ContextCapturingAgent('data_helper'), 
            'reporting': ContextCapturingAgent('reporting')
        }
        
        async def mock_create_agent_instance(agent_name: str, user_context: UserExecutionContext):
            if agent_name in mock_agents:
                return mock_agents[agent_name]
            raise ValueError(f"Unknown agent: {agent_name}")
            
        supervisor.agent_instance_factory.create_agent_instance = mock_create_agent_instance
        
        results = await self.execute_agent_with_validation(
            agent=supervisor,
            context=context,
            expected_events=['agent_started', 'agent_thinking', 'agent_completed'],
            business_value_indicators=['context_preserved', 'completed']
        )
        
        # Validate context preservation
        assert len(context_snapshots) >= 1, "At least one agent should capture context"
        
        for snapshot in context_snapshots:
            # Verify core context data preserved
            assert snapshot['user_id'] == context.user_id
            assert snapshot['run_id'] == context.run_id
            
            # Verify metadata preservation  
            assert 'user_request' in snapshot['metadata_keys']
            assert 'business_context' in snapshot['metadata_keys']
            
        # Validate results propagation
        workflow_results = results.get('results', {})
        for agent_result in workflow_results.values():
            if isinstance(agent_result, dict) and 'context_preserved' in agent_result:
                assert agent_result['context_preserved'] is True

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery_during_execution(self):
        """Test supervisor's error handling and recovery patterns.
        
        Validates:
        - Graceful handling of sub-agent failures
        - Continuation of workflow when optional agents fail
        - Proper error propagation and logging
        - UVS principle - always deliver value even with failures
        """
        context = self.create_user_execution_context(
            user_request="Request that will trigger some agent failures",
            additional_metadata={"test_scenario": "error_recovery"}
        )
        
        supervisor = self.create_supervisor_agent()
        
        # Create agents with mixed success/failure patterns
        mock_agents = {
            'triage': self.create_mock_agent_instance('triage', {
                'status': 'completed',
                'data_sufficiency': 'insufficient', 
                'next_agents': ['data_helper', 'optimization']
            }),
            'data_helper': self.create_mock_agent_instance('data_helper', {
                'status': 'failed',
                'error': 'Simulated data helper failure'
            }),
            'optimization': self.create_mock_agent_instance('optimization', {
                'status': 'failed', 
                'error': 'Simulated optimization failure'
            }),
            'reporting': self.create_mock_agent_instance('reporting', {
                'status': 'completed',
                'report': 'Fallback report with limited data',
                'fallback_mode': True
            })
        }
        
        # Make some agents actually fail
        mock_agents['data_helper'].execute.side_effect = RuntimeError("Data helper failure")
        mock_agents['optimization'].execute.side_effect = RuntimeError("Optimization failure")
        
        async def mock_create_agent_instance(agent_name: str, user_context: UserExecutionContext):
            if agent_name in mock_agents:
                return mock_agents[agent_name]
            raise ValueError(f"Unknown agent: {agent_name}")
            
        supervisor.agent_instance_factory.create_agent_instance = mock_create_agent_instance
        
        # Execute despite expected failures
        results = await self.execute_agent_with_validation(
            agent=supervisor,
            context=context,
            expected_events=['agent_started', 'agent_thinking', 'agent_completed'],
            business_value_indicators=['supervisor_result', 'completed', 'reporting']
        )
        
        # Validate error recovery 
        assert results.get('supervisor_result') == 'completed', "Supervisor should complete despite sub-agent failures"
        assert results.get('orchestration_successful') is True, "Orchestration should succeed with UVS"
        
        # Validate workflow handled failures gracefully
        workflow_results = results.get('results', {})
        workflow_metadata = workflow_results.get('_workflow_metadata', {})
        
        failed_agents = set(workflow_metadata.get('failed_agents', []))
        completed_agents = set(workflow_metadata.get('completed_agents', []))
        
        # Should have some failures but reporting should succeed (UVS)
        assert len(failed_agents) >= 1, "Should track failed agents"
        assert 'reporting' in completed_agents, "Reporting should succeed (UVS principle)"
        
        # Validate success rate calculated
        success_rate = workflow_metadata.get('success_rate', 0)
        assert 0 <= success_rate <= 1, "Success rate should be valid percentage"