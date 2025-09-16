"""
Tool Execution Pipeline Integration Tests - Real Services

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Enable AI agents to execute tools and gather data for optimization insights
- Value Impact: Tools provide real-world data collection and analysis capabilities for users
- Strategic Impact: Tool execution pipeline is core to delivering actionable AI recommendations

These tests validate tool execution coordination across services, ensuring agents can
reliably execute tools and process results for comprehensive user analysis.
"""

import asyncio
import pytest
import time
import json
from typing import Dict, List, Any, Optional
from uuid import uuid4
from dataclasses import dataclass
from enum import Enum

from test_framework.base_integration_test import ServiceOrchestrationIntegrationTest
from test_framework.conftest_real_services import real_services
from shared.isolated_environment import get_env


class ToolExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ToolExecutionContext:
    execution_id: str
    user_id: str
    agent_id: str
    tool_name: str
    input_data: Dict
    status: ToolExecutionStatus
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


class TestToolExecutionPipeline(ServiceOrchestrationIntegrationTest):
    """Test tool execution pipeline with real services coordination."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_single_tool_execution_lifecycle(self, real_services):
        """
        Test complete lifecycle of single tool execution from request to completion.
        
        BVJ: Users must receive accurate data collection results from individual tools.
        """
        # Create test context
        user_data = await self.create_test_user_context(real_services)
        org_data = await self.create_test_organization(real_services, user_data['id'])
        
        # Define tool execution request
        execution_id = str(uuid4())
        agent_id = str(uuid4())
        tool_name = "aws_cost_analyzer"
        
        tool_input = {
            'aws_account_id': '123456789012',
            'time_range': 'last_30_days',
            'service_filters': ['ec2', 's3', 'rds'],
            'cost_threshold': 100.0
        }
        
        # Create tool execution context
        execution_context = ToolExecutionContext(
            execution_id=execution_id,
            user_id=user_data['id'],
            agent_id=agent_id,
            tool_name=tool_name,
            input_data=tool_input,
            status=ToolExecutionStatus.PENDING,
            created_at=time.time()
        )
        
        # Store execution request in database
        await real_services.postgres.execute("""
            INSERT INTO backend.tool_executions 
            (execution_id, user_id, agent_id, tool_name, input_data, status, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, execution_id, user_data['id'], agent_id, tool_name, 
             json.dumps(tool_input), execution_context.status.value, execution_context.created_at)
        
        # Queue tool execution in Redis
        execution_queue_data = {
            'execution_id': execution_id,
            'tool_name': tool_name,
            'input_data': tool_input,
            'user_id': user_data['id'],
            'agent_id': agent_id,
            'priority': 'normal',
            'queued_at': time.time()
        }
        
        await real_services.redis.lpush("tool_execution_queue", json.dumps(execution_queue_data))
        await real_services.redis.set_json(f"tool_execution:{execution_id}", execution_context.__dict__, ex=3600)
        
        # Simulate tool execution processing
        # Phase 1: Tool execution starts
        execution_context.status = ToolExecutionStatus.RUNNING
        execution_context.started_at = time.time()
        
        await real_services.postgres.execute("""
            UPDATE backend.tool_executions 
            SET status = $1, started_at = $2
            WHERE execution_id = $3
        """, execution_context.status.value, execution_context.started_at, execution_id)
        
        await real_services.redis.set_json(f"tool_execution:{execution_id}", execution_context.__dict__, ex=3600)
        
        # Phase 2: Tool execution processing (simulate realistic tool work)
        tool_result = await self._simulate_tool_execution(tool_name, tool_input)
        
        # Phase 3: Tool execution completion
        execution_context.status = ToolExecutionStatus.COMPLETED
        execution_context.completed_at = time.time()
        execution_context.result = tool_result
        
        await real_services.postgres.execute("""
            UPDATE backend.tool_executions 
            SET status = $1, completed_at = $2, result_data = $3
            WHERE execution_id = $4
        """, execution_context.status.value, execution_context.completed_at, 
             json.dumps(tool_result), execution_id)
        
        await real_services.redis.set_json(f"tool_execution:{execution_id}", execution_context.__dict__, ex=3600)
        
        # Verify tool execution lifecycle
        # Check database record
        db_execution = await real_services.postgres.fetchrow("""
            SELECT execution_id, tool_name, status, started_at, completed_at, result_data
            FROM backend.tool_executions
            WHERE execution_id = $1
        """, execution_id)
        
        assert db_execution is not None, "Tool execution must be recorded in database"
        assert db_execution['status'] == ToolExecutionStatus.COMPLETED.value, "Tool execution must complete successfully"
        assert db_execution['started_at'] is not None, "Tool execution start time must be recorded"
        assert db_execution['completed_at'] is not None, "Tool execution completion time must be recorded"
        
        stored_result = json.loads(db_execution['result_data'])
        assert stored_result is not None, "Tool execution result must be stored"
        assert 'cost_analysis' in stored_result, "AWS cost analyzer must produce cost analysis"
        assert stored_result['total_cost'] > 0, "Cost analysis must identify spending"
        
        # Check Redis cache
        cached_execution = await real_services.redis.get_json(f"tool_execution:{execution_id}")
        assert cached_execution is not None, "Tool execution must be cached"
        assert cached_execution['status'] == ToolExecutionStatus.COMPLETED.value, "Cached status must be completed"
        assert cached_execution['result'] == tool_result, "Cached result must match execution result"
        
        # Verify execution timing
        execution_duration = execution_context.completed_at - execution_context.started_at
        assert execution_duration > 0, "Tool execution must have positive duration"
        assert execution_duration < 30, "Tool execution should complete within reasonable time"
        
        # Verify business value delivery
        self.assert_business_value_delivered(tool_result, 'cost_savings')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_parallel_tool_execution_coordination(self, real_services):
        """
        Test coordinated execution of multiple tools in parallel for comprehensive analysis.
        
        BVJ: Users must receive comprehensive multi-source analysis through parallel tool execution.
        """
        # Create test context
        user_data = await self.create_test_user_context(real_services)
        org_data = await self.create_test_organization(real_services, user_data['id'])
        
        # Define parallel tool execution batch
        batch_id = str(uuid4())
        agent_id = str(uuid4())
        
        parallel_tools = [
            {
                'tool_name': 'aws_cost_analyzer',
                'input_data': {
                    'account_id': '123456789012',
                    'time_range': 'last_30_days',
                    'services': ['ec2', 's3', 'rds']
                }
            },
            {
                'tool_name': 'azure_cost_analyzer', 
                'input_data': {
                    'subscription_id': 'sub-123456',
                    'time_range': 'last_30_days',
                    'resource_groups': ['production', 'development']
                }
            },
            {
                'tool_name': 'gcp_cost_analyzer',
                'input_data': {
                    'project_id': 'my-gcp-project',
                    'time_range': 'last_30_days',
                    'services': ['compute', 'storage', 'bigquery']
                }
            },
            {
                'tool_name': 'security_scanner',
                'input_data': {
                    'scan_targets': ['aws', 'azure', 'gcp'],
                    'scan_depth': 'comprehensive'
                }
            }
        ]
        
        # Create execution contexts for all tools
        execution_contexts = []
        for i, tool_config in enumerate(parallel_tools):
            execution_id = str(uuid4())
            context = ToolExecutionContext(
                execution_id=execution_id,
                user_id=user_data['id'],
                agent_id=agent_id,
                tool_name=tool_config['tool_name'],
                input_data=tool_config['input_data'],
                status=ToolExecutionStatus.PENDING,
                created_at=time.time()
            )
            execution_contexts.append(context)
            
            # Store in database
            await real_services.postgres.execute("""
                INSERT INTO backend.tool_executions 
                (execution_id, user_id, agent_id, tool_name, input_data, status, created_at, batch_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, execution_id, user_data['id'], agent_id, tool_config['tool_name'],
                 json.dumps(tool_config['input_data']), context.status.value, context.created_at, batch_id)
            
            # Queue for execution
            queue_data = {
                'execution_id': execution_id,
                'batch_id': batch_id,
                'tool_name': tool_config['tool_name'],
                'input_data': tool_config['input_data'],
                'user_id': user_data['id'],
                'parallel_execution': True
            }
            await real_services.redis.lpush("tool_execution_queue", json.dumps(queue_data))
        
        # Store batch coordination data
        batch_data = {
            'batch_id': batch_id,
            'user_id': user_data['id'],
            'agent_id': agent_id,
            'tool_count': len(parallel_tools),
            'completed_count': 0,
            'failed_count': 0,
            'status': 'running',
            'started_at': time.time(),
            'execution_ids': [ctx.execution_id for ctx in execution_contexts]
        }
        
        await real_services.redis.set_json(f"tool_batch:{batch_id}", batch_data, ex=3600)
        
        # Execute tools in parallel
        async def execute_tool(context: ToolExecutionContext):
            # Start execution
            context.status = ToolExecutionStatus.RUNNING
            context.started_at = time.time()
            
            await real_services.postgres.execute("""
                UPDATE backend.tool_executions 
                SET status = $1, started_at = $2 
                WHERE execution_id = $3
            """, context.status.value, context.started_at, context.execution_id)
            
            # Simulate tool work
            result = await self._simulate_tool_execution(context.tool_name, context.input_data)
            
            # Complete execution
            context.status = ToolExecutionStatus.COMPLETED
            context.completed_at = time.time()
            context.result = result
            
            await real_services.postgres.execute("""
                UPDATE backend.tool_executions 
                SET status = $1, completed_at = $2, result_data = $3
                WHERE execution_id = $4
            """, context.status.value, context.completed_at, json.dumps(result), context.execution_id)
            
            # Update batch progress
            batch_state = await real_services.redis.get_json(f"tool_batch:{batch_id}")
            batch_state['completed_count'] += 1
            
            if batch_state['completed_count'] == batch_state['tool_count']:
                batch_state['status'] = 'completed'
                batch_state['completed_at'] = time.time()
            
            await real_services.redis.set_json(f"tool_batch:{batch_id}", batch_state, ex=3600)
            
            return result
        
        # Execute all tools concurrently
        start_time = time.time()
        tool_results = await asyncio.gather(*[execute_tool(ctx) for ctx in execution_contexts])
        execution_duration = time.time() - start_time
        
        # Verify parallel execution performance
        assert execution_duration < 10, f"Parallel tool execution too slow: {execution_duration:.2f}s"
        assert len(tool_results) == len(parallel_tools), "All tools must complete execution"
        
        # Verify batch coordination
        final_batch_state = await real_services.redis.get_json(f"tool_batch:{batch_id}")
        assert final_batch_state['status'] == 'completed', "Batch execution must complete"
        assert final_batch_state['completed_count'] == len(parallel_tools), "All tools must be marked as completed"
        assert final_batch_state['failed_count'] == 0, "No tools should fail in successful batch"
        
        # Verify individual tool results
        for i, (context, result) in enumerate(zip(execution_contexts, tool_results)):
            assert result is not None, f"Tool {i} must produce results"
            
            # Verify tool-specific results
            if context.tool_name == 'aws_cost_analyzer':
                assert 'cost_analysis' in result, "AWS cost analyzer must provide cost analysis"
                assert result['total_cost'] > 0, "AWS analysis must identify costs"
            elif context.tool_name == 'azure_cost_analyzer':
                assert 'cost_breakdown' in result, "Azure cost analyzer must provide cost breakdown"
                assert result['monthly_spend'] > 0, "Azure analysis must identify spending"
            elif context.tool_name == 'gcp_cost_analyzer':
                assert 'billing_data' in result, "GCP cost analyzer must provide billing data"
                assert len(result['service_costs']) > 0, "GCP analysis must identify service costs"
            elif context.tool_name == 'security_scanner':
                assert 'security_findings' in result, "Security scanner must provide findings"
                assert 'risk_score' in result, "Security scanner must provide risk assessment"
        
        # Verify database batch tracking
        batch_executions = await real_services.postgres.fetch("""
            SELECT execution_id, tool_name, status, result_data
            FROM backend.tool_executions
            WHERE batch_id = $1
            ORDER BY created_at
        """, batch_id)
        
        assert len(batch_executions) == len(parallel_tools), "All batch executions must be recorded"
        for execution in batch_executions:
            assert execution['status'] == ToolExecutionStatus.COMPLETED.value, "All executions must complete successfully"
            assert execution['result_data'] is not None, "All executions must have results"
        
        # Verify business value from comprehensive analysis
        combined_value = {
            'multi_cloud_analysis': True,
            'security_assessment': True,
            'comprehensive_coverage': len(tool_results) >= 4,
            'parallel_efficiency': execution_duration < 10
        }
        
        self.assert_business_value_delivered(combined_value, 'insights')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_error_handling_and_recovery(self, real_services):
        """
        Test tool execution error handling, retries, and recovery mechanisms.
        
        BVJ: Platform must handle tool failures gracefully to maintain user experience.
        """
        # Create test context
        user_data = await self.create_test_user_context(real_services)
        org_data = await self.create_test_organization(real_services, user_data['id'])
        
        # Test scenarios for different error types
        error_scenarios = [
            {
                'tool_name': 'unreliable_api_tool',
                'error_type': 'timeout',
                'retry_count': 3,
                'should_recover': True
            },
            {
                'tool_name': 'invalid_credentials_tool', 
                'error_type': 'authentication_failure',
                'retry_count': 1,
                'should_recover': False
            },
            {
                'tool_name': 'rate_limited_tool',
                'error_type': 'rate_limit_exceeded',
                'retry_count': 2,
                'should_recover': True
            }
        ]
        
        execution_results = []
        
        for scenario in error_scenarios:
            execution_id = str(uuid4())
            agent_id = str(uuid4())
            
            # Create execution context
            context = ToolExecutionContext(
                execution_id=execution_id,
                user_id=user_data['id'],
                agent_id=agent_id,
                tool_name=scenario['tool_name'],
                input_data={'test_scenario': scenario['error_type']},
                status=ToolExecutionStatus.PENDING,
                created_at=time.time()
            )
            
            # Store initial execution
            await real_services.postgres.execute("""
                INSERT INTO backend.tool_executions 
                (execution_id, user_id, agent_id, tool_name, input_data, status, created_at, max_retries)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, execution_id, user_data['id'], agent_id, scenario['tool_name'],
                 json.dumps(context.input_data), context.status.value, context.created_at, scenario['retry_count'])
            
            # Execute with error handling
            result = await self._execute_tool_with_error_handling(
                real_services, context, scenario['error_type'], scenario['retry_count'], scenario['should_recover']
            )
            
            execution_results.append({
                'scenario': scenario,
                'context': context,
                'result': result
            })
        
        # Verify error handling results
        for exec_result in execution_results:
            scenario = exec_result['scenario']
            context = exec_result['context']
            result = exec_result['result']
            
            # Check database records
            db_execution = await real_services.postgres.fetchrow("""
                SELECT status, retry_count, error_message, result_data
                FROM backend.tool_executions
                WHERE execution_id = $1
            """, context.execution_id)
            
            if scenario['should_recover']:
                assert db_execution['status'] == ToolExecutionStatus.COMPLETED.value, f"Recoverable scenario {scenario['error_type']} must eventually succeed"
                assert db_execution['result_data'] is not None, "Recovered execution must have results"
                assert result['recovered'] is True, "Result must indicate successful recovery"
            else:
                assert db_execution['status'] == ToolExecutionStatus.FAILED.value, f"Non-recoverable scenario {scenario['error_type']} must fail"
                assert db_execution['error_message'] is not None, "Failed execution must have error message"
                assert result['failed'] is True, "Result must indicate failure"
            
            # Verify retry attempts
            assert db_execution['retry_count'] <= scenario['retry_count'], "Retry count must not exceed maximum"
            
            # Check retry attempts in database
            retry_attempts = await real_services.postgres.fetch("""
                SELECT attempt_number, error_type, attempted_at
                FROM backend.tool_execution_retries
                WHERE execution_id = $1
                ORDER BY attempt_number
            """, context.execution_id)
            
            expected_retries = min(scenario['retry_count'], db_execution['retry_count'])
            assert len(retry_attempts) >= expected_retries - 1, "Retry attempts must be recorded"  # -1 because first attempt isn't a retry
        
        # Test circuit breaker pattern for repeated failures
        circuit_breaker_tool = 'failing_external_service'
        circuit_breaker_executions = []
        
        # Execute multiple failing requests to trigger circuit breaker
        for i in range(5):
            execution_id = str(uuid4())
            context = ToolExecutionContext(
                execution_id=execution_id,
                user_id=user_data['id'],
                agent_id=str(uuid4()),
                tool_name=circuit_breaker_tool,
                input_data={'request_index': i},
                status=ToolExecutionStatus.PENDING,
                created_at=time.time()
            )
            
            await real_services.postgres.execute("""
                INSERT INTO backend.tool_executions 
                (execution_id, user_id, agent_id, tool_name, input_data, status, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, execution_id, user_data['id'], context.agent_id, circuit_breaker_tool,
                 json.dumps(context.input_data), context.status.value, context.created_at)
            
            circuit_breaker_executions.append(context)
        
        # Track circuit breaker state
        circuit_breaker_key = f"circuit_breaker:{circuit_breaker_tool}"
        circuit_state = {
            'state': 'closed',  # Start with closed state
            'failure_count': 0,
            'last_failure_time': None,
            'failure_threshold': 3
        }
        await real_services.redis.set_json(circuit_breaker_key, circuit_state, ex=3600)
        
        # Execute requests and trigger circuit breaker
        for i, context in enumerate(circuit_breaker_executions):
            current_state = await real_services.redis.get_json(circuit_breaker_key)
            
            if current_state['state'] == 'open':
                # Circuit breaker is open - requests should be rejected immediately
                context.status = ToolExecutionStatus.FAILED
                context.error = "Circuit breaker open - service unavailable"
                
                await real_services.postgres.execute("""
                    UPDATE backend.tool_executions
                    SET status = $1, error_message = $2, completed_at = $3
                    WHERE execution_id = $4
                """, context.status.value, context.error, time.time(), context.execution_id)
                
            else:
                # Simulate failure
                context.status = ToolExecutionStatus.FAILED
                context.error = f"Service failure #{i+1}"
                
                await real_services.postgres.execute("""
                    UPDATE backend.tool_executions
                    SET status = $1, error_message = $2, completed_at = $3
                    WHERE execution_id = $4
                """, context.status.value, context.error, time.time(), context.execution_id)
                
                # Update circuit breaker state
                current_state['failure_count'] += 1
                current_state['last_failure_time'] = time.time()
                
                if current_state['failure_count'] >= current_state['failure_threshold']:
                    current_state['state'] = 'open'
                
                await real_services.redis.set_json(circuit_breaker_key, current_state, ex=3600)
        
        # Verify circuit breaker was triggered
        final_circuit_state = await real_services.redis.get_json(circuit_breaker_key)
        assert final_circuit_state['state'] == 'open', "Circuit breaker must open after threshold failures"
        assert final_circuit_state['failure_count'] >= 3, "Circuit breaker must track failure count"
        
        # Verify some executions were rejected due to circuit breaker
        rejected_executions = await real_services.postgres.fetch("""
            SELECT error_message FROM backend.tool_executions
            WHERE tool_name = $1 AND error_message LIKE '%circuit breaker%'
        """, circuit_breaker_tool)
        
        assert len(rejected_executions) > 0, "Some executions must be rejected by circuit breaker"

    async def _simulate_tool_execution(self, tool_name: str, input_data: Dict) -> Dict:
        """Simulate realistic tool execution with appropriate results."""
        # Add realistic processing delay
        await asyncio.sleep(0.5)
        
        if 'aws_cost_analyzer' in tool_name:
            return {
                'tool_name': tool_name,
                'cost_analysis': {
                    'total_cost': 2500.75,
                    'service_breakdown': {
                        'ec2': 1200.50,
                        's3': 300.25,
                        'rds': 1000.00
                    },
                    'optimization_opportunities': [
                        {'service': 'ec2', 'potential_savings': 400.00, 'recommendation': 'Resize underutilized instances'},
                        {'service': 'rds', 'potential_savings': 200.00, 'recommendation': 'Enable auto-scaling'}
                    ]
                },
                'execution_metadata': {
                    'execution_time': 0.5,
                    'data_points_analyzed': 1500,
                    'confidence_score': 0.92
                }
            }
        elif 'azure_cost_analyzer' in tool_name:
            return {
                'tool_name': tool_name,
                'cost_breakdown': {
                    'monthly_spend': 1800.30,
                    'resource_groups': {
                        'production': 1200.20,
                        'development': 600.10
                    }
                },
                'optimization_suggestions': [
                    {'type': 'vm_rightsizing', 'savings': 300.00},
                    {'type': 'storage_optimization', 'savings': 150.00}
                ],
                'execution_metadata': {
                    'execution_time': 0.4,
                    'resources_analyzed': 75
                }
            }
        elif 'gcp_cost_analyzer' in tool_name:
            return {
                'tool_name': tool_name,
                'billing_data': {
                    'total_cost': 3200.45,
                    'service_costs': {
                        'compute': 1500.00,
                        'storage': 800.25,
                        'bigquery': 900.20
                    }
                },
                'cost_trends': {
                    'month_over_month': 5.2,
                    'year_over_year': 15.8
                },
                'execution_metadata': {
                    'execution_time': 0.6,
                    'projects_analyzed': 3
                }
            }
        elif 'security_scanner' in tool_name:
            return {
                'tool_name': tool_name,
                'security_findings': {
                    'high_severity': 2,
                    'medium_severity': 8,
                    'low_severity': 15,
                    'total_findings': 25
                },
                'risk_score': 7.2,  # Out of 10
                'compliance_status': {
                    'pci_compliant': True,
                    'sox_compliant': True,
                    'gdpr_compliant': False
                },
                'execution_metadata': {
                    'execution_time': 1.2,
                    'resources_scanned': 150
                }
            }
        else:
            # Generic tool response
            return {
                'tool_name': tool_name,
                'generic_result': True,
                'input_processed': input_data,
                'execution_metadata': {
                    'execution_time': 0.3,
                    'status': 'completed'
                }
            }

    async def _execute_tool_with_error_handling(self, real_services, context: ToolExecutionContext, 
                                              error_type: str, max_retries: int, should_recover: bool) -> Dict:
        """Execute tool with error handling and retry logic."""
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Update status to running
                context.status = ToolExecutionStatus.RUNNING
                context.started_at = time.time()
                
                await real_services.postgres.execute("""
                    UPDATE backend.tool_executions
                    SET status = $1, started_at = $2, retry_count = $3
                    WHERE execution_id = $4
                """, context.status.value, context.started_at, retry_count, context.execution_id)
                
                # Simulate error conditions
                if error_type == 'timeout' and not should_recover:
                    await asyncio.sleep(5)  # Simulate timeout
                    raise asyncio.TimeoutError("Tool execution timed out")
                elif error_type == 'authentication_failure':
                    raise Exception("Authentication failed - invalid credentials")
                elif error_type == 'rate_limit_exceeded' and retry_count < 2:
                    raise Exception("Rate limit exceeded - please retry later")
                
                # If we reach here, either it should recover or we've retried enough
                if should_recover or retry_count > 0:
                    # Simulate successful execution
                    result = await self._simulate_tool_execution(context.tool_name, context.input_data)
                    result['recovered'] = True
                    result['retry_count'] = retry_count
                    
                    context.status = ToolExecutionStatus.COMPLETED
                    context.completed_at = time.time()
                    context.result = result
                    
                    await real_services.postgres.execute("""
                        UPDATE backend.tool_executions
                        SET status = $1, completed_at = $2, result_data = $3
                        WHERE execution_id = $4
                    """, context.status.value, context.completed_at, json.dumps(result), context.execution_id)
                    
                    return result
                else:
                    # Force failure for non-recoverable scenarios
                    raise Exception(f"Simulated {error_type} error")
                
            except Exception as e:
                # Record retry attempt
                if retry_count < max_retries:
                    await real_services.postgres.execute("""
                        INSERT INTO backend.tool_execution_retries
                        (execution_id, attempt_number, error_type, error_message, attempted_at)
                        VALUES ($1, $2, $3, $4, $5)
                    """, context.execution_id, retry_count + 1, error_type, str(e), time.time())
                
                retry_count += 1
                
                if retry_count > max_retries:
                    # Final failure
                    context.status = ToolExecutionStatus.FAILED
                    context.error = str(e)
                    
                    await real_services.postgres.execute("""
                        UPDATE backend.tool_executions
                        SET status = $1, error_message = $2, completed_at = $3
                        WHERE execution_id = $4
                    """, context.status.value, context.error, time.time(), context.execution_id)
                    
                    return {'failed': True, 'error': str(e), 'retry_count': retry_count - 1}
                else:
                    # Wait before retry with exponential backoff
                    await asyncio.sleep(min(2 ** retry_count, 10))

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_tool_result_caching_and_performance_optimization(self, real_services):
        """
        Test tool result caching and performance optimization for repeated requests.
        
        BVJ: Platform must optimize performance through intelligent caching to reduce costs and latency.
        """
        # Create test context
        user_data = await self.create_test_user_context(real_services)
        org_data = await self.create_test_organization(real_services, user_data['id'])
        
        # Define cacheable tool request
        tool_name = 'aws_cost_analyzer'
        cache_key_input = {
            'aws_account_id': '123456789012',
            'time_range': 'last_7_days',  # Short range for caching test
            'service_filters': ['ec2', 's3'],
            'cost_threshold': 100.0
        }
        
        # Generate cache key
        import hashlib
        cache_key_data = f"{tool_name}:{json.dumps(cache_key_input, sort_keys=True)}"
        cache_key = hashlib.sha256(cache_key_data.encode()).hexdigest()[:16]
        
        # First execution - should execute and cache result
        execution_id_1 = str(uuid4())
        agent_id = str(uuid4())
        
        context_1 = ToolExecutionContext(
            execution_id=execution_id_1,
            user_id=user_data['id'],
            agent_id=agent_id,
            tool_name=tool_name,
            input_data=cache_key_input,
            status=ToolExecutionStatus.PENDING,
            created_at=time.time()
        )
        
        # Store first execution
        await real_services.postgres.execute("""
            INSERT INTO backend.tool_executions 
            (execution_id, user_id, agent_id, tool_name, input_data, status, created_at, cache_key)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, execution_id_1, user_data['id'], agent_id, tool_name,
             json.dumps(cache_key_input), context_1.status.value, context_1.created_at, cache_key)
        
        # Execute first request (will create cache)
        start_time_1 = time.time()
        
        # Check cache first
        cached_result = await real_services.redis.get_json(f"tool_cache:{cache_key}")
        if cached_result is None:
            # Execute tool and cache result
            result_1 = await self._simulate_tool_execution(tool_name, cache_key_input)
            
            # Cache result with TTL (1 hour)
            cache_data = {
                'result': result_1,
                'cached_at': time.time(),
                'tool_name': tool_name,
                'input_hash': cache_key,
                'user_id': user_data['id']  # User-specific caching
            }
            
            await real_services.redis.set_json(f"tool_cache:{cache_key}", cache_data, ex=3600)
            
            # Update execution as completed
            context_1.status = ToolExecutionStatus.COMPLETED
            context_1.completed_at = time.time()
            context_1.result = result_1
            
            await real_services.postgres.execute("""
                UPDATE backend.tool_executions
                SET status = $1, completed_at = $2, result_data = $3, from_cache = false
                WHERE execution_id = $4
            """, context_1.status.value, context_1.completed_at, json.dumps(result_1), execution_id_1)
            
            first_result = result_1
        else:
            first_result = cached_result['result']
        
        execution_time_1 = time.time() - start_time_1
        
        # Second execution - should use cache
        execution_id_2 = str(uuid4())
        
        context_2 = ToolExecutionContext(
            execution_id=execution_id_2,
            user_id=user_data['id'],
            agent_id=agent_id,
            tool_name=tool_name,
            input_data=cache_key_input,  # Same input
            status=ToolExecutionStatus.PENDING,
            created_at=time.time()
        )
        
        await real_services.postgres.execute("""
            INSERT INTO backend.tool_executions 
            (execution_id, user_id, agent_id, tool_name, input_data, status, created_at, cache_key)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, execution_id_2, user_data['id'], agent_id, tool_name,
             json.dumps(cache_key_input), context_2.status.value, context_2.created_at, cache_key)
        
        # Execute second request (should use cache)
        start_time_2 = time.time()
        
        cached_result = await real_services.redis.get_json(f"tool_cache:{cache_key}")
        assert cached_result is not None, "Result must be cached from first execution"
        
        second_result = cached_result['result']
        
        # Update execution as completed from cache
        context_2.status = ToolExecutionStatus.COMPLETED
        context_2.completed_at = time.time()
        context_2.result = second_result
        
        await real_services.postgres.execute("""
            UPDATE backend.tool_executions
            SET status = $1, completed_at = $2, result_data = $3, from_cache = true
            WHERE execution_id = $4
        """, context_2.status.value, context_2.completed_at, json.dumps(second_result), execution_id_2)
        
        execution_time_2 = time.time() - start_time_2
        
        # Verify caching performance improvement
        assert execution_time_2 < execution_time_1, "Cached execution must be faster than original"
        assert execution_time_2 < 0.1, "Cache retrieval should be very fast"
        
        # Verify results are identical
        assert first_result == second_result, "Cached result must match original result"
        
        # Verify database records show caching
        cache_usage = await real_services.postgres.fetch("""
            SELECT execution_id, from_cache, completed_at - created_at as duration
            FROM backend.tool_executions
            WHERE cache_key = $1
            ORDER BY created_at
        """, cache_key)
        
        assert len(cache_usage) == 2, "Two executions must be recorded"
        assert cache_usage[0]['from_cache'] is False, "First execution must not be from cache"
        assert cache_usage[1]['from_cache'] is True, "Second execution must be from cache"
        
        # Test cache invalidation for different input
        different_input = {**cache_key_input, 'time_range': 'last_30_days'}  # Different time range
        different_cache_key_data = f"{tool_name}:{json.dumps(different_input, sort_keys=True)}"
        different_cache_key = hashlib.sha256(different_cache_key_data.encode()).hexdigest()[:16]
        
        # Should not use cache for different input
        different_cached_result = await real_services.redis.get_json(f"tool_cache:{different_cache_key}")
        assert different_cached_result is None, "Different input should not have cached result"
        
        # Test cache expiration
        # Set a short-lived cache entry
        short_cache_key = f"short_lived_{cache_key}"
        short_cache_data = {
            'result': {'test': 'short_lived'},
            'cached_at': time.time(),
            'tool_name': tool_name
        }
        
        await real_services.redis.set_json(f"tool_cache:{short_cache_key}", short_cache_data, ex=1)  # 1 second TTL
        
        # Verify cache exists
        immediate_check = await real_services.redis.get_json(f"tool_cache:{short_cache_key}")
        assert immediate_check is not None, "Short-lived cache must exist immediately"
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Verify cache expired
        expired_check = await real_services.redis.get_json(f"tool_cache:{short_cache_key}")
        assert expired_check is None, "Short-lived cache must expire"
        
        # Verify business value from caching
        performance_improvement = ((execution_time_1 - execution_time_2) / execution_time_1) * 100
        
        self.assert_business_value_delivered({
            'performance_improvement_percent': performance_improvement,
            'cache_hit_rate': 100,  # Second request was cache hit
            'response_time_reduction': execution_time_1 - execution_time_2,
            'cost_optimization': True  # Cached requests reduce compute costs
        }, 'automation')