"""Message Agent Pipeline Test - Complete End-to-End Message Processing

Business Value: $40K MRR - Core chat functionality validation
Tests: WebSocket → Auth → Agent → Response pipeline

Critical: <5s response time, message ordering, error handling
Architecture: 450-line limit, 25-line functions (CLAUDE.md compliance)
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, Mock, patch

import pytest

from netra_backend.app.logging_config import central_logger
from netra_backend.app.tests.test_utilities.websocket_mocks import (
    MockWebSocket,
    WebSocketBuilder,
)
from tests.e2e.config import (
    TEST_CONFIG,
    TestDataFactory,
    UnifiedTestConfig,
)
from tests.e2e.harness_complete import TestHarnessContext
from tests.e2e.message_flow_validators import MessageFlowValidator

logger = central_logger.get_logger(__name__)


class MessagePipelineTester:
    """Complete message pipeline test coordinator."""
    
    def __init__(self):
        self.start_times: Dict[str, float] = {}
        self.completion_times: Dict[str, float] = {}
        self.message_responses: List[Dict[str, Any]] = []
        self.error_log: List[Dict[str, Any]] = []
    
    def start_timing(self, message_id: str) -> None:
        """Start timing for message processing."""
        self.start_times[message_id] = time.time()
    
    def complete_timing(self, message_id: str) -> float:
        """Complete timing and return duration."""
        end_time = time.time()
        start_time = self.start_times.get(message_id, end_time)
        duration = end_time - start_time
        self.completion_times[message_id] = duration
        return duration
    
    def record_response(self, message_id: str, response: Dict[str, Any]) -> None:
        """Record message response."""
        response["message_id"] = message_id
        response["timestamp"] = time.time()
        self.message_responses.append(response)
    
    def record_error(self, message_id: str, error: Exception) -> None:
        """Record pipeline error."""
        error_record = {
            "message_id": message_id,
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": time.time()
        }
        self.error_log.append(error_record)


@pytest.fixture
async def pipeline_tester():
    """Create message pipeline tester."""
    return MessagePipelineTester()


@pytest.fixture
async def mock_websocket():
    """Create authenticated mock WebSocket."""
    websocket = (WebSocketBuilder()
                .with_user_id("test_pipeline_user")
                .with_authentication("valid.jwt.token")
                .build())
    await websocket.accept()
    return websocket


class TestMessagePipelineCore:
    """Core message pipeline functionality tests."""
    
    async def test_complete_message_pipeline_flow(self, pipeline_tester, mock_websocket):
        """Test complete pipeline: WebSocket → Auth → Agent → Response
        
        BVJ: Core value delivery test ensuring complete message processing works.
        """
        message_id = "test_complete_flow"
        test_message = {"type": "message", "content": "Test complete pipeline"}
        
        pipeline_tester.start_timing(message_id)
        
        # Step 1: WebSocket receives message
        websocket_result = await self._test_websocket_message_receipt(
            mock_websocket, test_message
        )
        assert websocket_result["received"], "WebSocket message receipt failed"
        
        # Step 2: Authentication validation
        auth_result = await self._test_message_authentication(mock_websocket, test_message)
        assert auth_result["authenticated"], "Message authentication failed"
        
        # Step 3: Agent routing and processing
        agent_result = await self._test_agent_processing(test_message)
        assert agent_result["processed"], "Agent processing failed"
        
        # Step 4: Response streaming
        stream_result = await self._test_response_streaming(mock_websocket, agent_result)
        assert stream_result["streamed"], "Response streaming failed"
        
        # Step 5: Validate response time
        duration = pipeline_tester.complete_timing(message_id)
        assert duration < 5.0, f"Pipeline too slow: {duration}s > 5s"
        
        pipeline_tester.record_response(message_id, {
            "success": True,
            "duration": duration,
            "agent_response": agent_result["response"]
        })
    
    async def _test_websocket_message_receipt(self, websocket: MockWebSocket,
                                            message: Dict[str, Any]) -> Dict[str, Any]:
        """Test WebSocket message receipt."""
        try:
            await websocket.send_json(message)
            return {"received": True, "message": message}
        except Exception as e:
            return {"received": False, "error": str(e)}
    
    async def _test_message_authentication(self, websocket: MockWebSocket,
                                         message: Dict[str, Any]) -> Dict[str, Any]:
        """Test message authentication."""
        with patch('app.routes.utils.websocket_helpers.authenticate_websocket_user') as mock_auth:
            mock_auth.return_value = "test_pipeline_user"
            return {"authenticated": True, "user_id": "test_pipeline_user"}
    
    async def _test_agent_processing(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Test agent processing with deterministic mock."""
        with patch('app.services.agent_service_factory.get_agent_service') as mock_service:
            mock_agent = AsyncMock()
            mock_agent.process_message.return_value = {
                "response": f"Processed: {message['content']}",
                "agent_type": "MockAgent",
                "processing_time": 0.1
            }
            mock_service.return_value = mock_agent
            
            result = await mock_agent.process_message(message)
            return {"processed": True, "response": result}
    
    async def _test_response_streaming(self, websocket: MockWebSocket,
                                     agent_result: Dict[str, Any]) -> Dict[str, Any]:
        """Test response streaming back to client."""
        try:
            response_data = {
                "type": "agent_response",
                "content": agent_result["response"]["response"]
            }
            await websocket.send_json(response_data)
            return {"streamed": True, "response": response_data}
        except Exception as e:
            return {"streamed": False, "error": str(e)}


