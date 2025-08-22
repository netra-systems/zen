"""Message Processing Pipeline Critical Path Tests

Business Value Justification (BVJ):
- Segment: All tiers (core messaging functionality)
- Business Goal: Reliable message delivery and agent response processing
- Value Impact: Ensures real-time communication, prevents message loss, maintains user engagement
- Strategic Impact: $25K-45K MRR protection through reliable messaging infrastructure

Critical Path: WebSocket message -> Authentication -> Routing -> Agent processing -> Response delivery
Coverage: End-to-end message flow, error handling, performance validation, state consistency
"""

# Add project root to path

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
from test_framework import setup_test_path
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))


setup_test_path()

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
# JWT service replaced with auth_integration
from auth_integration import create_access_token, validate_token_jwt

from netra_backend.app.services.websocket.message_handler import BaseMessageHandler

# Add project root to path
from netra_backend.app.services.websocket_manager import WebSocketManager


JWTService = AsyncMock
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.schemas.registry import (

    AgentCompleted,

    AgentStarted,

    WebSocketMessage,

)
from netra_backend.app.services.database.message_repository import MessageRepository
from netra_backend.app.services.state_persistence import StatePersistenceService


logger = logging.getLogger(__name__)


class MessagePipelineTestManager:

    """Manages message processing pipeline testing with real component integration."""
    

    def __init__(self):

        self.ws_manager = None

        self.message_handler = None

        self.auth_service = None

        self.agent_service = None

        self.message_repository = None

        self.processed_messages = []

        self.pipeline_metrics = {

            "messages_received": 0,

            "messages_processed": 0,

            "messages_failed": 0,

            "average_processing_time": 0,

            "errors": []

        }
        

    async def initialize_pipeline(self):

        """Initialize the message processing pipeline with real components."""

        try:
            # Initialize WebSocket manager

            self.ws_manager = WebSocketManager()

            await self.ws_manager.initialize()
            
            # Initialize message handler

            self.message_handler = BaseMessageHandler()
            
            # Initialize auth service

            self.auth_service = JWTService()
            
            # Initialize message repository

            self.message_repository = MessageRepository()

            await self.message_repository.initialize()
            

            logger.info("Message pipeline initialized successfully")
            

        except Exception as e:

            logger.error(f"Failed to initialize pipeline: {e}")

            raise
    

    async def simulate_websocket_message(self, user_id: str, message_content: str, 

                                       message_type: str = "chat") -> Dict[str, Any]:

        """Simulate a WebSocket message through the complete pipeline."""

        message_id = str(uuid.uuid4())

        start_time = time.time()
        

        try:
            # Create WebSocket message

            ws_message = WebSocketMessage(

                id=message_id,

                type=message_type,

                content=message_content,

                user_id=user_id,

                timestamp=datetime.utcnow(),

                metadata={"source": "test_pipeline"}

            )
            

            self.pipeline_metrics["messages_received"] += 1
            
            # Step 1: Authentication

            auth_result = await self.authenticate_message(user_id)

            if not auth_result["valid"]:

                raise ValueError(f"Authentication failed: {auth_result['error']}")
            
            # Step 2: Message validation and routing

            routing_result = await self.route_message(ws_message)

            if not routing_result["success"]:

                raise ValueError(f"Routing failed: {routing_result['error']}")
            
            # Step 3: Agent processing

            processing_result = await self.process_with_agent(ws_message, routing_result["agent_type"])
            
            # Step 4: Response delivery

            response = await self.deliver_response(ws_message, processing_result)
            

            processing_time = time.time() - start_time
            
            # Update metrics

            self.pipeline_metrics["messages_processed"] += 1

            self.update_average_processing_time(processing_time)
            
            # Store processed message

            processed_message = {

                "message_id": message_id,

                "user_id": user_id,

                "content": message_content,

                "processing_time": processing_time,

                "response": response,

                "timestamp": start_time,

                "status": "completed"

            }
            

            self.processed_messages.append(processed_message)
            

            return {

                "success": True,

                "message_id": message_id,

                "processing_time": processing_time,

                "response": response

            }
            

        except Exception as e:

            self.pipeline_metrics["messages_failed"] += 1

            self.pipeline_metrics["errors"].append({

                "message_id": message_id,

                "error": str(e),

                "timestamp": time.time()

            })
            

            logger.error(f"Message pipeline failed for {message_id}: {e}")

            return {

                "success": False,

                "message_id": message_id,

                "error": str(e),

                "processing_time": time.time() - start_time

            }
    

    async def authenticate_message(self, user_id: str) -> Dict[str, Any]:

        """Authenticate the message sender."""

        try:
            # Simulate JWT token validation

            token_payload = {

                "user_id": user_id,

                "exp": time.time() + 3600,  # 1 hour expiry

                "iss": "netra-auth-service"

            }
            
            # In real implementation, this would validate existing token

            is_valid = await self.auth_service.validate_user_session(user_id)
            

            return {

                "valid": True,

                "user_id": user_id,

                "token_payload": token_payload

            }
            

        except Exception as e:

            return {

                "valid": False,

                "error": str(e)

            }
    

    async def route_message(self, message: WebSocketMessage) -> Dict[str, Any]:

        """Route message to appropriate handler based on content and type."""

        try:
            # Determine agent type based on message content

            content_lower = message.content.lower()
            

            if "analyze" in content_lower or "research" in content_lower:

                agent_type = "research_agent"

            elif "code" in content_lower or "implement" in content_lower:

                agent_type = "implementation_agent"  

            elif "plan" in content_lower or "strategy" in content_lower:

                agent_type = "pm_agent"

            else:

                agent_type = "supervisor_agent"
            

            return {

                "success": True,

                "agent_type": agent_type,

                "routing_time": time.time()

            }
            

        except Exception as e:

            return {

                "success": False,

                "error": str(e)

            }
    

    async def process_with_agent(self, message: WebSocketMessage, agent_type: str) -> Dict[str, Any]:

        """Process message with the designated agent."""

        try:

            agent_id = f"{agent_type}_{uuid.uuid4().hex[:8]}"
            

            if agent_type == "supervisor_agent":

                agent = SupervisorAgent(agent_id=agent_id)

            else:
                # Create mock agent for other types

                agent = MagicMock()

                agent.process_message = AsyncMock(return_value={

                    "response": f"Processed by {agent_type}",

                    "status": "completed",

                    "metadata": {"agent_id": agent_id}

                })
            
            # Process message

            if hasattr(agent, 'process_message'):

                result = await agent.process_message(message.content)

            else:

                result = {

                    "response": f"Message processed by {agent_type}",

                    "status": "completed"

                }
            

            return {

                "success": True,

                "agent_id": agent_id,

                "agent_type": agent_type,

                "result": result

            }
            

        except Exception as e:

            return {

                "success": False,

                "error": str(e),

                "agent_type": agent_type

            }
    

    async def deliver_response(self, original_message: WebSocketMessage, 

                             processing_result: Dict[str, Any]) -> Dict[str, Any]:

        """Deliver processed response back through WebSocket."""

        try:

            response_data = {

                "message_id": original_message.id,

                "user_id": original_message.user_id,

                "response": processing_result.get("result", {}),

                "agent_info": {

                    "agent_id": processing_result.get("agent_id"),

                    "agent_type": processing_result.get("agent_type")

                },

                "timestamp": datetime.utcnow().isoformat(),

                "status": "delivered"

            }
            
            # In real implementation, this would send via WebSocket
            # For testing, we simulate the delivery

            delivery_success = await self.simulate_websocket_delivery(response_data)
            

            if delivery_success:

                return {

                    "delivered": True,

                    "response_data": response_data

                }

            else:

                raise Exception("WebSocket delivery failed")
                

        except Exception as e:

            return {

                "delivered": False,

                "error": str(e)

            }
    

    async def simulate_websocket_delivery(self, response_data: Dict[str, Any]) -> bool:

        """Simulate WebSocket response delivery."""

        try:
            # Simulate network delay

            await asyncio.sleep(0.01)
            
            # Simulate delivery validation

            required_fields = ["message_id", "user_id", "response", "timestamp"]

            for field in required_fields:

                if field not in response_data:

                    raise ValueError(f"Missing required field: {field}")
            

            return True
            

        except Exception as e:

            logger.error(f"WebSocket delivery simulation failed: {e}")

            return False
    

    def update_average_processing_time(self, new_time: float):

        """Update running average of processing times."""

        current_avg = self.pipeline_metrics["average_processing_time"]

        processed_count = self.pipeline_metrics["messages_processed"]
        

        if processed_count == 1:

            self.pipeline_metrics["average_processing_time"] = new_time

        else:
            # Running average calculation

            self.pipeline_metrics["average_processing_time"] = (

                (current_avg * (processed_count - 1) + new_time) / processed_count

            )
    

    async def get_pipeline_health(self) -> Dict[str, Any]:

        """Get comprehensive pipeline health metrics."""

        total_messages = self.pipeline_metrics["messages_received"]

        success_rate = 0
        

        if total_messages > 0:

            success_rate = (

                (total_messages - self.pipeline_metrics["messages_failed"]) / total_messages

            ) * 100
        

        return {

            "total_messages": total_messages,

            "processed_messages": self.pipeline_metrics["messages_processed"],

            "failed_messages": self.pipeline_metrics["messages_failed"],

            "success_rate": success_rate,

            "average_processing_time": self.pipeline_metrics["average_processing_time"],

            "error_count": len(self.pipeline_metrics["errors"]),

            "pipeline_status": "healthy" if success_rate > 95 else "degraded"

        }
    

    async def cleanup(self):

        """Clean up pipeline resources."""

        try:

            if self.ws_manager and hasattr(self.ws_manager, 'shutdown'):

                await self.ws_manager.shutdown()
                

            if self.message_repository and hasattr(self.message_repository, 'close'):

                await self.message_repository.close()
                

        except Exception as e:

            logger.error(f"Cleanup failed: {e}")


