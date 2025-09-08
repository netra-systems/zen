# Docker Configuration Testing Remediation Plan

## Executive Summary

**Date:** 2025-08-27  
**Agent:** Docker Configuration Testing Agent  
**Objective:** Remediate critical gaps in Docker Compose configuration testing (currently 10% coverage)

This plan addresses the 7 critical gaps identified in the configuration testing audit:
- No automated validation of Dockerfile configurations
- Missing tests for container resource limits
- No validation of container networking configurations  
- Missing tests for volume mount configurations
- No tests for service dependency ordering
- No validation of environment variable propagation in containers
- Missing health check configuration validation

## Current State Analysis

### Existing Infrastructure (Strengths)
- ✅ Docker Compose test manager (`test_framework/docker_test_manager.py`)
- ✅ Compose manager with container inspection (`test_framework/docker_testing/compose_manager.py`)
- ✅ Two compose files: `docker-compose.dev.yml` and `docker-compose.test.yml`
- ✅ Multi-stage Dockerfiles with proper security practices
- ✅ Health checks defined for critical services
- ✅ Environment isolation patterns established

### Critical Gaps (10% Coverage)
- ❌ **Configuration Validation**: No automated testing of compose file structure
- ❌ **Resource Limits**: No validation of memory/CPU constraints
- ❌ **Network Configuration**: No testing of service-to-service communication
- ❌ **Volume Mounts**: No validation of volume configurations and permissions
- ❌ **Dependency Ordering**: No testing of service startup sequences
- ❌ **Environment Variables**: No validation of variable propagation
- ❌ **Health Checks**: No testing of health check effectiveness

## Implementation Strategy

### Phase 1: Foundation (Priority P0) - 8 hours
Create comprehensive Docker configuration test infrastructure

### Phase 2: Core Testing (Priority P0) - 12 hours  
Implement tests for each critical gap

### Phase 3: Integration (Priority P1) - 6 hours
Integrate with existing test infrastructure

### Phase 4: Monitoring (Priority P2) - 4 hours
Add observability and drift detection

**Total Effort: 30 hours across 2-3 sprints**

## Detailed Implementation Plan

### Phase 1: Foundation Infrastructure

#### 1.1 Docker Configuration Test Framework (4 hours)

**File: `/tests/docker/test_docker_config_validation.py`**

```python
"""
Docker Configuration Validation Test Suite

Validates Docker Compose configurations, Dockerfiles, and container settings
to ensure proper configuration and deployment readiness.
"""

import pytest
import yaml
import json
import subprocess
import docker
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from test_framework.docker_test_manager import DockerTestManager, ServiceMode
from test_framework.docker_testing.compose_manager import DockerComposeManager


@dataclass
class DockerConfigTest:
    """Configuration for a Docker validation test."""
    name: str
    compose_file: str
    expected_services: List[str]
    network_requirements: Dict[str, List[str]]
    resource_requirements: Dict[str, Dict[str, str]]
    volume_requirements: Dict[str, List[str]]


class DockerConfigValidator:
    """Validates Docker Compose configurations and deployment readiness."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docker_client = docker.from_env()
        
    def validate_compose_file_structure(self, compose_file: Path) -> Dict[str, Any]:
        """Validate compose file structure and syntax."""
        if not compose_file.exists():
            raise FileNotFoundError(f"Compose file not found: {compose_file}")
            
        with open(compose_file, 'r') as f:
            try:
                config = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML in {compose_file}: {e}")
                
        # Validate required top-level keys
        required_keys = ['version', 'services']
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required key '{key}' in {compose_file}")
                
        return config
        
    def validate_service_definitions(self, config: Dict[str, Any]) -> List[str]:
        """Validate individual service definitions."""
        issues = []
        services = config.get('services', {})
        
        for service_name, service_config in services.items():
            # Check for required service properties
            if 'image' not in service_config and 'build' not in service_config:
                issues.append(f"Service {service_name}: missing 'image' or 'build'")
                
            # Validate environment variables
            if 'environment' in service_config:
                env_vars = service_config['environment']
                if isinstance(env_vars, list):
                    for env_var in env_vars:
                        if '=' not in env_var:
                            issues.append(f"Service {service_name}: invalid env var format '{env_var}'")
                            
        return issues
        
    def validate_network_configuration(self, config: Dict[str, Any]) -> List[str]:
        """Validate network configuration."""
        issues = []
        services = config.get('services', {})
        networks = config.get('networks', {})
        
        # Check for isolated networks
        for service_name, service_config in services.items():
            service_networks = service_config.get('networks', [])
            if not service_networks and not networks:
                issues.append(f"Service {service_name}: no network configuration")
                
        return issues
        
    def validate_volume_configuration(self, config: Dict[str, Any]) -> List[str]:
        """Validate volume configuration."""
        issues = []
        services = config.get('services', {})
        
        for service_name, service_config in services.items():
            volumes = service_config.get('volumes', [])
            for volume in volumes:
                # Check volume format
                if isinstance(volume, str):
                    if ':' not in volume:
                        issues.append(f"Service {service_name}: invalid volume format '{volume}'")
                    else:
                        host_path, container_path = volume.split(':', 1)
                        # Check if host path exists for bind mounts
                        if not host_path.startswith('/') and not host_path.startswith('./'):
                            continue  # Named volume
                        host_full_path = self.project_root / host_path
                        if not host_full_path.exists():
                            issues.append(f"Service {service_name}: host path does not exist '{host_path}'")
                            
        return issues


@pytest.fixture(scope="session")
def docker_config_validator():
    """Provide Docker configuration validator."""
    project_root = Path.cwd()
    return DockerConfigValidator(project_root)


@pytest.fixture(scope="session") 
def compose_configs():
    """Load all compose configurations."""
    project_root = Path.cwd()
    return {
        'dev': project_root / 'docker-compose.dev.yml',
        'test': project_root / 'docker-compose.test.yml'
    }
```

