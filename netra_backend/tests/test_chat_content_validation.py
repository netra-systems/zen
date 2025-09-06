# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Test Chat Content Validation and Response Quality

# REMOVED_SYNTAX_ERROR: Tests that chat send/receive functionality not only works technically,
# REMOVED_SYNTAX_ERROR: but also validates that responses are relevant and meaningful.

# REMOVED_SYNTAX_ERROR: This test focuses on content quality and relevance - a critical gap in existing tests
# REMOVED_SYNTAX_ERROR: that only verify messages are sent/received but not their quality or relevance.

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: All (Free, Early, Mid, Enterprise)
    # REMOVED_SYNTAX_ERROR: - Business Goal: AI Response Quality and User Satisfaction
    # REMOVED_SYNTAX_ERROR: - Value Impact: Ensures AI responses are relevant, helpful, and contextually appropriate
    # REMOVED_SYNTAX_ERROR: - Revenue Impact: Higher quality responses lead to better user retention and conversions
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: from typing import Any, Dict, List
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.docker.unified_docker_manager import UnifiedDockerManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: import pytest

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_service_core import AgentService
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent


# REMOVED_SYNTAX_ERROR: class TestChatContentValidation:
    # REMOVED_SYNTAX_ERROR: """Test chat content validation and response quality."""
    # REMOVED_SYNTAX_ERROR: pass

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_chat_response_relevance_validation(self):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test that AI responses are contextually relevant to user queries.

        # REMOVED_SYNTAX_ERROR: This test validates that when a user asks a specific question,
        # REMOVED_SYNTAX_ERROR: the AI response actually addresses that question meaningfully.
        # REMOVED_SYNTAX_ERROR: This is currently MISSING from existing test coverage.
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # Setup tracking for responses
        # REMOVED_SYNTAX_ERROR: actual_responses = []

