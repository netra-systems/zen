class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks.

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        ""Send JSON message.
        if self._closed:
        raise RuntimeError(WebSocket is closed)"
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = Normal closure"):
        Close WebSocket connection.""
        pass
        self._closed = True
        self.is_connected = False

    async def get_messages(self) -> list:
        Get all sent messages."
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        "Proof that the threads fix actually works - simplified test without full DB.

        import pytest
        import asyncio
        from sqlalchemy.ext.asyncio import AsyncSession
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from shared.isolated_environment import IsolatedEnvironment

        from netra_backend.app.services.database.thread_repository import ThreadRepository
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


class TestProofOfFix:
        ""Proof that our fix actually works in production scenarios.

@pytest.mark.asyncio
    async def test_actual_code_with_jsonb_failure(self):
    Prove the actual ThreadRepository code handles JSONB failures.""

        # Create real ThreadRepository instance
thread_repo = ThreadRepository()

        # Create mock database session
mock_db = AsyncMock(spec=AsyncSession)

        # Simulate JSONB query failure (what happens in staging)
jsonb_error = Exception(operator does not exist: jsonb ->> unknown)

        # First execute raises JSONB error
        # Second execute returns all threads for fallback
mock_result = MagicMock(); mock_scalars = Magic
        # Create test threads with various metadata states
