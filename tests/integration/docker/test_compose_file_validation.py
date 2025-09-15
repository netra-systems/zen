"""
Integration tests for docker-compose file validation - NO DOCKER BUILDS REQUIRED

Purpose: Validate docker-compose configurations cause Alpine build integration issues
Issue: #1082 - Docker Alpine build infrastructure failure
Approach: YAML parsing and service integration validation only, no container builds

MISSION CRITICAL: These tests must detect docker-compose integration issues
WITHOUT requiring Docker to be running or functional.

Business Impact: $500K+ ARR Golden Path depends on working Docker infrastructure
Critical Context: Issue #1082 escalated P2→P1 due to mission-critical test blocking

Test Strategy: These tests are designed to FAIL initially to prove they detect real issues
"""
import pytest
import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Union
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestDockerComposeFileValidation(SSotBaseTestCase):
    """Integration tests for docker-compose file validation - YAML PARSING ONLY

    These tests validate docker-compose file configurations and service
    integrations that can cause Alpine build failures and cache key issues.
    """

    def setup_method(self, method):
        """Setup test environment - locate docker-compose files"""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.docker_dir = self.project_root / 'docker'

        self.compose_files = {
            'docker-compose.yml': 'production',
            'docker-compose.staging.yml': 'staging',
            'docker-compose.alpine-test.yml': 'alpine-test',
            'docker-compose.alpine-dev.yml': 'alpine-dev',
            'docker-compose.staging.alpine.yml': 'staging-alpine',
            'docker-compose.minimal-test.yml': 'minimal-test'
        }

        self.logger.info(f'Testing docker-compose files in: {self.docker_dir}')

    def test_compose_files_exist_and_parseable(self):
        """
        Test that all docker-compose files exist and contain valid YAML

        Issue: #1082 - Missing or corrupted compose files cause integration failures
        Difficulty: Low (5 minutes)
        Expected: FAIL initially - Some compose files may be missing or corrupted
        """
        compose_file_issues = []

        for compose_filename, environment in self.compose_files.items():
            compose_path = self.docker_dir / compose_filename

            if not compose_path.exists():
                compose_file_issues.append(f"Missing compose file: {compose_path}")
                continue

            try:
                with open(compose_path, 'r') as f:
                    compose_content = yaml.safe_load(f)

                if not isinstance(compose_content, dict):
                    compose_file_issues.append(
                        f"{compose_filename} - Invalid YAML structure: not a dictionary"
                    )
                    continue

                # Validate basic compose file structure
                if 'services' not in compose_content:
                    compose_file_issues.append(
                        f"{compose_filename} - Missing 'services' section"
                    )

                # Check for version specification
                if 'version' not in compose_content:
                    compose_file_issues.append(
                        f"{compose_filename} - Missing 'version' specification"
                    )

            except yaml.YAMLError as e:
                compose_file_issues.append(f"{compose_filename} - YAML parsing error: {str(e)}")
            except Exception as e:
                compose_file_issues.append(f"{compose_filename} - File reading error: {str(e)}")

        assert not compose_file_issues, \
            f"Docker compose file validation failures: {json.dumps(compose_file_issues, indent=2)}. " \
            f"Missing or corrupted compose files cause Alpine build integration failures."

    def test_alpine_compose_service_dockerfile_references(self):
        """
        Test that Alpine compose files reference existing Alpine Dockerfiles

        Issue: #1082 - Compose files referencing non-existent or wrong Dockerfiles
        Difficulty: Medium (10 minutes)
        Expected: FAIL initially - Dockerfile references may be incorrect
        """
        dockerfile_reference_issues = []

        alpine_compose_files = {
            name: env for name, env in self.compose_files.items()
            if 'alpine' in name.lower()
        }

        dockerfiles_dir = self.project_root / 'dockerfiles'

        for compose_filename, environment in alpine_compose_files.items():
            compose_path = self.docker_dir / compose_filename

            if not compose_path.exists():
                continue

            try:
                with open(compose_path, 'r') as f:
                    compose_content = yaml.safe_load(f)

                services = compose_content.get('services', {})

                for service_name, service_config in services.items():
                    if not isinstance(service_config, dict):
                        continue

                    # Check for dockerfile or build context
                    dockerfile_ref = None
                    build_config = service_config.get('build')

                    if isinstance(build_config, str):
                        # Simple build context
                        dockerfile_ref = 'Dockerfile'
                    elif isinstance(build_config, dict):
                        dockerfile_ref = build_config.get('dockerfile')
                        build_context = build_config.get('context', '.')

                    if dockerfile_ref:
                        # Resolve Dockerfile path
                        if dockerfile_ref.startswith('../dockerfiles/'):
                            dockerfile_path = dockerfiles_dir / dockerfile_ref.replace('../dockerfiles/', '')
                        elif dockerfile_ref.startswith('./dockerfiles/'):
                            dockerfile_path = dockerfiles_dir / dockerfile_ref.replace('./dockerfiles/', '')
                        else:
                            dockerfile_path = dockerfiles_dir / dockerfile_ref

                        if not dockerfile_path.exists():
                            dockerfile_reference_issues.append(
                                f"{compose_filename} - Service '{service_name}' references missing Dockerfile: "
                                f"{dockerfile_ref} -> {dockerfile_path}"
                            )

                        # For Alpine environments, verify Dockerfile is actually Alpine-based
                        if dockerfile_path.exists() and 'alpine' in environment:
                            try:
                                with open(dockerfile_path, 'r') as df:
                                    dockerfile_content = df.read().lower()

                                if 'alpine' not in dockerfile_content:
                                    dockerfile_reference_issues.append(
                                        f"{compose_filename} - Service '{service_name}' in Alpine environment "
                                        f"references non-Alpine Dockerfile: {dockerfile_ref}"
                                    )
                            except Exception as e:
                                dockerfile_reference_issues.append(
                                    f"{compose_filename} - Failed to validate Dockerfile {dockerfile_ref}: {str(e)}"
                                )

            except Exception as e:
                dockerfile_reference_issues.append(f"Failed to parse {compose_filename}: {str(e)}")

        assert not dockerfile_reference_issues, \
            f"Alpine compose Dockerfile reference validation failures: " \
            f"{json.dumps(dockerfile_reference_issues, indent=2)}. " \
            f"Incorrect Dockerfile references cause Alpine build integration failures."

    def test_compose_service_port_conflicts(self):
        """
        Test for port conflicts between compose files that cause integration issues

        Issue: #1082 - Port conflicts prevent proper service startup during builds
        Difficulty: Medium (15 minutes)
        Expected: FAIL initially - Port conflicts between different compose environments
        """
        port_conflict_issues = []

        all_ports_by_file = {}

        for compose_filename, environment in self.compose_files.items():
            compose_path = self.docker_dir / compose_filename

            if not compose_path.exists():
                continue

            try:
                with open(compose_path, 'r') as f:
                    compose_content = yaml.safe_load(f)

                services = compose_content.get('services', {})
                file_ports = {}

                for service_name, service_config in services.items():
                    if not isinstance(service_config, dict):
                        continue

                    service_ports = []
                    ports_config = service_config.get('ports', [])

                    for port_mapping in ports_config:
                        if isinstance(port_mapping, str):
                            if ':' in port_mapping:
                                host_port = port_mapping.split(':')[0]
                                try:
                                    host_port_int = int(host_port)
                                    service_ports.append(host_port_int)
                                except ValueError:
                                    port_conflict_issues.append(
                                        f"{compose_filename} - Service '{service_name}' has invalid port: {port_mapping}"
                                    )
                        elif isinstance(port_mapping, dict):
                            published_port = port_mapping.get('published')
                            if published_port:
                                try:
                                    service_ports.append(int(published_port))
                                except ValueError:
                                    port_conflict_issues.append(
                                        f"{compose_filename} - Service '{service_name}' has invalid port: {published_port}"
                                    )

                    if service_ports:
                        file_ports[service_name] = service_ports

                all_ports_by_file[compose_filename] = file_ports

            except Exception as e:
                port_conflict_issues.append(f"Failed to parse ports in {compose_filename}: {str(e)}")

        # Check for conflicts between files
        port_usage = {}  # port -> [(file, service), ...]

        for compose_file, services_ports in all_ports_by_file.items():
            for service_name, ports in services_ports.items():
                for port in ports:
                    if port not in port_usage:
                        port_usage[port] = []
                    port_usage[port].append((compose_file, service_name))

        # Report conflicts
        for port, usages in port_usage.items():
            if len(usages) > 1:
                # Filter out conflicts between same base environment (e.g., staging vs staging.alpine)
                unique_envs = set()
                for compose_file, service in usages:
                    base_env = compose_file.split('.')[0]  # docker-compose -> docker-compose
                    unique_envs.add(base_env)

                if len(unique_envs) > 1:
                    usage_details = [f"{compose_file}:{service}" for compose_file, service in usages]
                    port_conflict_issues.append(
                        f"Port {port} conflict between environments: {usage_details}"
                    )

        assert not port_conflict_issues, \
            f"Docker compose port conflict validation failures: " \
            f"{json.dumps(port_conflict_issues, indent=2)}. " \
            f"Port conflicts cause service startup failures during Alpine builds."

    def test_compose_volume_mount_consistency(self):
        """
        Test volume mount consistency across compose files

        Issue: #1082 - Inconsistent volume mounts cause cache key computation issues
        Difficulty: Medium (15 minutes)
        Expected: FAIL initially - Volume mount inconsistencies between environments
        """
        volume_mount_issues = []

        all_volumes_by_file = {}

        for compose_filename, environment in self.compose_files.items():
            compose_path = self.docker_dir / compose_filename

            if not compose_path.exists():
                continue

            try:
                with open(compose_path, 'r') as f:
                    compose_content = yaml.safe_load(f)

                services = compose_content.get('services', {})
                file_volumes = {}

                for service_name, service_config in services.items():
                    if not isinstance(service_config, dict):
                        continue

                    volumes_config = service_config.get('volumes', [])
                    service_volumes = []

                    for volume_mapping in volumes_config:
                        if isinstance(volume_mapping, str):
                            service_volumes.append(volume_mapping)
                        elif isinstance(volume_mapping, dict):
                            source = volume_mapping.get('source', '')
                            target = volume_mapping.get('target', '')
                            if source and target:
                                service_volumes.append(f"{source}:{target}")

                    if service_volumes:
                        file_volumes[service_name] = service_volumes

                all_volumes_by_file[compose_filename] = file_volumes

            except Exception as e:
                volume_mount_issues.append(f"Failed to parse volumes in {compose_filename}: {str(e)}")

        # Analyze volume consistency patterns
        service_volume_patterns = {}  # service_type -> {file -> volumes}

        for compose_file, services_volumes in all_volumes_by_file.items():
            for service_name, volumes in services_volumes.items():
                # Normalize service name (backend-dev -> backend)
                service_type = service_name.split('-')[0]

                if service_type not in service_volume_patterns:
                    service_volume_patterns[service_type] = {}

                service_volume_patterns[service_type][compose_file] = volumes

        # Check for inconsistencies
        for service_type, file_volumes in service_volume_patterns.items():
            if len(file_volumes) <= 1:
                continue

            # Compare volume patterns across files
            volume_sets = {}
            for compose_file, volumes in file_volumes.items():
                # Normalize volumes for comparison (remove host-specific paths)
                normalized_volumes = []
                for vol in volumes:
                    if ':' in vol:
                        parts = vol.split(':')
                        if len(parts) >= 2:
                            # Focus on container paths for consistency
                            container_path = parts[1]
                            normalized_volumes.append(container_path)

                volume_sets[compose_file] = set(normalized_volumes)

            # Find inconsistencies
            all_container_paths = set()
            for paths in volume_sets.values():
                all_container_paths.update(paths)

            for container_path in all_container_paths:
                files_with_path = [f for f, paths in volume_sets.items() if container_path in paths]
                files_without_path = [f for f, paths in volume_sets.items() if container_path not in paths]

                if files_without_path and len(files_with_path) > 1:
                    volume_mount_issues.append(
                        f"Service '{service_type}' volume '{container_path}' inconsistent: "
                        f"Present in {files_with_path}, Missing in {files_without_path}"
                    )

        assert not volume_mount_issues, \
            f"Docker compose volume mount validation failures: " \
            f"{json.dumps(volume_mount_issues, indent=2)}. " \
            f"Volume mount inconsistencies cause cache key computation failures in Alpine builds."

    def test_compose_environment_variable_validation(self):
        """
        Test environment variable configurations in compose files

        Issue: #1082 - Environment variable issues can cause Alpine build failures
        Difficulty: High (20 minutes)
        Expected: FAIL initially - Environment variable configuration problems
        """
        env_var_issues = []

        critical_env_vars = {
            'backend': ['DATABASE_URL', 'REDIS_URL', 'JWT_SECRET_KEY'],
            'auth': ['DATABASE_URL', 'JWT_SECRET_KEY', 'OAUTH_CLIENT_ID'],
            'frontend': ['NEXT_PUBLIC_API_URL', 'NEXT_PUBLIC_AUTH_URL']
        }

        for compose_filename, environment in self.compose_files.items():
            compose_path = self.docker_dir / compose_filename

            if not compose_path.exists():
                continue

            try:
                with open(compose_path, 'r') as f:
                    compose_content = yaml.safe_load(f)

                services = compose_content.get('services', {})

                for service_name, service_config in services.items():
                    if not isinstance(service_config, dict):
                        continue

                    # Determine service type
                    service_type = None
                    for svc_type in critical_env_vars.keys():
                        if svc_type in service_name.lower():
                            service_type = svc_type
                            break

                    if not service_type:
                        continue

                    # Check environment variables
                    env_config = service_config.get('environment', {})
                    env_file = service_config.get('env_file', [])

                    # Convert env_config to dict if it's a list
                    if isinstance(env_config, list):
                        env_dict = {}
                        for env_item in env_config:
                            if '=' in str(env_item):
                                key, value = str(env_item).split('=', 1)
                                env_dict[key] = value
                        env_config = env_dict

                    # Check for required environment variables
                    required_vars = critical_env_vars[service_type]
                    missing_vars = []

                    for required_var in required_vars:
                        if required_var not in env_config:
                            # Check if it might be in env_file (we can't validate file contents here)
                            if not env_file:
                                missing_vars.append(required_var)

                    if missing_vars:
                        env_var_issues.append(
                            f"{compose_filename} - Service '{service_name}' missing environment variables: "
                            f"{missing_vars}"
                        )

                    # Check for insecure environment variable patterns
                    insecure_patterns = []
                    for var_name, var_value in env_config.items():
                        if isinstance(var_value, str):
                            # Check for hardcoded secrets
                            if 'secret' in var_name.lower() or 'key' in var_name.lower() or 'password' in var_name.lower():
                                if len(var_value) > 0 and var_value not in ['${SECRET}', '${KEY}', '${PASSWORD}']:
                                    # Check if it looks like a hardcoded value rather than a reference
                                    if not var_value.startswith('${') and len(var_value) < 100:
                                        insecure_patterns.append(f"{var_name}={var_value[:20]}...")

                    if insecure_patterns:
                        env_var_issues.append(
                            f"{compose_filename} - Service '{service_name}' has potentially hardcoded secrets: "
                            f"{insecure_patterns}"
                        )

            except Exception as e:
                env_var_issues.append(f"Failed to parse environment variables in {compose_filename}: {str(e)}")

        assert not env_var_issues, \
            f"Docker compose environment variable validation failures: " \
            f"{json.dumps(env_var_issues, indent=2)}. " \
            f"Environment variable issues cause Alpine build and runtime failures."

    def test_compose_network_configuration_consistency(self):
        """
        Test network configuration consistency across compose files

        Issue: #1082 - Network configuration issues can cause integration failures
        Difficulty: Medium (10 minutes)
        Expected: FAIL initially - Network configuration inconsistencies
        """
        network_config_issues = []

        network_configs_by_file = {}

        for compose_filename, environment in self.compose_files.items():
            compose_path = self.docker_dir / compose_filename

            if not compose_path.exists():
                continue

            try:
                with open(compose_path, 'r') as f:
                    compose_content = yaml.safe_load(f)

                # Check networks section
                networks = compose_content.get('networks', {})
                services = compose_content.get('services', {})

                file_network_info = {
                    'defined_networks': list(networks.keys()),
                    'service_networks': {}
                }

                # Check service network usage
                for service_name, service_config in services.items():
                    if not isinstance(service_config, dict):
                        continue

                    service_networks = []
                    networks_config = service_config.get('networks', [])

                    if isinstance(networks_config, list):
                        service_networks.extend(networks_config)
                    elif isinstance(networks_config, dict):
                        service_networks.extend(networks_config.keys())

                    file_network_info['service_networks'][service_name] = service_networks

                network_configs_by_file[compose_filename] = file_network_info

            except Exception as e:
                network_config_issues.append(f"Failed to parse network config in {compose_filename}: {str(e)}")

        # Analyze network consistency
        for compose_file, network_info in network_configs_by_file.items():
            # Check if services reference undefined networks
            defined_networks = set(network_info['defined_networks'])
            defined_networks.add('default')  # Docker creates default network

            for service_name, service_networks in network_info['service_networks'].items():
                for network_name in service_networks:
                    if network_name not in defined_networks:
                        network_config_issues.append(
                            f"{compose_file} - Service '{service_name}' references undefined network: '{network_name}'"
                        )

        # Check for network naming consistency across environments
        network_names_by_env = {}
        for compose_file, network_info in network_configs_by_file.items():
            # Extract base environment name
            env_name = compose_file.replace('docker-compose.', '').replace('.yml', '')
            if env_name == 'docker-compose':
                env_name = 'default'

            network_names_by_env[env_name] = network_info['defined_networks']

        # Look for suspicious network naming patterns
        all_network_names = set()
        for networks in network_names_by_env.values():
            all_network_names.update(networks)

        for network_name in all_network_names:
            # Count how many environments define this network
            envs_with_network = [env for env, networks in network_names_by_env.items() if network_name in networks]

            # If a network is only defined in some environments, it might be an issue
            if len(envs_with_network) > 1 and len(envs_with_network) < len(network_names_by_env):
                missing_envs = [env for env in network_names_by_env.keys() if env not in envs_with_network]
                network_config_issues.append(
                    f"Network '{network_name}' defined inconsistently: "
                    f"Present in {envs_with_network}, Missing in {missing_envs}"
                )

        assert not network_config_issues, \
            f"Docker compose network configuration validation failures: " \
            f"{json.dumps(network_config_issues, indent=2)}. " \
            f"Network configuration issues cause service integration failures in Alpine builds."