# REMOVED_SYNTAX_ERROR: async def mock_send_message(user_id: str, message: Dict[str, Any]):
    # REMOVED_SYNTAX_ERROR: """Capture sent messages for validation."""
    # REMOVED_SYNTAX_ERROR: actual_responses.append({"user_id": user_id, "message": message})

    # Create comprehensive mocks
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager = MagicNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager.send_message = AsyncMock(side_effect=mock_send_message)
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager.send_error = AsyncMock(side_effect=mock_send_message)
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager.send_to_user = AsyncMock(side_effect=mock_send_message)

    # Add broadcasting mock
    # REMOVED_SYNTAX_ERROR: mock_broadcasting = MagicNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_broadcasting.join_room = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_broadcasting.leave_room = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager.broadcasting = mock_broadcasting

    # Create database and LLM mocks
    # REMOVED_SYNTAX_ERROR: mock_db_session = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_llm_manager = AsyncNone  # TODO: Use real service instance

    # CRITICAL: Mock LLM to await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return generic/irrelevant response
    # This simulates the case where AI isn't properly understanding context
    # REMOVED_SYNTAX_ERROR: mock_llm_manager.ask_llm = AsyncMock( )
    # REMOVED_SYNTAX_ERROR: return_value="Hello! I"m an AI assistant. I can help with many things."
    

    # REMOVED_SYNTAX_ERROR: mock_tool_dispatcher = MagicNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_tool_dispatcher.get_available_tools = MagicMock(return_value=["chat", "help"])

    # Create agent service
    # REMOVED_SYNTAX_ERROR: supervisor = SupervisorAgent( )
    # REMOVED_SYNTAX_ERROR: db_session=mock_db_session,
    # REMOVED_SYNTAX_ERROR: llm_manager=mock_llm_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=mock_tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: websocket_manager=mock_websocket_manager
    

    # REMOVED_SYNTAX_ERROR: agent_service = AgentService(supervisor)

    # Test specific technical query
    # REMOVED_SYNTAX_ERROR: technical_message = { )
    # REMOVED_SYNTAX_ERROR: "type": "user_message",
    # REMOVED_SYNTAX_ERROR: "payload": { )
    # REMOVED_SYNTAX_ERROR: "content": "How can I optimize my PostgreSQL database queries for better performance?",
    # REMOVED_SYNTAX_ERROR: "thread_id": "test_technical_thread"
    
    

    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.services.agent_service_core.manager', mock_websocket_manager):
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
            # REMOVED_SYNTAX_ERROR: await agent_service.handle_websocket_message( )
            # REMOVED_SYNTAX_ERROR: user_id="test_user_tech",
            # REMOVED_SYNTAX_ERROR: message=technical_message,
            # REMOVED_SYNTAX_ERROR: db_session=mock_db_session
            

            # VALIDATION: Check if response is relevant to PostgreSQL optimization
            # REMOVED_SYNTAX_ERROR: print("formatted_string")
            # REMOVED_SYNTAX_ERROR: for response in actual_responses:
                # REMOVED_SYNTAX_ERROR: print("formatted_string")

                # This test should FAIL because current system doesn't validate response relevance
                # REMOVED_SYNTAX_ERROR: assert len(actual_responses) > 0, "Should receive at least one response"

                # Extract response content - handle different response structures
                # REMOVED_SYNTAX_ERROR: response_found = False
                # REMOVED_SYNTAX_ERROR: response_content = ""

                # REMOVED_SYNTAX_ERROR: for response in actual_responses:
                    # REMOVED_SYNTAX_ERROR: print("formatted_string")

                    # Handle different response structures
                    # REMOVED_SYNTAX_ERROR: if "message" in response:
                        # REMOVED_SYNTAX_ERROR: msg = response["message"]
                        # REMOVED_SYNTAX_ERROR: if isinstance(msg, dict) and msg.get("type") == "agent_response":
                            # REMOVED_SYNTAX_ERROR: response_content = msg.get("payload", {}).get("content", "")
                            # REMOVED_SYNTAX_ERROR: response_found = True
                            # REMOVED_SYNTAX_ERROR: break
                            # REMOVED_SYNTAX_ERROR: elif isinstance(msg, str):
                                # REMOVED_SYNTAX_ERROR: response_content = msg
                                # REMOVED_SYNTAX_ERROR: response_found = True
                                # REMOVED_SYNTAX_ERROR: break
                                # REMOVED_SYNTAX_ERROR: elif "error" in response:
                                    # Even error messages should be relevant
                                    # REMOVED_SYNTAX_ERROR: response_content = response["error"]
                                    # REMOVED_SYNTAX_ERROR: response_found = True
                                    # REMOVED_SYNTAX_ERROR: break

                                    # This assertion should FAIL - proving we need better content validation
                                    # REMOVED_SYNTAX_ERROR: if response_found:
                                        # Check for PostgreSQL-related keywords in response
                                        # REMOVED_SYNTAX_ERROR: postgresql_keywords = ["postgresql", "postgres", "database", "query", "performance", "optimize", "index", "explain"]
                                        # REMOVED_SYNTAX_ERROR: contains_relevant_content = any(keyword in response_content.lower() for keyword in postgresql_keywords)

                                        # REMOVED_SYNTAX_ERROR: assert contains_relevant_content, "formatted_string"
                                        # REMOVED_SYNTAX_ERROR: else:
                                            # If no proper response structure, that's also a failure
                                            # REMOVED_SYNTAX_ERROR: assert False, "No properly structured agent response found"

                                            # Removed problematic line: @pytest.mark.asyncio
                                            # Removed problematic line: async def test_chat_response_completeness_validation(self):
                                                # REMOVED_SYNTAX_ERROR: '''
                                                # REMOVED_SYNTAX_ERROR: pass
                                                # REMOVED_SYNTAX_ERROR: Test that AI responses provide complete answers, not just acknowledgments.

                                                # REMOVED_SYNTAX_ERROR: This validates response quality - another gap in current testing.
                                                # REMOVED_SYNTAX_ERROR: '''
                                                # REMOVED_SYNTAX_ERROR: actual_responses = []