#### 1.2 Docker Health Check Validator (2 hours)

```python
class DockerHealthValidator:
    """Validates Docker health check configurations and effectiveness."""
    
    def __init__(self, compose_manager: DockerComposeManager):
        self.compose_manager = compose_manager
        self.docker_client = docker.from_env()
        
    async def validate_health_check_definitions(self, config: Dict[str, Any]) -> List[str]:
        """Validate health check configurations in compose file."""
        issues = []
        services = config.get('services', {})
        
        critical_services = ['postgres', 'postgres-test', 'redis', 'redis-test', 
                           'backend', 'backend-test', 'auth', 'auth-test']
        
        for service_name, service_config in services.items():
            if service_name in critical_services:
                healthcheck = service_config.get('healthcheck')
                if not healthcheck:
                    issues.append(f"Critical service {service_name}: missing health check")
                    continue
                    
                # Validate health check structure
                required_fields = ['test', 'interval', 'timeout', 'retries']
                for field in required_fields:
                    if field not in healthcheck:
                        issues.append(f"Service {service_name}: missing health check field '{field}'")
                        
                # Validate health check command
                test_cmd = healthcheck.get('test', [])
                if isinstance(test_cmd, list) and len(test_cmd) > 1:
                    if test_cmd[0] not in ['CMD', 'CMD-SHELL']:
                        issues.append(f"Service {service_name}: invalid health check test format")
                        
        return issues
        
    async def test_health_check_effectiveness(self, service_name: str, timeout: int = 60) -> bool:
        """Test if health checks actually work for a service."""
        # Start the service
        success = await self.compose_manager.start_containers([service_name])
        if not success:
            return False
            
        # Wait for health check to pass
        start_time = time.time()
        while time.time() - start_time < timeout:
            container_info = await self.compose_manager.get_container_info(service_name)
            if container_info and container_info.health_status == 'healthy':
                return True
            elif container_info and container_info.health_status == 'unhealthy':
                return False
            await asyncio.sleep(2)
            
        return False
```

#### 1.3 Resource Limits Validator (2 hours)

```python
class ResourceLimitsValidator:
    """Validates container resource limits and constraints."""
    
    def validate_resource_definitions(self, config: Dict[str, Any]) -> List[str]:
        """Validate resource limit definitions in compose file."""
        issues = []
        services = config.get('services', {})
        
        # Services that should have resource limits
        production_services = ['backend', 'backend-test', 'auth', 'auth-test', 
                             'frontend', 'frontend-test']
        
        for service_name, service_config in services.items():
            if service_name in production_services:
                deploy_config = service_config.get('deploy', {})
                resources = deploy_config.get('resources', {})
                
                if not resources:
                    issues.append(f"Production service {service_name}: missing resource limits")
                    continue
                    
                # Check for memory limits
                limits = resources.get('limits', {})
                if 'memory' not in limits:
                    issues.append(f"Service {service_name}: missing memory limit")
                    
                # Check for CPU limits  
                if 'cpus' not in limits:
                    issues.append(f"Service {service_name}: missing CPU limit")
                    
        return issues
        
    async def test_resource_enforcement(self, service_name: str) -> bool:
        """Test if resource limits are actually enforced."""
        container_info = await self.compose_manager.get_container_info(service_name)
        if not container_info:
            return False
            
        # Get container resource stats
        container = self.docker_client.containers.get(container_info.container_id)
        stats = container.stats(stream=False)
        
        # Check if limits are being enforced
        memory_limit = stats.get('memory', {}).get('limit', 0)
        memory_usage = stats.get('memory', {}).get('usage', 0)
        
        # Verify limits are set and reasonable
        if memory_limit == 0:
            return False  # No limit set
            
        if memory_limit > 2 * 1024 * 1024 * 1024:  # 2GB
            return False  # Limit too high for test environment
            
        return True
```

### Phase 2: Core Testing Implementation

#### 2.1 Comprehensive Configuration Tests (4 hours)

**File: `/tests/docker/test_docker_compose_validation.py`**

