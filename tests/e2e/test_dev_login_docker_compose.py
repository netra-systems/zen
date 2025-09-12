# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: End-to-end tests for dev login with Docker Compose.
# REMOVED_SYNTAX_ERROR: Tests the complete auth flow to prevent regression of database connectivity issues.

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: Platform/Internal
    # REMOVED_SYNTAX_ERROR: - Business Goal: Development velocity and reliability
    # REMOVED_SYNTAX_ERROR: - Value Impact: Ensures developers can always use dev login in local Docker environment
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: Prevents auth service regression that blocks development
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import requests
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: import subprocess
    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: from typing import Dict, Optional
    # REMOVED_SYNTAX_ERROR: from shared.port_discovery import PortDiscovery
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment


# REMOVED_SYNTAX_ERROR: class TestDevLoginDockerCompose:
    # REMOVED_SYNTAX_ERROR: """E2E tests for dev login in Docker Compose environment."""

    # REMOVED_SYNTAX_ERROR: @classmethod
# REMOVED_SYNTAX_ERROR: def setup_class(cls):
    # REMOVED_SYNTAX_ERROR: """Ensure Docker Compose services are running."""
    # Use dynamic port discovery based on environment
    # REMOVED_SYNTAX_ERROR: cls.auth_url = PortDiscovery.get_service_url("auth")
    # REMOVED_SYNTAX_ERROR: cls.backend_url = PortDiscovery.get_service_url("backend")
    # REMOVED_SYNTAX_ERROR: cls.ensure_docker_services_running()

    # REMOVED_SYNTAX_ERROR: @classmethod
# REMOVED_SYNTAX_ERROR: def ensure_docker_services_running(cls):
    # REMOVED_SYNTAX_ERROR: """Check and start Docker services if needed."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: try:
        # Check if services are running
        # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
        # REMOVED_SYNTAX_ERROR: ["docker", "ps", "--filter", "name=netra-dev-auth", "--format", "{{.Names}}"],
        # REMOVED_SYNTAX_ERROR: capture_output=True,
        # REMOVED_SYNTAX_ERROR: text=True,
        # REMOVED_SYNTAX_ERROR: check=True
        

        # REMOVED_SYNTAX_ERROR: if "netra-dev-auth" not in result.stdout:
            # REMOVED_SYNTAX_ERROR: print("Starting Docker Compose services...")
            # REMOVED_SYNTAX_ERROR: subprocess.run( )
            # REMOVED_SYNTAX_ERROR: ["docker-compose", "-f", "docker-compose.all.yml", "up", "-d"],
            # REMOVED_SYNTAX_ERROR: check=True
            
            # Wait for services to be ready
            # REMOVED_SYNTAX_ERROR: time.sleep(10)

            # REMOVED_SYNTAX_ERROR: except subprocess.CalledProcessError as e:
                # REMOVED_SYNTAX_ERROR: pytest.skip("formatted_string")

# REMOVED_SYNTAX_ERROR: def wait_for_service(self, url: str, timeout: int = 30) -> bool:
    # REMOVED_SYNTAX_ERROR: """Wait for a service to be available."""
    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: while time.time() - start_time < timeout:
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: response = requests.get("formatted_string", timeout=2)
            # REMOVED_SYNTAX_ERROR: if response.status_code == 200:
                # REMOVED_SYNTAX_ERROR: return True
                # REMOVED_SYNTAX_ERROR: except requests.exceptions.RequestException:
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: time.sleep(1)
                    # REMOVED_SYNTAX_ERROR: return False

# REMOVED_SYNTAX_ERROR: def test_auth_service_health(self):
    # REMOVED_SYNTAX_ERROR: """Test auth service is healthy and reachable."""
    # REMOVED_SYNTAX_ERROR: assert self.wait_for_service(self.auth_url), "Auth service not responding"

    # REMOVED_SYNTAX_ERROR: response = requests.get("formatted_string")
    # REMOVED_SYNTAX_ERROR: assert response.status_code == 200

    # REMOVED_SYNTAX_ERROR: health_data = response.json()
    # REMOVED_SYNTAX_ERROR: assert health_data["status"] == "healthy"
    # REMOVED_SYNTAX_ERROR: assert "database" in health_data

