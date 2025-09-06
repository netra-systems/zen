# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Tests for Docker Rate Limiter

    # REMOVED_SYNTAX_ERROR: Verifies that Docker commands are properly rate-limited to prevent API storms.
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import threading
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from test_framework.docker_rate_limiter import ( )
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.docker.unified_docker_manager import UnifiedDockerManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment
    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: DockerRateLimiter,
    # REMOVED_SYNTAX_ERROR: get_docker_rate_limiter,
    # REMOVED_SYNTAX_ERROR: execute_docker_command,
    # REMOVED_SYNTAX_ERROR: docker_health_check
    


# REMOVED_SYNTAX_ERROR: class TestDockerRateLimiter:
    # REMOVED_SYNTAX_ERROR: """Test Docker rate limiter functionality."""

# REMOVED_SYNTAX_ERROR: def test_rate_limiter_initialization(self):
    # REMOVED_SYNTAX_ERROR: """Test rate limiter initializes with correct parameters."""
    # REMOVED_SYNTAX_ERROR: rate_limiter = DockerRateLimiter( )
    # REMOVED_SYNTAX_ERROR: min_interval=1.0,
    # REMOVED_SYNTAX_ERROR: max_concurrent=2,
    # REMOVED_SYNTAX_ERROR: max_retries=5,
    # REMOVED_SYNTAX_ERROR: base_backoff=2.0
    

    # REMOVED_SYNTAX_ERROR: assert rate_limiter.min_interval == 1.0
    # REMOVED_SYNTAX_ERROR: assert rate_limiter.max_concurrent == 2
    # REMOVED_SYNTAX_ERROR: assert rate_limiter.max_retries == 5
    # REMOVED_SYNTAX_ERROR: assert rate_limiter.base_backoff == 2.0

# REMOVED_SYNTAX_ERROR: def test_singleton_rate_limiter(self):
    # REMOVED_SYNTAX_ERROR: """Test that get_docker_rate_limiter returns singleton."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: limiter1 = get_docker_rate_limiter()
    # REMOVED_SYNTAX_ERROR: limiter2 = get_docker_rate_limiter()

    # REMOVED_SYNTAX_ERROR: assert limiter1 is limiter2

# REMOVED_SYNTAX_ERROR: def test_successful_command_execution(self, mock_run):
    # REMOVED_SYNTAX_ERROR: """Test successful Docker command execution."""
    # REMOVED_SYNTAX_ERROR: mock_run.return_value = MagicMock( )
    # REMOVED_SYNTAX_ERROR: returncode=0,
    # REMOVED_SYNTAX_ERROR: stdout="Docker version 20.10.0",
    # REMOVED_SYNTAX_ERROR: stderr=""
    

    # REMOVED_SYNTAX_ERROR: rate_limiter = DockerRateLimiter(min_interval=0.1)
    # REMOVED_SYNTAX_ERROR: result = rate_limiter.execute_docker_command(["docker", "version"])

    # REMOVED_SYNTAX_ERROR: assert result.returncode == 0
    # REMOVED_SYNTAX_ERROR: assert "Docker version" in result.stdout
    # REMOVED_SYNTAX_ERROR: assert result.retry_count == 0
    # REMOVED_SYNTAX_ERROR: mock_run.assert_called_once()

# REMOVED_SYNTAX_ERROR: def test_rate_limiting_enforced(self, mock_run):
    # REMOVED_SYNTAX_ERROR: """Test that rate limiting is enforced between commands."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    # REMOVED_SYNTAX_ERROR: rate_limiter = DockerRateLimiter(min_interval=0.5)

    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: rate_limiter.execute_docker_command(["docker", "version"])
    # REMOVED_SYNTAX_ERROR: rate_limiter.execute_docker_command(["docker", "ps"])
    # REMOVED_SYNTAX_ERROR: end_time = time.time()

    # Should take at least min_interval seconds
    # REMOVED_SYNTAX_ERROR: assert end_time - start_time >= 0.4  # Account for some timing variance

# REMOVED_SYNTAX_ERROR: def test_concurrent_operations_limited(self, mock_run):
    # REMOVED_SYNTAX_ERROR: """Test that concurrent operations are limited."""
    # Mock a slow operation
# REMOVED_SYNTAX_ERROR: def slow_operation(*args, **kwargs):
    # REMOVED_SYNTAX_ERROR: time.sleep(0.2)
    # REMOVED_SYNTAX_ERROR: return MagicMock(returncode=0, stdout="", stderr="")

    # REMOVED_SYNTAX_ERROR: mock_run.side_effect = slow_operation

    # REMOVED_SYNTAX_ERROR: rate_limiter = DockerRateLimiter(min_interval=0.1, max_concurrent=2)

    # REMOVED_SYNTAX_ERROR: results = []
