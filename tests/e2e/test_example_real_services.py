from shared.isolated_environment import get_env

from shared.isolated_environment import IsolatedEnvironment

"""

Example test demonstrating the new real service testing infrastructure.

Shows how to use dev_launcher-based fixtures for E2E testing.

"""



import asyncio

import os



import pytest



# Enable real services for this test module

pytestmark = pytest.mark.skipif(

    reason="Real services disabled (set USE_REAL_SERVICES=true)"

)





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_auth_login_flow(real_services):

    """Test real authentication login flow."""

    # Create a new test user

    user_data = await real_services.auth_client.create_test_user(

        email="testuser@example.com",

        password="securepass123"

    )

    

    # Verify user was created

    assert user_data["email"] == "testuser@example.com"

    assert "token" in user_data

    

    # Test login with credentials

    token = await real_services.auth_client.login(

        email="testuser@example.com",

        password="securepass123"

    )

    

    assert token is not None

    assert len(token) > 0

    

    # Verify token

    verification = await real_services.auth_client.verify_token(token)

    assert verification["email"] == "testuser@example.com"





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_connection(real_services):

    """Test real WebSocket connection and messaging."""

    # Create WebSocket client with auth

    ws_client = await real_services.create_websocket_client()

    

    try:

        # Connect to WebSocket

        connected = await ws_client.connect()

        assert connected is True

        

        # Send ping message

        await ws_client.send_ping()

        

        # Wait for pong response

        response = await ws_client.receive_until("pong", timeout=5.0)

        assert response is not None

        assert response["type"] == "pong"

        

        # Send chat message

        await ws_client.send_chat("Hello from test!")

        

        # Wait for response

        chat_response = await ws_client.receive(timeout=10.0)

        assert chat_response is not None

        

    finally:

        await ws_client.disconnect()





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_backend_api_with_auth(real_services):

    """Test backend API endpoints with authentication."""

    # Backend client is already authenticated

    backend = real_services.backend_client

    

    # Create a new thread

    thread = await backend.create_thread(name="Test Thread")

    assert thread["name"] == "Test Thread"

    assert "id" in thread

    

    # Get threads list

    threads = await backend.get_threads()

    assert len(threads) > 0

    assert any(t["name"] == "Test Thread" for t in threads)

    

    # Send chat message

    chat_response = await backend.send_chat_message(

        message="Test message",

        thread_id=thread["id"]

    )

    assert chat_response is not None

    

    # Get chat history

    history = await backend.get_chat_history(thread_id=thread["id"])

    assert len(history) > 0





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_service_health_checks(real_services, service_discovery):

    """Test that all services are healthy."""

    # Discover all running services

    services = await service_discovery.discover_all_services()

    

    assert "auth" in services

    assert "backend" in services

    

    # Check auth service health

    auth_info = services["auth"]

    assert auth_info.port > 0

    assert await real_services.auth_client.health_check() is True

    

    # Check backend service health

    backend_info = services["backend"]

    assert backend_info.port > 0

    assert await real_services.backend_client.health_check() is True





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_dynamic_port_allocation(service_discovery):

    """Test that services use dynamic ports."""

    # Get service information

    auth_info = await service_discovery.get_service_info("auth")

    backend_info = await service_discovery.get_service_info("backend")

    

    # Verify ports are allocated (not necessarily the defaults)

    assert auth_info.port > 0

    assert backend_info.port > 0

    

    # Verify service URLs are constructed correctly

    assert auth_info.base_url == f"http://localhost:{auth_info.port}"

    assert backend_info.base_url == f"http://localhost:{backend_info.port}"

    

    # Verify WebSocket URL

    assert backend_info.websocket_url == f"ws://localhost:{backend_info.port}/ws"





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_multiple_users_concurrent(real_services):

    """Test multiple users connecting concurrently."""

    # Create multiple test users

    users = []

    for i in range(3):

        user_data = await real_services.auth_client.create_test_user(

            email=f"user{i}@example.com",

            password="password123"

        )

        users.append(user_data)

    

    # Create WebSocket clients for each user

    ws_clients = []

    for user in users:

        ws_client = await real_services.factory.create_websocket_client(user["token"])

        await ws_client.connect()

        ws_clients.append(ws_client)

    

    try:

        # Send messages from each client

        for i, client in enumerate(ws_clients):

            await client.send_chat(f"Message from user {i}")

        

        # Each client should receive responses

        for client in ws_clients:

            response = await client.receive(timeout=10.0)

            assert response is not None

            

    finally:

        # Cleanup all connections

        for client in ws_clients:

            await client.disconnect()





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_service_restart_resilience(real_services, dev_launcher):

    """Test that services can be restarted during tests."""

    # Initial health check

    assert await real_services.auth_client.health_check() is True

    

    # Note: In a real scenario, we might restart a service here

    # For now, just verify the service remains healthy

    await asyncio.sleep(1.0)

    

    # Verify service is still healthy

    assert await real_services.auth_client.health_check() is True

    

    # Create a new user after potential restart

    user_data = await real_services.auth_client.create_test_user()

    assert "token" in user_data





# Integration test combining multiple services

@pytest.mark.asyncio

@pytest.mark.e2e

async def test_full_user_journey(real_services):

    """Test complete user journey across all services."""

    # 1. Register new user

    user = await real_services.auth_client.register(

        email="journey@example.com",

        password="secure456",

        first_name="Test",

        last_name="Journey"

    )

    assert user["email"] == "journey@example.com"

    

    # 2. Login

    token = await real_services.auth_client.login(

        email="journey@example.com",

        password="secure456"

    )

    

    # 3. Create authenticated backend client

    backend = real_services.backend_client.with_token(token)

    

    # 4. Create thread

    thread = await backend.create_thread(name="Journey Thread")

    

    # 5. Connect WebSocket

    ws_client = await real_services.factory.create_websocket_client(token)

    await ws_client.connect()

    

    try:

        # 6. Send message via WebSocket

        await ws_client.send_chat("Starting my journey", thread_id=thread["id"])

        

        # 7. Receive response

        response = await ws_client.receive(timeout=15.0)

        assert response is not None

        

        # 8. Verify message in history

        history = await backend.get_chat_history(thread_id=thread["id"])

        assert len(history) > 0

        

    finally:

        await ws_client.disconnect()

