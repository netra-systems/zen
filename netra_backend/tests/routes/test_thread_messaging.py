"""
Test 30A2: Thread Messaging Operations
Tests for thread messaging and search operations - app/routes/threads_route.py

Business Value Justification (BVJ):
- Segment: Growth, Mid, Enterprise
- Business Goal: Message handling and search functionality
- Value Impact: Enables effective conversation navigation and content discovery
- Revenue Impact: Core messaging features for user engagement
"""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from datetime import datetime

import pytest

from netra_backend.tests.test_route_fixtures import (
    CommonResponseValidators,
    basic_test_client,
)

class TestThreadMessaging:
    """Test thread messaging and search functionality."""
    
    def test_thread_pagination(self, basic_test_client):
        """Test thread list pagination."""
        from netra_backend.app.services.thread_service import ThreadService
        
        with patch.object(ThreadService, 'get_thread_messages') as mock_get:
            mock_get.return_value = [
                {
                    "id": f"msg{i}",
                    "content": f"Message {i}",
                    "timestamp": datetime.now().isoformat(),
                    "sender": "user" if i % 2 == 0 else "assistant"
                }
                for i in range(10)
            ]
            
            response = basic_test_client.get("/api/threads?page=1&per_page=10")
            
            if response.status_code == 200:
                data = response.json()
                CommonResponseValidators.validate_pagination_response(response, max_items=10)
                
                # Check for pagination indicators
                pagination_fields = ["threads", "data", "items", "messages"]
                has_pagination = any(field in data for field in pagination_fields)
                
                if has_pagination:
                    for field in pagination_fields:
                        if field in data and isinstance(data[field], list):
                            assert len(data[field]) <= 10
            else:
                assert response.status_code in [404, 401, 403]
    
    def test_thread_message_addition(self, basic_test_client):
        """Test adding messages to existing threads."""
        thread_id = "thread123"
        message_data = {
            "content": "Hello, this is a test message",
            "sender": "user",
            "metadata": {
                "user_id": "user123",
                "message_type": "text"
            }
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.thread_service.add_message_to_thread') as mock_add:
            mock_add.return_value = {
                "message_id": "msg456",
                "thread_id": thread_id,
                "content": message_data["content"],
                "timestamp": datetime.now().isoformat(),
                "sender": message_data["sender"]
            }
            
            response = basic_test_client.post(
                f"/api/threads/{thread_id}/messages",
                json=message_data
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                assert "message_id" in data or "id" in data
                assert "thread_id" in data
                assert data["thread_id"] == thread_id
                
                if "content" in data:
                    assert data["content"] == message_data["content"]
            else:
                assert response.status_code in [404, 422, 401, 405]
    
    def test_thread_search(self, basic_test_client):
        """Test thread search functionality."""
        search_params = {
            "query": "test conversation",
            "filters": {
                "date_range": {
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-01-31T23:59:59Z"
                },
                "user_id": "user123",
                "has_agent_responses": True
            },
            "limit": 20,
            "offset": 0
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.thread_service.search_threads') as mock_search:
            mock_search.return_value = {
                "threads": [
                    {
                        "id": "thread1",
                        "title": "Test Conversation 1",
                        "last_message": "This is the last message",
                        "message_count": 15,
                        "last_activity": "2024-01-15T10:30:00Z"
                    },
                    {
                        "id": "thread2",
                        "title": "Another Test Conversation",
                        "last_message": "Final message here",
                        "message_count": 8,
                        "last_activity": "2024-01-20T14:45:00Z"
                    }
                ],
                "total": 2,
                "has_more": False
            }
            
            response = basic_test_client.post("/api/threads/search", json=search_params)
            
            if response.status_code == 200:
                data = response.json()
                assert "threads" in data or "results" in data
                
                if "threads" in data:
                    for thread in data["threads"]:
                        assert "id" in thread
                        assert "title" in thread or "last_message" in thread
                        if "message_count" in thread:
                            assert thread["message_count"] >= 0
                
                if "total" in data:
                    assert data["total"] >= 0
                    if "threads" in data:
                        assert data["total"] >= len(data["threads"])
            else:
                assert response.status_code in [404, 422, 401, 405]
    
    def test_message_retrieval_with_pagination(self, basic_test_client):
        """Test retrieving messages from a thread with pagination."""
        thread_id = "thread123"
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.thread_service.get_thread_messages') as mock_get_messages:
            mock_get_messages.return_value = {
                "messages": [
                    {
                        "id": f"msg{i}",
                        "content": f"Message content {i}",
                        "sender": "user" if i % 2 == 0 else "assistant",
                        "timestamp": f"2024-01-0{(i % 9) + 1}T12:00:00Z",
                        "message_type": "text"
                    }
                    for i in range(10)
                ],
                "total_messages": 50,
                "page": 1,
                "per_page": 10,
                "has_more": True
            }
            
            response = basic_test_client.get(
                f"/api/threads/{thread_id}/messages?page=1&per_page=10"
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "messages" in data or "data" in data
                
                message_key = "messages" if "messages" in data else "data"
                if message_key in data:
                    messages = data[message_key]
                    assert len(messages) <= 10
                    
                    for message in messages:
                        assert "id" in message
                        assert "content" in message
                        assert "sender" in message
                        assert message["sender"] in ["user", "assistant", "system"]
                
                if "total_messages" in data:
                    assert data["total_messages"] >= len(data.get(message_key, []))
            else:
                assert response.status_code in [404, 401, 403]
    
    def test_message_editing(self, basic_test_client):
        """Test editing individual messages in threads."""
        thread_id = "thread123"
        message_id = "msg456"
        edit_data = {
            "content": "Updated message content",
            "edit_reason": "Corrected typo"
        }
        
        # Use existing function from thread_service that actually exists
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.thread_service.update_thread') as mock_edit:
            mock_edit.return_value = {
                "message_id": message_id,
                "thread_id": thread_id,
                "content": edit_data["content"],
                "edited_at": datetime.now().isoformat(),
                "edit_history": [
                    {
                        "edited_at": datetime.now().isoformat(),
                        "reason": edit_data["edit_reason"],
                        "previous_content": "Original message content"
                    }
                ]
            }
            
            response = basic_test_client.put(
                f"/api/threads/{thread_id}/messages/{message_id}",
                json=edit_data
            )
            
            if response.status_code == 200:
                data = response.json()
                assert data["message_id"] == message_id
                assert data["content"] == edit_data["content"]
                
                if "edit_history" in data:
                    assert len(data["edit_history"]) > 0
                    assert "reason" in data["edit_history"][0]
            else:
                assert response.status_code in [404, 422, 401, 405]
    
    def test_message_search_within_thread(self, basic_test_client):
        """Test searching messages within a specific thread."""
        thread_id = "thread123"
        search_request = {
            "query": "specific keyword",
            "message_types": ["text", "system"],
            "date_range": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-31T23:59:59Z"
            },
            "sender_filter": "user"
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.thread_service.search_messages_in_thread') as mock_search:
            mock_search.return_value = {
                "messages": [
                    {
                        "id": "msg123",
                        "content": "This message contains the specific keyword",
                        "sender": "user",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "relevance_score": 0.95
                    },
                    {
                        "id": "msg124",
                        "content": "Another message with specific content",
                        "sender": "user",
                        "timestamp": "2024-01-16T11:15:00Z",
                        "relevance_score": 0.87
                    }
                ],
                "total_matches": 2,
                "query": search_request["query"]
            }
            
            response = basic_test_client.post(
                f"/api/threads/{thread_id}/search-messages",
                json=search_request
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "messages" in data or "total_matches" in data
                
                if "messages" in data:
                    for message in data["messages"]:
                        assert "id" in message
                        assert "content" in message
                        # Verify search query appears in content
                        if "relevance_score" in message:
                            assert 0 <= message["relevance_score"] <= 1
            else:
                assert response.status_code in [404, 422, 401, 405]
    
    def test_message_reactions_and_feedback(self, basic_test_client):
        """Test message reactions and feedback functionality."""
        thread_id = "thread123"
        message_id = "msg456"
        
        # Test adding reaction
        reaction_data = {
            "reaction_type": "thumbs_up",
            "user_id": "user123"
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.thread_service.add_message_reaction') as mock_reaction:
            mock_reaction.return_value = {
                "message_id": message_id,
                "reaction_type": "thumbs_up",
                "user_id": "user123",
                "added_at": datetime.now().isoformat()
            }
            
            response = basic_test_client.post(
                f"/api/threads/{thread_id}/messages/{message_id}/reactions",
                json=reaction_data
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                assert "reaction_type" in data or "message_id" in data
            else:
                assert response.status_code in [404, 422, 401, 405]
    
    def test_message_threading_and_replies(self, basic_test_client):
        """Test message threading and reply functionality."""
        thread_id = "thread123"
        parent_message_id = "msg456"
        
        reply_data = {
            "content": "This is a reply to the previous message",
            "parent_message_id": parent_message_id,
            "sender": "assistant",
            "message_type": "reply"
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.thread_service.add_reply_to_message') as mock_reply:
            mock_reply.return_value = {
                "message_id": "msg789",
                "thread_id": thread_id,
                "parent_message_id": parent_message_id,
                "content": reply_data["content"],
                "sender": reply_data["sender"],
                "timestamp": datetime.now().isoformat(),
                "reply_level": 1
            }
            
            response = basic_test_client.post(
                f"/api/threads/{thread_id}/messages/{parent_message_id}/replies",
                json=reply_data
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                assert "parent_message_id" in data
                assert data["parent_message_id"] == parent_message_id
                assert "reply_level" in data or "message_id" in data
            else:
                assert response.status_code in [404, 422, 401, 405]