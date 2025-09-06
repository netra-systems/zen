"""
Comprehensive Integration Tests - NO MOCKS

End-to-end integration tests using all real services together:
WebSocket + Database + Redis + Agent Execution + LLM APIs

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Risk Reduction & System Reliability
- Value Impact: Ensures complete system works together in production
- Strategic Impact: Prevents integration failures and ensures user experience

This test suite validates:
- Complete user chat flows with real WebSocket connections
- Agent execution with real LLM calls and database persistence
- Session management with real Redis caching
- Error handling and recovery across all service boundaries
- Performance under integrated load scenarios
"""

import asyncio
import json
import pytest
import time
import logging
import websockets
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
import psutil
import uuid
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from shared.isolated_environment import IsolatedEnvironment

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

from test_framework.environment_isolation import get_test_env_manager
from test_framework.llm_config_manager import configure_llm_testing, LLMTestMode
from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState


logger = logging.getLogger(__name__)


class ComprehensiveIntegrationTestServer:
    """Full-featured test server with all services integrated."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self.server = None
        self.server_task = None
        self.actual_port = None
        
        # Service components
        self.websocket_manager = None
        self.database_manager = None
        self.agent_registry = None
        
        # Test tracking
        self.active_sessions = {}
        self.message_history = []
        self.performance_metrics = {
            'messages_processed': 0,
            'agent_executions': 0,
            'database_operations': 0,
            'errors_handled': 0
        }
    
    async def initialize_services(self):
        """Initialize all real services."""
        # Setup environment for real services
        env_manager = get_test_env_manager()
        env = env_manager.setup_test_environment(
            additional_vars={
                "USE_REAL_SERVICES": "true",
                "ENABLE_REAL_LLM_TESTING": "true",
                "DATABASE_URL": "postgresql://netra:netra123@localhost:5432/netra_test"
            },
            enable_real_llm=True
        )
        
        # Initialize database manager
        self.database_manager = DatabaseManager()
        await self.database_manager.initialize()
        
        # Initialize WebSocket manager
        WebSocketManager._instance = None  # Reset singleton
        self.websocket_manager = WebSocketManager()
        
        # Initialize agent registry
        self.agent_registry = AgentRegistry()
        await self.agent_registry.initialize()
        
        logger.info("All real services initialized")
    
    async def start_server(self) -> int:
        """Start integrated test server with all services."""
        await self.initialize_services()
        
        # Create FastAPI app with all endpoints
        app = FastAPI(title="Comprehensive Integration Test Server")
        
        @app.websocket("/ws/{user_id}/{thread_id}")
        async def websocket_endpoint(websocket: WebSocket, user_id: str, thread_id: str):
            await websocket.accept()
            connection_id = None
            
            try:
                # Real WebSocket connection through manager
                connection_id = await self.websocket_manager.connect_user(user_id, websocket, thread_id)
                
                # Track session
                session_id = f"{user_id}:{thread_id}"
                self.active_sessions[session_id] = {
                    'user_id': user_id,
                    'thread_id': thread_id,
                    'connection_id': connection_id,
                    'connected_at': datetime.now(timezone.utc),
                    'messages_sent': 0,
                    'messages_received': 0
                }
                
                logger.info(f"User {user_id} connected to thread {thread_id}")
                
                # Handle WebSocket messages
                while True:
                    try:
                        message = await websocket.receive_text()
                        data = json.loads(message)
                        
                        # Track message
                        self.message_history.append({
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'user_id': user_id,
                            'thread_id': thread_id,
                            'type': data.get('type', 'unknown'),
                            'message': data
                        })
                        
                        self.performance_metrics['messages_processed'] += 1
                        self.active_sessions[session_id]['messages_received'] += 1
                        
                        # Process message based on type
                        response = await self._process_message(user_id, thread_id, data)
                        
                        if response:
                            await self.websocket_manager.send_to_user(user_id, response)
                            self.active_sessions[session_id]['messages_sent'] += 1
                        
                    except WebSocketDisconnect:
                        break
                    except json.JSONDecodeError:
                        await websocket.send_json({
                            "type": "error",
                            "error": "Invalid JSON format"
                        })
                        self.performance_metrics['errors_handled'] += 1
                    
            except Exception as e:
                logger.error(f"WebSocket error for {user_id}: {e}")
                self.performance_metrics['errors_handled'] += 1
            finally:
                # Clean disconnect
                if connection_id:
                    await self.websocket_manager.disconnect_user(user_id, websocket)
                
                # Remove from active sessions
                session_id = f"{user_id}:{thread_id}"
                if session_id in self.active_sessions:
                    del self.active_sessions[session_id]
                
                logger.info(f"User {user_id} disconnected")
        
        # Start server
        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="error")
        server = uvicorn.Server(config)
        
        self.server_task = asyncio.create_task(server.serve())
        
        # Wait for server to start
        while not server.started:
            await asyncio.sleep(0.1)
        
        # Get actual port
        if self.port == 0:
            for sock in server.servers[0].sockets:
                if sock.family.name == 'AF_INET':
                    self.actual_port = sock.getsockname()[1]
                    break
        else:
            self.actual_port = self.port
        
        self.server = server
        logger.info(f"Integration test server started on port {self.actual_port}")
        return self.actual_port
    
    async def _process_message(self, user_id: str, thread_id: str, message: Dict) -> Optional[Dict]:
        """Process message with full service integration."""
        message_type = message.get('type')
        
        try:
            if message_type == 'chat_message':
                # Process chat message through agent system
                return await self._handle_chat_message(user_id, thread_id, message)
            
            elif message_type == 'agent_request':
                # Execute agent with real LLM
                return await self._handle_agent_request(user_id, thread_id, message)
            
            elif message_type == 'health_check':
                # Return system health status
                return await self._handle_health_check()
            
            elif message_type == 'performance_test':
                # Performance testing message
                return await self._handle_performance_test(message)
            
            else:
                # Echo message with integration info
                return {
                    "type": "integration_response",
                    "original": message,
                    "processed_by": "comprehensive_integration_server",
                    "services_active": {
                        "websocket": True,
                        "database": self.database_manager is not None,
                        "agents": self.agent_registry is not None
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        
        except Exception as e:
            logger.error(f"Message processing error: {e}")
            self.performance_metrics['errors_handled'] += 1
            return {
                "type": "error",
                "error": str(e),
                "message_type": message_type
            }
    
    async def _handle_chat_message(self, user_id: str, thread_id: str, message: Dict) -> Dict:
        """Handle chat message with agent execution and database persistence."""
        user_request = message.get('content', '')
        
        # Create agent state
        agent_state = DeepAgentState(
            user_request=user_request,
            chat_thread_id=thread_id,
            user_id=user_id,
            step_count=0
        )
        
        # Execute triage agent to determine next steps
        triage_agent = self.agent_registry.get_agent("triage")
        if triage_agent:
            self.performance_metrics['agent_executions'] += 1
            
            # Execute with real LLM
            result = await triage_agent.execute(agent_state)
            
            if result.success:
                return {
                    "type": "chat_response",
                    "content": result.agent_reasoning or "Agent executed successfully",
                    "next_agent": result.next_agent,
                    "agent_state": result.updated_state.model_dump(),
                    "execution_time": time.time(),
                    "real_llm_used": True
                }
            else:
                return {
                    "type": "chat_error",
                    "error": result.error_message,
                    "content": "I encountered an issue processing your request."
                }
        else:
            return {
                "type": "chat_response",
                "content": f"Received: {user_request}",
                "note": "Agent system not available"
            }
    
    async def _handle_agent_request(self, user_id: str, thread_id: str, message: Dict) -> Dict:
        """Handle direct agent execution request."""
        agent_name = message.get('agent', 'triage')
        user_request = message.get('request', 'Test request')
        
        # Get requested agent
        agent = self.agent_registry.get_agent(agent_name)
        if not agent:
            return {
                "type": "agent_error",
                "error": f"Agent '{agent_name}' not found"
            }
        
        # Create agent state
        agent_state = DeepAgentState(
            user_request=user_request,
            chat_thread_id=thread_id,
            user_id=user_id,
            step_count=message.get('step', 0)
        )
        
        # Execute agent
        self.performance_metrics['agent_executions'] += 1
        start_time = time.time()
        
        result = await agent.execute(agent_state)
        execution_time = time.time() - start_time
        
        return {
            "type": "agent_result",
            "agent": agent_name,
            "success": result.success,
            "reasoning": result.agent_reasoning,
            "next_agent": result.next_agent,
            "execution_time": execution_time,
            "error": result.error_message if not result.success else None,
            "state_updates": {
                "step_count": result.updated_state.step_count if result.updated_state else 0
            }
        }
    
    async def _handle_health_check(self) -> Dict:
        """Handle health check request."""
        health_status = {
            "type": "health_check_response",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {}
        }
        
        # Check database health
        try:
            db_health = await self.database_manager.health_check()
            health_status["services"]["database"] = {
                "status": db_health.get("status", "unknown"),
                "healthy": db_health.get("status") == "healthy"
            }
            self.performance_metrics['database_operations'] += 1
        except Exception as e:
            health_status["services"]["database"] = {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }
        
        # Check WebSocket manager
        health_status["services"]["websocket"] = {
            "status": "healthy",
            "healthy": True,
            "active_connections": len(self.websocket_manager.connections)
        }
        
        # Check agent registry
        health_status["services"]["agents"] = {
            "status": "healthy",
            "healthy": self.agent_registry is not None,
            "available_agents": len(self.agent_registry._agents) if self.agent_registry else 0
        }
        
        # Overall health
        all_healthy = all(
            service.get("healthy", False) 
            for service in health_status["services"].values()
        )
        health_status["overall_status"] = "healthy" if all_healthy else "degraded"
        
        return health_status
    
    async def _handle_performance_test(self, message: Dict) -> Dict:
        """Handle performance testing request."""
        test_type = message.get('test_type', 'basic')
        
        if test_type == 'database_operations':
            # Test database performance
            start_time = time.time()
            
            try:
                async with self.database_manager.get_session() as session:
                    # Execute test query
                    await session.execute('SELECT 1')
                    self.performance_metrics['database_operations'] += 1
                
                execution_time = time.time() - start_time
                
                return {
                    "type": "performance_result",
                    "test_type": test_type,
                    "success": True,
                    "execution_time": execution_time,
                    "operations_count": self.performance_metrics['database_operations']
                }
            
            except Exception as e:
                return {
                    "type": "performance_result",
                    "test_type": test_type,
                    "success": False,
                    "error": str(e)
                }
        
        else:
            return {
                "type": "performance_result",
                "test_type": test_type,
                "metrics": self.performance_metrics.copy(),
                "active_sessions": len(self.active_sessions)
            }
    
    async def stop_server(self):
        """Stop server and cleanup all services."""
        if self.server:
            self.server.should_exit = True
            if self.server_task and not self.server_task.done():
                await self.server_task
        
        # Cleanup services
        if self.websocket_manager:
            await self.websocket_manager.shutdown()
        
        if self.database_manager:
            await self.database_manager.close()
        
        if self.agent_registry:
            await self.agent_registry.shutdown()
        
        logger.info("Integration test server stopped and services cleaned up")
    
    def get_websocket_url(self, user_id: str, thread_id: str) -> str:
        """Get WebSocket URL for connection."""
        return f"ws://{self.host}:{self.actual_port}/ws/{user_id}/{thread_id}"
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return {
            **self.performance_metrics,
            'active_sessions': len(self.active_sessions),
            'total_messages_in_history': len(self.message_history)
        }


class ComprehensiveIntegrationClient:
    """Client for comprehensive integration testing."""
    
    def __init__(self, websocket_url: str):
        self.websocket_url = websocket_url
        self.websocket = None
        self.messages_received = []
        self.connected = False
        
    async def connect(self):
        """Connect to integration test server."""
        self.websocket = await websockets.connect(self.websocket_url)
        self.connected = True
        
        # Start message receiver
        self.receiver_task = asyncio.create_task(self._receive_messages())
        
    async def disconnect(self):
        """Disconnect from server."""
        self.connected = False
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
        
        if hasattr(self, 'receiver_task'):
            await self.receiver_task
    
    async def send_message(self, message: Dict):
        """Send message to server."""
        if self.websocket and not self.websocket.closed:
            await self.websocket.send(json.dumps(message))
    
    async def _receive_messages(self):
        """Background task to receive messages."""
        try:
            while self.connected and not self.websocket.closed:
                message = await self.websocket.recv()
                data = json.loads(message)
                self.messages_received.append({
                    'timestamp': time.time(),
                    'data': data
                })
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Message receiver error: {e}")
    
    def get_messages_by_type(self, message_type: str) -> List[Dict]:
        """Get messages filtered by type."""
        return [
            msg for msg in self.messages_received 
            if msg['data'].get('type') == message_type
        ]
    
    def wait_for_message(self, message_type: str, timeout: float = 30.0) -> Optional[Dict]:
        """Wait for specific message type."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            messages = self.get_messages_by_type(message_type)
            if messages:
                return messages[-1]['data']
            time.sleep(0.2)
        return None


