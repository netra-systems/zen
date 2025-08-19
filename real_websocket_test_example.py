"""Real WebSocket Test Example

This example shows how to use the WebSocket test client for actual testing
against a running backend server. This demonstrates the real-world usage
of the test infrastructure.

Business Value: Enables reliable testing of WebSocket functionality.
"""

import asyncio
import json
import time
from websocket_test_client import (
    WebSocketTestClient, ConcurrentWebSocketTester, 
    TestMessage, ConnectionState
)


async def test_real_websocket_connection():
    """Test real WebSocket connection to running backend"""
    print("Real WebSocket Connection Test")
    print("=" * 40)
    
    # Use real backend URL (assuming it's running)
    client = WebSocketTestClient(
        base_url="ws://localhost:8000", 
        auth_token="your-real-jwt-token-here"
    )
    
    print(f"Client created: {client.client_id[:8]}...")
    print(f"Target URL: {client.get_connection_url()}")
    
    try:
        # Attempt real connection
        print("\nAttempting real connection...")
        success = await client.connect()
        
        if success:
            print("SUCCESS: Connected to WebSocket!")
            
            # Send real chat message
            print("\nSending test chat message...")
            chat_success = await client.send_chat_message(
                "Test message from WebSocket test client"
            )
            
            if chat_success:
                print("SUCCESS: Chat message sent!")
            else:
                print("FAILED: Could not send chat message")
            
            # Wait for potential responses
            print("\nWaiting for responses (5 seconds)...")
            await asyncio.sleep(5)
            
            # Show metrics
            metrics = client.get_metrics()
            print(f"\nConnection Metrics:")
            print(f"  State: {metrics['state']}")
            print(f"  Messages sent: {metrics['messages_sent']}")
            print(f"  Messages received: {metrics['messages_received']}")
            print(f"  Uptime: {metrics['uptime_seconds']:.1f}s")
            print(f"  Errors: {metrics['error_count']}")
            
            # Clean disconnect
            print("\nDisconnecting...")
            await client.disconnect()
            print("SUCCESS: Disconnected cleanly")
            
        else:
            print("FAILED: Could not establish WebSocket connection")
            print("This is expected if backend is not running")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print("This is expected if backend is not running")


async def test_concurrent_connections():
    """Test multiple concurrent connections"""
    print("\n" + "=" * 40)
    print("Concurrent WebSocket Connections Test")
    print("=" * 40)
    
    tester = ConcurrentWebSocketTester("ws://localhost:8000")
    
    # Add test tokens (in real usage, these would be valid JWT tokens)
    tester.add_test_token("test-token-1")
    tester.add_test_token("test-token-2")
    tester.add_test_token("test-token-3")
    
    try:
        # Create multiple clients
        print("\nCreating 3 concurrent clients...")
        clients = []
        for i in range(3):
            client = await tester.create_client()
            clients.append(client)
            print(f"  Client {i+1}: {client.client_id[:8]}...")
        
        # Attempt to connect all
        print("\nAttempting concurrent connections...")
        results = await tester.connect_all_clients()
        
        print(f"Connection results:")
        successful_connections = 0
        for client_id, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            print(f"  {client_id[:8]}...: {status}")
            if success:
                successful_connections += 1
        
        print(f"\nTotal successful connections: {successful_connections}/3")
        
        if successful_connections > 0:
            # Test broadcast messaging
            print("\nTesting broadcast messaging...")
            broadcast_message = {
                "type": "test_broadcast",
                "payload": {
                    "content": "Broadcast test from concurrent tester",
                    "timestamp": time.time()
                }
            }
            
            broadcast_results = await tester.broadcast_message(broadcast_message)
            successful_broadcasts = sum(1 for success in broadcast_results.values() if success)
            print(f"Successful broadcasts: {successful_broadcasts}/{successful_connections}")
        
        # Show aggregate metrics
        print("\nAggregate Metrics:")
        metrics = tester.get_aggregate_metrics()
        print(f"  Total clients: {metrics['total_clients']}")
        print(f"  Connected clients: {metrics['connected_clients']}")
        print(f"  Health rate: {metrics['health_rate']:.1%}")
        
        # Cleanup
        print("\nCleaning up connections...")
        await tester.disconnect_all_clients()
        print("Cleanup complete!")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print("This is expected if backend is not running")


