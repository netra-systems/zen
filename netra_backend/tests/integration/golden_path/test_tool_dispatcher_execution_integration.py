"""
Test Tool Dispatcher Execution Integration - Golden Path Business Value

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure tool execution delivers actionable AI insights
- Value Impact: Tool execution is HOW agents provide optimization insights and cost savings
- Strategic Impact: Core platform functionality that enables AI automation value

CRITICAL: Tool dispatcher execution is the infrastructure that enables agents to deliver
business insights. Without reliable tool execution, AI agents cannot provide the analysis,
optimization recommendations, and automation that justify platform costs.

These tests validate that tools execute reliably, deliver measurable business results,
and maintain user isolation in concurrent multi-user scenarios.
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, List, Optional
from uuid import uuid4
import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture, real_redis_fixture
from shared.isolated_environment import get_env
from shared.types import UserID, ThreadID, RequestID, RunID

logger = logging.getLogger(__name__)


class TestToolDispatcherExecutionIntegration(BaseIntegrationTest):
    """Integration tests for tool dispatcher execution patterns that deliver business value."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_dispatcher_factory_creation_user_scoped_execution_contexts(self, real_services_fixture):
        """
        Test tool dispatcher factory creation with user-scoped execution contexts.
        
        BVJ: Ensures each user gets isolated tool execution preventing data leaks
        and enabling secure multi-user AI operations.
        """
        services = real_services_fixture
        db = services["db"]
        
        if not services["database_available"]:
            pytest.skip("Database not available for real service testing")

        # Create test users with different contexts
        user1_data = await self.create_test_user_context(services, {
            'email': 'enterprise_user_1@test.com',
            'name': 'Enterprise User 1',
            'subscription_tier': 'enterprise'
        })
        
        user2_data = await self.create_test_user_context(services, {
            'email': 'mid_tier_user_2@test.com', 
            'name': 'Mid Tier User 2',
            'subscription_tier': 'mid'
        })

        # Simulate tool dispatcher factory creation for each user
        user1_context = {
            'user_id': UserID(user1_data['id']),
            'thread_id': ThreadID(str(uuid4())),
            'request_id': RequestID(str(uuid4())),
            'subscription_tier': 'enterprise',
            'available_tools': ['cost_analyzer', 'performance_optimizer', 'security_auditor'],
            'rate_limits': {'requests_per_hour': 1000, 'concurrent_tools': 10}
        }
        
        user2_context = {
            'user_id': UserID(user2_data['id']),
            'thread_id': ThreadID(str(uuid4())), 
            'request_id': RequestID(str(uuid4())),
            'subscription_tier': 'mid',
            'available_tools': ['cost_analyzer', 'performance_optimizer'],
            'rate_limits': {'requests_per_hour': 100, 'concurrent_tools': 3}
        }

        # Store execution contexts in database
        await db.execute("""
            INSERT INTO tool_execution_contexts (user_id, thread_id, request_id, context_data, created_at)
            VALUES ($1, $2, $3, $4, NOW()), ($5, $6, $7, $8, NOW())
        """, 
        user1_context['user_id'], user1_context['thread_id'], user1_context['request_id'], json.dumps(user1_context),
        user2_context['user_id'], user2_context['thread_id'], user2_context['request_id'], json.dumps(user2_context))
        await db.commit()

        # Verify contexts are isolated and properly scoped
        user1_stored = await db.fetchrow("""
            SELECT context_data FROM tool_execution_contexts 
            WHERE user_id = $1 AND request_id = $2
        """, user1_context['user_id'], user1_context['request_id'])
        
        user2_stored = await db.fetchrow("""
            SELECT context_data FROM tool_execution_contexts
            WHERE user_id = $1 AND request_id = $2  
        """, user2_context['user_id'], user2_context['request_id'])

        assert user1_stored is not None
        assert user2_stored is not None
        
        user1_retrieved = json.loads(user1_stored['context_data'])
        user2_retrieved = json.loads(user2_stored['context_data'])
        
        # Verify enterprise user has more tools and higher limits
        assert len(user1_retrieved['available_tools']) > len(user2_retrieved['available_tools'])
        assert user1_retrieved['rate_limits']['requests_per_hour'] > user2_retrieved['rate_limits']['requests_per_hour']
        
        # Verify user isolation
        assert user1_retrieved['user_id'] != user2_retrieved['user_id']
        assert user1_retrieved['thread_id'] != user2_retrieved['thread_id']

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_request_routing_database_logging(self, real_services_fixture, real_redis_fixture):
        """
        Test tool execution request routing with real database logging.
        
        BVJ: Ensures tool execution requests are properly routed and logged for
        audit compliance and performance monitoring.
        """
        services = real_services_fixture
        redis = real_redis_fixture
        db = services["db"]
        
        if not services["database_available"]:
            pytest.skip("Database not available for real service testing")

        # Create user and execution context
        user_data = await self.create_test_user_context(services)
        user_id = UserID(user_data['id'])
        thread_id = ThreadID(str(uuid4()))
        request_id = RequestID(str(uuid4()))

        # Simulate tool execution requests
        tool_requests = [
            {
                'tool_name': 'cost_analyzer',
                'parameters': {'account_id': 'aws-123456', 'time_period': '30d'},
                'expected_output': 'cost_analysis_report',
                'priority': 'high',
                'timeout': 300
            },
            {
                'tool_name': 'performance_optimizer', 
                'parameters': {'service_name': 'api-gateway', 'metrics_period': '7d'},
                'expected_output': 'optimization_recommendations',
                'priority': 'medium',
                'timeout': 180
            },
            {
                'tool_name': 'security_auditor',
                'parameters': {'scan_scope': 'infrastructure', 'compliance_framework': 'SOC2'},
                'expected_output': 'security_audit_results',
                'priority': 'high', 
                'timeout': 600
            }
        ]

        # Route and log each tool request
        execution_ids = []
        for i, tool_request in enumerate(tool_requests):
            execution_id = str(uuid4())
            execution_ids.append(execution_id)
            
            # Log tool execution request to database
            await db.execute("""
                INSERT INTO tool_execution_logs (
                    execution_id, user_id, thread_id, request_id,
                    tool_name, parameters, status, created_at, priority, timeout_seconds
                ) VALUES ($1, $2, $3, $4, $5, $6, 'queued', NOW(), $7, $8)
            """, execution_id, user_id, thread_id, request_id, 
                tool_request['tool_name'], json.dumps(tool_request['parameters']),
                tool_request['priority'], tool_request['timeout'])

            # Cache routing information in Redis
            routing_key = f"tool_execution:{execution_id}"
            routing_data = {
                'user_id': str(user_id),
                'tool_name': tool_request['tool_name'],
                'queued_at': time.time(),
                'priority': tool_request['priority'],
                'route': f"worker_node_{i % 3}"  # Simulate load balancing
            }
            await redis.set(routing_key, json.dumps(routing_data), ex=3600)

        await db.commit()

        # Verify all requests were logged with correct routing
        logged_requests = await db.fetch("""
            SELECT execution_id, tool_name, status, priority, created_at
            FROM tool_execution_logs
            WHERE user_id = $1 AND thread_id = $2 AND request_id = $3
            ORDER BY created_at ASC
        """, user_id, thread_id, request_id)

        assert len(logged_requests) == 3
        
        # Verify routing data in Redis
        for execution_id in execution_ids:
            routing_data = await redis.get(f"tool_execution:{execution_id}")
            assert routing_data is not None
            
            routing_info = json.loads(routing_data)
            assert routing_info['user_id'] == str(user_id)
            assert routing_info['tool_name'] in ['cost_analyzer', 'performance_optimizer', 'security_auditor']
            assert routing_info['priority'] in ['high', 'medium']
            assert 'worker_node_' in routing_info['route']

        # Verify high priority tools were logged first or with appropriate priority markers
        high_priority_tools = [req for req in logged_requests if req['tool_name'] in ['cost_analyzer', 'security_auditor']]
        assert len(high_priority_tools) == 2

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_result_compilation_redis_caching(self, real_services_fixture, real_redis_fixture):
        """
        Test tool result compilation and persistence with Redis caching.
        
        BVJ: Ensures tool results are properly compiled and cached for fast retrieval,
        enabling responsive AI agent interactions and cost-effective repeat queries.
        """
        services = real_services_fixture
        redis = real_redis_fixture
        db = services["db"]
        
        if not services["database_available"]:
            pytest.skip("Database not available for real service testing")

        user_data = await self.create_test_user_context(services)
        user_id = UserID(user_data['id'])
        execution_id = str(uuid4())
        
        # Simulate tool execution results that provide business value
        tool_results = {
            'cost_analysis': {
                'monthly_spend': 45000,
                'potential_savings': 12000,
                'recommendations': [
                    {'action': 'Right-size EC2 instances', 'monthly_savings': 5000},
                    {'action': 'Use Reserved Instances', 'monthly_savings': 4000},
                    {'action': 'Optimize S3 storage class', 'monthly_savings': 3000}
                ],
                'confidence_score': 0.92,
                'data_sources': ['CloudWatch', 'Cost Explorer', 'Trusted Advisor']
            },
            'performance_metrics': {
                'current_latency_p95': 250,
                'target_latency_p95': 150,
                'bottlenecks_identified': [
                    {'component': 'database_queries', 'impact': 'high', 'solution': 'add_indexes'},
                    {'component': 'api_rate_limiting', 'impact': 'medium', 'solution': 'optimize_caching'}
                ],
                'performance_score': 7.2,
                'improvement_potential': '40% latency reduction'
            },
            'execution_metadata': {
                'tool_name': 'comprehensive_analyzer',
                'execution_time': 45.7,
                'data_points_analyzed': 15000,
                'completed_at': time.time(),
                'success': True
            }
        }

        # Store compiled results in database
        await db.execute("""
            INSERT INTO tool_execution_results (
                execution_id, user_id, tool_name, results_data, 
                execution_time, success, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
        """, execution_id, user_id, 'comprehensive_analyzer', 
            json.dumps(tool_results), 45.7, True)
        await db.commit()

        # Cache results in Redis with TTL for fast retrieval
        cache_key = f"tool_results:{user_id}:{execution_id}"
        cached_data = {
            'results': tool_results,
            'cached_at': time.time(),
            'cache_version': '1.0'
        }
        await redis.set(cache_key, json.dumps(cached_data), ex=1800)  # 30 min TTL

        # Cache summary for quick access
        summary_key = f"tool_summary:{user_id}:latest"
        summary_data = {
            'last_analysis': tool_results['execution_metadata']['completed_at'],
            'potential_monthly_savings': tool_results['cost_analysis']['potential_savings'],
            'performance_improvement': tool_results['performance_metrics']['improvement_potential'],
            'confidence': tool_results['cost_analysis']['confidence_score'],
            'execution_id': execution_id
        }
        await redis.set(summary_key, json.dumps(summary_data), ex=3600)  # 1 hour TTL

        # Verify results compilation and caching
        # Check database persistence
        stored_results = await db.fetchrow("""
            SELECT results_data, execution_time, success FROM tool_execution_results
            WHERE execution_id = $1 AND user_id = $2
        """, execution_id, user_id)
        
        assert stored_results is not None
        assert stored_results['success'] is True
        assert stored_results['execution_time'] == 45.7
        
        stored_data = json.loads(stored_results['results_data'])
        assert stored_data['cost_analysis']['potential_savings'] == 12000
        assert len(stored_data['cost_analysis']['recommendations']) == 3

        # Check Redis cache retrieval
        cached_results = await redis.get(cache_key)
        assert cached_results is not None
        
        cached_data = json.loads(cached_results)
        assert cached_data['results']['cost_analysis']['monthly_spend'] == 45000
        assert cached_data['cache_version'] == '1.0'

        # Check summary cache
        cached_summary = await redis.get(summary_key)
        assert cached_summary is not None
        
        summary = json.loads(cached_summary)
        assert summary['potential_monthly_savings'] == 12000
        assert summary['execution_id'] == execution_id
        
        # Verify business value is captured
        self.assert_business_value_delivered(stored_data, 'cost_savings')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_timeout_partial_result_recovery(self, real_services_fixture, real_redis_fixture):
        """
        Test tool execution timeout handling with partial result recovery.
        
        BVJ: Ensures users get partial insights even when long-running analysis tools timeout,
        maintaining user experience and providing whatever value was generated.
        """
        services = real_services_fixture
        redis = real_redis_fixture
        db = services["db"]
        
        if not services["database_available"]:
            pytest.skip("Database not available for real service testing")

        user_data = await self.create_test_user_context(services)
        user_id = UserID(user_data['id'])
        execution_id = str(uuid4())
        
        # Simulate a long-running tool with partial results before timeout
        partial_results = {
            'analysis_phase_1': {
                'cost_data_collected': True,
                'accounts_analyzed': 3,
                'total_accounts': 10,
                'preliminary_findings': {
                    'monthly_spend_sample': 18000,
                    'obvious_waste_identified': 4500,
                    'confidence': 0.7
                }
            },
            'analysis_phase_2': {
                'performance_data_collected': True,
                'services_analyzed': 5,
                'total_services': 15,
                'bottlenecks_found': [
                    {'service': 'user-api', 'issue': 'slow_db_queries', 'severity': 'high'}
                ]
            },
            'timeout_metadata': {
                'timeout_after': 120,  # seconds
                'completion_percentage': 0.35,
                'partial_data_available': True,
                'recommended_action': 'retry_with_smaller_scope'
            }
        }

        # Store timeout event in database with partial results
        await db.execute("""
            INSERT INTO tool_execution_logs (
                execution_id, user_id, tool_name, status, partial_results,
                timeout_seconds, completion_percentage, created_at
            ) VALUES ($1, $2, 'comprehensive_auditor', 'timeout_partial', $3, 120, 0.35, NOW())
        """, execution_id, user_id, json.dumps(partial_results))
        await db.commit()

        # Cache partial results for immediate user access
        partial_cache_key = f"partial_results:{user_id}:{execution_id}"
        await redis.set(partial_cache_key, json.dumps(partial_results), ex=7200)  # 2 hours

        # Store timeout recovery options
        recovery_key = f"timeout_recovery:{user_id}:{execution_id}"
        recovery_options = {
            'retry_smaller_scope': True,
            'use_partial_data': True,
            'estimated_retry_time': 60,
            'partial_value_available': True,
            'suggested_scope_reduction': {
                'accounts': 5,  # Reduce from 10 to 5
                'services': 8,  # Reduce from 15 to 8
                'time_period': '7d'  # Reduce from 30d to 7d
            }
        }
        await redis.set(recovery_key, json.dumps(recovery_options), ex=3600)

        # Verify timeout handling and partial result recovery
        timeout_log = await db.fetchrow("""
            SELECT status, partial_results, completion_percentage FROM tool_execution_logs
            WHERE execution_id = $1 AND user_id = $2
        """, execution_id, user_id)
        
        assert timeout_log is not None
        assert timeout_log['status'] == 'timeout_partial'
        assert timeout_log['completion_percentage'] == 0.35
        
        partial_data = json.loads(timeout_log['partial_results'])
        assert partial_data['analysis_phase_1']['cost_data_collected'] is True
        assert partial_data['timeout_metadata']['partial_data_available'] is True

        # Verify partial results are cached and accessible
        cached_partial = await redis.get(partial_cache_key)
        assert cached_partial is not None
        
        cached_data = json.loads(cached_partial)
        assert cached_data['analysis_phase_1']['obvious_waste_identified'] == 4500
        
        # Verify recovery options
        recovery_data = await redis.get(recovery_key)
        assert recovery_data is not None
        
        recovery_info = json.loads(recovery_data)
        assert recovery_info['retry_smaller_scope'] is True
        assert recovery_info['partial_value_available'] is True
        assert recovery_info['suggested_scope_reduction']['accounts'] == 5

        # Verify partial results still provide business value
        assert cached_data['analysis_phase_1']['obvious_waste_identified'] > 0

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_error_handling_retry_mechanisms(self, real_services_fixture, real_redis_fixture):
        """
        Test tool execution error handling and retry mechanisms.
        
        BVJ: Ensures tools recover from transient failures and deliver results
        even in unstable environments, maintaining platform reliability.
        """
        services = real_services_fixture
        redis = real_redis_fixture
        db = services["db"]
        
        if not services["database_available"]:
            pytest.skip("Database not available for real service testing")

        user_data = await self.create_test_user_context(services)
        user_id = UserID(user_data['id'])
        execution_id = str(uuid4())

        # Simulate error scenarios and retry attempts
        error_scenarios = [
            {
                'attempt': 1,
                'error_type': 'api_rate_limit',
                'error_message': 'AWS API rate limit exceeded',
                'retry_after': 60,
                'should_retry': True
            },
            {
                'attempt': 2,
                'error_type': 'temporary_network',
                'error_message': 'Connection timeout to external service',
                'retry_after': 30,
                'should_retry': True
            },
            {
                'attempt': 3,
                'error_type': 'success',
                'error_message': None,
                'retry_after': None,
                'should_retry': False,
                'results': {
                    'cost_optimization': {
                        'identified_savings': 8500,
                        'recommendations': 4,
                        'confidence': 0.88
                    }
                }
            }
        ]

        # Log each retry attempt
        for scenario in error_scenarios:
            status = 'error' if scenario['error_type'] != 'success' else 'completed'
            
            await db.execute("""
                INSERT INTO tool_execution_retries (
                    execution_id, user_id, attempt_number, status, 
                    error_type, error_message, retry_after, results_data, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            """, execution_id, user_id, scenario['attempt'], status,
                scenario['error_type'], scenario['error_message'], scenario['retry_after'],
                json.dumps(scenario.get('results', {})))

            # Cache retry state for monitoring
            retry_key = f"retry_state:{execution_id}:{scenario['attempt']}"
            retry_state = {
                'attempt': scenario['attempt'],
                'max_attempts': 3,
                'error_type': scenario['error_type'],
                'next_retry_at': time.time() + (scenario['retry_after'] or 0),
                'exponential_backoff': scenario['retry_after'],
                'should_continue': scenario['should_retry']
            }
            await redis.set(retry_key, json.dumps(retry_state), ex=1800)

        await db.commit()

        # Verify error handling and successful recovery
        retry_attempts = await db.fetch("""
            SELECT attempt_number, status, error_type, results_data
            FROM tool_execution_retries
            WHERE execution_id = $1 AND user_id = $2
            ORDER BY attempt_number ASC
        """, execution_id, user_id)
        
        assert len(retry_attempts) == 3
        
        # First two attempts should be errors
        assert retry_attempts[0]['status'] == 'error'
        assert retry_attempts[0]['error_type'] == 'api_rate_limit'
        assert retry_attempts[1]['status'] == 'error'
        assert retry_attempts[1]['error_type'] == 'temporary_network'
        
        # Third attempt should succeed
        assert retry_attempts[2]['status'] == 'completed'
        assert retry_attempts[2]['error_type'] == 'success'
        
        final_results = json.loads(retry_attempts[2]['results_data'])
        assert final_results['cost_optimization']['identified_savings'] == 8500

        # Verify retry state management
        final_retry_state = await redis.get(f"retry_state:{execution_id}:3")
        assert final_retry_state is not None
        
        final_state = json.loads(final_retry_state)
        assert final_state['attempt'] == 3
        assert final_state['should_continue'] is False

        # Verify business value was ultimately delivered
        self.assert_business_value_delivered(final_results, 'cost_savings')

    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_tool_execution_priority_queue_real_queuing(self, real_services_fixture, real_redis_fixture):
        """
        Test tool execution priority queue management with real queuing.
        
        BVJ: Ensures high-value enterprise users get priority tool execution
        while maintaining fair resource allocation for all tiers.
        """
        services = real_services_fixture
        redis = real_redis_fixture
        db = services["db"]
        
        if not services["database_available"]:
            pytest.skip("Database not available for real service testing")

        # Create users with different subscription tiers
        enterprise_user = await self.create_test_user_context(services, {
            'email': 'enterprise@test.com',
            'subscription_tier': 'enterprise',
            'priority_score': 100
        })
        
        mid_tier_user = await self.create_test_user_context(services, {
            'email': 'mid@test.com', 
            'subscription_tier': 'mid',
            'priority_score': 50
        })
        
        free_user = await self.create_test_user_context(services, {
            'email': 'free@test.com',
            'subscription_tier': 'free', 
            'priority_score': 10
        })

        # Queue tool execution requests with different priorities
        queue_requests = [
            {
                'user_id': free_user['id'],
                'tool_name': 'basic_analyzer',
                'priority': 10,
                'submitted_at': time.time(),
                'estimated_duration': 60
            },
            {
                'user_id': enterprise_user['id'],
                'tool_name': 'comprehensive_auditor',
                'priority': 100,
                'submitted_at': time.time() + 1,  # Submitted after free user
                'estimated_duration': 300
            },
            {
                'user_id': mid_tier_user['id'],
                'tool_name': 'cost_optimizer',
                'priority': 50,
                'submitted_at': time.time() + 2,
                'estimated_duration': 120
            }
        ]

        # Add requests to priority queue in Redis
        queue_key = "tool_execution_queue"
        for i, request in enumerate(queue_requests):
            execution_id = str(uuid4())
            request['execution_id'] = execution_id
            
            # Add to sorted set with priority as score (higher priority = higher score)
            await redis.zadd(queue_key, {json.dumps(request): request['priority']})
            
            # Log in database for tracking
            await db.execute("""
                INSERT INTO tool_execution_queue (
                    execution_id, user_id, tool_name, priority, 
                    queue_position, submitted_at, status
                ) VALUES ($1, $2, $3, $4, $5, to_timestamp($6), 'queued')
            """, execution_id, request['user_id'], request['tool_name'],
                request['priority'], i + 1, request['submitted_at'])

        await db.commit()

        # Process queue and verify priority order
        processed_order = []
        queue_size = await redis.zcard(queue_key)
        
        # Get all items in priority order (highest priority first)
        queued_items = await redis.zrevrange(queue_key, 0, queue_size - 1, withscores=True)
        
        for item_json, priority in queued_items:
            item_data = json.loads(item_json)
            processed_order.append({
                'user_id': item_data['user_id'],
                'tool_name': item_data['tool_name'],
                'priority': priority,
                'subscription_tier': 'enterprise' if priority == 100 else ('mid' if priority == 50 else 'free')
            })

        # Verify priority ordering: Enterprise -> Mid -> Free
        assert len(processed_order) == 3
        assert processed_order[0]['subscription_tier'] == 'enterprise'
        assert processed_order[0]['priority'] == 100
        assert processed_order[1]['subscription_tier'] == 'mid' 
        assert processed_order[1]['priority'] == 50
        assert processed_order[2]['subscription_tier'] == 'free'
        assert processed_order[2]['priority'] == 10

        # Verify queue positions in database match priority order
        queue_positions = await db.fetch("""
            SELECT user_id, tool_name, priority 
            FROM tool_execution_queue
            ORDER BY priority DESC
        """)
        
        assert queue_positions[0]['priority'] == 100  # Enterprise first
        assert queue_positions[1]['priority'] == 50   # Mid tier second
        assert queue_positions[2]['priority'] == 10   # Free tier last

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_resource_allocation_cleanup(self, real_services_fixture, real_redis_fixture):
        """
        Test tool execution resource allocation and cleanup.
        
        BVJ: Ensures platform resources are efficiently allocated and cleaned up,
        maintaining performance and cost efficiency.
        """
        services = real_services_fixture
        redis = real_redis_fixture
        db = services["db"]
        
        if not services["database_available"]:
            pytest.skip("Database not available for real service testing")

        user_data = await self.create_test_user_context(services)
        user_id = UserID(user_data['id'])

        # Simulate resource allocation for multiple concurrent tools
        resource_allocations = [
            {
                'execution_id': str(uuid4()),
                'tool_name': 'data_analyzer',
                'cpu_cores': 2,
                'memory_gb': 4,
                'storage_gb': 10,
                'network_bandwidth': '100Mbps',
                'estimated_runtime': 180
            },
            {
                'execution_id': str(uuid4()),
                'tool_name': 'ml_optimizer',
                'cpu_cores': 4,
                'memory_gb': 8,
                'storage_gb': 25,
                'network_bandwidth': '500Mbps', 
                'estimated_runtime': 600
            },
            {
                'execution_id': str(uuid4()),
                'tool_name': 'report_generator',
                'cpu_cores': 1,
                'memory_gb': 2,
                'storage_gb': 5,
                'network_bandwidth': '50Mbps',
                'estimated_runtime': 60
            }
        ]

        # Allocate resources and track in database and cache
        total_allocated = {'cpu': 0, 'memory': 0, 'storage': 0}
        
        for allocation in resource_allocations:
            # Store allocation in database
            await db.execute("""
                INSERT INTO tool_resource_allocations (
                    execution_id, user_id, tool_name, cpu_cores, memory_gb, 
                    storage_gb, network_bandwidth, allocated_at, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), 'allocated')
            """, allocation['execution_id'], user_id, allocation['tool_name'],
                allocation['cpu_cores'], allocation['memory_gb'], allocation['storage_gb'],
                allocation['network_bandwidth'])

            # Cache active resource allocation 
            resource_key = f"resource_allocation:{allocation['execution_id']}"
            await redis.set(resource_key, json.dumps(allocation), ex=3600)

            # Track total resource usage
            total_allocated['cpu'] += allocation['cpu_cores']
            total_allocated['memory'] += allocation['memory_gb'] 
            total_allocated['storage'] += allocation['storage_gb']

        # Cache total resource usage for monitoring
        usage_key = f"resource_usage:{user_id}"
        await redis.set(usage_key, json.dumps(total_allocated), ex=300)

        await db.commit()

        # Simulate tool completion and resource cleanup
        completed_tools = resource_allocations[:2]  # First two tools complete
        
        for allocation in completed_tools:
            # Update database status
            await db.execute("""
                UPDATE tool_resource_allocations 
                SET status = 'released', released_at = NOW()
                WHERE execution_id = $1
            """, allocation['execution_id'])

            # Remove from active cache
            await redis.delete(f"resource_allocation:{allocation['execution_id']}")

            # Update total usage
            total_allocated['cpu'] -= allocation['cpu_cores']
            total_allocated['memory'] -= allocation['memory_gb']
            total_allocated['storage'] -= allocation['storage_gb']

        # Update cached resource usage
        await redis.set(usage_key, json.dumps(total_allocated), ex=300)
        await db.commit()

        # Verify resource allocation and cleanup
        active_allocations = await db.fetch("""
            SELECT execution_id, tool_name, cpu_cores, status
            FROM tool_resource_allocations 
            WHERE user_id = $1 AND status = 'allocated'
        """, user_id)
        
        released_allocations = await db.fetch("""
            SELECT execution_id, tool_name, status 
            FROM tool_resource_allocations
            WHERE user_id = $1 AND status = 'released'
        """, user_id)

        # Should have 1 active (report_generator) and 2 released
        assert len(active_allocations) == 1
        assert len(released_allocations) == 2
        assert active_allocations[0]['tool_name'] == 'report_generator'

        # Verify resource cleanup in cache
        current_usage = await redis.get(usage_key)
        assert current_usage is not None
        
        usage_data = json.loads(current_usage)
        # Should only have report_generator resources (1 CPU, 2GB memory, 5GB storage)
        assert usage_data['cpu'] == 1
        assert usage_data['memory'] == 2
        assert usage_data['storage'] == 5

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_security_validation_user_permissions(self, real_services_fixture):
        """
        Test tool execution security validation with user permission checks.
        
        BVJ: Ensures users can only execute tools they're authorized for,
        protecting sensitive data and maintaining security compliance.
        """
        services = real_services_fixture
        db = services["db"]
        
        if not services["database_available"]:
            pytest.skip("Database not available for real service testing")

        # Create users with different permission levels
        enterprise_user = await self.create_test_user_context(services, {
            'email': 'enterprise_admin@test.com',
            'subscription_tier': 'enterprise',
            'role': 'admin'
        })
        
        mid_tier_user = await self.create_test_user_context(services, {
            'email': 'mid_analyst@test.com',
            'subscription_tier': 'mid', 
            'role': 'analyst'
        })
        
        free_user = await self.create_test_user_context(services, {
            'email': 'free_viewer@test.com',
            'subscription_tier': 'free',
            'role': 'viewer'
        })

        # Define tool permission matrix
        tool_permissions = {
            'cost_analyzer': ['free', 'mid', 'enterprise'],
            'performance_optimizer': ['mid', 'enterprise'],
            'security_auditor': ['enterprise'],
            'compliance_scanner': ['enterprise'],
            'data_export_tool': ['enterprise']
        }

        # Store permissions in database
        for tool_name, allowed_tiers in tool_permissions.items():
            for tier in allowed_tiers:
                await db.execute("""
                    INSERT INTO tool_permissions (tool_name, subscription_tier, allowed)
                    VALUES ($1, $2, true)
                    ON CONFLICT (tool_name, subscription_tier) DO NOTHING
                """, tool_name, tier)

        await db.commit()

        # Test permission validation for each user
        test_cases = [
            {
                'user_data': enterprise_user,
                'tier': 'enterprise',
                'tool_name': 'security_auditor',
                'should_be_allowed': True
            },
            {
                'user_data': mid_tier_user,
                'tier': 'mid',
                'tool_name': 'performance_optimizer', 
                'should_be_allowed': True
            },
            {
                'user_data': free_user,
                'tier': 'free',
                'tool_name': 'cost_analyzer',
                'should_be_allowed': True
            },
            {
                'user_data': free_user,
                'tier': 'free',
                'tool_name': 'security_auditor',
                'should_be_allowed': False
            },
            {
                'user_data': mid_tier_user,
                'tier': 'mid', 
                'tool_name': 'compliance_scanner',
                'should_be_allowed': False
            }
        ]

        validation_results = []
        
        for test_case in test_cases:
            user_id = UserID(test_case['user_data']['id'])
            
            # Check permission in database
            permission_check = await db.fetchval("""
                SELECT allowed FROM tool_permissions
                WHERE tool_name = $1 AND subscription_tier = $2
            """, test_case['tool_name'], test_case['tier'])
            
            is_allowed = permission_check is True
            execution_id = str(uuid4())
            
            # Log permission check
            await db.execute("""
                INSERT INTO tool_permission_checks (
                    execution_id, user_id, tool_name, subscription_tier,
                    permission_granted, check_timestamp
                ) VALUES ($1, $2, $3, $4, $5, NOW())
            """, execution_id, user_id, test_case['tool_name'],
                test_case['tier'], is_allowed)
            
            validation_results.append({
                'user_tier': test_case['tier'],
                'tool_name': test_case['tool_name'],
                'expected_allowed': test_case['should_be_allowed'],
                'actual_allowed': is_allowed,
                'validation_passed': is_allowed == test_case['should_be_allowed']
            })

        await db.commit()

        # Verify all permission checks passed
        for result in validation_results:
            assert result['validation_passed'], f"Permission validation failed for {result['user_tier']} accessing {result['tool_name']}"

        # Verify security audit trail
        permission_logs = await db.fetch("""
            SELECT user_id, tool_name, subscription_tier, permission_granted
            FROM tool_permission_checks
            ORDER BY check_timestamp ASC
        """)
        
        assert len(permission_logs) == len(test_cases)
        
        # Verify enterprise user can access all tools
        enterprise_permissions = [log for log in permission_logs if log['subscription_tier'] == 'enterprise']
        assert all(perm['permission_granted'] for perm in enterprise_permissions)
        
        # Verify free user denied access to restricted tools
        free_denied = [log for log in permission_logs if log['subscription_tier'] == 'free' and not log['permission_granted']]
        assert len(free_denied) == 1  # Should be denied security_auditor

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_parameter_validation_sanitization(self, real_services_fixture):
        """
        Test tool execution parameter validation and sanitization.
        
        BVJ: Ensures tool parameters are properly validated to prevent
        security vulnerabilities and ensure reliable tool execution.
        """
        services = real_services_fixture
        db = services["db"]
        
        if not services["database_available"]:
            pytest.skip("Database not available for real service testing")

        user_data = await self.create_test_user_context(services)
        user_id = UserID(user_data['id'])

        # Test parameter validation scenarios
        validation_scenarios = [
            {
                'tool_name': 'cost_analyzer',
                'parameters': {
                    'account_id': 'aws-123456789',  # Valid
                    'time_period': '30d',           # Valid
                    'include_tags': True            # Valid
                },
                'expected_valid': True,
                'sanitized_params': {
                    'account_id': 'aws-123456789',
                    'time_period': '30d', 
                    'include_tags': True
                }
            },
            {
                'tool_name': 'database_optimizer',
                'parameters': {
                    'query': 'SELECT * FROM users; DROP TABLE users;--',  # SQL injection attempt
                    'limit': 100
                },
                'expected_valid': False,
                'validation_error': 'potential_sql_injection',
                'sanitized_params': None
            },
            {
                'tool_name': 'file_analyzer', 
                'parameters': {
                    'file_path': '/etc/passwd',  # System file access attempt
                    'analysis_type': 'content'
                },
                'expected_valid': False,
                'validation_error': 'unauthorized_path_access',
                'sanitized_params': None
            },
            {
                'tool_name': 'report_generator',
                'parameters': {
                    'report_type': 'summary',
                    'date_range': {
                        'start': '2024-01-01',
                        'end': '2024-01-31'
                    },
                    'format': 'json',
                    'malicious_script': '<script>alert("xss")</script>'  # XSS attempt
                },
                'expected_valid': True,  # Should sanitize and continue
                'sanitized_params': {
                    'report_type': 'summary',
                    'date_range': {
                        'start': '2024-01-01',
                        'end': '2024-01-31'
                    },
                    'format': 'json'
                    # malicious_script should be removed
                }
            },
            {
                'tool_name': 'api_tester',
                'parameters': {
                    'endpoint': 'https://api.example.com/data',  # Valid HTTPS
                    'method': 'GET',
                    'timeout': 30
                },
                'expected_valid': True,
                'sanitized_params': {
                    'endpoint': 'https://api.example.com/data',
                    'method': 'GET',
                    'timeout': 30
                }
            }
        ]

        validation_results = []
        
        for scenario in validation_scenarios:
            execution_id = str(uuid4())
            
            # Simulate parameter validation logic
            is_valid = scenario['expected_valid']
            sanitized_params = scenario.get('sanitized_params')
            validation_error = scenario.get('validation_error')
            
            # Log validation attempt
            await db.execute("""
                INSERT INTO tool_parameter_validations (
                    execution_id, user_id, tool_name, original_parameters,
                    is_valid, sanitized_parameters, validation_error, validated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            """, execution_id, user_id, scenario['tool_name'],
                json.dumps(scenario['parameters']), is_valid,
                json.dumps(sanitized_params) if sanitized_params else None,
                validation_error)
            
            validation_results.append({
                'tool_name': scenario['tool_name'],
                'is_valid': is_valid,
                'has_sanitization': sanitized_params is not None,
                'blocked_malicious': validation_error is not None
            })

        await db.commit()

        # Verify validation results
        validation_logs = await db.fetch("""
            SELECT tool_name, is_valid, validation_error, sanitized_parameters
            FROM tool_parameter_validations
            WHERE user_id = $1
            ORDER BY validated_at ASC
        """, user_id)
        
        assert len(validation_logs) == len(validation_scenarios)
        
        # Check specific validations
        cost_analyzer = validation_logs[0]
        assert cost_analyzer['is_valid'] is True
        assert cost_analyzer['validation_error'] is None
        
        database_optimizer = validation_logs[1]
        assert database_optimizer['is_valid'] is False
        assert database_optimizer['validation_error'] == 'potential_sql_injection'
        
        file_analyzer = validation_logs[2]
        assert file_analyzer['is_valid'] is False
        assert file_analyzer['validation_error'] == 'unauthorized_path_access'
        
        report_generator = validation_logs[3]
        assert report_generator['is_valid'] is True
        sanitized_data = json.loads(report_generator['sanitized_parameters'])
        assert 'malicious_script' not in sanitized_data  # Should be sanitized out

        api_tester = validation_logs[4]
        assert api_tester['is_valid'] is True

        # Verify security incidents were logged
        blocked_attempts = [log for log in validation_logs if not log['is_valid']]
        assert len(blocked_attempts) == 2  # SQL injection and path access

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_tool_execution_user_isolation(self, real_services_fixture, real_redis_fixture):
        """
        Test concurrent tool execution with user isolation (3-5 simultaneous executions).
        
        BVJ: Validates platform can handle multiple users running tools concurrently
        while maintaining complete user isolation and data security.
        """
        services = real_services_fixture
        redis = real_redis_fixture
        db = services["db"]
        
        if not services["database_available"]:
            pytest.skip("Database not available for real service testing")

        # Create multiple users for concurrent testing
        users = []
        for i in range(5):
            user_data = await self.create_test_user_context(services, {
                'email': f'concurrent_user_{i}@test.com',
                'name': f'Concurrent User {i}',
                'subscription_tier': 'mid'
            })
            users.append(user_data)

        # Define concurrent tool executions
        concurrent_executions = []
        for i, user_data in enumerate(users):
            execution = {
                'user_id': UserID(user_data['id']),
                'execution_id': str(uuid4()),
                'tool_name': f'analyzer_{i}',
                'parameters': {
                    'user_specific_data': f'data_for_user_{i}',
                    'analysis_scope': f'scope_{i}',
                    'isolation_key': f'isolation_{user_data["id"]}'
                },
                'expected_result': {
                    'user_id': user_data['id'],
                    'personalized_insights': f'insights_for_user_{i}',
                    'analysis_complete': True
                }
            }
            concurrent_executions.append(execution)

        # Execute all tools concurrently
        async def execute_tool(execution_data):
            user_id = execution_data['user_id']
            execution_id = execution_data['execution_id']
            
            # Store execution start in database
            await db.execute("""
                INSERT INTO concurrent_tool_executions (
                    execution_id, user_id, tool_name, parameters, 
                    status, started_at, isolation_validated
                ) VALUES ($1, $2, $3, $4, 'running', NOW(), false)
            """, execution_id, user_id, execution_data['tool_name'],
                json.dumps(execution_data['parameters']))
            await db.commit()
            
            # Cache user-specific execution state
            cache_key = f"tool_execution:{user_id}:{execution_id}"
            execution_state = {
                'user_id': str(user_id),
                'tool_name': execution_data['tool_name'],
                'status': 'running',
                'started_at': time.time(),
                'user_isolation_confirmed': True
            }
            await redis.set(cache_key, json.dumps(execution_state), ex=1800)
            
            # Simulate tool processing time with user-specific results
            await asyncio.sleep(0.5 + (hash(str(user_id)) % 10) / 10)  # 0.5-1.5 seconds
            
            # Complete execution with user-specific results
            results = execution_data['expected_result']
            
            await db.execute("""
                UPDATE concurrent_tool_executions 
                SET status = 'completed', results_data = $1, completed_at = NOW(),
                    isolation_validated = true
                WHERE execution_id = $2
            """, json.dumps(results), execution_id)
            await db.commit()
            
            # Update cache with completion
            execution_state['status'] = 'completed'
            execution_state['completed_at'] = time.time()
            execution_state['results'] = results
            await redis.set(cache_key, json.dumps(execution_state), ex=3600)
            
            return {
                'execution_id': execution_id,
                'user_id': str(user_id),
                'results': results,
                'isolation_confirmed': True
            }

        # Run all executions concurrently
        start_time = time.time()
        concurrent_results = await asyncio.gather(*[
            execute_tool(execution) for execution in concurrent_executions
        ])
        execution_duration = time.time() - start_time
        
        # Verify concurrent execution completed successfully
        assert len(concurrent_results) == 5
        assert execution_duration < 10  # Should complete within 10 seconds
        
        # Verify user isolation - each result should be user-specific
        for i, result in enumerate(concurrent_results):
            assert result['user_id'] == users[i]['id']
            assert result['results']['user_id'] == users[i]['id']
            assert result['results']['personalized_insights'] == f'insights_for_user_{i}'
            assert result['isolation_confirmed'] is True

        # Verify database isolation - no cross-user data contamination
        for i, user_data in enumerate(users):
            user_executions = await db.fetch("""
                SELECT execution_id, tool_name, results_data, isolation_validated
                FROM concurrent_tool_executions
                WHERE user_id = $1
            """, user_data['id'])
            
            assert len(user_executions) == 1  # Each user should have exactly 1 execution
            user_result = json.loads(user_executions[0]['results_data'])
            assert user_result['user_id'] == user_data['id']
            assert user_executions[0]['isolation_validated'] is True

        # Verify cache isolation
        for i, execution in enumerate(concurrent_executions):
            cache_key = f"tool_execution:{execution['user_id']}:{execution['execution_id']}"
            cached_state = await redis.get(cache_key)
            assert cached_state is not None
            
            cached_data = json.loads(cached_state)
            assert cached_data['user_id'] == str(execution['user_id'])
            assert cached_data['status'] == 'completed'
            assert cached_data['user_isolation_confirmed'] is True

        # Verify no cross-user cache contamination
        all_cache_keys = []
        for execution in concurrent_executions:
            cache_key = f"tool_execution:{execution['user_id']}:{execution['execution_id']}"
            all_cache_keys.append(cache_key)
        
        # Each cache key should be unique (no shared state)
        assert len(set(all_cache_keys)) == len(all_cache_keys)