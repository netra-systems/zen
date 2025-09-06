from shared.isolated_environment import get_env
# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Integration test for frontend startup issues during dev launcher.
# REMOVED_SYNTAX_ERROR: Tests frontend service configuration, build process, and startup dependencies.
""
import pytest
import requests
import subprocess
import os
import time
from netra_backend.app.config import get_config
from shared.isolated_environment import IsolatedEnvironment


# REMOVED_SYNTAX_ERROR: class TestFrontendStartupIssues:
    # REMOVED_SYNTAX_ERROR: """Test frontend startup issues and dependencies."""

# REMOVED_SYNTAX_ERROR: def test_frontend_configuration_check(self):
    # REMOVED_SYNTAX_ERROR: """Test frontend configuration in backend config."""
    # REMOVED_SYNTAX_ERROR: config = get_config()

    # Check frontend URL configuration
    # REMOVED_SYNTAX_ERROR: assert hasattr(config, 'frontend_url'), "Frontend URL missing from config"
    # REMOVED_SYNTAX_ERROR: assert config.frontend_url, "Frontend URL is empty"

    # REMOVED_SYNTAX_ERROR: print("formatted_string")

    # Should be localhost for development
    # REMOVED_SYNTAX_ERROR: if config.environment == "development":
        # REMOVED_SYNTAX_ERROR: assert 'localhost' in config.frontend_url or '127.0.0.1' in config.frontend_url, \
        # REMOVED_SYNTAX_ERROR: "Frontend should use localhost in development"

# REMOVED_SYNTAX_ERROR: def test_frontend_port_availability(self):
    # REMOVED_SYNTAX_ERROR: """Test if frontend port is available or in use."""
    # REMOVED_SYNTAX_ERROR: config = get_config()

    # Extract port from frontend URL
    # REMOVED_SYNTAX_ERROR: import urllib.parse
    # REMOVED_SYNTAX_ERROR: parsed_url = urllib.parse.urlparse(config.frontend_url)
    # REMOVED_SYNTAX_ERROR: port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 3000)
    # REMOVED_SYNTAX_ERROR: host = parsed_url.hostname or 'localhost'

    # REMOVED_SYNTAX_ERROR: print("formatted_string")

    # Try to connect to the port
    # REMOVED_SYNTAX_ERROR: import socket
    # REMOVED_SYNTAX_ERROR: sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # REMOVED_SYNTAX_ERROR: sock.settimeout(2)

    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: result = sock.connect_ex((host, port))
        # REMOVED_SYNTAX_ERROR: if result == 0:
            # REMOVED_SYNTAX_ERROR: print("formatted_string")
            # Could be frontend running or another service
            # REMOVED_SYNTAX_ERROR: else:
                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                # REMOVED_SYNTAX_ERROR: except Exception as e:
                    # REMOVED_SYNTAX_ERROR: print("formatted_string")
                    # REMOVED_SYNTAX_ERROR: finally:
                        # REMOVED_SYNTAX_ERROR: sock.close()