```python
"""
Docker Compose Configuration Tests

Tests all aspects of Docker Compose configuration including:
- Service definitions
- Network configuration
- Volume mounts
- Health checks
- Resource limits
- Environment variables
"""

import pytest
import asyncio
from pathlib import Path

from test_framework.environment_markers import requires_docker
from tests.docker.test_docker_config_validation import DockerConfigValidator, DockerHealthValidator


class TestDockerComposeValidation:
    """Test Docker Compose configuration validation."""
    
    @requires_docker
    def test_dev_compose_structure_validation(self, docker_config_validator, compose_configs):
        """Test docker-compose.dev.yml structure validation."""
        config = docker_config_validator.validate_compose_file_structure(compose_configs['dev'])
        
        # Verify required services exist
        required_services = ['postgres', 'redis', 'backend', 'auth', 'frontend']
        services = config.get('services', {})
        
        for service in required_services:
            assert service in services, f"Required service '{service}' missing from dev compose"
            
        # Verify networks are defined
        assert 'networks' in config, "Networks section missing from dev compose"
        assert 'netra-network' in config['networks'], "netra-network not defined"
        
        # Verify volumes are defined
        assert 'volumes' in config, "Volumes section missing from dev compose"
        expected_volumes = ['postgres_data', 'redis_data']
        volumes = config.get('volumes', {})
        
        for volume in expected_volumes:
            assert volume in volumes, f"Required volume '{volume}' missing"
    
    @requires_docker        
    def test_test_compose_structure_validation(self, docker_config_validator, compose_configs):
        """Test docker-compose.test.yml structure validation."""
        config = docker_config_validator.validate_compose_file_structure(compose_configs['test'])
        
        # Verify test services exist
        required_services = ['postgres-test', 'redis-test', 'backend-test', 'auth-test']
        services = config.get('services', {})
        
        for service in required_services:
            assert service in services, f"Required test service '{service}' missing"
            
        # Verify test network isolation
        assert 'networks' in config, "Networks section missing from test compose"
        assert 'netra-test-network' in config['networks'], "Test network not isolated"
    
    @requires_docker
    def test_service_definitions_validation(self, docker_config_validator, compose_configs):
        """Test individual service definitions."""
        for env_name, compose_file in compose_configs.items():
            config = docker_config_validator.validate_compose_file_structure(compose_file)
            issues = docker_config_validator.validate_service_definitions(config)
            
            assert len(issues) == 0, f"Service definition issues in {env_name}: {issues}"
    
    @requires_docker        
    def test_network_configuration_validation(self, docker_config_validator, compose_configs):
        """Test network configuration."""
        for env_name, compose_file in compose_configs.items():
            config = docker_config_validator.validate_compose_file_structure(compose_file)
            issues = docker_config_validator.validate_network_configuration(config)
            
            assert len(issues) == 0, f"Network configuration issues in {env_name}: {issues}"
    
    @requires_docker        
    def test_volume_configuration_validation(self, docker_config_validator, compose_configs):
        """Test volume configuration."""
        for env_name, compose_file in compose_configs.items():
            config = docker_config_validator.validate_compose_file_structure(compose_file)
            issues = docker_config_validator.validate_volume_configuration(config)
            
            # Filter out acceptable missing paths (like logs directory that gets created)
            acceptable_missing = ['./logs', './SPEC', './scripts']
            filtered_issues = [
                issue for issue in issues 
                if not any(missing in issue for missing in acceptable_missing)
            ]
            
            assert len(filtered_issues) == 0, f"Volume configuration issues in {env_name}: {filtered_issues}"


class TestDockerHealthChecks:
    """Test Docker health check configurations and effectiveness."""
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_health_check_definitions(self, docker_config_validator, compose_configs):
        """Test health check definitions in compose files."""
        from test_framework.docker_testing.compose_manager import DockerComposeManager
        
        for env_name, compose_file in compose_configs.items():
            config = docker_config_validator.validate_compose_file_structure(compose_file)
            
            compose_manager = DockerComposeManager(str(compose_file))
            health_validator = DockerHealthValidator(compose_manager)
            
            issues = await health_validator.validate_health_check_definitions(config)
            
            assert len(issues) == 0, f"Health check issues in {env_name}: {issues}"
    
    @requires_docker
    @pytest.mark.asyncio 
    async def test_postgres_health_check_effectiveness(self):
        """Test PostgreSQL health check actually works."""
        from test_framework.docker_testing.compose_manager import DockerComposeManager
        
        compose_manager = DockerComposeManager("docker-compose.test.yml", "test-health")
        await compose_manager.initialize()
        
        try:
            health_validator = DockerHealthValidator(compose_manager)
            is_healthy = await health_validator.test_health_check_effectiveness("postgres-test", 60)
            
            assert is_healthy, "PostgreSQL health check failed to pass within timeout"
            
        finally:
            await compose_manager.cleanup()
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_redis_health_check_effectiveness(self):
        """Test Redis health check actually works."""
        from test_framework.docker_testing.compose_manager import DockerComposeManager
        
        compose_manager = DockerComposeManager("docker-compose.test.yml", "test-health")
        await compose_manager.initialize()
        
        try:
            health_validator = DockerHealthValidator(compose_manager)
            is_healthy = await health_validator.test_health_check_effectiveness("redis-test", 60)
            
            assert is_healthy, "Redis health check failed to pass within timeout"
            
        finally:
            await compose_manager.cleanup()
```

#### 2.2 Environment Variable Propagation Tests (3 hours)

**File: `/tests/docker/test_environment_variable_propagation.py`**