# REMOVED_SYNTAX_ERROR: def test_dev_login_endpoint_exists(self):
    # REMOVED_SYNTAX_ERROR: """Test dev login endpoint is available."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: response = requests.post( )
    # REMOVED_SYNTAX_ERROR: "formatted_string",
    # REMOVED_SYNTAX_ERROR: json={"email": "test@example.com", "password": "test"}
    

    # Should return 200 for dev login
    # REMOVED_SYNTAX_ERROR: assert response.status_code == 200

# REMOVED_SYNTAX_ERROR: def test_dev_login_returns_tokens(self):
    # REMOVED_SYNTAX_ERROR: """Test dev login returns valid JWT tokens."""
    # REMOVED_SYNTAX_ERROR: response = requests.post( )
    # REMOVED_SYNTAX_ERROR: "formatted_string",
    # REMOVED_SYNTAX_ERROR: json={"email": "dev@test.com", "password": "devpass"}
    

    # REMOVED_SYNTAX_ERROR: assert response.status_code == 200
    # REMOVED_SYNTAX_ERROR: data = response.json()

    # Check required fields
    # REMOVED_SYNTAX_ERROR: assert "access_token" in data
    # REMOVED_SYNTAX_ERROR: assert "refresh_token" in data
    # REMOVED_SYNTAX_ERROR: assert "token_type" in data
    # REMOVED_SYNTAX_ERROR: assert data["token_type"] == "Bearer"
    # REMOVED_SYNTAX_ERROR: assert "expires_in" in data
    # REMOVED_SYNTAX_ERROR: assert "user" in data

    # Validate user data
    # REMOVED_SYNTAX_ERROR: user = data["user"]
    # REMOVED_SYNTAX_ERROR: assert "id" in user
    # REMOVED_SYNTAX_ERROR: assert "email" in user
    # REMOVED_SYNTAX_ERROR: assert user["email"] == "dev@example.com"  # Dev login always returns this

# REMOVED_SYNTAX_ERROR: def test_dev_login_token_validation(self):
    # REMOVED_SYNTAX_ERROR: """Test that dev login tokens can be validated."""
    # REMOVED_SYNTAX_ERROR: pass
    # Get token
    # REMOVED_SYNTAX_ERROR: login_response = requests.post( )
    # REMOVED_SYNTAX_ERROR: "formatted_string",
    # REMOVED_SYNTAX_ERROR: json={"email": "test@test.com", "password": "test"}
    

    # REMOVED_SYNTAX_ERROR: assert login_response.status_code == 200
    # REMOVED_SYNTAX_ERROR: token = login_response.json()["access_token"]

    # Validate token
    # REMOVED_SYNTAX_ERROR: headers = {"Authorization": "formatted_string"}
    # REMOVED_SYNTAX_ERROR: validate_response = requests.get( )
    # REMOVED_SYNTAX_ERROR: "formatted_string",
    # REMOVED_SYNTAX_ERROR: headers=headers
    

    # Should be valid
    # REMOVED_SYNTAX_ERROR: assert validate_response.status_code == 200

# REMOVED_SYNTAX_ERROR: def test_dev_login_database_connection(self):
    # REMOVED_SYNTAX_ERROR: """Test that dev login properly connects to database in Docker."""
    # This test specifically checks for the regression we fixed
    # REMOVED_SYNTAX_ERROR: response = requests.post( )
    # REMOVED_SYNTAX_ERROR: "formatted_string",
    # REMOVED_SYNTAX_ERROR: json={"email": "db_test@test.com", "password": "test"}
    

    # Should succeed (not 500 with connection refused)
    # REMOVED_SYNTAX_ERROR: assert response.status_code == 200

    # Check logs for database connection errors
    # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
    # REMOVED_SYNTAX_ERROR: ["docker", "logs", "netra-dev-auth", "--tail", "50"],
    # REMOVED_SYNTAX_ERROR: capture_output=True,
    # REMOVED_SYNTAX_ERROR: text=True
    

    # Should not have connection refused errors
    # REMOVED_SYNTAX_ERROR: assert "[Errno 111] Connection refused" not in result.stdout
    # REMOVED_SYNTAX_ERROR: assert "[Errno 111] Connection refused" not in result.stderr
    # REMOVED_SYNTAX_ERROR: assert "Database connection failed" not in result.stdout

    # Should have successful connection messages
    # REMOVED_SYNTAX_ERROR: assert "Auth database initialized successfully" in result.stdout or \
    # REMOVED_SYNTAX_ERROR: "Database tables created successfully" in result.stdout

