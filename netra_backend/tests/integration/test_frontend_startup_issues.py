"""
Integration test for frontend startup issues during dev launcher.
Tests frontend service configuration, build process, and startup dependencies.
"""
import pytest
import requests
import subprocess
import os
import time
from netra_backend.app.config import get_config


class TestFrontendStartupIssues:
    """Test frontend startup issues and dependencies."""

    def test_frontend_configuration_check(self):
        """Test frontend configuration in backend config."""
        config = get_config()
        
        # Check frontend URL configuration
        assert hasattr(config, 'frontend_url'), "Frontend URL missing from config"
        assert config.frontend_url, "Frontend URL is empty"
        
        print(f"Frontend URL: {config.frontend_url}")
        
        # Should be localhost for development
        if config.environment == "development":
            assert 'localhost' in config.frontend_url or '127.0.0.1' in config.frontend_url, \
                "Frontend should use localhost in development"

    def test_frontend_port_availability(self):
        """Test if frontend port is available or in use."""
        config = get_config()
        
        # Extract port from frontend URL
        import urllib.parse
        parsed_url = urllib.parse.urlparse(config.frontend_url)
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 3000)
        host = parsed_url.hostname or 'localhost'
        
        print(f"Testing frontend port: {host}:{port}")
        
        # Try to connect to the port
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        
        try:
            result = sock.connect_ex((host, port))
            if result == 0:
                print(f"Port {port} is in use")
                # Could be frontend running or another service
            else:
                print(f"Port {port} is available (result: {result})")
        except Exception as e:
            print(f"Error checking port {port}: {e}")
        finally:
            sock.close()

    def test_frontend_health_check(self):
        """Test frontend health endpoint if available."""
        config = get_config()
        frontend_url = config.frontend_url
        
        try:
            # Try common frontend health endpoints
            health_endpoints = [
                '/',
                '/health',
                '/api/health',
                '/_next/static/chunks/pages/index.js'  # Next.js indicator
            ]
            
            accessible_endpoints = []
            
            for endpoint in health_endpoints:
                try:
                    url = f"{frontend_url}{endpoint}"
                    response = requests.get(url, timeout=3)
                    
                    if response.status_code in [200, 301, 302]:
                        accessible_endpoints.append(endpoint)
                        print(f"Accessible endpoint: {endpoint} ({response.status_code})")
                        
                except requests.exceptions.RequestException:
                    pass
            
            if accessible_endpoints:
                print(f"Frontend appears to be running - accessible endpoints: {accessible_endpoints}")
            else:
                print("Frontend not accessible - may not be started")
                
        except Exception as e:
            print(f"Error checking frontend health: {e}")

    def test_frontend_directory_exists(self):
        """Test if frontend directory exists in project."""
        # Look for frontend directory
        possible_frontend_dirs = [
            'frontend',
            '../frontend',
            'netra-frontend',
            'client',
            'web'
        ]
        
        frontend_dir = None
        for dir_path in possible_frontend_dirs:
            if os.path.exists(dir_path):
                frontend_dir = dir_path
                break
        
        if frontend_dir:
            print(f"Found frontend directory: {frontend_dir}")
            
            # Check for frontend files
            frontend_files = os.listdir(frontend_dir)
            print(f"Frontend files: {frontend_files[:5]}...")  # Show first 5
            
            # Look for package.json
            if 'package.json' in frontend_files:
                print("Found package.json - appears to be Node.js frontend")
            
            # Look for common frontend frameworks
            if 'next.config.js' in frontend_files:
                print("Detected Next.js frontend")
            elif 'angular.json' in frontend_files:
                print("Detected Angular frontend")
            elif 'vue.config.js' in frontend_files:
                print("Detected Vue frontend")
            
        else:
            print("No frontend directory found in expected locations")

    def test_frontend_dependencies_check(self):
        """Test frontend dependencies like Node.js."""
        try:
            # Check Node.js version
            node_result = subprocess.run(['node', '--version'], 
                                       capture_output=True, text=True, timeout=5)
            
            if node_result.returncode == 0:
                node_version = node_result.stdout.strip()
                print(f"Node.js version: {node_version}")
            else:
                print("Node.js not found or not working")
                
        except subprocess.TimeoutExpired:
            print("Node.js check timed out")
        except FileNotFoundError:
            print("Node.js not installed")
        
        try:
            # Check npm version
            npm_result = subprocess.run(['npm', '--version'],
                                      capture_output=True, text=True, timeout=5)
            
            if npm_result.returncode == 0:
                npm_version = npm_result.stdout.strip()
                print(f"npm version: {npm_version}")
            else:
                print("npm not found or not working")
                
        except subprocess.TimeoutExpired:
            print("npm check timed out")
        except FileNotFoundError:
            print("npm not installed")

    def test_frontend_build_requirements(self):
        """Test frontend build requirements."""
        # Look for frontend directory
        frontend_dirs = ['frontend', '../frontend']
        
        for frontend_dir in frontend_dirs:
            if os.path.exists(frontend_dir):
                package_json = os.path.join(frontend_dir, 'package.json')
                
                if os.path.exists(package_json):
                    print(f"Found package.json at: {package_json}")
                    
                    # Check if node_modules exists
                    node_modules = os.path.join(frontend_dir, 'node_modules')
                    if os.path.exists(node_modules):
                        print("node_modules directory exists")
                    else:
                        print("node_modules missing - need to run npm install")
                    
                    # Check for build artifacts
                    common_build_dirs = ['.next', 'dist', 'build']
                    for build_dir in common_build_dirs:
                        build_path = os.path.join(frontend_dir, build_dir)
                        if os.path.exists(build_path):
                            print(f"Build directory found: {build_dir}")
                            break
                    else:
                        print("No build artifacts found - may need to build frontend")
                        
                break

    def test_frontend_cors_configuration(self):
        """Test CORS configuration for frontend-backend communication."""
        config = get_config()
        
        # Check if there's CORS configuration
        if hasattr(config, 'allowed_origins'):
            print(f"CORS allowed origins: {config.allowed_origins}")
        
        # Frontend URL should be in allowed origins for CORS
        frontend_url = config.frontend_url
        backend_url = config.api_base_url
        
        print(f"Frontend URL: {frontend_url}")
        print(f"Backend URL: {backend_url}")
        
        # These should be compatible for CORS
        if frontend_url and backend_url:
            from urllib.parse import urlparse
            frontend_parsed = urlparse(frontend_url)
            backend_parsed = urlparse(backend_url)
            
            # Check ports are different (typical setup)
            if frontend_parsed.port and backend_parsed.port:
                if frontend_parsed.port == backend_parsed.port:
                    print("Warning: Frontend and backend using same port")
                else:
                    print(f"Different ports: Frontend {frontend_parsed.port}, Backend {backend_parsed.port}")

    def test_frontend_environment_variables(self):
        """Test frontend environment variables."""
        # Check for frontend-related environment variables
        frontend_env_vars = [
            'FRONTEND_URL',
            'NEXT_PUBLIC_API_URL', 
            'REACT_APP_API_URL',
            'VUE_APP_API_URL',
            'PUBLIC_API_URL'
        ]
        
        found_vars = {}
        for var in frontend_env_vars:
            value = os.getenv(var)
            if value:
                found_vars[var] = value
        
        if found_vars:
            print(f"Frontend environment variables found: {found_vars}")
        else:
            print("No frontend-specific environment variables found")


if __name__ == "__main__":
    # Run this test to check frontend startup issues
    pytest.main([__file__, "-v", "-s"])