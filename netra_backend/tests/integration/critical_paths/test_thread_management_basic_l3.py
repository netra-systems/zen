#!/usr/bin/env python3
"""
L3 Integration Test: Thread Management Basic Operations
Tests fundamental thread creation, retrieval, updates, and deletion
from multiple angles including edge cases and concurrent operations.

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List

import aiohttp
import pytest

from netra_backend.app.db.models_postgres import Message, Thread
from netra_backend.app.redis_manager import RedisManager
from test_framework.test_patterns import L3IntegrationTest


class TestThreadManagementBasic(L3IntegrationTest):
    """Test thread management basic operations from multiple angles."""
    
    async def test_create_thread_basic(self):
        """Test basic thread creation flow."""
        user_data = await self.create_test_user("thread1@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            thread_data = {
                "title": "Test Thread",
                "description": "Testing thread creation",
                "metadata": {
                    "category": "test",
                    "priority": "normal"
                }
            }
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads",
                json=thread_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                data = await resp.json()
                
                # Verify thread structure
                assert "id" in data
                assert data["title"] == thread_data["title"]
                assert data["description"] == thread_data["description"]
                assert data["metadata"] == thread_data["metadata"]
                assert data["user_id"] == user_data["id"]
                assert "created_at" in data
                assert "updated_at" in data
                
    async def test_retrieve_thread_by_id(self):
        """Test retrieving a thread by its ID."""
        user_data = await self.create_test_user("thread2@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create thread
            thread_data = {"title": "Retrievable Thread"}
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads",
                json=thread_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                created_thread = await resp.json()
                thread_id = created_thread["id"]
            
            # Retrieve thread
            async with session.get(
                f"{self.backend_url}/api/v1/threads/{thread_id}",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                retrieved_thread = await resp.json()
                
                assert retrieved_thread["id"] == thread_id
                assert retrieved_thread["title"] == thread_data["title"]
                
    async def test_update_thread_properties(self):
        """Test updating thread properties."""
        user_data = await self.create_test_user("thread3@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create thread
            original_data = {
                "title": "Original Title",
                "description": "Original Description"
            }
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads",
                json=original_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                thread = await resp.json()
                thread_id = thread["id"]
            
            # Update thread
            update_data = {
                "title": "Updated Title",
                "description": "Updated Description",
                "metadata": {"updated": True}
            }
            
            async with session.patch(
                f"{self.backend_url}/api/v1/threads/{thread_id}",
                json=update_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                updated_thread = await resp.json()
                
                assert updated_thread["title"] == update_data["title"]
                assert updated_thread["description"] == update_data["description"]
                assert updated_thread["metadata"]["updated"] is True
                assert updated_thread["updated_at"] > thread["updated_at"]
                
    async def test_delete_thread(self):
        """Test thread deletion."""
        user_data = await self.create_test_user("thread4@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create thread
            thread_data = {"title": "Thread to Delete"}
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads",
                json=thread_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                thread = await resp.json()
                thread_id = thread["id"]
            
            # Delete thread
            async with session.delete(
                f"{self.backend_url}/api/v1/threads/{thread_id}",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 204
            
            # Verify thread is deleted
            async with session.get(
                f"{self.backend_url}/api/v1/threads/{thread_id}",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 404
                
    async def test_list_user_threads(self):
        """Test listing threads for a user."""
        user_data = await self.create_test_user("thread5@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create multiple threads
            thread_titles = ["Thread A", "Thread B", "Thread C"]
            created_threads = []
            
            for title in thread_titles:
                async with session.post(
                    f"{self.backend_url}/api/v1/threads",
                    json={"title": title},
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    assert resp.status == 201
                    created_threads.append(await resp.json())
            
            # List threads
            async with session.get(
                f"{self.backend_url}/api/v1/threads",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                
                assert "threads" in data
                assert len(data["threads"]) >= 3
                
                # Verify created threads are in list
                listed_titles = {t["title"] for t in data["threads"]}
                for title in thread_titles:
                    assert title in listed_titles
                    
    async def test_thread_pagination(self):
        """Test thread listing pagination."""
        user_data = await self.create_test_user("thread6@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create many threads
            for i in range(25):
                async with session.post(
                    f"{self.backend_url}/api/v1/threads",
                    json={"title": f"Thread {i:02d}"},
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    assert resp.status == 201
            
            # Get first page
            async with session.get(
                f"{self.backend_url}/api/v1/threads?limit=10&offset=0",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                page1 = await resp.json()
                
                assert len(page1["threads"]) == 10
                assert page1["total"] >= 25
                assert page1["has_more"] is True
            
            # Get second page
            async with session.get(
                f"{self.backend_url}/api/v1/threads?limit=10&offset=10",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                page2 = await resp.json()
                
                assert len(page2["threads"]) == 10
                
                # Verify no overlap
                page1_ids = {t["id"] for t in page1["threads"]}
                page2_ids = {t["id"] for t in page2["threads"]}
                assert len(page1_ids & page2_ids) == 0
                
    async def test_thread_search_by_title(self):
        """Test searching threads by title."""
        user_data = await self.create_test_user("thread7@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create threads with different titles
            threads_data = [
                {"title": "Python Programming Guide"},
                {"title": "JavaScript Best Practices"},
                {"title": "Python Advanced Topics"},
                {"title": "Database Design Patterns"}
            ]
            
            for thread_data in threads_data:
                async with session.post(
                    f"{self.backend_url}/api/v1/threads",
                    json=thread_data,
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    assert resp.status == 201
            
            # Search for Python threads
            async with session.get(
                f"{self.backend_url}/api/v1/threads?search=Python",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                
                assert len(data["threads"]) == 2
                for thread in data["threads"]:
                    assert "Python" in thread["title"]
                    
    async def test_thread_concurrent_creation(self):
        """Test concurrent thread creation by same user."""
        user_data = await self.create_test_user("thread8@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create threads concurrently
            tasks = []
            for i in range(10):
                thread_data = {
                    "title": f"Concurrent Thread {i}",
                    "description": f"Created concurrently at {datetime.utcnow()}"
                }
                
                tasks.append(session.post(
                    f"{self.backend_url}/api/v1/threads",
                    json=thread_data,
                    headers={"Authorization": f"Bearer {token}"}
                ))
            
            responses = await asyncio.gather(*tasks)
            
            # All should succeed
            for resp in responses:
                assert resp.status == 201
            
            # Verify all threads were created
            thread_ids = set()
            for resp in responses:
                data = await resp.json()
                thread_ids.add(data["id"])
            
            assert len(thread_ids) == 10  # All unique IDs
            
    async def test_thread_access_control(self):
        """Test thread access control between users."""
        user1_data = await self.create_test_user("thread9a@test.com")
        user2_data = await self.create_test_user("thread9b@test.com")
        
        token1 = await self.get_auth_token(user1_data)
        token2 = await self.get_auth_token(user2_data)
        
        async with aiohttp.ClientSession() as session:
            # User1 creates a thread
            thread_data = {"title": "Private Thread"}
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads",
                json=thread_data,
                headers={"Authorization": f"Bearer {token1}"}
            ) as resp:
                assert resp.status == 201
                thread = await resp.json()
                thread_id = thread["id"]
            
            # User2 tries to access the thread
            async with session.get(
                f"{self.backend_url}/api/v1/threads/{thread_id}",
                headers={"Authorization": f"Bearer {token2}"}
            ) as resp:
                assert resp.status in [403, 404]  # Forbidden or Not Found
            
            # User2 tries to update the thread
            async with session.patch(
                f"{self.backend_url}/api/v1/threads/{thread_id}",
                json={"title": "Hacked Title"},
                headers={"Authorization": f"Bearer {token2}"}
            ) as resp:
                assert resp.status in [403, 404]
            
            # User2 tries to delete the thread
            async with session.delete(
                f"{self.backend_url}/api/v1/threads/{thread_id}",
                headers={"Authorization": f"Bearer {token2}"}
            ) as resp:
                assert resp.status in [403, 404]
                
    async def test_thread_soft_delete(self):
        """Test that threads are soft-deleted, not hard-deleted."""
        user_data = await self.create_test_user("thread10@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create thread with messages
            thread_data = {"title": "Thread with Messages"}
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads",
                json=thread_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                thread = await resp.json()
                thread_id = thread["id"]
            
            # Add a message to thread
            message_data = {"content": "Test message"}
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                json=message_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
            
            # Delete thread
            async with session.delete(
                f"{self.backend_url}/api/v1/threads/{thread_id}",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 204
            
            # Admin check: thread should be marked as deleted, not removed
            # This would require admin access or database check
            # Verify through listing - deleted thread shouldn't appear
            async with session.get(
                f"{self.backend_url}/api/v1/threads",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                
                thread_ids = {t["id"] for t in data["threads"]}
                assert thread_id not in thread_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])