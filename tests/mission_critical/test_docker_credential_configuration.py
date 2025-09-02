"""
Mission Critical Test Suite: Docker Credential Configuration
Tests for P0 issues identified in DOCKER_UNIFIED_AUDIT_REPORT.md

This test suite validates:
1. Database credentials match environment configurations
2. Port discovery works correctly across environments
3. Service URLs are built with correct credentials
"""

import os
import sys
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
from test_framework.dynamic_port_allocator import DynamicPortAllocator, PortRange
from shared.isolated_environment import IsolatedEnvironment


class TestDockerCredentialConfiguration:
    """Test suite for Docker credential configuration mismatches."""
    
    # Expected credentials per environment (from docker-compose files)
    EXPECTED_CREDENTIALS = {
        "development": {
            "postgres_user": "netra",
            "postgres_password": "netra123", 
            "postgres_db": "netra_dev"
        },
        "test": {
            "postgres_user": "test_user",
            "postgres_password": "test_pass",
            "postgres_db": "netra_test"
        },
        "alpine_test": {
            "postgres_user": "test",
            "postgres_password": "test",
            "postgres_db": "netra_test"
        }
    }
    
    def test_postgres_credentials_match_docker_compose_development(self):
        """Test that development environment uses correct PostgreSQL credentials."""
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEVELOPMENT,
            use_alpine=False
        )
        
        # Test _build_service_url  
        port = 5432
        url = manager._build_service_url_from_port("postgres", port)
        
        # Current implementation uses hardcoded test:test
        # Should use netra:netra123 for development
        expected_url = f"postgresql://netra:netra123@localhost:{port}/netra_dev"
        
        # This test should FAIL because current implementation uses test:test
        assert url == expected_url, (
            f"Development environment should use netra:netra123, "
            f"but got URL: {url}"
        )
    
    def test_postgres_credentials_match_docker_compose_test(self):
        """Test that test environment uses correct PostgreSQL credentials."""
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.SHARED,
            use_alpine=False
        )
        
        # Test _build_service_url
        port = 5434
        url = manager._build_service_url_from_port("postgres", port)
        
        # Should use test_user:test_pass for test
        expected_url = f"postgresql://test_user:test_pass@localhost:{port}/netra_test"
        
        assert url == expected_url, (
            f"Test environment should use test_user:test_pass, "
            f"but got URL: {url}"
        )
    
    def test_postgres_credentials_match_docker_compose_alpine(self):
        """Test that Alpine test environment uses correct PostgreSQL credentials."""
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.SHARED,
            use_alpine=True
        )
        
        # Test _build_service_url
        port = 5435
        url = manager._build_service_url_from_port("postgres", port)
        
        # Should use test:test for Alpine
        expected_url = f"postgresql://test:test@localhost:{port}/netra_test"
        
        assert url == expected_url, (
            f"Alpine test environment should use test:test, "
            f"but got URL: {url}"
        )
    
    def test_environment_detection_based_on_compose_file(self):
        """Test that UnifiedDockerManager detects environment from active docker-compose."""
        manager = UnifiedDockerManager()
        
        # Should have a method to detect environment
        assert hasattr(manager, 'detect_environment'), (
            "UnifiedDockerManager should have detect_environment method"
        )
        
        # Test detection logic
        env_type = manager.detect_environment()
        assert env_type in [EnvironmentType.DEVELOPMENT, EnvironmentType.SHARED, EnvironmentType.DEDICATED], (
            f"Environment detection should return valid EnvironmentType, got {env_type}"
        )
    
    def test_dynamic_credential_loading_from_config(self):
        """Test that credentials are loaded dynamically based on environment."""
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEVELOPMENT
        )
        
        # Should have environment-specific credentials
        assert hasattr(manager, 'get_database_credentials'), (
            "UnifiedDockerManager should have get_database_credentials method"
        )
        
        creds = manager.get_database_credentials()
        assert creds['user'] == 'netra', f"Development should use 'netra' user, got {creds['user']}"
        assert creds['password'] == 'netra123', f"Development should use 'netra123' password"
        assert creds['database'] == 'netra_dev', f"Development should use 'netra_dev' database"


class TestPortDiscovery:
    """Test suite for port discovery and allocation issues."""
    
    def test_port_discovery_from_existing_containers(self):
        """Test that port discovery correctly identifies running container ports."""
        manager = UnifiedDockerManager()
        
        # Mock docker ps output with real container data
        mock_output = """
        CONTAINER ID   IMAGE                   COMMAND                  CREATED          STATUS          PORTS                    NAMES
        abc123         netra-dev-backend       "python app.py"          10 minutes ago   Up 10 minutes   0.0.0.0:8000->8000/tcp   netra-core-generation-1-dev-backend-1
        def456         netra-dev-postgres      "postgres"               10 minutes ago   Up 10 minutes   0.0.0.0:5433->5432/tcp   netra-core-generation-1-dev-postgres-1
        """
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout=mock_output,
                stderr="",
                returncode=0
            )
            
            # This should discover ports from running containers
            ports = manager._discover_ports_from_existing_containers()
            
            assert 'backend' in ports, "Should discover backend service"
            assert ports['backend'] == 8000, "Backend should be on port 8000"
            assert 'postgres' in ports, "Should discover postgres service"
            assert ports['postgres'] == 5433, "Postgres should be on port 5433"
    
    def test_port_allocator_respects_compose_mappings(self):
        """Test that port allocator respects docker-compose port mappings."""
        allocator = DynamicPortAllocator(
            port_range=PortRange.DEVELOPMENT,
            environment_id="dev"
        )
        
        # Should respect existing compose file mappings
        # Development uses: postgres=5433, backend=8000, auth=8081
        result = allocator.allocate_port("postgres", preferred_port=5433)
        assert result.success, "Should allocate preferred port when available"
        assert result.port == 5433, f"Should use compose-defined port 5433, got {result.port}"
    
    def test_port_conflict_resolution(self):
        """Test that port conflicts are properly resolved."""
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.SHARED
        )
        
        # Simulate port conflict
        with patch.object(manager.port_allocator, 'is_port_available') as mock_available:
            # First call returns False (conflict), second returns True
            mock_available.side_effect = [False, True]
            
            ports = manager._allocate_service_ports()
            
            # Should have allocated alternative ports
            assert len(ports) > 0, "Should allocate ports despite conflicts"


