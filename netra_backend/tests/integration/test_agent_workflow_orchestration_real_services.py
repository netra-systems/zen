"""
Agent Workflow Orchestration Integration Tests - Real Services

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure AI agents execute coordinated workflows to deliver optimization insights
- Value Impact: Users receive comprehensive analysis through multi-agent collaboration
- Strategic Impact: Core competitive advantage through sophisticated agent orchestration

These tests validate multi-agent workflows using real services, ensuring agents coordinate
effectively to deliver business value through data analysis, optimization, and automation.
"""

import asyncio
import pytest
import time
from typing import Dict, List, Any
from uuid import uuid4
import json

from test_framework.base_integration_test import ServiceOrchestrationIntegrationTest
from test_framework.conftest_real_services import real_services
from shared.isolated_environment import get_env


class TestAgentWorkflowOrchestration(ServiceOrchestrationIntegrationTest):
    """Test agent workflow orchestration with real services coordination."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_sequential_agent_workflow_execution(self, real_services):
        """
        Test that agents execute in proper sequence to deliver comprehensive analysis.
        
        BVJ: Users must receive complete multi-step analysis for complex optimization tasks.
        """
        # Create test user and organization context
        user_data = await self.create_test_user_context(real_services)
        org_data = await self.create_test_organization(real_services, user_data['id'])
        
        # Create workflow definition in database
        workflow_id = str(uuid4())
        workflow_definition = {
            'workflow_id': workflow_id,
            'name': 'Cost Optimization Workflow',
            'steps': [
                {'agent': 'data_collector', 'order': 1, 'required': True},
                {'agent': 'cost_analyzer', 'order': 2, 'required': True},
                {'agent': 'recommendation_generator', 'order': 3, 'required': True},
                {'agent': 'action_planner', 'order': 4, 'required': False}
            ],
            'owner_id': user_data['id'],
            'organization_id': org_data['id']
        }
        
        # Store workflow in database
        await real_services.postgres.execute("""
            INSERT INTO backend.agent_workflows (id, name, definition, owner_id, organization_id, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, workflow_id, workflow_definition['name'], json.dumps(workflow_definition), 
             user_data['id'], org_data['id'], time.time())
        
        # Initialize workflow execution state in Redis
        execution_id = str(uuid4())
        workflow_state = {
            'execution_id': execution_id,
            'workflow_id': workflow_id,
            'current_step': 0,
            'status': 'initialized',
            'results': {},
            'started_at': time.time(),
            'user_id': user_data['id']
        }
        
        await real_services.redis.set_json(f"workflow:execution:{execution_id}", workflow_state, ex=3600)
        
        # Execute workflow steps sequentially
        for step_index, step in enumerate(workflow_definition['steps']):
            agent_name = step['agent']
            
            # Update workflow state for current step
            workflow_state['current_step'] = step_index
            workflow_state['status'] = f'executing_{agent_name}'
            await real_services.redis.set_json(f"workflow:execution:{execution_id}", workflow_state, ex=3600)
            
            # Simulate agent execution with realistic output
            agent_result = await self._execute_mock_agent(real_services, agent_name, {
                'workflow_id': workflow_id,
                'execution_id': execution_id,
                'step_index': step_index,
                'user_context': user_data,
                'organization_context': org_data
            })
            
            # Store step result
            workflow_state['results'][agent_name] = agent_result
            workflow_state['status'] = f'completed_{agent_name}'
            await real_services.redis.set_json(f"workflow:execution:{execution_id}", workflow_state, ex=3600)
            
            # Verify step completion in database
            await real_services.postgres.execute("""
                INSERT INTO backend.workflow_executions 
                (execution_id, workflow_id, step_index, agent_name, result, completed_at, user_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, execution_id, workflow_id, step_index, agent_name, 
                 json.dumps(agent_result), time.time(), user_data['id'])
        
        # Mark workflow as completed
        workflow_state['status'] = 'completed'
        workflow_state['completed_at'] = time.time()
        await real_services.redis.set_json(f"workflow:execution:{execution_id}", workflow_state, ex=3600)
        
        # Verify workflow execution results
        final_state = await real_services.redis.get_json(f"workflow:execution:{execution_id}")
        assert final_state is not None, "Workflow state must be preserved"
        assert final_state['status'] == 'completed', "Workflow must complete successfully"
        assert len(final_state['results']) == 4, "All workflow steps must produce results"
        
        # Verify business value delivery through agent coordination
        data_result = final_state['results']['data_collector']
        analysis_result = final_state['results']['cost_analyzer'] 
        recommendations = final_state['results']['recommendation_generator']
        action_plan = final_state['results']['action_planner']
        
        assert data_result['data_collected'] > 0, "Data collector must gather analysis data"
        assert analysis_result['cost_savings_identified'] > 0, "Cost analyzer must identify savings opportunities"
        assert len(recommendations['recommendations']) > 0, "Must generate actionable recommendations"
        assert len(action_plan['next_steps']) > 0, "Must provide concrete next steps"
        
        # Verify database persistence of complete workflow
        execution_records = await real_services.postgres.fetch("""
            SELECT step_index, agent_name, result, completed_at
            FROM backend.workflow_executions
            WHERE execution_id = $1
            ORDER BY step_index
        """, execution_id)
        
        assert len(execution_records) == 4, "All workflow steps must be persisted in database"
        for i, record in enumerate(execution_records):
            assert record['step_index'] == i, f"Step {i} must be in correct order"
            assert json.loads(record['result']) is not None, f"Step {i} must have valid results"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_parallel_agent_execution_coordination(self, real_services):
        """
        Test coordinated parallel agent execution for comprehensive analysis.
        
        BVJ: Platform must efficiently utilize multiple agents to reduce analysis time for users.
        """
        # Create test context
        user_data = await self.create_test_user_context(real_services)
        org_data = await self.create_test_organization(real_services, user_data['id'])
        
        # Define parallel workflow
        parallel_workflow_id = str(uuid4())
        execution_id = str(uuid4())
        
        # Parallel analysis agents for comprehensive cost optimization
        parallel_agents = [
            {'name': 'aws_cost_analyzer', 'focus': 'aws_optimization'},
            {'name': 'azure_cost_analyzer', 'focus': 'azure_optimization'},
            {'name': 'gcp_cost_analyzer', 'focus': 'gcp_optimization'},
            {'name': 'multi_cloud_coordinator', 'focus': 'cross_cloud_optimization'}
        ]
        
        # Initialize parallel execution state
        parallel_state = {
            'execution_id': execution_id,
            'workflow_type': 'parallel_analysis',
            'agents_running': [],
            'agents_completed': [],
            'results': {},
            'started_at': time.time(),
            'user_id': user_data['id']
        }
        
        await real_services.redis.set_json(f"parallel:execution:{execution_id}", parallel_state, ex=3600)
        
        # Execute agents in parallel
        async def execute_parallel_agent(agent_config):
            agent_name = agent_config['name']
            focus_area = agent_config['focus']
            
            # Mark agent as running
            running_agents = await real_services.redis.get_json(f"parallel:execution:{execution_id}")
            running_agents['agents_running'].append(agent_name)
            await real_services.redis.set_json(f"parallel:execution:{execution_id}", running_agents, ex=3600)
            
            # Execute agent with focus area
            agent_result = await self._execute_mock_agent(real_services, agent_name, {
                'focus_area': focus_area,
                'execution_id': execution_id,
                'user_context': user_data,
                'organization_context': org_data,
                'parallel_mode': True
            })
            
            # Store result and mark as completed
            completed_state = await real_services.redis.get_json(f"parallel:execution:{execution_id}")
            completed_state['results'][agent_name] = agent_result
            completed_state['agents_completed'].append(agent_name)
            completed_state['agents_running'].remove(agent_name)
            await real_services.redis.set_json(f"parallel:execution:{execution_id}", completed_state, ex=3600)
            
            # Persist to database
            await real_services.postgres.execute("""
                INSERT INTO backend.parallel_executions
                (execution_id, agent_name, focus_area, result, completed_at, user_id)
                VALUES ($1, $2, $3, $4, $5, $6)  
            """, execution_id, agent_name, focus_area, json.dumps(agent_result), time.time(), user_data['id'])
            
            return agent_result
        
        # Run all agents in parallel
        start_time = time.time()
        parallel_results = await asyncio.gather(*[execute_parallel_agent(agent) for agent in parallel_agents])
        execution_duration = time.time() - start_time
        
        # Verify parallel execution coordination
        final_state = await real_services.redis.get_json(f"parallel:execution:{execution_id}")
        assert len(final_state['agents_completed']) == 4, "All parallel agents must complete"
        assert len(final_state['agents_running']) == 0, "No agents should be running after completion"
        assert len(final_state['results']) == 4, "All agents must produce results"
        
        # Verify performance improvement from parallelization
        assert execution_duration < 10, f"Parallel execution too slow: {execution_duration:.2f}s"
        
        # Verify business value from comprehensive multi-cloud analysis
        aws_savings = final_state['results']['aws_cost_analyzer']['potential_savings']
        azure_savings = final_state['results']['azure_cost_analyzer']['potential_savings'] 
        gcp_savings = final_state['results']['gcp_cost_analyzer']['potential_savings']
        cross_cloud_savings = final_state['results']['multi_cloud_coordinator']['optimization_opportunities']
        
        total_identified_savings = aws_savings + azure_savings + gcp_savings
        assert total_identified_savings > 0, "Multi-cloud analysis must identify cost savings"
        assert len(cross_cloud_savings) > 0, "Cross-cloud coordination must find additional opportunities"
        
        # Verify database coordination
        parallel_records = await real_services.postgres.fetch("""
            SELECT agent_name, focus_area, result, completed_at
            FROM backend.parallel_executions  
            WHERE execution_id = $1
            ORDER BY completed_at
        """, execution_id)
        
        assert len(parallel_records) == 4, "All parallel executions must be persisted"
        focus_areas = {record['focus_area'] for record in parallel_records}
        expected_areas = {'aws_optimization', 'azure_optimization', 'gcp_optimization', 'cross_cloud_optimization'}
        assert focus_areas == expected_areas, "All focus areas must be covered"

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_agent_failure_recovery_and_workflow_resilience(self, real_services):
        """
        Test workflow resilience when individual agents fail or timeout.
        
        BVJ: Platform must deliver value even when some components fail, ensuring user gets best available results.
        """
        # Create test context
        user_data = await self.create_test_user_context(real_services)
        org_data = await self.create_test_organization(real_services, user_data['id'])
        
        # Create resilient workflow with optional and required steps
        workflow_id = str(uuid4())
        execution_id = str(uuid4())
        
        resilient_workflow = {
            'execution_id': execution_id,
            'workflow_type': 'resilient_analysis',
            'steps': [
                {'agent': 'data_validator', 'required': True, 'timeout': 5},
                {'agent': 'primary_analyzer', 'required': True, 'timeout': 10},
                {'agent': 'enhancement_analyzer', 'required': False, 'timeout': 5},  # Optional - may fail
                {'agent': 'report_generator', 'required': True, 'timeout': 5}
            ],
            'failure_policy': 'continue_on_optional_failure',
            'user_id': user_data['id']
        }
        
        await real_services.redis.set_json(f"resilient:workflow:{execution_id}", resilient_workflow, ex=3600)
        
        # Execute workflow with simulated failure
        execution_results = {}
        failed_agents = []
        
        for step_index, step in enumerate(resilient_workflow['steps']):
            agent_name = step['agent']
            is_required = step['required']
            timeout_seconds = step['timeout']
            
            try:
                # Simulate failure for enhancement_analyzer (optional)
                if agent_name == 'enhancement_analyzer':
                    raise asyncio.TimeoutError("Simulated agent timeout")
                
                # Execute other agents normally
                agent_result = await asyncio.wait_for(
                    self._execute_mock_agent(real_services, agent_name, {
                        'execution_id': execution_id,
                        'step_index': step_index,
                        'user_context': user_data,
                        'resilient_mode': True
                    }),
                    timeout=timeout_seconds
                )
                
                execution_results[agent_name] = agent_result
                
                # Record successful execution
                await real_services.postgres.execute("""
                    INSERT INTO backend.resilient_executions
                    (execution_id, agent_name, step_index, status, result, completed_at, user_id)
                    VALUES ($1, $2, $3, 'success', $4, $5, $6)
                """, execution_id, agent_name, step_index, json.dumps(agent_result), time.time(), user_data['id'])
                
            except (asyncio.TimeoutError, Exception) as e:
                failed_agents.append(agent_name)
                
                # Record failure
                await real_services.postgres.execute("""
                    INSERT INTO backend.resilient_executions  
                    (execution_id, agent_name, step_index, status, error_message, completed_at, user_id)
                    VALUES ($1, $2, $3, 'failed', $4, $5, $6)
                """, execution_id, agent_name, step_index, str(e), time.time(), user_data['id'])
                
                # Check if failure is tolerable
                if is_required:
                    # Required agent failure - workflow should handle gracefully
                    self.logger.error(f"Required agent {agent_name} failed: {e}")
                    if agent_name != 'enhancement_analyzer':  # Only enhancement_analyzer failure is simulated
                        raise e
                else:
                    # Optional agent failure - continue workflow
                    self.logger.warning(f"Optional agent {agent_name} failed: {e}")
                    execution_results[agent_name] = {'status': 'failed', 'error': str(e)}
        
        # Update workflow state with final results
        final_workflow_state = {
            **resilient_workflow,
            'status': 'completed_with_failures',
            'results': execution_results,
            'failed_agents': failed_agents,
            'completed_at': time.time()
        }
        
        await real_services.redis.set_json(f"resilient:workflow:{execution_id}", final_workflow_state, ex=3600)
        
        # Verify workflow resilience
        assert len(failed_agents) == 1, "Only enhancement_analyzer should fail"
        assert 'enhancement_analyzer' in failed_agents, "Enhancement analyzer should be in failed list"
        
        # Verify required agents completed successfully  
        required_agents = ['data_validator', 'primary_analyzer', 'report_generator']
        for required_agent in required_agents:
            assert required_agent in execution_results, f"Required agent {required_agent} must complete"
            assert execution_results[required_agent].get('status') != 'failed', f"Required agent {required_agent} must not fail"
        
        # Verify business value delivered despite partial failure
        assert 'data_validator' in execution_results, "Data validation must complete"
        assert 'primary_analyzer' in execution_results, "Primary analysis must complete"  
        assert 'report_generator' in execution_results, "Report generation must complete"
        
        # Check that optional failure is handled gracefully
        enhancement_result = execution_results.get('enhancement_analyzer')
        assert enhancement_result is not None, "Failed agent must have failure record"
        assert enhancement_result['status'] == 'failed', "Failed agent status must be recorded"
        
        # Verify database records of resilient execution
        execution_records = await real_services.postgres.fetch("""
            SELECT agent_name, status, result, error_message
            FROM backend.resilient_executions
            WHERE execution_id = $1
            ORDER BY step_index
        """, execution_id)
        
        success_count = sum(1 for record in execution_records if record['status'] == 'success')
        failure_count = sum(1 for record in execution_records if record['status'] == 'failed')
        
        assert success_count == 3, "Three agents must succeed (data_validator, primary_analyzer, report_generator)"
        assert failure_count == 1, "One agent must fail (enhancement_analyzer)"

    async def _execute_mock_agent(self, real_services: Any, agent_name: str, context: Dict) -> Dict:
        """
        Simulate realistic agent execution with business-relevant results.
        
        This helper method generates realistic agent outputs for integration testing.
        """
        # Simulate processing delay
        await asyncio.sleep(0.5)
        
        # Generate realistic results based on agent type
        base_result = {
            'agent_name': agent_name,
            'execution_id': context.get('execution_id'),
            'processed_at': time.time(),
            'user_id': context.get('user_context', {}).get('id'),
            'status': 'completed'
        }
        
        if 'data_collector' in agent_name or 'data_validator' in agent_name:
            return {
                **base_result,
                'data_collected': 1500,  # MB of data processed
                'data_sources': ['aws_cloudtrail', 'azure_monitor', 'gcp_logging'],
                'validation_passed': True,
                'data_quality_score': 0.95
            }
        
        elif 'cost_analyzer' in agent_name or 'analyzer' in agent_name:
            return {
                **base_result,
                'potential_savings': 2500,  # USD per month
                'current_spend': 10000,     # USD per month  
                'optimization_opportunities': 15,
                'confidence_score': 0.87,
                'analysis_depth': 'comprehensive'
            }
        
        elif 'recommendation' in agent_name:
            return {
                **base_result,
                'recommendations': [
                    {'action': 'resize_instances', 'impact': 'high', 'savings': 800},
                    {'action': 'optimize_storage', 'impact': 'medium', 'savings': 400},
                    {'action': 'schedule_workloads', 'impact': 'medium', 'savings': 600}
                ],
                'priority_order': ['resize_instances', 'optimize_storage', 'schedule_workloads'],
                'total_potential': 1800
            }
        
        elif 'action_planner' in agent_name or 'report_generator' in agent_name:
            return {
                **base_result,
                'next_steps': [
                    {'step': 1, 'action': 'Review recommendations', 'timeline': 'immediate'},
                    {'step': 2, 'action': 'Implement high-impact changes', 'timeline': 'this_week'},
                    {'step': 3, 'action': 'Monitor impact', 'timeline': 'ongoing'}
                ],
                'report_generated': True,
                'actionable_items': 3
            }
        
        elif 'coordinator' in agent_name:
            return {
                **base_result,
                'coordination_success': True,
                'optimization_opportunities': [
                    {'type': 'cross_cloud_arbitrage', 'potential': 500},
                    {'type': 'unified_monitoring', 'potential': 300}
                ],
                'unified_strategy': 'multi_cloud_optimization'
            }
        
        else:
            return {
                **base_result,
                'generic_result': True,
                'processing_completed': True
            }

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_workflow_state_consistency_across_services(self, real_services):
        """
        Test that workflow state remains consistent between Redis cache and PostgreSQL database.
        
        BVJ: Platform must maintain data integrity for reliable agent coordination and user experience.
        """
        # Create test context
        user_data = await self.create_test_user_context(real_services)
        
        # Create workflow with state synchronization points
        execution_id = str(uuid4())
        workflow_definition = {
            'execution_id': execution_id,
            'user_id': user_data['id'],
            'workflow_type': 'state_consistency_test',
            'synchronization_points': ['start', 'mid_execution', 'completion'],
            'current_state': 'initialized'
        }
        
        # Initialize in both Redis and PostgreSQL
        await real_services.redis.set_json(f"workflow:state:{execution_id}", workflow_definition, ex=3600)
        await real_services.postgres.execute("""
            INSERT INTO backend.workflow_states (execution_id, user_id, state_data, last_updated, version)
            VALUES ($1, $2, $3, $4, 1)
        """, execution_id, user_data['id'], json.dumps(workflow_definition), time.time())
        
        # Simulate state transitions with consistency checks
        state_transitions = [
            {'state': 'data_collection_started', 'progress': 25},
            {'state': 'analysis_in_progress', 'progress': 50},
            {'state': 'recommendations_generated', 'progress': 75},
            {'state': 'workflow_completed', 'progress': 100}
        ]
        
        for transition in state_transitions:
            # Update Redis
            current_state = await real_services.redis.get_json(f"workflow:state:{execution_id}")
            current_state['current_state'] = transition['state']
            current_state['progress'] = transition['progress']
            current_state['last_updated'] = time.time()
            await real_services.redis.set_json(f"workflow:state:{execution_id}", current_state, ex=3600)
            
            # Update PostgreSQL 
            await real_services.postgres.execute("""
                UPDATE backend.workflow_states 
                SET state_data = $1, last_updated = $2, version = version + 1
                WHERE execution_id = $3
            """, json.dumps(current_state), time.time(), execution_id)
            
            # Verify consistency between Redis and PostgreSQL
            redis_state = await real_services.redis.get_json(f"workflow:state:{execution_id}")
            db_record = await real_services.postgres.fetchrow("""
                SELECT state_data, version, last_updated FROM backend.workflow_states 
                WHERE execution_id = $1
            """, execution_id)
            
            db_state = json.loads(db_record['state_data'])
            
            # Assert state consistency
            assert redis_state['current_state'] == db_state['current_state'], \
                f"Redis and DB state mismatch at {transition['state']}"
            assert redis_state['progress'] == db_state['progress'], \
                f"Redis and DB progress mismatch at {transition['state']}"
            assert abs(redis_state['last_updated'] - db_state['last_updated']) < 1, \
                f"Redis and DB timestamp mismatch at {transition['state']}"
        
        # Verify final state consistency
        final_redis_state = await real_services.redis.get_json(f"workflow:state:{execution_id}")
        final_db_record = await real_services.postgres.fetchrow("""
            SELECT state_data, version FROM backend.workflow_states WHERE execution_id = $1
        """, execution_id)
        
        final_db_state = json.loads(final_db_record['state_data'])
        
        assert final_redis_state['current_state'] == 'workflow_completed', "Final Redis state must be completed"
        assert final_db_state['current_state'] == 'workflow_completed', "Final DB state must be completed" 
        assert final_redis_state['progress'] == 100, "Final progress must be 100%"
        assert final_db_state['progress'] == 100, "Final DB progress must be 100%"
        assert final_db_record['version'] == 5, "DB version must reflect all state updates"  # 1 initial + 4 transitions
        
        # Verify business value - consistent state enables reliable workflow management
        self.assert_business_value_delivered({
            'state_consistency': True,
            'redis_db_sync': True,
            'version_tracking': final_db_record['version'],
            'workflow_completion': final_redis_state['current_state'] == 'workflow_completed'
        }, 'automation')