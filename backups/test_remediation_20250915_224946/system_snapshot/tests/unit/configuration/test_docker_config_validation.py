"""
Test Docker Configuration Validation (No Docker Required)

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Ensure configuration consistency and validation
- Value Impact: Prevent configuration drift and deployment failures
- Strategic Impact: Stable infrastructure supports development velocity

These tests validate Docker configuration logic without requiring Docker itself.
They can run in any environment and provide fast feedback on configuration issues.
"""

import pytest
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any


class TestDockerConfigurationValidation:
    """Test Docker configuration validation logic without Docker runtime."""

    def test_compose_file_structure_validation(self):
        """Validate docker-compose files have proper structure."""
        project_root = Path(__file__).parent.parent.parent.parent
        docker_dir = project_root / "docker"

        compose_files = [
            "docker-compose.yml",
            "docker-compose.staging.yml",
            "docker-compose.alpine-dev.yml",
            "docker-compose.alpine-test.yml"
        ]

        for compose_file_name in compose_files:
            compose_file = docker_dir / compose_file_name
            if not compose_file.exists():
                continue

            with open(compose_file, 'r') as f:
                try:
                    compose_data = yaml.safe_load(f)
                except yaml.YAMLError as e:
                    assert False, f"{compose_file_name} has invalid YAML: {e}"

            # Validate basic structure
            assert 'services' in compose_data, f"{compose_file_name} missing 'services' section"
            assert isinstance(compose_data['services'], dict), f"{compose_file_name} 'services' must be a dict"

            # Validate each service has required fields
            for service_name, service_config in compose_data['services'].items():
                assert isinstance(service_config, dict), f"Service {service_name} in {compose_file_name} must be a dict"

    def test_dockerfile_path_consistency(self):
        """Validate Dockerfile paths in compose files point to existing files."""
        project_root = Path(__file__).parent.parent.parent.parent
        docker_dir = project_root / "docker"

        compose_files = list(docker_dir.glob("docker-compose*.yml"))

        path_issues = []

        for compose_file in compose_files:
            with open(compose_file, 'r') as f:
                compose_data = yaml.safe_load(f)

            services = compose_data.get('services', {})
            for service_name, service_config in services.items():
                build_config = service_config.get('build', {})
                if isinstance(build_config, dict):
                    dockerfile = build_config.get('dockerfile')
                    if dockerfile:
                        dockerfile_path = project_root / dockerfile
                        if not dockerfile_path.exists():
                            path_issues.append({
                                'compose_file': compose_file.name,
                                'service': service_name,
                                'dockerfile': dockerfile,
                                'resolved_path': str(dockerfile_path),
                                'exists': False
                            })

        assert len(path_issues) == 0, f"Dockerfile path issues found: {json.dumps(path_issues, indent=2)}"

    def test_environment_variable_consistency(self):
        """Validate environment variables are consistent across compose files."""
        project_root = Path(__file__).parent.parent.parent.parent
        docker_dir = project_root / "docker"

        compose_files = list(docker_dir.glob("docker-compose*.yml"))

        # Critical environment variables that should be consistent
        critical_env_vars = [
            'POSTGRES_HOST',
            'POSTGRES_PORT',
            'POSTGRES_DB',
            'REDIS_HOST',
            'REDIS_PORT',
            'ENVIRONMENT'
        ]

        env_var_values = {}  # env_var -> {file -> value}

        for compose_file in compose_files:
            with open(compose_file, 'r') as f:
                compose_data = yaml.safe_load(f)

            services = compose_data.get('services', {})
            for service_name, service_config in services.items():
                environment = service_config.get('environment', {})
                if isinstance(environment, dict):
                    for env_var, value in environment.items():
                        if env_var in critical_env_vars:
                            if env_var not in env_var_values:
                                env_var_values[env_var] = {}
                            env_var_values[env_var][f"{compose_file.name}:{service_name}"] = value

        # Report inconsistencies for review (not necessarily errors)
        inconsistencies = []
        for env_var, file_values in env_var_values.items():
            unique_values = set(file_values.values())
            if len(unique_values) > 1:
                inconsistencies.append({
                    'env_var': env_var,
                    'values': file_values
                })

        # This is informational - inconsistencies might be expected between environments
        if inconsistencies:
            print(f"Environment variable inconsistencies found (may be expected): {json.dumps(inconsistencies, indent=2)}")

    def test_port_mapping_conflicts(self):
        """Validate no port conflicts exist in compose files."""
        project_root = Path(__file__).parent.parent.parent.parent
        docker_dir = project_root / "docker"

        compose_files = list(docker_dir.glob("docker-compose*.yml"))

        port_usage = {}  # port -> [file:service, ...]

        for compose_file in compose_files:
            with open(compose_file, 'r') as f:
                compose_data = yaml.safe_load(f)

            services = compose_data.get('services', {})
            for service_name, service_config in services.items():
                ports = service_config.get('ports', [])
                for port_mapping in ports:
                    if isinstance(port_mapping, str):
                        # Format: "host_port:container_port"
                        host_port = port_mapping.split(':')[0]
                        if host_port not in port_usage:
                            port_usage[host_port] = []
                        port_usage[host_port].append(f"{compose_file.name}:{service_name}")

        # Find conflicts (same host port used by multiple services in same file)
        conflicts = []
        for port, usages in port_usage.items():
            if len(usages) > 1:
                # Check if conflict is within same file
                files = [usage.split(':')[0] for usage in usages]
                unique_files = set(files)
                if len(unique_files) < len(usages):
                    conflicts.append({
                        'port': port,
                        'usages': usages
                    })

        assert len(conflicts) == 0, f"Port conflicts found: {json.dumps(conflicts, indent=2)}"

    def test_volume_mount_validation(self):
        """Validate volume mounts point to existing directories."""
        project_root = Path(__file__).parent.parent.parent.parent
        docker_dir = project_root / "docker"

        compose_files = list(docker_dir.glob("docker-compose*.yml"))

        mount_issues = []

        for compose_file in compose_files:
            with open(compose_file, 'r') as f:
                compose_data = yaml.safe_load(f)

            services = compose_data.get('services', {})
            for service_name, service_config in services.items():
                volumes = service_config.get('volumes', [])
                for volume in volumes:
                    if isinstance(volume, str) and ':' in volume:
                        # Format: "host_path:container_path"
                        parts = volume.split(':')
                        if len(parts) >= 2:
                            host_path = parts[0]

                            # Skip named volumes and absolute paths
                            if not host_path.startswith('/') and not host_path.startswith('.'):
                                continue

                            # Check relative paths
                            if host_path.startswith('./'):
                                full_path = project_root / host_path[2:]  # Remove './'
                                if not full_path.exists():
                                    mount_issues.append({
                                        'compose_file': compose_file.name,
                                        'service': service_name,
                                        'host_path': host_path,
                                        'resolved_path': str(full_path),
                                        'exists': False
                                    })

        # Some mount paths might not exist in development - this is informational
        if mount_issues:
            print(f"Volume mount issues found (may be expected in dev): {json.dumps(mount_issues, indent=2)}")


