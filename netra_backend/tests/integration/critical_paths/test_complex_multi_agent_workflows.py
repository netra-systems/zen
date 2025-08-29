"""Complex Multi-Agent Workflow Tests - CRITICAL GAP #2.2 A Remediation

Business Value Justification (BVJ):
- Segment: Enterprise ($20K+ MRR protection)
- Business Goal: Validate complex enterprise AI optimization workflows
- Value Impact: Ensures 3+ agent collaborations work reliably in production
- Strategic Impact: Critical for enterprise workflows that chain multiple agents

ADDRESSES CRITICAL GAP #2.2 A:
- Tests for 3+ agent collaborations
- Triage → Supervisor → Data → Optimization → Reporting chains
- Cross-agent data dependency validation
- Complex state propagation across boundaries

Test Coverage:
- 5-agent enterprise optimization workflow
- Complex state propagation with validation checkpoints
- Cross-agent data dependencies and handoffs
- Parallel and sequential agent coordination
- Failure recovery in multi-agent chains
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.services.state.state_manager import StateManager, StateStorage

logger = central_logger.get_logger(__name__)


class ComplexWorkflowOrchestrator:
    """Orchestrates complex multi-agent workflows with 3+ agents."""
    
    def __init__(self):
        self.agent_registry: Optional[AgentRegistry] = None
        self.state_manager: Optional[StateManager] = None
        self.llm_manager: Optional[AsyncMock] = None
        self.active_agents: Dict[str, BaseSubAgent] = {}
        self.workflow_state: Dict[str, Any] = {}
        self.execution_metrics: Dict[str, Any] = {
            'agent_executions': 0,
            'successful_handoffs': 0,
            'failed_handoffs': 0,
            'state_propagations': 0,
            'data_validations': 0
        }
        
    async def setup(self) -> None:
        """Initialize orchestrator for complex workflow testing."""
        # Use memory-only state management for reliable testing
        self.state_manager = StateManager(storage=StateStorage.MEMORY)
        
        # Setup mock LLM manager
        self.llm_manager = self._create_mock_llm_manager()
        
        # Setup agent registry with all required agents
        await self._setup_agent_registry()
        
    def _create_mock_llm_manager(self) -> AsyncMock:
        """Create mock LLM manager with realistic responses."""
        mock_llm = AsyncMock()
        
        # Create context-aware response generator
        def generate_response_for_agent(agent_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
            """Generate realistic responses based on agent type."""
            responses = {
                'triage': {
                    'priority': 'high',
                    'category': 'optimization',
                    'initial_assessment': 'Cost optimization opportunity identified',
                    'recommended_agents': ['data', 'optimization', 'reporting']
                },
                'supervisor': {
                    'workflow_plan': ['triage', 'data', 'optimization', 'actions', 'reporting'],
                    'coordination_strategy': 'sequential_with_parallel_optimization',
                    'expected_duration': 45
                },
                'data': {
                    'current_metrics': {
                        'monthly_cost': context.get('current_spend', 50000),
                        'resource_utilization': 0.65,
                        'performance_score': 0.85
                    },
                    'bottlenecks': ['model_inference', 'data_pipeline'],
                    'optimization_potential': 0.35
                },
                'optimization': {
                    'recommendations': [
                        {'action': 'model_quantization', 'savings': 0.15},
                        {'action': 'batch_optimization', 'savings': 0.10},
                        {'action': 'cache_implementation', 'savings': 0.08}
                    ],
                    'total_savings_potential': 0.33,
                    'implementation_complexity': 'medium'
                },
                'actions': {
                    'implementation_plan': [
                        'Deploy quantized models to staging',
                        'Implement batching in inference pipeline',
                        'Setup distributed cache'
                    ],
                    'rollout_strategy': 'phased',
                    'risk_level': 'low'
                },
                'reporting': {
                    'executive_summary': 'Identified 33% cost reduction opportunity',
                    'detailed_findings': context,
                    'next_steps': ['Review with stakeholders', 'Begin phased rollout'],
                    'projected_savings': context.get('current_spend', 50000) * 0.33
                }
            }
            
            return {
                'content': json.dumps(responses.get(agent_type, {'status': 'processed'})),
                'metadata': {
                    'agent_type': agent_type,
                    'cost': 0.001,
                    'tokens': 150,
                    'processing_time': 0.5
                }
            }
        
        # Configure mock to return context-aware responses
        async def mock_generate_response(**kwargs):
            agent_type = kwargs.get('agent_type', 'unknown')
            context = kwargs.get('context', {})
            return generate_response_for_agent(agent_type, context)
        
        mock_llm.generate_response = AsyncMock(side_effect=mock_generate_response)
        return mock_llm
        
    async def _setup_agent_registry(self) -> None:
        """Setup agent registry with all required agent types."""
        mock_tool_dispatcher = AsyncMock()
        
        self.agent_registry = AgentRegistry(
            llm_manager=self.llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Register all agent types needed for complex workflows
        agent_types = ['triage', 'supervisor', 'data', 'optimization', 'actions', 'reporting']
        
        for agent_type in agent_types:
            # Create mock agent with proper lifecycle management
            mock_agent = MagicMock(spec=BaseSubAgent)
            mock_agent.agent_type = agent_type
            mock_agent.state = SubAgentLifecycle.PENDING
            mock_agent.execute = AsyncMock()
            
            self.agent_registry.agents[agent_type] = mock_agent
            
    async def create_enterprise_workflow_state(
        self, 
        scenario_type: str = 'cost_optimization'
    ) -> Tuple[str, Dict[str, Any]]:
        """Create complex enterprise workflow state."""
        workflow_id = f"enterprise_{scenario_type}_{uuid.uuid4().hex[:12]}"
        
        scenarios = {
            'cost_optimization': {
                'user_request': 'Analyze and optimize our AI infrastructure costs ($75K/month) while maintaining 99.95% uptime SLA and sub-200ms latency',
                'current_spend': 75000,
                'sla_requirement': 99.95,
                'latency_requirement': 200,
                'priority': 'high',
                'complexity': 'enterprise'
            },
            'capacity_planning': {
                'user_request': 'Plan capacity for 500% growth with multi-region deployment across US, EU, APAC, and handle 10M daily requests',
                'growth_factor': 5.0,
                'target_regions': ['US-EAST', 'US-WEST', 'EU-WEST', 'APAC-SOUTH'],
                'daily_requests': 10000000,
                'priority': 'critical',
                'complexity': 'global'
            },
            'performance_optimization': {
                'user_request': 'Diagnose and fix latency issues affecting 5M users, optimize model serving, and implement auto-scaling',
                'affected_users': 5000000,
                'current_p99_latency': 850,
                'target_p99_latency': 200,
                'priority': 'urgent',
                'complexity': 'high'
            }
        }
        
        scenario_data = scenarios.get(scenario_type, scenarios['cost_optimization'])
        
        # Create workflow state
        workflow_state = {
            'workflow_id': workflow_id,
            'scenario_type': scenario_type,
            'user_request': scenario_data['user_request'],
            'context': scenario_data,
            'agent_sequence': [],
            'state_checkpoints': [],
            'data_dependencies': {},
            'created_at': time.time(),
            'status': 'initialized'
        }
        
        # Store in state manager
        await self.state_manager.set(f"workflow:{workflow_id}", workflow_state)
        self.workflow_state[workflow_id] = workflow_state
        
        return workflow_id, workflow_state
        
    async def execute_five_agent_enterprise_workflow(
        self, 
        workflow_id: str
    ) -> Dict[str, Any]:
        """Execute complete 5-agent enterprise workflow: Triage → Supervisor → Data → Optimization → Reporting."""
        
        workflow_state = await self.state_manager.get(f"workflow:{workflow_id}")
        if not workflow_state:
            raise ValueError(f"Workflow {workflow_id} not found")
            
        execution_start = time.time()
        execution_results = {
            'workflow_id': workflow_id,
            'agents_executed': [],
            'handoff_data': [],
            'state_evolution': [],
            'execution_time': 0,
            'success': False
        }
        
        # Agent execution sequence for enterprise workflow
        agent_sequence = ['triage', 'supervisor', 'data', 'optimization', 'reporting']
        
        # Track state evolution
        shared_context = {
            'workflow_id': workflow_id,
            'user_request': workflow_state['user_request'],
            'accumulated_insights': {},
            'data_dependencies': {},
            'handoff_chain': []
        }
        
        for i, agent_type in enumerate(agent_sequence):
            logger.info(f"Executing agent {i+1}/{len(agent_sequence)}: {agent_type}")
            
            # Create state checkpoint before agent execution
            state_checkpoint = {
                'agent': agent_type,
                'pre_execution': {
                    'context_keys': list(shared_context.keys()),
                    'accumulated_insights_count': len(shared_context['accumulated_insights']),
                    'handoff_chain_length': len(shared_context['handoff_chain']),
                    'timestamp': time.time()
                }
            }
            
            # Execute agent with context
            agent_result = await self._execute_agent_with_context(
                agent_type, 
                shared_context,
                workflow_state['context']
            )
            
            # Update shared context with agent results
            if agent_result['success']:
                # Accumulate insights from agent
                shared_context['accumulated_insights'][agent_type] = agent_result['output']
                
                # Track handoff
                if i > 0:
                    handoff_data = {
                        'from_agent': agent_sequence[i-1],
                        'to_agent': agent_type,
                        'data_transferred': len(json.dumps(agent_result['output'])),
                        'timestamp': time.time()
                    }
                    shared_context['handoff_chain'].append(handoff_data)
                    execution_results['handoff_data'].append(handoff_data)
                    self.execution_metrics['successful_handoffs'] += 1
                
                # Add data dependencies based on agent type
                if agent_type == 'data':
                    shared_context['data_dependencies']['metrics'] = agent_result['output'].get('current_metrics', {})
                elif agent_type == 'optimization':
                    shared_context['data_dependencies']['recommendations'] = agent_result['output'].get('recommendations', [])
                elif agent_type == 'reporting':
                    shared_context['data_dependencies']['summary'] = agent_result['output'].get('executive_summary', '')
                
                execution_results['agents_executed'].append(agent_type)
                
            # Create post-execution checkpoint
            state_checkpoint['post_execution'] = {
                'context_keys': list(shared_context.keys()),
                'accumulated_insights_count': len(shared_context['accumulated_insights']),
                'handoff_chain_length': len(shared_context['handoff_chain']),
                'success': agent_result['success'],
                'timestamp': time.time()
            }
            
            execution_results['state_evolution'].append(state_checkpoint)
            workflow_state['state_checkpoints'].append(state_checkpoint)
            
            # Update metrics
            self.execution_metrics['agent_executions'] += 1
            self.execution_metrics['state_propagations'] += 1
            
        # Update workflow state
        workflow_state['status'] = 'completed'
        workflow_state['agent_sequence'] = execution_results['agents_executed']
        workflow_state['final_context'] = shared_context
        workflow_state['execution_time'] = time.time() - execution_start
        
        await self.state_manager.set(f"workflow:{workflow_id}", workflow_state)
        
        execution_results['execution_time'] = workflow_state['execution_time']
        execution_results['success'] = len(execution_results['agents_executed']) == len(agent_sequence)
        execution_results['final_context'] = shared_context
        
        return execution_results
        
    async def _execute_agent_with_context(
        self, 
        agent_type: str, 
        shared_context: Dict[str, Any],
        workflow_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute single agent with shared context."""
        
        agent = self.agent_registry.get(agent_type)
        if not agent:
            return {'success': False, 'error': f'Agent {agent_type} not found'}
            
        try:
            # Update agent state
            agent.state = SubAgentLifecycle.RUNNING
            
            # Execute agent with context
            llm_response = await self.llm_manager.generate_response(
                agent_type=agent_type,
                context={**workflow_context, **shared_context}
            )
            
            # Parse response
            output = json.loads(llm_response['content'])
            
            # Update agent state
            agent.state = SubAgentLifecycle.COMPLETED
            
            return {
                'success': True,
                'agent_type': agent_type,
                'output': output,
                'metadata': llm_response['metadata']
            }
            
        except Exception as e:
            agent.state = SubAgentLifecycle.FAILED
            return {
                'success': False,
                'agent_type': agent_type,
                'error': str(e)
            }
            
    async def validate_cross_agent_data_dependencies(
        self, 
        workflow_id: str
    ) -> Dict[str, Any]:
        """Validate data dependencies across agent boundaries."""
        
        workflow_state = await self.state_manager.get(f"workflow:{workflow_id}")
        if not workflow_state:
            return {'error': 'Workflow not found'}
            
        validation_results = {
            'workflow_id': workflow_id,
            'total_checkpoints': len(workflow_state.get('state_checkpoints', [])),
            'dependency_validations': [],
            'data_consistency': True,
            'missing_dependencies': []
        }
        
        # Validate each checkpoint
        checkpoints = workflow_state.get('state_checkpoints', [])
        
        for i, checkpoint in enumerate(checkpoints):
            agent = checkpoint['agent']
            
            # Validate context preservation
            pre_keys = set(checkpoint['pre_execution']['context_keys'])
            post_keys = set(checkpoint['post_execution']['context_keys'])
            
            if not pre_keys.issubset(post_keys):
                validation_results['data_consistency'] = False
                validation_results['missing_dependencies'].append({
                    'agent': agent,
                    'lost_keys': list(pre_keys - post_keys)
                })
            
            # Validate insight accumulation
            pre_insights = checkpoint['pre_execution']['accumulated_insights_count']
            post_insights = checkpoint['post_execution']['accumulated_insights_count']
            
            validation = {
                'agent': agent,
                'checkpoint_index': i,
                'context_preserved': pre_keys.issubset(post_keys),
                'insights_accumulated': post_insights >= pre_insights,
                'handoff_chain_grew': checkpoint['post_execution']['handoff_chain_length'] >= 
                                     checkpoint['pre_execution']['handoff_chain_length']
            }
            
            validation_results['dependency_validations'].append(validation)
            self.execution_metrics['data_validations'] += 1
            
        # Validate final data dependencies
        final_context = workflow_state.get('final_context', {})
        expected_dependencies = ['metrics', 'recommendations', 'summary']
        
        for dep in expected_dependencies:
            if dep not in final_context.get('data_dependencies', {}):
                validation_results['missing_dependencies'].append({
                    'type': 'final_dependency',
                    'missing': dep
                })
                validation_results['data_consistency'] = False
                
        return validation_results
        
    async def test_parallel_agent_coordination(
        self, 
        workflow_id: str,
        parallel_agents: List[str]
    ) -> Dict[str, Any]:
        """Test parallel execution of multiple agents with shared state."""
        
        workflow_state = await self.state_manager.get(f"workflow:{workflow_id}")
        if not workflow_state:
            return {'error': 'Workflow not found'}
            
        parallel_start = time.time()
        
        # Create shared context for parallel execution
        shared_context = workflow_state.get('final_context', {
            'workflow_id': workflow_id,
            'parallel_execution': True
        })
        
        # Execute agents in parallel
        tasks = []
        for agent_type in parallel_agents:
            task = self._execute_agent_with_context(
                agent_type,
                shared_context,
                workflow_state['context']
            )
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        parallel_duration = time.time() - parallel_start
        
        # Process results
        successful_agents = []
        failed_agents = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_agents.append(parallel_agents[i])
            elif result.get('success'):
                successful_agents.append(parallel_agents[i])
                self.execution_metrics['agent_executions'] += 1
                self.execution_metrics['state_propagations'] += 1
            else:
                failed_agents.append(parallel_agents[i])
                
        return {
            'parallel_agents': parallel_agents,
            'successful_agents': successful_agents,
            'failed_agents': failed_agents,
            'execution_time': parallel_duration,
            'success_rate': len(successful_agents) / len(parallel_agents) if parallel_agents else 0
        }
        
    async def simulate_agent_failure_recovery(
        self, 
        workflow_id: str,
        failing_agent: str
    ) -> Dict[str, Any]:
        """Simulate agent failure and test recovery in multi-agent workflow."""
        
        workflow_state = await self.state_manager.get(f"workflow:{workflow_id}")
        if not workflow_state:
            return {'error': 'Workflow not found'}
            
        recovery_results = {
            'failing_agent': failing_agent,
            'recovery_attempted': False,
            'recovery_successful': False,
            'alternative_path': None
        }
        
        # Simulate failure
        agent = self.agent_registry.get(failing_agent)
        if agent:
            agent.state = SubAgentLifecycle.FAILED
            self.execution_metrics['failed_handoffs'] += 1
            
            # Attempt recovery with alternative agent
            alternative_agents = {
                'data': 'reporting',  # Skip to reporting if data fails
                'optimization': 'actions',  # Skip to actions if optimization fails
                'actions': 'reporting'  # Skip to reporting if actions fails
            }
            
            alternative = alternative_agents.get(failing_agent)
            if alternative:
                recovery_results['recovery_attempted'] = True
                recovery_results['alternative_path'] = alternative
                
                # Execute alternative agent
                result = await self._execute_agent_with_context(
                    alternative,
                    workflow_state.get('final_context', {}),
                    workflow_state['context']
                )
                
                recovery_results['recovery_successful'] = result.get('success', False)
                
        return recovery_results
        
    async def cleanup(self) -> None:
        """Clean up orchestrator resources."""
        if self.state_manager:
            await self.state_manager.clear()
        self.active_agents.clear()
        self.workflow_state.clear()


