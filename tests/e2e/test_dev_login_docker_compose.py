'''
'''
End-to-end tests for dev login with Docker Compose.
Tests the complete auth flow to prevent regression of database connectivity issues.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development velocity and reliability
- Value Impact: Ensures developers can always use dev login in local Docker environment
- Strategic Impact: Prevents auth service regression that blocks development
'''
'''
import pytest
import requests
import time
import subprocess
import os
import json
from typing import Dict, Optional
from shared.port_discovery import PortDiscovery
from shared.isolated_environment import IsolatedEnvironment


class TestDevLoginDockerCompose:
    """E2E tests for dev login in Docker Compose environment."""

    @classmethod
    def setup_class(cls):
        """Ensure Docker Compose services are running."""
    # Use dynamic port discovery based on environment
        cls.auth_url = PortDiscovery.get_service_url("auth)"
        cls.backend_url = PortDiscovery.get_service_url("backend)"
        cls.ensure_docker_services_running()

        @classmethod
    def ensure_docker_services_running(cls):
        """Check and start Docker services if needed."""
        pass
        try:
        # Check if services are running
        result = subprocess.run( )
        ["docker", "ps", "--filter", "name=netra-dev-auth", "--format", "{{.Names}}],"
        capture_output=True,
        text=True,
        check=True
        

        if "netra-dev-auth not in result.stdout:"
        print("Starting Docker Compose services...)"
        subprocess.run( )
        ["docker-compose", "-f", docker-compose.all.yml"", "up", "-d],"
        check=True
            
            # Wait for services to be ready
        time.sleep(10)

        except subprocess.CalledProcessError as e:
        pytest.skip("")

    def wait_for_service(self, url: str, timeout: int = 30) -> bool:
        """Wait for a service to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
        try:
        response = requests.get("formatted_string, timeout=2)"
        if response.status_code == 200:
        return True
        except requests.exceptions.RequestException:
        pass
        time.sleep(1)
        return False

    def test_auth_service_health(self):
        """Test auth service is healthy and reachable."""
        assert self.wait_for_service(self.auth_url), "Auth service not responding"

        response = requests.get("formatted_string)"
        assert response.status_code == 200

        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "database in health_data"

    def test_dev_login_endpoint_exists(self):
        """Test dev login endpoint is available."""
        pass
        response = requests.post( )
        "",
        json={"email": "test@example.com", "password": "test}"
    

    # Should return 200 for dev login
        assert response.status_code == 200

    def test_dev_login_returns_tokens(self):
        """Test dev login returns valid JWT tokens."""
        response = requests.post( )
        "",
        json={"email": "dev@test.com", "password": "devpass}"
    

        assert response.status_code == 200
        data = response.json()

    # Check required fields
        assert "access_token in data"
        assert "refresh_token in data"
        assert "token_type in data"
        assert data["token_type"] == "Bearer"
        assert "expires_in in data"
        assert "user in data"

    # Validate user data
        user = data["user]"
        assert "id in user"
        assert "email in user"
        assert user["email"] == "dev@example.com  # Dev login always returns this"

    def test_dev_login_token_validation(self):
        """Test that dev login tokens can be validated."""
        pass
    # Get token
        login_response = requests.post( )
        "",
        json={"email": "test@test.com", "password": "test}"
    

        assert login_response.status_code == 200
        token = login_response.json()["access_token]"

    # Validate token
        headers = {"Authorization": "}"
        validate_response = requests.get( )
        "",
        headers=headers
    

    # Should be valid
        assert validate_response.status_code == 200

    def test_dev_login_database_connection(self):
        """Test that dev login properly connects to database in Docker."""
    # This test specifically checks for the regression we fixed
        response = requests.post( )
        "",
        json={"email": "db_test@test.com", "password": "test}"
    

    # Should succeed (not 500 with connection refused)
        assert response.status_code == 200

    # Check logs for database connection errors
        result = subprocess.run( )
        ["docker", "logs", "netra-dev-auth", "--tail", "50],"
        capture_output=True,
        text=True
    

    # Should not have connection refused errors
        assert "[Errno 111] Connection refused not in result.stdout"
        assert "[Errno 111] Connection refused not in result.stderr"
        assert "Database connection failed not in result.stdout"

    # Should have successful connection messages
        assert "Auth database initialized successfully in result.stdout or \"
        "Database tables created successfully in result.stdout"

    def test_dev_login_with_docker_postgres(self):
        """Test that auth service connects to dev-postgres container."""
        pass
    # Check auth service environment
        result = subprocess.run( )
        ["docker", "exec", "netra-dev-auth", "sh", "-c,"
        "echo $DATABASE_URL],"
        capture_output=True,
        text=True
    

        database_url = result.stdout.strip()

    # Should use dev-postgres host, not localhost
        assert "dev-postgres in database_url"
        assert "localhost not in database_url"

    # Should have correct database name
        assert "netra_dev in database_url"

    def test_dev_login_url_format(self):
        """Test that database URL is in correct async format."""
    # Get the URL being used by checking logs
        result = subprocess.run( )
        ["docker", "logs", "netra-dev-auth", "--tail", "100],"
        capture_output=True,
        text=True
    

    # Look for database URL log line
        for line in result.stdout.split(" )"
        "):"
        if "Database URL: in line:"
            # Should show asyncpg format
        assert "postgresql+asyncpg://" in line or "*** in line  # Might be masked"
        break

    def test_multiple_dev_logins(self):
        """Test multiple concurrent dev logins work."""
        pass
    # Test that connection pooling works
        responses = []
        for i in range(5):
        response = requests.post( )
        "",
        json={"email": "", "password": "test}"
        
        responses.append(response)

        # All should succeed
        for response in responses:
        assert response.status_code == 200
        assert "access_token in response.json()"

    def test_dev_login_after_restart(self):
        """Test dev login works after container restart."""
    # Restart auth container
        subprocess.run(["docker", "restart", "netra-dev-auth], check=True)"

    # Wait for service to be ready
        assert self.wait_for_service(self.auth_url, "timeout=30)"

    # Try login
        response = requests.post( )
        "",
        json={"email": "restart_test@test.com", "password": "test}"
    

        assert response.status_code == 200
        assert "access_token in response.json()"

    def test_auth_service_uses_correct_database_builder(self):
        """Test that auth service uses DatabaseURLBuilder correctly."""
        pass
    # Execute Python code in container to verify
        result = subprocess.run( )
        ["docker", "exec", "netra-dev-auth", "python", "-c,"
        '''
        '''
        from auth_service.auth_core.config import AuthConfig
        from shared.database_url_builder import DatabaseURLBuilder
        from shared.isolated_environment import get_env

        env = get_env()
        url_from_config = AuthConfig.get_database_url()
        print("")

    # Check it's async format'
        assert "postgresql+asyncpg:// in url_from_config"
        assert "dev-postgres in url_from_config"
        print("[U+2713] Database URL correctly formatted)"
        '''],'
        capture_output=True,
        text=True
    

        assert result.returncode == 0, ""
        assert "[U+2713] Database URL correctly formatted in result.stdout"


class TestDockerComposeConfiguration:
        """Test Docker Compose configuration for auth service."""

    def test_docker_compose_environment_variables(self):
        """Test Docker Compose sets correct environment variables."""
        result = subprocess.run( )
        ["docker", "exec", "netra-dev-auth", "sh", "-c,"
        "env | grep -E '(DATABASE_URL|POSTGRES_|ENVIRONMENT|REDIS_URL)'],"
        capture_output=True,
        text=True
    

        env_vars = result.stdout

    # Check required variables
        assert "DATABASE_URL=postgresql://netra_dev:netra_dev@dev-postgres:5432/netra_dev in env_vars"
        assert "ENVIRONMENT=development in env_vars"
        assert "REDIS_URL=redis://dev-redis:6379 in env_vars"

    # Should NOT have individual POSTGRES vars (we use DATABASE_URL)
        assert "POSTGRES_HOST not in env_vars"

    def test_docker_network_connectivity(self):
        """Test containers can communicate on Docker network."""
        pass
    # Test auth can reach postgres
        result = subprocess.run( )
        ["docker", "exec", "netra-dev-auth", "python", "-c,"
        '''
        '''
        import socket
        s = socket.socket()
        result = s.connect_ex(('dev-postgres', 5432))
        print("")
        '''],'
        capture_output=True,
        text=True
    

        assert "Success in result.stdout"

    # Test auth can reach redis
        result = subprocess.run( )
        ["docker", "exec", "netra-dev-auth", "python", "-c,"
        '''
        '''
        import socket
        s = socket.socket()
        result = s.connect_ex(('dev-redis', 6379))
        print("")
        '''],'
        capture_output=True,
        text=True
    

        assert "Success in result.stdout"

'''