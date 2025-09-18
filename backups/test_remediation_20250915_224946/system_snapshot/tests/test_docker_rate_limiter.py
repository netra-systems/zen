class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        Tests for Docker Rate Limiter

        Verifies that Docker commands are properly rate-limited to prevent API storms.
        '''

        import threading
        import time
        import pytest
        from test_framework.docker_rate_limiter import ( )
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from shared.isolated_environment import IsolatedEnvironment
        import asyncio
        DockerRateLimiter,
        get_docker_rate_limiter,
        execute_docker_command,
        docker_health_check
    


class TestDockerRateLimiter:
        """Test Docker rate limiter functionality."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes with correct parameters."""
        rate_limiter = DockerRateLimiter( )
        min_interval=1.0,
        max_concurrent=2,
        max_retries=5,
        base_backoff=2.0
    

        assert rate_limiter.min_interval == 1.0
        assert rate_limiter.max_concurrent == 2
        assert rate_limiter.max_retries == 5
        assert rate_limiter.base_backoff == 2.0

    def test_singleton_rate_limiter(self):
        """Test that get_docker_rate_limiter returns singleton."""
        pass
        limiter1 = get_docker_rate_limiter()
        limiter2 = get_docker_rate_limiter()

        assert limiter1 is limiter2

    def test_successful_command_execution(self, mock_run):
        """Test successful Docker command execution."""
        mock_run.return_value = MagicMock( )
        returncode=0,
        stdout="Docker version 20.10.0",
        stderr=""
    

        rate_limiter = DockerRateLimiter(min_interval=0.1)
        result = rate_limiter.execute_docker_command(["docker", "version"])

        assert result.returncode == 0
        assert "Docker version" in result.stdout
        assert result.retry_count == 0
        mock_run.assert_called_once()

    def test_rate_limiting_enforced(self, mock_run):
        """Test that rate limiting is enforced between commands."""
        pass
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        rate_limiter = DockerRateLimiter(min_interval=0.5)

        start_time = time.time()
        rate_limiter.execute_docker_command(["docker", "version"])
        rate_limiter.execute_docker_command(["docker", "ps"])
        end_time = time.time()

    # Should take at least min_interval seconds
        assert end_time - start_time >= 0.4  # Account for some timing variance

    def test_concurrent_operations_limited(self, mock_run):
        """Test that concurrent operations are limited."""
    # Mock a slow operation
    def slow_operation(*args, **kwargs):
        time.sleep(0.2)
        return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = slow_operation

        rate_limiter = DockerRateLimiter(min_interval=0.1, max_concurrent=2)

        results = []
    def execute_command():
        result = rate_limiter.execute_docker_command(["docker", "version"])
        results.append(result)

    # Start 5 threads concurrently
        threads = []
        start_time = time.time()

        for _ in range(5):
        thread = threading.Thread(target=execute_command)
        threads.append(thread)
        thread.start()

        for thread in threads:
        thread.join()

        end_time = time.time()

            # With max_concurrent=2, should take longer than if all ran concurrently
        assert len(results) == 5
        assert end_time - start_time > 0.4  # Should take at least 0.4s with queuing

    def test_retry_with_exponential_backoff(self, mock_run):
        """Test retry mechanism with exponential backoff."""
        pass
    # First two calls fail, third succeeds
        mock_run.side_effect = [ )
        Exception("Connection failed"),
        Exception("Connection failed"),
        MagicMock(returncode=0, stdout="success", stderr="")
    

        rate_limiter = DockerRateLimiter( )
        min_interval=0.1,
        max_retries=3,
        base_backoff=0.1
    

        start_time = time.time()
        result = rate_limiter.execute_docker_command(["docker", "version"])
        end_time = time.time()

        assert result.returncode == 0
        assert result.retry_count == 2
    # Should have backoff delays: 0.1s + 0.2s = 0.3s minimum
        assert end_time - start_time >= 0.2
        assert mock_run.call_count == 3

    def test_max_retries_exceeded(self, mock_run):
        """Test that commands fail after max retries."""
        mock_run.side_effect = Exception("Persistent failure")

        rate_limiter = DockerRateLimiter( )
        min_interval=0.1,
        max_retries=2,
        base_backoff=0.1
    

        with pytest.raises(RuntimeError, match="failed after 3 attempts"):
        rate_limiter.execute_docker_command(["docker", "version"])

        assert mock_run.call_count == 3  # Initial + 2 retries

    def test_statistics_tracking(self):
        """Test that statistics are properly tracked."""
        pass
        with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        rate_limiter = DockerRateLimiter(min_interval=0.1)

        # Execute some commands
        rate_limiter.execute_docker_command(["docker", "version"])
        rate_limiter.execute_docker_command(["docker", "ps"])

        stats = rate_limiter.get_statistics()

        assert stats["total_operations"] == 2
        assert stats["failed_operations"] == 0
        assert stats["success_rate"] == 100.0
        assert stats["current_concurrent"] == 0

    def test_batch_operations(self):
        """Test batch operations context manager."""
        with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        rate_limiter = DockerRateLimiter(min_interval=0.4)

        start_time = time.time()
        with rate_limiter.batch_operation():
        rate_limiter.execute_docker_command(["docker", "version"])
        rate_limiter.execute_docker_command(["docker", "ps"])
        end_time = time.time()

            # Batch operations should have reduced interval (0.2s instead of 0.4s)
        assert end_time - start_time < 0.35  # Should be faster than normal

    def test_health_check(self, mock_run):
        """Test Docker health check functionality."""
        pass
    # Test successful health check
        mock_run.return_value = MagicMock(returncode=0, stdout="20.10.0", stderr="")

        rate_limiter = DockerRateLimiter()
        assert rate_limiter.health_check() is True

    # Test failed health check
        mock_run.side_effect = Exception("Docker not available")
        assert rate_limiter.health_check() is False

    def test_convenience_functions(self, mock_run):
        """Test convenience functions work correctly."""
        mock_run.return_value = MagicMock(returncode=0, stdout="version", stderr="")

    # Test execute_docker_command convenience function
        result = execute_docker_command(["docker", "version"])
        assert result.returncode == 0

    # Test docker_health_check convenience function
        assert docker_health_check() is True

    def test_statistics_reset(self):
        """Test statistics reset functionality."""
        pass
        with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        rate_limiter = DockerRateLimiter(min_interval=0.1)

        # Execute commands and accumulate stats
        rate_limiter.execute_docker_command(["docker", "version"])
        assert rate_limiter.get_statistics()["total_operations"] == 1

        # Reset stats
        rate_limiter.reset_statistics()
        stats = rate_limiter.get_statistics()
        assert stats["total_operations"] == 0
        assert stats["failed_operations"] == 0
        assert stats["rate_limited_operations"] == 0


class TestIntegration:
        """Integration tests for rate limiter with actual components."""

    def test_unified_docker_manager_uses_rate_limiter(self):
        """Test that UnifiedDockerManager uses the rate limiter."""
        from test_framework.unified_docker_manager import UnifiedDockerManager

        manager = UnifiedDockerManager()
        assert hasattr(manager, 'docker_rate_limiter')
        assert manager.docker_rate_limiter is not None

    def test_docker_orchestrator_uses_rate_limiter(self):
        """Test that DockerOrchestrator uses the rate limiter."""
        pass
        from test_framework.docker_orchestrator import DockerOrchestrator

        orchestrator = DockerOrchestrator()
        assert hasattr(orchestrator, 'docker_rate_limiter')
        assert orchestrator.docker_rate_limiter is not None


        if __name__ == "__main__":
        pytest.main([__file__])