# REMOVED_SYNTAX_ERROR: def execute_command():
    # REMOVED_SYNTAX_ERROR: result = rate_limiter.execute_docker_command(["docker", "version"])
    # REMOVED_SYNTAX_ERROR: results.append(result)

    # Start 5 threads concurrently
    # REMOVED_SYNTAX_ERROR: threads = []
    # REMOVED_SYNTAX_ERROR: start_time = time.time()

    # REMOVED_SYNTAX_ERROR: for _ in range(5):
        # REMOVED_SYNTAX_ERROR: thread = threading.Thread(target=execute_command)
        # REMOVED_SYNTAX_ERROR: threads.append(thread)
        # REMOVED_SYNTAX_ERROR: thread.start()

        # REMOVED_SYNTAX_ERROR: for thread in threads:
            # REMOVED_SYNTAX_ERROR: thread.join()

            # REMOVED_SYNTAX_ERROR: end_time = time.time()

            # With max_concurrent=2, should take longer than if all ran concurrently
            # REMOVED_SYNTAX_ERROR: assert len(results) == 5
            # REMOVED_SYNTAX_ERROR: assert end_time - start_time > 0.4  # Should take at least 0.4s with queuing

# REMOVED_SYNTAX_ERROR: def test_retry_with_exponential_backoff(self, mock_run):
    # REMOVED_SYNTAX_ERROR: """Test retry mechanism with exponential backoff."""
    # REMOVED_SYNTAX_ERROR: pass
    # First two calls fail, third succeeds
    # REMOVED_SYNTAX_ERROR: mock_run.side_effect = [ )
    # REMOVED_SYNTAX_ERROR: Exception("Connection failed"),
    # REMOVED_SYNTAX_ERROR: Exception("Connection failed"),
    # REMOVED_SYNTAX_ERROR: MagicMock(returncode=0, stdout="success", stderr="")
    

    # REMOVED_SYNTAX_ERROR: rate_limiter = DockerRateLimiter( )
    # REMOVED_SYNTAX_ERROR: min_interval=0.1,
    # REMOVED_SYNTAX_ERROR: max_retries=3,
    # REMOVED_SYNTAX_ERROR: base_backoff=0.1
    

    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: result = rate_limiter.execute_docker_command(["docker", "version"])
    # REMOVED_SYNTAX_ERROR: end_time = time.time()

    # REMOVED_SYNTAX_ERROR: assert result.returncode == 0
    # REMOVED_SYNTAX_ERROR: assert result.retry_count == 2
    # Should have backoff delays: 0.1s + 0.2s = 0.3s minimum
    # REMOVED_SYNTAX_ERROR: assert end_time - start_time >= 0.2
    # REMOVED_SYNTAX_ERROR: assert mock_run.call_count == 3

# REMOVED_SYNTAX_ERROR: def test_max_retries_exceeded(self, mock_run):
    # REMOVED_SYNTAX_ERROR: """Test that commands fail after max retries."""
    # REMOVED_SYNTAX_ERROR: mock_run.side_effect = Exception("Persistent failure")

    # REMOVED_SYNTAX_ERROR: rate_limiter = DockerRateLimiter( )
    # REMOVED_SYNTAX_ERROR: min_interval=0.1,
    # REMOVED_SYNTAX_ERROR: max_retries=2,
    # REMOVED_SYNTAX_ERROR: base_backoff=0.1
    

    # REMOVED_SYNTAX_ERROR: with pytest.raises(RuntimeError, match="failed after 3 attempts"):
        # REMOVED_SYNTAX_ERROR: rate_limiter.execute_docker_command(["docker", "version"])

        # REMOVED_SYNTAX_ERROR: assert mock_run.call_count == 3  # Initial + 2 retries

# REMOVED_SYNTAX_ERROR: def test_statistics_tracking(self):
    # REMOVED_SYNTAX_ERROR: """Test that statistics are properly tracked."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: with patch('subprocess.run') as mock_run:
        # REMOVED_SYNTAX_ERROR: mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # REMOVED_SYNTAX_ERROR: rate_limiter = DockerRateLimiter(min_interval=0.1)

        # Execute some commands
        # REMOVED_SYNTAX_ERROR: rate_limiter.execute_docker_command(["docker", "version"])
        # REMOVED_SYNTAX_ERROR: rate_limiter.execute_docker_command(["docker", "ps"])

        # REMOVED_SYNTAX_ERROR: stats = rate_limiter.get_statistics()

        # REMOVED_SYNTAX_ERROR: assert stats["total_operations"] == 2
        # REMOVED_SYNTAX_ERROR: assert stats["failed_operations"] == 0
        # REMOVED_SYNTAX_ERROR: assert stats["success_rate"] == 100.0
        # REMOVED_SYNTAX_ERROR: assert stats["current_concurrent"] == 0

