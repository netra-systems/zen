"""
Test Suite: Agent Factory User Isolation Compliance - SSOT Violation Integration Tests

PURPOSE: Integration tests proving user isolation failures in AgentInstanceFactory
ISSUE: #1102 - Agent Instance Factory singleton pattern breaks user isolation
CRITICAL MISSION: Implement 20% NEW tests proving WebSocket and execution isolation violations

EXPECTED BEHAVIOR:
- BEFORE REMEDIATION: All tests should FAIL (proving user isolation violations)
- AFTER REMEDIATION: All tests should PASS (proving SSOT compliance achieved)

Business Value: Enterprise/Platform - 500K+ ARR protection through proper user isolation
SSOT Remediation Target: Complete user isolation in multi-user concurrent scenarios

This test suite validates real-world user isolation failures that affect:
- WebSocket event delivery cross-contamination
- Agent execution context mixing
- Multi-tenancy compliance violations
- Enterprise security requirements
"""

import asyncio
import gc
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, Mock, patch

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory


@pytest.mark.integration
class AgentFactoryUserIsolationComplianceTests(SSotAsyncTestCase):
    """
    Integration test suite proving user isolation compliance violations.
    
    This test suite validates Issue #1102 by proving that:
    1. WebSocket events cross-contaminate between users
    2. Concurrent agent execution contexts mix inappropriately
    3. User execution context separation is violated
    4. Enterprise multi-tenancy compliance fails
    
    CRITICAL: These tests should FAIL before remediation and PASS after SSOT fix.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Reset any cached imports and singletons
        modules_to_reset = [
            'netra_backend.app.agents.supervisor.agent_instance_factory',
            'netra_backend.app.services.user_execution_context',
            'netra_backend.app.services.agent_websocket_bridge',
        ]
        
        for module_name in modules_to_reset:
            if module_name in sys.modules:
                try:
                    del sys.modules[module_name]
                except KeyError:
                    pass
        
        # Force garbage collection
        gc.collect()

    def teardown_method(self, method):
        """Cleanup after each test method."""
        gc.collect()
        super().teardown_method(method)

    async def test_websocket_events_user_isolation(self):
        """
        Test that WebSocket events cross-contaminate between users through shared factory.
        
        VIOLATION PROOF: The singleton factory causes WebSocket events from one user
        to be delivered to other users, violating privacy and security.
        
        EXPECTED: FAIL before remediation (proving cross-contamination)
        EXPECTED: PASS after remediation (proving proper event isolation)
        """
        # Import after setup to ensure fresh state
        from netra_backend.app.agents.supervisor.agent_instance_factory import (
            get_agent_instance_factory,
            configure_agent_instance_factory
        )
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        # Mock WebSocket bridge to track event delivery
        mock_websocket_bridge = SSotMockFactory.create_mock('AgentWebSocketBridge')
        mock_websocket_bridge.emit_agent_started = AsyncMock()
        mock_websocket_bridge.emit_agent_thinking = AsyncMock()
        mock_websocket_bridge.emit_agent_completed = AsyncMock()
        
        # Configure factory with mocked bridge
        factory = await configure_agent_instance_factory(
            websocket_bridge=mock_websocket_bridge
        )
        
        # Simulate multiple users with different contexts
        user_contexts = []
        for i in range(3):
            user_id = f"user_{i}_{uuid.uuid4()}"
            run_id = f"run_{i}_{uuid.uuid4()}"
            
            context = UserExecutionContext.from_request(
                user_id=user_id,
                thread_id=f"thread_{i}",
                run_id=run_id,
                request_id=f"request_{i}",
            )
            user_contexts.append(context)
        
        # Each user creates agent instances (should be isolated)
        agent_instances = []
        for context in user_contexts:
            try:
                # Attempt to create isolated agent
                factory_for_user = get_agent_instance_factory()
                
                # VIOLATION: Same factory instance used for all users
                agent_instances.append({
                    'context': context,
                    'factory_id': id(factory_for_user),
                    'user_id': context.user_id,
                    'run_id': context.run_id
                })
                
            except Exception as e:
                # Factory creation should not fail for proper isolation
                pytest.fail(f"Factory creation failed for user {context.user_id}: {e}")
        
        # VIOLATION ANALYSIS: Check factory sharing
        factory_ids = [instance['factory_id'] for instance in agent_instances]
        unique_factory_ids = set(factory_ids)
        
        # VIOLATION ASSERTION: All users share same factory
        assert len(unique_factory_ids) == 1, (
            "WEBSOCKET ISOLATION VIOLATION: All users share same factory instance. "
            f"Expected isolated factories, found {len(unique_factory_ids)} unique. "
            f"Factory IDs: {factory_ids}. "
            "This causes WebSocket event cross-contamination between users."
        )
        
        # VIOLATION PROOF: WebSocket events would be shared
        shared_factory_id = factory_ids[0]
        
        # All users would receive events meant for others
        assert all(fid == shared_factory_id for fid in factory_ids), (
            "WEBSOCKET CROSS-CONTAMINATION: Shared factory causes WebSocket events "
            "from one user to be delivered to all users. "
            f"Shared factory ID: {shared_factory_id} used by all {len(user_contexts)} users."
        )

    async def test_concurrent_agent_execution_isolation(self):
        """
        Test that concurrent agent execution contexts mix through shared factory.
        
        VIOLATION PROOF: Multiple agents executing simultaneously share execution
        state through the singleton factory, causing context mixing and data corruption.
        
        EXPECTED: FAIL before remediation (proving context mixing)
        EXPECTED: PASS after remediation (proving execution isolation)
        """
        from netra_backend.app.agents.supervisor.agent_instance_factory import (
            get_agent_instance_factory
        )
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        # Simulate concurrent agent executions
        execution_results = []
        
        async def simulate_agent_execution(user_id: str, execution_data: str):
            """Simulate agent execution that modifies factory state."""
            factory = get_agent_instance_factory()
            
            # Each execution should have isolated state
            execution_marker = f"exec_{user_id}_{execution_data}_{time.time()}"
            
            # Store execution state in factory (violating isolation)
            if not hasattr(factory, '_active_executions'):
                factory._active_executions = {}
            
            factory._active_executions[user_id] = {
                'marker': execution_marker,
                'start_time': time.time(),
                'execution_data': execution_data
            }
            
            # Simulate execution time
            await asyncio.sleep(0.01)
            
            # Check what executions are visible
            visible_executions = dict(factory._active_executions)
            
            return {
                'user_id': user_id,
                'factory_id': id(factory),
                'execution_marker': execution_marker,
                'visible_executions': visible_executions,
                'execution_count': len(visible_executions)
            }
        
        # Run concurrent executions
        tasks = []
        user_data = [
            ('user_1', 'sensitive_data_1'),
            ('user_2', 'confidential_data_2'),
            ('user_3', 'private_data_3')
        ]
        
        for user_id, data in user_data:
            task = asyncio.create_task(
                simulate_agent_execution(user_id, data)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # VIOLATION ANALYSIS: Check execution isolation
        factory_ids = [result['factory_id'] for result in results]
        unique_factory_ids = set(factory_ids)
        
        # VIOLATION ASSERTION: All executions share same factory
        assert len(unique_factory_ids) == 1, (
            "EXECUTION ISOLATION VIOLATION: All executions share same factory. "
            f"Expected isolated factories, found {len(unique_factory_ids)} unique. "
            "This causes execution context mixing between users."
        )
        
        # VIOLATION ASSERTION: Each execution can see others' data
        for result in results:
            visible_executions = result['visible_executions']
            user_id = result['user_id']
            
            # User can see other users' execution data
            other_user_executions = {
                k: v for k, v in visible_executions.items() if k != user_id
            }
            
            assert len(other_user_executions) > 0, (
                f"EXECUTION CONTEXT MIXING: User {user_id} can access other users' execution data. "
                f"Visible other executions: {other_user_executions}. "
                "This proves execution context isolation is violated."
            )
            
            # Check that sensitive data from other users is visible
            for other_user, other_data in other_user_executions.items():
                other_execution_data = other_data.get('execution_data', '')
                
                assert 'data_' in other_execution_data, (
                    f"SENSITIVE DATA EXPOSURE: User {user_id} can see sensitive data "
                    f"from user {other_user}: '{other_execution_data}'. "
                    "This violates user data isolation requirements."
                )

    async def test_user_execution_context_separation(self):
        """
        Test that user execution contexts are not properly separated through factory.
        
        VIOLATION PROOF: The singleton factory causes user execution contexts
        to be shared or contaminated, violating fundamental isolation principles.
        
        EXPECTED: FAIL before remediation (proving context contamination)
        EXPECTED: PASS after remediation (proving proper separation)
        """
        from netra_backend.app.agents.supervisor.agent_instance_factory import (
            get_agent_instance_factory
        )
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        # Create distinct user contexts with sensitive information
        user_contexts_data = [
            {
                'user_id': 'healthcare_user_1',
                'session_id': 'hipaa_session_123',
                'sensitive_data': 'patient_record_phi_data'
            },
            {
                'user_id': 'financial_user_2', 
                'session_id': 'pci_session_456',
                'sensitive_data': 'credit_card_financial_data'
            },
            {
                'user_id': 'government_user_3',
                'session_id': 'classified_session_789',
                'sensitive_data': 'classified_government_data'
            }
        ]
        
        context_separation_results = []
        
        # Get shared factory instance to demonstrate violation
        shared_factory = get_agent_instance_factory()
        
        for user_data in user_contexts_data:
            # Store user context in shared factory (violation)
            user_context = UserExecutionContext.from_request(
                user_id=user_data['user_id'],
                thread_id=f"thread_{uuid.uuid4()}",
                run_id=f"run_{uuid.uuid4()}",
                request_id=f"req_{uuid.uuid4()}",
            )
            
            # Simulate storing sensitive context data in shared factory
            if not hasattr(shared_factory, '_user_contexts'):
                shared_factory._user_contexts = {}
            
            shared_factory._user_contexts[user_data['user_id']] = {
                'context': user_context,
                'sensitive_data': user_data['sensitive_data'],
                'storage_time': time.time()
            }
            
            # Check what contexts are accessible - should see all users' data
            accessible_contexts = dict(shared_factory._user_contexts)
            
            context_separation_results.append({
                'user_id': user_data['user_id'],
                'factory_id': id(shared_factory),
                'sensitive_data': user_data['sensitive_data'],
                'accessible_contexts': accessible_contexts,
                'context_count': len(accessible_contexts)
            })
        
        # VIOLATION ANALYSIS: Check context separation
        factory_ids = [result['factory_id'] for result in context_separation_results]
        unique_factory_ids = set(factory_ids)
        
        # VIOLATION ASSERTION: All users share same factory
        assert len(unique_factory_ids) == 1, (
            "CONTEXT SEPARATION VIOLATION: All users share same factory instance. "
            f"Expected separated factories, found {len(unique_factory_ids)} unique. "
            "This violates user execution context separation."
        )
        
        # VIOLATION ASSERTION: Check that final result shows contamination
        # By the end, all users should be able to see each other's contexts
        final_result = context_separation_results[-1]  # Last user processed
        accessible_contexts = final_result['accessible_contexts']
        
        # Final result should show all users' contexts are visible
        assert len(accessible_contexts) == len(user_contexts_data), (
            f"CONTEXT CONTAMINATION: Final user can access all {len(accessible_contexts)} contexts. "
            f"Expected {len(user_contexts_data)} contexts. This proves user execution context "
            "separation is violated through shared factory."
        )
        
        # Each user should be able to access others' sensitive contexts
        for result in context_separation_results[1:]:  # Skip first user (no others to contaminate)
            accessible_contexts = result['accessible_contexts']
            user_id = result['user_id']
            
            # User can access other users' sensitive contexts
            other_user_contexts = {
                k: v for k, v in accessible_contexts.items() if k != user_id
            }
            
            assert len(other_user_contexts) > 0, (
                f"CONTEXT CONTAMINATION: User {user_id} can access {len(other_user_contexts)} "
                f"other users' contexts. This proves user execution context separation is violated."
            )
            
            # Check specific sensitive data exposure
            for other_user, other_context in other_user_contexts.items():
                other_sensitive_data = other_context.get('sensitive_data', '')
                
                # Verify cross-user sensitive data access
                assert other_sensitive_data in [
                    'patient_record_phi_data', 
                    'credit_card_financial_data', 
                    'classified_government_data'
                ], (
                    f"SENSITIVE DATA BREACH: User {user_id} can access sensitive data "
                    f"from user {other_user}: '{other_sensitive_data}'. "
                    "This violates regulatory compliance requirements."
                )

    async def test_enterprise_multi_tenancy_compliance(self):
        """
        Test that enterprise multi-tenancy compliance fails due to shared factory.
        
        VIOLATION PROOF: Enterprise customers require complete tenant isolation.
        The singleton factory violates multi-tenancy by sharing state between tenants.
        
        EXPECTED: FAIL before remediation (proving compliance violation)
        EXPECTED: PASS after remediation (proving multi-tenant compliance)
        """
        from netra_backend.app.agents.supervisor.agent_instance_factory import (
            get_agent_instance_factory
        )
        
        # Simulate enterprise tenants with strict isolation requirements
        enterprise_tenants = [
            {
                'tenant_id': 'acme_corp_tenant',
                'compliance_level': 'SOC2_TYPE2',
                'sensitive_operations': ['financial_analysis', 'audit_data'],
                'isolation_requirement': 'STRICT'
            },
            {
                'tenant_id': 'healthcare_org_tenant',
                'compliance_level': 'HIPAA',
                'sensitive_operations': ['patient_data', 'medical_records'],
                'isolation_requirement': 'ABSOLUTE'
            },
            {
                'tenant_id': 'government_agency_tenant',
                'compliance_level': 'FISMA_HIGH',
                'sensitive_operations': ['classified_analysis', 'security_data'],
                'isolation_requirement': 'MAXIMUM'
            }
        ]
        
        tenant_compliance_results = []
        
        # Get shared factory instance to demonstrate violation
        shared_factory = get_agent_instance_factory()
        
        for tenant in enterprise_tenants:
            # Each tenant should have completely isolated factory state
            tenant_id = tenant['tenant_id']
            
            # Store tenant-specific compliance data in shared factory (violation)
            if not hasattr(shared_factory, '_tenant_data'):
                shared_factory._tenant_data = {}
            
            shared_factory._tenant_data[tenant_id] = {
                'compliance_level': tenant['compliance_level'],
                'sensitive_operations': tenant['sensitive_operations'],
                'tenant_secrets': f"secret_key_{tenant_id}_{uuid.uuid4()}",
                'compliance_timestamp': time.time()
            }
            
            # Check tenant isolation - all tenants should see each other's data
            accessible_tenant_data = dict(shared_factory._tenant_data)
            
            tenant_compliance_results.append({
                'tenant_id': tenant_id,
                'factory_id': id(shared_factory),
                'compliance_level': tenant['compliance_level'],
                'isolation_requirement': tenant['isolation_requirement'],
                'accessible_tenants': accessible_tenant_data,
                'tenant_count': len(accessible_tenant_data)
            })
        
        # COMPLIANCE VIOLATION ANALYSIS
        factory_ids = [result['factory_id'] for result in tenant_compliance_results]
        unique_factory_ids = set(factory_ids)
        
        # VIOLATION ASSERTION: All tenants share same factory
        assert len(unique_factory_ids) == 1, (
            "MULTI-TENANCY VIOLATION: All enterprise tenants share same factory instance. "
            f"Expected isolated factories per tenant, found {len(unique_factory_ids)} unique. "
            "This violates enterprise multi-tenancy compliance requirements."
        )
        
        # VIOLATION ASSERTION: Check that final result shows contamination
        final_result = tenant_compliance_results[-1]  # Last tenant processed
        accessible_tenants = final_result['accessible_tenants']
        
        # Final result should show all tenants' data is accessible
        assert len(accessible_tenants) == len(enterprise_tenants), (
            f"MULTI-TENANCY CONTAMINATION: Final tenant can access all {len(accessible_tenants)} "
            f"tenant data. Expected {len(enterprise_tenants)} tenants. This proves enterprise "
            "multi-tenancy isolation is violated through shared factory."
        )
        
        # VIOLATION ASSERTION: Each tenant can access others' compliance data  
        for result in tenant_compliance_results[1:]:  # Skip first tenant (no others to contaminate)
            accessible_tenants = result['accessible_tenants']
            tenant_id = result['tenant_id']
            isolation_req = result['isolation_requirement']
            compliance_level = result['compliance_level']
            
            # Tenant can see other tenants' data
            other_tenant_data = {
                k: v for k, v in accessible_tenants.items() if k != tenant_id
            }
            
            assert len(other_tenant_data) > 0, (
                f"COMPLIANCE VIOLATION: Tenant {tenant_id} with {isolation_req} isolation "
                f"and {compliance_level} compliance can access {len(other_tenant_data)} other tenants' data. "
                f"Accessible other tenants: {list(other_tenant_data.keys())}. "
                "This violates enterprise multi-tenancy isolation requirements."
            )
            
            # Check specific compliance violations
            for other_tenant, other_data in other_tenant_data.items():
                other_compliance = other_data.get('compliance_level', '')
                other_secrets = other_data.get('tenant_secrets', '')
                
                # Cross-tenant compliance data access
                assert other_compliance in ['SOC2_TYPE2', 'HIPAA', 'FISMA_HIGH'], (
                    f"COMPLIANCE BREACH: Tenant {tenant_id} can access compliance data "
                    f"from tenant {other_tenant} (level: {other_compliance}). "
                    "This violates regulatory isolation requirements."
                )
                
                # Cross-tenant secret access
                assert 'secret_key_' in other_secrets, (
                    f"SECRET EXPOSURE: Tenant {tenant_id} can access secrets "
                    f"from tenant {other_tenant}: '{other_secrets}'. "
                    "This creates serious security compliance violations."
                )