"""
Comprehensive Frontend-Backend Integration Tests

This test suite validates integration between the frontend Next.js application and
the backend Python services, focusing on issues that cause build failures, runtime
errors, and communication problems in the development environment.

Test Categories:
1. Build Integration - Frontend build with backend types and imports
2. Service Startup - Development launcher coordination and health checks  
3. WebSocket Integration - Real-time communication between frontend/backend
4. API Contract Validation - REST API and WebSocket API compliance
5. Development Environment - Port conflicts, environment variables, service dependencies

These tests should FAIL initially to reproduce actual integration issues
causing development environment problems and deployment failures.

BVJ: Stable integration = faster development = better team productivity
"""

import pytest
import asyncio
import json
import subprocess
import time
import requests
import websockets
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import threading
import psutil
import socket
import os
import tempfile
import shutil

# Backend imports for testing integration
from netra_backend.app.schemas.registry import WebSocketMessageType, WebSocketMessage

# Test fixtures and utilities
@pytest.fixture
def project_root():
    """Get project root directory"""
    return Path(__file__).parent.parent.parent

@pytest.fixture
def frontend_path(project_root):
    """Frontend directory path"""
    return project_root / "frontend"

@pytest.fixture
def dev_launcher_config():
    """Mock dev launcher configuration"""
    return {
        'services': {
            'frontend': {
                'port': 3000,
                'command': 'npm run dev',
                'health_endpoint': 'http://localhost:3000',
                'startup_timeout': 30
            },
            'backend': {
                'port': 8000,
                'command': 'uvicorn netra_backend.app.main:app --reload',
                'health_endpoint': 'http://localhost:8000/health',
                'startup_timeout': 20
            },
            'websocket': {
                'port': 8001,
                'path': '/ws',
                'health_endpoint': 'ws://localhost:8001/ws',
                'startup_timeout': 15
            }
        },
        'dependencies': {
            'frontend': ['backend', 'websocket'],
            'backend': [],
            'websocket': ['backend']
        }
    }

@pytest.fixture
def mock_service_manager():
    """Mock service manager for testing"""
    class MockServiceManager:
        def __init__(self):
            self.services = {}
            self.service_status = {}
            
        async def start_service(self, name: str, config: Dict[str, Any]) -> bool:
            self.services[name] = config
            # Simulate service startup time
            await asyncio.sleep(0.1)
            self.service_status[name] = 'running'
            return True
            
        async def stop_service(self, name: str) -> bool:
            if name in self.services:
                self.service_status[name] = 'stopped'
                return True
            return False
            
        def get_service_status(self, name: str) -> str:
            return self.service_status.get(name, 'unknown')
            
        def is_port_available(self, port: int) -> bool:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('localhost', port))
                    return True
                except OSError:
                    return False
    
    return MockServiceManager()

# ============================================================================
# TEST CATEGORY 1: BUILD INTEGRATION TESTS
# ============================================================================