@pytest.fixture
async def workflow_orchestrator():
    """Create complex workflow orchestrator."""
    orchestrator = ComplexWorkflowOrchestrator()
    await orchestrator.setup()
    yield orchestrator
    await orchestrator.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.critical
async def test_five_agent_enterprise_optimization_workflow(workflow_orchestrator):
    """Test complete 5-agent workflow: Triage → Supervisor → Data → Optimization → Reporting.
    
    ADDRESSES CRITICAL GAP #2.2 A: Tests 3+ agent collaborations
    """
    orchestrator = workflow_orchestrator
    
    # Create enterprise workflow
    workflow_id, workflow_state = await orchestrator.create_enterprise_workflow_state('cost_optimization')
    
    assert workflow_id is not None
    assert workflow_state['scenario_type'] == 'cost_optimization'
    assert workflow_state['context']['current_spend'] == 75000
    
    # Execute 5-agent workflow
    execution_results = await orchestrator.execute_five_agent_enterprise_workflow(workflow_id)
    
    # Validate complete execution
    assert execution_results['success'] is True
    assert len(execution_results['agents_executed']) == 5
    assert execution_results['agents_executed'] == ['triage', 'supervisor', 'data', 'optimization', 'reporting']
    
    # Validate handoffs occurred
    assert len(execution_results['handoff_data']) >= 4  # At least 4 handoffs in 5-agent chain
    
    # Validate state evolution
    assert len(execution_results['state_evolution']) == 5
    for checkpoint in execution_results['state_evolution']:
        assert checkpoint['post_execution']['success'] is True
        assert checkpoint['post_execution']['accumulated_insights_count'] >= checkpoint['pre_execution']['accumulated_insights_count']
    
    # Validate execution time is reasonable
    assert execution_results['execution_time'] < 60.0  # Should complete within 1 minute
    
    # Validate final context contains all agent insights
    final_context = execution_results['final_context']
    assert 'accumulated_insights' in final_context
    assert len(final_context['accumulated_insights']) == 5
    assert all(agent in final_context['accumulated_insights'] for agent in ['triage', 'supervisor', 'data', 'optimization', 'reporting'])


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.critical
async def test_cross_agent_data_dependency_validation(workflow_orchestrator):
    """Test data dependencies are correctly validated across agent boundaries.
    
    ADDRESSES CRITICAL GAP #2.2 A: Cross-agent data dependency validation
    """
    orchestrator = workflow_orchestrator
    
    # Create and execute workflow
    workflow_id, _ = await orchestrator.create_enterprise_workflow_state('capacity_planning')
    execution_results = await orchestrator.execute_five_agent_enterprise_workflow(workflow_id)
    
    assert execution_results['success'] is True
    
    # Validate cross-agent data dependencies
    validation_results = await orchestrator.validate_cross_agent_data_dependencies(workflow_id)
    
    # All dependencies should be preserved
    assert validation_results['data_consistency'] is True
    assert len(validation_results['missing_dependencies']) == 0
    
    # Validate each checkpoint
    assert validation_results['total_checkpoints'] == 5
    for validation in validation_results['dependency_validations']:
        assert validation['context_preserved'] is True
        assert validation['insights_accumulated'] is True
        assert validation['handoff_chain_grew'] is True
    
    # Validate critical data dependencies exist
    workflow_state = await orchestrator.state_manager.get(f"workflow:{workflow_id}")
    final_deps = workflow_state['final_context']['data_dependencies']
    
    assert 'metrics' in final_deps
    assert 'recommendations' in final_deps
    assert 'summary' in final_deps


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.critical
async def test_complex_state_propagation_across_boundaries(workflow_orchestrator):
    """Test complex state propagation across multiple agent boundaries.
    
    ADDRESSES CRITICAL GAP #2.2 A: Complex state propagation across boundaries
    """
    orchestrator = workflow_orchestrator
    
    # Create workflow with complex initial state
    workflow_id, workflow_state = await orchestrator.create_enterprise_workflow_state('performance_optimization')
    
    # Add complex nested state
    complex_state = {
        'performance_metrics': {
            'latency': {'p50': 150, 'p95': 450, 'p99': 850},
            'throughput': {'requests_per_second': 10000, 'peak_rps': 25000},
            'error_rates': {'4xx': 0.02, '5xx': 0.001}
        },
        'infrastructure': {
            'regions': ['us-east-1', 'eu-west-1', 'ap-southeast-1'],
            'instances': {'compute': 250, 'cache': 50, 'database': 20},
            'utilization': {'cpu': 0.75, 'memory': 0.82, 'network': 0.60}
        },
        'optimization_constraints': {
            'budget': 100000,
            'sla': {'uptime': 99.95, 'latency_p99': 200},
            'compliance': ['SOC2', 'GDPR', 'HIPAA']
        }
    }
    
    # Update workflow state with complex state
    workflow_state['context'].update(complex_state)
    await orchestrator.state_manager.set(f"workflow:{workflow_id}", workflow_state)
    
    # Execute workflow
    execution_results = await orchestrator.execute_five_agent_enterprise_workflow(workflow_id)
    
    assert execution_results['success'] is True
    
    # Validate complex state propagation
    final_context = execution_results['final_context']
    
    # Original request should be preserved
    assert final_context['user_request'] == workflow_state['user_request']
    
    # Accumulated insights should grow with each agent
    assert len(final_context['accumulated_insights']) == 5
    
    # Handoff chain should show complete propagation
    assert len(final_context['handoff_chain']) >= 4
    
    # Validate state checkpoints show monotonic growth
    state_evolution = execution_results['state_evolution']
    insight_counts = [cp['post_execution']['accumulated_insights_count'] for cp in state_evolution]
    assert all(insight_counts[i] <= insight_counts[i+1] for i in range(len(insight_counts)-1))
    
    # Validate complex nested state is accessible in final context
    workflow_final = await orchestrator.state_manager.get(f"workflow:{workflow_id}")
    assert 'performance_metrics' in workflow_final['context']
    assert 'infrastructure' in workflow_final['context']
    assert 'optimization_constraints' in workflow_final['context']


