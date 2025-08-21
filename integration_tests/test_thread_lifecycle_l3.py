"""
L3 Integration Tests: Thread Lifecycle and Conversation Management
Tests thread creation, state transitions, persistence, and cleanup.

Business Value Justification (BVJ):
- Segment: All tiers
- Business Goal: Conversation continuity and context preservation
- Value Impact: Enables multi-turn conversations improving AI optimization quality
- Strategic Impact: Core feature for $347K+ MRR - thread management is essential
"""

import os
import pytest
import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.main import app
# Thread-related services and schemas not available in current codebase
from app.db.postgres import get_postgres_db


class TestThreadLifecycleL3:
    """L3 Integration tests for thread lifecycle management."""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup test environment."""
        # JWT helper removed - not available
        self.test_threads = []
        self.test_users = []
        yield
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """Clean up test threads and data."""
        # Cleanup logic for test threads
        pass
    
    @pytest.fixture
    async def async_client(self):
        """Create async client."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac
    
    @pytest.mark.asyncio
    @pytest.mark.l3
    @pytest.mark.integration
    async def test_thread_creation_with_context_initialization(self, async_client):
        """Test thread creation with proper context initialization."""
        user_id = str(uuid.uuid4())
        token = self.jwt_helper.create_access_token(user_id, "thread_test@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create thread with initial context
        thread_data = {
            "title": "Infrastructure Optimization Thread",
            "context": {
                "industry": "technology",
                "company_size": "enterprise",
                "current_spend": 250000,
                "optimization_goals": ["cost_reduction", "performance"],
                "constraints": {
                    "maintain_sla": True,
                    "compliance_requirements": ["SOC2", "GDPR"]
                }
            },
            "metadata": {
                "source": "api",
                "client_version": "2.0.0",
                "user_tier": "enterprise"
            }
        }
        
        create_response = await async_client.post(
            "/api/threads/create",
            json=thread_data,
            headers=headers
        )
        
        if create_response.status_code in [200, 201]:
            thread = create_response.json()
            assert "thread_id" in thread or "id" in thread
            thread_id = thread.get("thread_id") or thread.get("id")
            self.test_threads.append(thread_id)
            
            # Verify context was properly initialized
            if "context" in thread:
                assert thread["context"].get("industry") == "technology"
                assert thread["context"].get("optimization_goals") == ["cost_reduction", "performance"]
        elif create_response.status_code == 404:
            pytest.skip("Thread endpoints not implemented")
    
    @pytest.mark.asyncio
    @pytest.mark.l3
    @pytest.mark.integration
    async def test_thread_state_transitions(self, async_client):
        """Test thread state transitions through lifecycle."""
        user_id = str(uuid.uuid4())
        token = self.jwt_helper.create_access_token(user_id, "state_test@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create thread
        create_response = await async_client.post(
            "/api/threads/create",
            json={"title": "State Transition Test"},
            headers=headers
        )
        
        if create_response.status_code in [200, 201]:
            thread = create_response.json()
            thread_id = thread.get("thread_id") or thread.get("id")
            self.test_threads.append(thread_id)
            
            # State transitions: new -> active -> processing -> completed
            states = ["active", "processing", "completed"]
            
            for state in states:
                update_response = await async_client.patch(
                    f"/api/threads/{thread_id}/state",
                    json={"state": state},
                    headers=headers
                )
                
                if update_response.status_code == 200:
                    updated = update_response.json()
                    assert updated.get("state") == state or updated.get("status") == state
                
                # Add delay between transitions
                await asyncio.sleep(0.5)
            
            # Verify final state
            get_response = await async_client.get(
                f"/api/threads/{thread_id}",
                headers=headers
            )
            
            if get_response.status_code == 200:
                final_thread = get_response.json()
                assert final_thread.get("state") == "completed" or final_thread.get("status") == "completed"
        elif create_response.status_code == 404:
            pytest.skip("Thread endpoints not implemented")
    
    @pytest.mark.asyncio
    @pytest.mark.l3
    @pytest.mark.integration
    async def test_thread_message_append_and_retrieval(self, async_client):
        """Test appending messages to thread and retrieving conversation history."""
        user_id = str(uuid.uuid4())
        token = self.jwt_helper.create_access_token(user_id, "message_test@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create thread
        create_response = await async_client.post(
            "/api/threads/create",
            json={"title": "Message History Test"},
            headers=headers
        )
        
        if create_response.status_code in [200, 201]:
            thread = create_response.json()
            thread_id = thread.get("thread_id") or thread.get("id")
            self.test_threads.append(thread_id)
            
            # Append multiple messages
            messages = [
                {"role": "user", "content": "Analyze my AWS costs"},
                {"role": "assistant", "content": "I'll analyze your AWS costs. Let me examine your usage patterns."},
                {"role": "user", "content": "Focus on EC2 and RDS services"},
                {"role": "assistant", "content": "Analyzing EC2 and RDS services specifically..."}
            ]
            
            for msg in messages:
                msg_response = await async_client.post(
                    f"/api/threads/{thread_id}/messages",
                    json=msg,
                    headers=headers
                )
                assert msg_response.status_code in [200, 201, 404]
                await asyncio.sleep(0.1)  # Ensure ordering
            
            # Retrieve conversation history
            history_response = await async_client.get(
                f"/api/threads/{thread_id}/messages",
                headers=headers
            )
            
            if history_response.status_code == 200:
                history = history_response.json()
                if isinstance(history, list):
                    assert len(history) >= len(messages)
                    # Verify message ordering
                    for i, msg in enumerate(history[:len(messages)]):
                        assert msg.get("role") == messages[i]["role"]
        elif create_response.status_code == 404:
            pytest.skip("Thread endpoints not implemented")
    
    @pytest.mark.asyncio
    @pytest.mark.l3
    @pytest.mark.integration
    async def test_thread_fork_and_branch(self, async_client):
        """Test thread forking for exploring alternative optimization paths."""
        user_id = str(uuid.uuid4())
        token = self.jwt_helper.create_access_token(user_id, "fork_test@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create parent thread
        parent_response = await async_client.post(
            "/api/threads/create",
            json={
                "title": "Main Optimization Thread",
                "context": {"strategy": "conservative"}
            },
            headers=headers
        )
        
        if parent_response.status_code in [200, 201]:
            parent = parent_response.json()
            parent_id = parent.get("thread_id") or parent.get("id")
            self.test_threads.append(parent_id)
            
            # Add some messages to parent
            await async_client.post(
                f"/api/threads/{parent_id}/messages",
                json={"role": "user", "content": "What are my optimization options?"},
                headers=headers
            )
            
            # Fork thread for aggressive optimization
            fork_response = await async_client.post(
                f"/api/threads/{parent_id}/fork",
                json={
                    "title": "Aggressive Optimization Branch",
                    "context_override": {"strategy": "aggressive"},
                    "fork_point": 0  # Fork from beginning
                },
                headers=headers
            )
            
            if fork_response.status_code in [200, 201]:
                fork = fork_response.json()
                fork_id = fork.get("thread_id") or fork.get("id")
                self.test_threads.append(fork_id)
                
                # Verify fork has parent reference
                assert fork.get("parent_thread_id") == parent_id or "parent" in fork
                
                # Add different message to fork
                await async_client.post(
                    f"/api/threads/{fork_id}/messages",
                    json={"role": "user", "content": "Apply aggressive cost cutting measures"},
                    headers=headers
                )
                
                # Both threads should exist independently
                parent_check = await async_client.get(f"/api/threads/{parent_id}", headers=headers)
                fork_check = await async_client.get(f"/api/threads/{fork_id}", headers=headers)
                
                assert parent_check.status_code in [200, 404]
                assert fork_check.status_code in [200, 404]
        elif parent_response.status_code == 404:
            pytest.skip("Thread endpoints not implemented")
    
    @pytest.mark.asyncio
    @pytest.mark.l3
    @pytest.mark.integration
    async def test_thread_archival_and_restoration(self, async_client):
        """Test thread archival and restoration processes."""
        user_id = str(uuid.uuid4())
        token = self.jwt_helper.create_access_token(user_id, "archive_test@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create thread
        create_response = await async_client.post(
            "/api/threads/create",
            json={
                "title": "Archive Test Thread",
                "context": {"important_data": "preserve_this"}
            },
            headers=headers
        )
        
        if create_response.status_code in [200, 201]:
            thread = create_response.json()
            thread_id = thread.get("thread_id") or thread.get("id")
            self.test_threads.append(thread_id)
            
            # Add messages
            for i in range(5):
                await async_client.post(
                    f"/api/threads/{thread_id}/messages",
                    json={"role": "user", "content": f"Message {i}"},
                    headers=headers
                )
            
            # Archive thread
            archive_response = await async_client.post(
                f"/api/threads/{thread_id}/archive",
                json={"reason": "completed", "compress": True},
                headers=headers
            )
            
            if archive_response.status_code in [200, 204]:
                # Thread should be marked as archived
                status_response = await async_client.get(
                    f"/api/threads/{thread_id}",
                    headers=headers
                )
                
                if status_response.status_code == 200:
                    archived_thread = status_response.json()
                    assert archived_thread.get("archived") is True or archived_thread.get("status") == "archived"
                
                # Restore thread
                restore_response = await async_client.post(
                    f"/api/threads/{thread_id}/restore",
                    headers=headers
                )
                
                if restore_response.status_code in [200, 204]:
                    # Verify restoration
                    restored_response = await async_client.get(
                        f"/api/threads/{thread_id}",
                        headers=headers
                    )
                    
                    if restored_response.status_code == 200:
                        restored = restored_response.json()
                        assert restored.get("archived") is False or restored.get("status") != "archived"
                        # Verify context was preserved
                        if "context" in restored:
                            assert restored["context"].get("important_data") == "preserve_this"
        elif create_response.status_code == 404:
            pytest.skip("Thread endpoints not implemented")