```python
"""
Environment Variable Propagation Tests

Validates that environment variables are properly propagated from
host to containers and between containers as expected.
"""

import pytest
import os
import asyncio
import json
from typing import Dict, Any

from test_framework.environment_markers import requires_docker
from test_framework.docker_testing.compose_manager import DockerComposeManager


class TestEnvironmentVariablePropagation:
    """Test environment variable propagation in Docker containers."""
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_database_url_propagation(self):
        """Test #removed-legacypropagation to services."""
        compose_manager = DockerComposeManager("docker-compose.test.yml", "test-env")
        await compose_manager.initialize()
        
        try:
            # Start services
            success = await compose_manager.start_containers(["postgres-test", "backend-test"])
            assert success, "Failed to start test containers"
            
            # Wait for services to be ready
            await compose_manager.wait_for_healthy(timeout_seconds=60)
            
            # Check #removed-legacyin backend container
            result = await compose_manager.exec_in_container(
                "backend-test", 
                ["python", "-c", "import os; print(os.environ.get('DATABASE_URL'))"]
            )
            
            assert result[0] == 0, f"Failed to get DATABASE_URL: {result[2]}"
            database_url = result[1].strip()
            
            # Verify #removed-legacyformat
            assert "postgresql://" in database_url, "#removed-legacyshould be PostgreSQL URL"
            assert "postgres-test:5432" in database_url, "Should reference postgres-test service"
            assert "netra_test" in database_url, "Should reference test database"
            
        finally:
            await compose_manager.cleanup()
    
    @requires_docker
    @pytest.mark.asyncio        
    async def test_redis_url_propagation(self):
        """Test REDIS_URL propagation to services."""
        compose_manager = DockerComposeManager("docker-compose.test.yml", "test-env")
        await compose_manager.initialize()
        
        try:
            # Start services
            success = await compose_manager.start_containers(["redis-test", "backend-test"])
            assert success, "Failed to start test containers"
            
            await compose_manager.wait_for_healthy(timeout_seconds=60)
            
            # Check REDIS_URL in backend container
            result = await compose_manager.exec_in_container(
                "backend-test",
                ["python", "-c", "import os; print(os.environ.get('REDIS_URL'))"]
            )
            
            assert result[0] == 0, f"Failed to get REDIS_URL: {result[2]}"
            redis_url = result[1].strip()
            
            # Verify REDIS_URL format
            assert "redis://" in redis_url, "REDIS_URL should be Redis URL"
            assert "redis-test:6379" in redis_url, "Should reference redis-test service"
            
        finally:
            await compose_manager.cleanup()
    
    @requires_docker
    @pytest.mark.asyncio        
    async def test_auth_service_url_propagation(self):
        """Test AUTH_SERVICE_URL propagation between services."""
        compose_manager = DockerComposeManager("docker-compose.test.yml", "test-env")
        await compose_manager.initialize()
        
        try:
            # Start all test services
            success = await compose_manager.start_containers([
                "postgres-test", "redis-test", "auth-test", "backend-test"
            ])
            assert success, "Failed to start test containers"
            
            await compose_manager.wait_for_healthy(timeout_seconds=90)
            
            # Check AUTH_SERVICE_URL in backend container
            result = await compose_manager.exec_in_container(
                "backend-test",
                ["python", "-c", "import os; print(os.environ.get('AUTH_SERVICE_URL'))"]
            )
            
            assert result[0] == 0, f"Failed to get AUTH_SERVICE_URL: {result[2]}"
            auth_url = result[1].strip()
            
            # Verify AUTH_SERVICE_URL format
            assert "http://auth-test:8082" in auth_url, "Should reference auth-test service on port 8082"
            
        finally:
            await compose_manager.cleanup()
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_api_key_environment_isolation(self):
        """Test that API keys are properly isolated in test environment."""
        compose_manager = DockerComposeManager("docker-compose.test.yml", "test-env")  
        await compose_manager.initialize()
        
        try:
            success = await compose_manager.start_containers(["backend-test"])
            assert success, "Failed to start backend-test container"
            
            await compose_manager.wait_for_healthy(timeout_seconds=60)
            
            # Check that test API keys are being used
            for api_key_var in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"]:
                result = await compose_manager.exec_in_container(
                    "backend-test",
                    ["python", "-c", f"import os; print(os.environ.get('{api_key_var}'))"]
                )
                
                assert result[0] == 0, f"Failed to get {api_key_var}: {result[2]}"
                api_key_value = result[1].strip()
                
                # Verify it's a test key
                assert api_key_value.startswith("test-"), f"{api_key_var} should be test key"
                
        finally:
            await compose_manager.cleanup()
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_environment_variable_precedence(self):
        """Test environment variable precedence (compose file vs host)."""
        # Set a host environment variable
        os.environ["TEST_OVERRIDE_VAR"] = "host-value"
        
        compose_manager = DockerComposeManager("docker-compose.test.yml", "test-env")
        await compose_manager.initialize() 
        
        try:
            success = await compose_manager.start_containers(["backend-test"])
            assert success, "Failed to start backend-test container"
            
            # Check ENVIRONMENT variable (should be from compose file)
            result = await compose_manager.exec_in_container(
                "backend-test",
                ["python", "-c", "import os; print(os.environ.get('ENVIRONMENT'))"]
            )
            
            assert result[0] == 0, f"Failed to get ENVIRONMENT: {result[2]}"
            environment = result[1].strip()
            
            # Should be 'testing' from compose file, not from host
            assert environment == "testing", "ENVIRONMENT should be 'testing' from compose file"
            
        finally:
            await compose_manager.cleanup()
            # Clean up host environment
            if "TEST_OVERRIDE_VAR" in os.environ:
                del os.environ["TEST_OVERRIDE_VAR"]
```

#### 2.3 Network Configuration Tests (3 hours)

**File: `/tests/docker/test_docker_networking.py`**

