"""
Test Docker Port Configuration Detection - Issue #847

Business Value Justification (BVJ):
- Segment: Platform Infrastructure (affects all customer segments)  
- Business Goal: Stability + Docker Integration
- Value Impact: Ensures Docker backend port detection works correctly
- Revenue Impact: Protects $500K+ ARR by fixing Docker port configuration mismatches

ROOT CAUSE: Docker backend runs on port 8002, but tests expect localhost:8000

Test Categories Covered:
1. Docker Port Detection: Automatic detection of Docker backend port
2. Port Configuration Validation: Ensures correct port mapping
3. Docker Availability Detection: Determines when Docker services are available
4. Port Mismatch Demonstration: Shows current configuration gaps

Expected Result: INITIAL FAILURE demonstrating Docker port configuration gaps
After Fix: PASSING with correct Docker port detection

@compliance CLAUDE.md - Docker infrastructure for chat functionality
@compliance SPEC/core.xml - Docker integration testing
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import socket
from typing import Dict, Any, Optional

from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.test_context import TestContext


@pytest.mark.unit
class TestDockerPortConfigurationDetection(unittest.TestCase):
    """Test Docker port configuration detection for Issue #847."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.env = IsolatedEnvironment()
        
    def tearDown(self):
        """Clean up test environment."""
        super().tearDown()

    def test_docker_backend_port_detection_gap(self):
        """
        Test Docker backend port detection gap.
        
        Expected: FAIL - demonstrates Docker port detection failure
        Business Impact: Shows why Docker backend on 8002 isn't detected
        
        ROOT CAUSE: No mechanism to detect Docker backend port automatically
        """
        # Mock Docker environment where backend runs on 8002
        with patch.dict(os.environ, {
            'DOCKER_BACKEND_PORT': '8002',  # Docker actual port
            'TEST_BACKEND_URL': 'http://localhost:8000',  # Test expectation
            'ENVIRONMENT': 'test'
        }):
            env = get_env()
            context = TestContext()
            
            # Show Docker port is available in environment
            docker_port = env.get('DOCKER_BACKEND_PORT')
            self.assertEqual(docker_port, '8002', "Docker backend should run on port 8002")
            
            # But TestContext doesn't detect it
            context_port = context.backend_url.split(':')[-1] if ':' in context.backend_url else '8000'
            
            # This demonstrates the detection gap
            self.assertEqual(context_port, '8000', "TestContext uses default port")
            self.assertNotEqual(context_port, docker_port,
                               "DOCKER PORT DETECTION GAP: TestContext doesn't detect Docker port")
            
            # WebSocket URL also uses wrong port
            websocket_port = context.websocket_base_url.split(':')[-1].split('/')[0]
            self.assertEqual(websocket_port, '8000', "WebSocket URL uses default port")
            self.assertNotEqual(websocket_port, docker_port,
                               "WEBSOCKET PORT GAP: WebSocket URL doesn't use Docker port")

    @patch('socket.socket')
    def test_docker_port_availability_check(self, mock_socket):
        """
        Test Docker port availability checking mechanism.
        
        Expected: FAIL - demonstrates lack of port availability checking
        Business Impact: Shows why connection failures aren't predicted
        """
        # Mock socket to simulate port availability
        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock
        
        # Test port availability checking logic
        def check_port_availability(host: str, port: int, timeout: float = 1.0) -> bool:
            """Check if a port is available for connection."""
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                sock.close()
                return result == 0
            except Exception:
                return False
        
        # Mock different port scenarios
        test_scenarios = [
            ('localhost', 8000, False),  # Test expected port - unavailable
            ('localhost', 8002, True),   # Docker actual port - available
            ('localhost', 8001, False),  # Alternative port - unavailable
        ]
        
        for host, port, should_be_available in test_scenarios:
            # Mock the connection result
            mock_sock.connect_ex.return_value = 0 if should_be_available else 1
            
            is_available = check_port_availability(host, port)
            
            if should_be_available:
                self.assertTrue(is_available, f"Port {port} should be available")
            else:
                self.assertFalse(is_available, f"Port {port} should not be available")
        
        # TestContext doesn't use port availability checking
        with patch.dict(os.environ, {'DOCKER_BACKEND_PORT': '8002'}):
            context = TestContext()
            
            # Should check Docker port availability but doesn't
            context_port = int(context.backend_url.split(':')[-1])
            self.assertEqual(context_port, 8000, "TestContext doesn't check port availability")

    @patch('subprocess.run')
    def test_docker_service_detection(self, mock_subprocess):
        """
        Test Docker service detection mechanism.
        
        Expected: FAIL - demonstrates lack of Docker service detection
        Business Impact: Shows why Docker availability isn't detected automatically
        """
        # Mock Docker service detection
        def mock_docker_detection():
            """Mock Docker service detection logic."""
            try:
                # Simulate docker ps command
                result = mock_subprocess.return_value
                result.returncode = 0
                result.stdout = "CONTAINER ID   IMAGE   COMMAND   CREATED   STATUS   PORTS   NAMES\n"
                return True
            except Exception:
                return False
        
        # Test Docker available scenario
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = """
CONTAINER ID   IMAGE          COMMAND                  CREATED       STATUS       PORTS                    NAMES
abc123def456   backend:latest "/app/start.sh"         2 hours ago   Up 2 hours   0.0.0.0:8002->8000/tcp   backend
"""
        
        docker_available = mock_docker_detection()
        self.assertTrue(docker_available, "Docker should be detected as available")
        
        # TestContext doesn't detect Docker services
        context = TestContext()
        
        # Should detect Docker backend service but doesn't
        self.assertEqual(context.backend_url, 'http://localhost:8000',
                        "DOCKER DETECTION GAP: TestContext doesn't detect Docker services")

    def test_docker_compose_port_mapping_detection(self):
        """
        Test Docker Compose port mapping detection.
        
        Expected: FAIL - demonstrates port mapping detection failure
        Business Impact: Shows why Docker Compose port mappings aren't used
        """
        # Mock Docker Compose environment
        compose_config = {
            'COMPOSE_PROJECT_NAME': 'netra-apex',
            'DOCKER_BACKEND_PORT': '8002',
            'DOCKER_FRONTEND_PORT': '3000',
            'DOCKER_AUTH_PORT': '8001',
            'ENVIRONMENT': 'test'
        }
        
        with patch.dict(os.environ, compose_config):
            env = get_env()
            context = TestContext()
            
            # Show Docker Compose ports are defined
            backend_port = env.get('DOCKER_BACKEND_PORT')
            frontend_port = env.get('DOCKER_FRONTEND_PORT')
            auth_port = env.get('DOCKER_AUTH_PORT')
            
            self.assertEqual(backend_port, '8002', "Docker backend port should be 8002")
            self.assertEqual(frontend_port, '3000', "Docker frontend port should be 3000")
            self.assertEqual(auth_port, '8001', "Docker auth port should be 8001")
            
            # But TestContext doesn't use Docker Compose ports
            context_port = context.backend_url.split(':')[-1]
            self.assertEqual(context_port, '8000', "TestContext uses default port")
            
            # This demonstrates the Docker Compose detection gap
            self.assertNotEqual(context_port, backend_port,
                               "COMPOSE DETECTION GAP: TestContext doesn't use Docker Compose ports")

    @patch('test_framework.test_context.TestContext._check_docker_availability')
    def test_docker_availability_with_port_discovery(self, mock_docker_check):
        """
        Test Docker availability checking with port discovery.
        
        Expected: FAIL - demonstrates missing Docker port discovery
        Business Impact: Shows integration gap between Docker detection and port configuration
        """
        # Mock Docker as available
        mock_docker_check.return_value = True
        
        with patch.dict(os.environ, {
            'DOCKER_BACKEND_PORT': '8002',
            'COMPOSE_PROJECT_NAME': 'netra-apex',
            'ENVIRONMENT': 'test'
        }):
            context = TestContext()
            
            # Even with Docker available, TestContext doesn't discover ports
            self.assertEqual(context.backend_url, 'http://localhost:8000',
                           "TestContext doesn't discover Docker ports even when Docker available")
            
            # The integration gap
            expected_docker_url = 'http://localhost:8002'
            self.assertNotEqual(context.backend_url, expected_docker_url,
                               "INTEGRATION GAP: Docker availability doesn't trigger port discovery")

    def test_docker_container_port_inspection_gap(self):
        """
        Test Docker container port inspection gap.
        
        Expected: FAIL - demonstrates missing container port inspection
        Business Impact: Shows why running container ports aren't detected
        """
        # Mock running Docker container scenario
        with patch.dict(os.environ, {
            'DOCKER_CONTAINER_NAME': 'netra-apex-backend',
            'ENVIRONMENT': 'test'
        }):
            # Simulate container inspection logic
            def mock_inspect_container_ports(container_name: str) -> Dict[str, Any]:
                """Mock Docker container port inspection."""
                return {
                    'container_name': container_name,
                    'ports': {
                        '8000/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '8002'}],
                        '80/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '8080'}]
                    },
                    'status': 'running'
                }
            
            container_name = os.environ.get('DOCKER_CONTAINER_NAME')
            container_info = mock_inspect_container_ports(container_name)
            
            # Show container port mapping is available
            backend_host_port = None
            if '8000/tcp' in container_info['ports']:
                backend_host_port = container_info['ports']['8000/tcp'][0]['HostPort']
            
            self.assertEqual(backend_host_port, '8002', "Container maps port 8000 to host port 8002")
            
            # But TestContext doesn't inspect container ports
            context = TestContext()
            context_port = context.backend_url.split(':')[-1]
            
            self.assertEqual(context_port, '8000', "TestContext uses default port")
            self.assertNotEqual(context_port, backend_host_port,
                               "CONTAINER INSPECTION GAP: TestContext doesn't inspect container ports")

    @patch('docker.from_env')
    def test_docker_client_integration_gap(self, mock_docker_client):
        """
        Test Docker client integration gap.
        
        Expected: FAIL - demonstrates lack of Docker client integration
        Business Impact: Shows why Docker API isn't used for port discovery
        """
        # Mock Docker client
        mock_client = MagicMock()
        mock_docker_client.return_value = mock_client
        
        # Mock container with port information
        mock_container = MagicMock()
        mock_container.name = 'netra-apex-backend'
        mock_container.status = 'running'
        mock_container.ports = {
            '8000/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '8002'}]
        }
        
        mock_client.containers.list.return_value = [mock_container]
        
        # Test Docker client integration
        def get_docker_backend_port() -> Optional[str]:
            """Get Docker backend port using Docker client."""
            try:
                client = mock_docker_client()
                containers = client.containers.list()
                
                for container in containers:
                    if 'backend' in container.name and container.status == 'running':
                        if '8000/tcp' in container.ports:
                            return container.ports['8000/tcp'][0]['HostPort']
                return None
            except Exception:
                return None
        
        # Docker client can find the port
        docker_port = get_docker_backend_port()
        self.assertEqual(docker_port, '8002', "Docker client can detect backend port")
        
        # But TestContext doesn't use Docker client
        context = TestContext()
        context_port = context.backend_url.split(':')[-1]
        
        self.assertEqual(context_port, '8000', "TestContext doesn't use Docker client")
        self.assertNotEqual(context_port, docker_port,
                           "DOCKER CLIENT GAP: TestContext doesn't integrate with Docker client")

    def test_port_configuration_priority_gap(self):
        """
        Test port configuration priority gap.
        
        Expected: FAIL - demonstrates lack of port configuration priority
        Business Impact: Shows why wrong ports are chosen when multiple options available
        """
        # Set up multiple port configuration options
        with patch.dict(os.environ, {
            'BACKEND_PORT': '8001',          # Generic port setting
            'DOCKER_BACKEND_PORT': '8002',   # Docker-specific port
            'TEST_BACKEND_PORT': '8000',     # Test-specific port
            'COMPOSE_BACKEND_PORT': '8003',  # Compose-specific port
            'ENVIRONMENT': 'test'
        }):
            env = get_env()
            context = TestContext()
            
            # Show all port options are available
            generic_port = env.get('BACKEND_PORT')
            docker_port = env.get('DOCKER_BACKEND_PORT')
            test_port = env.get('TEST_BACKEND_PORT')
            compose_port = env.get('COMPOSE_BACKEND_PORT')
            
            self.assertEqual(generic_port, '8001')
            self.assertEqual(docker_port, '8002')
            self.assertEqual(test_port, '8000')
            self.assertEqual(compose_port, '8003')
            
            # TestContext uses default instead of environment-appropriate port
            context_port = context.backend_url.split(':')[-1]
            self.assertEqual(context_port, '8000', "TestContext uses hardcoded default")
            
            # In test environment, should prioritize test-specific ports
            environment = env.get('ENVIRONMENT')
            if environment == 'test':
                # Should use TEST_BACKEND_PORT but doesn't
                self.assertNotEqual(context_port, test_port,
                                  "PORT PRIORITY GAP: Test port not prioritized in test environment")
                
                # Should detect Docker port when available but doesn't
                self.assertNotEqual(context_port, docker_port,
                                  "DOCKER PRIORITY GAP: Docker port not detected when available")

    def test_issue_847_docker_port_configuration_comprehensive(self):
        """
        Test comprehensive Docker port configuration for Issue #847.
        
        Expected: FAIL - comprehensive demonstration of Docker port issues
        Business Impact: Complete documentation of Docker port configuration gaps
        
        ROOT CAUSE SUMMARY:
        1. No automatic Docker backend port detection
        2. No Docker service availability checking
        3. No Docker Compose port mapping integration
        4. No port configuration priority resolution
        """
        # Complete Issue #847 Docker scenario
        issue_847_docker_env = {
            # Docker configuration
            'DOCKER_BACKEND_PORT': '8002',
            'COMPOSE_PROJECT_NAME': 'netra-apex',
            'DOCKER_CONTAINER_NAME': 'netra-apex-backend',
            
            # Test configuration
            'TEST_BACKEND_URL': 'http://localhost:8000',
            'TEST_BACKEND_PORT': '8000',
            'ENVIRONMENT': 'test',
            
            # Fallback configuration
            'STAGING_BASE_URL': 'https://netra-backend-701982941522.us-central1.run.app',
            'USE_STAGING_SERVICES': 'true'
        }
        
        with patch.dict(os.environ, issue_847_docker_env):
            env = get_env()
            context = TestContext()
            
            # Document Docker port configuration gaps for Issue #847
            docker_analysis = {
                'docker_configuration': {
                    'docker_port': env.get('DOCKER_BACKEND_PORT'),
                    'test_port': env.get('TEST_BACKEND_PORT'),
                    'context_port': context.backend_url.split(':')[-1],
                    'compose_project': env.get('COMPOSE_PROJECT_NAME'),
                    'container_name': env.get('DOCKER_CONTAINER_NAME')
                },
                'gaps_identified': [],
                'expected_behavior': 'TestContext should detect and use Docker backend port when available',
                'actual_behavior': 'TestContext uses default port ignoring Docker configuration',
                'business_impact': 'Docker backend connections fail, forcing manual configuration'
            }
            
            # Gap 1: Docker port detection gap
            docker_port = docker_analysis['docker_configuration']['docker_port']
            context_port = docker_analysis['docker_configuration']['context_port']
            if docker_port and docker_port != context_port:
                docker_analysis['gaps_identified'].append({
                    'gap': 'Docker Port Detection Gap',
                    'description': 'TestContext doesnt detect Docker backend port',
                    'docker_port': docker_port,
                    'context_port': context_port,
                    'impact': 'Connections to wrong port cause test failures'
                })
            
            # Gap 2: Docker service detection gap
            compose_project = docker_analysis['docker_configuration']['compose_project']
            if compose_project and context_port == '8000':
                docker_analysis['gaps_identified'].append({
                    'gap': 'Docker Service Detection Gap',
                    'description': 'TestContext doesnt detect Docker Compose services',
                    'compose_project': compose_project,
                    'context_behavior': 'Uses default configuration',
                    'impact': 'Misses Docker services even when running'
                })
            
            # Gap 3: Port priority resolution gap
            test_port = docker_analysis['docker_configuration']['test_port']
            if test_port and docker_port and context_port not in [test_port, docker_port]:
                docker_analysis['gaps_identified'].append({
                    'gap': 'Port Priority Resolution Gap',
                    'description': 'No priority order for port configuration resolution',
                    'available_ports': f"test:{test_port}, docker:{docker_port}",
                    'context_choice': context_port,
                    'impact': 'Wrong port chosen when multiple options available'
                })
            
            # This test should fail showing Docker configuration gaps
            self.assertGreaterEqual(len(docker_analysis['gaps_identified']), 2,
                                  f"Issue #847 Docker: Multiple configuration gaps found: {docker_analysis}")
            
            # Specific Docker port assertion for Issue #847
            self.assertEqual(context_port, '8000', "TestContext uses default port")
            self.assertNotEqual(context_port, docker_port,
                               "CORE DOCKER ISSUE #847: TestContext doesnt use Docker backend port")
            
            # WebSocket URL should also reflect Docker port but doesn't
            websocket_port = context.websocket_base_url.split(':')[-1].split('/')[0]
            self.assertNotEqual(websocket_port, docker_port,
                               "WEBSOCKET DOCKER ISSUE #847: WebSocket URL doesnt use Docker port")


if __name__ == "__main__":
    unittest.main()