# REMOVED_SYNTAX_ERROR: def test_dev_login_with_docker_postgres(self):
    # REMOVED_SYNTAX_ERROR: """Test that auth service connects to dev-postgres container."""
    # REMOVED_SYNTAX_ERROR: pass
    # Check auth service environment
    # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
    # REMOVED_SYNTAX_ERROR: ["docker", "exec", "netra-dev-auth", "sh", "-c",
    # REMOVED_SYNTAX_ERROR: "echo $DATABASE_URL"],
    # REMOVED_SYNTAX_ERROR: capture_output=True,
    # REMOVED_SYNTAX_ERROR: text=True
    

    # REMOVED_SYNTAX_ERROR: database_url = result.stdout.strip()

    # Should use dev-postgres host, not localhost
    # REMOVED_SYNTAX_ERROR: assert "dev-postgres" in database_url
    # REMOVED_SYNTAX_ERROR: assert "localhost" not in database_url

    # Should have correct database name
    # REMOVED_SYNTAX_ERROR: assert "netra_dev" in database_url

# REMOVED_SYNTAX_ERROR: def test_dev_login_url_format(self):
    # REMOVED_SYNTAX_ERROR: """Test that database URL is in correct async format."""
    # Get the URL being used by checking logs
    # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
    # REMOVED_SYNTAX_ERROR: ["docker", "logs", "netra-dev-auth", "--tail", "100"],
    # REMOVED_SYNTAX_ERROR: capture_output=True,
    # REMOVED_SYNTAX_ERROR: text=True
    

    # Look for database URL log line
    # REMOVED_SYNTAX_ERROR: for line in result.stdout.split(" )
    # REMOVED_SYNTAX_ERROR: "):
        # REMOVED_SYNTAX_ERROR: if "Database URL:" in line:
            # Should show asyncpg format
            # REMOVED_SYNTAX_ERROR: assert "postgresql+asyncpg://" in line or "***" in line  # Might be masked
            # REMOVED_SYNTAX_ERROR: break

# REMOVED_SYNTAX_ERROR: def test_multiple_dev_logins(self):
    # REMOVED_SYNTAX_ERROR: """Test multiple concurrent dev logins work."""
    # REMOVED_SYNTAX_ERROR: pass
    # Test that connection pooling works
    # REMOVED_SYNTAX_ERROR: responses = []
    # REMOVED_SYNTAX_ERROR: for i in range(5):
        # REMOVED_SYNTAX_ERROR: response = requests.post( )
        # REMOVED_SYNTAX_ERROR: "formatted_string",
        # REMOVED_SYNTAX_ERROR: json={"email": "formatted_string", "password": "test"}
        
        # REMOVED_SYNTAX_ERROR: responses.append(response)

        # All should succeed
        # REMOVED_SYNTAX_ERROR: for response in responses:
            # REMOVED_SYNTAX_ERROR: assert response.status_code == 200
            # REMOVED_SYNTAX_ERROR: assert "access_token" in response.json()

# REMOVED_SYNTAX_ERROR: def test_dev_login_after_restart(self):
    # REMOVED_SYNTAX_ERROR: """Test dev login works after container restart."""
    # Restart auth container
    # REMOVED_SYNTAX_ERROR: subprocess.run(["docker", "restart", "netra-dev-auth"], check=True)

    # Wait for service to be ready
    # REMOVED_SYNTAX_ERROR: assert self.wait_for_service(self.auth_url, timeout=30)

    # Try login
    # REMOVED_SYNTAX_ERROR: response = requests.post( )
    # REMOVED_SYNTAX_ERROR: "formatted_string",
    # REMOVED_SYNTAX_ERROR: json={"email": "restart_test@test.com", "password": "test"}
    

    # REMOVED_SYNTAX_ERROR: assert response.status_code == 200
    # REMOVED_SYNTAX_ERROR: assert "access_token" in response.json()