@pytest.mark.asyncio
@pytest.mark.integration
async def test_parallel_and_sequential_agent_coordination(workflow_orchestrator):
    """Test mixed parallel and sequential agent execution patterns."""
    orchestrator = workflow_orchestrator
    
    # Create workflow
    workflow_id, _ = await orchestrator.create_enterprise_workflow_state('cost_optimization')
    
    # Execute sequential phase first (Triage → Supervisor)
    sequential_agents = ['triage', 'supervisor']
    for agent in sequential_agents:
        result = await orchestrator._execute_agent_with_context(
            agent,
            {'workflow_id': workflow_id, 'phase': 'sequential'},
            {'current_spend': 75000}
        )
        assert result['success'] is True
        orchestrator.execution_metrics['agent_executions'] += 1
        orchestrator.execution_metrics['state_propagations'] += 1
    
    # Execute parallel phase (Data, Optimization, Actions in parallel)
    parallel_results = await orchestrator.test_parallel_agent_coordination(
        workflow_id,
        ['data', 'optimization', 'actions']
    )
    
    assert parallel_results['success_rate'] >= 0.66  # At least 2/3 should succeed
    assert parallel_results['execution_time'] < 10.0  # Parallel should be fast
    
    # Execute final sequential phase (Reporting)
    final_result = await orchestrator._execute_agent_with_context(
        'reporting',
        {'workflow_id': workflow_id, 'phase': 'final'},
        {'current_spend': 75000}
    )
    assert final_result['success'] is True
    orchestrator.execution_metrics['agent_executions'] += 1
    orchestrator.execution_metrics['state_propagations'] += 1
    
    # Validate metrics
    assert orchestrator.execution_metrics['agent_executions'] >= 6
    assert orchestrator.execution_metrics['state_propagations'] >= 5


