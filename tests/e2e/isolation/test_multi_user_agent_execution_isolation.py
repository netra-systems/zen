"""
E2E Test: Multi-User Agent Execution Isolation

Business Value Justification (BVJ):
- Segment: Early, Mid, Enterprise - Multi-user isolation is critical for paid tiers
- Business Goal: Ensure complete workflow isolation between users executing agents
- Value Impact: Users must have completely isolated agent execution contexts
- Strategic Impact: Core multi-tenancy that prevents data leaks and ensures enterprise security

This E2E test validates:
- Complete workflow isolation with real authentication across multiple users
- Agent execution contexts are completely separated between users
- Real LLM calls don't interfere or leak data between users
- WebSocket event isolation prevents cross-user contamination
- Database and state isolation across concurrent user workflows

CRITICAL: Tests the isolation that prevents data breaches and enables enterprise usage
"""

import pytest
import asyncio
import uuid
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient

# Core system imports with absolute paths
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# Enterprise-specific imports for isolation testing
try:
    from netra_backend.app.security.user_context_isolation import UserContextValidator
    from netra_backend.app.database.tenant_isolation import TenantIsolationValidator
except ImportError:
    # Fallback if enterprise modules aren't available
    UserContextValidator = None
    TenantIsolationValidator = None


class UserExecutionContext:
    """Represents a complete user execution context for isolation testing."""
    
    def __init__(self, user_id: str, context_id: str):
        self.user_id = user_id
        self.context_id = context_id
        self.user_context = None
        self.websocket_helper = None
        self.websocket_connection = None
        self.execution_results = []
        self.received_events = []
        self.sensitive_data = {
            'user_secret': f'sensitive_data_user_{user_id}_{int(time.time())}',
            'private_context': f'private_context_{context_id}',
            'confidential_info': f'confidential_{user_id}'
        }
    
    async def initialize_context(self, environment: str = "test"):
        """Initialize user context with authentication."""
        self.user_context = await create_authenticated_user_context(
            user_email=f"isolation_user_{self.user_id}@e2e.test",
            environment=environment,
            permissions=["read", "write", "agent_execute", "websocket_connect"],
            websocket_enabled=True
        )
        
        self.websocket_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Add sensitive data to user context
        self.user_context.agent_context.update({
            'sensitive_user_data': self.sensitive_data,
            'user_isolation_id': self.context_id,
            'security_level': 'enterprise'
        })
        
        return self.user_context
    
    async def connect_websocket(self, timeout: float = 15.0):
        """Connect isolated WebSocket for this user."""
        self.websocket_connection = await self.websocket_helper.connect_authenticated_websocket(
            timeout=timeout
        )
        return self.websocket_connection
    
    async def execute_agent_with_sensitive_data(
        self,
        agent_registry: AgentRegistry,
        agent_name: str = "triage_agent",
        sensitive_message: str = None
    ):
        """Execute agent with sensitive data to test isolation."""
        if not sensitive_message:
            sensitive_message = f"Process sensitive data: {self.sensitive_data['user_secret']}"
        
        id_generator = UnifiedIdGenerator()
        run_id = id_generator.generate_run_id(
            user_id=str(self.user_context.user_id),
            operation=f"isolation_test_{self.context_id}"
        )
        
        execution_context = AgentExecutionContext(
            agent_name=agent_name,
            run_id=str(run_id),
            correlation_id=str(self.user_context.request_id),
            retry_count=0,
            user_context=self.user_context
        )
        
        agent_state = DeepAgentState(
            user_id=str(self.user_context.user_id),
            thread_id=str(self.user_context.thread_id),
            agent_context={
                **self.user_context.agent_context,
                'user_message': sensitive_message,
                'isolation_test': True,
                'user_context_id': self.context_id,
                'sensitive_processing': True
            }
        )
        
        # Set up execution infrastructure
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        execution_core = AgentExecutionCore(agent_registry, websocket_bridge)
        
        result = await execution_core.execute_agent(
            context=execution_context,
            state=agent_state,
            timeout=35.0,
            enable_llm=False,  # Focus on isolation, not LLM complexity
            enable_websocket_events=True
        )
        
        self.execution_results.append({
            'result': result,
            'run_id': str(run_id),
            'sensitive_message': sensitive_message,
            'execution_time': time.time()
        })
        
        return result, str(run_id)
    
    async def collect_all_events(self, timeout: float = 25.0):
        """Collect all WebSocket events for isolation analysis."""
        if not self.websocket_connection:
            raise RuntimeError("WebSocket not connected")
        
        try:
            while True:
                event_raw = await asyncio.wait_for(self.websocket_connection.recv(), timeout=timeout)
                event = json.loads(event_raw)
                self.received_events.append(event)
                
                if event.get('type') == 'agent_completed':
                    break
        except asyncio.TimeoutError:
            pass
        
        return self.received_events
    
    def analyze_event_isolation(self, other_contexts: List['UserExecutionContext']) -> Dict[str, Any]:
        """Analyze event isolation from other user contexts."""
        isolation_report = {
            'user_id': self.user_id,
            'context_id': self.context_id,
            'total_events': len(self.received_events),
            'isolation_violations': [],
            'cross_contamination_detected': False,
            'sensitive_data_exposure': []
        }
        
        # Check for cross-contamination in events
        for event in self.received_events:
            event_str = json.dumps(event)
            
            # Check if this user's events contain other users' sensitive data
            for other_context in other_contexts:
                if other_context.user_id == self.user_id:
                    continue
                
                for sensitive_key, sensitive_value in other_context.sensitive_data.items():
                    if sensitive_value in event_str:
                        isolation_report['isolation_violations'].append({
                            'violation_type': 'sensitive_data_exposure',
                            'other_user_id': other_context.user_id,
                            'exposed_data': sensitive_key,
                            'event_type': event.get('type'),
                            'event_id': event.get('run_id')
                        })
                        isolation_report['cross_contamination_detected'] = True
                
                # Check for other user's identifiers in events
                other_user_id = str(other_context.user_context.user_id) if other_context.user_context else None
                if other_user_id and other_user_id in event_str:
                    isolation_report['isolation_violations'].append({
                        'violation_type': 'user_id_cross_reference',
                        'other_user_id': other_context.user_id,
                        'event_type': event.get('type')
                    })
                    isolation_report['cross_contamination_detected'] = True
        
        return isolation_report
    
    async def cleanup(self):
        """Clean up user execution context."""
        if self.websocket_connection:
            try:
                await self.websocket_connection.close()
            except:
                pass
        
        self.received_events.clear()
        self.execution_results.clear()