# REMOVED_SYNTAX_ERROR: def test_auth_service_uses_correct_database_builder(self):
    # REMOVED_SYNTAX_ERROR: """Test that auth service uses DatabaseURLBuilder correctly."""
    # REMOVED_SYNTAX_ERROR: pass
    # Execute Python code in container to verify
    # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
    # REMOVED_SYNTAX_ERROR: ["docker", "exec", "netra-dev-auth", "python", "-c",
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.config import AuthConfig
    # REMOVED_SYNTAX_ERROR: from shared.database_url_builder import DatabaseURLBuilder
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env

    # REMOVED_SYNTAX_ERROR: env = get_env()
    # REMOVED_SYNTAX_ERROR: url_from_config = AuthConfig.get_database_url()
    # REMOVED_SYNTAX_ERROR: print("formatted_string")

    # Check it's async format
    # REMOVED_SYNTAX_ERROR: assert "postgresql+asyncpg://" in url_from_config
    # REMOVED_SYNTAX_ERROR: assert "dev-postgres" in url_from_config
    # REMOVED_SYNTAX_ERROR: print("[U+2713] Database URL correctly formatted")
    # REMOVED_SYNTAX_ERROR: '''],
    # REMOVED_SYNTAX_ERROR: capture_output=True,
    # REMOVED_SYNTAX_ERROR: text=True
    

    # REMOVED_SYNTAX_ERROR: assert result.returncode == 0, "formatted_string"
    # REMOVED_SYNTAX_ERROR: assert "[U+2713] Database URL correctly formatted" in result.stdout


# REMOVED_SYNTAX_ERROR: class TestDockerComposeConfiguration:
    # REMOVED_SYNTAX_ERROR: """Test Docker Compose configuration for auth service."""

# REMOVED_SYNTAX_ERROR: def test_docker_compose_environment_variables(self):
    # REMOVED_SYNTAX_ERROR: """Test Docker Compose sets correct environment variables."""
    # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
    # REMOVED_SYNTAX_ERROR: ["docker", "exec", "netra-dev-auth", "sh", "-c",
    # REMOVED_SYNTAX_ERROR: "env | grep -E '(DATABASE_URL|POSTGRES_|ENVIRONMENT|REDIS_URL)'"],
    # REMOVED_SYNTAX_ERROR: capture_output=True,
    # REMOVED_SYNTAX_ERROR: text=True
    

    # REMOVED_SYNTAX_ERROR: env_vars = result.stdout

    # Check required variables
    # REMOVED_SYNTAX_ERROR: assert "DATABASE_URL=postgresql://netra_dev:netra_dev@dev-postgres:5432/netra_dev" in env_vars
    # REMOVED_SYNTAX_ERROR: assert "ENVIRONMENT=development" in env_vars
    # REMOVED_SYNTAX_ERROR: assert "REDIS_URL=redis://dev-redis:6379" in env_vars

    # Should NOT have individual POSTGRES vars (we use DATABASE_URL)
    # REMOVED_SYNTAX_ERROR: assert "POSTGRES_HOST" not in env_vars

# REMOVED_SYNTAX_ERROR: def test_docker_network_connectivity(self):
    # REMOVED_SYNTAX_ERROR: """Test containers can communicate on Docker network."""
    # REMOVED_SYNTAX_ERROR: pass
    # Test auth can reach postgres
    # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
    # REMOVED_SYNTAX_ERROR: ["docker", "exec", "netra-dev-auth", "python", "-c",
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: import socket
    # REMOVED_SYNTAX_ERROR: s = socket.socket()
    # REMOVED_SYNTAX_ERROR: result = s.connect_ex(('dev-postgres', 5432))
    # REMOVED_SYNTAX_ERROR: print("formatted_string")
    # REMOVED_SYNTAX_ERROR: '''],
    # REMOVED_SYNTAX_ERROR: capture_output=True,
    # REMOVED_SYNTAX_ERROR: text=True
    

    # REMOVED_SYNTAX_ERROR: assert "Success" in result.stdout

    # Test auth can reach redis
    # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
    # REMOVED_SYNTAX_ERROR: ["docker", "exec", "netra-dev-auth", "python", "-c",
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: import socket
    # REMOVED_SYNTAX_ERROR: s = socket.socket()
    # REMOVED_SYNTAX_ERROR: result = s.connect_ex(('dev-redis', 6379))
    # REMOVED_SYNTAX_ERROR: print("formatted_string")
    # REMOVED_SYNTAX_ERROR: '''],
    # REMOVED_SYNTAX_ERROR: capture_output=True,
    # REMOVED_SYNTAX_ERROR: text=True
    

    # REMOVED_SYNTAX_ERROR: assert "Success" in result.stdout