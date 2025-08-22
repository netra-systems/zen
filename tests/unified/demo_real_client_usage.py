"""Demo Real Client Usage Example

Shows how to use RealClientFactory for E2E testing with actual HTTP and WebSocket connections.
Demonstrates authentication flows, message patterns, and error handling scenarios.

Business Value Justification (BVJ):
- Segment: All tiers  
- Business Goal: Provide clear examples for reliable E2E test implementation
- Value Impact: Accelerates test development and reduces bugs
- Revenue Impact: Faster testing -> faster feature delivery -> revenue growth
"""

import asyncio
import json

from tests.unified.config import TEST_ENDPOINTS, get_test_user
from tests.unified.real_client_factory import create_real_client_factory
from tests.unified.real_client_types import create_test_config


async def demo_http_client():
    """Demonstrate HTTP client usage"""
    factory = create_real_client_factory()
    
    # Create HTTP client for backend API
    api_client = factory.create_backend_http_client(TEST_ENDPOINTS.api_base)
    
    try:
        # Test health endpoint
        health_response = await api_client.get("/health")
        print(f"Health check: {health_response}")
        
        # Test with authentication
        user = get_test_user("enterprise")
        token = "test-jwt-token-here"
        
        # Authenticated request
        user_data = await api_client.get("/user/profile", token=token)
        print(f"User profile: {user_data}")
        
        # POST request
        message_data = {"content": "Test message", "user_id": user.id}
        response = await api_client.post("/chat/message", message_data, token=token)
        print(f"Message sent: {response}")
        
    except Exception as e:
        print(f"HTTP client error: {e}")
    finally:
        await api_client.close()


async def demo_websocket_client():
    """Demonstrate WebSocket client usage"""
    factory = create_real_client_factory()
    
    # Create WebSocket client
    ws_client = factory.create_websocket_client(TEST_ENDPOINTS.ws_url)
    
    try:
        # Connect with authentication headers
        headers = {"Authorization": "Bearer test-jwt-token-here"}
        connected = await ws_client.connect(headers=headers)
        
        if connected:
            print("WebSocket connected successfully")
            
            # Send test message
            test_message = {
                "type": "chat_message",
                "content": "Hello from real client!",
                "user_id": "test-user-123"
            }
            
            sent = await ws_client.send(test_message)
            if sent:
                print("Message sent")
                
                # Wait for response
                response = await ws_client.receive(timeout=10.0)
                if response:
                    print(f"Received response: {response}")
                else:
                    print("No response received")
            else:
                print("Failed to send message")
        else:
            print("Failed to connect to WebSocket")
            
    except Exception as e:
        print(f"WebSocket client error: {e}")
    finally:
        await ws_client.close()


async def demo_auth_flow():
    """Demonstrate complete authentication flow"""
    factory = create_real_client_factory()
    
    # Create auth service client
    auth_client = factory.create_auth_http_client(TEST_ENDPOINTS.auth_base)
    
    try:
        # Login request
        login_data = {
            "email": "test-user@example.com",
            "password": "test-password"
        }
        
        login_response = await auth_client.post("/auth/login", login_data)
        print(f"Login response: {login_response}")
        
        # Extract token (this would be real in actual test)
        token = login_response.get("access_token", "mock-token")
        
        # Validate token
        validation_response = await auth_client.get(
            "/auth/validate", token=token
        )
        print(f"Token validation: {validation_response}")
        
    except Exception as e:
        print(f"Auth flow error: {e}")
    finally:
        await auth_client.close()


async def demo_error_scenarios():
    """Demonstrate error handling scenarios"""
    config = create_test_config(timeout=5.0, max_retries=2)
    factory = create_real_client_factory(config)
    
    # Test connection to non-existent service
    client = factory.create_http_client("http://non-existent-service:9999")
    
    try:
        await client.get("/test")
    except Exception as e:
        print(f"Expected error caught: {type(e).__name__}: {e}")
    finally:
        await client.close()
        
    # Test WebSocket connection failure
    ws_client = factory.create_websocket_client("ws://invalid-host:8080/ws")
    
    connected = await ws_client.connect()
    print(f"Connection result for invalid host: {connected}")
    
    if not connected:
        print(f"Connection metrics: {ws_client.metrics}")
        
    await ws_client.close()


async def demo_performance_monitoring():
    """Demonstrate performance monitoring features"""
    factory = create_real_client_factory()
    
    # Create multiple clients
    api_client = factory.create_backend_http_client(TEST_ENDPOINTS.api_base)
    ws_client = factory.create_websocket_client(TEST_ENDPOINTS.ws_url)
    
    try:
        # Simulate some activity
        await api_client.get("/health")
        
        await ws_client.connect()
        await ws_client.send({"type": "ping"})
        await ws_client.receive(timeout=1.0)
        
        # Get aggregated metrics
        metrics = factory.get_connection_metrics()
        print(f"Connection metrics: {json.dumps(metrics, indent=2)}")
        
    except Exception as e:
        print(f"Performance demo error: {e}")
    finally:
        await factory.cleanup()


async def main():
    """Run all demo scenarios"""
    print("=== Real Client Factory Demo ===")
    
    print("\n1. HTTP Client Demo:")
    await demo_http_client()
    
    print("\n2. WebSocket Client Demo:")
    await demo_websocket_client()
    
    print("\n3. Auth Flow Demo:")
    await demo_auth_flow()
    
    print("\n4. Error Scenarios Demo:")
    await demo_error_scenarios()
    
    print("\n5. Performance Monitoring Demo:")
    await demo_performance_monitoring()
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(main())