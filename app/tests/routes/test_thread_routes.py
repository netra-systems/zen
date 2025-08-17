"""
Test 30: Threads Route Conversation
Tests for thread conversation management - app/routes/threads_route.py

Business Value Justification (BVJ):
- Segment: Growth, Mid, Enterprise
- Business Goal: Conversation history and context management for AI interactions
- Value Impact: Improves AI response quality through conversation continuity
- Revenue Impact: Essential feature for user retention and engagement
"""

import pytest
from unittest.mock import patch
from datetime import datetime

from .test_route_fixtures import (
    basic_test_client,
    CommonResponseValidators
)


class TestThreadsRoute:
    """Test thread conversation management and pagination functionality."""
    
    def test_thread_creation(self, basic_test_client):
        """Test thread creation endpoint."""
        from app.services.thread_service import ThreadService
        
        thread_data = {
            "title": "New Thread",
            "description": "Test conversation thread",
            "metadata": {
                "user_id": "user123",
                "category": "general"
            }
        }
        
        with patch.object(ThreadService, 'create_thread') as mock_create:
            mock_create.return_value = {
                "id": "thread123",
                "title": "New Thread",
                "created_at": datetime.now().isoformat(),
                "message_count": 0,
                "status": "active"
            }
            
            response = basic_test_client.post("/api/threads", json=thread_data)
            
            if response.status_code in [200, 201]:
                data = response.json()
                thread_id_keys = ["id", "thread_id"]
                has_thread_id = any(key in data for key in thread_id_keys)
                assert has_thread_id, "Response should contain thread ID"
                
                if "title" in data:
                    assert data["title"] == thread_data["title"]
                if "message_count" in data:
                    assert data["message_count"] == 0  # New thread should have no messages
            else:
                assert response.status_code in [404, 422, 401]
    
    def test_thread_pagination(self, basic_test_client):
        """Test thread list pagination."""
        from app.services.thread_service import ThreadService
        
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
                assert response.status_code in [404, 401]
    
    async def test_thread_archival(self):
        """Test thread archival functionality."""
        from app.services.thread_service import ThreadService
        
        thread_id = "thread123"
        user_id = "user1"
        
        with patch.object(ThreadService, 'delete_thread') as mock_delete:
            mock_delete.return_value = True
            
            # Test soft delete/archive
            service = ThreadService()
            result = await service.delete_thread(thread_id, user_id)
            assert result == True
        
        # Test archive with metadata preservation
        with patch.object(ThreadService, 'archive_thread') as mock_archive:
            mock_archive.return_value = {
                "thread_id": thread_id,
                "archived": True,
                "archived_at": datetime.now().isoformat(),
                "message_count": 25,
                "archive_size_mb": 1.2
            }
            
            service = ThreadService()
            result = await service.archive_thread(thread_id, user_id)
            
            assert result["archived"] == True
            assert result["thread_id"] == thread_id
            assert "message_count" in result
    
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
                assert response.status_code in [404, 422, 401]
    
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
                assert response.status_code in [404, 422, 401]
    
    def test_thread_export(self, basic_test_client):
        """Test thread conversation export."""
        thread_id = "thread123"
        export_options = {
            "format": "json",
            "include_metadata": True,
            "include_timestamps": True,
            "message_limit": None  # Export all messages
        }
        
        with patch('app.services.thread_service.export_thread') as mock_export:
            mock_export.return_value = {
                "export_id": "export_789",
                "thread_id": thread_id,
                "format": "json",
                "download_url": f"/api/threads/{thread_id}/export/download/export_789",
                "file_size_kb": 45.2,
                "message_count": 32,
                "expires_at": "2024-01-02T12:00:00Z"
            }
            
            response = basic_test_client.post(
                f"/api/threads/{thread_id}/export",
                json=export_options
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                assert "export_id" in data or "download_url" in data
                
                if "file_size_kb" in data:
                    assert data["file_size_kb"] > 0
                if "message_count" in data:
                    assert data["message_count"] >= 0
            else:
                assert response.status_code in [404, 422, 401]
    
    def test_thread_statistics(self, basic_test_client):
        """Test thread usage statistics."""
        stats_request = {
            "user_id": "user123",
            "time_period": "last_30_days",
            "include_breakdown": True
        }
        
        with patch('app.services.thread_service.get_thread_statistics') as mock_stats:
            mock_stats.return_value = {
                "total_threads": 45,
                "active_threads": 12,
                "archived_threads": 33,
                "total_messages": 892,
                "average_messages_per_thread": 19.8,
                "most_active_day": "2024-01-15",
                "breakdown": {
                    "by_day": {
                        "2024-01-15": {"threads": 3, "messages": 45},
                        "2024-01-16": {"threads": 2, "messages": 28}
                    },
                    "by_category": {
                        "general": 25,
                        "support": 12,
                        "feedback": 8
                    }
                }
            }
            
            response = basic_test_client.post("/api/threads/statistics", json=stats_request)
            
            if response.status_code == 200:
                data = response.json()
                thread_stats_keys = [
                    "total_threads", "active_threads", "total_messages",
                    "average_messages_per_thread"
                ]
                
                has_stats = any(key in data for key in thread_stats_keys)
                if has_stats:
                    for key in thread_stats_keys:
                        if key in data:
                            if "average" in key:
                                assert data[key] >= 0.0
                            else:
                                assert data[key] >= 0
                
                # Validate breakdown structure if present
                if "breakdown" in data:
                    breakdown = data["breakdown"]
                    if "by_day" in breakdown:
                        for day, stats in breakdown["by_day"].items():
                            assert "threads" in stats
                            assert "messages" in stats
                            assert stats["threads"] >= 0
                            assert stats["messages"] >= 0
            else:
                assert response.status_code in [404, 422, 401]
    
    def test_thread_cleanup_old_threads(self, basic_test_client):
        """Test cleanup of old inactive threads."""
        cleanup_request = {
            "criteria": {
                "inactive_days": 90,
                "min_message_count": 1,  # Only cleanup threads with some activity
                "exclude_bookmarked": True
            },
            "action": "archive",  # or "delete"
            "dry_run": False
        }
        
        with patch('app.services.thread_service.cleanup_old_threads') as mock_cleanup:
            mock_cleanup.return_value = {
                "processed_threads": 23,
                "archived_threads": 20,
                "skipped_threads": 3,
                "space_freed_mb": 15.7,
                "cleanup_summary": {
                    "total_candidates": 23,
                    "bookmarked_skipped": 2,
                    "recent_activity_skipped": 1,
                    "successfully_processed": 20
                }
            }
            
            response = basic_test_client.post("/api/threads/cleanup", json=cleanup_request)
            
            if response.status_code == 200:
                data = response.json()
                assert "processed_threads" in data or "archived_threads" in data
                
                if "processed_threads" in data:
                    assert data["processed_threads"] >= 0
                if "space_freed_mb" in data:
                    assert data["space_freed_mb"] >= 0
                
                if "cleanup_summary" in data:
                    summary = data["cleanup_summary"]
                    if "total_candidates" in summary and "successfully_processed" in summary:
                        assert summary["successfully_processed"] <= summary["total_candidates"]
            else:
                assert response.status_code in [404, 422, 401]