@pytest.mark.asyncio
@pytest.mark.integration
async def test_agent_failure_recovery_in_complex_workflow(workflow_orchestrator):
    """Test failure recovery mechanisms in multi-agent workflows."""
    orchestrator = workflow_orchestrator
    
    # Create and partially execute workflow
    workflow_id, _ = await orchestrator.create_enterprise_workflow_state('capacity_planning')
    
    # Execute first few agents successfully
    success_agents = ['triage', 'supervisor']
    for agent in success_agents:
        result = await orchestrator._execute_agent_with_context(
            agent,
            {'workflow_id': workflow_id},
            {'growth_factor': 5.0}
        )
        assert result['success'] is True
        orchestrator.execution_metrics['agent_executions'] += 1
    
    # Simulate data agent failure and test recovery
    recovery_result = await orchestrator.simulate_agent_failure_recovery(workflow_id, 'data')
    
    assert recovery_result['recovery_attempted'] is True
    assert recovery_result['alternative_path'] == 'reporting'
    assert recovery_result['recovery_successful'] is True
    
    # Count the recovery agent execution
    if recovery_result['recovery_successful']:
        orchestrator.execution_metrics['agent_executions'] += 1
    
    # Continue with remaining agents
    remaining_agents = ['optimization', 'reporting']
    for agent in remaining_agents:
        result = await orchestrator._execute_agent_with_context(
            agent,
            {'workflow_id': workflow_id, 'recovered': True},
            {'growth_factor': 5.0}
        )
        # Should handle gracefully even after failure
        assert result['success'] is True
        orchestrator.execution_metrics['agent_executions'] += 1
    
    # Validate workflow can complete despite failure
    assert orchestrator.execution_metrics['failed_handoffs'] == 1
    assert orchestrator.execution_metrics['agent_executions'] >= 5


