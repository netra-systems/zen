"""
Test Docker Phase 1 Broken State Validation

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Ensure stable development environment
- Value Impact: Broken Docker infrastructure blocks development velocity
- Strategic Impact: Core platform stability for $500K+ ARR protection

CRITICAL: These tests MUST fail initially to prove current broken state.
After Phase 1 cleanup, these tests should be updated to validate fixed state.
"""

import pytest
import subprocess
import yaml
import time
from pathlib import Path
from test_framework.base_integration_test import BaseIntegrationTest


class TestDockerPhase1BrokenState(BaseIntegrationTest):
    """Test Docker infrastructure Phase 1 broken state."""

    @pytest.mark.integration
    @pytest.mark.docker_infrastructure
    def test_alpine_dockerfiles_still_exist(self):
        """EXPECTED TO FAIL: Alpine Dockerfiles should not exist after Phase 1 cleanup."""
        project_root = Path(__file__).parent.parent.parent.parent
        dockerfiles_dir = project_root / "dockerfiles"

        # These files should NOT exist after Phase 1 cleanup
        alpine_files = [
            "auth.alpine.Dockerfile",
            "backend.alpine.Dockerfile",
            "frontend.alpine.Dockerfile",
            "migration.alpine.Dockerfile",
            "auth.staging.alpine.Dockerfile",
            "backend.staging.alpine.Dockerfile",
            "frontend.staging.alpine.Dockerfile"
        ]

        existing_alpine_files = []
        for alpine_file in alpine_files:
            if (dockerfiles_dir / alpine_file).exists():
                existing_alpine_files.append(alpine_file)

        # This assertion SHOULD FAIL initially - proving cleanup never happened
        assert len(existing_alpine_files) == 0, (
            f"Phase 1 cleanup incomplete - Alpine Dockerfiles still exist: {existing_alpine_files}"
        )

    @pytest.mark.integration
    @pytest.mark.docker_infrastructure
    def test_docker_compose_alpine_dev_broken_paths(self):
        """EXPECTED TO FAIL: docker-compose.alpine-dev.yml has broken path references."""
        project_root = Path(__file__).parent.parent.parent.parent
        compose_file = project_root / "docker" / "docker-compose.alpine-dev.yml"

        assert compose_file.exists(), "docker-compose.alpine-dev.yml should exist"

        with open(compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)

        services = compose_data.get('services', {})

        # Check for broken path references
        broken_paths = []
        for service_name, service_config in services.items():
            build_config = service_config.get('build', {})
            if isinstance(build_config, dict):
                dockerfile = build_config.get('dockerfile')
                if dockerfile and dockerfile.startswith('docker/'):
                    # These are broken paths - should be 'dockerfiles/'
                    dockerfile_path = project_root / dockerfile
                    if not dockerfile_path.exists():
                        broken_paths.append({
                            'service': service_name,
                            'dockerfile': dockerfile,
                            'exists': False
                        })

        # This assertion SHOULD FAIL initially - proving broken paths
        assert len(broken_paths) == 0, (
            f"docker-compose.alpine-dev.yml has broken Dockerfile paths: {broken_paths}"
        )

    @pytest.mark.integration
    @pytest.mark.docker_infrastructure
    def test_docker_compose_validation_fails(self):
        """EXPECTED TO FAIL: docker-compose config validation should fail due to broken paths."""
        project_root = Path(__file__).parent.parent.parent.parent
        compose_file = project_root / "docker" / "docker-compose.alpine-dev.yml"

        try:
            # This should fail due to broken Dockerfile paths
            result = subprocess.run([
                "docker-compose",
                "-f", str(compose_file),
                "config"
            ], capture_output=True, text=True, timeout=30)

            # If validation passes, there's a problem with our test
            validation_passed = result.returncode == 0

            # This assertion SHOULD FAIL initially
            assert validation_passed, (
                f"docker-compose config validation should fail due to broken paths. "
                f"Return code: {result.returncode}, stderr: {result.stderr}"
            )

        except subprocess.TimeoutExpired:
            # Expected - validation hangs due to infrastructure issues
            assert False, "docker-compose config validation timed out - infrastructure problems confirmed"
        except FileNotFoundError:
            pytest.skip("docker-compose not available - cannot validate compose files")


class TestDockerTimeoutProblems(BaseIntegrationTest):
    """Test Docker-related timeout issues in test infrastructure."""

    @pytest.mark.integration
    @pytest.mark.performance
    def test_docker_container_startup_timeout(self):
        """EXPECTED TO FAIL: Docker container startup should be fast (<30s)."""
        project_root = Path(__file__).parent.parent.parent.parent
        compose_file = project_root / "docker" / "docker-compose.alpine-dev.yml"

        if not compose_file.exists():
            pytest.skip("docker-compose.alpine-dev.yml not found")

        start_time = time.time()
        try:
            # Try to start just the database services (should be quick)
            result = subprocess.run([
                "docker-compose",
                "-f", str(compose_file),
                "up", "-d", "dev-postgres", "dev-redis"
            ], capture_output=True, text=True, timeout=30)

            startup_time = time.time() - start_time
            startup_success = result.returncode == 0

            # Cleanup
            subprocess.run([
                "docker-compose",
                "-f", str(compose_file),
                "down"
            ], capture_output=True, text=True, timeout=30)

            # This assertion SHOULD FAIL if infrastructure has problems
            assert startup_success, (
                f"Docker container startup failed in {startup_time:.2f}s. "
                f"Error: {result.stderr}"
            )

            # This assertion SHOULD FAIL if startup is too slow
            assert startup_time < 30.0, (
                f"Docker container startup too slow: {startup_time:.2f}s (should be <30s)"
            )

        except subprocess.TimeoutExpired:
            # Expected failure - proves timeout problems
            assert False, "Docker container startup timed out after 30s - infrastructure problems confirmed"
        except FileNotFoundError:
            pytest.skip("docker-compose not available - cannot test container startup")


    @pytest.mark.integration
    @pytest.mark.performance
    def test_test_discovery_timeout_reproduction(self):
        """Reproduce the 10s timeout issue from business_workflow_validation_test.py"""
        import time

        start_time = time.time()
        try:
            # This reproduces the exact command that times out
            result = subprocess.run([
                "python", "-m", "pytest",
                "--collect-only", "--quiet", "--maxfail=5",
                "-k", "test_user_execution"
            ], capture_output=True, text=True, timeout=10)

            discovery_time = time.time() - start_time
            discovery_success = result.returncode == 0

            # This assertion documents the current timeout problem
            if not discovery_success:
                assert False, (
                    f"Test discovery failed in {discovery_time:.2f}s - reproduces Issue #1082 timeout. "
                    f"Error: {result.stderr}"
                )

            # This assertion SHOULD FAIL if discovery is too slow
            assert discovery_time < 5.0, (
                f"Test discovery too slow: {discovery_time:.2f}s (should be <5s for TDD workflow)"
            )

        except subprocess.TimeoutExpired:
            # Expected failure - proves the 10s timeout issue
            assert False, "Test discovery timed out after 10s - reproduces Issue #1082 exactly"