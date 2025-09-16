"""Frontend Data Mocks for Type Safety Testing.

Provides standardized mock data representing typical frontend payloads
for testing type consistency across the full stack.
"""

from datetime import datetime
from typing import Any, Dict, List

class FrontendDataMocks:
    """Mock data representing typical frontend payloads."""
    
    @staticmethod
    def start_agent_payload() -> Dict[str, Any]:
        """Frontend StartAgent payload structure."""
        return {
            "type": "start_agent",
            "payload": {
                "query": "Analyze system performance",
                "user_id": "user123",
                "thread_id": "thread456",
                "context": {
                    "session_id": "session789",
                    "metadata": {"source": "chat_ui"}
                }
            }
        }
    
    @staticmethod
    def user_message_payload() -> Dict[str, Any]:
        """Frontend UserMessage payload structure."""
        return {
            "type": "user_message",
            "payload": {
                "content": "What are the optimization opportunities?",
                "thread_id": "thread456",
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "client_id": "web_client_1"
                }
            }
        }
    
    @staticmethod
    def tool_call_payload() -> Dict[str, Any]:
        """Frontend tool call structure."""
        return {
            "tool_name": "log_fetcher",
            "tool_args": {
                "start_time": "2025-01-01T00:00:00Z",
                "end_time": "2025-01-02T00:00:00Z",
                "filters": {"level": "error"}
            },
            "run_id": "run123"
        }
    
    @staticmethod
    def create_thread_operation() -> Dict[str, Any]:
        """Frontend create thread operation."""
        return {
            "type": "create_thread",
            "payload": {
                "title": "New Analysis Thread",
                "metadata": {"tags": ["performance", "optimization"]}
            }
        }
    
    @staticmethod
    def rename_thread_operation() -> Dict[str, Any]:
        """Frontend rename thread operation."""
        return {
            "type": "rename_thread",
            "payload": {
                "thread_id": "thread456",
                "new_title": "Performance Analysis Q1 2025"
            }
        }
    
    @staticmethod
    def delete_thread_operation() -> Dict[str, Any]:
        """Frontend delete thread operation."""
        return {
            "type": "delete_thread",
            "payload": {
                "thread_id": "thread456"
            }
        }
    
    @staticmethod
    def switch_thread_operation() -> Dict[str, Any]:
        """Frontend switch thread operation."""
        return {
            "type": "switch_thread",
            "payload": {
                "thread_id": "thread789"
            }
        }
    
    @staticmethod
    def thread_operations() -> List[Dict[str, Any]]:
        """All frontend thread operation payloads."""
        return [
            FrontendDataMocks.create_thread_operation(),
            FrontendDataMocks.rename_thread_operation(),
            FrontendDataMocks.delete_thread_operation(),
            FrontendDataMocks.switch_thread_operation()
        ]
    
    @staticmethod
    def ping_message() -> Dict[str, Any]:
        """Frontend ping WebSocket message."""
        return {
            "type": "ping",
            "payload": {}
        }
    
    @staticmethod
    def list_threads_message() -> Dict[str, Any]:
        """Frontend list threads message."""
        return {
            "type": "list_threads",
            "payload": {}
        }
    
    @staticmethod
    def stop_agent_message() -> Dict[str, Any]:
        """Frontend stop agent message."""
        return {
            "type": "stop_agent",
            "payload": {
                "run_id": "run123"
            }
        }
    
    @staticmethod
    def websocket_messages() -> List[Dict[str, Any]]:
        """Various WebSocket message formats from frontend."""
        return [
            FrontendDataMocks.ping_message(),
            FrontendDataMocks.list_threads_message(),
            FrontendDataMocks.stop_agent_message()
        ]
    
    @staticmethod
    def minimal_start_agent_payload() -> Dict[str, Any]:
        """Minimal StartAgent payload for testing optional fields."""
        return {
            "query": "Test query",
            "user_id": "user123"
        }
    
    @staticmethod
    def full_start_agent_payload() -> Dict[str, Any]:
        """Full StartAgent payload with all fields."""
        return {
            "query": "Test query",
            "user_id": "user123",
            "thread_id": "thread456",
            "context": {"key": "value"}
        }
    
    @staticmethod
    def nested_request_data() -> Dict[str, Any]:
        """Complex nested request structure."""
        return {
            "id": "req123",
            "user_id": "user123",
            "query": "Analyze workload",
            "workloads": [
                {
                    "run_id": "run123",
                    "query": "sub-query",
                    "data_source": {
                        "source_table": "logs",
                        "filters": {"level": "error"}
                    },
                    "time_range": {
                        "start_time": "2025-01-01T00:00:00Z",
                        "end_time": "2025-01-02T00:00:00Z"
                    }
                }
            ]
        }
    
    @staticmethod
    def complex_websocket_payload() -> Dict[str, Any]:
        """Complex deeply nested WebSocket payload."""
        return {
            "type": "start_agent",
            "payload": {
                "query": "Complex analysis",
                "user_id": "user123",
                "context": {
                    "session": {
                        "id": "session123",
                        "metadata": {
                            "client": {
                                "name": "web",
                                "version": "1.0.0"
                            }
                        }
                    }
                }
            }
        }
    
    @staticmethod
    def workloads_array_data() -> List[Dict[str, Any]]:
        """Array of workload data for testing."""
        return [
            {
                "run_id": f"run{i}",
                "query": f"query{i}",
                "data_source": {
                    "source_table": "logs",
                    "filters": None
                },
                "time_range": {
                    "start_time": "2025-01-01T00:00:00Z",
                    "end_time": "2025-01-02T00:00:00Z"
                }
            }
            for i in range(3)
        ]

class EnumValueMocks:
    """Mock enum values for testing consistency."""
    
    @staticmethod
    def tool_statuses() -> List[str]:
        """Frontend tool status values."""
        return ["success", "error", "partial_success", "in_progress", "complete"]
    
    @staticmethod
    def message_types() -> List[str]:
        """Frontend message type values."""
        return ["user", "agent", "system", "error", "tool"]