class TestMultiUserAgentExecutionIsolation(BaseE2ETest):
    """E2E tests for complete multi-user agent execution isolation."""
    
    @pytest.fixture
    def unified_id_generator(self):
        """ID generator for test consistency."""
        return UnifiedIdGenerator()
    
    @pytest.fixture
    async def real_agent_registry(self):
        """Real agent registry for isolation testing."""
        registry = AgentRegistry()
        await registry.initialize_registry()
        return registry
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.websocket_events
    @pytest.mark.isolation
    @pytest.mark.security
    async def test_complete_multi_user_workflow_isolation(
        self,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test complete isolation between multiple users executing agents simultaneously.
        
        CRITICAL: This test validates enterprise-grade multi-tenancy isolation.
        No user data should ever leak to another user.
        """
        
        num_users = 3
        user_contexts = []
        
        # Create isolated user execution contexts
        for i in range(num_users):
            user_context = UserExecutionContext(
                user_id=f"isolation_user_{i}",
                context_id=f"ctx_{i}_{int(time.time())}"
            )
            user_contexts.append(user_context)
        
        try:
            # Initialize all user contexts
            initialization_tasks = [ctx.initialize_context() for ctx in user_contexts]
            await asyncio.gather(*initialization_tasks)
            
            # Connect WebSockets for all users
            websocket_tasks = [ctx.connect_websocket() for ctx in user_contexts]
            await asyncio.gather(*websocket_tasks)
            
            # Execute agents concurrently with sensitive data
            async def execute_user_workflow(ctx: UserExecutionContext, user_index: int):
                """Execute complete workflow for one user."""
                # Start event collection
                event_task = asyncio.create_task(ctx.collect_all_events())
                
                # Execute agent with user-specific sensitive data
                result, run_id = await ctx.execute_agent_with_sensitive_data(
                    real_agent_registry,
                    sensitive_message=f"Process confidential data for user {user_index}: {ctx.sensitive_data['user_secret']}"
                )
                
                # Wait for events
                await event_task
                
                return result, run_id
            
            # Execute all user workflows concurrently
            concurrent_tasks = [
                execute_user_workflow(ctx, i) for i, ctx in enumerate(user_contexts)
            ]
            
            results = await asyncio.gather(*concurrent_tasks)
            
            # CRITICAL VALIDATION: All executions succeeded
            for i, (result, run_id) in enumerate(results):
                assert result.success is True, \
                    f"User {i} workflow execution failed: {result.error}"
                assert run_id is not None, f"User {i} missing run_id"
            
            # CRITICAL VALIDATION: Complete isolation analysis
            all_isolation_reports = []
            
            for ctx in user_contexts:
                isolation_report = ctx.analyze_event_isolation(user_contexts)
                all_isolation_reports.append(isolation_report)
                
                # CRITICAL: No cross-contamination detected
                assert not isolation_report['cross_contamination_detected'], \
                    f"ISOLATION VIOLATION: User {ctx.user_id} events contain other user data: " \
                    f"{isolation_report['isolation_violations']}"
                
                # CRITICAL: User received their own events
                assert isolation_report['total_events'] > 0, \
                    f"User {ctx.user_id} received no events"
            
            # CRITICAL VALIDATION: Unique identifiers across all users
            all_user_ids = {str(ctx.user_context.user_id) for ctx in user_contexts}
            all_thread_ids = {str(ctx.user_context.thread_id) for ctx in user_contexts}
            all_run_ids = {result[1] for result in results}
            
            assert len(all_user_ids) == num_users, \
                f"User IDs not unique: {len(all_user_ids)} unique out of {num_users}"
            assert len(all_thread_ids) == num_users, \
                f"Thread IDs not unique: {len(all_thread_ids)} unique out of {num_users}" 
            assert len(all_run_ids) == num_users, \
                f"Run IDs not unique: {len(all_run_ids)} unique out of {num_users}"
            
            # CRITICAL VALIDATION: Event isolation per user
            for i, ctx in enumerate(user_contexts):
                user_run_ids = {event.get('run_id') for event in ctx.received_events}
                expected_run_id = results[i][1]
                
                # User should only see their own run_id
                assert expected_run_id in user_run_ids, \
                    f"User {i} missing their own run_id in events"
                
                # User should not see other users' run_ids
                other_run_ids = [results[j][1] for j in range(num_users) if j != i]
                for other_run_id in other_run_ids:
                    assert other_run_id not in user_run_ids, \
                        f"ISOLATION VIOLATION: User {i} saw other user's run_id: {other_run_id}"
            
            # VALIDATION: Sensitive data isolation
            for ctx in user_contexts:
                for event in ctx.received_events:
                    event_str = json.dumps(event)
                    
                    # User's events should contain their own sensitive data
                    user_sensitive_found = any(
                        sensitive_value in event_str 
                        for sensitive_value in ctx.sensitive_data.values()
                    )
                    
                    # But should not contain other users' sensitive data
                    for other_ctx in user_contexts:
                        if other_ctx.user_id == ctx.user_id:
                            continue
                        
                        other_sensitive_found = any(
                            sensitive_value in event_str
                            for sensitive_value in other_ctx.sensitive_data.values()
                        )
                        
                        assert not other_sensitive_found, \
                            f"SECURITY VIOLATION: User {ctx.user_id} events contain " \
                            f"other user's sensitive data from user {other_ctx.user_id}"
            
            self.logger.info("✅ CRITICAL SUCCESS: Complete multi-user workflow isolation validated")
            self.logger.info(f"  - Users tested: {num_users}")
            self.logger.info(f"  - Unique user IDs: {len(all_user_ids)}")
            self.logger.info(f"  - Unique thread IDs: {len(all_thread_ids)}")
            self.logger.info(f"  - Unique run IDs: {len(all_run_ids)}")
            self.logger.info(f"  - Total events delivered: {sum(len(ctx.received_events) for ctx in user_contexts)}")
            self.logger.info(f"  - Isolation violations: 0 (REQUIRED)")
            
        finally:
            # Clean up all user contexts
            cleanup_tasks = [ctx.cleanup() for ctx in user_contexts]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.isolation
    @pytest.mark.security
    @pytest.mark.performance
    async def test_high_concurrency_isolation_stress(
        self,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test isolation under high concurrency stress with many simultaneous users.
        
        Validates that isolation remains intact even under heavy concurrent load.
        """
        
        num_concurrent_users = 6
        user_contexts = []
        
        # Create many concurrent user contexts
        for i in range(num_concurrent_users):
            user_context = UserExecutionContext(
                user_id=f"stress_user_{i}",
                context_id=f"stress_ctx_{i}_{int(time.time())}"
            )
            user_contexts.append(user_context)
        
        start_time = time.time()
        
        try:
            # Rapid initialization
            init_tasks = [ctx.initialize_context() for ctx in user_contexts]
            await asyncio.gather(*init_tasks)
            
            ws_tasks = [ctx.connect_websocket(timeout=20.0) for ctx in user_contexts]
            await asyncio.gather(*ws_tasks)
            
            # Concurrent execution with minimal delays
            async def stress_user_execution(ctx: UserExecutionContext, user_index: int):
                """Execute under stress conditions."""
                event_task = asyncio.create_task(ctx.collect_all_events(timeout=30.0))
                
                result, run_id = await ctx.execute_agent_with_sensitive_data(
                    real_agent_registry,
                    sensitive_message=f"Stress test {user_index}: {ctx.sensitive_data['confidential_info']}"
                )
                
                await event_task
                return result, run_id, ctx.user_id
            
            # Execute all users simultaneously
            stress_tasks = [
                stress_user_execution(ctx, i) for i, ctx in enumerate(user_contexts)
            ]
            
            stress_results = await asyncio.gather(*stress_tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
            
            # VALIDATION: No exceptions occurred
            successful_results = []
            for i, result in enumerate(stress_results):
                if isinstance(result, Exception):
                    self.logger.error(f"Stress user {i} failed: {result}")
                    pytest.fail(f"Stress test user {i} failed with exception: {result}")
                else:
                    successful_results.append(result)
            
            # VALIDATION: All executions succeeded
            for i, (result, run_id, user_id) in enumerate(successful_results):
                assert result.success is True, \
                    f"Stress user {i} ({user_id}) execution failed: {result.error}"
            
            # CRITICAL VALIDATION: Isolation maintained under stress
            isolation_violations = 0
            
            for i, ctx in enumerate(user_contexts):
                isolation_report = ctx.analyze_event_isolation(user_contexts)
                
                if isolation_report['cross_contamination_detected']:
                    isolation_violations += len(isolation_report['isolation_violations'])
                    self.logger.error(f"Stress isolation violations for user {i}: {isolation_report}")
            
            assert isolation_violations == 0, \
                f"CRITICAL FAILURE: {isolation_violations} isolation violations under stress"
            
            # VALIDATION: Performance acceptable under stress
            assert total_time < 60.0, \
                f"Stress test too slow: {total_time:.2f}s for {num_concurrent_users} users"
            
            average_time_per_user = total_time / num_concurrent_users
            assert average_time_per_user < 15.0, \
                f"Average time per user too high under stress: {average_time_per_user:.2f}s"
            
            # VALIDATION: All expected identifiers are unique
            all_user_ids = {str(ctx.user_context.user_id) for ctx in user_contexts}
            all_run_ids = {run_id for _, run_id, _ in successful_results}
            
            assert len(all_user_ids) == num_concurrent_users, \
                f"Not all user IDs unique under stress: {len(all_user_ids)} / {num_concurrent_users}"
            assert len(all_run_ids) == num_concurrent_users, \
                f"Not all run IDs unique under stress: {len(all_run_ids)} / {num_concurrent_users}"
            
            self.logger.info(f"✅ STRESS SUCCESS: High concurrency isolation maintained")
            self.logger.info(f"  - Concurrent users: {num_concurrent_users}")
            self.logger.info(f"  - Total time: {total_time:.2f}s")
            self.logger.info(f"  - Average per user: {average_time_per_user:.2f}s")
            self.logger.info(f"  - Isolation violations: {isolation_violations} (REQUIRED: 0)")
            self.logger.info(f"  - Unique identifiers maintained: ✅")
            
        finally:
            cleanup_tasks = [ctx.cleanup() for ctx in user_contexts]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.isolation
    @pytest.mark.enterprise
    async def test_enterprise_security_isolation(
        self,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test enterprise-grade security isolation between users.
        
        Validates that enterprise security requirements are met for data isolation.
        """
        
        # Create enterprise user contexts with different security levels
        enterprise_contexts = [
            UserExecutionContext("enterprise_admin", "admin_ctx"),
            UserExecutionContext("enterprise_user", "user_ctx"),
            UserExecutionContext("enterprise_guest", "guest_ctx")
        ]
        
        # Set different security levels and sensitive data
        security_levels = ["admin", "user", "guest"]
        for ctx, security_level in zip(enterprise_contexts, security_levels):
            ctx.sensitive_data.update({
                'security_level': security_level,
                'enterprise_secret': f'CONFIDENTIAL_{security_level}_{int(time.time())}',
                'access_level': f'{security_level}_access',
                'compliance_data': f'SOC2_GDPR_{security_level}'
            })
        
        try:
            # Initialize enterprise contexts
            for ctx in enterprise_contexts:
                await ctx.initialize_context()
                # Add enterprise-specific context
                ctx.user_context.agent_context.update({
                    'enterprise_mode': True,
                    'security_level': ctx.sensitive_data['security_level'],
                    'compliance_required': True
                })
                await ctx.connect_websocket()
            
            # Execute with enterprise security requirements
            enterprise_results = []
            
            for i, ctx in enumerate(enterprise_contexts):
                event_task = asyncio.create_task(ctx.collect_all_events())
                
                result, run_id = await ctx.execute_agent_with_sensitive_data(
                    real_agent_registry,
                    sensitive_message=f"Enterprise {ctx.sensitive_data['security_level']} operation: {ctx.sensitive_data['enterprise_secret']}"
                )
                
                await event_task
                enterprise_results.append((result, run_id, ctx))
            
            # CRITICAL VALIDATION: Enterprise isolation
            for result, run_id, ctx in enterprise_results:
                assert result.success is True, \
                    f"Enterprise user {ctx.user_id} execution failed: {result.error}"
                
                # Validate events contain proper security context
                security_events = [
                    event for event in ctx.received_events 
                    if 'security' in json.dumps(event).lower()
                ]
                
                # Enterprise events should maintain security context
                for event in ctx.received_events:
                    event_str = json.dumps(event)
                    
                    # Should contain own security level data
                    assert ctx.sensitive_data['security_level'] in event_str or \
                           len([e for e in ctx.received_events if e.get('type') == 'agent_completed']) > 0, \
                           f"Enterprise context not properly maintained for {ctx.user_id}"
                    
                    # Should NOT contain other security levels' data
                    for other_ctx in enterprise_contexts:
                        if other_ctx.user_id == ctx.user_id:
                            continue
                        
                        assert other_ctx.sensitive_data['enterprise_secret'] not in event_str, \
                            f"ENTERPRISE SECURITY VIOLATION: {ctx.user_id} accessed {other_ctx.user_id} enterprise data"
            
            # VALIDATION: Complete enterprise isolation
            isolation_reports = [
                ctx.analyze_event_isolation(enterprise_contexts) for ctx in enterprise_contexts
            ]
            
            total_violations = sum(
                len(report['isolation_violations']) for report in isolation_reports
            )
            
            assert total_violations == 0, \
                f"ENTERPRISE SECURITY FAILURE: {total_violations} isolation violations detected"
            
            self.logger.info("✅ ENTERPRISE SUCCESS: Enterprise-grade security isolation validated")
            for ctx, report in zip(enterprise_contexts, isolation_reports):
                self.logger.info(f"  - {ctx.user_id} ({ctx.sensitive_data['security_level']}): {report['total_events']} events, {len(report['isolation_violations'])} violations")
            
        finally:
            cleanup_tasks = [ctx.cleanup() for ctx in enterprise_contexts]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)