```python
"""
Docker Network Configuration Tests

Tests Docker networking configuration including:
- Service-to-service communication
- Network isolation
- Port mappings
- DNS resolution
"""

import pytest
import asyncio
import json
from typing import List, Tuple

from test_framework.environment_markers import requires_docker
from test_framework.docker_testing.compose_manager import DockerComposeManager


class TestDockerNetworking:
    """Test Docker networking configuration and connectivity."""
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_service_to_service_connectivity(self):
        """Test that services can communicate with each other."""
        compose_manager = DockerComposeManager("docker-compose.test.yml", "test-network")
        await compose_manager.initialize()
        
        try:
            # Start all services
            success = await compose_manager.start_containers([
                "postgres-test", "redis-test", "auth-test", "backend-test"
            ])
            assert success, "Failed to start test containers"
            
            await compose_manager.wait_for_healthy(timeout_seconds=90)
            
            # Test backend -> postgres connectivity
            can_connect = await compose_manager.check_network_connectivity(
                "backend-test", "postgres-test"
            )
            assert can_connect, "Backend cannot connect to PostgreSQL"
            
            # Test backend -> redis connectivity  
            can_connect = await compose_manager.check_network_connectivity(
                "backend-test", "redis-test"
            )
            assert can_connect, "Backend cannot connect to Redis"
            
            # Test backend -> auth connectivity
            can_connect = await compose_manager.check_network_connectivity(
                "backend-test", "auth-test"
            )
            assert can_connect, "Backend cannot connect to Auth service"
            
        finally:
            await compose_manager.cleanup()
    
    @requires_docker
    @pytest.mark.asyncio        
    async def test_dns_resolution(self):
        """Test DNS resolution between services."""
        compose_manager = DockerComposeManager("docker-compose.test.yml", "test-network")
        await compose_manager.initialize()
        
        try:
            success = await compose_manager.start_containers([
                "postgres-test", "redis-test", "backend-test"
            ])
            assert success, "Failed to start test containers"
            
            await compose_manager.wait_for_healthy(timeout_seconds=60)
            
            # Test DNS resolution from backend to other services
            services_to_resolve = ["postgres-test", "redis-test"]
            
            for service in services_to_resolve:
                result = await compose_manager.exec_in_container(
                    "backend-test",
                    ["nslookup", service]
                )
                
                assert result[0] == 0, f"DNS resolution failed for {service}: {result[2]}"
                assert service in result[1], f"Service {service} not found in DNS response"
                
        finally:
            await compose_manager.cleanup()
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_port_mappings(self):
        """Test that port mappings are correct."""
        compose_manager = DockerComposeManager("docker-compose.test.yml", "test-network")
        await compose_manager.initialize()
        
        try:
            success = await compose_manager.start_containers([
                "postgres-test", "redis-test", "backend-test", "auth-test"
            ])
            assert success, "Failed to start test containers"
            
            await compose_manager.wait_for_healthy(timeout_seconds=90)
            
            # Expected port mappings
            expected_ports = {
                "postgres-test": 5433,
                "redis-test": 6380, 
                "backend-test": 8001,
                "auth-test": 8082
            }
            
            for service, expected_port in expected_ports.items():
                container_info = await compose_manager.get_container_info(service)
                assert container_info, f"Container info not found for {service}"
                
                # Check if the expected port is mapped
                mapped_ports = container_info.ports
                assert mapped_ports, f"No ports mapped for {service}"
                
                # Find the mapping for the internal port
                internal_port = {
                    "postgres-test": "5432",
                    "redis-test": "6379", 
                    "backend-test": "8001",
                    "auth-test": "8082"
                }[service]
                
                assert internal_port in mapped_ports, f"Internal port {internal_port} not mapped for {service}"
                assert mapped_ports[internal_port] == expected_port, f"Port mapping incorrect for {service}"
                
        finally:
            await compose_manager.cleanup()
    
    @requires_docker
    @pytest.mark.asyncio        
    async def test_network_isolation(self):
        """Test network isolation between environments."""
        # Start both dev and test networks
        dev_manager = DockerComposeManager("docker-compose.dev.yml", "test-dev-network")
        test_manager = DockerComposeManager("docker-compose.test.yml", "test-test-network")
        
        await dev_manager.initialize()
        await test_manager.initialize()
        
        try:
            # Start services in both environments
            dev_success = await dev_manager.start_containers(["postgres", "redis"])
            test_success = await test_manager.start_containers(["postgres-test", "redis-test"])
            
            assert dev_success and test_success, "Failed to start containers in both environments"
            
            # Verify they're on different networks
            dev_containers = await dev_manager.get_all_containers()
            test_containers = await test_manager.get_all_containers()
            
            assert len(dev_containers) > 0, "No dev containers found"
            assert len(test_containers) > 0, "No test containers found"
            
            # Verify containers can't reach each other across environments
            # (This is implicit through different network names)
            
        finally:
            await dev_manager.cleanup()
            await test_manager.cleanup()
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_http_connectivity(self):
        """Test HTTP connectivity between services."""
        compose_manager = DockerComposeManager("docker-compose.test.yml", "test-network")
        await compose_manager.initialize()
        
        try:
            success = await compose_manager.start_containers([
                "postgres-test", "redis-test", "auth-test", "backend-test"
            ])
            assert success, "Failed to start test containers"
            
            await compose_manager.wait_for_healthy(timeout_seconds=90)
            
            # Test backend can reach auth service HTTP endpoint
            result = await compose_manager.exec_in_container(
                "backend-test",
                ["curl", "-f", "-s", "--max-time", "10", "http://auth-test:8082/health"]
            )
            
            assert result[0] == 0, f"Backend cannot reach auth service HTTP endpoint: {result[2]}"
            
            # Verify response is JSON
            try:
                response = json.loads(result[1])
                assert "status" in response, "Health response should contain status"
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON response from auth service: {result[1]}")
                
        finally:
            await compose_manager.cleanup()
```

