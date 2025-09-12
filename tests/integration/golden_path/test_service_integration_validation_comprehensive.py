"""
SERVICE INTEGRATION VALIDATION for Golden Path - COMPREHENSIVE Testing

[U+1F517] SERVICE INTEGRATION TEST [U+1F517]
This test suite validates that all services integrate correctly to deliver
the golden path user experience. It ensures service boundaries, data flow,
and inter-service communication work reliably under realistic conditions.

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Service Reliability
- Business Goal: Ensure all services work together to deliver business value
- Value Impact: Service integration failures = broken user experience = revenue loss
- Strategic Impact: Validates microservice architecture delivers unified platform value

SERVICE INTEGRATION VALIDATION AREAS:
1. Authentication Service  ->  Backend Service integration
2. Backend Service  ->  Database integration and persistence
3. WebSocket Service  ->  Real-time communication integration
4. Agent Service  ->  Tool execution and LLM integration
5. Cross-service data consistency and state management
6. Error handling and recovery across service boundaries

SUCCESS CRITERIA: All services integrate seamlessly for golden path delivery.
"""

import asyncio
import pytest
import time
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import aiohttp
import httpx

# SSOT imports following CLAUDE.md absolute import rules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context
)
from test_framework.websocket_helpers import WebSocketTestHelpers
from shared.types.core_types import UserID, ThreadID, RunID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestServiceIntegrationValidationComprehensive(SSotAsyncTestCase):
    """
    [U+1F517] COMPREHENSIVE SERVICE INTEGRATION TEST [U+1F517]
    
    Validates that all microservices integrate correctly to deliver
    the complete golden path user experience.
    """
    
    def setup_method(self, method=None):
        """Setup with service integration testing context."""
        super().setup_method(method)
        
        # Service integration metrics
        self.record_metric("service_integration_test", True)
        self.record_metric("microservice_validation", True)
        self.record_metric("cross_service_reliability", True)
        self.record_metric("system_architecture_validation", True)
        
        # Initialize components
        self.environment = self.get_env_var("TEST_ENV", "test")
        self.auth_helper = E2EAuthHelper(environment=self.environment)
        self.websocket_helper = E2EWebSocketAuthHelper(environment=self.environment)
        self.id_generator = UnifiedIdGenerator()
        
        # Service endpoint configuration
        self.backend_url = self.get_env_var("BACKEND_URL", "http://localhost:8000")
        self.auth_service_url = self.get_env_var("AUTH_SERVICE_URL", "http://localhost:8081")
        self.websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        # Service integration tracking
        self.service_health_checks = {}
        self.integration_test_results = {}
        self.active_connections = []
        
    async def async_teardown_method(self, method=None):
        """Cleanup with service integration validation."""
        try:
            # Close WebSocket connections
            for connection in self.active_connections:
                try:
                    await WebSocketTestHelpers.close_test_connection(connection)
                except Exception:
                    pass
            
            # Log integration test results
            if hasattr(self, 'integration_test_results'):
                successful_integrations = sum(1 for result in self.integration_test_results.values() 
                                            if result.get('success', False))
                total_integrations = len(self.integration_test_results)
                if total_integrations > 0:
                    self.record_metric("service_integration_success_rate", 
                                     successful_integrations / total_integrations)
            
        except Exception as e:
            print(f" WARNING: [U+FE0F]  Service integration cleanup error: {e}")
        
        await super().async_teardown_method(method)
    
    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.real_services
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_auth_service_backend_integration_flow(self):
        """
        [U+1F510] AUTH  ->  BACKEND INTEGRATION: Authentication to Backend Service Flow
        
        Tests that authentication service properly integrates with backend service
        for user authentication, session management, and authorized API access.
        """
        auth_backend_start = time.time()
        
        print(f"\n[U+1F510] AUTH  ->  BACKEND INTEGRATION: Testing authentication flow")
        
        # Step 1: Create user through auth service
        try:
            user_data = await self.auth_helper.create_test_user_with_auth(
                email=f"auth_backend_test_{uuid.uuid4().hex[:8]}@example.com",
                name="Auth Backend Integration User"
            )
            
            auth_token = user_data.get("access_token")
            user_id = user_data.get("user_id")
            
            assert auth_token, "Auth service must provide valid access token"
            assert user_id, "Auth service must provide valid user ID"
            
            print(f"    PASS:  Auth service: User created with token")
            
        except Exception as auth_error:
            pytest.fail(f" ALERT:  AUTH SERVICE FAILURE: Cannot create user: {auth_error}")
        
        # Step 2: Validate token with auth service
        try:
            token_validation = await self.auth_helper.validate_jwt_token(auth_token)
            
            assert token_validation.get("valid", False), "Token must be valid"
            assert token_validation.get("user_id") == user_id, "Token must contain correct user ID"
            
            print(f"    PASS:  Auth service: Token validated")
            
        except Exception as validation_error:
            pytest.fail(f" ALERT:  AUTH TOKEN VALIDATION FAILURE: {validation_error}")
        
        # Step 3: Use token to access backend API endpoints
        try:
            auth_headers = self.auth_helper.get_auth_headers(auth_token)
            
            # Test backend API endpoints with auth token
            backend_endpoints = [
                {"path": "/health", "method": "GET", "expected_status": 200},
                {"path": "/api/user/profile", "method": "GET", "expected_status": [200, 404]},  # 404 acceptable if no profile
                {"path": "/api/conversations", "method": "GET", "expected_status": 200}
            ]
            
            endpoint_results = []
            
            async with aiohttp.ClientSession() as session:
                for endpoint in backend_endpoints:
                    endpoint_start = time.time()
                    
                    try:
                        url = f"{self.backend_url}{endpoint['path']}"
                        
                        if endpoint["method"] == "GET":
                            async with session.get(url, headers=auth_headers, timeout=10) as response:
                                response_data = await response.text()
                                
                                expected_statuses = endpoint["expected_status"]
                                if isinstance(expected_statuses, int):
                                    expected_statuses = [expected_statuses]
                                
                                success = response.status in expected_statuses
                                
                                endpoint_results.append({
                                    "path": endpoint["path"],
                                    "success": success,
                                    "status": response.status,
                                    "response_time": time.time() - endpoint_start,
                                    "auth_accepted": response.status != 401  # 401 = auth failure
                                })
                                
                                if success:
                                    print(f"      PASS:  {endpoint['path']}: {response.status}")
                                else:
                                    print(f"      FAIL:  {endpoint['path']}: {response.status} (expected {expected_statuses})")
                                    
                    except Exception as endpoint_error:
                        endpoint_results.append({
                            "path": endpoint["path"],
                            "success": False,
                            "error": str(endpoint_error),
                            "response_time": time.time() - endpoint_start,
                            "auth_accepted": False
                        })
                        print(f"      FAIL:  {endpoint['path']}: {endpoint_error}")
            
            # Validate backend API integration
            successful_endpoints = sum(1 for result in endpoint_results if result.get("success"))
            auth_accepted_endpoints = sum(1 for result in endpoint_results if result.get("auth_accepted"))
            total_endpoints = len(endpoint_results)
            
            backend_integration_success = successful_endpoints >= (total_endpoints * 0.7)  # 70% success threshold
            auth_integration_success = auth_accepted_endpoints >= total_endpoints  # All must accept auth
            
            print(f"    CHART:  Backend endpoints tested: {total_endpoints}")
            print(f"    PASS:  Successful responses: {successful_endpoints}")
            print(f"   [U+1F510] Auth accepted: {auth_accepted_endpoints}")
            
        except Exception as backend_error:
            pytest.fail(f" ALERT:  BACKEND API INTEGRATION FAILURE: {backend_error}")
        
        auth_backend_time = time.time() - auth_backend_start
        
        # Record integration results
        self.integration_test_results["auth_backend"] = {
            "success": backend_integration_success and auth_integration_success,
            "auth_service_working": True,
            "backend_api_success_rate": successful_endpoints / total_endpoints,
            "auth_acceptance_rate": auth_accepted_endpoints / total_endpoints,
            "duration": auth_backend_time,
            "endpoints_tested": total_endpoints
        }
        
        # Validate integration success
        if not auth_integration_success:
            pytest.fail(
                f" ALERT:  AUTH  ->  BACKEND INTEGRATION FAILURE\n"
                f"Auth Acceptance Rate: {auth_accepted_endpoints}/{total_endpoints}\n"
                f"Backend not properly accepting auth service tokens!"
            )
        
        if not backend_integration_success:
            pytest.fail(
                f" ALERT:  BACKEND API INTEGRATION FAILURE\n"
                f"Success Rate: {successful_endpoints}/{total_endpoints}\n"
                f"Backend API endpoints not responding correctly!"
            )
        
        print(f"\n PASS:  AUTH  ->  BACKEND INTEGRATION: SUCCESS")
        print(f"   [U+1F510] Authentication flow: VALIDATED")
        print(f"   [U+1F310] Backend API access: VALIDATED")
        print(f"   [U+23F1][U+FE0F]  Integration time: {auth_backend_time:.2f}s")
        
    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.real_services
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_backend_database_integration_flow(self):
        """
        [U+1F5C4][U+FE0F] BACKEND  ->  DATABASE INTEGRATION: Data Persistence and Retrieval
        
        Tests that backend service properly integrates with database for
        user data persistence, conversation storage, and data consistency.
        """
        backend_db_start = time.time()
        
        print(f"\n[U+1F5C4][U+FE0F] BACKEND  ->  DATABASE INTEGRATION: Testing data persistence")
        
        # Create authenticated user for database testing
        user_data = await self.auth_helper.create_test_user_with_auth(
            email=f"backend_db_test_{uuid.uuid4().hex[:8]}@example.com",
            name="Backend Database Integration User"
        )
        
        auth_token = user_data.get("access_token")
        user_id = user_data.get("user_id")
        auth_headers = self.auth_helper.get_auth_headers(auth_token)
        
        # Test database operations through backend API
        database_operations = []
        
        try:
            async with aiohttp.ClientSession() as session:
                
                # Operation 1: Create conversation (database write)
                create_conversation_data = {
                    "title": "Database Integration Test Conversation",
                    "user_id": user_id,
                    "type": "integration_test"
                }
                
                operation_start = time.time()
                try:
                    url = f"{self.backend_url}/api/conversations"
                    async with session.post(
                        url, 
                        headers=auth_headers, 
                        json=create_conversation_data,
                        timeout=10
                    ) as response:
                        response_data = await response.json() if response.status == 200 else await response.text()
                        
                        conversation_created = response.status in [200, 201]
                        conversation_id = None
                        
                        if conversation_created and isinstance(response_data, dict):
                            conversation_id = response_data.get("id") or response_data.get("conversation_id")
                        
                        database_operations.append({
                            "operation": "create_conversation",
                            "success": conversation_created,
                            "conversation_id": conversation_id,
                            "status": response.status,
                            "response_time": time.time() - operation_start,
                            "data_persisted": conversation_created
                        })
                        
                        print(f"   [U+1F4DD] Create conversation: {' PASS: ' if conversation_created else ' FAIL: '} ({response.status})")
                        
                except Exception as create_error:
                    database_operations.append({
                        "operation": "create_conversation",
                        "success": False,
                        "error": str(create_error),
                        "response_time": time.time() - operation_start,
                        "data_persisted": False
                    })
                    print(f"   [U+1F4DD] Create conversation:  FAIL:  {create_error}")
                
                # Operation 2: Retrieve conversations (database read)
                operation_start = time.time()
                try:
                    url = f"{self.backend_url}/api/conversations"
                    async with session.get(url, headers=auth_headers, timeout=10) as response:
                        response_data = await response.json() if response.status == 200 else await response.text()
                        
                        conversations_retrieved = response.status == 200
                        conversation_count = 0
                        
                        if conversations_retrieved and isinstance(response_data, (list, dict)):
                            if isinstance(response_data, list):
                                conversation_count = len(response_data)
                            elif isinstance(response_data, dict) and "conversations" in response_data:
                                conversation_count = len(response_data["conversations"])
                        
                        database_operations.append({
                            "operation": "retrieve_conversations",
                            "success": conversations_retrieved,
                            "conversation_count": conversation_count,
                            "status": response.status,
                            "response_time": time.time() - operation_start,
                            "data_retrieved": conversations_retrieved
                        })
                        
                        print(f"   [U+1F4D6] Retrieve conversations: {' PASS: ' if conversations_retrieved else ' FAIL: '} ({conversation_count} found)")
                        
                except Exception as retrieve_error:
                    database_operations.append({
                        "operation": "retrieve_conversations",
                        "success": False,
                        "error": str(retrieve_error),
                        "response_time": time.time() - operation_start,
                        "data_retrieved": False
                    })
                    print(f"   [U+1F4D6] Retrieve conversations:  FAIL:  {retrieve_error}")
                
                # Operation 3: Store message in conversation (complex database operation)
                if database_operations and database_operations[0].get("conversation_id"):
                    conversation_id = database_operations[0]["conversation_id"]
                    
                    message_data = {
                        "conversation_id": conversation_id,
                        "content": "Database integration test message",
                        "user_id": user_id,
                        "type": "user_message"
                    }
                    
                    operation_start = time.time()
                    try:
                        url = f"{self.backend_url}/api/conversations/{conversation_id}/messages"
                        async with session.post(
                            url,
                            headers=auth_headers,
                            json=message_data,
                            timeout=10
                        ) as response:
                            response_data = await response.json() if response.status in [200, 201] else await response.text()
                            
                            message_stored = response.status in [200, 201]
                            
                            database_operations.append({
                                "operation": "store_message",
                                "success": message_stored,
                                "status": response.status,
                                "response_time": time.time() - operation_start,
                                "data_persisted": message_stored,
                                "conversation_id": conversation_id
                            })
                            
                            print(f"   [U+1F4AC] Store message: {' PASS: ' if message_stored else ' FAIL: '} ({response.status})")
                            
                    except Exception as message_error:
                        database_operations.append({
                            "operation": "store_message",
                            "success": False,
                            "error": str(message_error),
                            "response_time": time.time() - operation_start,
                            "data_persisted": False
                        })
                        print(f"   [U+1F4AC] Store message:  FAIL:  {message_error}")
                
        except Exception as session_error:
            pytest.fail(f" ALERT:  BACKEND  ->  DATABASE SESSION FAILURE: {session_error}")
        
        backend_db_time = time.time() - backend_db_start
        
        # Analyze database integration results
        successful_operations = sum(1 for op in database_operations if op.get("success"))
        data_persistence_operations = sum(1 for op in database_operations if op.get("data_persisted"))
        data_retrieval_operations = sum(1 for op in database_operations if op.get("data_retrieved"))
        total_operations = len(database_operations)
        
        database_integration_success = successful_operations >= (total_operations * 0.8)  # 80% success threshold
        data_consistency = (data_persistence_operations + data_retrieval_operations) > 0
        
        # Record database integration results
        self.integration_test_results["backend_database"] = {
            "success": database_integration_success and data_consistency,
            "operation_success_rate": successful_operations / total_operations if total_operations > 0 else 0,
            "data_persistence_working": data_persistence_operations > 0,
            "data_retrieval_working": data_retrieval_operations > 0,
            "duration": backend_db_time,
            "operations_tested": total_operations
        }
        
        print(f"\n CHART:  BACKEND  ->  DATABASE INTEGRATION ANALYSIS:")
        print(f"   [U+1F5C4][U+FE0F] Operations tested: {total_operations}")
        print(f"    PASS:  Successful operations: {successful_operations}")
        print(f"   [U+1F4BE] Data persistence: {' PASS: ' if data_persistence_operations > 0 else ' FAIL: '}")
        print(f"   [U+1F4D6] Data retrieval: {' PASS: ' if data_retrieval_operations > 0 else ' FAIL: '}")
        
        # Validate database integration
        if not data_consistency:
            pytest.fail(
                f" ALERT:  DATABASE INTEGRATION FAILURE\n"
                f"Data persistence: {data_persistence_operations > 0}\n"
                f"Data retrieval: {data_retrieval_operations > 0}\n"
                f"Backend not properly integrating with database!"
            )
        
        if not database_integration_success:
            pytest.fail(
                f" ALERT:  BACKEND  ->  DATABASE OPERATION FAILURE\n"
                f"Success Rate: {successful_operations}/{total_operations}\n"
                f"Database operations failing through backend API!"
            )
        
        print(f"\n PASS:  BACKEND  ->  DATABASE INTEGRATION: SUCCESS")
        print(f"   [U+1F5C4][U+FE0F] Data persistence: VALIDATED")
        print(f"   [U+1F4D6] Data retrieval: VALIDATED")
        print(f"   [U+23F1][U+FE0F]  Integration time: {backend_db_time:.2f}s")
        
    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.real_services
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_websocket_backend_integration_flow(self):
        """
        [U+1F310] WEBSOCKET  ->  BACKEND INTEGRATION: Real-time Communication Flow
        
        Tests that WebSocket service properly integrates with backend for
        real-time message delivery, agent communication, and event streaming.
        """
        websocket_backend_start = time.time()
        
        print(f"\n[U+1F310] WEBSOCKET  ->  BACKEND INTEGRATION: Testing real-time communication")
        
        # Create authenticated user for WebSocket testing
        user_context = await create_authenticated_user_context(
            user_email=f"websocket_backend_test_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        jwt_token = self.auth_helper.create_test_jwt_token(
            user_id=str(user_context.user_id),
            email=user_context.agent_context.get('user_email')
        )
        
        # Test WebSocket connection and backend integration
        try:
            # Establish WebSocket connection
            ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
            connection = await WebSocketTestHelpers.create_test_websocket_connection(
                url=self.websocket_url,
                headers=ws_headers,
                timeout=10.0,
                user_id=str(user_context.user_id)
            )
            self.active_connections.append(connection)
            
            print(f"    PASS:  WebSocket connection established")
            
            # Test message flow: WebSocket  ->  Backend  ->  Response
            integration_tests = []
            
            # Test 1: Simple message handling
            test_start = time.time()
            simple_message = {
                "type": "chat_message",
                "content": "WebSocket backend integration test",
                "user_id": str(user_context.user_id),
                "integration_test": True
            }
            
            await WebSocketTestHelpers.send_test_message(
                connection, simple_message, timeout=5.0
            )
            
            # Wait for backend response through WebSocket
            response_received = False
            response_time = None
            
            response_start = time.time()
            while (time.time() - response_start) < 10.0:
                try:
                    response = await WebSocketTestHelpers.receive_test_message(
                        connection, timeout=3.0
                    )
                    
                    if response and isinstance(response, dict):
                        response_received = True
                        response_time = time.time() - test_start
                        break
                        
                except:
                    continue
            
            integration_tests.append({
                "test": "simple_message_flow",
                "success": response_received,
                "response_time": response_time,
                "backend_processing": response_received
            })
            
            print(f"   [U+1F4E8] Simple message flow: {' PASS: ' if response_received else ' FAIL: '}")
            
            # Test 2: Agent request processing (WebSocket  ->  Backend  ->  Agent  ->  WebSocket)
            test_start = time.time()
            agent_message = {
                "type": "chat_message",
                "content": "Test agent processing integration",
                "user_id": str(user_context.user_id),
                "agent_integration_test": True
            }
            
            await WebSocketTestHelpers.send_test_message(
                connection, agent_message, timeout=5.0
            )
            
            # Collect agent processing events
            agent_events = []
            agent_processing_success = False
            
            agent_start = time.time()
            while (time.time() - agent_start) < 20.0:
                try:
                    event = await WebSocketTestHelpers.receive_test_message(
                        connection, timeout=3.0
                    )
                    
                    if event and isinstance(event, dict):
                        event_type = event.get("type")
                        agent_events.append(event_type)
                        
                        # Check for agent processing events
                        if event_type in ["agent_started", "agent_thinking", "agent_completed"]:
                            agent_processing_success = True
                        
                        if event_type == "agent_completed":
                            break
                            
                except:
                    continue
            
            agent_processing_time = time.time() - test_start
            
            integration_tests.append({
                "test": "agent_processing_flow",
                "success": agent_processing_success,
                "processing_time": agent_processing_time,
                "events_received": len(agent_events),
                "backend_agent_integration": agent_processing_success
            })
            
            print(f"   [U+1F916] Agent processing flow: {' PASS: ' if agent_processing_success else ' FAIL: '}")
            
            # Test 3: Bidirectional communication (ensure real-time updates)
            test_start = time.time()
            bidirectional_message = {
                "type": "status_request",
                "user_id": str(user_context.user_id),
                "request_id": str(uuid.uuid4())
            }
            
            await WebSocketTestHelpers.send_test_message(
                connection, bidirectional_message, timeout=5.0
            )
            
            status_response_received = False
            bidirectional_start = time.time()
            
            while (time.time() - bidirectional_start) < 10.0:
                try:
                    response = await WebSocketTestHelpers.receive_test_message(
                        connection, timeout=2.0
                    )
                    
                    if response and isinstance(response, dict):
                        if response.get("type") in ["status_response", "message_response"]:
                            status_response_received = True
                            break
                            
                except:
                    continue
            
            bidirectional_time = time.time() - test_start
            
            integration_tests.append({
                "test": "bidirectional_communication",
                "success": status_response_received,
                "communication_time": bidirectional_time,
                "real_time_integration": status_response_received
            })
            
            print(f"    CYCLE:  Bidirectional communication: {' PASS: ' if status_response_received else ' FAIL: '}")
            
            # Cleanup
            await WebSocketTestHelpers.close_test_connection(connection)
            self.active_connections.remove(connection)
            
        except Exception as websocket_error:
            pytest.fail(f" ALERT:  WEBSOCKET CONNECTION FAILURE: {websocket_error}")
        
        websocket_backend_time = time.time() - websocket_backend_start
        
        # Analyze WebSocket integration results
        successful_tests = sum(1 for test in integration_tests if test.get("success"))
        backend_integration_working = sum(1 for test in integration_tests if test.get("backend_processing") or test.get("backend_agent_integration"))
        total_tests = len(integration_tests)
        
        websocket_integration_success = successful_tests >= (total_tests * 0.8)
        backend_communication_success = backend_integration_working > 0
        
        # Record WebSocket integration results
        self.integration_test_results["websocket_backend"] = {
            "success": websocket_integration_success and backend_communication_success,
            "test_success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "backend_communication_working": backend_communication_success,
            "real_time_integration": any(test.get("real_time_integration") for test in integration_tests),
            "duration": websocket_backend_time,
            "tests_performed": total_tests
        }
        
        print(f"\n CHART:  WEBSOCKET  ->  BACKEND INTEGRATION ANALYSIS:")
        print(f"   [U+1F310] Tests performed: {total_tests}")
        print(f"    PASS:  Successful tests: {successful_tests}")
        print(f"   [U+1F517] Backend communication: {' PASS: ' if backend_communication_success else ' FAIL: '}")
        
        # Validate WebSocket integration
        if not backend_communication_success:
            pytest.fail(
                f" ALERT:  WEBSOCKET  ->  BACKEND COMMUNICATION FAILURE\n"
                f"Backend integration working: {backend_communication_success}\n"
                f"WebSocket not properly communicating with backend!"
            )
        
        if not websocket_integration_success:
            pytest.fail(
                f" ALERT:  WEBSOCKET INTEGRATION FAILURE\n"
                f"Success Rate: {successful_tests}/{total_tests}\n"
                f"WebSocket real-time communication not working correctly!"
            )
        
        print(f"\n PASS:  WEBSOCKET  ->  BACKEND INTEGRATION: SUCCESS")
        print(f"   [U+1F310] Real-time communication: VALIDATED")
        print(f"   [U+1F517] Backend integration: VALIDATED")
        print(f"   [U+23F1][U+FE0F]  Integration time: {websocket_backend_time:.2f}s")
        
    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.real_services
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_end_to_end_service_integration_validation(self):
        """
        [U+1F517] END-TO-END SERVICE INTEGRATION: Complete Service Chain Validation
        
        Tests the complete service integration chain for golden path delivery:
        Auth  ->  Backend  ->  Database + WebSocket  ->  Agent  ->  Tools  ->  Response
        """
        e2e_integration_start = time.time()
        
        print(f"\n[U+1F517] END-TO-END SERVICE INTEGRATION: Testing complete service chain")
        
        # Execute complete service integration chain
        service_chain_results = []
        
        try:
            # Step 1: Authentication Service
            step_start = time.time()
            user_data = await self.auth_helper.create_test_user_with_auth(
                email=f"e2e_integration_{uuid.uuid4().hex[:8]}@example.com",
                name="End-to-End Integration User"
            )
            
            auth_step_success = bool(user_data.get("access_token"))
            service_chain_results.append({
                "service": "authentication",
                "success": auth_step_success,
                "duration": time.time() - step_start,
                "output": "JWT token" if auth_step_success else "No token"
            })
            
            if not auth_step_success:
                raise Exception("Authentication service failed")
            
            print(f"   [U+1F510] Authentication Service:  PASS: ")
            
            # Step 2: Backend API Integration
            step_start = time.time()
            auth_headers = self.auth_helper.get_auth_headers(user_data.get("access_token"))
            
            backend_health_check = False
            async with aiohttp.ClientSession() as session:
                try:
                    url = f"{self.backend_url}/health"
                    async with session.get(url, headers=auth_headers, timeout=5) as response:
                        backend_health_check = response.status == 200
                except:
                    pass
            
            service_chain_results.append({
                "service": "backend_api",
                "success": backend_health_check,
                "duration": time.time() - step_start,
                "output": "API accessible" if backend_health_check else "API unavailable"
            })
            
            print(f"   [U+1F310] Backend API: {' PASS: ' if backend_health_check else ' FAIL: '}")
            
            # Step 3: WebSocket Connection
            step_start = time.time()
            jwt_token = user_data.get("access_token")
            ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
            
            websocket_connection_success = False
            connection = None
            
            try:
                connection = await WebSocketTestHelpers.create_test_websocket_connection(
                    url=self.websocket_url,
                    headers=ws_headers,
                    timeout=10.0,
                    user_id=user_data.get("user_id")
                )
                self.active_connections.append(connection)
                websocket_connection_success = True
            except:
                pass
            
            service_chain_results.append({
                "service": "websocket",
                "success": websocket_connection_success,
                "duration": time.time() - step_start,
                "output": "Connected" if websocket_connection_success else "Connection failed"
            })
            
            print(f"   [U+1F310] WebSocket Service: {' PASS: ' if websocket_connection_success else ' FAIL: '}")
            
            # Step 4: Agent Processing Integration
            step_start = time.time()
            agent_processing_success = False
            agent_events_received = 0
            
            if connection:
                try:
                    # Send agent request
                    agent_message = {
                        "type": "chat_message",
                        "content": "E2E integration test: provide cost analysis",
                        "user_id": user_data.get("user_id"),
                        "integration_test": True
                    }
                    
                    await WebSocketTestHelpers.send_test_message(
                        connection, agent_message, timeout=5.0
                    )
                    
                    # Collect agent events
                    agent_start = time.time()
                    while (time.time() - agent_start) < 30.0:
                        try:
                            event = await WebSocketTestHelpers.receive_test_message(
                                connection, timeout=3.0
                            )
                            
                            if event and isinstance(event, dict):
                                agent_events_received += 1
                                event_type = event.get("type")
                                
                                if event_type in ["agent_started", "agent_completed"]:
                                    agent_processing_success = True
                                
                                if event_type == "agent_completed":
                                    break
                                    
                        except:
                            continue
                            
                except Exception as agent_error:
                    print(f"     Agent processing error: {agent_error}")
            
            service_chain_results.append({
                "service": "agent_processing",
                "success": agent_processing_success,
                "duration": time.time() - step_start,
                "output": f"{agent_events_received} events" if agent_processing_success else "No agent response"
            })
            
            print(f"   [U+1F916] Agent Processing: {' PASS: ' if agent_processing_success else ' FAIL: '}")
            
            # Step 5: Data Persistence Validation
            step_start = time.time()
            data_persistence_success = False
            
            if backend_health_check:
                try:
                    async with aiohttp.ClientSession() as session:
                        url = f"{self.backend_url}/api/conversations"
                        async with session.get(url, headers=auth_headers, timeout=5) as response:
                            data_persistence_success = response.status == 200
                except:
                    pass
            
            service_chain_results.append({
                "service": "data_persistence",
                "success": data_persistence_success,
                "duration": time.time() - step_start,
                "output": "Data accessible" if data_persistence_success else "Data not accessible"
            })
            
            print(f"   [U+1F5C4][U+FE0F] Data Persistence: {' PASS: ' if data_persistence_success else ' FAIL: '}")
            
            # Cleanup
            if connection:
                await WebSocketTestHelpers.close_test_connection(connection)
                if connection in self.active_connections:
                    self.active_connections.remove(connection)
            
        except Exception as chain_error:
            service_chain_results.append({
                "service": "error",
                "success": False,
                "error": str(chain_error),
                "duration": time.time() - e2e_integration_start
            })
        
        e2e_integration_time = time.time() - e2e_integration_start
        
        # Analyze end-to-end integration results
        successful_services = sum(1 for result in service_chain_results if result.get("success"))
        total_services = len([r for r in service_chain_results if r.get("service") != "error"])
        
        e2e_success_rate = successful_services / total_services if total_services > 0 else 0
        e2e_integration_success = e2e_success_rate >= 0.8  # 80% success threshold
        
        # Record end-to-end integration results
        self.integration_test_results["end_to_end"] = {
            "success": e2e_integration_success,
            "service_success_rate": e2e_success_rate,
            "services_tested": total_services,
            "successful_services": successful_services,
            "duration": e2e_integration_time,
            "complete_chain_working": e2e_integration_success
        }
        
        print(f"\n CHART:  END-TO-END INTEGRATION ANALYSIS:")
        print(f"   [U+1F517] Services tested: {total_services}")
        print(f"    PASS:  Successful services: {successful_services}")
        print(f"   [U+1F4C8] Success rate: {e2e_success_rate:.1%}")
        print(f"   [U+23F1][U+FE0F]  Total time: {e2e_integration_time:.2f}s")
        
        # Display service chain results
        for result in service_chain_results:
            if result.get("service") != "error":
                status = " PASS: " if result.get("success") else " FAIL: "
                service = result.get("service", "unknown")
                duration = result.get("duration", 0)
                output = result.get("output", "")
                print(f"     {status} {service}: {duration:.2f}s - {output}")
        
        # Validate end-to-end integration
        if not e2e_integration_success:
            failed_services = [result.get("service") for result in service_chain_results 
                             if not result.get("success") and result.get("service") != "error"]
            
            pytest.fail(
                f" ALERT:  END-TO-END SERVICE INTEGRATION FAILURE\n"
                f"Success Rate: {e2e_success_rate:.1%} (< 80% required)\n"
                f"Failed Services: {failed_services}\n"
                f"Service chain not delivering complete golden path!\n"
                f"Integration Results: {json.dumps(service_chain_results, indent=2, default=str)}"
            )
        
        print(f"\n CELEBRATION:  END-TO-END SERVICE INTEGRATION: SUCCESS!")
        print(f"   [U+1F517] Complete service chain: VALIDATED")
        print(f"   [U+1F680] Golden path delivery: ENABLED")
        print(f"   [U+1F4B0] Business value integration: PROVEN")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])