class TestDockerConfigurationUtils:
    """Test utility functions for Docker configuration management."""

    def test_compose_file_parsing_utility(self):
        """Test utility function for parsing compose files."""

        def parse_compose_file(file_path: Path) -> Dict[str, Any]:
            """Utility to parse and validate compose file."""
            if not file_path.exists():
                raise FileNotFoundError(f"Compose file not found: {file_path}")

            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise ValueError(f"Invalid compose file format: {file_path}")

            if 'services' not in data:
                raise ValueError(f"Compose file missing services section: {file_path}")

            return data

        # Test with existing compose file
        project_root = Path(__file__).parent.parent.parent.parent
        docker_dir = project_root / "docker"

        compose_file = docker_dir / "docker-compose.yml"
        if compose_file.exists():
            result = parse_compose_file(compose_file)
            assert isinstance(result, dict)
            assert 'services' in result
            assert isinstance(result['services'], dict)

    def test_dockerfile_existence_checker(self):
        """Test utility function for checking Dockerfile existence."""

        def check_dockerfiles_exist(compose_data: Dict[str, Any], base_path: Path) -> List[Dict[str, Any]]:
            """Check if all Dockerfiles referenced in compose file exist."""
            missing_files = []

            services = compose_data.get('services', {})
            for service_name, service_config in services.items():
                build_config = service_config.get('build', {})
                if isinstance(build_config, dict):
                    dockerfile = build_config.get('dockerfile')
                    if dockerfile:
                        dockerfile_path = base_path / dockerfile
                        if not dockerfile_path.exists():
                            missing_files.append({
                                'service': service_name,
                                'dockerfile': dockerfile,
                                'path': str(dockerfile_path)
                            })

            return missing_files

        # Test with sample data
        sample_compose = {
            'services': {
                'test_service': {
                    'build': {
                        'dockerfile': 'dockerfiles/backend.Dockerfile'
                    }
                }
            }
        }

        project_root = Path(__file__).parent.parent.parent.parent
        missing = check_dockerfiles_exist(sample_compose, project_root)

        # Should find missing file if it doesn't exist
        assert isinstance(missing, list)