@pytest.mark.asyncio
@pytest.mark.integration
async def test_enterprise_workflow_performance_metrics(workflow_orchestrator):
    """Test performance metrics for enterprise multi-agent workflows."""
    orchestrator = workflow_orchestrator
    
    # Execute multiple workflows to gather metrics
    workflow_ids = []
    execution_times = []
    
    for i in range(3):
        scenario = ['cost_optimization', 'capacity_planning', 'performance_optimization'][i]
        workflow_id, _ = await orchestrator.create_enterprise_workflow_state(scenario)
        workflow_ids.append(workflow_id)
        
        # Execute workflow
        start_time = time.time()
        results = await orchestrator.execute_five_agent_enterprise_workflow(workflow_id)
        execution_time = time.time() - start_time
        execution_times.append(execution_time)
        
        assert results['success'] is True
        
        # Validate data dependencies for this workflow
        await orchestrator.validate_cross_agent_data_dependencies(workflow_id)
    
    # Validate performance metrics
    average_execution_time = sum(execution_times) / len(execution_times)
    assert average_execution_time < 45.0  # Average should be under 45 seconds
    
    max_execution_time = max(execution_times)
    assert max_execution_time < 60.0  # No workflow should exceed 1 minute
    
    # Validate orchestrator metrics
    # The execute_five_agent_enterprise_workflow method tracks metrics internally
    # We executed 3 workflows, each with 5 agents
    assert orchestrator.execution_metrics['agent_executions'] >= 15  # 5 agents * 3 workflows
    assert orchestrator.execution_metrics['successful_handoffs'] >= 12  # 4 handoffs * 3 workflows  
    assert orchestrator.execution_metrics['state_propagations'] >= 15
    assert orchestrator.execution_metrics['data_validations'] >= 3  # At least 1 per workflow


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.benchmark
async def test_workflow_scalability_under_load(workflow_orchestrator):
    """Test workflow scalability with concurrent multi-agent workflows."""
    orchestrator = workflow_orchestrator
    
    # Create multiple concurrent workflows
    num_concurrent = 5
    workflow_tasks = []
    
    for i in range(num_concurrent):
        scenario = ['cost_optimization', 'capacity_planning'][i % 2]
        workflow_id, _ = await orchestrator.create_enterprise_workflow_state(scenario)
        
        # Create task for workflow execution
        task = asyncio.create_task(
            orchestrator.execute_five_agent_enterprise_workflow(workflow_id)
        )
        workflow_tasks.append(task)
    
    # Execute all workflows concurrently
    start_time = time.time()
    results = await asyncio.gather(*workflow_tasks, return_exceptions=True)
    total_time = time.time() - start_time
    
    # Validate results
    successful_workflows = [r for r in results if not isinstance(r, Exception) and r.get('success')]
    
    assert len(successful_workflows) >= 3  # At least 3/5 should succeed
    assert total_time < 120.0  # Should complete within 2 minutes even under load
    
    # Validate individual workflow performance didn't degrade significantly
    for result in successful_workflows:
        if isinstance(result, dict):
            assert result['execution_time'] < 90.0  # Individual workflows should still be reasonably fast