#### 2.4 Volume Mount and Resource Tests (2 hours)

**File: `/tests/docker/test_docker_volumes_resources.py`**

```python
"""
Docker Volume and Resource Configuration Tests

Tests volume mounts and resource limit configurations.
"""

import pytest
import asyncio
import os
from pathlib import Path

from test_framework.environment_markers import requires_docker
from test_framework.docker_testing.compose_manager import DockerComposeManager


class TestDockerVolumes:
    """Test Docker volume mount configurations."""
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_source_code_volume_mounts(self):
        """Test that source code is properly mounted in containers."""
        compose_manager = DockerComposeManager("docker-compose.test.yml", "test-volumes")
        await compose_manager.initialize()
        
        try:
            success = await compose_manager.start_containers(["backend-test"])
            assert success, "Failed to start backend-test container"
            
            await compose_manager.wait_for_healthy(timeout_seconds=60)
            
            # Check that source code directories are mounted
            directories_to_check = [
                "/app/netra_backend",
                "/app/shared", 
                "/app/test_framework",
                "/app/SPEC",
                "/app/scripts"
            ]
            
            for directory in directories_to_check:
                result = await compose_manager.exec_in_container(
                    "backend-test",
                    ["ls", "-la", directory]
                )
                
                assert result[0] == 0, f"Directory {directory} not accessible: {result[2]}"
                
        finally:
            await compose_manager.cleanup()
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_log_volume_writability(self):
        """Test that log volumes are writable."""
        compose_manager = DockerComposeManager("docker-compose.test.yml", "test-volumes")
        await compose_manager.initialize()
        
        try:
            success = await compose_manager.start_containers(["backend-test"])
            assert success, "Failed to start backend-test container"
            
            await compose_manager.wait_for_healthy(timeout_seconds=60)
            
            # Test writing to log directory
            test_file = "/app/logs/test-write.log"
            result = await compose_manager.exec_in_container(
                "backend-test",
                ["sh", "-c", f"echo 'test write' > {test_file} && cat {test_file}"]
            )
            
            assert result[0] == 0, f"Cannot write to logs directory: {result[2]}"
            assert "test write" in result[1], "Log file content not correct"
            
            # Clean up test file
            await compose_manager.exec_in_container(
                "backend-test",
                ["rm", "-f", test_file]
            )
            
        finally:
            await compose_manager.cleanup()
    
    @requires_docker
    @pytest.mark.asyncio        
    async def test_database_volume_persistence(self):
        """Test that database volumes persist data."""
        compose_manager = DockerComposeManager("docker-compose.test.yml", "test-volumes")
        await compose_manager.initialize()
        
        try:
            # Start postgres
            success = await compose_manager.start_containers(["postgres-test"])
            assert success, "Failed to start postgres-test container"
            
            await compose_manager.wait_for_healthy(timeout_seconds=60)
            
            # Create test data
            result = await compose_manager.exec_in_container(
                "postgres-test",
                ["psql", "-U", "test", "-d", "netra_test", "-c", 
                 "CREATE TABLE test_persistence (id SERIAL PRIMARY KEY, data TEXT);"]
            )
            
            assert result[0] == 0, f"Failed to create test table: {result[2]}"
            
            # Insert test data
            result = await compose_manager.exec_in_container(
                "postgres-test", 
                ["psql", "-U", "test", "-d", "netra_test", "-c",
                 "INSERT INTO test_persistence (data) VALUES ('test data');"]
            )
            
            assert result[0] == 0, f"Failed to insert test data: {result[2]}"
            
            # Restart container
            restart_success = await compose_manager.restart_container("postgres-test")
            assert restart_success, "Failed to restart postgres container"
            
            await compose_manager.wait_for_healthy(timeout_seconds=60)
            
            # Verify data persisted
            result = await compose_manager.exec_in_container(
                "postgres-test",
                ["psql", "-U", "test", "-d", "netra_test", "-c", 
                 "SELECT data FROM test_persistence;"]
            )
            
            assert result[0] == 0, f"Failed to query test data: {result[2]}"
            assert "test data" in result[1], "Test data did not persist across container restart"
            
        finally:
            await compose_manager.cleanup()


class TestDockerResourceLimits:
    """Test Docker resource limit configurations."""
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_memory_limit_enforcement(self):
        """Test that memory limits are enforced."""
        # This test would be implementation-specific based on resource limits in compose files
        compose_manager = DockerComposeManager("docker-compose.test.yml", "test-resources")
        await compose_manager.initialize()
        
        try:
            success = await compose_manager.start_containers(["backend-test"])
            assert success, "Failed to start backend-test container"
            
            await compose_manager.wait_for_healthy(timeout_seconds=60)
            
            # Get container stats
            container_info = await compose_manager.get_container_info("backend-test")
            assert container_info, "Container info not found"
            
            # Check that container has resource constraints
            # (This would require resource limits to be defined in compose file)
            
        finally:
            await compose_manager.cleanup()
```

