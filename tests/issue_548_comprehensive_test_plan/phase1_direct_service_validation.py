"""
Issue #548 - Phase 1: Direct Service Validation Tests
FAILING-TEST-REGRESSION-P0: Docker Golden Path Execution Blocked

Purpose: Create failing tests that demonstrate Docker dependency blocking Golden Path tests.
These tests are DESIGNED TO FAIL to validate that Issue #548 exists as described.

Test Plan Context: 4-Phase comprehensive test approach
- Phase 1: Direct Service Validation (THIS FILE)
- Phase 2: Golden Path Component tests  
- Phase 3: Integration tests without Docker
- Phase 4: E2E Staging tests

CRITICAL: These tests must fail appropriately when Docker is not available,
demonstrating the exact issue described in Issue #548.
"""

import pytest
import asyncio
import time
from typing import Dict, List, Any, Optional
import socket
import requests
import subprocess

# Test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.real_services_test_fixtures import real_services_fixture


class TestPhase1DirectServiceValidation(SSotAsyncTestCase):
    """
    Phase 1: Direct Service Validation - Tests that require Docker services.
    
    These tests are DESIGNED TO FAIL when Docker is not available,
    demonstrating the exact Docker dependency issue described in Issue #548.
    
    EXPECTED BEHAVIOR:
    - When Docker is available: Tests should pass
    - When Docker is NOT available: Tests should fail with clear Docker dependency errors
    
    This validates that Issue #548 exists by showing real dependency failures.
    """
    
    def setup_method(self, method=None):
        """Setup test environment and record test intent."""
        super().setup_method(method)
        self.record_metric("test_phase", "1_direct_service_validation")
        self.record_metric("expected_to_fail_without_docker", True)
        self.record_metric("demonstrates_issue_548", True)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.docker_required
    def test_docker_redis_service_availability_required(self, real_services_fixture):
        """
        Test: Redis service availability check through Docker.
        
        EXPECTED TO FAIL when Docker is not running.
        This demonstrates the exact Docker dependency blocking Golden Path tests.
        """
        # Attempt to connect to Redis service that requires Docker
        try:
            import redis
            # Try to connect to Redis (requires Docker container)
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            
            # This should fail if Docker Redis container is not running
            redis_client.ping()
            
            # If we reach here, Docker is available
            self.record_metric("redis_service_available", True)
            self.record_metric("docker_dependency_satisfied", True)
            
            # Test basic Redis operations
            test_key = f"issue_548_test_{int(time.time())}"
            redis_client.set(test_key, "docker_service_test")
            result = redis_client.get(test_key)
            
            assert result == "docker_service_test", f"Redis operation failed: {result}"
            
            # Cleanup
            redis_client.delete(test_key)
            
        except Exception as e:
            # This is the EXPECTED failure demonstrating Issue #548
            self.record_metric("redis_service_available", False)
            self.record_metric("docker_dependency_failure", True)
            self.record_metric("error_type", type(e).__name__)
            self.record_metric("error_message", str(e))
            
            # Re-raise to demonstrate the blocking issue
            raise AssertionError(
                f"ISSUE #548 DEMONSTRATED: Docker dependency blocking test execution. "
                f"Redis service not available (requires Docker): {e}"
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.docker_required
    def test_docker_postgres_service_connectivity_required(self, real_services_fixture):
        """
        Test: PostgreSQL service connectivity through Docker.
        
        EXPECTED TO FAIL when Docker is not running.
        This demonstrates database dependency for Golden Path persistence tests.
        """
        try:
            import psycopg2
            from psycopg2 import sql
            
            # Try to connect to PostgreSQL (requires Docker container)
            connection = psycopg2.connect(
                host='localhost',
                port=5432,
                database='test_db',
                user='test_user',
                password='test_password'
            )
            
            # If connection succeeds, test basic operations
            cursor = connection.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            
            self.record_metric("postgres_service_available", True)
            self.record_metric("postgres_version", str(version[0]) if version else "unknown")
            
            # Test table creation for Golden Path persistence
            test_table = f"issue_548_test_{int(time.time())}"
            cursor.execute(sql.SQL("CREATE TABLE {} (id SERIAL PRIMARY KEY, data TEXT)").format(
                sql.Identifier(test_table)))
            cursor.execute(sql.SQL("INSERT INTO {} (data) VALUES (%s)").format(
                sql.Identifier(test_table)), ("docker_test_data",))
            
            connection.commit()
            
            # Cleanup
            cursor.execute(sql.SQL("DROP TABLE {}").format(sql.Identifier(test_table)))
            connection.commit()
            cursor.close()
            connection.close()
            
        except Exception as e:
            # This is the EXPECTED failure demonstrating Issue #548
            self.record_metric("postgres_service_available", False)
            self.record_metric("docker_dependency_failure", True)
            self.record_metric("error_type", type(e).__name__)
            self.record_metric("error_message", str(e))
            
            # Re-raise to demonstrate the blocking issue
            raise AssertionError(
                f"ISSUE #548 DEMONSTRATED: Docker dependency blocking database tests. "
                f"PostgreSQL service not available (requires Docker): {e}"
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    @pytest.mark.docker_required
    def test_docker_services_health_check_required(self, real_services_fixture):
        """
        Test: Docker services health check required for Golden Path tests.
        
        EXPECTED TO FAIL when Docker services are not healthy.
        This demonstrates the broader Docker orchestration dependency.
        """
        try:
            # Check if Docker is running
            result = subprocess.run(['docker', 'ps'], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                raise Exception(f"Docker not running: {result.stderr}")
            
            # Check specific services required for Golden Path
            required_services = ['redis', 'postgres']
            running_containers = result.stdout
            
            for service in required_services:
                if service not in running_containers.lower():
                    raise Exception(f"Required service '{service}' not running in Docker")
            
            self.record_metric("docker_services_healthy", True)
            self.record_metric("all_required_services_running", True)
            
            # Test service connectivity
            for service_port in [6379, 5432]:  # Redis, PostgreSQL
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex(('localhost', service_port))
                sock.close()
                
                if result != 0:
                    raise Exception(f"Service on port {service_port} not accessible")
            
        except Exception as e:
            # This is the EXPECTED failure demonstrating Issue #548
            self.record_metric("docker_services_healthy", False) 
            self.record_metric("docker_orchestration_failure", True)
            self.record_metric("error_type", type(e).__name__)
            self.record_metric("error_message", str(e))
            
            # Re-raise to demonstrate the blocking issue
            raise AssertionError(
                f"ISSUE #548 DEMONSTRATED: Docker services not healthy, blocking Golden Path execution. "
                f"Service health check failed: {e}"
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.docker_required
    def test_golden_path_websocket_docker_dependency(self, real_services_fixture):
        """
        Test: WebSocket services requiring Docker backend services.
        
        EXPECTED TO FAIL when Docker services are not available.
        This demonstrates WebSocket dependency on Docker-orchestrated services.
        """
        try:
            # Test WebSocket server availability (may depend on Docker services)
            websocket_url = "ws://localhost:8000/ws"
            
            # First check if backend server is running
            response = requests.get("http://localhost:8000/health", timeout=5)
            
            if response.status_code != 200:
                raise Exception(f"Backend server not healthy: {response.status_code}")
            
            # Check if health response indicates Docker service dependencies
            health_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            
            # Look for Redis/Database health indicators
            if 'redis' in health_data:
                redis_healthy = health_data['redis'].get('healthy', False)
                if not redis_healthy:
                    raise Exception("Redis service not healthy in backend health check")
            
            if 'database' in health_data:
                db_healthy = health_data['database'].get('healthy', False) 
                if not db_healthy:
                    raise Exception("Database service not healthy in backend health check")
            
            self.record_metric("websocket_docker_dependencies_available", True)
            self.record_metric("backend_services_healthy", True)
            
        except Exception as e:
            # This is the EXPECTED failure demonstrating Issue #548
            self.record_metric("websocket_docker_dependencies_available", False)
            self.record_metric("backend_service_dependency_failure", True)
            self.record_metric("error_type", type(e).__name__)
            self.record_metric("error_message", str(e))
            
            # Re-raise to demonstrate the blocking issue
            raise AssertionError(
                f"ISSUE #548 DEMONSTRATED: WebSocket services require Docker backend dependencies. "
                f"Service dependency check failed: {e}"
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.docker_required
    def test_golden_path_agent_execution_docker_requirements(self, real_services_fixture):
        """
        Test: Agent execution requiring Docker-orchestrated services.
        
        EXPECTED TO FAIL when Docker services are not available.
        This demonstrates agent execution dependency on Docker services.
        """
        try:
            # Agent execution often requires multiple Docker services
            service_requirements = {
                'redis': 6379,      # For caching and session management
                'postgres': 5432,   # For persistence and state
                'backend': 8000     # For agent orchestration
            }
            
            failed_services = []
            
            for service_name, port in service_requirements.items():
                try:
                    if service_name == 'backend':
                        # HTTP health check for backend
                        response = requests.get(f"http://localhost:{port}/health", timeout=5)
                        if response.status_code != 200:
                            failed_services.append(f"{service_name} (HTTP {response.status_code})")
                    else:
                        # Socket connection test for databases
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(3)
                        result = sock.connect_ex(('localhost', port))
                        sock.close()
                        
                        if result != 0:
                            failed_services.append(f"{service_name} (connection failed)")
                            
                except Exception as e:
                    failed_services.append(f"{service_name} ({str(e)})")
            
            if failed_services:
                raise Exception(f"Required services failed: {', '.join(failed_services)}")
            
            self.record_metric("agent_execution_docker_dependencies_available", True)
            self.record_metric("all_agent_services_healthy", True)
            
            # Test agent execution readiness by checking service endpoints
            try:
                # Check agent registry endpoint
                response = requests.get("http://localhost:8000/api/agents", timeout=5)
                if response.status_code not in [200, 404]:  # 404 might be expected
                    raise Exception(f"Agent registry not accessible: {response.status_code}")
                    
            except Exception as e:
                raise Exception(f"Agent execution services not ready: {e}")
            
        except Exception as e:
            # This is the EXPECTED failure demonstrating Issue #548
            self.record_metric("agent_execution_docker_dependencies_available", False)
            self.record_metric("agent_service_dependency_failure", True)
            self.record_metric("error_type", type(e).__name__)
            self.record_metric("error_message", str(e))
            
            # Re-raise to demonstrate the blocking issue
            raise AssertionError(
                f"ISSUE #548 DEMONSTRATED: Agent execution requires Docker-orchestrated services. "
                f"Service dependency validation failed: {e}"
            )


class TestPhase1ServiceConnectivityValidation(SSotAsyncTestCase):
    """
    Additional Phase 1 tests focusing on service connectivity patterns
    that require Docker orchestration for Golden Path functionality.
    """
    
    def setup_method(self, method=None):
        """Setup for connectivity validation tests."""
        super().setup_method(method)
        self.record_metric("test_phase", "1_service_connectivity")
        self.record_metric("focus", "docker_orchestration_dependencies")
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.docker_required
    def test_multi_service_orchestration_required(self, real_services_fixture):
        """
        Test: Multi-service orchestration required for Golden Path.
        
        EXPECTED TO FAIL when Docker orchestration is not available.
        Demonstrates that Golden Path requires coordinated service startup.
        """
        try:
            # Golden Path requires multiple services to be coordinated
            service_chain = [
                ('postgres', 5432, 'database persistence'),
                ('redis', 6379, 'session and caching'),
                ('backend', 8000, 'API and WebSocket services')
            ]
            
            service_statuses = []
            
            for service_name, port, description in service_chain:
                try:
                    if service_name == 'backend':
                        # More detailed backend health check
                        response = requests.get(f"http://localhost:{port}/health", timeout=3)
                        if response.status_code == 200:
                            health_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                            service_statuses.append({
                                'name': service_name,
                                'status': 'healthy',
                                'description': description,
                                'details': health_data
                            })
                        else:
                            service_statuses.append({
                                'name': service_name,
                                'status': 'unhealthy',
                                'description': description,
                                'error': f"HTTP {response.status_code}"
                            })
                    else:
                        # Database service connectivity
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        result = sock.connect_ex(('localhost', port))
                        sock.close()
                        
                        if result == 0:
                            service_statuses.append({
                                'name': service_name,
                                'status': 'connected',
                                'description': description
                            })
                        else:
                            service_statuses.append({
                                'name': service_name,
                                'status': 'connection_failed',
                                'description': description,
                                'error': f"Connection refused on port {port}"
                            })
                            
                except Exception as e:
                    service_statuses.append({
                        'name': service_name,
                        'status': 'error',
                        'description': description,
                        'error': str(e)
                    })
            
            # Check for any failures in the service chain
            failed_services = [s for s in service_statuses if s['status'] not in ['healthy', 'connected']]
            
            if failed_services:
                failure_details = [f"{s['name']}: {s.get('error', s['status'])}" for s in failed_services]
                raise Exception(f"Service orchestration failed: {', '.join(failure_details)}")
            
            self.record_metric("service_orchestration_successful", True)
            self.record_metric("all_services_coordinated", True)
            self.record_metric("service_statuses", service_statuses)
            
        except Exception as e:
            # This is the EXPECTED failure demonstrating Issue #548
            self.record_metric("service_orchestration_successful", False)
            self.record_metric("docker_orchestration_dependency_failure", True)
            self.record_metric("error_type", type(e).__name__)
            self.record_metric("error_message", str(e))
            
            # Re-raise to demonstrate the blocking issue
            raise AssertionError(
                f"ISSUE #548 DEMONSTRATED: Golden Path requires Docker service orchestration. "
                f"Multi-service coordination failed: {e}"
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.docker_required
    def test_docker_compose_service_dependencies(self, real_services_fixture):
        """
        Test: Docker Compose service dependencies for Golden Path.
        
        EXPECTED TO FAIL when Docker Compose services are not running.
        Demonstrates dependency on Docker Compose orchestration.
        """
        try:
            # Check if Docker Compose is managing our services
            result = subprocess.run(['docker-compose', 'ps'], 
                                  capture_output=True, text=True, timeout=10,
                                  cwd='.')
            
            if result.returncode != 0:
                raise Exception(f"Docker Compose not running or configured: {result.stderr}")
            
            compose_output = result.stdout
            expected_services = ['redis', 'postgres', 'backend']  # Example services
            
            running_services = []
            missing_services = []
            
            for service in expected_services:
                if service in compose_output and 'Up' in compose_output:
                    running_services.append(service)
                else:
                    missing_services.append(service)
            
            if missing_services:
                raise Exception(f"Required Docker Compose services not running: {missing_services}")
            
            self.record_metric("docker_compose_orchestration_active", True)
            self.record_metric("running_services", running_services)
            
        except Exception as e:
            # This is the EXPECTED failure demonstrating Issue #548
            self.record_metric("docker_compose_orchestration_active", False)
            self.record_metric("docker_compose_dependency_failure", True)
            self.record_metric("error_type", type(e).__name__)
            self.record_metric("error_message", str(e))
            
            # Re-raise to demonstrate the blocking issue
            raise AssertionError(
                f"ISSUE #548 DEMONSTRATED: Golden Path requires Docker Compose orchestration. "
                f"Docker Compose service dependency validation failed: {e}"
            )


if __name__ == "__main__":
    # Allow running individual test file for debugging
    import sys
    print(f"Issue #548 Phase 1 Tests - Direct Service Validation")
    print(f"These tests are DESIGNED TO FAIL when Docker is not available.")
    print(f"This demonstrates the Docker dependency issue blocking Golden Path tests.")
    
    # Run with pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure to clearly show the issue
        "--no-header"
    ])
    
    sys.exit(exit_code)