# REMOVED_SYNTAX_ERROR: def test_frontend_health_check(self):
    # REMOVED_SYNTAX_ERROR: """Test frontend health endpoint if available."""
    # REMOVED_SYNTAX_ERROR: config = get_config()
    # REMOVED_SYNTAX_ERROR: frontend_url = config.frontend_url

    # REMOVED_SYNTAX_ERROR: try:
        # Try common frontend health endpoints
        # REMOVED_SYNTAX_ERROR: health_endpoints = [ )
        # REMOVED_SYNTAX_ERROR: '/',
        # REMOVED_SYNTAX_ERROR: '/health',
        # REMOVED_SYNTAX_ERROR: '/api/health',
        # REMOVED_SYNTAX_ERROR: '/_next/static/chunks/pages/index.js'  # Next.js indicator
        

        # REMOVED_SYNTAX_ERROR: accessible_endpoints = []

        # REMOVED_SYNTAX_ERROR: for endpoint in health_endpoints:
            # REMOVED_SYNTAX_ERROR: try:
                # REMOVED_SYNTAX_ERROR: url = "formatted_string"
                # REMOVED_SYNTAX_ERROR: response = requests.get(url, timeout=3)

                # REMOVED_SYNTAX_ERROR: if response.status_code in [200, 301, 302]:
                    # REMOVED_SYNTAX_ERROR: accessible_endpoints.append(endpoint)
                    # REMOVED_SYNTAX_ERROR: print("formatted_string")

                    # REMOVED_SYNTAX_ERROR: except requests.exceptions.RequestException:
                        # REMOVED_SYNTAX_ERROR: pass

                        # REMOVED_SYNTAX_ERROR: if accessible_endpoints:
                            # REMOVED_SYNTAX_ERROR: print("formatted_string")
                            # REMOVED_SYNTAX_ERROR: else:
                                # REMOVED_SYNTAX_ERROR: print("Frontend not accessible - may not be started")

                                # REMOVED_SYNTAX_ERROR: except Exception as e:
                                    # REMOVED_SYNTAX_ERROR: print("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_frontend_directory_exists(self):
    # REMOVED_SYNTAX_ERROR: """Test if frontend directory exists in project."""
    # Look for frontend directory
    # REMOVED_SYNTAX_ERROR: possible_frontend_dirs = [ )
    # REMOVED_SYNTAX_ERROR: 'frontend',
    # REMOVED_SYNTAX_ERROR: '../frontend',
    # REMOVED_SYNTAX_ERROR: 'netra-frontend',
    # REMOVED_SYNTAX_ERROR: 'client',
    # REMOVED_SYNTAX_ERROR: 'web'
    

    # REMOVED_SYNTAX_ERROR: frontend_dir = None
    # REMOVED_SYNTAX_ERROR: for dir_path in possible_frontend_dirs:
        # REMOVED_SYNTAX_ERROR: if os.path.exists(dir_path):
            # REMOVED_SYNTAX_ERROR: frontend_dir = dir_path
            # REMOVED_SYNTAX_ERROR: break

            # REMOVED_SYNTAX_ERROR: if frontend_dir:
                # REMOVED_SYNTAX_ERROR: print("formatted_string")

                # Check for frontend files
                # REMOVED_SYNTAX_ERROR: frontend_files = os.listdir(frontend_dir)
                # REMOVED_SYNTAX_ERROR: print("formatted_string")
            # REMOVED_SYNTAX_ERROR: else:
                # REMOVED_SYNTAX_ERROR: print("Node.js not found or not working")

                # REMOVED_SYNTAX_ERROR: except subprocess.TimeoutExpired:
                    # REMOVED_SYNTAX_ERROR: print("Node.js check timed out")
                    # REMOVED_SYNTAX_ERROR: except FileNotFoundError:
                        # REMOVED_SYNTAX_ERROR: print("Node.js not installed")

                        # REMOVED_SYNTAX_ERROR: try:
                            # Check npm version
                            # REMOVED_SYNTAX_ERROR: npm_result = subprocess.run(['npm', '--version'],
                            # REMOVED_SYNTAX_ERROR: capture_output=True, text=True, timeout=5)

                            # REMOVED_SYNTAX_ERROR: if npm_result.returncode == 0:
                                # REMOVED_SYNTAX_ERROR: npm_version = npm_result.stdout.strip()
                                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                # REMOVED_SYNTAX_ERROR: else:
                                    # REMOVED_SYNTAX_ERROR: print("npm not found or not working")

                                    # REMOVED_SYNTAX_ERROR: except subprocess.TimeoutExpired:
                                        # REMOVED_SYNTAX_ERROR: print("npm check timed out")
                                        # REMOVED_SYNTAX_ERROR: except FileNotFoundError:
                                            # REMOVED_SYNTAX_ERROR: print("npm not installed")

