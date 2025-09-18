"""
Test Suite for NetraOptimizerClient

TDD tests that validate every step of the client's execution sequence.
These tests are written BEFORE the implementation to drive the design.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import UUID, uuid4

# Import the client we're about to build
from netraoptimizer.client import NetraOptimizerClient
from netraoptimizer.database.models import ExecutionRecord


class NetraOptimizerClientTests:
    """Comprehensive test suite for the NetraOptimizerClient."""

    @pytest.fixture
    def mock_db_client(self):
        """Mock database client for testing."""
        mock = AsyncMock()
        mock.insert_execution = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def mock_subprocess_success(self):
        """Mock successful subprocess execution with realistic output."""
        output = json.dumps({
            "usage": {
                "input_tokens": 1570,
                "output_tokens": 1330,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 5400000,
                "total_cost": 0.087
            },
            "tool_calls": 8,
            "status": "completed",
            "message": "Task completed successfully"
        })
        return output

    @pytest.fixture
    def mock_subprocess_failure(self):
        """Mock failed subprocess execution."""
        return "Error: Command execution failed"

    @pytest.mark.asyncio
    async def test_client_initialization(self, mock_db_client):
        """Test that the client initializes correctly with required dependencies."""
        client = NetraOptimizerClient(database_client=mock_db_client)

        assert client is not None
        assert client.database_client == mock_db_client
        assert hasattr(client, 'run')

    @pytest.mark.asyncio
    async def test_run_records_start_time(self, mock_db_client):
        """Test that the client records the start time before execution."""
        client = NetraOptimizerClient(database_client=mock_db_client)

        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b'{"status": "completed"}', b''))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            start_time = datetime.now(timezone.utc)
            result = await client.run("/test command")

            # Verify timing was recorded
            assert mock_db_client.insert_execution.called
            call_args = mock_db_client.insert_execution.call_args[0][0]
            assert isinstance(call_args, ExecutionRecord)
            assert (call_args.timestamp - start_time).total_seconds() < 1

    @pytest.mark.asyncio
    async def test_run_executes_subprocess(self, mock_db_client):
        """Test that the client properly executes the subprocess with the command."""
        client = NetraOptimizerClient(database_client=mock_db_client)
        command = "/test command with args"

        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b'{"status": "completed"}', b''))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            await client.run(command)

            # Verify subprocess was called with correct arguments
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0]
            assert 'claude' in call_args[0]  # Claude executable
            # Check if command parts are in the arguments
            command_parts = command.strip('/').split()
            assert any(part in call_args for part in command_parts)

    @pytest.mark.asyncio
    async def test_run_parses_token_metrics(self, mock_db_client, mock_subprocess_success):
        """Test that the client correctly parses token metrics from output."""
        client = NetraOptimizerClient(database_client=mock_db_client)

        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(mock_subprocess_success.encode(), b''))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            await client.run("/test command")

            # Verify token metrics were parsed and saved
            assert mock_db_client.insert_execution.called
            record = mock_db_client.insert_execution.call_args[0][0]
            assert record.input_tokens == 1570
            assert record.output_tokens == 1330
            assert record.cached_tokens == 5400000
            # Total should be fresh (input + output) + cached
            assert record.total_tokens == 1570 + 1330 + 5400000
            assert record.tool_calls == 8

    @pytest.mark.asyncio
    async def test_run_calculates_execution_time(self, mock_db_client):
        """Test that the client calculates execution time correctly."""
        client = NetraOptimizerClient(database_client=mock_db_client)

        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()

            # Simulate 500ms execution time
            async def delayed_communicate():
                await asyncio.sleep(0.5)
                return (b'{"status": "completed"}', b'')

            mock_process.communicate = delayed_communicate
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            await client.run("/test command")

            # Verify execution time was recorded
            record = mock_db_client.insert_execution.call_args[0][0]
            assert record.execution_time_ms >= 500
            assert record.execution_time_ms < 1000  # Should be ~500ms

    @pytest.mark.asyncio
    async def test_run_handles_subprocess_failure(self, mock_db_client, mock_subprocess_failure):
        """Test that the client properly handles subprocess failures."""
        client = NetraOptimizerClient(database_client=mock_db_client)

        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b'', mock_subprocess_failure.encode()))
            mock_process.returncode = 1
            mock_subprocess.return_value = mock_process

            result = await client.run("/failing command")

            # Verify failure was recorded
            record = mock_db_client.insert_execution.call_args[0][0]
            assert record.status == "failed"
            assert record.error_message == mock_subprocess_failure
            assert result['status'] == "failed"

    @pytest.mark.asyncio
    async def test_run_handles_timeout(self, mock_db_client):
        """Test that the client handles command timeouts properly."""
        client = NetraOptimizerClient(database_client=mock_db_client, timeout=1)  # 1 second timeout

        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()

            # Simulate timeout
            async def timeout_communicate():
                await asyncio.sleep(2)  # Longer than timeout
                return (b'', b'')

            mock_process.communicate = timeout_communicate
            mock_process.returncode = None
            mock_subprocess.return_value = mock_process

            with pytest.raises(asyncio.TimeoutError):
                await client.run("/timeout command")

            # Verify timeout was recorded
            record = mock_db_client.insert_execution.call_args[0][0]
            assert record.status == "timeout"

    @pytest.mark.asyncio
    async def test_run_extracts_command_base(self, mock_db_client):
        """Test that the client correctly extracts the command base."""
        client = NetraOptimizerClient(database_client=mock_db_client)

        test_cases = [
            ("/gitissueprogressorv3 p0 agents", "/gitissueprogressorv3"),
            ("/test simple", "/test"),
            ("/complex-command --flag value", "/complex-command"),
        ]

        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b'{"status": "completed"}', b''))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            for command, expected_base in test_cases:
                await client.run(command)
                record = mock_db_client.insert_execution.call_args[0][0]
                assert record.command_base == expected_base

    @pytest.mark.asyncio
    async def test_run_calculates_costs(self, mock_db_client, mock_subprocess_success):
        """Test that the client calculates costs correctly."""
        client = NetraOptimizerClient(database_client=mock_db_client)

        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(mock_subprocess_success.encode(), b''))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            await client.run("/test command")

            # Verify costs were calculated
            record = mock_db_client.insert_execution.call_args[0][0]
            assert record.fresh_cost_usd > 0
            assert record.cache_savings_usd > 0
            assert record.cost_usd == record.fresh_cost_usd

    @pytest.mark.asyncio
    async def test_run_returns_result_dict(self, mock_db_client, mock_subprocess_success):
        """Test that the client returns a properly formatted result dictionary."""
        client = NetraOptimizerClient(database_client=mock_db_client)

        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(mock_subprocess_success.encode(), b''))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            result = await client.run("/test command")

            # Verify result structure
            assert isinstance(result, dict)
            assert 'status' in result
            assert 'execution_id' in result
            assert 'tokens' in result
            assert 'execution_time_ms' in result
            assert 'cost_usd' in result
            assert result['status'] == 'completed'

    @pytest.mark.asyncio
    async def test_run_with_batch_context(self, mock_db_client):
        """Test that the client handles batch execution context."""
        from uuid import uuid4
        batch_id = str(uuid4())  # Generate valid UUID
        client = NetraOptimizerClient(database_client=mock_db_client)

        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b'{"status": "completed"}', b''))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            await client.run("/test command", batch_id=batch_id, execution_sequence=3)

            # Verify batch context was recorded
            record = mock_db_client.insert_execution.call_args[0][0]
            assert str(record.batch_id) == batch_id
            assert record.execution_sequence == 3

    @pytest.mark.asyncio
    async def test_run_with_workspace_context(self, mock_db_client):
        """Test that the client captures workspace context."""
        client = NetraOptimizerClient(database_client=mock_db_client)

        workspace_context = {
            "workspace_path": "/test/workspace",
            "file_count": 1247,
            "total_size_mb": 89.3
        }

        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b'{"status": "completed"}', b''))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            await client.run("/test command", workspace_context=workspace_context)

            # Verify workspace context was recorded
            record = mock_db_client.insert_execution.call_args[0][0]
            assert record.workspace_context == workspace_context