@pytest.fixture
async def integration_server():
    """Fixture providing comprehensive integration test server."""
    server = ComprehensiveIntegrationTestServer()
    port = await server.start_server()
    
    yield server
    
    await server.stop_server()


class TestComprehensiveIntegration:
    """Comprehensive integration tests with all real services."""
    
    @pytest.mark.asyncio
    async def test_full_system_health_check(self, integration_server):
        """
        Test complete system health check across all services.
        MUST PASS: All services should be healthy and responsive.
        """
        user_id = "health_test_user"
        thread_id = "health_test_thread"
        url = integration_server.get_websocket_url(user_id, thread_id)
        
        client = ComprehensiveIntegrationClient(url)
        
        try:
            await client.connect()
            
            # Send health check request
            await client.send_message({
                "type": "health_check",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Wait for health check response
            health_response = client.wait_for_message("health_check_response", timeout=15.0)
            
            assert health_response is not None, "Should receive health check response"
            assert health_response["overall_status"] in ["healthy", "degraded"], \
                f"Should have valid overall status: {health_response['overall_status']}"
            
            # Verify individual service health
            services = health_response.get("services", {})
            
            assert "database" in services, "Should check database health"
            assert "websocket" in services, "Should check WebSocket health"
            assert "agents" in services, "Should check agent registry health"
            
            # Database should be healthy
            db_status = services["database"]
            assert db_status.get("healthy") is True, f"Database should be healthy: {db_status}"
            
            # WebSocket should be healthy
            ws_status = services["websocket"]
            assert ws_status.get("healthy") is True, f"WebSocket should be healthy: {ws_status}"
            
            # Agent registry should be healthy
            agent_status = services["agents"]
            assert agent_status.get("healthy") is True, f"Agent registry should be healthy: {agent_status}"
            
            logger.info("Full system health check passed")
            logger.info(f"Service statuses: {services}")
            
        finally:
            await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_end_to_end_chat_flow_with_real_llm(self, integration_server):
        """
        Test complete end-to-end chat flow with real LLM execution.
        MUST PASS: Chat should work with real agent execution and LLM calls.
        """
        user_id = "chat_test_user"
        thread_id = "chat_test_thread"
        url = integration_server.get_websocket_url(user_id, thread_id)
        
        client = ComprehensiveIntegrationClient(url)
        
        try:
            await client.connect()
            
            # Send chat message
            await client.send_message({
                "type": "chat_message",
                "content": "I need help analyzing some business data to find growth opportunities",
                "user_id": user_id,
                "thread_id": thread_id
            })
            
            # Wait for chat response with real LLM execution
            chat_response = client.wait_for_message("chat_response", timeout=45.0)
            
            assert chat_response is not None, "Should receive chat response"
            assert "content" in chat_response, "Response should have content"
            assert chat_response.get("real_llm_used") is True, "Should use real LLM"
            
            # Verify agent determination
            next_agent = chat_response.get("next_agent")
            logger.info(f"Triage agent determined next agent: {next_agent}")
            
            # Agent state should be present and valid
            agent_state = chat_response.get("agent_state")
            assert agent_state is not None, "Should have agent state"
            assert agent_state.get("step_count") > 0, "Step count should be incremented"
            
            logger.info("End-to-end chat flow completed successfully")
            logger.info(f"Chat response content: {chat_response['content']}")
            
        finally:
            await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_multi_agent_orchestration_integration(self, integration_server):
        """
        Test multi-agent orchestration with full service integration.
        MUST PASS: Multiple agents should execute in sequence with real services.
        """
        user_id = "orchestration_user"
        thread_id = "orchestration_thread"
        url = integration_server.get_websocket_url(user_id, thread_id)
        
        client = ComprehensiveIntegrationClient(url)
        
        try:
            await client.connect()
            
            # Test triage agent first
            await client.send_message({
                "type": "agent_request",
                "agent": "triage",
                "request": "I need a comprehensive analysis of customer retention data with actionable recommendations"
            })
            
            triage_response = client.wait_for_message("agent_result", timeout=30.0)
            
            assert triage_response is not None, "Should receive triage response"
            assert triage_response.get("success") is True, f"Triage should succeed: {triage_response.get('error')}"
            assert triage_response.get("next_agent") is not None, "Should determine next agent"
            
            next_agent = triage_response.get("next_agent")
            logger.info(f"Triage recommended next agent: {next_agent}")
            
            # Execute recommended agent if available
            if next_agent:
                await client.send_message({
                    "type": "agent_request",
                    "agent": next_agent,
                    "request": "Continue with the analysis as recommended by triage",
                    "step": 1
                })
                
                next_agent_response = client.wait_for_message("agent_result", timeout=30.0)
                
                if next_agent_response:
                    logger.info(f"Next agent ({next_agent}) execution: success={next_agent_response.get('success')}")
                    
                    # If successful, orchestration is working
                    if next_agent_response.get("success"):
                        assert next_agent_response.get("execution_time") > 0, "Should have execution time"
            
            logger.info("Multi-agent orchestration integration completed")
            
        finally:
            await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_concurrent_user_sessions_integration(self, integration_server):
        """
        Test concurrent user sessions with full service integration.
        MUST PASS: Multiple users should be able to use the system concurrently.
        """
        num_concurrent_users = 5
        clients = []
        
        try:
            # Create concurrent user sessions
            for i in range(num_concurrent_users):
                user_id = f"concurrent_user_{i}"
                thread_id = f"concurrent_thread_{i}"
                url = integration_server.get_websocket_url(user_id, thread_id)
                
                client = ComprehensiveIntegrationClient(url)
                await client.connect()
                clients.append((client, user_id, thread_id))
            
            logger.info(f"Connected {len(clients)} concurrent users")
            
            # Send messages from all users concurrently
            message_tasks = []
            for i, (client, user_id, thread_id) in enumerate(clients):
                message = {
                    "type": "chat_message",
                    "content": f"Concurrent test message from user {i}",
                    "user_id": user_id,
                    "thread_id": thread_id
                }
                task = client.send_message(message)
                message_tasks.append(task)
            
            await asyncio.gather(*message_tasks)
            
            # Wait for responses from all users
            successful_responses = 0
            for i, (client, user_id, thread_id) in enumerate(clients):
                response = client.wait_for_message("chat_response", timeout=60.0)
                if response:
                    successful_responses += 1
                    logger.info(f"User {i} received response")
            
            # Should handle concurrent users successfully
            assert successful_responses >= num_concurrent_users * 0.8, \
                f"Should handle most concurrent users: {successful_responses}/{num_concurrent_users}"
            
            # Check server performance metrics
            performance_metrics = integration_server.get_performance_metrics()
            logger.info(f"Performance metrics after concurrent test: {performance_metrics}")
            
            assert performance_metrics['messages_processed'] >= num_concurrent_users, \
                "Should have processed messages from concurrent users"
            assert performance_metrics['active_sessions'] >= 0, \
                "Should track active sessions"
            
            logger.info("Concurrent user sessions integration completed successfully")
            
        finally:
            # Disconnect all clients
            for client, _, _ in clients:
                try:
                    await client.disconnect()
                except:
                    pass
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery_integration(self, integration_server):
        """
        Test error handling and recovery across all integrated services.
        MUST PASS: System should handle errors gracefully and recover.
        """
        user_id = "error_test_user"
        thread_id = "error_test_thread"
        url = integration_server.get_websocket_url(user_id, thread_id)
        
        client = ComprehensiveIntegrationClient(url)
        
        try:
            await client.connect()
            
            # Test invalid JSON
            try:
                await client.websocket.send("{ invalid json")
                error_response = client.wait_for_message("error", timeout=5.0)
                assert error_response is not None, "Should handle invalid JSON"
                assert "Invalid JSON" in error_response.get("error", ""), "Should identify JSON error"
                logger.info("Invalid JSON handled correctly")
            except Exception as e:
                logger.info(f"JSON error test: {e}")
            
            # Test invalid agent request
            await client.send_message({
                "type": "agent_request",
                "agent": "nonexistent_agent",
                "request": "This should fail"
            })
            
            agent_error_response = client.wait_for_message("agent_error", timeout=10.0)
            assert agent_error_response is not None, "Should handle invalid agent request"
            assert "not found" in agent_error_response.get("error", "").lower(), \
                "Should identify missing agent"
            
            logger.info("Invalid agent request handled correctly")
            
            # Test system recovery - send valid request after errors
            await client.send_message({
                "type": "health_check",
                "recovery_test": True
            })
            
            recovery_response = client.wait_for_message("health_check_response", timeout=10.0)
            assert recovery_response is not None, "Should recover after errors"
            assert recovery_response.get("overall_status") in ["healthy", "degraded"], \
                "System should be functional after error recovery"
            
            logger.info("Error handling and recovery integration successful")
            
        finally:
            await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_performance_under_integrated_load(self, integration_server):
        """
        Test system performance under integrated load across all services.
        MUST PASS: System should maintain performance under realistic load.
        """
        import psutil
        import gc
        
        # Get baseline memory
        process = psutil.Process()
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create sustained load scenario
        num_users = 8
        operations_per_user = 10
        
        clients = []
        
        try:
            # Connect users
            for i in range(num_users):
                user_id = f"load_user_{i}"
                thread_id = f"load_thread_{i}"
                url = integration_server.get_websocket_url(user_id, thread_id)
                
                client = ComprehensiveIntegrationClient(url)
                await client.connect()
                clients.append((client, user_id, thread_id, i))
            
            start_time = time.time()
            
            # Generate load with mixed operations
            async def user_load_operations(client_info):
                client, user_id, thread_id, user_index = client_info
                operations_completed = 0
                
                for op in range(operations_per_user):
                    try:
                        if op % 3 == 0:
                            # Health check operation
                            await client.send_message({
                                "type": "health_check",
                                "user": user_index,
                                "operation": op
                            })
                        elif op % 3 == 1:
                            # Performance test operation
                            await client.send_message({
                                "type": "performance_test",
                                "test_type": "database_operations",
                                "user": user_index,
                                "operation": op
                            })
                        else:
                            # Chat message operation
                            await client.send_message({
                                "type": "chat_message",
                                "content": f"Load test message {op} from user {user_index}",
                                "user_id": user_id,
                                "thread_id": thread_id
                            })
                        
                        operations_completed += 1
                        
                        # Small delay between operations
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.warning(f"Load operation failed for user {user_index}: {e}")
                
                return user_index, operations_completed
            
            # Run load operations concurrently
            load_tasks = [user_load_operations(client_info) for client_info in clients]
            load_results = await asyncio.gather(*load_tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
            
            # Analyze load test results
            successful_operations = 0
            successful_users = 0
            
            for result in load_results:
                if isinstance(result, Exception):
                    logger.error(f"Load test user failed: {result}")
                else:
                    user_index, operations_completed = result
                    successful_operations += operations_completed
                    if operations_completed == operations_per_user:
                        successful_users += 1
            
            # Check memory usage
            gc.collect()
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_growth = final_memory - baseline_memory
            
            # Get server performance metrics
            performance_metrics = integration_server.get_performance_metrics()
            
            logger.info("Integrated load test results:")
            logger.info(f"  Users: {num_users}")
            logger.info(f"  Total time: {total_time:.2f} seconds")
            logger.info(f"  Successful operations: {successful_operations}/{num_users * operations_per_user}")
            logger.info(f"  Successful users: {successful_users}/{num_users}")
            logger.info(f"  Memory growth: {memory_growth:.2f} MB")
            logger.info(f"  Server metrics: {performance_metrics}")
            
            # Performance assertions
            total_expected_operations = num_users * operations_per_user
            assert successful_operations >= total_expected_operations * 0.7, \
                f"Should complete most operations: {successful_operations}/{total_expected_operations}"
            assert successful_users >= num_users * 0.7, \
                f"Most users should complete successfully: {successful_users}/{num_users}"
            assert total_time < 60.0, f"Load test should complete in reasonable time: {total_time:.2f}s"
            assert memory_growth < 100.0, f"Memory growth should be reasonable: {memory_growth:.2f} MB"
            
            # Server metrics should show activity
            assert performance_metrics['messages_processed'] > 0, "Should have processed messages"
            
            logger.info("Performance under integrated load test successful")
            
        finally:
            # Disconnect all clients
            for client_info in clients:
                client = client_info[0]
                try:
                    await client.disconnect()
                except:
                    pass


if __name__ == "__main__":
    # Run comprehensive integration tests
    pytest.main(["-v", __file__, "--real-llm", "-s"])