# REMOVED_SYNTAX_ERROR: def test_frontend_build_requirements(self):
    # REMOVED_SYNTAX_ERROR: """Test frontend build requirements."""
    # Look for frontend directory
    # REMOVED_SYNTAX_ERROR: frontend_dirs = ['frontend', '../frontend']

    # REMOVED_SYNTAX_ERROR: for frontend_dir in frontend_dirs:
        # REMOVED_SYNTAX_ERROR: if os.path.exists(frontend_dir):
            # REMOVED_SYNTAX_ERROR: package_json = os.path.join(frontend_dir, 'package.json')

            # REMOVED_SYNTAX_ERROR: if os.path.exists(package_json):
                # REMOVED_SYNTAX_ERROR: print("formatted_string")

                # Check if node_modules exists
                # REMOVED_SYNTAX_ERROR: node_modules = os.path.join(frontend_dir, 'node_modules')
                # REMOVED_SYNTAX_ERROR: if os.path.exists(node_modules):
                    # REMOVED_SYNTAX_ERROR: print("node_modules directory exists")
                    # REMOVED_SYNTAX_ERROR: else:
                        # REMOVED_SYNTAX_ERROR: print("node_modules missing - need to run npm install")

                        # Check for build artifacts
                        # REMOVED_SYNTAX_ERROR: common_build_dirs = ['.next', 'dist', 'build']
                        # REMOVED_SYNTAX_ERROR: for build_dir in common_build_dirs:
                            # REMOVED_SYNTAX_ERROR: build_path = os.path.join(frontend_dir, build_dir)
                            # REMOVED_SYNTAX_ERROR: if os.path.exists(build_path):
                                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                # REMOVED_SYNTAX_ERROR: break
                                # REMOVED_SYNTAX_ERROR: else:
                                    # REMOVED_SYNTAX_ERROR: print("No build artifacts found - may need to build frontend")

                                    # REMOVED_SYNTAX_ERROR: break

# REMOVED_SYNTAX_ERROR: def test_frontend_cors_configuration(self):
    # REMOVED_SYNTAX_ERROR: """Test CORS configuration for frontend-backend communication."""
    # REMOVED_SYNTAX_ERROR: config = get_config()

    # Check if there's CORS configuration
    # REMOVED_SYNTAX_ERROR: if hasattr(config, 'allowed_origins'):
        # REMOVED_SYNTAX_ERROR: print("formatted_string")

        # Frontend URL should be in allowed origins for CORS
        # REMOVED_SYNTAX_ERROR: frontend_url = config.frontend_url
        # REMOVED_SYNTAX_ERROR: backend_url = config.api_base_url

        # REMOVED_SYNTAX_ERROR: print("formatted_string")
        # REMOVED_SYNTAX_ERROR: print("formatted_string")

        # These should be compatible for CORS
        # REMOVED_SYNTAX_ERROR: if frontend_url and backend_url:
            # REMOVED_SYNTAX_ERROR: from urllib.parse import urlparse
            # REMOVED_SYNTAX_ERROR: frontend_parsed = urlparse(frontend_url)
            # REMOVED_SYNTAX_ERROR: backend_parsed = urlparse(backend_url)

            # Check ports are different (typical setup)
            # REMOVED_SYNTAX_ERROR: if frontend_parsed.port and backend_parsed.port:
                # REMOVED_SYNTAX_ERROR: if frontend_parsed.port == backend_parsed.port:
                    # REMOVED_SYNTAX_ERROR: print("Warning: Frontend and backend using same port")
                    # REMOVED_SYNTAX_ERROR: else:
                        # REMOVED_SYNTAX_ERROR: print("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_frontend_environment_variables(self):
    # REMOVED_SYNTAX_ERROR: """Test frontend environment variables."""
    # Check for frontend-related environment variables
    # REMOVED_SYNTAX_ERROR: frontend_env_vars = [ )
    # REMOVED_SYNTAX_ERROR: 'FRONTEND_URL',
    # REMOVED_SYNTAX_ERROR: 'NEXT_PUBLIC_API_URL',
    # REMOVED_SYNTAX_ERROR: 'REACT_APP_API_URL',
    # REMOVED_SYNTAX_ERROR: 'VUE_APP_API_URL',
    # REMOVED_SYNTAX_ERROR: 'PUBLIC_API_URL'
    

    # REMOVED_SYNTAX_ERROR: found_vars = {}
    # REMOVED_SYNTAX_ERROR: for var in frontend_env_vars:
        # REMOVED_SYNTAX_ERROR: value = get_env().get(var)
        # REMOVED_SYNTAX_ERROR: if value:
            # REMOVED_SYNTAX_ERROR: found_vars[var] = value

            # REMOVED_SYNTAX_ERROR: if found_vars:
                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                # REMOVED_SYNTAX_ERROR: else:
                    # REMOVED_SYNTAX_ERROR: print("No frontend-specific environment variables found")


                    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                        # Run this test to check frontend startup issues
                        # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "-s"])
