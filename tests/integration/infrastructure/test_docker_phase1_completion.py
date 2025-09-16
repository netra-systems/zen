"""
Test Docker Phase 1 Completion Validation

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Validate infrastructure cleanup completion
- Value Impact: Clean Docker infrastructure enables fast development cycles
- Strategic Impact: Supports $500K+ ARR through stable development environment

CRITICAL: These tests should PASS after Phase 1 cleanup is complete.
They validate that the cleanup was successful and infrastructure is working.
"""

import pytest
import subprocess
import yaml
import time
from pathlib import Path
from test_framework.base_integration_test import BaseIntegrationTest


class TestDockerPhase1Completion(BaseIntegrationTest):
    """Test Docker infrastructure Phase 1 completion validation."""

    @pytest.mark.integration
    @pytest.mark.docker_infrastructure
    def test_alpine_dockerfiles_removed(self):
        """Validate Alpine Dockerfiles were successfully removed in Phase 1 cleanup."""
        project_root = Path(__file__).parent.parent.parent.parent
        dockerfiles_dir = project_root / "dockerfiles"

        # These files should NOT exist after Phase 1 cleanup
        alpine_files_to_remove = [
            "auth.alpine.Dockerfile",
            "backend.alpine.Dockerfile",
            "frontend.alpine.Dockerfile",
            "migration.alpine.Dockerfile",
            "auth.staging.alpine.Dockerfile",
            "backend.staging.alpine.Dockerfile",
            "frontend.staging.alpine.Dockerfile"
        ]

        remaining_alpine_files = []
        for alpine_file in alpine_files_to_remove:
            if (dockerfiles_dir / alpine_file).exists():
                remaining_alpine_files.append(alpine_file)

        assert len(remaining_alpine_files) == 0, (
            f"Phase 1 cleanup incomplete - Alpine Dockerfiles still exist: {remaining_alpine_files}"
        )

    @pytest.mark.integration
    @pytest.mark.docker_infrastructure
    def test_backup_directory_created(self):
        """Validate backup directory was created during Phase 1 cleanup."""
        project_root = Path(__file__).parent.parent.parent.parent
        backup_dir = project_root / "backup_dockerfiles_phase1_1082"

        assert backup_dir.exists(), "Backup directory should exist after Phase 1 cleanup"
        assert backup_dir.is_dir(), "Backup path should be a directory"

        # Verify backup contains the removed files
        expected_backup_files = [
            "auth.alpine.Dockerfile",
            "backend.alpine.Dockerfile",
            "frontend.alpine.Dockerfile",
            "migration.alpine.Dockerfile",
            "auth.staging.alpine.Dockerfile",
            "backend.staging.alpine.Dockerfile",
            "frontend.staging.alpine.Dockerfile"
        ]

        backup_files = [f.name for f in backup_dir.glob("*.Dockerfile")]

        for expected_file in expected_backup_files:
            assert expected_file in backup_files, (
                f"Backup directory missing expected file: {expected_file}"
            )

    @pytest.mark.integration
    @pytest.mark.docker_infrastructure
    def test_docker_compose_paths_fixed(self):
        """Validate docker-compose.alpine-dev.yml has correct Dockerfile paths."""
        project_root = Path(__file__).parent.parent.parent.parent
        compose_file = project_root / "docker" / "docker-compose.alpine-dev.yml"

        assert compose_file.exists(), "docker-compose.alpine-dev.yml should exist"

        with open(compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)

        services = compose_data.get('services', {})

        # Check that all Dockerfile paths are correct
        for service_name, service_config in services.items():
            build_config = service_config.get('build', {})
            if isinstance(build_config, dict):
                dockerfile = build_config.get('dockerfile')
                if dockerfile:
                    # Paths should now point to 'dockerfiles/' not 'docker/'
                    assert dockerfile.startswith('dockerfiles/'), (
                        f"Service {service_name} still has incorrect Dockerfile path: {dockerfile}"
                    )

                    # Verify the referenced Dockerfile exists
                    dockerfile_path = project_root / dockerfile
                    assert dockerfile_path.exists(), (
                        f"Service {service_name} references non-existent Dockerfile: {dockerfile}"
                    )

    @pytest.mark.integration
    @pytest.mark.docker_infrastructure
    def test_docker_compose_validation_passes(self):
        """Validate docker-compose config validation passes after path fixes."""
        project_root = Path(__file__).parent.parent.parent.parent
        compose_file = project_root / "docker" / "docker-compose.alpine-dev.yml"

        try:
            result = subprocess.run([
                "docker-compose",
                "-f", str(compose_file),
                "config"
            ], capture_output=True, text=True, timeout=30)

            assert result.returncode == 0, (
                f"docker-compose config validation failed. "
                f"Return code: {result.returncode}, stderr: {result.stderr}"
            )

        except subprocess.TimeoutExpired:
            assert False, "docker-compose config validation timed out - infrastructure still has problems"
        except FileNotFoundError:
            pytest.skip("docker-compose not available - cannot validate compose files")

    @pytest.mark.integration
    @pytest.mark.docker_infrastructure
    def test_only_production_dockerfiles_remain(self):
        """Validate only production/staging Dockerfiles remain after cleanup."""
        project_root = Path(__file__).parent.parent.parent.parent
        dockerfiles_dir = project_root / "dockerfiles"

        # These files should still exist (production/staging variants)
        expected_remaining_files = [
            "auth.Dockerfile",
            "auth.staging.Dockerfile",
            "backend.Dockerfile",
            "backend.staging.Dockerfile",
            "frontend.Dockerfile",
            "frontend.staging.Dockerfile",
            "load-tester.Dockerfile"
        ]

        for expected_file in expected_remaining_files:
            dockerfile_path = dockerfiles_dir / expected_file
            assert dockerfile_path.exists(), (
                f"Production Dockerfile should still exist: {expected_file}"
            )

    @pytest.mark.integration
    @pytest.mark.docker_infrastructure
    def test_docker_ssot_matrix_updated(self):
        """Validate DOCKER_SSOT_MATRIX.md reflects Phase 1 cleanup changes."""
        project_root = Path(__file__).parent.parent.parent.parent
        matrix_file = project_root / "dockerfiles" / "DOCKER_SSOT_MATRIX.md"

        if matrix_file.exists():
            with open(matrix_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Should not reference Alpine variants anymore
            alpine_references = [
                ".alpine.Dockerfile",
                "alpine-dev",
                "alpine-test"
            ]

            problematic_references = []
            for alpine_ref in alpine_references:
                if alpine_ref in content:
                    problematic_references.append(alpine_ref)

            assert len(problematic_references) == 0, (
                f"DOCKER_SSOT_MATRIX.md still references Alpine variants: {problematic_references}"
            )


class TestDockerInfrastructurePerformance(BaseIntegrationTest):
    """Test Docker infrastructure performance after Phase 1 cleanup."""

    @pytest.mark.integration
    @pytest.mark.performance
    def test_docker_container_startup_improved(self):
        """Validate Docker container startup performance after cleanup."""
        project_root = Path(__file__).parent.parent.parent.parent

        # Use a working compose file (not the broken alpine-dev one)
        compose_file = project_root / "docker" / "docker-compose.yml"

        if not compose_file.exists():
            pytest.skip("docker-compose.yml not found")

        start_time = time.time()
        try:
            # Start just database services for quick test
            result = subprocess.run([
                "docker-compose",
                "-f", str(compose_file),
                "up", "-d", "dev-postgres", "dev-redis"
            ], capture_output=True, text=True, timeout=45)

            startup_time = time.time() - start_time

            # Cleanup regardless of success/failure
            subprocess.run([
                "docker-compose",
                "-f", str(compose_file),
                "down"
            ], capture_output=True, text=True, timeout=30)

            assert result.returncode == 0, (
                f"Docker container startup failed in {startup_time:.2f}s. "
                f"Error: {result.stderr}"
            )

            # After cleanup, startup should be faster than 30s
            assert startup_time < 30.0, (
                f"Docker container startup still slow: {startup_time:.2f}s (should be <30s)"
            )

        except subprocess.TimeoutExpired:
            assert False, "Docker container startup still times out after Phase 1 cleanup"
        except FileNotFoundError:
            pytest.skip("docker-compose not available - cannot test container startup")

    @pytest.mark.integration
    @pytest.mark.performance
    def test_test_discovery_performance_improved(self):
        """Validate test discovery performance after Docker infrastructure fixes."""
        start_time = time.time()

        try:
            # Test discovery should be fast after infrastructure cleanup
            result = subprocess.run([
                "python", "-m", "pytest",
                "--collect-only", "--quiet", "--maxfail=5",
                "tests/unit/"  # Use specific path to avoid discovery issues
            ], capture_output=True, text=True, timeout=15)

            discovery_time = time.time() - start_time

            assert result.returncode == 0, (
                f"Test discovery failed in {discovery_time:.2f}s after Phase 1 cleanup. "
                f"Error: {result.stderr}"
            )

            # After cleanup, discovery should be under 5s for good TDD workflow
            assert discovery_time < 5.0, (
                f"Test discovery still slow: {discovery_time:.2f}s (should be <5s for TDD)"
            )

        except subprocess.TimeoutExpired:
            assert False, "Test discovery still times out after Phase 1 cleanup"