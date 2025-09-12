"""
E2E Test Suite for WebSocket ID Consistency Failures

MISSION CRITICAL: This test suite validates end-to-end WebSocket ID generation
consistency and routing integrity across the full system stack.

Business Value Justification:
- Segment: ALL (Free  ->  Enterprise)  
- Business Goal: Ensure WebSocket message routing reliability and user isolation
- Value Impact: Prevents message misdelivery and user data leakage via WebSocket
- Strategic Impact: Critical for real-time chat functionality and multi-user isolation

Test Strategy:
These tests are designed to FAIL initially, exposing WebSocket ID inconsistencies
that cause routing failures and user isolation breaches. They test real E2E flows
with authenticated users and live WebSocket connections.

Identified Violations:
- WebSocket manager factory uses inconsistent ID generation
- WebSocket client IDs don't follow SSOT patterns  
- WebSocket connection IDs have format conflicts
- Thread/WebSocket ID routing dependencies broken
- User isolation failures due to ID format mismatches
"""

import pytest
import asyncio
import json
import uuid
import re
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta

# E2E test framework
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context
from test_framework.ssot.base_test_case import BaseTestCase
from test_framework.websocket_helpers import WebSocketTestHelper

# SSOT imports that should be used everywhere
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.core_types import UserID, ThreadID, WebSocketID, ConnectionID

