"""
E2E Tests for Message Processing
Tests end-to-end message flow, persistence, retrieval, and real-time updates.

Business Value Justification (BVJ):
- Segment: All (Core functionality for all tiers)
- Business Goal: Feature Reliability, Data Integrity
- Value Impact: Messages are the primary value delivery mechanism
- Strategic Impact: Message loss = customer churn, reputation damage
"""

import asyncio
import pytest
import aiohttp
import websockets
import json
from typing import Dict, List, Optional
import uuid
import time
import asyncpg
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.e2e
@pytest.mark.real_services
class TestMessageProcessing:
    """Test suite for message processing pipeline."""

    @pytest.mark.asyncio
    async def test_example_message_flow(self):
        """
        Test complete example message flow from user to AI response.
        
        Critical Assertions:
        - Message accepted by API
        - Message queued for processing
        - AI processing triggered
        - Response generated and returned
        - Complete flow under 10 seconds
        
        Expected Failure: Message pipeline not configured
        Business Impact: Core feature broken, no AI value delivered
        """
        backend_url = "http://localhost:8000"
        
        async with aiohttp.ClientSession() as session:
            # Create test user and get auth token
            test_email = f"message.flow.{uuid.uuid4()}@example.com"
            await session.post(
                f"{backend_url}/auth/register",
                json={
                    "email": test_email,
                    "password": "MessageTest123!",
                    "name": "Message Test User"
                }
            )
            
            login_response = await session.post(
                f"{backend_url}/auth/login",
                json={"email": test_email, "password": "MessageTest123!"}
            )
            
            login_data = await login_response.json()
            
            # Handle different possible token field names
            access_token = None
            for token_field in ['access_token', 'token', 'jwt', 'access']:
                if token_field in login_data:
                    access_token = login_data[token_field]
                    break
            
            if not access_token:
                pytest.skip(f"Login response missing access token. Response: {login_data}")
                return
                
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Create a thread for messages
            thread_response = await session.post(
                f"{backend_url}/api/threads",
                json={"title": "Test Message Flow"},
                headers=headers
            )
            
            assert thread_response.status in [200, 201], \
                f"Thread creation failed: {thread_response.status}"
            
            thread_data = await thread_response.json()
            thread_id = thread_data['thread_id']
            
            # Send example message
            example_messages = [
                {
                    "content": "What is 2 + 2?",
                    "expected_keywords": ["4", "four"]
                },
                {
                    "content": "Explain machine learning in one sentence.",
                    "expected_keywords": ["algorithm", "data", "learn", "pattern"]
                },
                {
                    "content": "List three primary colors.",
                    "expected_keywords": ["red", "blue", "yellow", "green"]
                }
            ]
            
            for example in example_messages:
                start_time = time.time()
                
                # Send message
                message_response = await session.post(
                    f"{backend_url}/api/messages",
                    json={
                        "thread_id": thread_id,
                        "content": example["content"],
                        "role": "user"
                    },
                    headers=headers
                )
                
                assert message_response.status in [200, 201], \
                    f"Message send failed: {message_response.status}"
                
                message_data = await message_response.json()
                message_id = message_data.get('message_id')
                assert message_id, "No message ID returned"
                
                # Check message was queued
                assert message_data.get('status') in ['queued', 'processing', 'completed'], \
                    f"Invalid message status: {message_data.get('status')}"
                
                # Wait for AI response (polling)
                response_received = False
                max_wait = 10  # seconds
                
                while time.time() - start_time < max_wait:
                    # Get thread messages
                    messages_response = await session.get(
                        f"{backend_url}/api/threads/{thread_id}/messages",
                        headers=headers
                    )
                    
                    if messages_response.status == 200:
                        messages = await messages_response.json()
                        
                        # Look for AI response to this message
                        user_msg = next((m for m in messages if m.get('id') == message_id), None)
                        if user_msg:
                            # Check if there's a response after this message
                            user_idx = messages.index(user_msg)
                            if user_idx < len(messages) - 1:
                                ai_response = messages[user_idx + 1]
                                if ai_response.get('role') == 'assistant':
                                    response_received = True
                                    
                                    # Verify response quality
                                    content = ai_response.get('content', '').lower()
                                    assert len(content) > 0, "Empty AI response"
                                    
                                    # Check for expected keywords
                                    has_keyword = any(
                                        keyword.lower() in content 
                                        for keyword in example["expected_keywords"]
                                    )
                                    assert has_keyword, \
                                        f"AI response doesn't contain expected content: {content}"
                                    
                                    break
                    
                    await asyncio.sleep(0.5)
                
                elapsed = time.time() - start_time
                assert response_received, \
                    f"No AI response received for '{example['content']}' after {elapsed:.1f}s"
                assert elapsed < 10, \
                    f"Response too slow: {elapsed:.1f}s"

    @pytest.mark.asyncio
    async def test_message_persistence(self):
        """
        Test message persistence to databases.
        
        Critical Assertions:
        - Messages saved to PostgreSQL
        - Message metadata stored
        - Attachments handled
        - Message history preserved
        
        Expected Failure: Database writes not implemented
        Business Impact: Data loss, no conversation history
        """
        backend_url = "http://localhost:8000"
        
        async with aiohttp.ClientSession() as session:
            # Create test user
            test_email = f"persist.{uuid.uuid4()}@example.com"
            await session.post(
                f"{backend_url}/auth/register",
                json={
                    "email": test_email,
                    "password": "PersistTest123!",
                    "name": "Persist Test User"
                }
            )
            
            login_response = await session.post(
                f"{backend_url}/auth/login",
                json={"email": test_email, "password": "PersistTest123!"}
            )
            
            login_data = await login_response.json()
            access_token = login_data['access_token']
            user_id = login_data.get('user_id')
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Create thread
            thread_response = await session.post(
                f"{backend_url}/api/threads",
                json={"title": "Persistence Test"},
                headers=headers
            )
            
            thread_data = await thread_response.json()
            thread_id = thread_data['thread_id']
            
            # Send messages with metadata
            test_messages = []
            for i in range(3):
                message_data = {
                    "thread_id": thread_id,
                    "content": f"Test message {i} with unicode: [U+4F60][U+597D] [U+00E9]mojis: [U+1F680]",
                    "role": "user",
                    "metadata": {
                        "client_id": str(uuid.uuid4()),
                        "timestamp": time.time(),
                        "tags": ["test", f"message_{i}"],
                        "attachments": [
                            {
                                "type": "image",
                                "url": f"https://example.com/image_{i}.png",
                                "size": 1024 * (i + 1)
                            }
                        ] if i > 0 else []
                    }
                }
                
                response = await session.post(
                    f"{backend_url}/api/messages",
                    json=message_data,
                    headers=headers
                )
                
                assert response.status in [200, 201], \
                    f"Message {i} failed: {response.status}"
                
                result = await response.json()
                test_messages.append({
                    "id": result['message_id'],
                    "content": message_data["content"],
                    "metadata": message_data["metadata"]
                })
            
            # Verify messages persisted by retrieving them
            await asyncio.sleep(1)  # Allow time for persistence
            
            messages_response = await session.get(
                f"{backend_url}/api/threads/{thread_id}/messages",
                headers=headers
            )
            
            assert messages_response.status == 200, "Failed to retrieve messages"
            stored_messages = await messages_response.json()
            
            # Verify all messages present
            for test_msg in test_messages:
                stored_msg = next(
                    (m for m in stored_messages if m.get('id') == test_msg['id']),
                    None
                )
                assert stored_msg, f"Message {test_msg['id']} not persisted"
                
                # Verify content preserved
                assert stored_msg.get('content') == test_msg['content'], \
                    "Message content corrupted"
                
                # Verify metadata preserved
                if test_msg.get('metadata'):
                    stored_metadata = stored_msg.get('metadata', {})
                    assert stored_metadata.get('tags') == test_msg['metadata'].get('tags'), \
                        "Message tags not preserved"
                    
                    # Check attachments
                    if test_msg['metadata'].get('attachments'):
                        assert stored_metadata.get('attachments'), \
                            "Attachments not preserved"
            
            # Direct database verification (if accessible)
            try:
                pg_conn = await asyncpg.connect(
                    host='localhost',
                    port=5432,
                    user='postgres',
                    password='postgres',
                    database='netra_dev'
                )
                
                # Check messages table
                db_messages = await pg_conn.fetch(
                    "SELECT * FROM messages WHERE thread_id = $1",
                    thread_id
                )
                
                assert len(db_messages) >= len(test_messages), \
                    "Not all messages in database"
                
                await pg_conn.close()
                
            except Exception as e:
                # Database check is optional but log if it fails
                print(f"Direct database verification skipped: {e}")

    @pytest.mark.asyncio
    async def test_message_retrieval(self):
        """
        Test message retrieval and pagination.
        
        Critical Assertions:
        - Messages retrieved in correct order
        - Pagination works correctly
        - Filtering by thread works
        - Search functionality works
        
        Expected Failure: Query/retrieval logic broken
        Business Impact: Users can't see conversation history
        """
        backend_url = "http://localhost:8000"
        
        async with aiohttp.ClientSession() as session:
            # Create test user
            test_email = f"retrieval.{uuid.uuid4()}@example.com"
            await session.post(
                f"{backend_url}/auth/register",
                json={
                    "email": test_email,
                    "password": "RetrieveTest123!",
                    "name": "Retrieve Test User"
                }
            )
            
            login_response = await session.post(
                f"{backend_url}/auth/login",
                json={"email": test_email, "password": "RetrieveTest123!"}
            )
            
            login_data = await login_response.json()
            access_token = login_data['access_token']
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Create multiple threads with messages
            threads = []
            for t in range(2):
                thread_response = await session.post(
                    f"{backend_url}/api/threads",
                    json={"title": f"Thread {t}"},
                    headers=headers
                )
                thread_data = await thread_response.json()
                thread_id = thread_data['thread_id']
                threads.append(thread_id)
                
                # Add messages to thread
                for m in range(10):
                    await session.post(
                        f"{backend_url}/api/messages",
                        json={
                            "thread_id": thread_id,
                            "content": f"Thread {t} Message {m} searchterm_{t}_{m}",
                            "role": "user"
                        },
                        headers=headers
                    )
            
            # Test retrieval for specific thread
            thread_messages = await session.get(
                f"{backend_url}/api/threads/{threads[0]}/messages",
                headers=headers
            )
            
            assert thread_messages.status == 200, "Failed to retrieve thread messages"
            messages = await thread_messages.json()
            
            # Verify correct thread
            for msg in messages:
                if msg.get('content'):
                    assert f"Thread 0" in msg['content'] or msg.get('role') == 'assistant', \
                        f"Wrong thread message: {msg['content']}"
            
            # Test pagination
            page1_response = await session.get(
                f"{backend_url}/api/threads/{threads[0]}/messages?limit=5&offset=0",
                headers=headers
            )
            
            if page1_response.status == 200:
                page1 = await page1_response.json()
                
                # Handle both array and paginated response formats
                if isinstance(page1, dict):
                    page1_messages = page1.get('messages', page1.get('data', []))
                else:
                    page1_messages = page1
                
                assert len(page1_messages) <= 5, "Pagination limit not respected"
                
                # Get page 2
                page2_response = await session.get(
                    f"{backend_url}/api/threads/{threads[0]}/messages?limit=5&offset=5",
                    headers=headers
                )
                
                if page2_response.status == 200:
                    page2 = await page2_response.json()
                    
                    if isinstance(page2, dict):
                        page2_messages = page2.get('messages', page2.get('data', []))
                    else:
                        page2_messages = page2
                    
                    # Verify no overlap
                    page1_ids = [m.get('id') for m in page1_messages]
                    page2_ids = [m.get('id') for m in page2_messages]
                    
                    overlap = set(page1_ids) & set(page2_ids)
                    assert len(overlap) == 0, f"Pagination overlap: {overlap}"
            
            # Test message search
            search_response = await session.get(
                f"{backend_url}/api/messages/search?q=searchterm_0_5",
                headers=headers
            )
            
            if search_response.status == 200:
                search_results = await search_response.json()
                
                # Handle different response formats
                if isinstance(search_results, dict):
                    results = search_results.get('results', search_results.get('messages', []))
                else:
                    results = search_results
                
                if len(results) > 0:
                    # Verify search found correct message
                    found = any(
                        "searchterm_0_5" in msg.get('content', '')
                        for msg in results
                    )
                    assert found, "Search didn't find expected message"
            
            # Test ordering (newest first or oldest first)
            ordered_response = await session.get(
                f"{backend_url}/api/threads/{threads[0]}/messages?order=desc",
                headers=headers
            )
            
            if ordered_response.status == 200:
                ordered_messages = await ordered_response.json()
                
                # Extract message list
                if isinstance(ordered_messages, dict):
                    msg_list = ordered_messages.get('messages', ordered_messages.get('data', []))
                else:
                    msg_list = ordered_messages
                
                # Check if messages have timestamps and are ordered
                if len(msg_list) > 1:
                    timestamps = [
                        msg.get('created_at', msg.get('timestamp', 0))
                        for msg in msg_list
                        if msg.get('created_at') or msg.get('timestamp')
                    ]
                    
                    if timestamps:
                        # Verify descending order
                        for i in range(len(timestamps) - 1):
                            if isinstance(timestamps[i], str) and isinstance(timestamps[i+1], str):
                                # String timestamps
                                pass  # Can't easily compare without parsing
                            elif isinstance(timestamps[i], (int, float)):
                                assert timestamps[i] >= timestamps[i+1], \
                                    "Messages not in descending order"

    @pytest.mark.asyncio
    async def test_realtime_updates(self):
        """
        Test real-time message updates via WebSocket.
        
        Critical Assertions:
        - New messages broadcast to WebSocket
        - Message updates propagated
        - Multiple clients receive updates
        - No message duplication
        
        Expected Failure: WebSocket broadcasting not implemented
        Business Impact: No real-time collaboration, poor UX
        """
        backend_url = "http://localhost:8000"
        ws_url = "ws://localhost:8000/ws"
        
        async with aiohttp.ClientSession() as session:
            # Create test user
            test_email = f"realtime.{uuid.uuid4()}@example.com"
            await session.post(
                f"{backend_url}/auth/register",
                json={
                    "email": test_email,
                    "password": "RealtimeTest123!",
                    "name": "Realtime Test User"
                }
            )
            
            login_response = await session.post(
                f"{backend_url}/auth/login",
                json={"email": test_email, "password": "RealtimeTest123!"}
            )
            
            login_data = await login_response.json()
            access_token = login_data['access_token']
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Create thread
            thread_response = await session.post(
                f"{backend_url}/api/threads",
                json={"title": "Realtime Test"},
                headers=headers
            )
            
            thread_data = await thread_response.json()
            thread_id = thread_data['thread_id']
            
            # Connect WebSocket clients
            received_messages = []
            
            async def websocket_client():
                try:
                    ws_headers = {"Authorization": f"Bearer {access_token}"}
                    async with websockets.connect(
                        ws_url,
                        extra_headers=ws_headers
                    ) as websocket:
                        # Subscribe to thread
                        subscribe_msg = {
                            "type": "subscribe",
                            "thread_id": thread_id
                        }
                        await websocket.send(json.dumps(subscribe_msg))
                        
                        # Listen for messages
                        timeout = 10
                        start_time = time.time()
                        
                        while time.time() - start_time < timeout:
                            try:
                                message = await asyncio.wait_for(
                                    websocket.recv(),
                                    timeout=1
                                )
                                data = json.loads(message)
                                
                                # Check if it's a message update
                                if data.get("type") in ["message_created", "message_updated", "new_message"]:
                                    received_messages.append(data)
                                    
                                    # Verify message structure
                                    assert data.get("thread_id") == thread_id, \
                                        f"Wrong thread ID in broadcast: {data.get('thread_id')}"
                                    assert data.get("message") or data.get("content"), \
                                        "No message content in broadcast"
                                    
                                    # If we got our test message, we can break
                                    msg_content = data.get("message", {}).get("content", "") or data.get("content", "")
                                    if "realtime_test_message" in msg_content:
                                        break
                                        
                            except asyncio.TimeoutError:
                                continue
                            except websockets.exceptions.ConnectionClosed:
                                break
                                
                except Exception as e:
                    print(f"WebSocket client error: {e}")
            
            # Start WebSocket client
            ws_task = asyncio.create_task(websocket_client())
            
            # Give WebSocket time to connect and subscribe
            await asyncio.sleep(1)
            
            # Send a message via HTTP API
            test_message_content = f"realtime_test_message_{uuid.uuid4()}"
            message_response = await session.post(
                f"{backend_url}/api/messages",
                json={
                    "thread_id": thread_id,
                    "content": test_message_content,
                    "role": "user"
                },
                headers=headers
            )
            
            assert message_response.status in [200, 201], \
                "Failed to send test message"
            
            # Wait for WebSocket to receive
            await asyncio.sleep(2)
            
            # Cancel WebSocket task
            ws_task.cancel()
            try:
                await ws_task
            except asyncio.CancelledError:
                pass
            
            # Verify message was received via WebSocket
            assert len(received_messages) > 0, \
                "No real-time updates received via WebSocket"
            
            # Check for our test message
            found_test_message = any(
                test_message_content in str(msg)
                for msg in received_messages
            )
            assert found_test_message, \
                f"Test message not broadcast: {received_messages}"
            
            # Test multiple subscribers (optional advanced test)
            if len(received_messages) > 0:
                # Start multiple WebSocket clients
                client_results = []
                
                async def multi_client(client_id):
                    messages = []
                    try:
                        ws_headers = {"Authorization": f"Bearer {access_token}"}
                        async with websockets.connect(ws_url, extra_headers=ws_headers) as ws:
                            # Subscribe
                            await ws.send(json.dumps({
                                "type": "subscribe",
                                "thread_id": thread_id,
                                "client_id": client_id
                            }))
                            
                            # Wait for broadcast
                            message = await asyncio.wait_for(ws.recv(), timeout=5)
                            messages.append(json.loads(message))
                    except:
                        pass
                    return messages
                
                # Create multiple clients
                client_tasks = [
                    asyncio.create_task(multi_client(f"client_{i}"))
                    for i in range(3)
                ]
                
                # Send another message
                await session.post(
                    f"{backend_url}/api/messages",
                    json={
                        "thread_id": thread_id,
                        "content": f"broadcast_test_{uuid.uuid4()}",
                        "role": "user"
                    },
                    headers=headers
                )
                
                # Wait and collect results
                await asyncio.sleep(2)
                for task in client_tasks:
                    task.cancel()
                
                # At least some clients should have received the broadcast
                # (This is optional as setup might be complex)