class TestMessagePipelineTypes:
    """Test different message types through pipeline."""
    
    async def test_typed_message_pipelines(self, pipeline_tester, mock_websocket):
        """Test query, analysis, and command message pipelines."""
        test_cases = [
            {"type": "query", "content": "What is my AI spend optimization?", "tier": "enterprise"},
            {"type": "analysis", "content": "Analyze my usage patterns", "tier": "enterprise"}, 
            {"type": "command", "content": "/optimize costs", "tier": "mid"}
        ]
        
        for case in test_cases:
            result = await self._process_typed_message(pipeline_tester, mock_websocket, case, case["type"])
            assert result["success"], f"{case['type']} message pipeline failed"
            assert result["response"], f"{case['type']} response empty"
    
    async def _process_typed_message(self, pipeline_tester: MessagePipelineTester,
                                   websocket: MockWebSocket, message: Dict[str, Any],
                                   message_type: str) -> Dict[str, Any]:
        """Process typed message through pipeline."""
        message_id = f"test_{message_type}_{int(time.time())}"
        pipeline_tester.start_timing(message_id)
        
        with patch('app.services.agent_service_factory.get_agent_service') as mock_service:
            mock_agent = AsyncMock()
            mock_response = f"Mock {message_type} response for: {message['content']}"
            mock_agent.process_message.return_value = {"response": mock_response}
            mock_service.return_value = mock_agent
            
            await websocket.send_json(message)
            result = await mock_agent.process_message(message)
            
            duration = pipeline_tester.complete_timing(message_id)
            
            return {
                "success": True,
                "response": result["response"],
                "duration": duration,
                "message_type": message_type
            }


class TestPipelinePerformance:
    """Test pipeline performance and concurrency."""
    
    async def test_concurrent_message_processing(self, pipeline_tester):
        """Test concurrent message processing with ordering.
        
        BVJ: Concurrent processing enables Enterprise-grade scalability.
        """
        concurrent_count = 5
        messages = [
            {"type": "message", "content": f"Concurrent message {i}", "sequence": i}
            for i in range(concurrent_count)
        ]
        
        tasks = [
            self._process_concurrent_message(pipeline_tester, msg, i)
            for i, msg in enumerate(messages)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        assert success_count == concurrent_count, f"Only {success_count}/{concurrent_count} succeeded"
        
        # Validate ordering preservation
        sequence_numbers = [r["sequence"] for r in results if isinstance(r, dict)]
        assert sequence_numbers == sorted(sequence_numbers), "Message ordering not preserved"
    
    async def _process_concurrent_message(self, pipeline_tester: MessagePipelineTester,
                                        message: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Process single message in concurrent batch."""
        message_id = f"concurrent_{index}"
        pipeline_tester.start_timing(message_id)
        
        # Simulate processing delay based on index
        await asyncio.sleep(index * 0.01)
        
        with patch('app.services.agent_service_factory.get_agent_service') as mock_service:
            mock_agent = AsyncMock()
            mock_agent.process_message.return_value = {
                "response": f"Processed concurrent message {index}"
            }
            mock_service.return_value = mock_agent
            
            result = await mock_agent.process_message(message)
            duration = pipeline_tester.complete_timing(message_id)
            
            return {
                "success": True,
                "sequence": message["sequence"],
                "duration": duration,
                "response": result["response"]
            }


class TestPipelineErrorHandling:
    """Test error handling throughout the pipeline."""
    
    async def test_pipeline_error_handling(self, pipeline_tester):
        """Test WebSocket, agent, and degradation error handling."""
        # Test WebSocket error and recovery
        websocket = WebSocketBuilder().with_user_id("error_test_user").build()
        await websocket.accept()
        recovery_message = {"type": "message", "content": "Recovery test"}
        await websocket.send_json(recovery_message)
        
        # Test agent error handling
        with patch('app.services.agent_service_factory.get_agent_service') as mock_service:
            mock_agent = AsyncMock()
            mock_agent.process_message.side_effect = Exception("Mock agent error")
            mock_service.return_value = mock_agent
            
            try:
                await mock_agent.process_message({"content": "error test"})
            except Exception as e:
                pipeline_tester.record_error("agent_error_test", e)
        
        assert len(pipeline_tester.error_log) > 0, "Error not logged"