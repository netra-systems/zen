"""

E2E Tests for Auth Service Port Configuration Consistency

Tests that auth service port configuration is consistent across all environments.



Business Value Justification (BVJ):

- Segment: Platform/Internal (affects all environments)

- Business Goal: Development velocity and environment stability

- Value Impact: Prevents port conflicts and connection failures

- Strategic Impact: Ensures auth service reliability across all environments

"""



import pytest

import os

import json

import yaml

from pathlib import Path

from typing import Dict, List, Set

from shared.isolated_environment import IsolatedEnvironment





@pytest.mark.e2e

class TestAuthServicePortConfigurationConsistency:

    """Test suite for auth service port configuration consistency."""

    

    @pytest.mark.auth

    def test_port_configuration_consistency_across_files(self):

        """

        Test that auth service port is consistent across all configuration files.

        

        This test SHOULD FAIL until port configuration is standardized.

        Exposes the coverage gap in configuration consistency.

        

        Critical Assertions:

        - All config files use the same auth service port

        - Environment templates match GitHub Actions

        - Main application matches documentation

        

        Expected Failure: Port mismatch between files

        Business Impact: Service discovery failures, connection errors

        """

        base_dir = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1")

        

        # Files to check for port configurations

        config_files = [

            base_dir / ".env.unified.template",

            base_dir / ".github/workflows/e2e-tests.yml", 

            base_dir / "auth_service/main.py",

            base_dir / "config/oauth_redirect_uris.json",

            base_dir / "auth_service/README.md"

        ]

        

        ports_found = {}  # file -> set of ports

        

        for config_file in config_files:

            if not config_file.exists():

                continue

                

            content = config_file.read_text(encoding='utf-8')

            file_ports = set()

            

            # Look for common port patterns

            import re

            

            # Look for 8081 and 8001 specifically

            port_matches = re.findall(r'(?:localhost:)?(8001|8081)(?![0-9])', content)

            for port in port_matches:

                file_ports.add(int(port))

            

            # Look for AUTH_SERVICE_URL patterns

            auth_url_matches = re.findall(r'AUTH_SERVICE_URL=http://[^:]+:(\d+)', content)

            for port in auth_url_matches:

                if port in ['8001', '8081']:

                    file_ports.add(int(port))

            

            # Look for --port arguments

            port_arg_matches = re.findall(r'--port["\s]+(\d+)', content)

            for port in port_arg_matches:

                if port in ['8001', '8081']:

                    file_ports.add(int(port))

            

            if file_ports:

                ports_found[str(config_file)] = file_ports

        

        # Analyze port consistency

        all_ports = set()

        for file_path, ports in ports_found.items():

            all_ports.update(ports)

        

        # Check if we found any auth service ports

        auth_ports = {p for p in all_ports if p in [8001, 8081]}

        assert len(auth_ports) > 0, "No auth service ports found in configuration files"

        

        # This assertion SHOULD FAIL - there should be only one port used consistently

        assert len(auth_ports) == 1, \

            f"Inconsistent auth service ports found: {auth_ports}. " \

            f"Port usage by file: {ports_found}"

        

        # If we get here, all files use the same port (which would be good)

        consistent_port = list(auth_ports)[0]

        

        # Verify each file uses only the consistent port

        for file_path, ports in ports_found.items():

            file_auth_ports = {p for p in ports if p in [8001, 8081]}

            assert consistent_port in file_auth_ports, \

                f"File {file_path} does not use consistent port {consistent_port}, uses: {ports}"



    @pytest.mark.auth

    def test_development_launcher_port_consistency(self):

        """

        Test that development launcher uses consistent port configuration.

        

        Critical Assertions:

        - Dev launcher script uses correct port

        - Port matches environment configuration

        - No hardcoded port conflicts

        

        Expected Failure: Dev launcher port mismatch

        Business Impact: Local development broken, services unreachable

        """

        base_dir = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1")

        

        # Check dev launcher script

        dev_launcher_files = [

            base_dir / "scripts/dev_launcher.py",

            base_dir / "dev_launcher" / "launcher.py"

        ]

        

        expected_port = None

        

        # Get expected port from environment template

        env_template = base_dir / ".env.unified.template"

        if env_template.exists():

            content = env_template.read_text()

            import re

            matches = re.findall(r'AUTH_SERVICE_URL=http://[^:]+:(\d+)', content)

            if matches:

                expected_port = int(matches[0])

        

        if expected_port is None:

            pytest.skip("Could not determine expected auth service port from environment template")

        

        for launcher_file in dev_launcher_files:

            if not launcher_file.exists():

                continue

                

            content = launcher_file.read_text()

            

            # Look for hardcoded ports

            import re

            hardcoded_ports = re.findall(r'(?:localhost:)?(8001|8081)(?![0-9])', content)

            

            if hardcoded_ports:

                for port in hardcoded_ports:

                    port_int = int(port)

                    assert port_int == expected_port, \

                        f"Dev launcher file {launcher_file} uses port {port_int}, " \

                        f"expected {expected_port} from environment template"



    @pytest.mark.auth

    def test_docker_compose_port_consistency(self):

        """

        Test that Docker Compose files use consistent auth service ports.

        

        Critical Assertions:

        - Docker Compose port mappings are correct

        - Internal and external ports align

        - No port conflicts between services

        

        Expected Failure: Docker port configuration mismatch

        Business Impact: Container orchestration fails, service unreachable

        """

        base_dir = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1")

        

        # Find Docker Compose files

        docker_files = []

        for pattern in ["docker-compose*.yml", "docker-compose*.yaml"]:

            docker_files.extend(base_dir.glob(pattern))

            docker_files.extend(base_dir.glob(f"*/{pattern}"))

        

        if not docker_files:

            pytest.skip("No Docker Compose files found")

        

        expected_port = None

        

        # Get expected port from environment template

        env_template = base_dir / ".env.unified.template" 

        if env_template.exists():

            content = env_template.read_text()

            import re

            matches = re.findall(r'AUTH_SERVICE_URL=http://[^:]+:(\d+)', content)

            if matches:

                expected_port = int(matches[0])

        

        for docker_file in docker_files:

            try:

                content = docker_file.read_text()

                

                # Parse YAML content

                import yaml

                docker_config = yaml.safe_load(content)

                

                if not docker_config or 'services' not in docker_config:

                    continue

                

                # Look for auth service configuration

                for service_name, service_config in docker_config['services'].items():

                    if 'auth' in service_name.lower():

                        ports = service_config.get('ports', [])

                        

                        for port_mapping in ports:

                            if isinstance(port_mapping, str):

                                # Parse "external:internal" format

                                if ':' in port_mapping:

                                    external, internal = port_mapping.split(':', 1)

                                    external_port = int(external)

                                    internal_port = int(internal)

                                    

                                    if expected_port:

                                        assert external_port == expected_port, \

                                            f"Docker service {service_name} in {docker_file} " \

                                            f"uses external port {external_port}, " \

                                            f"expected {expected_port}"

                                    

                                    # Internal port should typically match external for auth

                                    if external_port in [8001, 8081]:

                                        assert internal_port == external_port, \

                                            f"Port mapping mismatch in {service_name}: " \

                                            f"{external_port}:{internal_port}"

                            

            except yaml.YAMLError:

                # Skip invalid YAML files

                continue



    @pytest.mark.auth

    def test_github_actions_port_consistency(self):

        """

        Test that GitHub Actions workflows use consistent auth service ports.

        

        Critical Assertions:

        - CI/CD workflows use correct port

        - Health check URLs match service port

        - Environment variables consistent

        

        Expected Failure: GitHub Actions port mismatch with other configs

        Business Impact: CI/CD pipeline failures, deployment issues

        """

        base_dir = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1")

        

        # Find GitHub Actions workflows

        github_dir = base_dir / ".github/workflows"

        if not github_dir.exists():

            pytest.skip("No GitHub Actions workflows found")

        

        workflow_files = list(github_dir.glob("*.yml")) + list(github_dir.glob("*.yaml"))

        

        expected_port = None

        

        # Get expected port from environment template

        env_template = base_dir / ".env.unified.template"

        if env_template.exists():

            content = env_template.read_text()

            import re

            matches = re.findall(r'AUTH_SERVICE_URL=http://[^:]+:(\d+)', content)

            if matches:

                expected_port = int(matches[0])

        

        workflow_ports = set()

        

        for workflow_file in workflow_files:

            content = workflow_file.read_text()

            

            # Look for auth service port references

            import re

            

            # Environment variable settings

            env_ports = re.findall(r'AUTH_SERVICE_URL=http://[^:]+:(\d+)', content)

            for port in env_ports:

                if port in ['8001', '8081']:

                    workflow_ports.add(int(port))

            

            # Health check URLs

            health_ports = re.findall(r'http://localhost:(\d+)/health', content)

            for port in health_ports:

                if port in ['8001', '8081']:

                    workflow_ports.add(int(port))

            

            # Curl commands

            curl_ports = re.findall(r'curl[^:]*http://[^:]+:(\d+)', content)

            for port in curl_ports:

                if port in ['8001', '8081']:

                    workflow_ports.add(int(port))

        

        if not workflow_ports:

            pytest.skip("No auth service ports found in GitHub Actions workflows")

        

        # Check consistency within workflows

        assert len(workflow_ports) == 1, \

            f"GitHub Actions workflows use inconsistent ports: {workflow_ports}"

        

        # Check consistency with expected port

        if expected_port:

            workflow_port = list(workflow_ports)[0]

            assert workflow_port == expected_port, \

                f"GitHub Actions uses port {workflow_port}, " \

                f"but environment template expects {expected_port}"



    @pytest.mark.auth

    def test_service_discovery_port_consistency(self):

        """

        Test that service discovery mechanisms use consistent ports.

        

        Critical Assertions:

        - Service registry entries match configuration

        - Load balancer configurations use correct ports

        - DNS/discovery records point to right ports

        

        Expected Failure: Service discovery port mismatch

        Business Impact: Service mesh failures, load balancing issues

        """

        base_dir = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1")

        

        # Check service registry files

        service_registry_dir = base_dir / ".service_registry"

        if service_registry_dir.exists():

            for registry_file in service_registry_dir.glob("*.json"):

                if "auth" in registry_file.name.lower():

                    try:

                        config = json.loads(registry_file.read_text())

                        

                        # Check port in service config

                        if 'port' in config:

                            registry_port = config['port']

                            assert registry_port in [8001, 8081], \

                                f"Service registry {registry_file} uses unexpected port: {registry_port}"

                        

                        # Check URL in service config

                        if 'url' in config:

                            url = config['url']

                            import re

                            port_match = re.search(r':(\d+)/', url)

                            if port_match:

                                url_port = int(port_match.group(1))

                                assert url_port in [8001, 8081], \

                                    f"Service registry URL uses unexpected port: {url_port}"

                                

                                if 'port' in config:

                                    assert url_port == config['port'], \

                                        f"Port mismatch in {registry_file}: URL={url_port}, config={config['port']}"

                    

                    except (json.JSONDecodeError, KeyError):

                        continue

        

        # Check any Kubernetes service definitions

        k8s_files = []

        for pattern in ["*.yaml", "*.yml"]:

            k8s_files.extend(base_dir.glob(f"k8s/{pattern}"))

            k8s_files.extend(base_dir.glob(f"kubernetes/{pattern}"))

            k8s_files.extend(base_dir.glob(f"deploy/{pattern}"))

        

        for k8s_file in k8s_files:

            try:

                content = k8s_file.read_text()

                if 'kind: Service' in content and 'auth' in content.lower():

                    import yaml

                    k8s_config = yaml.safe_load(content)

                    

                    if k8s_config.get('kind') == 'Service':

                        ports = k8s_config.get('spec', {}).get('ports', [])

                        for port_config in ports:

                            port = port_config.get('port')

                            if port in [8001, 8081]:

                                target_port = port_config.get('targetPort', port)

                                assert target_port == port, \

                                    f"K8s service port mismatch: port={port}, targetPort={target_port}"

            

            except (yaml.YAMLError, KeyError):

                continue