class TestServiceURLConstruction:
    """Test suite for service URL construction issues."""
    
    def test_service_url_uses_environment_credentials(self):
        """Test that service URLs include correct environment-specific credentials."""
        # Test for each environment
        environments = [
            (EnvironmentType.DEVELOPMENT, "netra", "netra123", "netra_dev"),
            (EnvironmentType.SHARED, "test_user", "test_pass", "netra_test"),
        ]
        
        for env_type, expected_user, expected_pass, expected_db in environments:
            manager = UnifiedDockerManager(environment_type=env_type)
            
            # Build PostgreSQL URL
            port = 5432
            url = manager._build_service_url_from_port("postgres", port)
            
            # Parse and validate URL
            assert expected_user in url, f"URL should contain user '{expected_user}' for {env_type}"
            assert expected_pass in url, f"URL should contain password '{expected_pass}' for {env_type}"
            assert expected_db in url, f"URL should contain database '{expected_db}' for {env_type}"
    
    def test_database_url_environment_variable_setting(self):
        """Test that DATABASE_URL is set with correct credentials."""
        env = IsolatedEnvironment()
        
        with patch.object(env, 'set') as mock_set:
            manager = UnifiedDockerManager(
                environment_type=EnvironmentType.DEVELOPMENT
            )
            
            # Simulate setting up environment
            manager._setup_environment_for_e2e({'postgres': 5433})
            
            # Check DATABASE_URL was set with correct credentials
            calls = mock_set.call_args_list
            db_url_call = None
            for call in calls:
                if call[0][0] == 'DATABASE_URL':
                    db_url_call = call
                    break
            
            assert db_url_call is not None, "DATABASE_URL should be set"
            db_url = db_url_call[0][1]
            assert 'netra:netra123' in db_url, f"Development DATABASE_URL should use netra:netra123"


class TestEnvironmentIsolation:
    """Test suite for environment isolation and configuration."""
    
    def test_container_name_patterns_match_environment(self):
        """Test that container names follow environment-specific patterns."""
        patterns = {
            EnvironmentType.DEVELOPMENT: "netra-core-generation-1-dev-",
            EnvironmentType.SHARED: "netra-core-generation-1-test-",
        }
        
        for env_type, expected_prefix in patterns.items():
            manager = UnifiedDockerManager(environment_type=env_type)
            
            # Get expected container names
            for service in manager.SERVICES:
                container_name = manager._get_container_name(service)
                assert container_name.startswith(expected_prefix), (
                    f"Container name should start with '{expected_prefix}' "
                    f"for {env_type}, got {container_name}"
                )
    
    def test_network_isolation_between_environments(self):
        """Test that different environments use isolated networks."""
        dev_manager = UnifiedDockerManager(environment_type=EnvironmentType.DEVELOPMENT)
        test_manager = UnifiedDockerManager(environment_type=EnvironmentType.SHARED)
        
        dev_network = dev_manager._get_network_name()
        test_network = test_manager._get_network_name()
        
        assert dev_network != test_network, (
            f"Development and test environments should use different networks, "
            f"but both use {dev_network}"
        )


class TestConfigurationValidation:
    """Test suite for configuration validation."""
    
    def test_validate_compose_file_matches_manager_config(self):
        """Test that docker-compose files match UnifiedDockerManager configuration."""
        manager = UnifiedDockerManager()
        
        # Should have validation method
        assert hasattr(manager, 'validate_configuration'), (
            "UnifiedDockerManager should have validate_configuration method"
        )
        
        # Validate configuration
        validation_result = manager.validate_configuration()
        
        assert validation_result['is_valid'], (
            f"Configuration validation failed: {validation_result.get('errors', [])}"
        )
    
    def test_startup_credential_check(self):
        """Test that startup includes credential validation."""
        manager = UnifiedDockerManager()
        
        with patch('subprocess.run') as mock_run:
            # Mock successful postgres connection test
            mock_run.return_value = MagicMock(returncode=0)
            
            # Start services should validate credentials
            result = manager.start_services(['postgres'])
            
            # Should have attempted credential validation
            assert mock_run.called, "Should validate database credentials on startup"


if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v", "--tb=short"])