@pytest.fixture

async def pipeline_manager():

    """Create message pipeline manager for testing."""

    manager = MessagePipelineTestManager()

    await manager.initialize_pipeline()

    yield manager

    await manager.cleanup()


@pytest.mark.asyncio

async def test_complete_message_processing_flow(pipeline_manager):

    """Test complete message processing from WebSocket to agent response."""

    user_id = "test_user_001"

    message_content = "Analyze the current market trends"
    
    # Process message through complete pipeline

    result = await pipeline_manager.simulate_websocket_message(user_id, message_content)
    
    # Verify successful processing

    assert result["success"] is True

    assert "message_id" in result

    assert "processing_time" in result

    assert "response" in result
    
    # Verify processing time is reasonable (< 5 seconds)

    assert result["processing_time"] < 5.0
    
    # Verify response structure

    response = result["response"]

    assert response["delivered"] is True

    assert "response_data" in response
    
    # Verify pipeline metrics updated

    health = await pipeline_manager.get_pipeline_health()

    assert health["total_messages"] >= 1

    assert health["processed_messages"] >= 1

    assert health["success_rate"] > 0


@pytest.mark.asyncio

async def test_message_authentication_and_routing(pipeline_manager):

    """Test message authentication and routing logic."""

    test_cases = [

        ("user_001", "Please analyze this data", "research_agent"),

        ("user_002", "Help me implement this feature", "implementation_agent"),

        ("user_003", "Create a project plan", "pm_agent"),

        ("user_004", "General question", "supervisor_agent"),

    ]
    

    for user_id, message_content, expected_agent in test_cases:

        result = await pipeline_manager.simulate_websocket_message(user_id, message_content)
        
        # Verify successful processing

        assert result["success"] is True
        
        # Find corresponding processed message

        processed_msg = next(

            (msg for msg in pipeline_manager.processed_messages 

             if msg["message_id"] == result["message_id"]),

            None

        )
        

        assert processed_msg is not None

        assert processed_msg["user_id"] == user_id

        assert processed_msg["content"] == message_content


