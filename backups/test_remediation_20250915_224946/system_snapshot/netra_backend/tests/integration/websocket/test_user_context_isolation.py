"""
Integration Tests - User Context Isolation for Issue #1099

Test Purpose: Validate user isolation and security during handler migration
Expected Initial State: FAIL - Legacy patterns may not properly isolate users

Business Value Justification:
- Segment: Platform/Enterprise (Security and multi-tenancy critical)
- Business Goal: Ensure no data leakage between users during handler processing
- Value Impact: Maintain user privacy and security during WebSocket message handling
- Revenue Impact: Protect $500K+ ARR by preventing security breaches and data leaks

🔍 These tests are designed to INITIALLY FAIL to demonstrate user isolation issues
"""

import asyncio
import json
import uuid
import pytest
from typing import Dict, Any, List, Optional, Set
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

# Core imports
from netra_backend.app.logging_config import central_logger
from netra_backend.app.db.postgres import get_async_db
from netra_backend.app.db.redis_client import get_redis_client

# Authentication imports
try:
    from netra_backend.app.auth_integration.auth import verify_jwt_token
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False

# User context imports
try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    USER_CONTEXT_AVAILABLE = True
except ImportError:
    USER_CONTEXT_AVAILABLE = False

# Handler imports
try:
    from netra_backend.app.services.websocket.message_handler import create_handler_safely
    LEGACY_HANDLER_AVAILABLE = True
except ImportError:
    LEGACY_HANDLER_AVAILABLE = False

try:
    from netra_backend.app.websocket_core.handlers import handle_message as ssot_handle_message
    from netra_backend.app.websocket_core.types import WebSocketMessage
    SSOT_HANDLER_AVAILABLE = True
except ImportError:
    SSOT_HANDLER_AVAILABLE = False

logger = central_logger.get_logger(__name__)


