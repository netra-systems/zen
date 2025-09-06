"""
Test to reproduce agent_started event not being sent issue.
Uses Five Whys methodology to investigate root cause.
"""
import asyncio
import json
import websockets
import requests
import time
from typing import Dict, List, Optional
from datetime import datetime
from netra_backend.app.core.agent_registry import AgentRegistry
from shared.isolated_environment import IsolatedEnvironment

# Test configuration
API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"
AUTH_URL = "http://localhost:8081"

class AgentStartedEventTester:
    """Test harness for verifying agent_started WebSocket events."""
    
    def __init__(self):
        self.received_events: List[Dict] = []
        self.agent_started_events: List[Dict] = []
        self.ws_connection = None
        self.token = None
        
    async def connect_websocket(self) -> bool:
        """Establish WebSocket connection and listen for events."""
        try:
            # Connect without auth for development
            print(f"[{datetime.now()}] Connecting to WebSocket at {WS_URL}...")
            self.ws_connection = await websockets.connect(WS_URL)
            print(f"[{datetime.now()}] WebSocket connected successfully")
            return True
        except Exception as e:
            print(f"[{datetime.now()}] Failed to connect WebSocket: {e}")
            return False
    
    async def listen_for_events(self, duration: int = 10):
        """Listen for WebSocket events for specified duration."""
        print(f"[{datetime.now()}] Listening for events for {duration} seconds...")
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                # Set timeout to avoid blocking forever
                message = await asyncio.wait_for(
                    self.ws_connection.recv(), 
                    timeout=0.5
                )
                
                event = json.loads(message)
                self.received_events.append(event)
                
                print(f"[{datetime.now()}] Received event: {event.get('type', 'unknown')}")
                
                # Check if it's an agent_started event
                if event.get('type') == 'agent_started':
                    self.agent_started_events.append(event)
                    print(f"[{datetime.now()}] ✓ AGENT_STARTED EVENT RECEIVED!")
                    print(f"  Payload: {json.dumps(event.get('payload', {}), indent=2)}")
                    
            except asyncio.TimeoutError:
                # No message received, continue listening
                continue
            except websockets.exceptions.ConnectionClosed:
                print(f"[{datetime.now()}] WebSocket connection closed")
                break
            except Exception as e:
                print(f"[{datetime.now()}] Error receiving message: {e}")
                continue
    
    def send_chat_message(self, message: str) -> Optional[Dict]:
        """Send a chat message via HTTP API."""
        try:
            print(f"[{datetime.now()}] Sending chat message: '{message}'")
            
            # Send message to chat endpoint
            response = requests.post(
                f"{API_URL}/api/v2/chat",
                json={
                    "message": message,
                    "thread_id": None  # Let backend create new thread
                },
                headers={
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                print(f"[{datetime.now()}] Chat message sent successfully")
                return response.json()
            else:
                print(f"[{datetime.now()}] Failed to send chat message: {response.status_code}")
                print(f"  Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"[{datetime.now()}] Error sending chat message: {e}")
            return None
    
    async def run_test(self):
        """Run the complete test sequence."""
        print("\n" + "="*60)
        print("AGENT_STARTED EVENT TEST - FIVE WHYS ANALYSIS")
        print("="*60 + "\n")
        
        # Step 1: Connect to WebSocket
        if not await self.connect_websocket():
            print("❌ Test failed: Could not connect to WebSocket")
            return False
        
        # Step 2: Start listening task
        listen_task = asyncio.create_task(self.listen_for_events(duration=15))
        
        # Step 3: Wait a bit for connection to stabilize
        await asyncio.sleep(1)
        
        # Step 4: Send test messages
        test_messages = [
            "What are the top 3 ways to optimize my AI costs?",
            "Analyze my current AI infrastructure",
            "Help me reduce my LLM API expenses"
        ]
        
        for msg in test_messages:
            self.send_chat_message(msg)
            await asyncio.sleep(2)  # Wait between messages
        
        # Step 5: Wait for listening to complete
        await listen_task
        
        # Step 6: Analyze results
        print("\n" + "="*60)
        print("TEST RESULTS AND FIVE WHYS ANALYSIS")
        print("="*60)
        
        self.analyze_results()
        
        # Close WebSocket connection
        if self.ws_connection:
            await self.ws_connection.close()
        
        return len(self.agent_started_events) > 0
    
    def analyze_results(self):
        """Analyze test results using Five Whys methodology."""
        print(f"\nTotal events received: {len(self.received_events)}")
        print(f"Agent_started events received: {len(self.agent_started_events)}")
        
        # List all event types received
        event_types = {}
        for event in self.received_events:
            event_type = event.get('type', 'unknown')
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        print("\nEvent type breakdown:")
        for event_type, count in event_types.items():
            print(f"  - {event_type}: {count}")
        
        # Five Whys Analysis
        print("\n" + "-"*40)
        print("FIVE WHYS ANALYSIS")
        print("-"*40)
        
        if len(self.agent_started_events) == 0:
            print("\n❌ PROBLEM: No agent_started events received\n")
            
            print("WHY #1: Why are agent_started events not received?")
            if len(self.received_events) == 0:
                print("  → No WebSocket events received at all")
                print("  → Possible WebSocket connection issue")
            else:
                print("  → Other events received, but not agent_started")
                print("  → Event might not be sent or might be filtered")
            
            print("\nWHY #2: Why might the event not be sent?")
            print("  → Backend might not be sending the event")
            print("  → Event might be sent with wrong type name")
            print("  → Event might be blocked by middleware")
            
            print("\nWHY #3: Why would backend not send the event?")
            print("  → Agent execution might not be triggered")
            print("  → WebSocket bridge might not be initialized")
            print("  → Event emission might be failing silently")
            
            print("\nWHY #4: Why would agent execution not trigger?")
            print("  → Chat message might not reach agent supervisor")
            print("  → Agent registry might not be configured")
            print("  → Execution engine might not have WebSocket bridge")
            
            print("\nWHY #5: Why would execution engine lack WebSocket bridge?")
            print("  → Dependency injection might be failing")
            print("  → Bridge initialization might be incomplete")
            print("  → Request-scoped context might be missing")
            
        else:
            print(f"\n✅ SUCCESS: {len(self.agent_started_events)} agent_started events received")
            for i, event in enumerate(self.agent_started_events, 1):
                print(f"\nEvent #{i}:")
                print(f"  Timestamp: {event.get('timestamp', 'N/A')}")
                print(f"  Payload: {json.dumps(event.get('payload', {}), indent=4)}")


async def main():
    """Main test runner."""
    tester = AgentStartedEventTester()
    success = await tester.run_test()
    
    print("\n" + "="*60)
    if success:
        print("✅ TEST PASSED: agent_started events are being sent")
    else:
        print("❌ TEST FAILED: agent_started events are NOT being sent")
        print("\nRECOMMENDED ACTIONS:")
        print("1. Check backend logs for WebSocket bridge initialization")
        print("2. Verify AgentRegistry.set_websocket_manager() is called")
        print("3. Check ExecutionEngine has WebSocketNotifier")
        print("4. Verify agent supervisor is processing chat messages")
        print("5. Check for any error logs during agent execution")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())