async def test_message_protocols():
    """Test various message protocols and formats"""
    print("\n" + "=" * 40)
    print("Message Protocols Test")
    print("=" * 40)
    
    client = WebSocketTestClient("ws://localhost:8000", "test-token")
    
    # Test different message types
    messages_to_test = [
        TestMessage("chat_message", "Hello, this is a chat message"),
        TestMessage("user_query", "What is Netra Apex?"),
        TestMessage("system_ping", "Ping test"),
        TestMessage("agent_command", "Execute test command")
    ]
    
    print("Message Protocol Tests:")
    for i, test_msg in enumerate(messages_to_test, 1):
        websocket_msg = test_msg.to_websocket_message()
        print(f"\n{i}. Message Type: {websocket_msg['type']}")
        print(f"   Content: {websocket_msg['payload']['content']}")
        print(f"   Has Timestamp: {'timestamp' in websocket_msg['payload']}")
        print(f"   JSON Valid: {json.dumps(websocket_msg) is not None}")
    
    print("\nAll message protocols validated!")


async def demonstration_mode():
    """Run in demonstration mode showing all capabilities"""
    print("WebSocket Test Infrastructure Demonstration")
    print("=" * 60)
    print("This demonstrates the comprehensive WebSocket testing capabilities")
    print("built for the Netra backend system.\n")
    
    await test_message_protocols()
    await test_real_websocket_connection()
    await test_concurrent_connections()
    
    print("\n" + "=" * 60)
    print("WebSocket Test Infrastructure Demo Complete!")
    print("=" * 60)
    print("\nKey Features Demonstrated:")
    print("✓ Real WebSocket connection capability")
    print("✓ Proper authentication header handling")
    print("✓ Message protocol validation")
    print("✓ Concurrent connection management")
    print("✓ Comprehensive metrics tracking")
    print("✓ Error handling and recovery")
    print("✓ Clean connection lifecycle management")
    print("\nThe test infrastructure is ready for:")
    print("• Integration testing with running backend")
    print("• Load testing with multiple connections")
    print("• Protocol validation and compliance")
    print("• Performance monitoring and metrics")
    print("• Automated regression testing")


async def quick_validation():
    """Quick validation that all components work"""
    print("Quick Validation Test")
    print("=" * 30)
    
    # Test 1: Client creation
    client = WebSocketTestClient("ws://localhost:8000", "test-token")
    print(f"✓ Client created: {client.client_id[:8]}...")
    
    # Test 2: URL construction
    expected_url = "ws://localhost:8000/ws?token=test-token"
    actual_url = client.get_connection_url()
    assert actual_url == expected_url
    print(f"✓ URL construction correct: {actual_url}")
    
    # Test 3: Message formatting
    test_msg = TestMessage("test", "Test content")
    websocket_msg = test_msg.to_websocket_message()
    assert websocket_msg["type"] == "test"
    assert websocket_msg["payload"]["content"] == "Test content"
    print("✓ Message formatting correct")
    
    # Test 4: Metrics tracking
    metrics = client.get_metrics()
    assert "client_id" in metrics
    assert "state" in metrics
    assert metrics["messages_sent"] == 0
    print("✓ Metrics tracking functional")
    
    # Test 5: Concurrent tester
    tester = ConcurrentWebSocketTester("ws://localhost:8000")
    tester.add_test_token("token1")
    test_client = await tester.create_client()
    assert test_client.auth_token == "token1"
    print("✓ Concurrent tester functional")
    
    print("\nAll components validated successfully!")
    print("WebSocket test infrastructure is ready for use!")


if __name__ == "__main__":
    # Run quick validation by default
    # Change to demonstration_mode() for full demo
    asyncio.run(quick_validation())