# REMOVED_SYNTAX_ERROR: async def mock_send_message(user_id: str, message: Dict[str, Any]):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: actual_responses.append({"user_id": user_id, "message": message})

    # Setup mocks
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager = MagicNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager.send_message = AsyncMock(side_effect=mock_send_message)
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager.send_error = AsyncMock(side_effect=mock_send_message)
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager.send_to_user = AsyncMock(side_effect=mock_send_message)

    # REMOVED_SYNTAX_ERROR: mock_broadcasting = MagicNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_broadcasting.join_room = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_broadcasting.leave_room = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager.broadcasting = mock_broadcasting

    # REMOVED_SYNTAX_ERROR: mock_db_session = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_llm_manager = AsyncNone  # TODO: Use real service instance

    # Mock with minimal/incomplete response
    # REMOVED_SYNTAX_ERROR: mock_llm_manager.ask_llm = AsyncMock(return_value="Yes, I can help with that.")

    # REMOVED_SYNTAX_ERROR: mock_tool_dispatcher = MagicNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_tool_dispatcher.get_available_tools = MagicMock(return_value=["chat"])

    # REMOVED_SYNTAX_ERROR: supervisor = SupervisorAgent( )
    # REMOVED_SYNTAX_ERROR: db_session=mock_db_session,
    # REMOVED_SYNTAX_ERROR: llm_manager=mock_llm_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=mock_tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: websocket_manager=mock_websocket_manager
    

    # REMOVED_SYNTAX_ERROR: agent_service = AgentService(supervisor)

    # Test detailed how-to question
    # REMOVED_SYNTAX_ERROR: detailed_question = { )
    # REMOVED_SYNTAX_ERROR: "type": "user_message",
    # REMOVED_SYNTAX_ERROR: "payload": { )
    # REMOVED_SYNTAX_ERROR: "content": "Can you provide step-by-step instructions to set up Docker containers for microservices deployment?",
    # REMOVED_SYNTAX_ERROR: "thread_id": "test_detailed_thread"
    
    

    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.services.agent_service_core.manager', mock_websocket_manager):
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
            # REMOVED_SYNTAX_ERROR: await agent_service.handle_websocket_message( )
            # REMOVED_SYNTAX_ERROR: user_id="test_user_detailed",
            # REMOVED_SYNTAX_ERROR: message=detailed_question,
            # REMOVED_SYNTAX_ERROR: db_session=mock_db_session
            

            # Validate response completeness
            # REMOVED_SYNTAX_ERROR: assert len(actual_responses) > 0, "Should receive response"

            # REMOVED_SYNTAX_ERROR: response_content = ""
            # REMOVED_SYNTAX_ERROR: for response in actual_responses:
                # REMOVED_SYNTAX_ERROR: if "message" in response and response["message"].get("type") == "agent_response":
                    # REMOVED_SYNTAX_ERROR: response_content = response["message"].get("payload", {}).get("content", "")
                    # REMOVED_SYNTAX_ERROR: break

                    # This should FAIL - response should be comprehensive, not just "Yes, I can help"
                    # REMOVED_SYNTAX_ERROR: if response_content:
                        # Check for completeness indicators
                        # REMOVED_SYNTAX_ERROR: completeness_indicators = ["step", "first", "then", "next", "docker", "container", "setup", "deploy"]
                        # REMOVED_SYNTAX_ERROR: is_complete_response = any(indicator in response_content.lower() for indicator in completeness_indicators)

                        # Also check minimum length for detailed responses
                        # REMOVED_SYNTAX_ERROR: is_sufficient_length = len(response_content) > 50

                        # REMOVED_SYNTAX_ERROR: assert is_complete_response and is_sufficient_length, ( )
                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                        
                        # REMOVED_SYNTAX_ERROR: else:
                            # REMOVED_SYNTAX_ERROR: assert False, "No response content found"

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_chat_context_retention_validation(self):
                                # REMOVED_SYNTAX_ERROR: '''
                                # REMOVED_SYNTAX_ERROR: Test that AI maintains context across multiple messages in conversation.

                                # REMOVED_SYNTAX_ERROR: This tests conversational memory - critical for chat quality.
                                # REMOVED_SYNTAX_ERROR: '''
                                # REMOVED_SYNTAX_ERROR: pass
                                # REMOVED_SYNTAX_ERROR: actual_responses = []
                                # REMOVED_SYNTAX_ERROR: conversation_context = []

# REMOVED_SYNTAX_ERROR: async def mock_send_message(user_id: str, message: Dict[str, Any]):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: actual_responses.append({"user_id": user_id, "message": message})
    # Track conversation for context
    # REMOVED_SYNTAX_ERROR: if message.get("type") == "agent_response":
        # REMOVED_SYNTAX_ERROR: conversation_context.append(message.get("payload", {}).get("content", ""))

        # Setup mocks
        # REMOVED_SYNTAX_ERROR: mock_websocket_manager = MagicNone  # TODO: Use real service instance
        # REMOVED_SYNTAX_ERROR: mock_websocket_manager.send_message = AsyncMock(side_effect=mock_send_message)
        # REMOVED_SYNTAX_ERROR: mock_websocket_manager.send_error = AsyncMock(side_effect=mock_send_message)
        # REMOVED_SYNTAX_ERROR: mock_websocket_manager.send_to_user = AsyncMock(side_effect=mock_send_message)

        # REMOVED_SYNTAX_ERROR: mock_broadcasting = MagicNone  # TODO: Use real service instance
        # REMOVED_SYNTAX_ERROR: mock_broadcasting.join_room = AsyncNone  # TODO: Use real service instance
        # REMOVED_SYNTAX_ERROR: mock_broadcasting.leave_room = AsyncNone  # TODO: Use real service instance
        # REMOVED_SYNTAX_ERROR: mock_websocket_manager.broadcasting = mock_broadcasting

        # REMOVED_SYNTAX_ERROR: mock_db_session = AsyncNone  # TODO: Use real service instance
        # REMOVED_SYNTAX_ERROR: mock_llm_manager = AsyncNone  # TODO: Use real service instance

        # Mock responses that DON'T maintain context
        # REMOVED_SYNTAX_ERROR: responses = [ )
        # REMOVED_SYNTAX_ERROR: "I can help you with AWS deployment.",
        # REMOVED_SYNTAX_ERROR: "Hello! How can I assist you today?",  # Forgets previous context
        # REMOVED_SYNTAX_ERROR: "I"m an AI assistant."  # Generic response ignoring conversation
        
        # REMOVED_SYNTAX_ERROR: response_index = 0

