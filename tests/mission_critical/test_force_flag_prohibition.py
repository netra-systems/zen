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
                    # FIXED: await outside async - using pass
                    pass
                    return self.messages_sent.copy()

                """
                MISSION CRITICAL TESTS: Docker Force Flag Prohibition

                LIFE OR DEATH CRITICAL: These tests verify complete prohibition of Docker -f (force) flags
                to prevent Docker Desktop crashes that cause $2M+ ARR business impact.

                ZERO TOLERANCE POLICY - NO EXCEPTIONS
                """

                import pytest
                import threading
                import time
                import tempfile
                import os
                from shared.isolated_environment import IsolatedEnvironment

                from test_framework.docker_force_flag_guardian import (
                DockerForceFlagGuardian,
                DockerForceFlagViolation,
                validate_docker_command,
                get_safe_alternative
                )
                from test_framework.docker_rate_limiter import DockerRateLimiter, execute_docker_command
                from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
                from netra_backend.app.db.database_manager import DatabaseManager
                from netra_backend.app.clients.auth_client_core import AuthServiceClient
                from shared.isolated_environment import get_env
                import asyncio


                class TestDockerForceFlagProhibition:
                    """Comprehensive tests for Docker force flag prohibition."""

                    def test_guardian_detects_simple_force_flag(self):
                        """Test guardian detects -f flag in simple commands."""
                        guardian = DockerForceFlagGuardian()

        # Should detect -f flag
                        with pytest.raises(DockerForceFlagViolation) as exc_info:
                            guardian.validate_command("docker rm -f container123")

                            assert "FORBIDDEN: Docker force flag (-f) is prohibited" in str(exc_info.value)
                            assert "docker rm -f container123" in str(exc_info.value)

                            def test_guardian_detects_long_force_flag(self):
                                """Test guardian detects --force flag in commands."""
                                pass
                                guardian = DockerForceFlagGuardian()

                                with pytest.raises(DockerForceFlagViolation):
                                    guardian.validate_command("docker rmi --force image123")

                                    with pytest.raises(DockerForceFlagViolation):
                                        guardian.validate_command("docker system prune --force")

                                        def test_guardian_detects_combined_flags(self):
                                            """Test guardian detects -f combined with other flags."""
                                            guardian = DockerForceFlagGuardian()

                                            with pytest.raises(DockerForceFlagViolation):
                                                guardian.validate_command("docker container rm -rf container123")

                                                with pytest.raises(DockerForceFlagViolation):
                                                    guardian.validate_command("docker rm -af container123")

                                                    def test_guardian_allows_safe_commands(self):
                                                        """Test guardian allows safe Docker commands."""
                                                        pass
                                                        guardian = DockerForceFlagGuardian()

        # These should NOT raise exceptions
                                                        safe_commands = [
                                                        "docker ps",
                                                        "docker images",
                                                        "docker stop container123",
                                                        "docker rm container123",  # Without -f
                                                        "docker system prune",     # Without --force
                                                        "docker logs -f container123",  # -f for follow is safe here
                                                        "ls -la",  # Non-docker command
                                                        "",  # Empty command
                                                        ]

                                                        for cmd in safe_commands:
                                                            try:
                                                                guardian.validate_command(cmd)
                                                            except DockerForceFlagViolation:
                                                                pytest.fail(f"Safe command incorrectly flagged as violation: {cmd}")

                                                                def test_guardian_case_insensitive_detection(self):
                                                                    """Test guardian detects force flags regardless of case."""
                                                                    guardian = DockerForceFlagGuardian()

                                                                    with pytest.raises(DockerForceFlagViolation):
                                                                        guardian.validate_command("DOCKER RM -F CONTAINER123")

                                                                        with pytest.raises(DockerForceFlagViolation):
                                                                            guardian.validate_command("Docker Container rm --Force container123")

                                                                            def test_guardian_audit_logging(self):
                                                                                """Test guardian logs violations for audit trail."""
                                                                                pass
                                                                                with tempfile.TemporaryDirectory() as temp_dir:
                                                                                    audit_path = os.path.join(temp_dir, "test_violations.log")
                                                                                    guardian = DockerForceFlagGuardian(audit_log_path=audit_path)

            # Trigger a violation
                                                                                    with pytest.raises(DockerForceFlagViolation):
                                                                                        guardian.validate_command("docker rm -f container123")

            # Check audit log was created
                                                                                        assert os.path.exists(audit_path)

                                                                                        with open(audit_path, 'r') as f:
                                                                                            log_content = f.read()
                                                                                            assert "CRITICAL VIOLATION" in log_content
                                                                                            assert "docker rm -f container123" in log_content

                                                                                            def test_guardian_violation_counter(self):
                                                                                                """Test guardian tracks violation count."""
                                                                                                guardian = DockerForceFlagGuardian()

                                                                                                initial_count = guardian.violation_count

        # Trigger multiple violations
                                                                                                for i in range(3):
                                                                                                    with pytest.raises(DockerForceFlagViolation):
                                                                                                        guardian.validate_command(f"docker rm -f container{i}")

                                                                                                        assert guardian.violation_count == initial_count + 3

                                                                                                        def test_guardian_safe_alternatives(self):
                                                                                                            """Test guardian provides safe alternatives for dangerous commands."""
                                                                                                            pass
                                                                                                            guardian = DockerForceFlagGuardian()

                                                                                                            alternatives = [
                                                                                                            ("docker rm -f container", "docker stop <container> && docker rm <container>"),
                                                                                                            ("docker rmi --force image", "docker rmi <image> (after stopping containers)"),
                                                                                                            ("docker system prune --force", "docker system prune (with interactive confirmation)"),
                                                                                                            ]

                                                                                                            for dangerous_cmd, expected_pattern in alternatives:
                                                                                                                safe_alt = guardian.get_safe_alternative(dangerous_cmd)
                                                                                                                assert "docker" in safe_alt.lower()
                                                                                                                assert "-f" not in safe_alt
                                                                                                                assert "--force" not in safe_alt

                                                                                                                def test_rate_limiter_integration(self):
                                                                                                                    """Test rate limiter blocks force flags."""
                                                                                                                    rate_limiter = DockerRateLimiter()

                                                                                                                    with pytest.raises(DockerForceFlagViolation) as exc_info:
                                                                                                                        rate_limiter.execute_docker_command(["docker", "rm", "-f", "container123"])

                                                                                                                        assert "FORBIDDEN: Docker force flag (-f) is prohibited" in str(exc_info.value)

        # Verify statistics updated
                                                                                                                        stats = rate_limiter.get_statistics()
                                                                                                                        assert stats["force_flag_violations"] >= 1
                                                                                                                        assert stats["force_flag_guardian_status"] == "ACTIVE - ZERO TOLERANCE ENFORCED"

                                                                                                                        def test_convenience_function_integration(self):
                                                                                                                            """Test convenience function also blocks force flags."""
                                                                                                                            pass
                                                                                                                            with pytest.raises(DockerForceFlagViolation):
                                                                                                                                execute_docker_command(["docker", "container", "rm", "--force", "test"])

                                                                                                                                def test_thread_safety(self):
                                                                                                                                    """Test guardian is thread-safe under concurrent access."""
                                                                                                                                    guardian = DockerForceFlagGuardian()
                                                                                                                                    violations = []

                                                                                                                                    def violate_in_thread():
                                                                                                                                        try:
                                                                                                                                            guardian.validate_command("docker rm -f thread_container")
                                                                                                                                        except DockerForceFlagViolation as e:
                                                                                                                                            violations.append(e)

        # Run concurrent violations
                                                                                                                                            threads = []
                                                                                                                                            for i in range(5):
                                                                                                                                                thread = threading.Thread(target=violate_in_thread)
                                                                                                                                                threads.append(thread)
                                                                                                                                                thread.start()

                                                                                                                                                for thread in threads:
                                                                                                                                                    thread.join()

        # All should have been caught
                                                                                                                                                    assert len(violations) == 5
                                                                                                                                                    assert guardian.violation_count >= 5

                                                                                                                                                    def test_high_risk_command_detection(self):
                                                                                                                                                        """Test extra vigilance for high-risk commands."""
                                                                                                                                                        pass
                                                                                                                                                        guardian = DockerForceFlagGuardian()

                                                                                                                                                        high_risk_with_force = [
                                                                                                                                                        "docker rm -f container",
                                                                                                                                                        "docker rmi --force image", 
                                                                                                                                                        "docker container rm -f test",
                                                                                                                                                        "docker image rm --force test",
                                                                                                                                                        "docker volume rm -f vol",
                                                                                                                                                        "docker system prune --force",
                                                                                                                                                        ]

                                                                                                                                                        for cmd in high_risk_with_force:
                                                                                                                                                            with pytest.raises(DockerForceFlagViolation):
                                                                                                                                                                guardian.validate_command(cmd)

                                                                                                                                                                def test_edge_case_patterns(self):
                                                                                                                                                                    """Test detection of edge case force flag patterns."""
                                                                                                                                                                    guardian = DockerForceFlagGuardian()

                                                                                                                                                                    edge_cases = [
                                                                                                                                                                    "docker rm -rf container",  # Combined with other flags
                                                                                                                                                                    "docker rmi -f --no-prune image",  # Mixed flag positions
                                                                                                                                                                    "docker system prune --force=true",  # Assignment format
                                                                                                                                                                    "docker rm -f",  # Flag at end
                                                                                                                                                                    "docker --context=prod rm -f container",  # Global flags mixed
                                                                                                                                                                    ]

                                                                                                                                                                    for cmd in edge_cases:
                                                                                                                                                                        with pytest.raises(DockerForceFlagViolation) as exc_info:
                                                                                                                                                                            guardian.validate_command(cmd)

            # Ensure detailed violation information
                                                                                                                                                                            assert "Pattern" in str(exc_info.value) or "force" in str(exc_info.value).lower()

                                                                                                                                                                            def test_non_docker_commands_ignored(self):
                                                                                                                                                                                """Test non-Docker commands with -f are ignored."""
                                                                                                                                                                                pass
                                                                                                                                                                                guardian = DockerForceFlagGuardian()

                                                                                                                                                                                non_docker_commands = [
                                                                                                                                                                                "ls -la",
                                                                                                                                                                                "rm -rf /tmp/test",
                                                                                                                                                                                "grep -f pattern file.txt",
                                                                                                                                                                                "tail -f logfile.txt",
                                                                                                                                                                                "find . -name '*.txt'",
                                                                                                                                                                                ]

                                                                                                                                                                                for cmd in non_docker_commands:
                                                                                                                                                                                    try:
                                                                                                                                                                                        guardian.validate_command(cmd)  # Should not raise
                                                                                                                                                                                    except DockerForceFlagViolation:
                                                                                                                                                                                        pytest.fail(f"Non-Docker command incorrectly flagged: {cmd}")

                                                                                                                                                                                        def test_audit_report_generation(self):
                                                                                                                                                                                            """Test comprehensive audit report generation."""
                                                                                                                                                                                            guardian = DockerForceFlagGuardian()

        # Trigger some violations
                                                                                                                                                                                            for i in range(3):
                                                                                                                                                                                                with pytest.raises(DockerForceFlagViolation):
                                                                                                                                                                                                    guardian.validate_command(f"docker rm -f container{i}")

                                                                                                                                                                                                    report = guardian.audit_report()

                                                                                                                                                                                                    assert "total_violations" in report
                                                                                                                                                                                                    assert report["total_violations"] >= 3
                                                                                                                                                                                                    assert report["guardian_status"] == "ACTIVE - ZERO TOLERANCE ENFORCED"
                                                                                                                                                                                                    assert "business_impact_prevented" in report
                                                                                                                                                                                                    assert "3 Docker crashes" in report["business_impact_prevented"]

                                                                                                                                                                                                    def test_empty_and_malformed_commands(self):
                                                                                                                                                                                                        """Test guardian handles empty and malformed commands safely."""
                                                                                                                                                                                                        pass
                                                                                                                                                                                                        guardian = DockerForceFlagGuardian()

        # Should not raise exceptions
                                                                                                                                                                                                        safe_inputs = [
                                                                                                                                                                                                        "",
                                                                                                                                                                                                        None,
                                                                                                                                                                                                        "   ",
                                                                                                                                                                                                        123,  # Non-string input
                                                                                                                                                                                                        ]

                                                                                                                                                                                                        for cmd in safe_inputs:
                                                                                                                                                                                                            try:
                                                                                                                                                                                                                guardian.validate_command(cmd)
                                                                                                                                                                                                            except DockerForceFlagViolation:
                                                                                                                                                                                                                pytest.fail(f"Safe input incorrectly flagged: {repr(cmd)}")

                                                                                                                                                                                                                def test_business_impact_messaging(self):
                                                                                                                                                                                                                    """Test violation messages include business impact warnings."""
                                                                                                                                                                                                                    guardian = DockerForceFlagGuardian()

                                                                                                                                                                                                                    with pytest.raises(DockerForceFlagViolation) as exc_info:
                                                                                                                                                                                                                        guardian.validate_command("docker rm -f critical_container")

                                                                                                                                                                                                                        error_msg = str(exc_info.value)
                                                                                                                                                                                                                        assert "Business Impact" in error_msg
                                                                                                                                                                                                                        assert "4-8 hours downtime" in error_msg
                                                                                                                                                                                                                        assert "Docker Desktop" in error_msg

                                                                                                                                                                                                                        def test_no_actual_docker_commands_executed(self, mock_subprocess):
                                                                                                                                                                                                                            """Test that no actual Docker commands are executed during testing."""
                                                                                                                                                                                                                            pass
        # This test ensures we're not accidentally running real Docker commands'
                                                                                                                                                                                                                            guardian = DockerForceFlagGuardian()

                                                                                                                                                                                                                            try:
                                                                                                                                                                                                                                guardian.validate_command("docker rm -f test")
                                                                                                                                                                                                                            except DockerForceFlagViolation:
                                                                                                                                                                                                                                pass  # Expected

        # No subprocess should have been called
                                                                                                                                                                                                                                mock_subprocess.assert_not_called()


                                                                                                                                                                                                                                class TestGlobalValidationFunction:
                                                                                                                                                                                                                                    """Test the global validation convenience function."""

                                                                                                                                                                                                                                    def test_global_validate_function(self):
                                                                                                                                                                                                                                        """Test global validate_docker_command function."""
                                                                                                                                                                                                                                        with pytest.raises(DockerForceFlagViolation):
                                                                                                                                                                                                                                            validate_docker_command("docker rm -f container")

        # Safe command should not raise
                                                                                                                                                                                                                                            validate_docker_command("docker ps")

                                                                                                                                                                                                                                            def test_get_safe_alternative_function(self):
                                                                                                                                                                                                                                                """Test global get_safe_alternative function."""
                                                                                                                                                                                                                                                pass
                                                                                                                                                                                                                                                alt = get_safe_alternative("docker rm -f container")
                                                                                                                                                                                                                                                assert isinstance(alt, str)
                                                                                                                                                                                                                                                assert len(alt) > 0
                                                                                                                                                                                                                                                assert "docker stop" in alt


                                                                                                                                                                                                                                                class TestRealWorldScenarios:
                                                                                                                                                                                                                                                    """Test scenarios based on real-world Docker usage."""

                                                                                                                                                                                                                                                    def test_docker_compose_with_force(self):
                                                                                                                                                                                                                                                        """Test detection in docker-compose scenarios."""
                                                                                                                                                                                                                                                        guardian = DockerForceFlagGuardian()

        # docker-compose doesn't typically use -f for force, but test anyway'
                                                                                                                                                                                                                                                        with pytest.raises(DockerForceFlagViolation):
                                                                                                                                                                                                                                                            guardian.validate_command("docker-compose down --remove-orphans && docker rm -f $(docker ps -aq)")

                                                                                                                                                                                                                                                            def test_cleanup_script_patterns(self):
                                                                                                                                                                                                                                                                """Test detection of common cleanup script patterns."""
                                                                                                                                                                                                                                                                pass
                                                                                                                                                                                                                                                                guardian = DockerForceFlagGuardian()

                                                                                                                                                                                                                                                                dangerous_patterns = [
                                                                                                                                                                                                                                                                "docker system prune -f --all --volumes",
                                                                                                                                                                                                                                                                "docker container prune --force",
                                                                                                                                                                                                                                                                "docker image prune -f",
                                                                                                                                                                                                                                                                "docker volume prune --force",
                                                                                                                                                                                                                                                                "docker network prune -f",
                                                                                                                                                                                                                                                                ]

                                                                                                                                                                                                                                                                for pattern in dangerous_patterns:
                                                                                                                                                                                                                                                                    with pytest.raises(DockerForceFlagViolation):
                                                                                                                                                                                                                                                                        guardian.validate_command(pattern)

                                                                                                                                                                                                                                                                        def test_ci_cd_pipeline_patterns(self):
                                                                                                                                                                                                                                                                            """Test detection of CI/CD pipeline dangerous patterns."""
                                                                                                                                                                                                                                                                            guardian = DockerForceFlagGuardian()

                                                                                                                                                                                                                                                                            ci_dangerous = [
                                                                                                                                                                                                                                                                            "docker rmi -f $(docker images -q)",
                                                                                                                                                                                                                                                                            "docker rm -f $(docker ps -aq)",
                                                                                                                                                                                                                                                                            "docker system prune -f --volumes",
                                                                                                                                                                                                                                                                            ]

                                                                                                                                                                                                                                                                            for cmd in ci_dangerous:
                                                                                                                                                                                                                                                                                with pytest.raises(DockerForceFlagViolation):
                                                                                                                                                                                                                                                                                    guardian.validate_command(cmd)


                                                                                                                                                                                                                                                                                    if __name__ == "__main__":
                                                                                                                                                                                                                                                                                        pytest.main([__file__, "-v", "--tb=short"])
                                                                                                                                                                                                                                                                                        pass