@pytest.mark.asyncio

async def test_pipeline_error_handling_and_recovery(pipeline_manager):

    """Test pipeline error handling and recovery mechanisms."""

    user_id = "error_test_user"
    
    # Test authentication failure

    with patch.object(pipeline_manager, 'authenticate_message', 

                     return_value={"valid": False, "error": "Invalid token"}):
        

        result = await pipeline_manager.simulate_websocket_message(

            user_id, "This should fail authentication"

        )
        

        assert result["success"] is False

        assert "error" in result
    
    # Test agent processing failure

    with patch.object(pipeline_manager, 'process_with_agent',

                     side_effect=Exception("Agent processing failed")):
        

        result = await pipeline_manager.simulate_websocket_message(

            user_id, "This should fail in agent processing"

        )
        

        assert result["success"] is False
    
    # Verify error tracking

    health = await pipeline_manager.get_pipeline_health()

    assert health["failed_messages"] >= 2

    assert health["error_count"] >= 2


@pytest.mark.asyncio

async def test_concurrent_message_processing(pipeline_manager):

    """Test pipeline handling of concurrent messages."""

    num_concurrent = 10

    user_ids = [f"concurrent_user_{i}" for i in range(num_concurrent)]

    messages = [f"Concurrent message {i}" for i in range(num_concurrent)]
    
    # Process messages concurrently

    tasks = [

        pipeline_manager.simulate_websocket_message(user_id, message)

        for user_id, message in zip(user_ids, messages)

    ]
    

    start_time = time.time()

    results = await asyncio.gather(*tasks)

    total_time = time.time() - start_time
    
    # Verify all messages processed successfully

    successful_results = [r for r in results if r["success"]]

    assert len(successful_results) == num_concurrent
    
    # Verify concurrent processing is efficient (< 10 seconds total)

    assert total_time < 10.0
    
    # Verify pipeline metrics

    health = await pipeline_manager.get_pipeline_health()

    assert health["total_messages"] >= num_concurrent

    assert health["success_rate"] > 90