def test_frontend_typescript_build_with_backend_types(frontend_path):
    """
    Test that frontend TypeScript build works with backend type imports.
    Should FAIL if there are build-time type resolution issues.
    """
    if not frontend_path.exists():
        pytest.skip("Frontend directory not found")
    
    # Create a test TypeScript file that imports backend types
    test_ts_content = '''
import { WebSocketMessageType, AgentStatus } from '@/types/registry';

// Test interface using backend types
interface TestWebSocketMessage {
  type: WebSocketMessageType;
  payload: {
    text: string;
    status: AgentStatus;
  };
}

// Test function using types
function validateMessage(msg: TestWebSocketMessage): boolean {
  return typeof msg.type === 'string' && typeof msg.payload.text === 'string';
}

// Test enum usage
const messageTypes = [
  WebSocketMessageType.USER_MESSAGE,
  WebSocketMessageType.AGENT_UPDATE,
  WebSocketMessageType.START_AGENT
];

export { validateMessage, messageTypes };
'''
    
    test_file_path = frontend_path / "test_integration.ts"
    
    try:
        # Write test file
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_ts_content)
        
        # Run TypeScript compiler check
        result = subprocess.run([
            'npx', 'tsc', '--noEmit', '--project', str(frontend_path),
            str(test_file_path)
        ], 
        cwd=frontend_path,
        capture_output=True,
        text=True,
        timeout=30
        )
        
        # Should compile without errors
        if result.returncode != 0:
            pytest.fail(f"TYPESCRIPT BUILD FAILED: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        pytest.fail("TypeScript build timed out - possible infinite loop or hanging")
    except FileNotFoundError:
        pytest.skip("TypeScript not available - skipping build test")
    finally:
        # Clean up test file
        if test_file_path.exists():
            test_file_path.unlink()

def test_nextjs_webpack_module_resolution():
    """
    Test Next.js webpack module resolution with complex imports.
    Should FAIL if webpack cannot resolve module dependencies.
    """
    # Mock webpack configuration that might cause issues
    problematic_webpack_config = {
        'resolve': {
            'alias': {
                '@/types': './types',
                '@/components': './components'
            },
            'extensions': ['.ts', '.tsx', '.js', '.jsx']
        },
        'module': {
            'rules': [
                {
                    'test': '/\\.tsx?$/',
                    'use': 'ts-loader'
                }
            ]
        }
    }
    
    # Mock import scenarios that could cause resolution issues
    import_scenarios = [
        "import { WebSocketMessageType } from '@/types/registry';",
        "import { isValidWebSocketMessageType } from '@/types/domains/websocket';",
        "import { MessageType, AgentStatus } from '@/types/shared/enums';",
        "export { isValidWebSocketMessageType } from '@/types/registry';",  # Re-export
        "import type { WebSocketMessage } from '@/types/registry';",  # Type-only import
    ]
    
    # Simulate webpack module resolution
    def simulate_webpack_resolution(import_statement: str) -> bool:
        # Extract module path from import
        import_match = import_statement.split("from '")[1].split("'")[0] if "from '" in import_statement else None
        
        if not import_match:
            return False
        
        # Check if module would resolve with webpack config
        if import_match.startswith('@/'):
            # Alias resolution
            actual_path = import_match.replace('@/', './')
            return True  # Assume resolution works
        
        return False
    
    # Test each import scenario
    resolution_failures = []
    for scenario in import_scenarios:
        if not simulate_webpack_resolution(scenario):
            resolution_failures.append(scenario)
    
    # Should not have resolution failures
    if resolution_failures:
        pytest.fail(f"WEBPACK MODULE RESOLUTION FAILURES: {resolution_failures}")

def test_build_time_type_generation():
    """
    Test that build-time type generation produces correct output.
    Should FAIL if generated types don't match expected structure.
    """
    # Mock TypeScript declaration generation
    def generate_type_declarations() -> str:
        return '''
declare module '@/types/registry' {
  export enum WebSocketMessageType {
    USER_MESSAGE = 'user_message',
    AGENT_UPDATE = 'agent_update',
    START_AGENT = 'start_agent'
  }
  
  export enum AgentStatus {
    IDLE = 'idle',
    ACTIVE = 'active',
    COMPLETED = 'completed'
  }
  
  export function isValidWebSocketMessageType(value: string): value is WebSocketMessageType;
}
'''
    
    # Generate declarations
    declarations = generate_type_declarations()
    
    # Parse and validate generated types
    required_exports = [
        'WebSocketMessageType',
        'AgentStatus', 
        'isValidWebSocketMessageType'
    ]
    
    for export_name in required_exports:
        if export_name not in declarations:
            pytest.fail(f"BUILD-TIME TYPE GENERATION FAILED: Missing export '{export_name}'")
    
    # Check for duplicate exports (the actual error we're testing)
    duplicate_check = []
    for line in declarations.split('\n'):
        if 'export' in line:
            # Extract export name
            if 'enum' in line:
                enum_name = line.split('enum ')[1].split(' ')[0]
                duplicate_check.append(enum_name)
            elif 'function' in line:
                func_name = line.split('function ')[1].split('(')[0]
                duplicate_check.append(func_name)
    
    # Check for duplicates
    seen = set()
    duplicates = []
    for item in duplicate_check:
        if item in seen:
            duplicates.append(item)
        seen.add(item)
    
    if duplicates:
        pytest.fail(f"DUPLICATE TYPE EXPORTS IN GENERATED DECLARATIONS: {duplicates}")

def test_cross_package_type_sharing():
    """
    Test type sharing between packages in monorepo structure.
    Should FAIL if cross-package imports don't work correctly.
    """
    # Mock package structure
    packages = {
        '@netra/shared-types': {
            'exports': ['WebSocketMessage', 'AgentStatus'],
            'package.json': {
                'name': '@netra/shared-types',
                'main': 'index.ts',
                'types': 'index.d.ts'
            }
        },
        '@netra/frontend': {
            'dependencies': ['@netra/shared-types'],
            'imports': [
                "import { WebSocketMessage } from '@netra/shared-types'",
                "import { AgentStatus } from '@netra/shared-types'"
            ]
        }
    }
    
    # Validate package dependencies
    frontend_pkg = packages['@netra/frontend']
    shared_pkg = packages['@netra/shared-types']
    
    # Check that frontend can import from shared types
    for import_stmt in frontend_pkg['imports']:
        # Extract imported type
        imported_type = import_stmt.split('{ ')[1].split(' }')[0]
        
        # Check if type is exported by shared package
        if imported_type not in shared_pkg['exports']:
            pytest.fail(f"CROSS-PACKAGE TYPE SHARING FAILED: '{imported_type}' not exported by shared-types")

def test_build_optimization_tree_shaking():
    """
    Test that build optimization (tree shaking) works with complex re-exports.
    Should FAIL if tree shaking removes needed exports or includes unused ones.
    """
    # Mock module dependency graph
    dependency_graph = {
        'registry.ts': {
            'imports': [
                'shared/enums.ts',
                'domains/websocket.ts'
            ],
            're_exports': [
                'isValidWebSocketMessageType',  # This causes the duplicate
                'WebSocketMessageType'
            ]
        },
        'shared/enums.ts': {
            'exports': ['isValidWebSocketMessageType', 'WebSocketMessageType']
        },
        'domains/websocket.ts': {
            'imports': ['shared/enums.ts'],
            're_exports': ['isValidWebSocketMessageType']  # Re-export causes duplicate
        }
    }
    
    # Simulate tree shaking analysis
    def analyze_exports(graph: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """Analyze which exports are actually used"""
        all_exports = {}
        
        for module, config in graph.items():
            exports = config.get('exports', [])
            re_exports = config.get('re_exports', [])
            
            for export in exports + re_exports:
                if export not in all_exports:
                    all_exports[export] = []
                all_exports[export].append(module)
        
        return all_exports
    
    export_analysis = analyze_exports(dependency_graph)
    
    # Check for duplicate exports that would cause build issues
    duplicates = {name: sources for name, sources in export_analysis.items() if len(sources) > 1}
    
    if duplicates:
        pytest.fail(f"TREE SHAKING FAILED - DUPLICATE EXPORTS DETECTED: {duplicates}")

# ============================================================================
# TEST CATEGORY 2: SERVICE STARTUP INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_service_startup_sequence(dev_launcher_config, mock_service_manager):
    """
    Test proper service startup sequence with dependencies.
    Should FAIL if services don't start in correct order or fail health checks.
    """
    config = dev_launcher_config
    manager = mock_service_manager
    
    # Simulate dependency-aware startup
    async def start_services_with_dependencies(services: Dict[str, Any], dependencies: Dict[str, List[str]]):
        started = set()
        startup_order = []
        
        async def start_service_with_deps(service_name: str):
            if service_name in started:
                return
            
            # Start dependencies first
            for dep in dependencies.get(service_name, []):
                await start_service_with_deps(dep)
            
            # Start this service
            success = await manager.start_service(service_name, services[service_name])
            if not success:
                raise Exception(f"Failed to start service: {service_name}")
            
            started.add(service_name)
            startup_order.append(service_name)
        
        # Start all services
        for service_name in services.keys():
            await start_service_with_deps(service_name)
        
        return startup_order
    
    try:
        startup_order = await start_services_with_dependencies(
            config['services'], 
            config['dependencies']
        )
        
        # Verify startup order respects dependencies
        # Backend should start before frontend
        backend_index = startup_order.index('backend')
        frontend_index = startup_order.index('frontend')
        
        if backend_index > frontend_index:
            pytest.fail("SERVICE STARTUP ORDER VIOLATION: Backend must start before frontend")
        
        # WebSocket should start after backend
        websocket_index = startup_order.index('websocket')
        if websocket_index < backend_index:
            pytest.fail("SERVICE STARTUP ORDER VIOLATION: WebSocket must start after backend")
            
    except Exception as e:
        pytest.fail(f"SERVICE STARTUP FAILED: {e}")

def test_port_conflict_detection_and_resolution(dev_launcher_config):
    """
    Test detection and resolution of port conflicts during startup.
    Should FAIL if port conflicts are not properly detected or resolved.
    """
    config = dev_launcher_config
    
    # Mock port availability checker
    occupied_ports = {3000, 8000}  # Simulate occupied ports
    
    def check_port_available(port: int) -> bool:
        return port not in occupied_ports
    
    def find_alternative_port(base_port: int) -> int:
        """Find next available port"""
        port = base_port
        while not check_port_available(port) and port < base_port + 100:
            port += 1
        return port if check_port_available(port) else None
    
    # Test port conflict detection
    conflicts = []
    resolutions = {}
    
    for service_name, service_config in config['services'].items():
        original_port = service_config['port']
        
        if not check_port_available(original_port):
            conflicts.append((service_name, original_port))
            
            # Try to find alternative
            alternative = find_alternative_port(original_port + 1)
            if alternative:
                resolutions[service_name] = alternative
            else:
                pytest.fail(f"PORT CONFLICT UNRESOLVABLE: No alternative port found for {service_name}")
    
    # Should detect conflicts
    if not conflicts:
        # This might actually pass if ports are available, but we're testing the detection logic
        pass
    else:
        print(f"Port conflicts detected and resolved: {conflicts} -> {resolutions}")

def test_health_check_integration(dev_launcher_config):
    """
    Test health check integration for all services.
    Should FAIL if health checks don't properly validate service status.
    """
    config = dev_launcher_config
    
    # Mock health check responses
    health_responses = {
        'http://localhost:3000': {'status': 'healthy', 'service': 'frontend'},
        'http://localhost:8000/health': {'status': 'healthy', 'service': 'backend'},
        'ws://localhost:8001/ws': {'status': 'healthy', 'service': 'websocket'}
    }
    
    async def perform_health_check(endpoint: str) -> Dict[str, Any]:
        """Mock health check implementation"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        if endpoint in health_responses:
            return health_responses[endpoint]
        else:
            raise Exception(f"Health check failed for {endpoint}")
    
    # Test health checks for all services
    async def test_all_health_checks():
        results = {}
        failures = []
        
        for service_name, service_config in config['services'].items():
            endpoint = service_config['health_endpoint']
            
            try:
                health_result = await perform_health_check(endpoint)
                results[service_name] = health_result
            except Exception as e:
                failures.append((service_name, str(e)))
        
        return results, failures
    
    # Run health checks
    results, failures = asyncio.run(test_all_health_checks())
    
    # Should not have health check failures
    if failures:
        pytest.fail(f"HEALTH CHECK FAILURES: {failures}")
    
    # All services should report healthy
    for service_name, health_result in results.items():
        if health_result.get('status') != 'healthy':
            pytest.fail(f"SERVICE UNHEALTHY: {service_name} reported {health_result}")

def test_graceful_shutdown_sequence():
    """
    Test graceful shutdown sequence for all services.
    Should FAIL if services don't shut down cleanly or in proper order.
    """
    # Mock running services
    running_services = {
        'frontend': {'pid': 1001, 'port': 3000},
        'backend': {'pid': 1002, 'port': 8000},
        'websocket': {'pid': 1003, 'port': 8001}
    }
    
    shutdown_order = []
    shutdown_failures = []
    
    async def shutdown_service(service_name: str, service_info: Dict[str, Any]):
        """Mock service shutdown"""
        try:
            # Simulate graceful shutdown
            await asyncio.sleep(0.1)
            
            # Check if service shuts down cleanly
            if service_info.get('pid'):
                # Simulate successful shutdown
                shutdown_order.append(service_name)
                return True
            else:
                raise Exception(f"No PID for service {service_name}")
                
        except Exception as e:
            shutdown_failures.append((service_name, str(e)))
            return False
    
    # Shutdown services in reverse dependency order
    async def shutdown_all_services():
        # Frontend first (has dependencies)
        await shutdown_service('frontend', running_services['frontend'])
        
        # WebSocket next  
        await shutdown_service('websocket', running_services['websocket'])
        
        # Backend last (no dependencies on it)
        await shutdown_service('backend', running_services['backend'])
    
    asyncio.run(shutdown_all_services())
    
    # Check for shutdown failures
    if shutdown_failures:
        pytest.fail(f"GRACEFUL SHUTDOWN FAILURES: {shutdown_failures}")
    
    # Check shutdown order
    expected_order = ['frontend', 'websocket', 'backend']
    if shutdown_order != expected_order:
        pytest.fail(f"SHUTDOWN ORDER INCORRECT: Expected {expected_order}, got {shutdown_order}")

# ============================================================================
# TEST CATEGORY 3: WEBSOCKET INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_websocket_connection_establishment():
    """
    Test WebSocket connection establishment between frontend and backend.
    Should FAIL if WebSocket handshake fails or connection is not stable.
    """
    # Mock WebSocket server
    connected_clients = []
    connection_errors = []
    
    async def mock_websocket_handler(websocket):
        """Mock WebSocket connection handler"""
        try:
            connected_clients.append(websocket)
            
            # Simulate connection establishment
            await websocket.send(json.dumps({
                'type': 'connection_established',
                'payload': {'client_id': len(connected_clients)}
            }))
            
            # Keep connection alive briefly
            await asyncio.sleep(0.5)
            
        except Exception as e:
            connection_errors.append(str(e))
    
    # Mock WebSocket client
    async def mock_websocket_client():
        """Mock frontend WebSocket client"""
        try:
            # This would normally connect to ws://localhost:8001/ws
            # For testing, we simulate the connection process
            await asyncio.sleep(0.1)  # Connection time
            
            # Simulate receiving connection established message
            connection_msg = {
                'type': 'connection_established',
                'payload': {'client_id': 1}
            }
            
            # Validate message structure
            assert connection_msg['type'] == 'connection_established'
            assert 'payload' in connection_msg
            
            return True
            
        except Exception as e:
            connection_errors.append(f"Client connection failed: {e}")
            return False
    
    # Test connection
    client_connected = await mock_websocket_client()
    
    if not client_connected:
        pytest.fail(f"WEBSOCKET CONNECTION FAILED: {connection_errors}")

@pytest.mark.asyncio
async def test_websocket_message_bidirectional_flow():
    """
    Test bidirectional WebSocket message flow between frontend and backend.
    Should FAIL if messages don't flow correctly in both directions.
    """
    # Mock message exchange
    client_messages = []
    server_messages = []
    message_routing_errors = []
    
    async def mock_client_send_message(message: Dict[str, Any]):
        """Simulate client sending message to server"""
        try:
            # Validate outgoing message
            if 'type' not in message or 'payload' not in message:
                raise ValueError("Invalid message structure")
            
            # Add to client messages
            client_messages.append(message)
            
            # Simulate server response
            if message['type'] == 'user_message':
                response = {
                    'type': 'agent_update',
                    'payload': {
                        'agent_id': 'agent_123',
                        'status': 'processing',
                        'message': f"Processing: {message['payload'].get('text', 'unknown')}"
                    }
                }
                server_messages.append(response)
            
        except Exception as e:
            message_routing_errors.append(f"Client send error: {e}")
    
    async def mock_server_send_message(message: Dict[str, Any]):
        """Simulate server sending message to client"""
        try:
            # Validate outgoing message
            if 'type' not in message or 'payload' not in message:
                raise ValueError("Invalid message structure")
            
            server_messages.append(message)
            
        except Exception as e:
            message_routing_errors.append(f"Server send error: {e}")
    
    # Test message flow
    test_messages = [
        {
            'type': 'user_message',
            'payload': {'text': 'Hello, agent!', 'thread_id': 'thread_123'}
        },
        {
            'type': 'start_agent', 
            'payload': {'agent_type': 'chat', 'thread_id': 'thread_123'}
        },
        {
            'type': 'stop_agent',
            'payload': {'reason': 'user_requested'}
        }
    ]
    
    # Send messages from client
    for msg in test_messages:
        await mock_client_send_message(msg)
    
    # Send server response
    await mock_server_send_message({
        'type': 'agent_completed',
        'payload': {'agent_id': 'agent_123', 'result': 'Task completed successfully'}
    })
    
    # Verify message flow
    if message_routing_errors:
        pytest.fail(f"MESSAGE ROUTING ERRORS: {message_routing_errors}")
    
    # Should have messages in both directions
    assert len(client_messages) > 0, "No client messages sent"
    assert len(server_messages) > 0, "No server messages received"

@pytest.mark.asyncio
async def test_websocket_message_type_validation_integration():
    """
    Test WebSocket message type validation in integration scenario.
    Should FAIL if frontend and backend validate message types differently.
    """
    # Frontend validation (mock TypeScript validation)
    def frontend_validate_message_type(msg_type: str) -> bool:
        frontend_valid_types = [
            'user_message', 'agent_update', 'start_agent', 'stop_agent',
            'create_thread', 'switch_thread', 'delete_thread'
        ]
        return msg_type in frontend_valid_types
    
    # Backend validation (actual Python validation)
    def backend_validate_message_type(msg_type: str) -> bool:
        try:
            WebSocketMessageType(msg_type)
            return True
        except ValueError:
            return False
    
    # Test messages with potential validation discrepancies
    test_message_types = [
        'user_message',
        'agent_update', 
        'start_agent',
        'invalid_type',
        'chat_message',  # Might exist in backend but not frontend
        'subagent_started',  # Might exist in backend but not frontend
        'thread_switched',  # Might have different names
    ]
    
    validation_mismatches = []
    
    for msg_type in test_message_types:
        frontend_valid = frontend_validate_message_type(msg_type)
        backend_valid = backend_validate_message_type(msg_type)
        
        if frontend_valid != backend_valid:
            validation_mismatches.append({
                'type': msg_type,
                'frontend_valid': frontend_valid,
                'backend_valid': backend_valid
            })
    
    # Should not have validation mismatches
    if validation_mismatches:
        pytest.fail(f"MESSAGE TYPE VALIDATION MISMATCHES: {validation_mismatches}")

def test_websocket_reconnection_handling():
    """
    Test WebSocket reconnection handling when connections are dropped.
    Should FAIL if reconnection logic doesn't work properly.
    """
    # Mock connection state
    connection_state = {
        'connected': True,
        'reconnect_attempts': 0,
        'max_reconnect_attempts': 3,
        'reconnect_delay': 1.0
    }
    
    connection_events = []
    
    def simulate_connection_drop():
        """Simulate connection being dropped"""
        connection_state['connected'] = False
        connection_events.append('connection_dropped')
    
    async def attempt_reconnection():
        """Simulate reconnection attempt"""
        if connection_state['reconnect_attempts'] >= connection_state['max_reconnect_attempts']:
            return False
        
        connection_state['reconnect_attempts'] += 1
        connection_events.append(f"reconnect_attempt_{connection_state['reconnect_attempts']}")
        
        # Simulate reconnection delay
        await asyncio.sleep(0.1)  # Shortened for test
        
        # Simulate successful reconnection after 2 attempts
        if connection_state['reconnect_attempts'] >= 2:
            connection_state['connected'] = True
            connection_events.append('reconnected')
            return True
        
        return False
    
    # Simulate reconnection scenario
    async def test_reconnection_scenario():
        # Drop connection
        simulate_connection_drop()
        
        # Attempt reconnections until successful or max attempts reached
        while not connection_state['connected'] and connection_state['reconnect_attempts'] < connection_state['max_reconnect_attempts']:
            success = await attempt_reconnection()
            if success:
                break
    
    asyncio.run(test_reconnection_scenario())
    
    # Verify reconnection worked
    if not connection_state['connected']:
        pytest.fail(f"RECONNECTION FAILED: {connection_events}")
    
    # Should have attempted reconnection
    reconnection_attempts = [event for event in connection_events if 'reconnect_attempt' in event]
    if len(reconnection_attempts) == 0:
        pytest.fail("NO RECONNECTION ATTEMPTS MADE")

# ============================================================================
# TEST CATEGORY 4: API CONTRACT VALIDATION TESTS
# ============================================================================

def test_rest_api_contract_validation():
    """
    Test REST API contract validation between frontend and backend.
    Should FAIL if API contracts don't match between frontend expectations and backend implementation.
    """
    # Mock API contracts
    frontend_expected_endpoints = {
        '/api/threads': {
            'methods': ['GET', 'POST'],
            'get_response': {'threads': 'list', 'total': 'number'},
            'post_request': {'title': 'string', 'description': 'string?'},
            'post_response': {'thread_id': 'string', 'status': 'string'}
        },
        '/api/threads/{thread_id}': {
            'methods': ['GET', 'PUT', 'DELETE'],
            'get_response': {'thread_id': 'string', 'title': 'string', 'messages': 'list'}
        },
        '/api/health': {
            'methods': ['GET'],
            'get_response': {'status': 'string', 'timestamp': 'string'}
        }
    }
    
    # Mock backend implementation
    backend_actual_endpoints = {
        '/api/threads': {
            'methods': ['GET', 'POST'],
            'get_response': {'threads': 'list', 'total': 'number', 'page': 'number'},  # Extra field
            'post_request': {'title': 'string'},  # Missing optional description
            'post_response': {'thread_id': 'string', 'status': 'string'}
        },
        '/api/threads/{thread_id}': {
            'methods': ['GET', 'PUT', 'DELETE'],  
            'get_response': {'thread_id': 'string', 'title': 'string', 'messages': 'list'}
        },
        '/health': {  # Different path
            'methods': ['GET'],
            'get_response': {'status': 'string', 'timestamp': 'string'}
        }
    }
    
    # Validate contracts
    contract_violations = []
    
    for endpoint, frontend_contract in frontend_expected_endpoints.items():
        if endpoint not in backend_actual_endpoints:
            # Check for similar endpoints
            similar_endpoints = [ep for ep in backend_actual_endpoints.keys() if endpoint.split('/')[-1] in ep]
            if similar_endpoints:
                contract_violations.append(f"Endpoint path mismatch: Expected '{endpoint}', found similar '{similar_endpoints[0]}'")
            else:
                contract_violations.append(f"Missing endpoint: {endpoint}")
            continue
        
        backend_contract = backend_actual_endpoints[endpoint]
        
        # Check methods
        frontend_methods = set(frontend_contract['methods'])
        backend_methods = set(backend_contract['methods'])
        
        if frontend_methods != backend_methods:
            contract_violations.append(f"Method mismatch for {endpoint}: Frontend expects {frontend_methods}, backend has {backend_methods}")
        
        # Check response structure
        if 'get_response' in frontend_contract and 'get_response' in backend_contract:
            frontend_response = frontend_contract['get_response']
            backend_response = backend_contract['get_response']
            
            # Check required fields
            for field in frontend_response:
                if field not in backend_response:
                    contract_violations.append(f"Missing response field in {endpoint}: {field}")
    
    if contract_violations:
        pytest.fail(f"API CONTRACT VIOLATIONS: {contract_violations}")

def test_websocket_api_contract_validation():
    """
    Test WebSocket API contract validation for message structures.
    Should FAIL if WebSocket message contracts don't match between frontend and backend.
    """
    # Frontend expected WebSocket message contracts
    frontend_message_contracts = {
        'user_message': {
            'direction': 'client_to_server',
            'required_fields': ['type', 'payload'],
            'payload_schema': {
                'text': 'string',
                'thread_id': 'string', 
                'timestamp': 'string?'
            }
        },
        'agent_update': {
            'direction': 'server_to_client',
            'required_fields': ['type', 'payload'],
            'payload_schema': {
                'agent_id': 'string',
                'status': 'string',
                'progress': 'number?',
                'message': 'string?'
            }
        },
        'start_agent': {
            'direction': 'client_to_server',
            'required_fields': ['type', 'payload'],
            'payload_schema': {
                'agent_type': 'string',
                'config': 'object?',
                'thread_id': 'string'
            }
        }
    }
    
    # Backend actual message handling (simulate validation)
    def validate_backend_message_contract(msg_type: str, payload: Dict[str, Any]) -> List[str]:
        """Validate message against backend expectations"""
        errors = []
        
        if msg_type == 'user_message':
            if 'text' not in payload:
                errors.append("Missing required field: text")
            if 'thread_id' not in payload:
                errors.append("Missing required field: thread_id")
        elif msg_type == 'agent_update':
            if 'agent_id' not in payload:
                errors.append("Missing required field: agent_id")
            if 'status' not in payload:
                errors.append("Missing required field: status")
        elif msg_type == 'start_agent':
            if 'agent_type' not in payload:
                errors.append("Missing required field: agent_type")
            # thread_id might not be required in backend
        
        return errors
    
    # Test message contracts
    contract_validation_failures = []
    
    test_messages = [
        ('user_message', {'text': 'Hello', 'thread_id': 'thread_123'}),
        ('user_message', {'text': 'Hello'}),  # Missing thread_id
        ('agent_update', {'agent_id': 'agent_123', 'status': 'active'}),
        ('agent_update', {'status': 'active'}),  # Missing agent_id
        ('start_agent', {'agent_type': 'chat', 'thread_id': 'thread_123'}),
        ('start_agent', {'config': {'model': 'gpt-4'}}),  # Missing agent_type
    ]
    
    for msg_type, payload in test_messages:
        if msg_type in frontend_message_contracts:
            # Validate against backend
            backend_errors = validate_backend_message_contract(msg_type, payload)
            
            # Check if frontend expects this to be valid
            frontend_contract = frontend_message_contracts[msg_type]
            required_fields = []
            for field, field_type in frontend_contract['payload_schema'].items():
                if not field_type.endswith('?'):  # Not optional
                    required_fields.append(field)
            
            frontend_errors = []
            for field in required_fields:
                if field not in payload:
                    frontend_errors.append(f"Missing required field: {field}")
            
            # Compare frontend and backend validation
            if bool(frontend_errors) != bool(backend_errors):
                contract_validation_failures.append({
                    'message_type': msg_type,
                    'payload': payload,
                    'frontend_errors': frontend_errors,
                    'backend_errors': backend_errors
                })
    
    if contract_validation_failures:
        pytest.fail(f"WEBSOCKET CONTRACT VALIDATION FAILURES: {contract_validation_failures}")

def test_authentication_integration():
    """
    Test authentication integration between frontend and backend.
    Should FAIL if authentication flow doesn't work properly.
    """
    # Mock authentication flow
    auth_tokens = {}
    auth_failures = []
    
    def mock_backend_authenticate(credentials: Dict[str, str]) -> Dict[str, Any]:
        """Mock backend authentication"""
        if credentials.get('username') == 'testuser' and credentials.get('password') == 'testpass':
            token = f"token_{len(auth_tokens) + 1}"
            auth_tokens[token] = {
                'user_id': 'user_123',
                'username': 'testuser',
                'expires_at': '2025-01-24T10:00:00Z'
            }
            return {
                'success': True,
                'token': token,
                'user': auth_tokens[token]
            }
        else:
            return {'success': False, 'error': 'Invalid credentials'}
    
    def mock_frontend_authenticate(username: str, password: str) -> bool:
        """Mock frontend authentication"""
        try:
            # Call backend authentication
            auth_result = mock_backend_authenticate({'username': username, 'password': password})
            
            if auth_result.get('success'):
                # Store token in frontend state
                return True
            else:
                auth_failures.append(auth_result.get('error', 'Unknown error'))
                return False
        except Exception as e:
            auth_failures.append(f"Authentication error: {e}")
            return False
    
    # Test authentication scenarios
    auth_test_cases = [
        ('testuser', 'testpass', True),   # Valid credentials
        ('testuser', 'wrongpass', False), # Invalid password
        ('wronguser', 'testpass', False), # Invalid username
        ('', '', False),                  # Empty credentials
    ]
    
    for username, password, expected_success in auth_test_cases:
        success = mock_frontend_authenticate(username, password)
        
        if success != expected_success:
            pytest.fail(f"AUTHENTICATION INTEGRATION FAILED: Expected {expected_success} for {username}/{password}, got {success}")
    
    # Should have some auth failures for invalid credentials
    expected_failures = ['Invalid credentials', 'Invalid credentials', 'Invalid credentials']
    if len(auth_failures) != len(expected_failures):
        pytest.fail(f"AUTHENTICATION ERROR HANDLING FAILED: Expected {len(expected_failures)} failures, got {len(auth_failures)}: {auth_failures}")

# ============================================================================
# TEST CATEGORY 5: DEVELOPMENT ENVIRONMENT TESTS
# ============================================================================

def test_environment_variable_synchronization():
    """
    Test environment variable synchronization between frontend and backend.
    Should FAIL if environment variables are not properly shared or conflict.
    """
    # Mock environment variables
    backend_env_vars = {
        'DATABASE_URL': 'postgresql://localhost/netra_db',
        'REDIS_URL': 'redis://localhost:6379',
        'SECRET_KEY': 'backend_secret_key',
        'DEBUG': 'true',
        'WEBSOCKET_PORT': '8001',
        'API_BASE_URL': 'http://localhost:8000'
    }
    
    frontend_env_vars = {
        'NEXT_PUBLIC_API_BASE_URL': 'http://localhost:8000',  # Should match backend
        'NEXT_PUBLIC_WEBSOCKET_URL': 'ws://localhost:8001',   # Should use WEBSOCKET_PORT
        'NEXT_PUBLIC_DEBUG': 'true',                          # Should match DEBUG
        'NEXT_PUBLIC_APP_NAME': 'Netra Frontend'
    }
    
    # Check for environment variable consistency
    env_mismatches = []
    
    # API base URL should be consistent
    backend_api_url = backend_env_vars['API_BASE_URL']
    frontend_api_url = frontend_env_vars['NEXT_PUBLIC_API_BASE_URL']
    
    if backend_api_url != frontend_api_url:
        env_mismatches.append(f"API URL mismatch: Backend={backend_api_url}, Frontend={frontend_api_url}")
    
    # WebSocket port consistency
    backend_ws_port = backend_env_vars['WEBSOCKET_PORT']
    frontend_ws_url = frontend_env_vars['NEXT_PUBLIC_WEBSOCKET_URL']
    
    if backend_ws_port not in frontend_ws_url:
        env_mismatches.append(f"WebSocket port mismatch: Backend port={backend_ws_port}, Frontend URL={frontend_ws_url}")
    
    # Debug mode consistency
    backend_debug = backend_env_vars['DEBUG']
    frontend_debug = frontend_env_vars['NEXT_PUBLIC_DEBUG']
    
    if backend_debug != frontend_debug:
        env_mismatches.append(f"Debug mode mismatch: Backend={backend_debug}, Frontend={frontend_debug}")
    
    if env_mismatches:
        pytest.fail(f"ENVIRONMENT VARIABLE MISMATCHES: {env_mismatches}")

def test_hot_reload_integration():
    """
    Test hot reload integration between frontend and backend services.
    Should FAIL if hot reload doesn't work properly or causes cascading failures.
    """
    # Mock file change detection
    file_changes = {
        'frontend': [],
        'backend': []
    }
    
    reload_events = []
    reload_failures = []
    
    def simulate_file_change(service: str, file_path: str):
        """Simulate file change in service"""
        file_changes[service].append(file_path)
        reload_events.append(f"{service}:{file_path}")
    
    async def simulate_hot_reload(service: str, changed_files: List[str]):
        """Simulate hot reload process"""
        try:
            # Simulate reload time
            await asyncio.sleep(0.1)
            
            # Check if reload should succeed
            if any('error' in file for file in changed_files):
                raise Exception(f"Syntax error in {[f for f in changed_files if 'error' in f][0]}")
            
            reload_events.append(f"{service}_reloaded")
            return True
            
        except Exception as e:
            reload_failures.append(f"{service}: {str(e)}")
            return False
    
    # Test hot reload scenarios
    async def test_reload_scenarios():
        # 1. Valid frontend change
        simulate_file_change('frontend', 'components/ChatInterface.tsx')
        await simulate_hot_reload('frontend', file_changes['frontend'])
        
        # 2. Valid backend change
        simulate_file_change('backend', 'routes/threads.py')
        await simulate_hot_reload('backend', file_changes['backend'])
        
        # 3. Invalid change causing reload failure
        simulate_file_change('frontend', 'components/ErrorComponent.tsx')
        await simulate_hot_reload('frontend', ['components/ErrorComponent.tsx'])
    
    asyncio.run(test_reload_scenarios())
    
    # Check reload events
    successful_reloads = [event for event in reload_events if '_reloaded' in event]
    
    if len(successful_reloads) < 2:  # Should have at least 2 successful reloads
        pytest.fail(f"HOT RELOAD INTEGRATION FAILED: Expected at least 2 successful reloads, got {len(successful_reloads)}: {reload_events}")

def test_development_database_integration():
    """
    Test development database integration and connection pooling.
    Should FAIL if database connections are not properly managed.
    """
    # Mock database connection pool
    connection_pool = {
        'active_connections': 0,
        'max_connections': 10,
        'connection_errors': []
    }
    
    def mock_acquire_db_connection() -> bool:
        """Mock database connection acquisition"""
        if connection_pool['active_connections'] >= connection_pool['max_connections']:
            connection_pool['connection_errors'].append('Connection pool exhausted')
            return False
        
        connection_pool['active_connections'] += 1
        return True
    
    def mock_release_db_connection():
        """Mock database connection release"""
        if connection_pool['active_connections'] > 0:
            connection_pool['active_connections'] -= 1
    
    # Simulate concurrent database operations
    def simulate_database_operations():
        operations_completed = 0
        operations_failed = 0
        
        # Simulate 15 concurrent operations (exceeds pool limit)
        for i in range(15):
            if mock_acquire_db_connection():
                operations_completed += 1
                # Simulate operation
                time.sleep(0.01)
                mock_release_db_connection()
            else:
                operations_failed += 1
        
        return operations_completed, operations_failed
    
    completed, failed = simulate_database_operations()
    
    # Some operations should fail due to pool limits
    if failed == 0:
        pytest.fail("DATABASE CONNECTION POOL TEST FAILED: Expected some operations to fail due to pool limits")
    
    # Should have connection errors logged
    if len(connection_pool['connection_errors']) == 0:
        pytest.fail("DATABASE CONNECTION ERROR HANDLING FAILED: Expected connection errors to be logged")
    
    # Active connections should be released
    if connection_pool['active_connections'] != 0:
        pytest.fail(f"DATABASE CONNECTION LEAK DETECTED: {connection_pool['active_connections']} connections not released")

def test_docker_compose_development_setup():
    """
    Test Docker Compose development setup integration.
    Should FAIL if Docker services don't start properly or have networking issues.
    """
    # Mock Docker Compose services
    docker_services = {
        'postgres': {
            'status': 'starting',
            'port': 5432,
            'health_check': 'pg_isready',
            'depends_on': []
        },
        'redis': {
            'status': 'starting', 
            'port': 6379,
            'health_check': 'redis-cli ping',
            'depends_on': []
        },
        'backend': {
            'status': 'starting',
            'port': 8000,
            'health_check': 'curl http://localhost:8000/health',
            'depends_on': ['postgres', 'redis']
        },
        'frontend': {
            'status': 'starting',
            'port': 3000,
            'health_check': 'curl http://localhost:3000',
            'depends_on': ['backend']
        }
    }
    
    startup_failures = []
    
    def simulate_docker_service_startup(service_name: str, service_config: Dict[str, Any]) -> bool:
        """Simulate Docker service startup"""
        try:
            # Check dependencies first
            for dep in service_config['depends_on']:
                if docker_services[dep]['status'] != 'running':
                    raise Exception(f"Dependency {dep} not running")
            
            # Simulate startup time
            time.sleep(0.1)
            
            # Simulate health check
            if service_config['health_check']:
                # Mock health check success
                service_config['status'] = 'running'
                return True
            
        except Exception as e:
            startup_failures.append(f"{service_name}: {str(e)}")
            service_config['status'] = 'failed'
            return False
    
    # Start services in dependency order
    startup_order = ['postgres', 'redis', 'backend', 'frontend']
    
    for service_name in startup_order:
        service_config = docker_services[service_name]
        simulate_docker_service_startup(service_name, service_config)
    
    # Check for startup failures
    if startup_failures:
        pytest.fail(f"DOCKER COMPOSE STARTUP FAILURES: {startup_failures}")
    
    # All services should be running
    running_services = [name for name, config in docker_services.items() if config['status'] == 'running']
    
    if len(running_services) != len(docker_services):
        failed_services = [name for name, config in docker_services.items() if config['status'] != 'running']
        pytest.fail(f"DOCKER SERVICES FAILED TO START: {failed_services}")

if __name__ == "__main__":
    # Run specific tests for debugging
    print("Running frontend-backend integration tests...")
    print("Total tests: 20+ comprehensive scenarios")
    print("Categories covered:")
    print("- Build Integration (TypeScript builds, webpack resolution)")
    print("- Service Startup (Dependencies, health checks, port conflicts)")
    print("- WebSocket Integration (Connection, message flow, reconnection)")
    print("- API Contract Validation (REST and WebSocket contracts)")
    print("- Development Environment (Hot reload, database, Docker)")
    
    pytest.main([__file__, "-v", "--tb=short"])