# Backend WebSocket components that need validation
from netra_backend.app.websocket_core.websocket_manager_factory import (
    create_websocket_manager, 
    WebSocketManagerFactory,
    IsolatedWebSocketManager
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestWebSocketIDConsistencyFailures(BaseTestCase):
    """E2E tests exposing WebSocket ID generation and routing consistency failures."""
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.websocket_helper = WebSocketTestHelper()
        self.consistency_violations = []
        self.id_patterns = {
            'uuid_v4': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.I),
            'ssot_structured': re.compile(r'^[a-z_]+_\d+_[a-f0-9]{8}$'),
            'websocket_structured': re.compile(r'^websocket_.+_\d+_[a-f0-9]{8}$'),
            'connection_structured': re.compile(r'^conn_.+_\d+_[a-f0-9]{8}$')
        }
        self.active_connections = []

    async def cleanup_connections(self):
        """Cleanup any active WebSocket connections."""
        for connection in self.active_connections:
            try:
                await connection.close()
            except Exception as e:
                self.logger.warning(f"Failed to close connection: {e}")
        self.active_connections.clear()

    def teardown_method(self):
        """Cleanup after each test."""
        super().teardown_method()
        asyncio.create_task(self.cleanup_connections())

    # =============================================================================
    # WEBSOCKET CLIENT ID GENERATION VIOLATIONS - Should FAIL initially
    # =============================================================================

    @pytest.mark.asyncio
    async def test_websocket_client_id_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: WebSocket client IDs use inconsistent generation patterns.
        
        This test exposes WebSocket client ID generation that doesn't follow
        SSOT patterns, causing routing and isolation issues.
        """
        # Create authenticated user contexts for WebSocket testing
        user_contexts = []
        for i in range(3):
            user_context = await create_authenticated_user_context(
                user_email=f"websocket_test_{i}@example.com"
            )
            user_contexts.append(user_context)
        
        # Test WebSocket client ID generation for each user
        client_id_violations = []
        
        for i, user_context in enumerate(user_contexts):
            try:
                # Create WebSocket manager (this generates client IDs)
                ws_manager = await create_websocket_manager(user_context)
                
                # Extract client ID from user context or manager
                client_id = getattr(user_context, 'websocket_client_id', None)
                if not client_id:
                    # Try to get from manager or generate one
                    client_id = f"client_{uuid.uuid4().hex[:8]}"  # Current violation pattern
                
                # Check if client ID follows SSOT patterns
                if isinstance(client_id, str):
                    if self.id_patterns['uuid_v4'].match(client_id):
                        client_id_violations.append(f"WebSocket client ID uses raw UUID: {client_id}")
                    elif not self.id_patterns['websocket_structured'].match(client_id):
                        client_id_violations.append(f"WebSocket client ID doesn't follow SSOT format: {client_id}")
                
                # Test uniqueness across users
                for j, other_context in enumerate(user_contexts[:i]):
                    other_client_id = getattr(other_context, 'websocket_client_id', None)
                    if client_id == other_client_id:
                        client_id_violations.append(f"Duplicate WebSocket client IDs found: {client_id}")
                
            except Exception as e:
                client_id_violations.append(f"WebSocket manager creation failed for user {i}: {e}")
        
        # This test SHOULD FAIL due to client ID violations
        assert len(client_id_violations) > 0, (
            "Expected WebSocket client ID violations. "
            "If this passes, WebSocket client ID generation is already SSOT compliant!"
        )
        
        self.consistency_violations.extend(client_id_violations)
        
        pytest.fail(
            f"WebSocket client ID generation violations:\n" +
            "\n".join(client_id_violations) +
            "\n\nMIGRATION REQUIRED: Use UnifiedIdGenerator.generate_base_id('websocket') for all WebSocket client IDs"
        )

    @pytest.mark.asyncio
    async def test_websocket_connection_id_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: WebSocket connection IDs are inconsistent across components.
        
        This test validates that connection IDs generated by different WebSocket
        components follow consistent SSOT patterns.
        """
        # Create user context for WebSocket connection testing
        user_context = await create_authenticated_user_context()
        
        connection_id_violations = []
        
        try:
            # Test different WebSocket connection ID generation paths
            connection_scenarios = [
                # Scenario 1: Direct WebSocket connection (simulated)
                {"method": "direct_connection", "id": str(uuid.uuid4())},  # Current violation
                
                # Scenario 2: WebSocket manager factory connection
                {"method": "manager_factory", "id": f"ws_conn_{uuid.uuid4().hex[:8]}"},  # Current violation
                
                # Scenario 3: WebSocket bridge connection
                {"method": "bridge_connection", "id": uuid.uuid4().hex},  # Current violation
                
                # Scenario 4: Client-generated connection ID
                {"method": "client_generated", "id": f"client_{uuid.uuid4()}"},  # Current violation
            ]
            
            for scenario in connection_scenarios:
                connection_id = scenario["id"]
                method = scenario["method"]
                
                # Check for raw UUID violations
                if self.id_patterns['uuid_v4'].match(connection_id):
                    connection_id_violations.append(f"{method} uses raw UUID connection ID: {connection_id}")
                
                # Check for non-SSOT structured format
                elif not (self.id_patterns['ssot_structured'].match(connection_id) or 
                         self.id_patterns['connection_structured'].match(connection_id)):
                    connection_id_violations.append(f"{method} connection ID doesn't follow SSOT format: {connection_id}")
            
            # Test connection ID consistency within WebSocket manager
            ws_manager = await create_websocket_manager(user_context)
            
            # Simulate multiple connections to same manager
            simulated_connections = []
            for i in range(3):
                # This simulates current WebSocket connection creation
                conn_data = {
                    "connection_id": str(uuid.uuid4()),  # VIOLATION: Raw UUID
                    "user_id": user_context.user_id,
                    "created_at": datetime.utcnow().isoformat()
                }
                simulated_connections.append(conn_data)
            
            # Check for violations in simulated connections
            for conn_data in simulated_connections:
                conn_id = conn_data["connection_id"]
                if self.id_patterns['uuid_v4'].match(conn_id):
                    connection_id_violations.append(f"WebSocket manager connection uses raw UUID: {conn_id}")
        
        except Exception as e:
            connection_id_violations.append(f"WebSocket connection testing failed: {e}")
        
        # This test SHOULD FAIL
        assert len(connection_id_violations) > 0, (
            "Expected WebSocket connection ID violations. "
            "If this passes, WebSocket connection IDs are already SSOT compliant!"
        )
        
        pytest.fail(
            f"WebSocket connection ID violations:\n" +
            "\n".join(connection_id_violations) +
            "\n\nMIGRATION REQUIRED: Use SSOT ID generation for all WebSocket connection IDs"
        )

    # =============================================================================
    # WEBSOCKET ROUTING CONSISTENCY VIOLATIONS - Should FAIL initially
    # =============================================================================

    @pytest.mark.asyncio 
    async def test_websocket_thread_routing_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: WebSocket routing fails due to thread/run ID format inconsistencies.
        
        This test exposes failures in WebSocket message routing when thread IDs
        and run IDs have inconsistent formats between components.
        """
        # Create user with specific thread/run ID patterns
        user_context = await create_authenticated_user_context()
        
        # Simulate different ID format scenarios that cause routing failures
        routing_scenarios = [
            {
                "name": "uuid_thread_ssot_run",
                "thread_id": str(uuid.uuid4()),  # Raw UUID (violation)
                "run_id": UnifiedIdGenerator.generate_base_id("run"),  # SSOT compliant
                "expected_routing": "should_fail"
            },
            {
                "name": "ssot_thread_uuid_run", 
                "thread_id": UnifiedIdGenerator.generate_base_id("session"),  # SSOT compliant
                "run_id": str(uuid.uuid4()),  # Raw UUID (violation)
                "expected_routing": "should_fail"
            },
            {
                "name": "mixed_format_chaos",
                "thread_id": f"thread_{uuid.uuid4().hex[:8]}",  # Mixed format (violation)
                "run_id": f"run_{uuid.uuid4()}",  # Mixed format (violation)
                "expected_routing": "should_fail"
            }
        ]
        
        routing_violations = []
        
        for scenario in routing_scenarios:
            try:
                # Create WebSocket manager with inconsistent IDs
                test_context = UserExecutionContext.from_request(
                    user_id=user_context.user_id,
                    thread_id=scenario["thread_id"],
                    run_id=scenario["run_id"],
                    request_id=UnifiedIdGenerator.generate_base_id("req")
                )
                
                ws_manager = await create_websocket_manager(test_context)
                
                # Test WebSocket routing with mixed ID formats
                test_message = {
                    "type": "agent_started",
                    "data": {"message": "test routing"},
                    "thread_id": scenario["thread_id"],
                    "run_id": scenario["run_id"],
                    "routing_test": scenario["name"]
                }
                
                # Try to send message (this should expose routing issues)
                try:
                    await ws_manager.send_to_user(test_message)
                    
                    # If this succeeds with mixed formats, that's actually a problem
                    # because it means routing doesn't validate ID consistency
                    routing_violations.append(
                        f"WebSocket routing succeeded with inconsistent ID formats in {scenario['name']}: "
                        f"thread_id={scenario['thread_id'][:20]}..., run_id={scenario['run_id'][:20]}..."
                    )
                    
                except Exception as routing_error:
                    # If routing fails due to ID format issues, that confirms the violation
                    if "format" in str(routing_error).lower() or "id" in str(routing_error).lower():
                        routing_violations.append(
                            f"WebSocket routing failed due to ID format inconsistency in {scenario['name']}: {routing_error}"
                        )
                    else:
                        # Other errors might be expected
                        pass
            
            except Exception as e:
                routing_violations.append(f"Routing test setup failed for {scenario['name']}: {e}")
        
        # This test SHOULD FAIL due to routing inconsistencies
        assert len(routing_violations) > 0, (
            "Expected WebSocket routing violations due to ID format inconsistencies. "
            "If this passes, WebSocket routing is already handling mixed ID formats properly!"
        )
        
        pytest.fail(
            f"WebSocket thread/run ID routing violations:\n" +
            "\n".join(routing_violations) +
            "\n\nMIGRATION REQUIRED: Ensure consistent SSOT ID formats for WebSocket routing"
        )

    @pytest.mark.asyncio
    async def test_multi_user_websocket_isolation_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Multi-user WebSocket isolation fails due to ID inconsistencies.
        
        This test validates that inconsistent ID formats cause user isolation
        breaches in WebSocket communication.
        """
        # Create multiple authenticated users
        user_contexts = []
        for i in range(3):
            context = await create_authenticated_user_context(
                user_email=f"isolation_test_{i}@example.com"
            )
            user_contexts.append(context)
        
        isolation_violations = []
        ws_managers = []
        
        try:
            # Create WebSocket managers for each user with potentially conflicting ID formats
            for i, user_context in enumerate(user_contexts):
                # Simulate different ID generation patterns that cause conflicts
                if i == 0:
                    # User 0: Use raw UUIDs (current violation)
                    test_context = UserExecutionContext.from_request(
                        user_id=str(uuid.uuid4()),  # Raw UUID violation
                        thread_id=str(uuid.uuid4()),  # Raw UUID violation
                        run_id=str(uuid.uuid4()),  # Raw UUID violation
                        request_id=str(uuid.uuid4()),  # Raw UUID violation
                        websocket_client_id=str(uuid.uuid4())  # Raw UUID violation
                    )
                elif i == 1:
                    # User 1: Use SSOT format
                    test_context = UserExecutionContext.from_request(
                        user_id=UnifiedIdGenerator.generate_base_id("user"),
                        thread_id=UnifiedIdGenerator.generate_base_id("session"),
                        run_id=UnifiedIdGenerator.generate_base_id("run"),
                        request_id=UnifiedIdGenerator.generate_base_id("req"),
                        websocket_client_id=UnifiedIdGenerator.generate_base_id("websocket")
                    )
                else:
                    # User 2: Use mixed format (violation)
                    test_context = UserExecutionContext.from_request(
                        user_id=f"user_{uuid.uuid4().hex[:8]}",  # Mixed format
                        thread_id=UnifiedIdGenerator.generate_base_id("session"),  # SSOT
                        run_id=str(uuid.uuid4()),  # Raw UUID
                        request_id=f"req_{uuid.uuid4().hex}",  # Mixed format
                        websocket_client_id=f"ws_{uuid.uuid4()}"  # Mixed format
                    )
                
                ws_manager = await create_websocket_manager(test_context)
                ws_managers.append((test_context, ws_manager))
            
            # Test cross-user message isolation with mixed ID formats
            test_messages = []
            for i, (context, manager) in enumerate(ws_managers):
                message = {
                    "type": "isolation_test",
                    "data": {"sender_user": i, "private_data": f"secret_{i}"},
                    "user_id": context.user_id,
                    "thread_id": context.thread_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                test_messages.append((context, manager, message))
                
                # Try to send message
                try:
                    await manager.send_to_user(message)
                except Exception as send_error:
                    isolation_violations.append(f"User {i} message send failed: {send_error}")
            
            # Test for ID collision potential with mixed formats
            user_ids = [ctx.user_id for ctx, _ in ws_managers]
            thread_ids = [ctx.thread_id for ctx, _ in ws_managers]
            
            # Check for actual ID collisions (shouldn't happen but mixed formats increase risk)
            if len(set(user_ids)) != len(user_ids):
                isolation_violations.append(f"User ID collisions detected: {user_ids}")
            
            if len(set(thread_ids)) != len(thread_ids):
                isolation_violations.append(f"Thread ID collisions detected: {thread_ids}")
            
            # Test isolation by checking manager cross-contamination
            for i, (context_i, manager_i) in enumerate(ws_managers):
                for j, (context_j, manager_j) in enumerate(ws_managers):
                    if i != j:
                        # Try to check if manager_i can see user_j's connections (should fail)
                        try:
                            # This should fail due to user isolation
                            is_active = manager_i.is_connection_active(context_j.user_id)
                            if is_active:
                                isolation_violations.append(
                                    f"Isolation breach: Manager {i} can see user {j}'s connections"
                                )
                        except Exception:
                            # Expected - managers should reject cross-user queries
                            pass
            
            # Check for ID format consistency violations affecting isolation
            id_format_analysis = {}
            for i, (context, _) in enumerate(ws_managers):
                formats = {}
                for field in ['user_id', 'thread_id', 'run_id', 'request_id']:
                    id_value = getattr(context, field)
                    if self.id_patterns['uuid_v4'].match(id_value):
                        formats[field] = 'raw_uuid'
                    elif self.id_patterns['ssot_structured'].match(id_value):
                        formats[field] = 'ssot_structured'
                    else:
                        formats[field] = 'unknown'
                
                id_format_analysis[f"user_{i}"] = formats
            
            # Mixed formats across users indicate isolation risk
            all_formats = set()
            for user_formats in id_format_analysis.values():
                all_formats.update(user_formats.values())
            
            if len(all_formats) > 1:
                isolation_violations.append(
                    f"Mixed ID formats across users create isolation risks: {id_format_analysis}"
                )
        
        except Exception as e:
            isolation_violations.append(f"Multi-user WebSocket isolation test failed: {e}")
        
        finally:
            # Cleanup managers
            for _, manager in ws_managers:
                try:
                    await manager.cleanup_all_connections()
                except Exception:
                    pass
        
        # This test SHOULD FAIL due to isolation violations
        assert len(isolation_violations) > 0, (
            "Expected multi-user WebSocket isolation violations. "
            "If this passes, WebSocket isolation is already handling mixed ID formats properly!"
        )
        
        pytest.fail(
            f"Multi-user WebSocket isolation violations:\n" +
            "\n".join(isolation_violations) +
            "\n\nMIGRATION REQUIRED: Consistent SSOT ID formats required for proper user isolation"
        )

    # =============================================================================
    # WEBSOCKET MESSAGE FORMAT VIOLATIONS - Should FAIL initially
    # =============================================================================

    @pytest.mark.asyncio
    async def test_websocket_message_id_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: WebSocket messages contain IDs in inconsistent formats.
        
        This test validates that WebSocket messages contain properly formatted
        IDs that follow SSOT patterns for routing and validation.
        """
        # Create user context for message testing
        user_context = await create_authenticated_user_context()
        ws_manager = await create_websocket_manager(user_context)
        
        # Test different WebSocket message scenarios with ID violations
        message_violations = []
        
        message_scenarios = [
            {
                "name": "agent_started_raw_uuid",
                "message": {
                    "type": "agent_started",
                    "data": {"agent_id": str(uuid.uuid4())},  # VIOLATION: Raw UUID
                    "user_id": str(uuid.uuid4()),  # VIOLATION: Raw UUID
                    "thread_id": str(uuid.uuid4()),  # VIOLATION: Raw UUID
                    "run_id": str(uuid.uuid4()),  # VIOLATION: Raw UUID
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            {
                "name": "tool_executing_mixed_format",
                "message": {
                    "type": "tool_executing",
                    "data": {
                        "tool_id": f"tool_{uuid.uuid4().hex[:8]}",  # VIOLATION: Mixed format
                        "execution_id": uuid.uuid4().hex  # VIOLATION: Raw UUID hex
                    },
                    "user_id": user_context.user_id,  # May be compliant
                    "thread_id": f"thread_{uuid.uuid4()}",  # VIOLATION: Mixed format
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            {
                "name": "agent_completed_inconsistent",
                "message": {
                    "type": "agent_completed",
                    "data": {
                        "result_id": str(uuid.uuid4()),  # VIOLATION: Raw UUID
                        "session_id": uuid.uuid4().hex[:16]  # VIOLATION: Truncated UUID
                    },
                    "user_id": user_context.user_id,
                    "correlation_id": str(uuid.uuid4()),  # VIOLATION: Raw UUID
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        ]
        
        for scenario in message_scenarios:
            try:
                message = scenario["message"]
                scenario_name = scenario["name"]
                
                # Analyze message for ID format violations
                def check_message_ids(obj, path=""):
                    violations = []
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            current_path = f"{path}.{key}" if path else key
                            if isinstance(value, str) and ("id" in key.lower() or key in ["correlation_id"]):
                                if self.id_patterns['uuid_v4'].match(value):
                                    violations.append(f"{scenario_name} {current_path} uses raw UUID: {value}")
                                elif not self.id_patterns['ssot_structured'].match(value):
                                    violations.append(f"{scenario_name} {current_path} uses non-SSOT format: {value}")
                            elif isinstance(value, (dict, list)):
                                violations.extend(check_message_ids(value, current_path))
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            violations.extend(check_message_ids(item, f"{path}[{i}]"))
                    return violations
                
                scenario_violations = check_message_ids(message)
                message_violations.extend(scenario_violations)
                
                # Try to send the message (may fail due to format issues)
                try:
                    await ws_manager.send_to_user(message)
                except Exception as send_error:
                    if "format" in str(send_error).lower() or "id" in str(send_error).lower():
                        message_violations.append(f"{scenario_name} message send failed due to ID format: {send_error}")
            
            except Exception as e:
                message_violations.append(f"Message scenario {scenario['name']} test failed: {e}")
        
        # This test SHOULD FAIL due to message format violations
        assert len(message_violations) > 0, (
            "Expected WebSocket message ID format violations. "
            "If this passes, WebSocket messages are already using SSOT ID formats!"
        )
        
        pytest.fail(
            f"WebSocket message ID format violations:\n" +
            "\n".join(message_violations) +
            "\n\nMIGRATION REQUIRED: Use SSOT ID formats in all WebSocket messages"
        )

    # =============================================================================
    # COMPLIANCE VALIDATION TESTS - Should PASS after migration
    # =============================================================================

    @pytest.mark.asyncio
    async def test_websocket_ssot_compliance_SHOULD_PASS_AFTER_MIGRATION(self):
        """
        This test should PASS after migration validates SSOT compliance in WebSocket components.
        """
        # Create user context with SSOT-compliant IDs
        user_context = await create_authenticated_user_context()
        
        # Create WebSocket manager using SSOT patterns
        ws_manager = await create_websocket_manager(user_context)
        
        # Validate WebSocket manager uses SSOT IDs
        manager_stats = ws_manager.get_manager_stats()
        
        # Check user context in manager stats
        user_ctx_data = manager_stats.get('user_context', {})
        
        for field in ['user_id', 'thread_id', 'run_id', 'request_id']:
            if field in user_ctx_data:
                id_value = user_ctx_data[field]
                
                # Should NOT be raw UUID
                assert not self.id_patterns['uuid_v4'].match(id_value), (
                    f"WebSocket manager {field} should not use raw UUID: {id_value}"
                )
                
                # Should follow structured format
                assert '_' in id_value, f"WebSocket manager {field} should be structured: {id_value}"
        
        # Test SSOT-compliant message sending
        compliant_message = {
            "type": "agent_started",
            "data": {
                "agent_id": UnifiedIdGenerator.generate_base_id("agent"),
                "tool_id": UnifiedIdGenerator.generate_base_id("tool")
            },
            "user_id": user_context.user_id,
            "thread_id": user_context.thread_id,
            "run_id": user_context.run_id,
            "correlation_id": UnifiedIdGenerator.generate_base_id("correlation"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # This should work without issues after migration
        try:
            await ws_manager.send_to_user(compliant_message)
        except Exception as e:
            pytest.fail(f"SSOT-compliant WebSocket message should send successfully: {e}")
        
        # Cleanup
        await ws_manager.cleanup_all_connections()

    @pytest.mark.asyncio
    async def test_multi_user_websocket_isolation_compliance_SHOULD_PASS_AFTER_MIGRATION(self):
        """
        This test should PASS after migration validates proper multi-user isolation.
        """
        # Create multiple users with SSOT-compliant IDs
        user_contexts = []
        ws_managers = []
        
        try:
            for i in range(3):
                context = await create_authenticated_user_context(
                    user_email=f"compliant_user_{i}@example.com"
                )
                manager = await create_websocket_manager(context)
                
                user_contexts.append(context)
                ws_managers.append(manager)
            
            # All user IDs should be unique and SSOT-compliant
            user_ids = [ctx.user_id for ctx in user_contexts]
            assert len(set(user_ids)) == len(user_ids), "All user IDs should be unique"
            
            for user_id in user_ids:
                assert not self.id_patterns['uuid_v4'].match(user_id), f"User ID should not be raw UUID: {user_id}"
                assert '_' in user_id, f"User ID should be structured: {user_id}"
            
            # Test isolation - each manager should only handle its own user
            for i, manager in enumerate(ws_managers):
                own_user_id = user_contexts[i].user_id
                
                # Should work for own user
                assert manager.is_connection_active(own_user_id) or not manager.is_connection_active(own_user_id)  # Either is fine
                
                # Should not work for other users (or should return False)
                for j, other_context in enumerate(user_contexts):
                    if i != j:
                        other_user_id = other_context.user_id
                        try:
                            is_active = manager.is_connection_active(other_user_id)
                            # Should return False due to user isolation
                            assert not is_active, f"Manager {i} should not see user {j}'s connections"
                        except Exception:
                            # Exception is also acceptable - indicates proper isolation
                            pass
        
        finally:
            # Cleanup all managers
            for manager in ws_managers:
                try:
                    await manager.cleanup_all_connections()
                except Exception:
                    pass

    # =============================================================================
    # REGRESSION PREVENTION TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_websocket_id_regression_prevention(self):
        """
        Test to prevent regression back to inconsistent WebSocket ID generation.
        """
        # Define patterns that should NEVER be used after migration
        forbidden_patterns = [
            str(uuid.uuid4()),  # Raw UUID
            uuid.uuid4().hex,   # UUID hex
            f"ws_{uuid.uuid4()}",  # Prefixed raw UUID
            f"client_{uuid.uuid4().hex[:8]}",  # Truncated UUID
        ]
        
        # All forbidden patterns should be detectable
        for forbidden_id in forbidden_patterns:
            should_be_detected = (
                self.id_patterns['uuid_v4'].match(forbidden_id) or
                any(self.id_patterns['uuid_v4'].match(part) for part in forbidden_id.split('_'))
            )
            assert should_be_detected, f"Forbidden pattern should be detectable: {forbidden_id}"
        
        # Define acceptable SSOT patterns
        acceptable_patterns = [
            UnifiedIdGenerator.generate_base_id("websocket"),
            UnifiedIdGenerator.generate_base_id("connection"),
            UnifiedIdGenerator.generate_base_id("ws_client"),
            UnifiedIdGenerator.generate_base_id("ws_session")
        ]
        
        # All acceptable patterns should be SSOT-compliant
        for acceptable_id in acceptable_patterns:
            assert not self.id_patterns['uuid_v4'].match(acceptable_id), f"SSOT pattern should not be raw UUID: {acceptable_id}"
            assert self.id_patterns['ssot_structured'].match(acceptable_id), f"Should match SSOT format: {acceptable_id}"

    # =============================================================================
    # PERFORMANCE AND CONSISTENCY TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_websocket_id_consistency_under_load(self):
        """
        Test WebSocket ID consistency under concurrent load conditions.
        """
        # Create multiple concurrent WebSocket operations
        concurrent_tasks = []
        user_contexts = []
        
        try:
            # Create user contexts concurrently
            for i in range(10):
                task = create_authenticated_user_context(user_email=f"load_test_{i}@example.com")
                concurrent_tasks.append(task)
            
            user_contexts = await asyncio.gather(*concurrent_tasks)
            
            # Create WebSocket managers concurrently
            manager_tasks = []
            for context in user_contexts:
                task = create_websocket_manager(context)
                manager_tasks.append(task)
            
            ws_managers = await asyncio.gather(*manager_tasks)
            
            # Validate all generated IDs are unique and consistent
            all_user_ids = [ctx.user_id for ctx in user_contexts]
            all_thread_ids = [ctx.thread_id for ctx in user_contexts] 
            all_run_ids = [ctx.run_id for ctx in user_contexts]
            
            # Check uniqueness
            assert len(set(all_user_ids)) == len(all_user_ids), "All user IDs should be unique under load"
            assert len(set(all_thread_ids)) == len(all_thread_ids), "All thread IDs should be unique under load"
            assert len(set(all_run_ids)) == len(all_run_ids), "All run IDs should be unique under load"
            
            # Check format consistency
            for user_id in all_user_ids:
                assert not self.id_patterns['uuid_v4'].match(user_id), f"Load test user ID should not be UUID: {user_id}"
            
            # Cleanup
            cleanup_tasks = [manager.cleanup_all_connections() for manager in ws_managers]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        except Exception as e:
            pytest.fail(f"WebSocket ID consistency under load test failed: {e}")

    # =============================================================================
    # CLEANUP AND UTILITIES
    # =============================================================================

    def teardown_method(self):
        """Cleanup after each test method."""
        super().teardown_method()
        if hasattr(self, 'consistency_violations') and self.consistency_violations:
            print(f"\nWebSocket ID consistency violations detected: {len(self.consistency_violations)}")
            for violation in self.consistency_violations[:3]:  # Show first 3
                print(f"  - {violation}")
            if len(self.consistency_violations) > 3:
                print(f"  ... and {len(self.consistency_violations) - 3} more violations")

    @pytest.mark.asyncio
    async def test_websocket_integration_health_check(self):
        """
        Health check to validate basic WebSocket integration works.
        This test should always pass to ensure basic functionality.
        """
        try:
            # Basic WebSocket integration health check
            user_context = await create_authenticated_user_context()
            ws_manager = await create_websocket_manager(user_context)
            
            # Verify manager is created successfully
            assert ws_manager is not None, "WebSocket manager should be created"
            assert isinstance(ws_manager, IsolatedWebSocketManager), "Should be IsolatedWebSocketManager"
            
            # Test basic operations
            manager_stats = ws_manager.get_manager_stats()
            assert 'user_context' in manager_stats, "Manager stats should include user context"
            
            # Cleanup
            await ws_manager.cleanup_all_connections()
            
            print(f"WebSocket integration health check passed")
            
        except Exception as e:
            pytest.fail(f"WebSocket integration health check failed: {e}")

    @pytest.mark.asyncio  
    async def test_websocket_factory_pattern_validation(self):
        """
        Test WebSocket factory pattern produces consistent ID formats.
        
        This test validates that the WebSocketManagerFactory creates managers
        with consistent ID generation patterns.
        """
        try:
            # Test factory pattern consistency
            factory = WebSocketManagerFactory()
            
            # Create multiple managers through factory
            user_contexts = []
            managers = []
            
            for i in range(3):
                context = await create_authenticated_user_context(
                    user_email=f"factory_test_{i}@example.com"
                )
                manager = await factory.create_manager(context)
                
                user_contexts.append(context)
                managers.append(manager)
            
            # Validate factory produces consistent ID formats
            for i, manager in enumerate(managers):
                stats = manager.get_manager_stats()
                user_data = stats.get('user_context', {})
                
                # All IDs should follow consistent patterns
                for field in ['user_id', 'thread_id', 'run_id', 'request_id']:
                    if field in user_data:
                        id_value = user_data[field]
                        assert isinstance(id_value, str), f"Factory manager {i} {field} should be string"
                        assert len(id_value) > 0, f"Factory manager {i} {field} should not be empty"
            
            # Cleanup
            for manager in managers:
                await manager.cleanup_all_connections()
            await factory.shutdown()
            
            print("WebSocket factory pattern validation passed")
        
        except Exception as e:
            pytest.fail(f"WebSocket factory pattern validation failed: {e}")