# REMOVED_SYNTAX_ERROR: def test_batch_operations(self):
    # REMOVED_SYNTAX_ERROR: """Test batch operations context manager."""
    # REMOVED_SYNTAX_ERROR: with patch('subprocess.run') as mock_run:
        # REMOVED_SYNTAX_ERROR: mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # REMOVED_SYNTAX_ERROR: rate_limiter = DockerRateLimiter(min_interval=0.4)

        # REMOVED_SYNTAX_ERROR: start_time = time.time()
        # REMOVED_SYNTAX_ERROR: with rate_limiter.batch_operation():
            # REMOVED_SYNTAX_ERROR: rate_limiter.execute_docker_command(["docker", "version"])
            # REMOVED_SYNTAX_ERROR: rate_limiter.execute_docker_command(["docker", "ps"])
            # REMOVED_SYNTAX_ERROR: end_time = time.time()

            # Batch operations should have reduced interval (0.2s instead of 0.4s)
            # REMOVED_SYNTAX_ERROR: assert end_time - start_time < 0.35  # Should be faster than normal

# REMOVED_SYNTAX_ERROR: def test_health_check(self, mock_run):
    # REMOVED_SYNTAX_ERROR: """Test Docker health check functionality."""
    # REMOVED_SYNTAX_ERROR: pass
    # Test successful health check
    # REMOVED_SYNTAX_ERROR: mock_run.return_value = MagicMock(returncode=0, stdout="20.10.0", stderr="")

    # REMOVED_SYNTAX_ERROR: rate_limiter = DockerRateLimiter()
    # REMOVED_SYNTAX_ERROR: assert rate_limiter.health_check() is True

    # Test failed health check
    # REMOVED_SYNTAX_ERROR: mock_run.side_effect = Exception("Docker not available")
    # REMOVED_SYNTAX_ERROR: assert rate_limiter.health_check() is False

# REMOVED_SYNTAX_ERROR: def test_convenience_functions(self, mock_run):
    # REMOVED_SYNTAX_ERROR: """Test convenience functions work correctly."""
    # REMOVED_SYNTAX_ERROR: mock_run.return_value = MagicMock(returncode=0, stdout="version", stderr="")

    # Test execute_docker_command convenience function
    # REMOVED_SYNTAX_ERROR: result = execute_docker_command(["docker", "version"])
    # REMOVED_SYNTAX_ERROR: assert result.returncode == 0

    # Test docker_health_check convenience function
    # REMOVED_SYNTAX_ERROR: assert docker_health_check() is True

# REMOVED_SYNTAX_ERROR: def test_statistics_reset(self):
    # REMOVED_SYNTAX_ERROR: """Test statistics reset functionality."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: with patch('subprocess.run') as mock_run:
        # REMOVED_SYNTAX_ERROR: mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # REMOVED_SYNTAX_ERROR: rate_limiter = DockerRateLimiter(min_interval=0.1)

        # Execute commands and accumulate stats
        # REMOVED_SYNTAX_ERROR: rate_limiter.execute_docker_command(["docker", "version"])
        # REMOVED_SYNTAX_ERROR: assert rate_limiter.get_statistics()["total_operations"] == 1

        # Reset stats
        # REMOVED_SYNTAX_ERROR: rate_limiter.reset_statistics()
        # REMOVED_SYNTAX_ERROR: stats = rate_limiter.get_statistics()
        # REMOVED_SYNTAX_ERROR: assert stats["total_operations"] == 0
        # REMOVED_SYNTAX_ERROR: assert stats["failed_operations"] == 0
        # REMOVED_SYNTAX_ERROR: assert stats["rate_limited_operations"] == 0


# REMOVED_SYNTAX_ERROR: class TestIntegration:
    # REMOVED_SYNTAX_ERROR: """Integration tests for rate limiter with actual components."""

# REMOVED_SYNTAX_ERROR: def test_unified_docker_manager_uses_rate_limiter(self):
    # REMOVED_SYNTAX_ERROR: """Test that UnifiedDockerManager uses the rate limiter."""
    # REMOVED_SYNTAX_ERROR: from test_framework.unified_docker_manager import UnifiedDockerManager

    # REMOVED_SYNTAX_ERROR: manager = UnifiedDockerManager()
    # REMOVED_SYNTAX_ERROR: assert hasattr(manager, 'docker_rate_limiter')
    # REMOVED_SYNTAX_ERROR: assert manager.docker_rate_limiter is not None

# REMOVED_SYNTAX_ERROR: def test_docker_orchestrator_uses_rate_limiter(self):
    # REMOVED_SYNTAX_ERROR: """Test that DockerOrchestrator uses the rate limiter."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from test_framework.docker_orchestrator import DockerOrchestrator

    # REMOVED_SYNTAX_ERROR: orchestrator = DockerOrchestrator()
    # REMOVED_SYNTAX_ERROR: assert hasattr(orchestrator, 'docker_rate_limiter')
    # REMOVED_SYNTAX_ERROR: assert orchestrator.docker_rate_limiter is not None


    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
        # REMOVED_SYNTAX_ERROR: pytest.main([__file__])