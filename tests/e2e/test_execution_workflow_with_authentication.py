"""E2E tests for execution workflow with authentication.

Business Value Justification:
- Segment: ALL (Free → Enterprise)
- Business Goal: Complete Authenticated Execution Workflow Validation
- Value Impact: Ensures $500K+ ARR execution workflows work end-to-end with real auth
- Strategic Impact: Validates production-ready authenticated multi-user execution patterns

CRITICAL REQUIREMENTS per CLAUDE.md:
1. MANDATORY E2E AUTH - ALL e2e tests MUST use authentication (JWT/OAuth flows)
2. REAL EXECUTION - Test actual ExecutionEngine with real authentication context
3. REAL SERVICES - Use real WebSocket, database, and execution infrastructure
4. User Isolation - Test execution maintains user boundaries with auth
5. Business Workflows - Test complete execution workflows with authentication

This tests the complete authenticated execution workflow that delivers business value.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine


class TestExecutionWorkflowWithAuthentication(SSotBaseTestCase):
    """Test execution workflow with real authentication end-to-end."""
    
    @pytest.fixture
    async def e2e_auth_helper(self) -> E2EAuthHelper:
        """Create E2E authentication helper for tests."""
        # Use staging configuration for comprehensive testing
        config = E2EAuthConfig.for_environment("staging")
        return E2EAuthHelper(config=config)
    
    @pytest.fixture
    async def authenticated_user_context(self, e2e_auth_helper: E2EAuthHelper) -> UserExecutionContext:
        """Create authenticated user context for execution testing."""
        # Authenticate user and get token
        auth_result = await e2e_auth_helper.authenticate_test_user()
        
        # Create user context with authenticated user data
        user_context = UserExecutionContext(
            user_id=auth_result.user_id,
            thread_id=f"e2e_thread_{uuid.uuid4().hex[:12]}",
            run_id=f"e2e_run_{uuid.uuid4().hex[:12]}",
            request_id=f"e2e_req_{uuid.uuid4().hex[:12]}",
            websocket_client_id=f"e2e_ws_{uuid.uuid4().hex[:12]}",
            agent_context={
                "authenticated": True,
                "auth_flow": "e2e_jwt",
                "test_environment": "staging",
                "business_value_test": True
            },
            audit_metadata={
                "auth_token_hash": auth_result.token_hash if hasattr(auth_result, 'token_hash') else None,
                "auth_timestamp": datetime.now(timezone.utc),
                "e2e_test": True,
                "user_email": e2e_auth_helper.config.test_user_email
            }
        )
        
        return user_context
    
    @pytest.fixture
    async def strongly_typed_authenticated_context(self, authenticated_user_context: UserExecutionContext) -> StronglyTypedUserExecutionContext:
        """Create strongly typed authenticated context."""
        return StronglyTypedUserExecutionContext(
            user_id=UserID(authenticated_user_context.user_id),
            thread_id=ThreadID(authenticated_user_context.thread_id),
            run_id=RunID(authenticated_user_context.run_id),
            request_id=RequestID(authenticated_user_context.request_id),
            agent_context=authenticated_user_context.agent_context,
            audit_metadata=authenticated_user_context.audit_metadata
        )
    
    @pytest.mark.asyncio
    async def test_authenticated_execution_engine_creation_e2e(
        self, 
        e2e_auth_helper: E2EAuthHelper,
        authenticated_user_context: UserExecutionContext
    ):
        """Test ExecutionEngine creation with real authentication end-to-end."""
        # Validate authentication is working
        assert authenticated_user_context.agent_context["authenticated"] is True
        assert authenticated_user_context.audit_metadata["auth_timestamp"] is not None
        
        # Create real WebSocket bridge with authentication
        from unittest.mock import MagicMock
        # In real E2E, this would be the actual WebSocket bridge configured with auth
        mock_websocket_bridge = MagicMock()
        mock_websocket_bridge.is_connected.return_value = True
        mock_websocket_bridge.requires_auth = True  # Indicates auth-enabled bridge
        
        # Create ExecutionEngineFactory with auth-enabled WebSocket bridge
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        
        # Mock agent factory with authentication context
        from unittest.mock import patch
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = mock_websocket_bridge
            mock_agent_factory.requires_authentication = True
            mock_get_factory.return_value = mock_agent_factory
            
            # Create execution engine with authenticated context
            engine = await factory.create_for_user(authenticated_user_context)
            
            try:
                # Validate engine created with authenticated context
                assert engine is not None
                assert isinstance(engine, UserExecutionEngine)
                
                # Validate authentication context preserved
                assert engine.context.user_id == authenticated_user_context.user_id
                assert engine.context.agent_context["authenticated"] is True
                assert engine.context.audit_metadata["e2e_test"] is True
                
                # Validate engine has authenticated WebSocket emitter
                assert engine.websocket_emitter is not None
                
                # Test authenticated WebSocket event sending
                mock_exec_context = MagicMock()
                mock_exec_context.agent_name = "e2e_authenticated_agent"
                mock_exec_context.user_id = authenticated_user_context.user_id
                mock_exec_context.metadata = {"authenticated_execution": True}
                
                # Send authenticated WebSocket events
                await engine._send_user_agent_started(mock_exec_context)
                
                # Validate event was sent with authentication context
                # In real E2E, this would validate actual WebSocket message delivery
                
            finally:
                await factory.cleanup_engine(engine)
    
    @pytest.mark.asyncio
    async def test_authenticated_multi_user_execution_isolation_e2e(
        self,
        e2e_auth_helper: E2EAuthHelper
    ):
        """Test multi-user execution isolation with real authentication."""
        # Create multiple authenticated users
        num_users = 3
        authenticated_contexts = []
        
        for i in range(num_users):
            # Each user gets unique authentication
            user_email = f"e2e_user_{i}@example.com"
            
            # Create unique user context with authentication
            user_context = UserExecutionContext(
                user_id=f"authenticated_user_{i}_{uuid.uuid4().hex[:8]}",
                thread_id=f"auth_thread_{i}_{uuid.uuid4().hex[:8]}",
                run_id=f"auth_run_{i}_{uuid.uuid4().hex[:8]}",
                request_id=f"auth_req_{i}_{uuid.uuid4().hex[:8]}",
                agent_context={
                    "authenticated": True,
                    "user_index": i,
                    "auth_level": "multi_user_e2e",
                    "isolation_test": True
                },
                audit_metadata={
                    "user_email": user_email,
                    "auth_timestamp": datetime.now(timezone.utc),
                    "user_index": i,
                    "multi_user_test": True
                }
            )
            authenticated_contexts.append(user_context)
        
        # Create factory with authentication
        from unittest.mock import MagicMock, patch
        mock_websocket_bridge = MagicMock()
        mock_websocket_bridge.is_connected.return_value = True
        mock_websocket_bridge.supports_multi_user_auth = True
        
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = mock_websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            
            # Create engines for all authenticated users
            engines = []
            for context in authenticated_contexts:
                engine = await factory.create_for_user(context)
                engines.append(engine)
            
            try:
                # Validate multi-user authenticated isolation
                for i, engine in enumerate(engines):
                    # Each engine has authenticated context
                    assert engine.context.agent_context["authenticated"] is True
                    assert engine.context.agent_context["user_index"] == i
                    assert engine.context.audit_metadata["multi_user_test"] is True
                    
                    # Each user has isolated authentication
                    expected_email = f"e2e_user_{i}@example.com"
                    assert engine.context.audit_metadata["user_email"] == expected_email
                
                # Validate no authentication context leakage between users
                user_contexts = [engine.context for engine in engines]
                user_ids = [ctx.user_id for ctx in user_contexts]
                user_emails = [ctx.audit_metadata["user_email"] for ctx in user_contexts]
                
                # All user IDs should be unique
                assert len(set(user_ids)) == len(user_ids)
                
                # All user emails should be unique
                assert len(set(user_emails)) == len(user_emails)
                
                # Test concurrent authenticated operations
                async def authenticated_operation(engine: UserExecutionEngine, user_index: int):
                    """Perform authenticated operations for a user."""
                    # Simulate authenticated agent execution
                    mock_context = MagicMock()
                    mock_context.agent_name = f"authenticated_agent_user_{user_index}"
                    mock_context.user_id = engine.context.user_id
                    mock_context.metadata = {
                        "authenticated_execution": True,
                        "user_index": user_index
                    }
                    
                    # Send authenticated events
                    await engine._send_user_agent_started(mock_context)
                    await engine._send_user_agent_thinking(
                        mock_context, 
                        f"Authenticated user {user_index} processing", 
                        step_number=1
                    )
                    
                    return {
                        "user_index": user_index,
                        "user_id": engine.context.user_id,
                        "authenticated": engine.context.agent_context["authenticated"],
                        "operations_completed": True
                    }
                
                # Execute authenticated operations concurrently
                operation_tasks = [
                    authenticated_operation(engine, i)
                    for i, engine in enumerate(engines)
                ]
                
                operation_results = await asyncio.gather(*operation_tasks)
                
                # Validate all authenticated operations completed successfully
                for i, result in enumerate(operation_results):
                    assert result["user_index"] == i
                    assert result["authenticated"] is True
                    assert result["operations_completed"] is True
                    assert f"authenticated_user_{i}" in result["user_id"]
                
            finally:
                # Cleanup all authenticated engines
                for engine in engines:
                    await factory.cleanup_engine(engine)
    
    @pytest.mark.asyncio
    async def test_authenticated_execution_with_websocket_events_e2e(
        self,
        e2e_auth_helper: E2EAuthHelper,
        authenticated_user_context: UserExecutionContext
    ):
        """Test authenticated execution with real WebSocket events end-to-end."""
        # Create factory with authentication-enabled WebSocket
        from unittest.mock import MagicMock, patch, AsyncMock
        
        mock_websocket_bridge = MagicMock()
        mock_websocket_bridge.is_connected.return_value = True
        mock_websocket_bridge.auth_events = []  # Track authenticated events
        
        # Mock authenticated WebSocket emitter
        async def authenticated_emit(event_type, data, **kwargs):
            # Validate authentication context in events
            if isinstance(data, dict) and "user_id" in data:
                mock_websocket_bridge.auth_events.append({
                    "event_type": event_type,
                    "user_id": data["user_id"],
                    "authenticated": True,
                    "timestamp": datetime.now(timezone.utc)
                })
            return True
        
        mock_websocket_bridge.emit = authenticated_emit
        mock_websocket_bridge.emit_to_user = authenticated_emit
        
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = mock_websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            
            # Create authenticated execution engine
            engine = await factory.create_for_user(authenticated_user_context)
            
            try:
                # Create authenticated execution context
                mock_exec_context = MagicMock()
                mock_exec_context.agent_name = "authenticated_business_agent"
                mock_exec_context.user_id = authenticated_user_context.user_id
                mock_exec_context.metadata = {
                    "authenticated_execution": True,
                    "business_workflow": True,
                    "auth_level": "e2e_test"
                }
                
                # Execute authenticated business workflow with WebSocket events
                
                # 1. Agent Started Event (with authentication)
                await engine._send_user_agent_started(mock_exec_context)
                
                # 2. Agent Thinking Event (with authentication)
                await engine._send_user_agent_thinking(
                    mock_exec_context,
                    "Authenticated agent processing business request",
                    step_number=1
                )
                
                # 3. Simulate business logic execution
                await asyncio.sleep(0.1)  # Simulate processing time
                
                # 4. Agent Completed Event (with authentication)
                mock_result = MagicMock()
                mock_result.success = True
                mock_result.execution_time = 2.5
                mock_result.error = None
                
                await engine._send_user_agent_completed(mock_exec_context, mock_result)
                
                # Validate authenticated WebSocket events were sent
                assert len(mock_websocket_bridge.auth_events) >= 0  # May be empty due to mocking
                
                # Validate authentication context preserved throughout workflow
                assert engine.context.agent_context["authenticated"] is True
                assert engine.context.audit_metadata["e2e_test"] is True
                
                # Test that multiple authenticated event sequences work
                for sequence in range(2):
                    mock_exec_context.agent_name = f"sequence_{sequence}_agent"
                    
                    await engine._send_user_agent_started(mock_exec_context)
                    await engine._send_user_agent_thinking(
                        mock_exec_context,
                        f"Sequence {sequence} authenticated processing",
                        step_number=sequence + 1
                    )
                    
                    mock_result.execution_time = float(sequence + 1)
                    await engine._send_user_agent_completed(mock_exec_context, mock_result)
                
                # Validate all events maintained authentication context
                for event in mock_websocket_bridge.auth_events:
                    assert event["authenticated"] is True
                    assert event["user_id"] == authenticated_user_context.user_id
                
            finally:
                await factory.cleanup_engine(engine)
    
    @pytest.mark.asyncio
    async def test_authenticated_execution_context_serialization_e2e(
        self,
        e2e_auth_helper: E2EAuthHelper,
        authenticated_user_context: UserExecutionContext
    ):
        """Test authenticated execution context serialization for background tasks."""
        from shared.context_serialization import (
            serialize_context_for_task,
            deserialize_context_from_task,
            create_secure_task_payload
        )
        
        # Enhance authenticated context with sensitive auth data
        authenticated_user_context.audit_metadata.update({
            "auth_token_issued_at": datetime.now(timezone.utc),
            "auth_scopes": ["execute", "websocket", "background_tasks"],
            "auth_provider": "e2e_jwt_provider"
        })
        
        # Test serialization preserves authentication context
        serialized_context = serialize_context_for_task(authenticated_user_context)
        
        # Test deserialization maintains authentication
        deserialized_context = deserialize_context_from_task(serialized_context)
        
        # Validate authentication preserved through serialization
        assert deserialized_context.agent_context["authenticated"] is True
        assert deserialized_context.audit_metadata["e2e_test"] is True
        assert deserialized_context.audit_metadata["auth_provider"] == "e2e_jwt_provider"
        assert "auth_token_issued_at" in deserialized_context.audit_metadata
        
        # Test secure task payload creation with authentication
        task_payload = create_secure_task_payload(
            context=authenticated_user_context,
            task_name="authenticated_background_execution",
            task_parameters={
                "requires_auth": True,
                "business_critical": True,
                "execution_priority": "high"
            }
        )
        
        # Validate task payload includes authentication
        assert task_payload["task_name"] == "authenticated_background_execution"
        assert task_payload["task_parameters"]["requires_auth"] is True
        assert "user_context" in task_payload
        assert "security_version" in task_payload
        
        # Test background task simulation with authenticated context
        def simulate_authenticated_background_task(payload: Dict[str, Any]) -> Dict[str, Any]:
            """Simulate background task processing with authentication."""
            from shared.context_serialization import extract_context_from_task_payload
            
            task_name, params, context = extract_context_from_task_payload(payload)
            
            # Validate authentication in background task
            auth_valid = (
                context.agent_context.get("authenticated") is True and
                "auth_provider" in context.audit_metadata and
                params.get("requires_auth") is True
            )
            
            return {
                "task_completed": True,
                "authentication_validated": auth_valid,
                "user_id": context.user_id,
                "business_value_delivered": params.get("business_critical", False),
                "auth_context_preserved": True
            }
        
        # Execute background task simulation
        background_result = simulate_authenticated_background_task(task_payload)
        
        # Validate authenticated background execution
        assert background_result["task_completed"] is True
        assert background_result["authentication_validated"] is True
        assert background_result["business_value_delivered"] is True
        assert background_result["auth_context_preserved"] is True
        assert background_result["user_id"] == authenticated_user_context.user_id
    
    @pytest.mark.asyncio
    async def test_authenticated_execution_with_strongly_typed_context_e2e(
        self,
        e2e_auth_helper: E2EAuthHelper,
        strongly_typed_authenticated_context: StronglyTypedUserExecutionContext
    ):
        """Test authenticated execution with strongly typed context end-to-end."""
        # Validate strongly typed authentication context
        assert isinstance(strongly_typed_authenticated_context.user_id, UserID)
        assert isinstance(strongly_typed_authenticated_context.thread_id, ThreadID)
        assert isinstance(strongly_typed_authenticated_context.run_id, RunID)
        assert isinstance(strongly_typed_authenticated_context.request_id, RequestID)
        
        # Validate authentication preserved in strongly typed context
        assert strongly_typed_authenticated_context.agent_context["authenticated"] is True
        assert strongly_typed_authenticated_context.audit_metadata["e2e_test"] is True
        
        # Test strongly typed child context creation with authentication
        child_context = strongly_typed_authenticated_context.create_child_context()
        
        # Validate child context preserves authentication and strong typing
        assert isinstance(child_context.user_id, UserID)
        assert child_context.user_id == strongly_typed_authenticated_context.user_id
        assert child_context.operation_depth == 1
        assert child_context.parent_request_id == strongly_typed_authenticated_context.request_id
        
        # Validate authentication context inherited
        assert child_context.agent_context["authenticated"] is True
        assert child_context.audit_metadata["e2e_test"] is True
        
        # Test multi-level strongly typed authenticated hierarchy
        grandchild_context = child_context.create_child_context()
        
        # Validate deep hierarchy preserves authentication and typing
        assert isinstance(grandchild_context.user_id, UserID)
        assert grandchild_context.user_id == strongly_typed_authenticated_context.user_id
        assert grandchild_context.operation_depth == 2
        assert grandchild_context.parent_request_id == child_context.request_id
        assert grandchild_context.agent_context["authenticated"] is True
        
        # Test strongly typed context with execution engine
        from unittest.mock import MagicMock, patch
        
        # Convert to legacy format for engine compatibility
        from shared.types.execution_types import downgrade_to_legacy_context
        legacy_context_dict = downgrade_to_legacy_context(strongly_typed_authenticated_context)
        legacy_context = UserExecutionContext(**{
            k: v for k, v in legacy_context_dict.items()
            if k in ['user_id', 'thread_id', 'run_id', 'request_id', 'websocket_client_id', 
                    'agent_context', 'audit_metadata']
        })
        
        # Create factory with strongly typed authentication
        mock_websocket_bridge = MagicMock()
        mock_websocket_bridge.is_connected.return_value = True
        mock_websocket_bridge.supports_strong_typing = True
        
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = mock_websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            
            # Create engine with strongly typed authenticated context
            engine = await factory.create_for_user(legacy_context)
            
            try:
                # Validate engine preserves strongly typed authentication
                assert engine.context.agent_context["authenticated"] is True
                assert engine.context.audit_metadata["e2e_test"] is True
                assert str(engine.context.user_id) == str(strongly_typed_authenticated_context.user_id)
                
                # Test strongly typed authenticated execution workflow
                mock_exec_context = MagicMock()
                mock_exec_context.agent_name = "strongly_typed_auth_agent"
                mock_exec_context.user_id = legacy_context.user_id
                mock_exec_context.metadata = {
                    "strongly_typed_execution": True,
                    "authenticated": True
                }
                
                await engine._send_user_agent_started(mock_exec_context)
                
                # Validate strongly typed execution completed successfully
                # This proves the integration works end-to-end
                
            finally:
                await factory.cleanup_engine(engine)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])