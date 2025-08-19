"""Simple WebSocket Test Client Demo

Simple demonstration without unicode characters that might cause encoding issues.

Business Value: Validates WebSocket infrastructure reliability.
"""

import asyncio
import json
import uuid
from datetime import datetime
from websocket_test_client import (
    WebSocketTestClient, ConcurrentWebSocketTester, 
    TestMessage, ConnectionState
)


async def demo_basic_features():
    """Demonstrate basic WebSocket test client features"""
    print("WebSocket Test Client Demo")
    print("=" * 50)
    
    # Test 1: Basic client functionality
    print("\nTest 1: Basic Client Creation and Configuration")
    client = WebSocketTestClient("ws://localhost:8000", "test-auth-token")
    
    print(f"Client ID: {client.client_id[:8]}...")
    print(f"Base URL: {client.base_url}")
    print(f"Connection URL: {client.get_connection_url()}")
    print(f"Initial state: {client.state.value}")
    print(f"Is connected: {client.is_connected()}")
    print(f"Is healthy: {client.is_healthy()}")
    
    # Test 2: Message creation and structure
    print("\nTest 2: Message Creation and Protocols")
    test_message = TestMessage(
        message_type="chat_message",
        content="Hello from WebSocket test client!",
        thread_id=str(uuid.uuid4())
    )
    
    websocket_message = test_message.to_websocket_message()
    print(f"Test message created:")
    print(f"   Type: {websocket_message['type']}")
    print(f"   Content: {websocket_message['payload']['content']}")
    print(f"   Thread ID: {websocket_message['payload']['thread_id']}")
    print(f"   Has timestamp: {'timestamp' in websocket_message['payload']}")
    
    # Test 3: Metrics tracking
    print("\nTest 3: Metrics and Connection Tracking")
    initial_metrics = client.get_metrics()
    print(f"Initial metrics:")
    print(f"   Client ID: {initial_metrics['client_id'][:8]}...")
    print(f"   State: {initial_metrics['state']}")
    print(f"   Messages sent: {initial_metrics['messages_sent']}")
    print(f"   Messages received: {initial_metrics['messages_received']}")
    print(f"   Error count: {initial_metrics['error_count']}")
    
    # Test 4: Message handlers
    print("\nTest 4: Message Handler System")
    received_messages = []
    
    def test_handler(message):
        received_messages.append(message)
        print(f"   Handler received: {message.get('type', 'unknown')}")
    
    client.add_message_handler(test_handler)
    print(f"Added message handler")
    
    # Simulate message reception
    test_response = {
        "type": "agent_response",
        "payload": {
            "content": "Response from agent",
            "thread_id": str(uuid.uuid4()),
            "agent_name": "TestAgent"
        }
    }
    
    await client._handle_received_message(test_response)
    print(f"Simulated message reception")
    print(f"Messages handled: {len(received_messages)}")
    
    print("\nWebSocket Test Client Demo Complete!")
    print("All client features demonstrated successfully")
    print("Ready for integration testing")


async def demo_concurrent_testing():
    """Demo concurrent testing capabilities"""
    print("\nConcurrent Testing Demo")
    print("=" * 30)
    
    tester = ConcurrentWebSocketTester("ws://localhost:8000")
    tester.add_test_token("token-1")
    tester.add_test_token("token-2")
    tester.add_test_token("token-3")
    
    print(f"Concurrent tester created")
    print(f"Test tokens: {len(tester.test_tokens)}")
    
    # Create multiple test clients
    clients = []
    for i in range(3):
        client = await tester.create_client()
        clients.append(client)
        
    print(f"Created {len(clients)} test clients")
    print(f"Client IDs:")
    for i, client in enumerate(clients):
        print(f"   Client {i+1}: {client.client_id[:8]}... (Token: {client.auth_token})")
        
    # Test aggregate metrics
    aggregate_metrics = tester.get_aggregate_metrics()
    print(f"Aggregate metrics:")
    print(f"   Total clients: {aggregate_metrics['total_clients']}")
    print(f"   Connected clients: {aggregate_metrics['connected_clients']}")
    print(f"   Health rate: {aggregate_metrics['health_rate']:.1%}")
    
    print("Concurrent testing demo complete!")


async def main():
    """Main demo function"""
    await demo_basic_features()
    await demo_concurrent_testing()


if __name__ == "__main__":
    asyncio.run(main())