# REMOVED_SYNTAX_ERROR: async def mock_ask_llm(prompt, *args, **kwargs):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: nonlocal response_index
    # REMOVED_SYNTAX_ERROR: if response_index < len(responses):
        # REMOVED_SYNTAX_ERROR: result = responses[response_index]
        # REMOVED_SYNTAX_ERROR: response_index += 1
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return result
        # REMOVED_SYNTAX_ERROR: return "I can help you with that."

        # REMOVED_SYNTAX_ERROR: mock_llm_manager.ask_llm = AsyncMock(side_effect=mock_ask_llm)

        # REMOVED_SYNTAX_ERROR: mock_tool_dispatcher = MagicNone  # TODO: Use real service instance
        # REMOVED_SYNTAX_ERROR: mock_tool_dispatcher.get_available_tools = MagicMock(return_value=["chat"])

        # REMOVED_SYNTAX_ERROR: supervisor = SupervisorAgent( )
        # REMOVED_SYNTAX_ERROR: db_session=mock_db_session,
        # REMOVED_SYNTAX_ERROR: llm_manager=mock_llm_manager,
        # REMOVED_SYNTAX_ERROR: tool_dispatcher=mock_tool_dispatcher,
        # REMOVED_SYNTAX_ERROR: websocket_manager=mock_websocket_manager
        

        # REMOVED_SYNTAX_ERROR: agent_service = AgentService(supervisor)

        # Send first message about AWS
        # REMOVED_SYNTAX_ERROR: message1 = { )
        # REMOVED_SYNTAX_ERROR: "type": "user_message",
        # REMOVED_SYNTAX_ERROR: "payload": { )
        # REMOVED_SYNTAX_ERROR: "content": "I need help setting up AWS EC2 instances for production.",
        # REMOVED_SYNTAX_ERROR: "thread_id": "context_test_thread"
        
        

        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.services.agent_service_core.manager', mock_websocket_manager):
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
                # REMOVED_SYNTAX_ERROR: await agent_service.handle_websocket_message( )
                # REMOVED_SYNTAX_ERROR: user_id="test_context_user",
                # REMOVED_SYNTAX_ERROR: message=message1,
                # REMOVED_SYNTAX_ERROR: db_session=mock_db_session
                

                # Send follow-up question that should reference previous context
                # REMOVED_SYNTAX_ERROR: message2 = { )
                # REMOVED_SYNTAX_ERROR: "type": "user_message",
                # REMOVED_SYNTAX_ERROR: "payload": { )
                # REMOVED_SYNTAX_ERROR: "content": "What about security groups for those instances?",
                # REMOVED_SYNTAX_ERROR: "thread_id": "context_test_thread"  # Same thread
                
                

                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.services.agent_service_core.manager', mock_websocket_manager):
                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
                        # REMOVED_SYNTAX_ERROR: await agent_service.handle_websocket_message( )
                        # REMOVED_SYNTAX_ERROR: user_id="test_context_user",
                        # REMOVED_SYNTAX_ERROR: message=message2,
                        # REMOVED_SYNTAX_ERROR: db_session=mock_db_session
                        

                        # Validate context retention
                        # REMOVED_SYNTAX_ERROR: assert len(actual_responses) >= 2, "Should receive responses to both messages"

                        # Check if second response acknowledges the EC2/AWS context
                        # REMOVED_SYNTAX_ERROR: second_response_content = ""
                        # REMOVED_SYNTAX_ERROR: response_count = 0
                        # REMOVED_SYNTAX_ERROR: for response in actual_responses:
                            # REMOVED_SYNTAX_ERROR: if "message" in response and response["message"].get("type") == "agent_response":
                                # REMOVED_SYNTAX_ERROR: response_count += 1
                                # REMOVED_SYNTAX_ERROR: if response_count == 2:  # Second AI response
                                # REMOVED_SYNTAX_ERROR: second_response_content = response["message"].get("payload", {}).get("content", "")
                                # REMOVED_SYNTAX_ERROR: break

                                # This should FAIL - second response should reference AWS/EC2 context
                                # REMOVED_SYNTAX_ERROR: if second_response_content:
                                    # REMOVED_SYNTAX_ERROR: context_indicators = ["ec2", "aws", "instances", "security group", "security"]
                                    # REMOVED_SYNTAX_ERROR: maintains_context = any(indicator in second_response_content.lower() for indicator in context_indicators)

                                    # REMOVED_SYNTAX_ERROR: assert maintains_context, ( )
                                    # REMOVED_SYNTAX_ERROR: "formatted_string"
                                    
                                    # REMOVED_SYNTAX_ERROR: else:
                                        # REMOVED_SYNTAX_ERROR: assert False, "No second response found to validate context retention"

                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_chat_error_message_quality(self):
                                            # REMOVED_SYNTAX_ERROR: '''
                                            # REMOVED_SYNTAX_ERROR: Test that error messages in chat are helpful and actionable.

                                            # REMOVED_SYNTAX_ERROR: This validates error handling quality in chat interactions.
                                            # REMOVED_SYNTAX_ERROR: '''
                                            # REMOVED_SYNTAX_ERROR: pass
                                            # REMOVED_SYNTAX_ERROR: actual_responses = []

