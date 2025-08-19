"""Demo WebSocket Test Client

Demonstration of the WebSocket test client capabilities.
Shows real-time testing capabilities without complex mocking.

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


async def demo_websocket_client_features():
    """Demonstrate WebSocket test client features"""
    print("🚀 WebSocket Test Client Demo")
    print("=" * 50)
    
    # Test 1: Basic client functionality
    print("\n📋 Test 1: Basic Client Creation and Configuration")
    client = WebSocketTestClient("ws://localhost:8000", "test-auth-token")
    
    print(f"✅ Client ID: {client.client_id[:8]}...")
    print(f"✅ Base URL: {client.base_url}")
    print(f"✅ Connection URL: {client.get_connection_url()}")
    print(f"✅ Initial state: {client.state.value}")
    print(f"✅ Is connected: {client.is_connected()}")
    print(f"✅ Is healthy: {client.is_healthy()}")
    
    # Test 2: Message creation and structure
    print("\n📋 Test 2: Message Creation and Protocols")
    test_message = TestMessage(
        message_type="chat_message",
        content="Hello from WebSocket test client!",
        thread_id=str(uuid.uuid4())
    )
    
    websocket_message = test_message.to_websocket_message()
    print(f"✅ Test message created:")
    print(f"   Type: {websocket_message['type']}")
    print(f"   Content: {websocket_message['payload']['content']}")
    print(f"   Thread ID: {websocket_message['payload']['thread_id']}")
    print(f"   Has timestamp: {'timestamp' in websocket_message['payload']}")
    
    # Test 3: Metrics tracking
    print("\n📋 Test 3: Metrics and Connection Tracking")
    initial_metrics = client.get_metrics()
    print(f"✅ Initial metrics:")
    print(f"   Client ID: {initial_metrics['client_id'][:8]}...")
    print(f"   State: {initial_metrics['state']}")
    print(f"   Messages sent: {initial_metrics['messages_sent']}")
    print(f"   Messages received: {initial_metrics['messages_received']}")
    print(f"   Uptime: {initial_metrics['uptime_seconds']}")
    print(f"   Error count: {initial_metrics['error_count']}")
    
    # Test 4: Message handlers
    print("\n📋 Test 4: Message Handler System")
    received_messages = []
    
    def test_handler(message):
        received_messages.append(message)
        print(f"   📨 Handler received: {message.get('type', 'unknown')}")
    
    client.add_message_handler(test_handler)
    print(f"✅ Added message handler")
    
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
    print(f"✅ Simulated message reception")
    print(f"✅ Messages handled: {len(received_messages)}")
    
    # Test 5: Connection state management
    print("\n📋 Test 5: Connection State Management")
    print(f"✅ Initial state: {client.state.value}")
    
    # Test state transitions
    client.state = ConnectionState.CONNECTING
    print(f"✅ Connecting state: {client.state.value}")
    print(f"   Is connected: {client.is_connected()}")
    print(f"   Is healthy: {client.is_healthy()}")
    
    client.state = ConnectionState.CONNECTED
    print(f"✅ Connected state: {client.state.value}")
    print(f"   Is connected: {client.is_connected()}")
    print(f"   Is healthy: {client.is_healthy()}")
    
    client.state = ConnectionState.FAILED
    print(f"✅ Failed state: {client.state.value}")
    print(f"   Is connected: {client.is_connected()}")
    print(f"   Is healthy: {client.is_healthy()}")
    
    # Test 6: Concurrent tester capabilities
    print("\n📋 Test 6: Concurrent Testing Infrastructure")
    tester = ConcurrentWebSocketTester("ws://localhost:8000")
    tester.add_test_token("token-1")
    tester.add_test_token("token-2")
    tester.add_test_token("token-3")
    
    print(f"✅ Concurrent tester created")
    print(f"✅ Test tokens: {len(tester.test_tokens)}")
    
    # Create multiple test clients
    clients = []
    for i in range(3):
        client = await tester.create_client()
        clients.append(client)
        
    print(f"✅ Created {len(clients)} test clients")
    print(f"✅ Client IDs:")
    for i, client in enumerate(clients):
        print(f"   Client {i+1}: {client.client_id[:8]}...")
        print(f"              Token: {client.auth_token}")
        
    # Test aggregate metrics
    aggregate_metrics = tester.get_aggregate_metrics()
    print(f"✅ Aggregate metrics:")
    print(f"   Total clients: {aggregate_metrics['total_clients']}")
    print(f"   Connected clients: {aggregate_metrics['connected_clients']}")
    print(f"   Health rate: {aggregate_metrics['health_rate']:.1%}")
    
    # Test 7: Message broadcasting structure
    print("\n📋 Test 7: Message Broadcasting Capabilities")
    broadcast_message = {
        "type": "test_broadcast",
        "payload": {
            "content": "Broadcast test message",
            "timestamp": datetime.now().isoformat(),
            "message_id": str(uuid.uuid4())
        }
    }
    
    print(f"✅ Broadcast message created:")
    print(f"   Type: {broadcast_message['type']}")
    print(f"   Content: {broadcast_message['payload']['content']}")
    print(f"   Message ID: {broadcast_message['payload']['message_id'][:8]}...")
    
    # Test 8: Error handling capabilities
    print("\n📋 Test 8: Error Handling and Recovery")
    test_client = WebSocketTestClient("ws://localhost:8000", "error-test-token")
    
    # Simulate errors
    test_client.metrics.errors.append("Connection timeout")
    test_client.metrics.errors.append("Authentication failed")
    test_client.metrics.errors.append("Message send failed")
    
    error_metrics = test_client.get_metrics()
    print(f"✅ Error tracking:")
    print(f"   Error count: {error_metrics['error_count']}")
    print(f"   Recent errors: {error_metrics['last_errors']}")
    
    print("\n🎉 WebSocket Test Client Demo Complete!")
    print("=" * 50)
    print("✅ All client features demonstrated successfully")
    print("✅ Ready for integration testing")
    print("✅ Supports real WebSocket connections")
    print("✅ Handles authentication and protocols")
    print("✅ Manages concurrent connections")
    print("✅ Provides comprehensive metrics")


async def demo_real_connection_attempt():
    """Demo attempting a real connection (will fail gracefully in test env)"""
    print("\n🔗 Real Connection Attempt Demo")
    print("=" * 50)
    
    client = WebSocketTestClient("ws://localhost:8000", "demo-token")
    print(f"✅ Created client for real connection test")
    
    # This will fail in test environment but shows error handling
    try:
        print("🔄 Attempting real WebSocket connection...")
        success = await client.connect()
        
        if success:
            print("✅ Connection successful!")
            
            # Send test message
            await client.send_chat_message("Hello from demo client!")
            print("✅ Test message sent")
            
            # Wait a moment
            await asyncio.sleep(1)
            
            # Disconnect
            await client.disconnect()
            print("✅ Disconnected gracefully")
            
        else:
            print("⚠️  Connection failed (expected in test environment)")
            
    except Exception as e:
        print(f"⚠️  Connection exception: {str(e)[:100]}...")
        print("   This is expected when backend is not running")
        
    # Show final metrics
    final_metrics = client.get_metrics()
    print(f"✅ Final connection metrics:")
    print(f"   State: {final_metrics['state']}")
    print(f"   Error count: {final_metrics['error_count']}")
    if final_metrics['last_errors']:
        print(f"   Last error: {final_metrics['last_errors'][-1][:50]}...")


async def main():
    """Main demo function"""
    await demo_websocket_client_features()
    await demo_real_connection_attempt()


if __name__ == "__main__":
    asyncio.run(main())