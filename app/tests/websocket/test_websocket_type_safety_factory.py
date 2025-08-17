"""WebSocket Message Factory for Type Safety Testing.

Factory classes for creating test WebSocket messages with proper typing.
"""

import json
from typing import Dict, Any
from datetime import datetime


class WebSocketMessageFactory:
    """Factory for creating test WebSocket messages."""
    
    @staticmethod
    def create_client_message(msg_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a client-to-server message."""
        return {
            "type": msg_type,
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
            "message_id": f"msg_{msg_type}_{datetime.now().timestamp()}"
        }
    
    @staticmethod
    def create_server_message(msg_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a server-to-client message."""
        return {
            "type": msg_type,
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
            "message_id": f"srv_{msg_type}_{datetime.now().timestamp()}"
        }
    
    @staticmethod
    def create_agent_lifecycle_message(msg_type: str, run_id: str, **kwargs) -> Dict[str, Any]:
        """Create agent lifecycle message."""
        payload = {"run_id": run_id}
        payload.update(kwargs)
        return WebSocketMessageFactory.create_server_message(msg_type, payload)
    
    @staticmethod
    def create_tool_message(msg_type: str, tool_name: str, run_id: str, **kwargs) -> Dict[str, Any]:
        """Create tool-related message."""
        payload = {
            "tool_name": tool_name,
            "run_id": run_id
        }
        payload.update(kwargs)
        return WebSocketMessageFactory.create_server_message(msg_type, payload)
    
    @staticmethod
    def create_thread_message(msg_type: str, thread_id: str, **kwargs) -> Dict[str, Any]:
        """Create thread-related message."""
        payload = {"thread_id": thread_id}
        payload.update(kwargs)
        return WebSocketMessageFactory.create_client_message(msg_type, payload)
    
    @staticmethod
    def create_control_message(msg_type: str, **kwargs) -> Dict[str, Any]:
        """Create control message (ping, stop, etc)."""
        return WebSocketMessageFactory.create_client_message(msg_type, kwargs)
    
    @staticmethod
    def create_streaming_message(msg_type: str, content: str = None, **kwargs) -> Dict[str, Any]:
        """Create streaming message."""
        payload = kwargs
        if content is not None:
            payload["content"] = content
        return WebSocketMessageFactory.create_server_message(msg_type, payload)
    
    @staticmethod
    def create_error_message(message: str, code: str, severity: str = "medium", **kwargs) -> Dict[str, Any]:
        """Create error message."""
        payload = {
            "message": message,
            "code": code,
            "severity": severity
        }
        payload.update(kwargs)
        return WebSocketMessageFactory.create_server_message("error", payload)
    
    @staticmethod
    def create_connection_message(connection_id: str, session_id: str, server_version: str = "1.0.0") -> Dict[str, Any]:
        """Create connection established message."""
        payload = {
            "connection_id": connection_id,
            "session_id": session_id,
            "server_version": server_version
        }
        return WebSocketMessageFactory.create_server_message("connection_established", payload)


class WebSocketTestDataFactory:
    """Factory for creating test data sets."""
    
    @staticmethod
    def get_client_message_test_cases():
        """Get test cases for client messages."""
        return [
            {
                "type": "start_agent",
                "payload": {
                    "query": "Analyze performance metrics",
                    "user_id": "user123",
                    "thread_id": "thread456",
                    "context": {"session": "abc123"}
                }
            },
            {
                "type": "user_message",
                "payload": {
                    "content": "What are the key insights?",
                    "thread_id": "thread456",
                    "metadata": {"source": "chat_input"}
                }
            },
            {
                "type": "create_thread",
                "payload": {"title": "New Thread"}
            },
            {
                "type": "switch_thread",
                "payload": {"thread_id": "thread789"}
            },
            {
                "type": "delete_thread",
                "payload": {"thread_id": "thread456"}
            }
        ]
    
    @staticmethod
    def get_server_message_test_cases():
        """Get test cases for server messages."""
        return [
            {
                "type": "agent_started",
                "payload": {"run_id": "run123"}
            },
            {
                "type": "agent_completed",
                "payload": {
                    "run_id": "run123",
                    "result": {"status": "success", "data": {}}
                }
            },
            {
                "type": "tool_started",
                "payload": {
                    "tool_name": "log_analyzer",
                    "tool_args": {"level": "error"},
                    "run_id": "run123"
                }
            },
            {
                "type": "stream_chunk",
                "payload": {
                    "content": "Processing data",
                    "index": 0,
                    "finished": False,
                    "metadata": {"tokens": 3}
                }
            }
        ]
    
    @staticmethod
    def get_validation_error_test_cases():
        """Get test cases that should cause validation errors."""
        return [
            {
                "description": "Missing required field 'query'",
                "payload_class": "StartAgentPayload",
                "payload_data": {"user_id": "user123"}
            },
            {
                "description": "Invalid type for 'limit' (should be int)",
                "payload_class": "ThreadHistoryPayload",
                "payload_data": {
                    "thread_id": "thread123",
                    "limit": "not_an_int",
                    "offset": 0
                }
            },
            {
                "description": "Extra fields should be forbidden",
                "payload_class": "StartAgentPayload",
                "payload_data": {
                    "query": "Test",
                    "user_id": "user123",
                    "extra_field": "should_fail"
                }
            }
        ]
    
    @staticmethod
    def get_thread_operation_test_cases():
        """Get thread operation test cases."""
        return [
            ("create_thread", "CreateThreadPayload", {"title": "New Thread"}),
            ("switch_thread", "SwitchThreadPayload", {"thread_id": "thread789"}),
            ("delete_thread", "DeleteThreadPayload", {"thread_id": "thread456"}),
            ("rename_thread", "RenameThreadPayload", {
                "thread_id": "thread456",
                "new_title": "Updated Thread Title"
            }),
            ("list_threads", "ListThreadsPayload", {}),
        ]
    
    @staticmethod
    def get_agent_lifecycle_test_cases():
        """Get agent lifecycle test cases."""
        return [
            ("agent_started", "AgentStartedPayload", {"run_id": "run123"}),
            ("agent_completed", "AgentCompletedPayload", {
                "run_id": "run123",
                "result": {"status": "success", "data": {}}
            }),
            ("agent_error", "AgentErrorPayload", {
                "run_id": "run123",
                "message": "Processing failed",
                "code": "PROCESSING_ERROR"
            }),
        ]
    
    @staticmethod
    def get_tool_message_test_cases():
        """Get tool message test cases."""
        return [
            ("tool_started", "ToolStartedPayload", {
                "tool_name": "log_analyzer",
                "tool_args": {"level": "error"},
                "run_id": "run123"
            }),
            ("tool_completed", "ToolCompletedPayload", {
                "tool_name": "log_analyzer",
                "tool_output": {"logs": [], "count": 0},
                "run_id": "run123",
                "status": "success"
            }),
            ("tool_call", "ToolCallPayload", {
                "tool_name": "cost_analyzer",
                "tool_args": {"period": "monthly"},
                "run_id": "run123"
            }),
            ("tool_result", "ToolResultPayload", {
                "tool_name": "cost_analyzer",
                "result": {"total_cost": 1500.00},
                "run_id": "run123"
            }),
        ]