# REMOVED_SYNTAX_ERROR: async def mock_send_error(user_id: str, error: str):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: actual_responses.append({"user_id": user_id, "error": error, "type": "error"})

# REMOVED_SYNTAX_ERROR: async def mock_send_message(user_id: str, message: Dict[str, Any]):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: actual_responses.append({"user_id": user_id, "message": message})

    # Setup mocks
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager = MagicNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager.send_message = AsyncMock(side_effect=mock_send_message)
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager.send_error = AsyncMock(side_effect=mock_send_error)
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager.send_to_user = AsyncMock(side_effect=mock_send_message)

    # REMOVED_SYNTAX_ERROR: mock_broadcasting = MagicNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_broadcasting.join_room = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_broadcasting.leave_room = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager.broadcasting = mock_broadcasting

    # REMOVED_SYNTAX_ERROR: mock_db_session = AsyncNone  # TODO: Use real service instance

    # REMOVED_SYNTAX_ERROR: supervisor = SupervisorAgent( )
    # REMOVED_SYNTAX_ERROR: db_session=mock_db_session,
    # REMOVED_SYNTAX_ERROR: llm_manager=AsyncNone  # TODO: Use real service instance,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=MagicNone  # TODO: Use real service instance,
    # REMOVED_SYNTAX_ERROR: websocket_manager=mock_websocket_manager
    

    # REMOVED_SYNTAX_ERROR: agent_service = AgentService(supervisor)

    # Send malformed message to trigger error
    # REMOVED_SYNTAX_ERROR: malformed_message = { )
    # REMOVED_SYNTAX_ERROR: "invalid_structure": True,
    # Missing "type" field which is required
    

    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.services.agent_service_core.manager', mock_websocket_manager):
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
            # REMOVED_SYNTAX_ERROR: await agent_service.handle_websocket_message( )
            # REMOVED_SYNTAX_ERROR: user_id="test_error_user",
            # REMOVED_SYNTAX_ERROR: message=malformed_message,
            # REMOVED_SYNTAX_ERROR: db_session=mock_db_session
            

            # Validate error message quality
            # REMOVED_SYNTAX_ERROR: assert len(actual_responses) > 0, "Should receive error response"

            # REMOVED_SYNTAX_ERROR: error_found = False
            # REMOVED_SYNTAX_ERROR: error_message = ""

            # REMOVED_SYNTAX_ERROR: for response in actual_responses:
                # REMOVED_SYNTAX_ERROR: if "error" in response:
                    # REMOVED_SYNTAX_ERROR: error_message = response["error"]
                    # REMOVED_SYNTAX_ERROR: error_found = True
                    # REMOVED_SYNTAX_ERROR: break

                    # This should validate that error messages are helpful
                    # REMOVED_SYNTAX_ERROR: if error_found:
                        # Check that error message is helpful, not just generic
                        # REMOVED_SYNTAX_ERROR: assert "type" in error_message or "required" in error_message, ( )
                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                        
                        # Check it's not too generic
                        # REMOVED_SYNTAX_ERROR: assert error_message != "Internal server error", ( )
                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                        
                        # REMOVED_SYNTAX_ERROR: else:
                            # REMOVED_SYNTAX_ERROR: assert False, "No error message found for malformed input"


                            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v"])