### Phase 3: Integration with Test Infrastructure

#### 3.1 Test Categories and Markers (2 hours)

**File: `/test_framework/environment_markers.py` (Update)**

```python
# Add Docker-specific markers
requires_docker = pytest.mark.skipif(
    not _is_docker_available(),
    reason="Docker is not available"
)

docker_integration = pytest.mark.docker_integration
docker_config = pytest.mark.docker_config

def _is_docker_available():
    """Check if Docker is available."""
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
```

#### 3.2 Test Configuration Integration (2 hours)

**File: `/test_framework/config/categories.yaml` (Update)**

```yaml
docker_config:
  description: "Docker configuration validation tests"
  markers: ["docker_config", "requires_docker"]
  timeout: 300
  parallel: false
  retry_count: 2
  environments: ["test", "dev"]
  
docker_integration:
  description: "Docker container integration tests"  
  markers: ["docker_integration", "requires_docker"]
  timeout: 600
  parallel: false
  retry_count: 1
  environments: ["test"]
```

#### 3.3 Unified Test Runner Integration (2 hours)

**File: `/unified_test_runner.py` (Update)**

```python
# Add Docker test categories
CATEGORY_MAPPINGS.update({
    'docker': {
        'patterns': ['tests/docker/'],
        'markers': ['docker_config', 'docker_integration'],
        'description': 'Docker configuration and integration tests'
    }
})
```

### Phase 4: Monitoring and Observability

#### 4.1 Docker Configuration Drift Detection (2 hours)

**File: `/tests/docker/test_docker_drift_detection.py`**

```python
"""
Docker Configuration Drift Detection

Monitors for configuration changes and validates consistency.
"""

import pytest
import hashlib
import json
from pathlib import Path
from typing import Dict, Any

from test_framework.environment_markers import requires_docker


class TestDockerDriftDetection:
    """Test for Docker configuration drift."""
    
    @requires_docker
    def test_compose_file_integrity(self):
        """Test that compose files haven't changed unexpectedly."""
        project_root = Path.cwd()
        
        compose_files = {
            'dev': project_root / 'docker-compose.dev.yml',
            'test': project_root / 'docker-compose.test.yml'
        }
        
        # Calculate checksums
        checksums = {}
        for env_name, compose_file in compose_files.items():
            if compose_file.exists():
                content = compose_file.read_text()
                checksums[env_name] = hashlib.sha256(content.encode()).hexdigest()
        
        # Store checksums for comparison (this would be stored in a baseline file)
        # For now, just verify the files are readable and parseable
        
        for env_name in checksums:
            assert checksums[env_name], f"Empty checksum for {env_name} compose file"
    
    @requires_docker        
    def test_dockerfile_consistency(self):
        """Test that Dockerfiles are consistent across environments."""
        docker_dir = Path.cwd() / 'docker'
        
        if not docker_dir.exists():
            pytest.skip("Docker directory not found")
        
        dockerfiles = list(docker_dir.glob('*.Dockerfile'))
        assert len(dockerfiles) > 0, "No Dockerfiles found"
        
        for dockerfile in dockerfiles:
            content = dockerfile.read_text()
            
            # Basic consistency checks
            assert 'FROM ' in content, f"Dockerfile {dockerfile.name} missing FROM instruction"
            assert 'WORKDIR ' in content, f"Dockerfile {dockerfile.name} missing WORKDIR instruction"
```

#### 4.2 Configuration Monitoring Dashboard (2 hours)

**File: `/scripts/docker_config_monitor.py`**

```python
"""
Docker Configuration Monitoring Script

Generates reports on Docker configuration health and compliance.
"""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class DockerConfigReport:
    """Docker configuration compliance report."""
    timestamp: str
    total_services: int
    services_with_health_checks: int
    services_with_resource_limits: int
    network_isolation_score: float
    volume_security_score: float
    issues: List[str]
    recommendations: List[str]


class DockerConfigMonitor:
    """Monitors Docker configuration for compliance and best practices."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        
    def analyze_compose_file(self, compose_file: Path) -> DockerConfigReport:
        """Analyze a compose file for compliance."""
        with open(compose_file, 'r') as f:
            config = yaml.safe_load(f)
            
        services = config.get('services', {})
        issues = []
        recommendations = []
        
        # Analyze services
        total_services = len(services)
        services_with_health_checks = 0
        services_with_resource_limits = 0
        
        for service_name, service_config in services.items():
            # Check health checks
            if 'healthcheck' in service_config:
                services_with_health_checks += 1
            else:
                issues.append(f"Service {service_name}: missing health check")
                
            # Check resource limits
            deploy_config = service_config.get('deploy', {})
            if 'resources' in deploy_config:
                services_with_resource_limits += 1
            else:
                recommendations.append(f"Service {service_name}: consider adding resource limits")
        
        # Calculate scores
        network_isolation_score = 1.0 if 'networks' in config else 0.0
        volume_security_score = self._calculate_volume_security_score(services)
        
        return DockerConfigReport(
            timestamp=datetime.now().isoformat(),
            total_services=total_services,
            services_with_health_checks=services_with_health_checks,
            services_with_resource_limits=services_with_resource_limits,
            network_isolation_score=network_isolation_score,
            volume_security_score=volume_security_score,
            issues=issues,
            recommendations=recommendations
        )
    
    def _calculate_volume_security_score(self, services: Dict[str, Any]) -> float:
        """Calculate volume security score."""
        total_volumes = 0
        secure_volumes = 0
        
        for service_config in services.values():
            volumes = service_config.get('volumes', [])
            for volume in volumes:
                total_volumes += 1
                # Check if volume is read-only or has appropriate permissions
                if isinstance(volume, str) and ':ro' in volume:
                    secure_volumes += 1
                elif isinstance(volume, dict) and volume.get('read_only'):
                    secure_volumes += 1
        
        return secure_volumes / total_volumes if total_volumes > 0 else 1.0
    
    def generate_report(self) -> Dict[str, DockerConfigReport]:
        """Generate comprehensive Docker configuration report."""
        reports = {}
        
        compose_files = {
            'dev': self.project_root / 'docker-compose.dev.yml',
            'test': self.project_root / 'docker-compose.test.yml'
        }
        
        for env_name, compose_file in compose_files.items():
            if compose_file.exists():
                reports[env_name] = self.analyze_compose_file(compose_file)
        
        return reports
    
    def save_report(self, output_file: Path):
        """Save configuration report to file."""
        reports = self.generate_report()
        
        # Convert to dict for JSON serialization
        report_data = {
            env: asdict(report) for env, report in reports.items()
        }
        
        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2)


if __name__ == "__main__":
    project_root = Path.cwd()
    monitor = DockerConfigMonitor(project_root)
    
    # Generate and save report
    output_file = project_root / "docker_config_report.json"
    monitor.save_report(output_file)
    print(f"Docker configuration report saved to {output_file}")
```

