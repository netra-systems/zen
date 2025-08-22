#!/usr/bin/env python3
"""
L3 Integration Test: Agent Communication Basic Operations
Tests agent-to-agent communication, message routing, and coordination
from multiple angles including error cases and concurrent operations.

import sys
from pathlib import Path

from test_framework import setup_test_path

"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List

import aiohttp
import pytest

from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.redis_manager import RedisManager
from test_framework.test_patterns import L3IntegrationTest

class TestAgentCommunicationBasic(L3IntegrationTest):
    """Test agent communication patterns from multiple angles."""
    
    async def test_agent_message_routing(self):
        """Test basic agent message routing."""
        user_data = await self.create_test_user("agent1@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create thread for agent interaction
            thread_data = {"title": "Agent Test Thread"}
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads",
                json=thread_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                thread = await resp.json()
                thread_id = thread["id"]
            
            # Send message to trigger agent
            message_data = {
                "content": "Analyze this data",
                "agent_type": "analyzer"
            }
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                json=message_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                message = await resp.json()
                
                # Verify agent processing
                assert message["status"] == "processing"
                assert message["assigned_agent"] == "analyzer"
                
    async def test_agent_response_handling(self):
        """Test agent response handling and storage."""
        user_data = await self.create_test_user("agent2@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create thread
            thread_data = {"title": "Response Test"}
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads",
                json=thread_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                thread = await resp.json()
                thread_id = thread["id"]
            
            # Send message requiring agent response
            message_data = {
                "content": "Calculate 2+2",
                "agent_type": "calculator"
            }
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                json=message_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                message = await resp.json()
                message_id = message["id"]
            
            # Poll for response
            max_attempts = 10
            for _ in range(max_attempts):
                async with session.get(
                    f"{self.backend_url}/api/v1/threads/{thread_id}/messages/{message_id}",
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    assert resp.status == 200
                    message = await resp.json()
                    
                    if message["status"] == "completed":
                        assert "response" in message
                        assert message["response"]["result"] == 4
                        break
                        
                await asyncio.sleep(1)
            else:
                pytest.fail("Agent did not respond in time")
                
    async def test_agent_chain_execution(self):
        """Test chained agent execution."""
        user_data = await self.create_test_user("agent3@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create thread
            thread_data = {"title": "Chain Test"}
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads",
                json=thread_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                thread = await resp.json()
                thread_id = thread["id"]
            
            # Send message requiring multiple agents
            message_data = {
                "content": "Fetch data, analyze it, and summarize",
                "agent_chain": ["fetcher", "analyzer", "summarizer"]
            }
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                json=message_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                message = await resp.json()
                message_id = message["id"]
            
            # Monitor chain execution
            max_attempts = 20
            for _ in range(max_attempts):
                async with session.get(
                    f"{self.backend_url}/api/v1/threads/{thread_id}/messages/{message_id}",
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    assert resp.status == 200
                    message = await resp.json()
                    
                    if message["status"] == "completed":
                        # Verify all agents executed
                        assert "execution_chain" in message
                        assert len(message["execution_chain"]) == 3
                        assert message["execution_chain"][0]["agent"] == "fetcher"
                        assert message["execution_chain"][1]["agent"] == "analyzer"
                        assert message["execution_chain"][2]["agent"] == "summarizer"
                        break
                        
                await asyncio.sleep(1)
            else:
                pytest.fail("Agent chain did not complete")
                
    async def test_agent_error_handling(self):
        """Test agent error handling and recovery."""
        user_data = await self.create_test_user("agent4@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create thread
            thread_data = {"title": "Error Test"}
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads",
                json=thread_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                thread = await resp.json()
                thread_id = thread["id"]
            
            # Send message that will cause agent error
            message_data = {
                "content": "divide by zero",
                "agent_type": "calculator",
                "operation": "divide",
                "values": [10, 0]
            }
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                json=message_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                message = await resp.json()
                message_id = message["id"]
            
            # Check error handling
            await asyncio.sleep(2)
            
            async with session.get(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages/{message_id}",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                message = await resp.json()
                
                assert message["status"] == "error"
                assert "error" in message
                assert "division by zero" in message["error"].lower()
                
    async def test_agent_timeout_handling(self):
        """Test agent timeout and fallback."""
        user_data = await self.create_test_user("agent5@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create thread
            thread_data = {"title": "Timeout Test"}
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads",
                json=thread_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                thread = await resp.json()
                thread_id = thread["id"]
            
            # Send message requiring long processing
            message_data = {
                "content": "Process large dataset",
                "agent_type": "slow_processor",
                "timeout": 5  # 5 second timeout
            }
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                json=message_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                message = await resp.json()
                message_id = message["id"]
            
            # Wait for timeout
            await asyncio.sleep(7)
            
            async with session.get(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages/{message_id}",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                message = await resp.json()
                
                assert message["status"] in ["timeout", "error"]
                assert "timeout" in message.get("error", "").lower()
                
    async def test_agent_concurrent_processing(self):
        """Test concurrent agent processing of multiple messages."""
        user_data = await self.create_test_user("agent6@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create thread
            thread_data = {"title": "Concurrent Test"}
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads",
                json=thread_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                thread = await resp.json()
                thread_id = thread["id"]
            
            # Send multiple messages concurrently
            tasks = []
            for i in range(5):
                message_data = {
                    "content": f"Process message {i}",
                    "agent_type": "processor"
                }
                
                tasks.append(session.post(
                    f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                    json=message_data,
                    headers={"Authorization": f"Bearer {token}"}
                ))
            
            responses = await asyncio.gather(*tasks)
            
            # All should be accepted
            message_ids = []
            for resp in responses:
                assert resp.status == 201
                data = await resp.json()
                message_ids.append(data["id"])
            
            # Verify all are being processed
            await asyncio.sleep(2)
            
            for message_id in message_ids:
                async with session.get(
                    f"{self.backend_url}/api/v1/threads/{thread_id}/messages/{message_id}",
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    assert resp.status == 200
                    message = await resp.json()
                    assert message["status"] in ["processing", "completed"]
                    
    async def test_agent_priority_queue(self):
        """Test agent message priority handling."""
        user_data = await self.create_test_user("agent7@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create thread
            thread_data = {"title": "Priority Test"}
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads",
                json=thread_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                thread = await resp.json()
                thread_id = thread["id"]
            
            # Send messages with different priorities
            messages = [
                {"content": "Low priority", "priority": 1},
                {"content": "High priority", "priority": 10},
                {"content": "Medium priority", "priority": 5}
            ]
            
            message_ids = []
            for msg in messages:
                message_data = {
                    "content": msg["content"],
                    "agent_type": "processor",
                    "priority": msg["priority"]
                }
                
                async with session.post(
                    f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                    json=message_data,
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    assert resp.status == 201
                    data = await resp.json()
                    message_ids.append((data["id"], msg["priority"]))
            
            # Check processing order (high priority should complete first)
            await asyncio.sleep(3)
            
            completion_times = []
            for message_id, priority in message_ids:
                async with session.get(
                    f"{self.backend_url}/api/v1/threads/{thread_id}/messages/{message_id}",
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    assert resp.status == 200
                    message = await resp.json()
                    
                    if message["status"] == "completed":
                        completion_times.append((priority, message.get("completed_at")))
            
            # Higher priority should complete first
            if len(completion_times) >= 2:
                completion_times.sort(key=lambda x: x[1])
                priorities_order = [p for p, _ in completion_times]
                assert priorities_order[0] >= priorities_order[-1]
                
    async def test_agent_context_preservation(self):
        """Test agent context preservation across messages."""
        user_data = await self.create_test_user("agent8@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create thread
            thread_data = {"title": "Context Test"}
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads",
                json=thread_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                thread = await resp.json()
                thread_id = thread["id"]
            
            # Send initial message to establish context
            message1_data = {
                "content": "My name is John",
                "agent_type": "context_aware"
            }
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                json=message1_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
            
            await asyncio.sleep(2)
            
            # Send follow-up message requiring context
            message2_data = {
                "content": "What is my name?",
                "agent_type": "context_aware"
            }
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                json=message2_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                message = await resp.json()
                message_id = message["id"]
            
            # Check response uses context
            await asyncio.sleep(3)
            
            async with session.get(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages/{message_id}",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                message = await resp.json()
                
                if message["status"] == "completed":
                    assert "John" in message.get("response", {}).get("content", "")
                    
    async def test_agent_load_balancing(self):
        """Test agent load balancing across multiple instances."""
        user_data = await self.create_test_user("agent9@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create multiple threads
            thread_ids = []
            for i in range(3):
                thread_data = {"title": f"Load Test {i}"}
                
                async with session.post(
                    f"{self.backend_url}/api/v1/threads",
                    json=thread_data,
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    assert resp.status == 201
                    thread = await resp.json()
                    thread_ids.append(thread["id"])
            
            # Send messages to all threads simultaneously
            tasks = []
            for thread_id in thread_ids:
                for i in range(5):
                    message_data = {
                        "content": f"Process {i}",
                        "agent_type": "processor"
                    }
                    
                    tasks.append(session.post(
                        f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                        json=message_data,
                        headers={"Authorization": f"Bearer {token}"}
                    ))
            
            responses = await asyncio.gather(*tasks)
            
            # All should be accepted
            for resp in responses:
                assert resp.status == 201
            
            # Check agent assignment distribution
            agent_assignments = {}
            for resp in responses:
                data = await resp.json()
                agent_id = data.get("assigned_agent_instance")
                if agent_id:
                    agent_assignments[agent_id] = agent_assignments.get(agent_id, 0) + 1
            
            # Should be distributed across multiple agents
            if len(agent_assignments) > 1:
                # Check reasonable distribution
                max_load = max(agent_assignments.values())
                min_load = min(agent_assignments.values())
                assert max_load - min_load <= 5  # Reasonable balance
                
    async def test_agent_retry_mechanism(self):
        """Test agent retry on transient failures."""
        user_data = await self.create_test_user("agent10@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Create thread
            thread_data = {"title": "Retry Test"}
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads",
                json=thread_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                thread = await resp.json()
                thread_id = thread["id"]
            
            # Send message that may fail initially
            message_data = {
                "content": "Process with retry",
                "agent_type": "flaky_processor",
                "max_retries": 3
            }
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                json=message_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201
                message = await resp.json()
                message_id = message["id"]
            
            # Monitor retries
            max_attempts = 15
            for _ in range(max_attempts):
                async with session.get(
                    f"{self.backend_url}/api/v1/threads/{thread_id}/messages/{message_id}",
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    assert resp.status == 200
                    message = await resp.json()
                    
                    if message["status"] == "completed":
                        # Check retry count
                        assert "retry_count" in message
                        assert message["retry_count"] <= 3
                        break
                    elif message["status"] == "error":
                        # Should have exhausted retries
                        assert message.get("retry_count", 0) >= 3
                        break
                        
                await asyncio.sleep(1)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])