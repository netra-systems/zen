"""
Test Chat Content Validation and Response Quality

Tests that chat send/receive functionality not only works technically, 
but also validates that responses are relevant and meaningful.

This test focuses on content quality and relevance - a critical gap in existing tests
that only verify messages are sent/received but not their quality or relevance.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: AI Response Quality and User Satisfaction
- Value Impact: Ensures AI responses are relevant, helpful, and contextually appropriate
- Revenue Impact: Higher quality responses lead to better user retention and conversions
"""

import asyncio
import json
import uuid
from typing import Any, Dict, List
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent


class TestChatContentValidation:
    """Test chat content validation and response quality."""
    pass

    @pytest.mark.asyncio
    async def test_chat_response_relevance_validation(self):
        """
        Test that AI responses are contextually relevant to user queries.
        
        This test validates that when a user asks a specific question,
        the AI response actually addresses that question meaningfully.
        This is currently MISSING from existing test coverage.
        """
    pass
        # Setup tracking for responses
        actual_responses = []
        
        async def mock_send_message(user_id: str, message: Dict[str, Any]):
            """Capture sent messages for validation."""
            actual_responses.append({"user_id": user_id, "message": message})
        
        # Create comprehensive mocks
        mock_websocket_manager = MagicNone  # TODO: Use real service instance
        mock_websocket_manager.send_message = AsyncMock(side_effect=mock_send_message)
        mock_websocket_manager.send_error = AsyncMock(side_effect=mock_send_message)
        mock_websocket_manager.send_to_user = AsyncMock(side_effect=mock_send_message)
        
        # Add broadcasting mock
        mock_broadcasting = MagicNone  # TODO: Use real service instance
        mock_broadcasting.join_room = AsyncNone  # TODO: Use real service instance
        mock_broadcasting.leave_room = AsyncNone  # TODO: Use real service instance
        mock_websocket_manager.broadcasting = mock_broadcasting
        
        # Create database and LLM mocks
        mock_db_session = AsyncNone  # TODO: Use real service instance
        mock_llm_manager = AsyncNone  # TODO: Use real service instance
        
        # CRITICAL: Mock LLM to await asyncio.sleep(0)
    return generic/irrelevant response
        # This simulates the case where AI isn't properly understanding context
        mock_llm_manager.ask_llm = AsyncMock(
            return_value="Hello! I'm an AI assistant. I can help with many things."
        )
        
        mock_tool_dispatcher = MagicNone  # TODO: Use real service instance
        mock_tool_dispatcher.get_available_tools = MagicMock(return_value=["chat", "help"])
        
        # Create agent service
        supervisor = SupervisorAgent(
            db_session=mock_db_session,
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            websocket_manager=mock_websocket_manager
        )
        
        agent_service = AgentService(supervisor)
        
        # Test specific technical query
        technical_message = {
            "type": "user_message",
            "payload": {
                "content": "How can I optimize my PostgreSQL database queries for better performance?",
                "thread_id": "test_technical_thread"
            }
        }
        
        with patch('netra_backend.app.services.agent_service_core.manager', mock_websocket_manager):
            with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
                await agent_service.handle_websocket_message(
                    user_id="test_user_tech",
                    message=technical_message,
                    db_session=mock_db_session
                )
        
        # VALIDATION: Check if response is relevant to PostgreSQL optimization
        print(f"Captured responses: {len(actual_responses)}")
        for response in actual_responses:
            print(f"Response: {response}")
        
        # This test should FAIL because current system doesn't validate response relevance
        assert len(actual_responses) > 0, "Should receive at least one response"
        
        # Extract response content - handle different response structures
        response_found = False
        response_content = ""
        
        for response in actual_responses:
            print(f"Examining response: {response}")
            
            # Handle different response structures
            if "message" in response:
                msg = response["message"]
                if isinstance(msg, dict) and msg.get("type") == "agent_response":
                    response_content = msg.get("payload", {}).get("content", "")
                    response_found = True
                    break
                elif isinstance(msg, str):
                    response_content = msg
                    response_found = True
                    break
            elif "error" in response:
                # Even error messages should be relevant
                response_content = response["error"] 
                response_found = True
                break
        
        # This assertion should FAIL - proving we need better content validation
        if response_found:
            # Check for PostgreSQL-related keywords in response
            postgresql_keywords = ["postgresql", "postgres", "database", "query", "performance", "optimize", "index", "explain"]
            contains_relevant_content = any(keyword in response_content.lower() for keyword in postgresql_keywords)
            
            assert contains_relevant_content, f"Response not relevant to PostgreSQL query: '{response_content}'"
        else:
            # If no proper response structure, that's also a failure
            assert False, "No properly structured agent response found"

    @pytest.mark.asyncio
    async def test_chat_response_completeness_validation(self):
        """
    pass
        Test that AI responses provide complete answers, not just acknowledgments.
        
        This validates response quality - another gap in current testing.
        """
        actual_responses = []
        
        async def mock_send_message(user_id: str, message: Dict[str, Any]):
    pass
            actual_responses.append({"user_id": user_id, "message": message})
        
        # Setup mocks
        mock_websocket_manager = MagicNone  # TODO: Use real service instance
        mock_websocket_manager.send_message = AsyncMock(side_effect=mock_send_message)
        mock_websocket_manager.send_error = AsyncMock(side_effect=mock_send_message)
        mock_websocket_manager.send_to_user = AsyncMock(side_effect=mock_send_message)
        
        mock_broadcasting = MagicNone  # TODO: Use real service instance
        mock_broadcasting.join_room = AsyncNone  # TODO: Use real service instance
        mock_broadcasting.leave_room = AsyncNone  # TODO: Use real service instance
        mock_websocket_manager.broadcasting = mock_broadcasting
        
        mock_db_session = AsyncNone  # TODO: Use real service instance
        mock_llm_manager = AsyncNone  # TODO: Use real service instance
        
        # Mock with minimal/incomplete response
        mock_llm_manager.ask_llm = AsyncMock(return_value="Yes, I can help with that.")
        
        mock_tool_dispatcher = MagicNone  # TODO: Use real service instance
        mock_tool_dispatcher.get_available_tools = MagicMock(return_value=["chat"])
        
        supervisor = SupervisorAgent(
            db_session=mock_db_session,
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            websocket_manager=mock_websocket_manager
        )
        
        agent_service = AgentService(supervisor)
        
        # Test detailed how-to question
        detailed_question = {
            "type": "user_message", 
            "payload": {
                "content": "Can you provide step-by-step instructions to set up Docker containers for microservices deployment?",
                "thread_id": "test_detailed_thread"
            }
        }
        
        with patch('netra_backend.app.services.agent_service_core.manager', mock_websocket_manager):
            with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
                await agent_service.handle_websocket_message(
                    user_id="test_user_detailed",
                    message=detailed_question,
                    db_session=mock_db_session
                )
        
        # Validate response completeness
        assert len(actual_responses) > 0, "Should receive response"
        
        response_content = ""
        for response in actual_responses:
            if "message" in response and response["message"].get("type") == "agent_response":
                response_content = response["message"].get("payload", {}).get("content", "")
                break
        
        # This should FAIL - response should be comprehensive, not just "Yes, I can help"
        if response_content:
            # Check for completeness indicators
            completeness_indicators = ["step", "first", "then", "next", "docker", "container", "setup", "deploy"]
            is_complete_response = any(indicator in response_content.lower() for indicator in completeness_indicators)
            
            # Also check minimum length for detailed responses
            is_sufficient_length = len(response_content) > 50
            
            assert is_complete_response and is_sufficient_length, (
                f"Response too brief/incomplete for detailed question: '{response_content}'"
            )
        else:
            assert False, "No response content found"

    @pytest.mark.asyncio
    async def test_chat_context_retention_validation(self):
        """
        Test that AI maintains context across multiple messages in conversation.
        
        This tests conversational memory - critical for chat quality.
        """
    pass
        actual_responses = []
        conversation_context = []
        
        async def mock_send_message(user_id: str, message: Dict[str, Any]):
    pass
            actual_responses.append({"user_id": user_id, "message": message})
            # Track conversation for context
            if message.get("type") == "agent_response":
                conversation_context.append(message.get("payload", {}).get("content", ""))
        
        # Setup mocks
        mock_websocket_manager = MagicNone  # TODO: Use real service instance
        mock_websocket_manager.send_message = AsyncMock(side_effect=mock_send_message)
        mock_websocket_manager.send_error = AsyncMock(side_effect=mock_send_message)
        mock_websocket_manager.send_to_user = AsyncMock(side_effect=mock_send_message)
        
        mock_broadcasting = MagicNone  # TODO: Use real service instance
        mock_broadcasting.join_room = AsyncNone  # TODO: Use real service instance
        mock_broadcasting.leave_room = AsyncNone  # TODO: Use real service instance
        mock_websocket_manager.broadcasting = mock_broadcasting
        
        mock_db_session = AsyncNone  # TODO: Use real service instance
        mock_llm_manager = AsyncNone  # TODO: Use real service instance
        
        # Mock responses that DON'T maintain context
        responses = [
            "I can help you with AWS deployment.",
            "Hello! How can I assist you today?",  # Forgets previous context
            "I'm an AI assistant."  # Generic response ignoring conversation
        ]
        response_index = 0
        
        async def mock_ask_llm(prompt, *args, **kwargs):
    pass
            nonlocal response_index
            if response_index < len(responses):
                result = responses[response_index]
                response_index += 1
                await asyncio.sleep(0)
    return result
            return "I can help you with that."
        
        mock_llm_manager.ask_llm = AsyncMock(side_effect=mock_ask_llm)
        
        mock_tool_dispatcher = MagicNone  # TODO: Use real service instance
        mock_tool_dispatcher.get_available_tools = MagicMock(return_value=["chat"])
        
        supervisor = SupervisorAgent(
            db_session=mock_db_session,
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            websocket_manager=mock_websocket_manager
        )
        
        agent_service = AgentService(supervisor)
        
        # Send first message about AWS
        message1 = {
            "type": "user_message",
            "payload": {
                "content": "I need help setting up AWS EC2 instances for production.",
                "thread_id": "context_test_thread"
            }
        }
        
        with patch('netra_backend.app.services.agent_service_core.manager', mock_websocket_manager):
            with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
                await agent_service.handle_websocket_message(
                    user_id="test_context_user",
                    message=message1,
                    db_session=mock_db_session
                )
        
        # Send follow-up question that should reference previous context
        message2 = {
            "type": "user_message",
            "payload": {
                "content": "What about security groups for those instances?",
                "thread_id": "context_test_thread"  # Same thread
            }
        }
        
        with patch('netra_backend.app.services.agent_service_core.manager', mock_websocket_manager):
            with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
                await agent_service.handle_websocket_message(
                    user_id="test_context_user",
                    message=message2,
                    db_session=mock_db_session
                )
        
        # Validate context retention
        assert len(actual_responses) >= 2, "Should receive responses to both messages"
        
        # Check if second response acknowledges the EC2/AWS context
        second_response_content = ""
        response_count = 0
        for response in actual_responses:
            if "message" in response and response["message"].get("type") == "agent_response":
                response_count += 1
                if response_count == 2:  # Second AI response
                    second_response_content = response["message"].get("payload", {}).get("content", "")
                    break
        
        # This should FAIL - second response should reference AWS/EC2 context
        if second_response_content:
            context_indicators = ["ec2", "aws", "instances", "security group", "security"]
            maintains_context = any(indicator in second_response_content.lower() for indicator in context_indicators)
            
            assert maintains_context, (
                f"Second response lost conversation context about AWS EC2: '{second_response_content}'"
            )
        else:
            assert False, "No second response found to validate context retention"

    @pytest.mark.asyncio
    async def test_chat_error_message_quality(self):
        """
        Test that error messages in chat are helpful and actionable.
        
        This validates error handling quality in chat interactions.
        """
    pass
        actual_responses = []
        
        async def mock_send_error(user_id: str, error: str):
    pass
            actual_responses.append({"user_id": user_id, "error": error, "type": "error"})
        
        async def mock_send_message(user_id: str, message: Dict[str, Any]):
    pass
            actual_responses.append({"user_id": user_id, "message": message})
        
        # Setup mocks
        mock_websocket_manager = MagicNone  # TODO: Use real service instance
        mock_websocket_manager.send_message = AsyncMock(side_effect=mock_send_message)
        mock_websocket_manager.send_error = AsyncMock(side_effect=mock_send_error)
        mock_websocket_manager.send_to_user = AsyncMock(side_effect=mock_send_message)
        
        mock_broadcasting = MagicNone  # TODO: Use real service instance
        mock_broadcasting.join_room = AsyncNone  # TODO: Use real service instance
        mock_broadcasting.leave_room = AsyncNone  # TODO: Use real service instance
        mock_websocket_manager.broadcasting = mock_broadcasting
        
        mock_db_session = AsyncNone  # TODO: Use real service instance
        
        supervisor = SupervisorAgent(
            db_session=mock_db_session,
            llm_manager=AsyncNone  # TODO: Use real service instance,
            tool_dispatcher=MagicNone  # TODO: Use real service instance,
            websocket_manager=mock_websocket_manager
        )
        
        agent_service = AgentService(supervisor)
        
        # Send malformed message to trigger error
        malformed_message = {
            "invalid_structure": True,
            # Missing "type" field which is required
        }
        
        with patch('netra_backend.app.services.agent_service_core.manager', mock_websocket_manager):
            with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
                await agent_service.handle_websocket_message(
                    user_id="test_error_user",
                    message=malformed_message,
                    db_session=mock_db_session
                )
        
        # Validate error message quality
        assert len(actual_responses) > 0, "Should receive error response"
        
        error_found = False
        error_message = ""
        
        for response in actual_responses:
            if "error" in response:
                error_message = response["error"]
                error_found = True
                break
        
        # This should validate that error messages are helpful
        if error_found:
            # Check that error message is helpful, not just generic
            assert "type" in error_message or "required" in error_message, (
                f"Error message not helpful enough: '{error_message}'"
            )
            # Check it's not too generic
            assert error_message != "Internal server error", (
                f"Error message too generic: '{error_message}'"
            )
        else:
            assert False, "No error message found for malformed input"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])