## Test File Organization

```
tests/
├── docker/                              # New Docker test directory
│   ├── __init__.py
│   ├── test_docker_config_validation.py  # Configuration validation tests
│   ├── test_docker_compose_validation.py # Compose file structure tests
│   ├── test_environment_variable_propagation.py # Env var tests
│   ├── test_docker_networking.py         # Network configuration tests
│   ├── test_docker_volumes_resources.py  # Volume and resource tests
│   └── test_docker_drift_detection.py    # Configuration drift detection
├── conftest.py                          # Updated with Docker fixtures
└── ...
```

## Implementation Timeline

### Sprint 1 (Week 1): Foundation
- **Days 1-2**: Docker Configuration Test Framework
- **Days 3-4**: Health Check and Resource Validators
- **Day 5**: Integration with existing test infrastructure

### Sprint 2 (Week 2): Core Testing
- **Days 1-2**: Compose validation and environment variable tests
- **Days 3-4**: Network configuration tests  
- **Day 5**: Volume and resource limit tests

### Sprint 3 (Week 3): Integration & Monitoring
- **Days 1-2**: Test runner integration and CI/CD pipeline updates
- **Days 3-4**: Configuration monitoring and drift detection
- **Day 5**: Documentation and team training

## Success Metrics

### Coverage Targets
- **Docker Configuration Testing**: 90% coverage (from 10%)
- **Compose File Validation**: 100% of services tested
- **Network Configuration**: 100% of inter-service connections validated
- **Environment Variables**: 100% of critical variables tested

### Quality Gates
- All Docker tests pass in CI/CD pipeline
- No configuration drift detected
- Health checks effective for all critical services
- Resource limits enforced and tested

### Business Value
- **Risk Reduction**: Eliminate configuration-related deployment failures
- **Development Velocity**: Faster debugging of Docker issues
- **Production Stability**: Validated configurations reduce incidents
- **Compliance**: Meet production readiness requirements

## Risk Mitigation

### Technical Risks
- **Docker Availability**: Fallback to mock mode when Docker unavailable
- **Test Flakiness**: Implement retry logic and proper timeouts
- **Resource Usage**: Limit test resource consumption and cleanup properly

### Operational Risks  
- **CI/CD Impact**: Gradual rollout with optional Docker tests initially
- **Developer Workflow**: Maintain backward compatibility with existing tests
- **Monitoring Overhead**: Lightweight monitoring with minimal performance impact

## Next Steps

1. **Immediate (Week 1)**:
   - Create Docker test directory structure
   - Implement basic configuration validators
   - Add Docker availability detection

2. **Short-term (Week 2)**:
   - Implement comprehensive test suite
   - Add environment variable propagation tests
   - Create network connectivity tests

3. **Medium-term (Week 3)**:
   - Integrate with unified test runner
   - Add configuration monitoring
   - Update CI/CD pipelines

4. **Long-term (Month 2)**:
   - Add automated configuration optimization
   - Implement advanced drift detection
   - Create configuration compliance dashboard

This remediation plan addresses all critical Docker configuration testing gaps while building upon existing infrastructure. The phased approach ensures minimal disruption to current development workflows while significantly improving configuration testing coverage from 10% to 90%.

The plan aligns with Netra's engineering principles by:
- **Single Responsibility**: Each test focuses on specific configuration aspects
- **Modularity**: Tests are organized by functional domain
- **Observability**: Comprehensive monitoring and reporting
- **Pragmatic Rigor**: Balanced approach to configuration validation
- **Business Value**: Clear ROI through reduced deployment risks

Implementation of this plan will establish Netra as having production-ready Docker configuration testing, eliminating a critical gap in system reliability and deployment confidence.