thread1 = MagicMock(id="thread_1, metadata_={user_id": user123}
thread2 = MagicMock(id=thread_2, metadata_=None)  # NULL metadata"
thread3 = MagicMock(id="thread_3, metadata_={}  # Empty metadata
thread4 = MagicMock(id=thread_4, metadata_={user_id: user456"}"

mock_scalars.all.return_value = [thread1, thread2, thread3, thread4]
mock_result.scalars.return_value = mock_scalars

        # Set up mock to fail first, succeed second
mock_db.execute.side_effect = [jsonb_error, mock_result]

        # Execute the actual code
with patch('netra_backend.app.services.database.thread_repository.logger') as mock_logger:
    result = await thread_repo.find_by_user(mock_db, user123)

            # PROOF POINTS:

                # 1. The function didn't crash despite JSONB error
assert result is not None

                # 2. It returned the correct thread
assert len(result) == 1
assert result[0].id == thread_1"

                # 3. It logged the primary failure
mock_logger.error.assert_called()
error_calls = mock_logger.error.call_args_list
assert "Primary JSONB query failed in str(error_calls[0]

                # 4. It logged the fallback attempt
mock_logger.warning.assert_called_with(Attempting fallback query for user user123)

                # 5. Both queries were attempted
assert mock_db.execute.call_count == 2

print("")
[PASS] PROOF: ThreadRepository handles JSONB failures correctly)
print()
print(f   - Fallback query executed successfully")
print(")
print(f   - NULL and empty metadata threads were filtered out)

@pytest.mark.asyncio
    async def test_actual_code_with_null_metadata(self):
    "Prove the code handles NULL metadata without crashing."

thread_repo = ThreadRepository()
mock_db = AsyncMock(spec=AsyncSession)

                    # Force fallback to test NULL metadata handling
mock_result = MagicMock(); mock_scalars = Magic
                    # Mix of threads with NULL, empty, and valid metadata
threads = [
MagicMock(id=thread_null, metadata_=None),
MagicMock(id=thread_empty, metadata_={},
MagicMock(id=thread_valid, metadata_={"user_id": target-user},
MagicMock(id=thread_malformed, metadata_=not a dict),  # Malformed
                    

mock_scalars.all.return_value = threads
mock_result.scalars.return_value = mock_scalars

                    # Force fallback to test filtering logic
mock_db.execute.side_effect = [Exception(Force fallback"), mock_result]

                    # Execute
result = await thread_repo.find_by_user(mock_db, target-user)

                    # PROOF: NULL metadata filtered out, only valid thread returned
assert len(result) == 1
assert result[0].id == "thread_valid

print()
[PASS] PROOF: NULL metadata doesn't crash the system')
print()
print(f   - Filtered out NULL, empty, and malformed metadata")
print(f"   - Returned only valid matching thread)

@pytest.mark.asyncio
    async def test_actual_code_both_queries_fail(self):
    Prove graceful handling when both queries fail.

thread_repo = ThreadRepository()
mock_db = AsyncMock(spec=AsyncSession)

                        # Both queries fail
mock_db.execute.side_effect = [
Exception("JSONB query failed"),
Exception(Fallback query also failed)
                        

                        # Execute with logging
with patch('netra_backend.app.services.database.thread_repository.logger') as mock_logger:
    result = await thread_repo.find_by_user(mock_db, user123)

                            # PROOF POINTS:

                                # 1. Doesn't crash the application
assert result == []

                                # 2. Logs both failures
error_calls = [str(call) for call in mock_logger.error.call_args_list]
assert any(Primary JSONB query failed in call for call in error_calls)
assert any(Fallback query also failed" in call for call in error_calls)

                                # 3. Logs critical message
mock_logger.critical.assert_called_with( )
Unable to retrieve threads for user user123 - returning empty list
                                

                                # 4. Both queries were attempted
assert mock_db.execute.call_count == 2

print(")
[PASS] PROOF: Both queries failing is handled gracefully)
print(   - Primary query failed")"
print(   - Fallback query failed)
print(   - Returned empty list instead of crashing"")
print(   - Critical error was logged for monitoring)"

@pytest.mark.asyncio
    async def test_type_normalization_works(self):
    "Prove that type normalization works correctly.

thread_repo = ThreadRepository()
mock_db = AsyncMock(spec=AsyncSession)

                                    # Force fallback to test normalization
mock_result = MagicMock(); mock_scalars = Magic
                                    # Threads with different ID types
import uuid
uuid_obj = uuid.UUID("550e8400-e29b-41d4-a716-446655440000)"

threads = [
MagicMock(id=t1, metadata_={user_id: 550e8400-e29b-41d4-a716-446655440000},  # String"
MagicMock(id="t2, metadata_={user_id: uuid_obj},  # UUID object
MagicMock(id=t3, metadata_={user_id: 123},  # Integer
MagicMock(id="t4, metadata_={user_id":   123  },  # String with whitespace
                                    

mock_scalars.all.return_value = threads
mock_result.scalars.return_value = mock_scalars

                                    # Force fallback
mock_db.execute.side_effect = [Exception(Force fallback), mock_result]"

                                    # Test 1: Find UUID string
result = await thread_repo.find_by_user(mock_db, "550e8400-e29b-41d4-a716-446655440000)

assert len(result) == 2  # Should find both t1 (string) and t2 (UUID object)
assert {r.id for r in result} == {t1, t2}

                                    # Reset mock
mock_db.execute.side_effect = [Exception(Force fallback"), mock_result]"

                                    # Test 2: Find integer as string
result = await thread_repo.find_by_user(mock_db, 123)

assert len(result) == 2  # Should find both t3 (int) and t4 (string with spaces)
assert {r.id for r in result} == {t3, "t4}

print(")
[PASS] PROOF: Type normalization works correctly)"
print(   - UUID objects normalized to string)
print("   - Integer IDs normalized to string)
print(   - Whitespace properly stripped)

@pytest.mark.asyncio
    async def test_error_logging_improvements(self):
    "Prove that error logging improvements work."
from netra_backend.app.routes.utils.thread_error_handling import handle_route_with_error_logging
from fastapi import HTTPException

                                        # Mock handler that fails
async def failing_handler():
    raise ValueError(Database connection lost)

    # Test staging environment (detailed errors)
with patch('netra_backend.app.config.get_config') as mock_config:
    mock_config.return_value.environment = staging

with patch('netra_backend.app.logging_config.central_logger.get_logger') as mock_logger:
    mock_logger.return_value.error = Magic
with pytest.raises(HTTPException) as exc:
    await handle_route_with_error_logging(failing_handler, listing threads)

                # PROOF: Detailed error in staging
assert "Database connection lost" in exc.value.detail

                # PROOF: Full stack trace logged
log_call = mock_logger.return_value.error.call_args
assert log_call[1]['exc_info'] == True

                # Test production environment (generic errors)
with patch('netra_backend.app.config.get_config') as mock_config:
    mock_config.return_value.environment = production

with patch('netra_backend.app.logging_config.central_logger.get_logger') as mock_logger:
    mock_logger.return_value.error = Magic
with pytest.raises(HTTPException) as exc:
    await handle_route_with_error_logging(failing_handler, listing threads)

                            # PROOF: Generic error in production
assert Database connection lost not in exc.value.detail
assert Failed to list threads" in exc.value.detail

print()
[PASS] PROOF: Error logging is environment-aware")
print(   - Staging: Detailed errors with stack traces)"
print(   - Production: Generic errors for security")


class TestRealWorldScenarios:
        Test real-world scenarios that caused the 500 error.""

@pytest.mark.asyncio
    async def test_staging_scenario_jwt_user(self):
    Test the exact scenario from staging with JWT user.""

thread_repo = ThreadRepository()
mock_db = AsyncMock(spec=AsyncSession)

        # Simulate staging data state
staging_threads = [
        Thread with proper UUID from JWT
MagicMock(id=thread_1, metadata_={user_id: 7c5e1032-ed21-4aea-b12a-aeddf3622bec},"
        # Legacy thread with NULL metadata
MagicMock(id=thread_legacy", metadata_=None),
        Thread from different user
MagicMock(id=thread_other, metadata_={user_id: "different-user},"
        

mock_result = MagicMock(); mock_result.scalars.return_value.all.return_value = staging_threads

        # Simulate JSONB failure (what happens in staging)
mock_db.execute.side_effect = [
Exception(ERROR: operator does not exist: jsonb ->> unknown),
mock_result
        

        # Execute with the actual JWT user ID
jwt_user_id = 7c5e1032-ed21-4aea-b12a-aeddf3622bec"

result = await thread_repo.find_by_user(mock_db, jwt_user_id)

        # PROOF: Returns correct thread for JWT user
assert len(result) == 1
assert result[0].id == thread_1"

print()"
[PASS] PROOF: Staging scenario with JWT user works)
print(")
print(formatted_string)
print(   - Legacy NULL metadata threads filtered out"")
print(   - Other users threads filtered out)


if __name__ == "__main__":
            # Run the proof tests
pass
