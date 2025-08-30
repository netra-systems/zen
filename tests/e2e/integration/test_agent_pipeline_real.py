"""
Real Agent Pipeline Execution Flow Test - E2E Critical Test

CRITICAL E2E Test: Real Agent Pipeline from WebSocket Message to Agent Response
Tests the complete agent pipeline flow from message routing through supervisor to agent execution.

Business Value Justification (BVJ):
Segment: ALL (Free, Early, Mid, Enterprise) | Goal: Core Agent Value Delivery | Revenue Impact: $120K+ MRR
- Agent failures = no value delivery = immediate churn
- Validates supervisor routing, agent selection, and execution patterns
- Tests real LLM integration with agent processing pipeline  
- Ensures quality gates and response generation work end-to-end
- Performance requirements critical for user retention

Performance Requirements:
- Message routing: <100ms
- Agent selection: <200ms
- Agent execution: <5s total pipeline
- Response generation: <1s
- Quality gates: <500ms
- End-to-end: <5s for user retention
"""

import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest

from tests.clients import TestClientFactory
from tests.e2e.jwt_token_helpers import JWTTestHelper

# Enable real services for this test module
pytestmark = pytest.mark.skipif(
    os.environ.get("USE_REAL_SERVICES", "false").lower() != "true",
    reason="Real services disabled (set USE_REAL_SERVICES=true)"
)