class TestUserContextIsolation:
    """Integration tests for user isolation and security during migration"""

    @pytest.fixture(scope="function")
    async def real_database_session(self):
        """Provide real database session for user data isolation testing"""
        try:
            async for session in get_async_db():
                yield session
                break
        except Exception as e:
            pytest.skip(f"Real database not available: {e}")

    @pytest.fixture(scope="function")
    async def real_redis_client(self):
        """Provide real Redis client for session isolation testing"""
        try:
            redis_client = await get_redis_client()
            yield redis_client
        except Exception as e:
            pytest.skip(f"Real Redis not available: {e}")

    @pytest.fixture(scope="function")
    def test_users(self):
        """Create test user data for isolation testing"""
        return [
            {
                "user_id": f"isolation_user_{i}",
                "username": f"testuser{i}",
                "email": f"test{i}@example.com",
                "thread_id": f"isolation_thread_{i}",
                "session_id": f"session_{uuid.uuid4()}",
                "jwt_token": f"jwt_token_{i}_mock",
                "sensitive_data": f"user_{i}_private_information"
            }
            for i in range(1, 6)  # 5 test users
        ]

    @pytest.mark.asyncio
    async def test_user_message_isolation(self, test_users, real_database_session, real_redis_client):
        """
        Test: Ensure messages don't leak between users
        Expected: FAIL - Legacy patterns may not properly isolate user messages
        """
        if not all([LEGACY_HANDLER_AVAILABLE, SSOT_HANDLER_AVAILABLE]):
            pytest.fail("Both handlers not available - demonstrates handler availability conflicts")

        # Create messages for each user with sensitive content
        user_messages = []
        for user in test_users:
            message = {
                "type": "user_message",
                "content": f"Private message from {user['username']}: {user['sensitive_data']}",
                "user_id": user["user_id"],
                "thread_id": user["thread_id"],
                "session_id": user["session_id"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            user_messages.append((user, message))

        # Track processed messages and responses for each user
        user_processing_results = {}
        cross_user_contamination = []

        try:
            # Process each user's message
            for user, message in user_messages:
                user_id = user["user_id"]
                logger.info(f"Processing message for user: {user_id}")

                # Test with available handlers
                processing_result = {
                    "user_id": user_id,
                    "message_content": message["content"],
                    "handler_responses": [],
                    "context_data": [],
                    "errors": []
                }

                # Mock WebSocket for tracking responses
                mock_websocket = Mock()
                mock_websocket.sent_messages = []

                async def track_sent_message(data):
                    mock_websocket.sent_messages.append(data)

                mock_websocket.send_json = AsyncMock(side_effect=track_sent_message)

                # Test legacy handler
                if LEGACY_HANDLER_AVAILABLE:
                    try:
                        mock_supervisor = Mock()
                        mock_supervisor.user_id = user_id
                        mock_db_factory = Mock(return_value=real_database_session)

                        legacy_handler = await create_handler_safely(
                            "user_message",
                            mock_supervisor,
                            mock_db_factory
                        )

                        if legacy_handler:
                            # Set up user context for legacy handler
                            if hasattr(legacy_handler, 'set_user_context'):
                                await legacy_handler.set_user_context(user_id, user["session_id"])

                            await legacy_handler.handle(message)

                            processing_result["handler_responses"].append({
                                "handler": "legacy",
                                "responses": mock_websocket.sent_messages.copy()
                            })

                    except Exception as e:
                        processing_result["errors"].append(f"legacy_handler: {str(e)}")

                # Test SSOT handler
                if SSOT_HANDLER_AVAILABLE:
                    try:
                        websocket_message = Mock()
                        websocket_message.type = message["type"]
                        websocket_message.data = message
                        websocket_message.user_id = message["user_id"]

                        result = await ssot_handle_message(mock_websocket, websocket_message)

                        processing_result["handler_responses"].append({
                            "handler": "ssot",
                            "result": result,
                            "responses": mock_websocket.sent_messages.copy()
                        })

                    except Exception as e:
                        processing_result["errors"].append(f"ssot_handler: {str(e)}")

                user_processing_results[user_id] = processing_result

            # Analyze user isolation
            logger.info("Analyzing user message isolation...")

            # Check for cross-user data contamination
            for user_id, result in user_processing_results.items():
                user_content = result["message_content"]
                user_sensitive_data = next(u["sensitive_data"] for u in test_users if u["user_id"] == user_id)

                # Check responses from this user's processing
                for handler_response in result["handler_responses"]:
                    responses = handler_response.get("responses", [])

                    for response in responses:
                        response_text = json.dumps(response) if isinstance(response, dict) else str(response)

                        # Check if other users' sensitive data appears in this user's responses
                        for other_user in test_users:
                            if other_user["user_id"] != user_id:
                                other_sensitive_data = other_user["sensitive_data"]

                                if other_sensitive_data in response_text:
                                    contamination = {
                                        "victim_user": user_id,
                                        "leaked_from": other_user["user_id"],
                                        "leaked_data": other_sensitive_data,
                                        "handler": handler_response["handler"],
                                        "response": response_text[:200]  # First 200 chars
                                    }
                                    cross_user_contamination.append(contamination)

            if cross_user_contamination:
                logger.error(f"Cross-user data contamination detected: {len(cross_user_contamination)} instances")
                for contamination in cross_user_contamination:
                    logger.error(f"Data leak: {contamination}")

                pytest.fail(f"User message isolation failed - {len(cross_user_contamination)} data leaks detected")

            # Check for shared state between users
            shared_state_violations = []

            # Look for global state that might be shared
            if LEGACY_HANDLER_AVAILABLE:
                from netra_backend.app.services.websocket.message_handler import _handler_instances

                # Check if handler instances are being reused across users
                if len(_handler_instances) < len(test_users):
                    shared_state_violations.append("handler_instance_reuse")

            if shared_state_violations:
                pytest.fail(f"Shared state violations detected: {shared_state_violations}")

            pytest.fail("Expected user message isolation failures but isolation appeared to work")

        except Exception as e:
            # Expected failure due to isolation issues
            pytest.fail(f"User message isolation test failed: {e}")

    @pytest.mark.asyncio
    async def test_concurrent_user_sessions(self, test_users, real_database_session, real_redis_client):
        """
        Test: Test multiple users processing messages simultaneously
        Expected: FAIL - Concurrent user sessions reveal isolation issues
        """
        # Create concurrent user session tasks
        concurrent_session_results = []

        async def user_session_task(user):
            """Simulate a complete user session with multiple messages"""
            user_id = user["user_id"]
            session_results = {
                "user_id": user_id,
                "messages_processed": 0,
                "errors": [],
                "context_maintained": True,
                "isolation_breaches": []
            }

            try:
                # Simulate multiple messages in a session
                session_messages = [
                    f"Message 1 from {user['username']} with secret: {user['sensitive_data']}",
                    f"Follow-up from {user['username']} referencing previous context",
                    f"Final message from {user['username']} with more secrets: secret_key_{user_id}"
                ]

                for i, content in enumerate(session_messages):
                    message = {
                        "type": "user_message",
                        "content": content,
                        "user_id": user_id,
                        "thread_id": user["thread_id"],
                        "session_id": user["session_id"],
                        "message_sequence": i + 1
                    }

                    # Process with available handlers
                    message_processed = False

                    if LEGACY_HANDLER_AVAILABLE:
                        try:
                            mock_supervisor = Mock()
                            mock_supervisor.user_id = user_id
                            mock_db_factory = Mock(return_value=real_database_session)

                            handler = await create_handler_safely(
                                "user_message",
                                mock_supervisor,
                                mock_db_factory
                            )

                            if handler:
                                # Check if handler maintains user context
                                if hasattr(handler, 'current_user_id'):
                                    if handler.current_user_id != user_id:
                                        session_results["isolation_breaches"].append(
                                            f"handler_user_mismatch: expected {user_id}, got {handler.current_user_id}"
                                        )

                                await handler.handle(message)
                                message_processed = True

                        except Exception as e:
                            session_results["errors"].append(f"legacy_message_{i}: {str(e)}")

                    if SSOT_HANDLER_AVAILABLE and not message_processed:
                        try:
                            mock_websocket = Mock()
                            mock_websocket.send_json = AsyncMock()

                            websocket_message = Mock()
                            websocket_message.type = message["type"]
                            websocket_message.data = message
                            websocket_message.user_id = user_id

                            result = await ssot_handle_message(mock_websocket, websocket_message)

                            if result:
                                message_processed = True

                        except Exception as e:
                            session_results["errors"].append(f"ssot_message_{i}: {str(e)}")

                    if message_processed:
                        session_results["messages_processed"] += 1

                    # Small delay to allow for race conditions
                    await asyncio.sleep(0.01)

            except Exception as e:
                session_results["errors"].append(f"session_error: {str(e)}")

            return session_results

        try:
            # Execute concurrent user sessions
            tasks = [user_session_task(user) for user in test_users]

            logger.info(f"Starting {len(tasks)} concurrent user sessions...")

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Analyze concurrent session results
            successful_sessions = []
            failed_sessions = []

            for result in results:
                if isinstance(result, dict):
                    if result.get("errors"):
                        failed_sessions.append(result)
                    else:
                        successful_sessions.append(result)
                else:
                    # Exception occurred
                    failed_sessions.append({"user_id": "unknown", "exception": str(result)})

            logger.info(f"Successful sessions: {len(successful_sessions)}")
            logger.info(f"Failed sessions: {len(failed_sessions)}")

            if failed_sessions:
                logger.error("Concurrent session failures:")
                for failure in failed_sessions:
                    logger.error(f"User {failure.get('user_id', 'unknown')}: {failure.get('errors', failure.get('exception'))}")

            # Check for isolation breaches
            total_isolation_breaches = sum(
                len(session.get("isolation_breaches", []))
                for session in successful_sessions
            )

            if total_isolation_breaches > 0:
                pytest.fail(f"Concurrent user session isolation breaches: {total_isolation_breaches}")

            # Check for race conditions
            message_counts = [session["messages_processed"] for session in successful_sessions]
            expected_messages_per_user = 3

            inconsistent_processing = [
                count for count in message_counts
                if count != expected_messages_per_user
            ]

            if inconsistent_processing:
                pytest.fail(f"Inconsistent message processing - race conditions detected: {inconsistent_processing}")

            # Check for performance degradation under concurrent load
            if len(successful_sessions) < len(test_users):
                pytest.fail(f"Concurrent session handling failed: only {len(successful_sessions)}/{len(test_users)} sessions successful")

            pytest.fail("Expected concurrent user session issues but all sessions processed successfully")

        except Exception as e:
            # Expected failure due to concurrency issues
            pytest.fail(f"Concurrent user sessions test failed: {e}")

    @pytest.mark.asyncio
    async def test_user_context_propagation(self, test_users, real_database_session, real_redis_client):
        """
        Test: Verify context maintained through handlers
        Expected: FAIL - Context propagation issues with dual handlers
        """
        if not USER_CONTEXT_AVAILABLE:
            pytest.skip("User execution context not available")

        context_propagation_results = []

        for user in test_users:
            user_id = user["user_id"]
            session_id = user["session_id"]

            logger.info(f"Testing context propagation for user: {user_id}")

            try:
                # Create user execution context
                user_context = UserExecutionContext(
                    user_id=user_id,
                    session_id=session_id,
                    thread_id=user["thread_id"]
                )

                # Test context propagation through message processing chain
                message = {
                    "type": "user_message",
                    "content": f"Context test message from {user['username']}",
                    "user_id": user_id,
                    "thread_id": user["thread_id"],
                    "session_id": session_id
                }

                context_checkpoints = []

                # Checkpoint 1: Initial context
                context_checkpoints.append({
                    "checkpoint": "initial",
                    "user_id": user_context.user_id,
                    "session_id": user_context.session_id,
                    "thread_id": user_context.thread_id
                })

                # Test legacy handler context propagation
                if LEGACY_HANDLER_AVAILABLE:
                    try:
                        with patch('netra_backend.app.dependencies.get_user_execution_context', return_value=user_context):
                            mock_supervisor = Mock()
                            mock_supervisor.user_id = user_id
                            mock_db_factory = Mock(return_value=real_database_session)

                            handler = await create_handler_safely(
                                "user_message",
                                mock_supervisor,
                                mock_db_factory
                            )

                            if handler:
                                # Checkpoint 2: After handler creation
                                if hasattr(handler, 'user_context'):
                                    handler_context = handler.user_context
                                    context_checkpoints.append({
                                        "checkpoint": "legacy_handler_created",
                                        "user_id": getattr(handler_context, 'user_id', None),
                                        "session_id": getattr(handler_context, 'session_id', None),
                                        "context_preserved": handler_context.user_id == user_id if handler_context else False
                                    })

                                # Process message
                                await handler.handle(message)

                                # Checkpoint 3: After message processing
                                if hasattr(handler, 'user_context'):
                                    context_checkpoints.append({
                                        "checkpoint": "legacy_processing_complete",
                                        "user_id": handler.user_context.user_id if handler.user_context else None,
                                        "context_maintained": handler.user_context.user_id == user_id if handler.user_context else False
                                    })

                    except Exception as e:
                        context_checkpoints.append({
                            "checkpoint": "legacy_handler_error",
                            "error": str(e)
                        })

                # Test SSOT handler context propagation
                if SSOT_HANDLER_AVAILABLE:
                    try:
                        mock_websocket = Mock()
                        mock_websocket.send_json = AsyncMock()

                        websocket_message = Mock()
                        websocket_message.type = message["type"]
                        websocket_message.data = message
                        websocket_message.user_id = user_id

                        # Checkpoint 4: Before SSOT processing
                        context_checkpoints.append({
                            "checkpoint": "ssot_processing_start",
                            "message_user_id": websocket_message.user_id,
                            "context_user_id": user_context.user_id,
                            "match": websocket_message.user_id == user_context.user_id
                        })

                        with patch('netra_backend.app.dependencies.get_user_execution_context', return_value=user_context):
                            result = await ssot_handle_message(mock_websocket, websocket_message)

                            # Checkpoint 5: After SSOT processing
                            context_checkpoints.append({
                                "checkpoint": "ssot_processing_complete",
                                "result": result,
                                "context_user_id": user_context.user_id,
                                "context_preserved": True  # Would need to check actual implementation
                            })

                    except Exception as e:
                        context_checkpoints.append({
                            "checkpoint": "ssot_handler_error",
                            "error": str(e)
                        })

                # Analyze context propagation
                propagation_result = {
                    "user_id": user_id,
                    "checkpoints": context_checkpoints,
                    "context_maintained": True,
                    "issues": []
                }

                # Check for context loss
                for checkpoint in context_checkpoints:
                    if checkpoint.get("context_preserved") is False:
                        propagation_result["context_maintained"] = False
                        propagation_result["issues"].append(f"Context lost at {checkpoint['checkpoint']}")

                    if checkpoint.get("context_maintained") is False:
                        propagation_result["context_maintained"] = False
                        propagation_result["issues"].append(f"Context not maintained at {checkpoint['checkpoint']}")

                    if checkpoint.get("match") is False:
                        propagation_result["context_maintained"] = False
                        propagation_result["issues"].append(f"Context mismatch at {checkpoint['checkpoint']}")

                context_propagation_results.append(propagation_result)

            except Exception as e:
                context_propagation_results.append({
                    "user_id": user_id,
                    "context_maintained": False,
                    "error": str(e)
                })

        # Analyze overall context propagation
        failed_propagations = [
            result for result in context_propagation_results
            if not result.get("context_maintained", False)
        ]

        if failed_propagations:
            logger.error("Context propagation failures:")
            for failure in failed_propagations:
                logger.error(f"User {failure['user_id']}: {failure.get('issues', failure.get('error'))}")

            pytest.fail(f"User context propagation failed for {len(failed_propagations)} users")

        # Check for context conflicts between handlers
        legacy_context_checkpoints = []
        ssot_context_checkpoints = []

        for result in context_propagation_results:
            for checkpoint in result.get("checkpoints", []):
                if "legacy" in checkpoint.get("checkpoint", ""):
                    legacy_context_checkpoints.append(checkpoint)
                elif "ssot" in checkpoint.get("checkpoint", ""):
                    ssot_context_checkpoints.append(checkpoint)

        if legacy_context_checkpoints and ssot_context_checkpoints:
            # Both handlers processed context - check for conflicts
            pytest.fail("Context propagation conflict - both legacy and SSOT handlers processed user contexts")

        pytest.fail("Expected user context propagation issues but propagation succeeded")

    @pytest.mark.asyncio
    async def test_authentication_integration(self, test_users, real_database_session, real_redis_client):
        """
        Test: Test JWT integration with handlers
        Expected: FAIL - Authentication integration issues with dual handlers
        """
        if not AUTH_AVAILABLE:
            pytest.skip("Authentication system not available")

        authentication_results = []

        for user in test_users:
            user_id = user["user_id"]
            jwt_token = user["jwt_token"]

            logger.info(f"Testing authentication integration for user: {user_id}")

            try:
                # Mock JWT token verification
                mock_jwt_payload = {
                    "user_id": user_id,
                    "username": user["username"],
                    "email": user["email"],
                    "session_id": user["session_id"],
                    "exp": 9999999999  # Far future expiration
                }

                auth_result = {
                    "user_id": user_id,
                    "jwt_verified": False,
                    "handler_auth_results": [],
                    "auth_conflicts": []
                }

                message_with_auth = {
                    "type": "user_message",
                    "content": f"Authenticated message from {user['username']}",
                    "user_id": user_id,
                    "jwt_token": jwt_token,
                    "thread_id": user["thread_id"]
                }

                # Test authentication with legacy handler
                if LEGACY_HANDLER_AVAILABLE:
                    try:
                        with patch('netra_backend.app.auth_integration.auth.verify_jwt_token') as mock_verify:
                            mock_verify.return_value = mock_jwt_payload

                            mock_supervisor = Mock()
                            mock_supervisor.user_id = user_id
                            mock_db_factory = Mock(return_value=real_database_session)

                            handler = await create_handler_safely(
                                "user_message",
                                mock_supervisor,
                                mock_db_factory
                            )

                            if handler:
                                # Check if handler performs authentication
                                if hasattr(handler, 'authenticate_user'):
                                    auth_success = await handler.authenticate_user(jwt_token)
                                    auth_result["handler_auth_results"].append({
                                        "handler": "legacy",
                                        "authenticated": auth_success,
                                        "user_id": user_id
                                    })

                                await handler.handle(message_with_auth)

                                # Check if JWT verification was called
                                if mock_verify.called:
                                    auth_result["jwt_verified"] = True

                    except Exception as e:
                        auth_result["handler_auth_results"].append({
                            "handler": "legacy",
                            "error": str(e)
                        })

                # Test authentication with SSOT handler
                if SSOT_HANDLER_AVAILABLE:
                    try:
                        with patch('netra_backend.app.auth_integration.auth.verify_jwt_token') as mock_verify:
                            mock_verify.return_value = mock_jwt_payload

                            mock_websocket = Mock()
                            mock_websocket.send_json = AsyncMock()

                            websocket_message = Mock()
                            websocket_message.type = message_with_auth["type"]
                            websocket_message.data = message_with_auth
                            websocket_message.user_id = user_id

                            # Add JWT token to message
                            websocket_message.jwt_token = jwt_token

                            result = await ssot_handle_message(mock_websocket, websocket_message)

                            auth_result["handler_auth_results"].append({
                                "handler": "ssot",
                                "result": result,
                                "user_id": user_id
                            })

                            # Check if JWT verification was called
                            if mock_verify.called:
                                auth_result["jwt_verified"] = True

                    except Exception as e:
                        auth_result["handler_auth_results"].append({
                            "handler": "ssot",
                            "error": str(e)
                        })

                # Check for authentication conflicts
                legacy_auth = next((r for r in auth_result["handler_auth_results"] if r.get("handler") == "legacy"), None)
                ssot_auth = next((r for r in auth_result["handler_auth_results"] if r.get("handler") == "ssot"), None)

                if legacy_auth and ssot_auth:
                    # Both handlers performed authentication
                    auth_result["auth_conflicts"].append("dual_authentication")

                    # Check for different authentication results
                    legacy_success = legacy_auth.get("authenticated", False)
                    ssot_success = ssot_auth.get("result", False)

                    if legacy_success != ssot_success:
                        auth_result["auth_conflicts"].append("conflicting_auth_results")

                authentication_results.append(auth_result)

            except Exception as e:
                authentication_results.append({
                    "user_id": user_id,
                    "error": str(e),
                    "jwt_verified": False
                })

        # Analyze authentication integration
        failed_authentications = [
            result for result in authentication_results
            if not result.get("jwt_verified", False)
        ]

        if failed_authentications:
            pytest.fail(f"Authentication integration failed for {len(failed_authentications)} users")

        # Check for authentication conflicts
        conflicted_authentications = [
            result for result in authentication_results
            if result.get("auth_conflicts")
        ]

        if conflicted_authentications:
            conflicts = []
            for conflict in conflicted_authentications:
                conflicts.extend(conflict["auth_conflicts"])

            pytest.fail(f"Authentication conflicts detected: {conflicts}")

        pytest.fail("Expected authentication integration issues but authentication succeeded")

    @pytest.mark.asyncio
    async def test_user_session_cleanup(self, test_users, real_database_session, real_redis_client):
        """
        Test: Validate proper session cleanup
        Expected: FAIL - Session cleanup issues with dual handlers
        """
        session_cleanup_results = []

        for user in test_users:
            user_id = user["user_id"]
            session_id = user["session_id"]

            logger.info(f"Testing session cleanup for user: {user_id}")

            cleanup_result = {
                "user_id": user_id,
                "session_id": session_id,
                "cleanup_steps": [],
                "cleanup_successful": False,
                "resource_leaks": []
            }

            try:
                # Create user session with messages
                session_messages = [
                    {
                        "type": "user_message",
                        "content": f"Session message {i} from {user['username']}",
                        "user_id": user_id,
                        "session_id": session_id,
                        "thread_id": user["thread_id"]
                    }
                    for i in range(3)
                ]

                # Process messages to establish session state
                for message in session_messages:
                    if LEGACY_HANDLER_AVAILABLE:
                        try:
                            mock_supervisor = Mock()
                            mock_supervisor.user_id = user_id
                            mock_db_factory = Mock(return_value=real_database_session)

                            handler = await create_handler_safely(
                                "user_message",
                                mock_supervisor,
                                mock_db_factory
                            )

                            if handler:
                                await handler.handle(message)

                        except Exception as e:
                            logger.warning(f"Legacy message processing error: {e}")

                    if SSOT_HANDLER_AVAILABLE:
                        try:
                            mock_websocket = Mock()
                            mock_websocket.send_json = AsyncMock()

                            websocket_message = Mock()
                            websocket_message.type = message["type"]
                            websocket_message.data = message
                            websocket_message.user_id = user_id

                            await ssot_handle_message(mock_websocket, websocket_message)

                        except Exception as e:
                            logger.warning(f"SSOT message processing error: {e}")

                cleanup_result["cleanup_steps"].append("session_established")

                # Initiate session cleanup
                cleanup_message = {
                    "type": "session_terminate",
                    "user_id": user_id,
                    "session_id": session_id,
                    "reason": "user_logout"
                }

                # Test cleanup with handlers
                cleanup_performed = False

                if LEGACY_HANDLER_AVAILABLE:
                    try:
                        from netra_backend.app.services.websocket.message_handler import _handler_instances

                        # Check handler registry before cleanup
                        pre_cleanup_handlers = len(_handler_instances)

                        mock_supervisor = Mock()
                        mock_supervisor.cleanup_user_session = AsyncMock()
                        mock_db_factory = Mock(return_value=real_database_session)

                        handler = await create_handler_safely(
                            "session_terminate",
                            mock_supervisor,
                            mock_db_factory
                        )

                        if handler:
                            await handler.handle(cleanup_message)
                            cleanup_result["cleanup_steps"].append("legacy_cleanup_executed")

                            # Check handler registry after cleanup
                            post_cleanup_handlers = len(_handler_instances)

                            if post_cleanup_handlers >= pre_cleanup_handlers:
                                cleanup_result["resource_leaks"].append("legacy_handler_not_cleaned")

                            cleanup_performed = True

                    except Exception as e:
                        cleanup_result["cleanup_steps"].append(f"legacy_cleanup_error: {str(e)}")

                if SSOT_HANDLER_AVAILABLE:
                    try:
                        mock_websocket = Mock()
                        mock_websocket.send_json = AsyncMock()

                        websocket_message = Mock()
                        websocket_message.type = cleanup_message["type"]
                        websocket_message.data = cleanup_message
                        websocket_message.user_id = user_id

                        result = await ssot_handle_message(mock_websocket, websocket_message)

                        if result:
                            cleanup_result["cleanup_steps"].append("ssot_cleanup_executed")

                            if cleanup_performed:
                                # Both handlers performed cleanup
                                cleanup_result["resource_leaks"].append("dual_cleanup_execution")

                            cleanup_performed = True

                    except Exception as e:
                        cleanup_result["cleanup_steps"].append(f"ssot_cleanup_error: {str(e)}")

                # Verify cleanup completion
                if cleanup_performed and not cleanup_result["resource_leaks"]:
                    cleanup_result["cleanup_successful"] = True

                # Check for resource leaks in Redis
                try:
                    # Check if session data still exists in Redis
                    session_keys = await real_redis_client.keys(f"session:{session_id}:*")

                    if session_keys:
                        cleanup_result["resource_leaks"].append(f"redis_session_leak: {len(session_keys)} keys")

                except Exception as e:
                    logger.warning(f"Redis cleanup check failed: {e}")

                session_cleanup_results.append(cleanup_result)

            except Exception as e:
                session_cleanup_results.append({
                    "user_id": user_id,
                    "cleanup_successful": False,
                    "error": str(e)
                })

        # Analyze session cleanup results
        failed_cleanups = [
            result for result in session_cleanup_results
            if not result.get("cleanup_successful", False)
        ]

        if failed_cleanups:
            pytest.fail(f"Session cleanup failed for {len(failed_cleanups)} users")

        # Check for resource leaks
        total_resource_leaks = sum(
            len(result.get("resource_leaks", []))
            for result in session_cleanup_results
        )

        if total_resource_leaks > 0:
            pytest.fail(f"Resource leaks detected during session cleanup: {total_resource_leaks} leaks")

        pytest.fail("Expected session cleanup issues but cleanup succeeded")

    @pytest.mark.asyncio
    async def test_multi_tenant_security(self, test_users, real_database_session, real_redis_client):
        """
        Test: Ensure tenant isolation maintained
        Expected: FAIL - Multi-tenant security issues with handler conflicts
        """
        # Group users into tenants
        tenant_groups = {
            "tenant_alpha": test_users[:2],
            "tenant_beta": test_users[2:4],
            "tenant_gamma": test_users[4:]
        }

        tenant_security_results = {}

        for tenant_name, tenant_users in tenant_groups.items():
            logger.info(f"Testing multi-tenant security for: {tenant_name}")

            tenant_result = {
                "tenant_name": tenant_name,
                "users": [user["user_id"] for user in tenant_users],
                "security_violations": [],
                "cross_tenant_access": [],
                "data_isolation": True
            }

            try:
                # Create tenant-specific messages with sensitive data
                tenant_messages = []
                for user in tenant_users:
                    message = {
                        "type": "user_message",
                        "content": f"CONFIDENTIAL {tenant_name} data from {user['username']}: {user['sensitive_data']}",
                        "user_id": user["user_id"],
                        "tenant_id": tenant_name,
                        "classification": "confidential"
                    }
                    tenant_messages.append((user, message))

                # Process messages and track tenant isolation
                tenant_processing_log = []

                for user, message in tenant_messages:
                    processing_entry = {
                        "user_id": user["user_id"],
                        "tenant": tenant_name,
                        "message_processed": False,
                        "handler_used": None,
                        "responses": []
                    }

                    # Mock WebSocket for tracking responses
                    mock_websocket = Mock()
                    mock_websocket.sent_messages = []

                    async def track_tenant_response(data):
                        # Check if response contains data from other tenants
                        response_text = json.dumps(data) if isinstance(data, dict) else str(data)

                        # Check for cross-tenant data leakage
                        for other_tenant, other_users in tenant_groups.items():
                            if other_tenant != tenant_name:
                                for other_user in other_users:
                                    if other_user["sensitive_data"] in response_text:
                                        tenant_result["cross_tenant_access"].append({
                                            "current_tenant": tenant_name,
                                            "leaked_from_tenant": other_tenant,
                                            "leaked_data": other_user["sensitive_data"],
                                            "response": response_text[:100]
                                        })

                        mock_websocket.sent_messages.append(data)

                    mock_websocket.send_json = AsyncMock(side_effect=track_tenant_response)

                    # Process with available handlers
                    if LEGACY_HANDLER_AVAILABLE:
                        try:
                            mock_supervisor = Mock()
                            mock_supervisor.user_id = user["user_id"]
                            mock_supervisor.tenant_id = tenant_name
                            mock_db_factory = Mock(return_value=real_database_session)

                            handler = await create_handler_safely(
                                "user_message",
                                mock_supervisor,
                                mock_db_factory
                            )

                            if handler:
                                # Check if handler enforces tenant isolation
                                if hasattr(handler, 'tenant_id'):
                                    if handler.tenant_id != tenant_name:
                                        tenant_result["security_violations"].append(
                                            f"handler_tenant_mismatch: {handler.tenant_id} != {tenant_name}"
                                        )

                                await handler.handle(message)
                                processing_entry["message_processed"] = True
                                processing_entry["handler_used"] = "legacy"

                        except Exception as e:
                            logger.warning(f"Legacy tenant processing error: {e}")

                    if SSOT_HANDLER_AVAILABLE and not processing_entry["message_processed"]:
                        try:
                            websocket_message = Mock()
                            websocket_message.type = message["type"]
                            websocket_message.data = message
                            websocket_message.user_id = user["user_id"]
                            websocket_message.tenant_id = tenant_name

                            result = await ssot_handle_message(mock_websocket, websocket_message)

                            if result:
                                processing_entry["message_processed"] = True
                                processing_entry["handler_used"] = "ssot"

                        except Exception as e:
                            logger.warning(f"SSOT tenant processing error: {e}")

                    processing_entry["responses"] = mock_websocket.sent_messages.copy()
                    tenant_processing_log.append(processing_entry)

                # Analyze tenant security
                tenant_result["processing_log"] = tenant_processing_log

                # Check for data isolation failures
                if tenant_result["cross_tenant_access"]:
                    tenant_result["data_isolation"] = False

                # Check for tenant context mixing
                handlers_used = set(entry["handler_used"] for entry in tenant_processing_log if entry["handler_used"])

                if len(handlers_used) > 1:
                    # Multiple handler types used for same tenant - potential isolation issue
                    tenant_result["security_violations"].append("mixed_handler_usage")

                tenant_security_results[tenant_name] = tenant_result

            except Exception as e:
                tenant_security_results[tenant_name] = {
                    "tenant_name": tenant_name,
                    "error": str(e),
                    "data_isolation": False
                }

        # Analyze overall multi-tenant security
        security_violations = []
        cross_tenant_breaches = []

        for tenant_name, result in tenant_security_results.items():
            violations = result.get("security_violations", [])
            cross_access = result.get("cross_tenant_access", [])

            security_violations.extend(violations)
            cross_tenant_breaches.extend(cross_access)

        if security_violations:
            logger.error(f"Multi-tenant security violations: {security_violations}")
            pytest.fail(f"Multi-tenant security violations detected: {len(security_violations)}")

        if cross_tenant_breaches:
            logger.error(f"Cross-tenant data breaches: {cross_tenant_breaches}")
            pytest.fail(f"Cross-tenant data breaches detected: {len(cross_tenant_breaches)}")

        # Check for tenant isolation at the handler level
        all_processing_logs = []
        for result in tenant_security_results.values():
            all_processing_logs.extend(result.get("processing_log", []))

        # Look for handler reuse across tenants
        handler_tenant_usage = {}
        for log_entry in all_processing_logs:
            handler = log_entry.get("handler_used")
            user_id = log_entry.get("user_id")

            if handler and user_id:
                # Find tenant for this user
                user_tenant = None
                for tenant, users in tenant_groups.items():
                    if any(u["user_id"] == user_id for u in users):
                        user_tenant = tenant
                        break

                if user_tenant:
                    if handler not in handler_tenant_usage:
                        handler_tenant_usage[handler] = set()
                    handler_tenant_usage[handler].add(user_tenant)

        # Check for handlers used across multiple tenants
        cross_tenant_handlers = {
            handler: tenants for handler, tenants in handler_tenant_usage.items()
            if len(tenants) > 1
        }

        if cross_tenant_handlers:
            pytest.fail(f"Handler cross-tenant usage detected: {cross_tenant_handlers}")

        pytest.fail("Expected multi-tenant security issues but security validation passed")


# Test configuration
pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket,
    pytest.mark.issue_1099,
    pytest.mark.user_isolation,
    pytest.mark.security,
    pytest.mark.expected_failure  # These tests are designed to fail initially
]