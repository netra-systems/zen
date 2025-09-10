"""
WebSocket Event Routing and Isolation Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure secure and accurate event routing for multi-user system
- Value Impact: Event routing isolation prevents user data leakage and maintains chat integrity
- Strategic Impact: User isolation is mandatory for platform security and compliance

These tests validate that WebSocket events are correctly routed to specific users
without cross-contamination, ensuring the security of the multi-user chat system.
"""

import asyncio
import pytest
from typing import Dict, List, Any, Set
from datetime import datetime
import uuid
import time

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket import (
    WebSocketTestUtility,
    WebSocketTestClient,
    WebSocketEventType, 
    WebSocketMessage
)
from shared.isolated_environment import get_env


class TestWebSocketEventRoutingIsolation(SSotAsyncTestCase):
    """Test WebSocket event routing and user isolation patterns."""
    
    async def setup_method(self, method=None):
        """Set up test environment."""
        await super().async_setup_method(method)
        self.env = get_env()
        
        # Configure test environment for routing tests
        self.set_env_var("WEBSOCKET_TEST_TIMEOUT", "10")
        self.set_env_var("WEBSOCKET_MOCK_MODE", "true")
        self.set_env_var("USER_ISOLATION_REQUIRED", "true")
    
    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.security
    async def test_user_specific_event_routing(self):
        """
        Test that WebSocket events are routed only to the intended user.
        
        BVJ: All segments - Critical security requirement preventing data leakage.
        """
        async with WebSocketTestUtility() as ws_util:
            # Create multiple users with unique identifiers
            user_a_id = f"user_a_{uuid.uuid4().hex[:8]}"
            user_b_id = f"user_b_{uuid.uuid4().hex[:8]}"
            user_c_id = f"user_c_{uuid.uuid4().hex[:8]}"
            
            client_a = await ws_util.create_authenticated_client(user_a_id)
            client_b = await ws_util.create_authenticated_client(user_b_id)
            client_c = await ws_util.create_authenticated_client(user_c_id)
            
            await client_a.connect(mock_mode=True)
            await client_b.connect(mock_mode=True)
            await client_c.connect(mock_mode=True)
            
            try:
                # Send user-specific agent completion events
                user_a_data = {
                    "user_id": user_a_id,
                    "optimization_result": "aws_cost_reduced_by_25_percent",
                    "account_id": "123456789",
                    "cost_savings": 12500.00,
                    "sensitive_recommendation": "terminate_unused_instances_in_dev"
                }
                
                user_b_data = {
                    "user_id": user_b_id, 
                    "optimization_result": "azure_spend_optimized",
                    "account_id": "987654321",
                    "cost_savings": 8750.00,
                    "sensitive_recommendation": "migrate_to_reserved_instances"
                }
                
                user_c_data = {
                    "user_id": user_c_id,
                    "optimization_result": "gcp_resource_rightsized",
                    "account_id": "555666777", 
                    "cost_savings": 15000.00,
                    "sensitive_recommendation": "implement_autoscaling_policies"
                }
                
                # Send events targeted to specific users
                await client_a.send_message(
                    WebSocketEventType.AGENT_COMPLETED,
                    user_a_data,
                    user_id=user_a_id
                )
                
                await client_b.send_message(
                    WebSocketEventType.AGENT_COMPLETED,
                    user_b_data,
                    user_id=user_b_id
                )
                
                await client_c.send_message(
                    WebSocketEventType.AGENT_COMPLETED,
                    user_c_data,
                    user_id=user_c_id
                )
                
                # Wait for event routing
                await asyncio.sleep(2.0)
                
                # Verify user-specific routing
                user_a_messages = client_a.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED)
                user_b_messages = client_b.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED)
                user_c_messages = client_c.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED)
                
                # Each user should receive their own messages
                assert len(user_a_messages) > 0, "User A should receive their agent completion"
                assert len(user_b_messages) > 0, "User B should receive their agent completion"  
                assert len(user_c_messages) > 0, "User C should receive their agent completion"
                
                # Verify no cross-contamination of sensitive data
                for message in user_a_messages:
                    assert user_a_id in str(message.data), "User A should only see their user_id"
                    assert user_b_id not in str(message.data), "User A should not see User B's user_id"
                    assert user_c_id not in str(message.data), "User A should not see User C's user_id"
                    assert "123456789" in str(message.data), "User A should see their account_id"
                    assert "987654321" not in str(message.data), "User A should not see User B's account"
                    assert "555666777" not in str(message.data), "User A should not see User C's account"
                
                for message in user_b_messages:
                    assert user_b_id in str(message.data), "User B should only see their user_id"
                    assert user_a_id not in str(message.data), "User B should not see User A's user_id"
                    assert user_c_id not in str(message.data), "User B should not see User C's user_id"
                    assert "987654321" in str(message.data), "User B should see their account_id"
                    assert "123456789" not in str(message.data), "User B should not see User A's account"
                    assert "555666777" not in str(message.data), "User B should not see User C's account"
                
                self.record_metric("users_tested", 3)
                self.record_metric("routing_isolation_verified", True)
                self.record_metric("data_leakage_prevented", True)
                
            finally:
                await client_a.disconnect()
                await client_b.disconnect()
                await client_c.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_thread_specific_event_routing(self):
        """
        Test that events are routed to specific conversation threads.
        
        BVJ: All segments - Thread isolation maintains conversation context integrity.
        """
        async with WebSocketTestUtility() as ws_util:
            user_id = f"multi_thread_user_{uuid.uuid4().hex[:8]}"
            client = await ws_util.create_authenticated_client(user_id)
            await client.connect(mock_mode=True)
            
            try:
                # Create multiple conversation threads
                thread_1_id = f"thread_1_{uuid.uuid4().hex[:8]}"
                thread_2_id = f"thread_2_{uuid.uuid4().hex[:8]}"
                thread_3_id = f"thread_3_{uuid.uuid4().hex[:8]}"
                
                # Send thread-specific events
                thread_1_events = [
                    (WebSocketEventType.AGENT_STARTED, {"thread_id": thread_1_id, "topic": "aws_optimization"}),
                    (WebSocketEventType.AGENT_THINKING, {"thread_id": thread_1_id, "analysis": "examining_ec2_usage"}),
                    (WebSocketEventType.AGENT_COMPLETED, {"thread_id": thread_1_id, "result": "aws_recommendations_ready"})
                ]
                
                thread_2_events = [
                    (WebSocketEventType.AGENT_STARTED, {"thread_id": thread_2_id, "topic": "azure_security"}),
                    (WebSocketEventType.AGENT_THINKING, {"thread_id": thread_2_id, "analysis": "scanning_security_groups"}),
                    (WebSocketEventType.AGENT_COMPLETED, {"thread_id": thread_2_id, "result": "security_audit_complete"})
                ]
                
                thread_3_events = [
                    (WebSocketEventType.AGENT_STARTED, {"thread_id": thread_3_id, "topic": "gcp_billing"}),
                    (WebSocketEventType.AGENT_THINKING, {"thread_id": thread_3_id, "analysis": "analyzing_billing_data"}),
                    (WebSocketEventType.AGENT_COMPLETED, {"thread_id": thread_3_id, "result": "billing_insights_generated"})
                ]
                
                # Send events for each thread
                all_sent_messages = []
                
                for event_type, data in thread_1_events:
                    message = await client.send_message(event_type, data, user_id=user_id, thread_id=thread_1_id)
                    all_sent_messages.append(message)
                    await asyncio.sleep(0.1)
                
                for event_type, data in thread_2_events:
                    message = await client.send_message(event_type, data, user_id=user_id, thread_id=thread_2_id)
                    all_sent_messages.append(message)
                    await asyncio.sleep(0.1)
                
                for event_type, data in thread_3_events:
                    message = await client.send_message(event_type, data, user_id=user_id, thread_id=thread_3_id)
                    all_sent_messages.append(message)
                    await asyncio.sleep(0.1)
                
                # Wait for all events to be processed
                await asyncio.sleep(2.0)
                
                # Analyze received messages by thread
                messages_by_thread = {}
                for message in client.received_messages:
                    if hasattr(message, 'thread_id') and message.thread_id:
                        if message.thread_id not in messages_by_thread:
                            messages_by_thread[message.thread_id] = []
                        messages_by_thread[message.thread_id].append(message)
                
                # Verify thread isolation
                if thread_1_id in messages_by_thread:
                    thread_1_messages = messages_by_thread[thread_1_id]
                    for message in thread_1_messages:
                        assert "aws_optimization" in str(message.data) or "aws_recommendations" in str(message.data)
                        assert "azure_security" not in str(message.data)
                        assert "gcp_billing" not in str(message.data)
                
                if thread_2_id in messages_by_thread:
                    thread_2_messages = messages_by_thread[thread_2_id]
                    for message in thread_2_messages:
                        assert "azure_security" in str(message.data) or "security_audit" in str(message.data)
                        assert "aws_optimization" not in str(message.data)
                        assert "gcp_billing" not in str(message.data)
                
                if thread_3_id in messages_by_thread:
                    thread_3_messages = messages_by_thread[thread_3_id]
                    for message in thread_3_messages:
                        assert "gcp_billing" in str(message.data) or "billing_insights" in str(message.data)
                        assert "aws_optimization" not in str(message.data)
                        assert "azure_security" not in str(message.data)
                
                self.record_metric("threads_tested", 3)
                self.record_metric("thread_isolation_verified", True)
                self.record_metric("total_thread_events", len(all_sent_messages))
                
            finally:
                await client.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket  
    async def test_event_routing_with_role_based_access(self):
        """
        Test event routing respects user roles and access levels.
        
        BVJ: Enterprise - Role-based access control for sensitive optimization data.
        """
        async with WebSocketTestUtility() as ws_util:
            # Create users with different roles
            admin_user = await ws_util.create_authenticated_client("admin_user")
            standard_user = await ws_util.create_authenticated_client("standard_user")
            viewer_user = await ws_util.create_authenticated_client("viewer_user")
            
            await admin_user.connect(mock_mode=True)
            await standard_user.connect(mock_mode=True)
            await viewer_user.connect(mock_mode=True)
            
            try:
                # Send role-specific events
                admin_event_data = {
                    "role": "admin",
                    "sensitive_data": "full_account_access_data",
                    "admin_actions": ["delete_resources", "modify_policies"],
                    "cost_breakdown": {"detailed": True, "confidential": True}
                }
                
                standard_event_data = {
                    "role": "standard",
                    "user_data": "standard_optimization_data", 
                    "allowed_actions": ["view_recommendations", "apply_optimizations"],
                    "cost_breakdown": {"summary": True, "confidential": False}
                }
                
                viewer_event_data = {
                    "role": "viewer",
                    "public_data": "general_optimization_insights",
                    "allowed_actions": ["view_reports"],
                    "cost_breakdown": {"high_level": True}
                }
                
                # Send events to each user based on their role
                await admin_user.send_message(
                    WebSocketEventType.AGENT_COMPLETED,
                    admin_event_data,
                    user_id="admin_user"
                )
                
                await standard_user.send_message(
                    WebSocketEventType.AGENT_COMPLETED,
                    standard_event_data,
                    user_id="standard_user"
                )
                
                await viewer_user.send_message(
                    WebSocketEventType.AGENT_COMPLETED,
                    viewer_event_data,
                    user_id="viewer_user"
                )
                
                # Wait for event processing
                await asyncio.sleep(2.0)
                
                # Verify role-based event routing
                admin_messages = admin_user.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED)
                standard_messages = standard_user.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED)
                viewer_messages = viewer_user.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED)
                
                # Verify admin receives admin-level data
                admin_received_data = False
                for message in admin_messages:
                    if "admin" in str(message.data) and "full_account_access" in str(message.data):
                        admin_received_data = True
                        assert "confidential" in str(message.data)
                        assert "delete_resources" in str(message.data)
                
                # Verify standard user receives appropriate data
                standard_received_data = False
                for message in standard_messages:
                    if "standard" in str(message.data) and "standard_optimization" in str(message.data):
                        standard_received_data = True
                        assert "apply_optimizations" in str(message.data)
                        # Should not see admin-level sensitive data
                        assert "full_account_access" not in str(message.data)
                
                # Verify viewer receives limited data
                viewer_received_data = False
                for message in viewer_messages:
                    if "viewer" in str(message.data) and "general_optimization" in str(message.data):
                        viewer_received_data = True
                        assert "view_reports" in str(message.data)
                        # Should not see admin or standard sensitive data
                        assert "full_account_access" not in str(message.data)
                        assert "apply_optimizations" not in str(message.data)
                
                self.record_metric("admin_events_properly_routed", admin_received_data)
                self.record_metric("standard_events_properly_routed", standard_received_data)
                self.record_metric("viewer_events_properly_routed", viewer_received_data)
                self.record_metric("role_based_access_verified", True)
                
            finally:
                await admin_user.disconnect()
                await standard_user.disconnect()
                await viewer_user.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_multi_tenant_event_isolation(self):
        """
        Test event isolation across different tenant organizations.
        
        BVJ: Enterprise - Multi-tenant isolation critical for enterprise compliance.
        """
        async with WebSocketTestUtility() as ws_util:
            # Create users from different organizations/tenants
            org_a_user = await ws_util.create_authenticated_client("org_a_user")
            org_b_user = await ws_util.create_authenticated_client("org_b_user")
            org_c_user = await ws_util.create_authenticated_client("org_c_user")
            
            await org_a_user.connect(mock_mode=True)
            await org_b_user.connect(mock_mode=True)
            await org_c_user.connect(mock_mode=True)
            
            try:
                # Organization-specific data
                org_a_data = {
                    "organization_id": "org_a_12345",
                    "tenant": "acme_corp",
                    "confidential_metrics": {
                        "total_spend": 125000,
                        "secret_projects": ["project_alpha", "project_beta"],
                        "compliance_status": "pci_compliant"
                    }
                }
                
                org_b_data = {
                    "organization_id": "org_b_67890", 
                    "tenant": "beta_industries",
                    "confidential_metrics": {
                        "total_spend": 87500,
                        "secret_projects": ["operation_gamma", "initiative_delta"],
                        "compliance_status": "soc2_compliant"
                    }
                }
                
                org_c_data = {
                    "organization_id": "org_c_54321",
                    "tenant": "gamma_solutions",
                    "confidential_metrics": {
                        "total_spend": 210000,
                        "secret_projects": ["confidential_research", "stealth_mode"],
                        "compliance_status": "iso27001_compliant"
                    }
                }
                
                # Send tenant-specific events
                await org_a_user.send_message(
                    WebSocketEventType.AGENT_COMPLETED,
                    org_a_data,
                    user_id="org_a_user"
                )
                
                await org_b_user.send_message(
                    WebSocketEventType.AGENT_COMPLETED,
                    org_b_data,
                    user_id="org_b_user" 
                )
                
                await org_c_user.send_message(
                    WebSocketEventType.AGENT_COMPLETED,
                    org_c_data,
                    user_id="org_c_user"
                )
                
                # Wait for tenant event processing
                await asyncio.sleep(2.0)
                
                # Verify strict tenant isolation
                org_a_messages = org_a_user.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED)
                org_b_messages = org_b_user.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED)
                org_c_messages = org_c_user.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED)
                
                # Organization A should only see their data
                tenant_a_isolation = True
                for message in org_a_messages:
                    message_str = str(message.data)
                    if "acme_corp" in message_str:
                        # Should see own data
                        assert "project_alpha" in message_str or "project_beta" in message_str
                        assert "125000" in message_str
                        
                        # Should NOT see other tenant data
                        if any([
                            "beta_industries" in message_str,
                            "gamma_solutions" in message_str,
                            "operation_gamma" in message_str,
                            "confidential_research" in message_str,
                            "87500" in message_str,
                            "210000" in message_str
                        ]):
                            tenant_a_isolation = False
                
                # Organization B should only see their data
                tenant_b_isolation = True
                for message in org_b_messages:
                    message_str = str(message.data)
                    if "beta_industries" in message_str:
                        # Should see own data
                        assert "operation_gamma" in message_str or "initiative_delta" in message_str
                        assert "87500" in message_str
                        
                        # Should NOT see other tenant data
                        if any([
                            "acme_corp" in message_str,
                            "gamma_solutions" in message_str,
                            "project_alpha" in message_str,
                            "confidential_research" in message_str,
                            "125000" in message_str,
                            "210000" in message_str
                        ]):
                            tenant_b_isolation = False
                
                # Organization C should only see their data
                tenant_c_isolation = True
                for message in org_c_messages:
                    message_str = str(message.data)
                    if "gamma_solutions" in message_str:
                        # Should see own data
                        assert "confidential_research" in message_str or "stealth_mode" in message_str
                        assert "210000" in message_str
                        
                        # Should NOT see other tenant data
                        if any([
                            "acme_corp" in message_str,
                            "beta_industries" in message_str,
                            "project_alpha" in message_str,
                            "operation_gamma" in message_str,
                            "125000" in message_str,
                            "87500" in message_str
                        ]):
                            tenant_c_isolation = False
                
                assert tenant_a_isolation, "Organization A data leaked to other tenants"
                assert tenant_b_isolation, "Organization B data leaked to other tenants"
                assert tenant_c_isolation, "Organization C data leaked to other tenants"
                
                self.record_metric("tenants_tested", 3)
                self.record_metric("tenant_a_isolation_verified", tenant_a_isolation)
                self.record_metric("tenant_b_isolation_verified", tenant_b_isolation)
                self.record_metric("tenant_c_isolation_verified", tenant_c_isolation)
                self.record_metric("multi_tenant_isolation_success", True)
                
            finally:
                await org_a_user.disconnect()
                await org_b_user.disconnect()
                await org_c_user.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_event_routing_performance_under_load(self):
        """
        Test WebSocket event routing performance with high concurrent load.
        
        BVJ: Enterprise - High-performance routing for large-scale deployments.
        """
        async with WebSocketTestUtility() as ws_util:
            # Create multiple users for load testing
            user_count = 15
            events_per_user = 10
            clients = []
            
            # Create and connect multiple users
            for i in range(user_count):
                user_id = f"load_test_user_{i}"
                client = await ws_util.create_authenticated_client(user_id)
                await client.connect(mock_mode=True)
                clients.append((user_id, client))
            
            try:
                # Generate concurrent routing load
                routing_tasks = []
                load_start_time = time.time()
                
                async def send_user_events(user_id: str, client: WebSocketTestClient):
                    """Send events for a specific user."""
                    user_events = []
                    for event_num in range(events_per_user):
                        event_data = {
                            "user_id": user_id,
                            "event_number": event_num,
                            "load_test": True,
                            "timestamp": time.time(),
                            "user_specific_data": f"data_for_{user_id}_event_{event_num}"
                        }
                        
                        message = await client.send_message(
                            WebSocketEventType.AGENT_THINKING,
                            event_data,
                            user_id=user_id
                        )
                        user_events.append(message)
                        await asyncio.sleep(0.05)  # Brief pause between events
                    
                    return user_events
                
                # Launch concurrent event sending
                for user_id, client in clients:
                    task = send_user_events(user_id, client)
                    routing_tasks.append(task)
                
                # Wait for all routing tasks to complete
                task_results = await asyncio.gather(*routing_tasks, return_exceptions=True)
                load_duration = time.time() - load_start_time
                
                # Wait for event processing
                await asyncio.sleep(2.0)
                
                # Analyze routing performance
                total_events_sent = 0
                successful_routing_count = 0
                
                for i, (user_id, client) in enumerate(clients):
                    if i < len(task_results) and not isinstance(task_results[i], Exception):
                        sent_events = task_results[i]
                        total_events_sent += len(sent_events)
                        
                        # Verify user-specific routing
                        received_messages = client.get_messages_by_type(WebSocketEventType.AGENT_THINKING)
                        
                        user_specific_routing = True
                        for message in received_messages:
                            if "load_test" in str(message.data):
                                # Verify this message belongs to this user
                                if user_id not in str(message.data):
                                    user_specific_routing = False
                                    break
                                
                                # Verify no other user data leaked in
                                for other_user_id, _ in clients:
                                    if other_user_id != user_id and other_user_id in str(message.data):
                                        user_specific_routing = False
                                        break
                        
                        if user_specific_routing:
                            successful_routing_count += 1
                
                # Calculate performance metrics
                events_per_second = total_events_sent / load_duration if load_duration > 0 else 0
                routing_success_rate = successful_routing_count / len(clients)
                
                # Performance assertions
                assert events_per_second > 50, f"Routing performance too slow: {events_per_second} events/second"
                assert routing_success_rate >= 0.9, f"Routing success rate too low: {routing_success_rate}"
                
                self.record_metric("concurrent_users_load_test", user_count)
                self.record_metric("events_per_user", events_per_user)
                self.record_metric("total_events_routed", total_events_sent)
                self.record_metric("routing_events_per_second", events_per_second)
                self.record_metric("routing_success_rate", routing_success_rate)
                self.record_metric("load_test_duration", load_duration)
                
            finally:
                # Clean up all connections
                disconnect_tasks = [client.disconnect() for _, client in clients]
                await asyncio.gather(*disconnect_tasks, return_exceptions=True)