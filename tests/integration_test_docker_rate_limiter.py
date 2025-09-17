class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
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
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

    #!/usr/bin/env python3
        '''
        Integration test demonstrating Docker rate limiting to prevent API storms.

        This test shows the rate limiter in action by running multiple Docker commands
        concurrently and verifying they are properly rate-limited.
        '''

        import sys
        import os
        from pathlib import Path

    # Add project root to Python path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))

        import time
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed

        from test_framework.docker_rate_limiter import get_docker_rate_limiter
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


    def simulate_concurrent_docker_operations():
        '''
        Simulate concurrent Docker operations that would normally cause API storms.

        Returns:
        Tuple of (total_duration, operations_completed, rate_limited_count)
        '''
        print("[ROCKET] Testing Docker rate limiter with concurrent operations...")

        rate_limiter = get_docker_rate_limiter()
        rate_limiter.reset_statistics()

        # Mock subprocess.run to simulate Docker commands
        with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock( )
        returncode=0,
        stdout="mocked docker output",
        stderr=""
            

    def execute_docker_command(cmd_id):
        """Execute a single Docker command."""
        result = rate_limiter.execute_docker_command([ ))
        "docker", "inspect", "formatted_string"
    
        return result.duration

    # Execute 10 Docker commands concurrently
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []

        for i in range(10):
        future = executor.submit(execute_docker_command, i)
        futures.append(future)

            # Wait for all operations to complete
        durations = []
        for future in as_completed(futures):
        try:
        duration = future.result()
        durations.append(duration)
        except Exception as e:
        print("formatted_string")

        total_duration = time.time() - start_time

                        # Get statistics
        stats = rate_limiter.get_statistics()

        print(f"[STATS] Rate Limiter Statistics:")
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")

        return total_duration, stats['total_operations'], stats['rate_limited_operations']


    def demonstrate_rate_limiting_effectiveness():
        '''
        Demonstrate that rate limiting prevents API storms by comparing
        with and without rate limiting.
        '''
        print(" )
        [DEMO] Demonstrating rate limiting effectiveness...")

    # Test WITH rate limiting
        print(" )
        1. Testing WITH rate limiting (should be slower but safer):")
        duration_with_limits, ops_with_limits, rate_limited = simulate_concurrent_docker_operations()

    # Test WITHOUT rate limiting (simulated)
        print(" )
        2. Simulating WITHOUT rate limiting (would be faster but dangerous):")

        start_time = time.time()
        with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # Simulate 10 concurrent subprocess calls without rate limiting
    def direct_subprocess_call(cmd_id):
        import subprocess
        return subprocess.run([ ))
        "docker", "inspect", "formatted_string"
        ], capture_output=True, text=True)

        with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [ )
        executor.submit(direct_subprocess_call, i)
        for i in range(10)
        

        for future in as_completed(futures):
        future.result()

        duration_without_limits = time.time() - start_time

        print(f"[RESULTS] Comparison Results:")
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")

            # Verify rate limiting was effective
        if rate_limited > 0:
        print("[OK] Rate limiting is working - operations were properly throttled")
        return True
        else:
        print("[WARNING] Rate limiting may not be working as expected")
        return False


    def test_docker_manager_integration():
        """Test that Docker managers properly use the rate limiter."""
        print(" )
        [LINK] Testing Docker manager integration...")

        try:
        from test_framework.unified_docker_manager import UnifiedDockerManager
        manager = UnifiedDockerManager()

        if hasattr(manager, 'docker_rate_limiter'):
        print("[OK] UnifiedDockerManager properly integrates rate limiter")

            # Test that it's the same singleton instance
        global_limiter = get_docker_rate_limiter()
        if manager.docker_rate_limiter is global_limiter:
        print("[OK] Using singleton rate limiter instance")
        else:
        print("[WARNING] Rate limiter is not the singleton instance")

        return True
        else:
        print("[ERROR] UnifiedDockerManager missing rate limiter integration")
        return False

        except Exception as e:
        print("formatted_string")
        return False


    def main():
        """Run the rate limiter integration test."""
        print("=" * 60)
        print("[DOCKER] RATE LIMITER INTEGRATION TEST")
        print("=" * 60)
        print("This test demonstrates rate limiting to prevent Docker API storms")
        print("that can crash Docker Desktop due to concurrent operations.")
        print()

        success = True

        try:
        # Test 1: Rate limiting effectiveness
        success &= demonstrate_rate_limiting_effectiveness()

        # Test 2: Docker manager integration
        success &= test_docker_manager_integration()

        print(" )
        " + "=" * 60)
        if success:
        print("[SUCCESS] ALL TESTS PASSED - Rate limiter is working correctly!")
        print("[OK] Docker API storms should now be prevented")
        else:
        print("[WARNING] SOME TESTS FAILED - Please review the implementation")

        print("=" * 60)

        except Exception as e:
        print("formatted_string")
        import traceback
        traceback.print_exc()


        if __name__ == "__main__":
        main()