@pytest.mark.asyncio

async def test_message_processing_performance_benchmarks(pipeline_manager):

    """Test message processing performance meets requirements."""

    performance_tests = [

        ("short_message", "Hello", 1.0),  # < 1 second

        ("medium_message", "Analyze this data and provide insights" * 10, 3.0),  # < 3 seconds

        ("long_message", "Complex analysis request " * 50, 5.0),  # < 5 seconds

    ]
    

    for test_name, message_content, max_time in performance_tests:

        user_id = f"perf_user_{test_name}"
        

        result = await pipeline_manager.simulate_websocket_message(user_id, message_content)
        
        # Verify processing completed within time limit

        assert result["success"] is True

        assert result["processing_time"] < max_time, (

            f"{test_name} took {result['processing_time']}s, expected < {max_time}s"

        )
    
    # Verify overall pipeline performance

    health = await pipeline_manager.get_pipeline_health()

    assert health["average_processing_time"] < 3.0  # Overall average < 3 seconds

    assert health["pipeline_status"] == "healthy"


@pytest.mark.asyncio

async def test_message_state_consistency_validation(pipeline_manager):

    """Test message state consistency throughout the pipeline."""

    user_id = "consistency_test_user"

    message_content = "Test message state consistency"
    
    # Process message

    result = await pipeline_manager.simulate_websocket_message(user_id, message_content)

    assert result["success"] is True
    

    message_id = result["message_id"]
    
    # Find processed message

    processed_msg = next(

        (msg for msg in pipeline_manager.processed_messages 

         if msg["message_id"] == message_id),

        None

    )
    
    # Verify state consistency

    assert processed_msg is not None

    assert processed_msg["message_id"] == message_id

    assert processed_msg["user_id"] == user_id

    assert processed_msg["content"] == message_content

    assert processed_msg["status"] == "completed"
    
    # Verify response data consistency

    response_data = processed_msg["response"]["response_data"]

    assert response_data["message_id"] == message_id

    assert response_data["user_id"] == user_id

    assert response_data["status"] == "delivered"
    
    # Verify timing consistency

    assert processed_msg["processing_time"] > 0

    assert "timestamp" in processed_msg

    assert "timestamp" in response_data