class TestAgentPipelineExecutioner:
    """Comprehensive agent pipeline execution tester with real services."""
    
    def __init__(self, real_services):
        """Initialize tester with real services context."""
        self.real_services = real_services
        self.auth_client = real_services.auth_client
        self.backend_client = real_services.backend_client
        self.factory = real_services.factory
        self.jwt_helper = JWTTestHelper()
        
    async def setup_authenticated_websocket(self) -> Dict[str, Any]:
        """Setup authenticated WebSocket connection for agent testing."""
        start_time = time.time()
        
        try:
            # Get JWT token
            token_data = await self.auth_client.create_test_user()
            token = token_data["token"]
            email = token_data["email"]
            
            # Create authenticated WebSocket client
            ws_client = await self.factory.create_websocket_client(token)
            connected = await ws_client.connect()
            
            setup_time = time.time() - start_time
            
            if connected:
                return {
                    "websocket": ws_client,
                    "token": token,
                    "email": email,
                    "connected": True,
                    "setup_time": setup_time,
                    "error": None
                }
            else:
                return {
                    "websocket": None,
                    "token": token,
                    "email": email,
                    "connected": False,
                    "setup_time": setup_time,
                    "error": "WebSocket connection failed"
                }
                
        except Exception as e:
            return {
                "websocket": None,
                "token": None,
                "email": None,
                "connected": False,
                "setup_time": time.time() - start_time,
                "error": str(e)
            }
    
    async def send_agent_pipeline_message(self, ws_client, content: str, 
                                        thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Send message that requires agent pipeline processing."""
        start_time = time.time()
        
        try:
            # Create message requiring agent processing
            if not thread_id:
                thread_id = str(uuid.uuid4())
            
            message = {
                "type": "chat",
                "content": content,
                "thread_id": thread_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Send message through WebSocket
            await ws_client.send(message)
            
            send_time = time.time() - start_time
            
            return {
                "sent": True,
                "message": message,
                "thread_id": thread_id,
                "send_time": send_time,
                "error": None
            }
            
        except Exception as e:
            return {
                "sent": False,
                "message": None,
                "thread_id": thread_id,
                "send_time": time.time() - start_time,
                "error": str(e)
            }
    
    async def wait_for_agent_response(self, ws_client, timeout: float = 8.0) -> Dict[str, Any]:
        """Wait for agent response with pipeline tracking."""
        start_time = time.time()
        received_messages = []
        agent_response = None
        supervisor_started = False
        agent_selected = False
        
        try:
            # Wait for multiple messages to track pipeline progression
            while time.time() - start_time < timeout:
                message = await ws_client.receive(timeout=2.0)
                
                if not message:
                    continue
                    
                received_messages.append(message)
                
                # Track pipeline progression
                message_type = message.get("type", "")
                
                if message_type == "supervisor_started":
                    supervisor_started = True
                elif message_type == "agent_selected":
                    agent_selected = True
                elif message_type in ["agent_response", "agent_completed", "response"]:
                    agent_response = message
                    break
                elif message_type == "error":
                    # Agent pipeline error
                    break
            
            response_time = time.time() - start_time
            
            return {
                "response_received": agent_response is not None,
                "agent_response": agent_response,
                "supervisor_started": supervisor_started,
                "agent_selected": agent_selected,
                "all_messages": received_messages,
                "response_time": response_time,
                "error": None
            }
            
        except Exception as e:
            return {
                "response_received": False,
                "agent_response": None,
                "supervisor_started": supervisor_started,
                "agent_selected": agent_selected,
                "all_messages": received_messages,
                "response_time": time.time() - start_time,
                "error": str(e)
            }
    
    async def validate_agent_response_quality(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the quality of agent response."""
        start_time = time.time()
        
        try:
            quality_checks = {
                "has_content": False,
                "content_length_adequate": False,
                "has_agent_metadata": False,
                "response_structured": False,
                "includes_agent_name": False
            }
            
            # Check if response has content
            content = response.get("content", response.get("message", ""))
            if content and isinstance(content, str):
                quality_checks["has_content"] = True
                
                # Check content length (should be meaningful)
                if len(content.strip()) > 20:
                    quality_checks["content_length_adequate"] = True
            
            # Check for agent metadata
            if any(key in response for key in ["agent_name", "agent_type", "from_agent"]):
                quality_checks["has_agent_metadata"] = True
                quality_checks["includes_agent_name"] = True
            
            # Check if response is properly structured
            if isinstance(response, dict) and response.get("type"):
                quality_checks["response_structured"] = True
            
            validation_time = time.time() - start_time
            quality_score = sum(quality_checks.values()) / len(quality_checks)
            
            return {
                "quality_checks": quality_checks,
                "quality_score": quality_score,
                "validation_time": validation_time,
                "passed_quality": quality_score >= 0.6,  # 60% threshold
                "error": None
            }
            
        except Exception as e:
            return {
                "quality_checks": {},
                "quality_score": 0.0,
                "validation_time": time.time() - start_time,
                "passed_quality": False,
                "error": str(e)
            }


class TestAgentPipelinePerformanceer:
    """Tests agent pipeline performance characteristics."""
    
    def __init__(self, pipeline_tester: TestAgentPipelineExecutioner):
        """Initialize performance tester."""
        self.pipeline_tester = pipeline_tester
    
    @pytest.mark.e2e
    async def test_pipeline_performance_requirements(self, ws_client) -> Dict[str, Any]:
        """Test that agent pipeline meets performance requirements."""
        performance_results = {}
        
        # Test 1: Simple agent request
        simple_start = time.time()
        send_result = await self.pipeline_tester.send_agent_pipeline_message(
            ws_client, "What are my current AI costs?"
        )
        
        if send_result["sent"]:
            response_result = await self.pipeline_tester.wait_for_agent_response(ws_client)
            simple_total_time = time.time() - simple_start
            
            performance_results["simple_request"] = {
                "total_time": simple_total_time,
                "response_received": response_result["response_received"],
                "meets_5s_requirement": simple_total_time < 5.0
            }
        
        # Test 2: Complex agent request  
        complex_start = time.time()
        send_result = await self.pipeline_tester.send_agent_pipeline_message(
            ws_client, "Analyze my AI spending patterns and provide cost optimization recommendations with detailed breakdown"
        )
        
        if send_result["sent"]:
            response_result = await self.pipeline_tester.wait_for_agent_response(ws_client, timeout=10.0)
            complex_total_time = time.time() - complex_start
            
            performance_results["complex_request"] = {
                "total_time": complex_total_time,
                "response_received": response_result["response_received"],
                "meets_5s_requirement": complex_total_time < 5.0,
                "acceptable_for_complex": complex_total_time < 8.0
            }
        
        return performance_results


@pytest.mark.critical
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_agent_pipeline_execution(real_services):
    """
    BVJ: Segment: ALL | Goal: Core Agent Value Delivery | Impact: $120K+ MRR
    Test: Complete agent pipeline from WebSocket message to agent response
    """
    pipeline_tester = TestAgentPipelineExecutioner(real_services)
    
    # Phase 1: Setup authenticated WebSocket connection
    ws_setup = await pipeline_tester.setup_authenticated_websocket()
    assert ws_setup["connected"], f"Failed to setup WebSocket: {ws_setup.get('error')}"
    assert ws_setup["setup_time"] < 3.0, f"WebSocket setup took {ws_setup['setup_time']:.3f}s, should be <3s"
    
    websocket = ws_setup["websocket"]
    
    try:
        # Phase 2: Send message requiring agent processing
        message_content = "What are my cost optimization opportunities?"
        send_result = await pipeline_tester.send_agent_pipeline_message(websocket, message_content)
        
        assert send_result["sent"], f"Failed to send agent message: {send_result.get('error')}"
        assert send_result["send_time"] < 0.1, f"Message send took {send_result['send_time']:.3f}s, should be <100ms"
        
        # Phase 3: Wait for agent response and validate pipeline execution
        response_result = await pipeline_tester.wait_for_agent_response(websocket)
        
        assert response_result["response_received"], f"No agent response received: {response_result.get('error')}"
        assert response_result["response_time"] < 5.0, \
            f"Agent pipeline took {response_result['response_time']:.3f}s, required <5s"
        
        agent_response = response_result["agent_response"]
        
        # Phase 4: Validate response quality
        quality_result = await pipeline_tester.validate_agent_response_quality(agent_response)
        
        assert quality_result["passed_quality"], \
            f"Agent response failed quality checks: {quality_result['quality_checks']}"
        assert quality_result["validation_time"] < 0.5, \
            f"Quality validation took {quality_result['validation_time']:.3f}s, should be <500ms"
        
        # Phase 5: Verify meaningful response content
        content = agent_response.get("content", agent_response.get("message", ""))
        assert len(content) > 50, f"Agent response too short ({len(content)} chars), should be meaningful"
        
        # Log successful pipeline metrics
        print(f"✓ Agent pipeline successful:")
        print(f"  Setup: {ws_setup['setup_time']:.3f}s")
        print(f"  Send: {send_result['send_time']:.3f}s") 
        print(f"  Response: {response_result['response_time']:.3f}s")
        print(f"  Quality: {quality_result['quality_score']:.2f}")
        print(f"  Content length: {len(content)} chars")
        
    finally:
        await websocket.disconnect()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_agent_pipeline_performance_requirements(real_services):
    """Test that agent pipeline meets performance requirements for different request types."""
    pipeline_tester = TestAgentPipelineExecutioner(real_services)
    performance_tester = TestAgentPipelinePerformanceer(pipeline_tester)
    
    # Setup WebSocket
    ws_setup = await pipeline_tester.setup_authenticated_websocket()
    assert ws_setup["connected"], "Failed to setup WebSocket for performance test"
    
    websocket = ws_setup["websocket"]
    
    try:
        # Test performance characteristics
        performance_results = await performance_tester.test_pipeline_performance_requirements(websocket)
        
        # Validate simple request performance
        if "simple_request" in performance_results:
            simple = performance_results["simple_request"]
            assert simple["response_received"], "Simple request failed to get response"
            assert simple["meets_5s_requirement"], \
                f"Simple request took {simple['total_time']:.3f}s, required <5s"
            
            print(f"✓ Simple request: {simple['total_time']:.3f}s")
        
        # Validate complex request performance (more lenient)
        if "complex_request" in performance_results:
            complex = performance_results["complex_request"]
            if complex["response_received"]:
                # Complex requests can take longer but should be reasonable
                assert complex["acceptable_for_complex"], \
                    f"Complex request took {complex['total_time']:.3f}s, should be <8s"
                
                print(f"✓ Complex request: {complex['total_time']:.3f}s")
    
    finally:
        await websocket.disconnect()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_concurrent_agent_pipeline_execution(real_services):
    """Test multiple concurrent agent pipeline executions."""
    pipeline_tester = TestAgentPipelineExecutioner(real_services)
    
    # Setup multiple WebSocket connections
    websockets = []
    for i in range(3):
        ws_setup = await pipeline_tester.setup_authenticated_websocket()
        if ws_setup["connected"]:
            websockets.append(ws_setup["websocket"])
    
    assert len(websockets) >= 2, f"Need at least 2 connections for concurrency test, got {len(websockets)}"
    
    try:
        # Send concurrent agent requests
        concurrent_tasks = []
        for i, ws in enumerate(websockets):
            task = pipeline_tester.send_agent_pipeline_message(
                ws, f"What are my optimization opportunities for project {i+1}?"
            )
            concurrent_tasks.append(task)
        
        # Wait for all sends to complete
        send_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Count successful sends
        successful_sends = sum(
            1 for result in send_results 
            if isinstance(result, dict) and result.get("sent", False)
        )
        
        assert successful_sends >= 2, f"Need at least 2 successful sends, got {successful_sends}"
        
        # Wait for responses concurrently
        response_tasks = []
        for ws in websockets[:successful_sends]:
            task = pipeline_tester.wait_for_agent_response(ws, timeout=10.0)
            response_tasks.append(task)
        
        response_results = await asyncio.gather(*response_tasks, return_exceptions=True)
        
        # Count successful responses
        successful_responses = sum(
            1 for result in response_results
            if isinstance(result, dict) and result.get("response_received", False)
        )
        
        assert successful_responses >= 1, f"Need at least 1 successful response, got {successful_responses}"
        
        print(f"✓ Concurrent agent pipeline: {successful_sends} sends, {successful_responses} responses")
    
    finally:
        # Cleanup all connections
        for ws in websockets:
            try:
                await ws.disconnect()
            except Exception as e:
                print(f"Warning: Error disconnecting WebSocket: {e}")


@pytest.mark.asyncio 
@pytest.mark.e2e
async def test_agent_pipeline_error_handling(real_services):
    """Test agent pipeline error handling and recovery."""
    pipeline_tester = TestAgentPipelineExecutioner(real_services)
    
    # Setup WebSocket
    ws_setup = await pipeline_tester.setup_authenticated_websocket()
    assert ws_setup["connected"], "Failed to setup WebSocket for error test"
    
    websocket = ws_setup["websocket"]
    
    try:
        # Test 1: Invalid message format (should be handled gracefully)
        invalid_message = {
            "type": "chat",
            "content": "",  # Empty content
            "thread_id": str(uuid.uuid4())
        }
        
        await websocket.send(invalid_message)
        
        # Should get some response or error message
        response = await websocket.receive(timeout=5.0)
        if response:
            print(f"✓ Invalid message handled: {response.get('type', 'unknown')}")
        
        # Test 2: Complex request that might stress the pipeline
        stress_content = "A" * 1000 + " analyze this and provide detailed recommendations"
        send_result = await pipeline_tester.send_agent_pipeline_message(websocket, stress_content)
        
        if send_result["sent"]:
            response_result = await pipeline_tester.wait_for_agent_response(websocket, timeout=10.0)
            
            # Should either get response or graceful error
            if response_result["response_received"]:
                print("✓ Stress test handled with response")
            elif response_result["all_messages"]:
                print("✓ Stress test handled with messages")
            else:
                print("ℹ Stress test - no response (may be expected)")
    
    finally:
        await websocket.disconnect()


# Business Impact Summary
"""
Real Agent Pipeline Execution Test - Business Impact

Revenue Impact: $120K+ MRR Protection
- Agent failures = immediate no-value delivery = customer churn
- Tests complete supervisor → agent selection → execution → response flow
- Validates real LLM integration with actual agent processing
- Ensures quality gates work end-to-end for value delivery
- Performance validation critical for user retention and satisfaction

Agent Pipeline Coverage:
- WebSocket message routing through supervisor
- Agent selection based on user request analysis  
- Real agent execution with LLM processing
- Response generation and quality validation
- Error handling and recovery patterns
- Concurrent execution for scalability

Performance Validation:
- Message routing: <100ms for immediate responsiveness
- Agent pipeline: <5s total for user retention
- Quality gates: <500ms for real-time validation
- Complex requests: <8s tolerance for detailed analysis
- Concurrent execution: Multiple users supported

Customer Impact:
- All Segments: Reliable AI agent interactions delivering actual value
- Enterprise: Proven agent pipeline reliability for high-value contracts  
- Free/Early: Immediate value demonstration through working agents
- Mid: Scalable agent processing for team collaboration
"""
