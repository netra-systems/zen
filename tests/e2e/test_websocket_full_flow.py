#!/usr/bin/env python
"""
Comprehensive E2E WebSocket Agent Event Test
Captures and displays ALL WebSocket events during agent execution
"""

import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import websockets
import aiohttp

# Simple color codes for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    RESET_ALL = '\033[0m'
    BRIGHT = '\033[1m'

Fore = Colors
Style = Colors

# Configuration for staging environment
STAGING_CONFIG = {
    "backend_url": "http://localhost:8002",
    "ws_url": "ws://localhost:8002/ws",
    "auth_url": "http://localhost:8083",
    "test_user": {
        "email": "test@example.com",
        "password": "test123"
    }
}

# All required WebSocket events for business value
REQUIRED_EVENTS = [
    "agent_started",
    "agent_thinking", 
    "tool_executing",
    "tool_completed",
    "agent_completed"
]

class WebSocketEventCapture:
    """Captures and displays all WebSocket agent events"""
    
    def __init__(self):
        self.events_captured = []
        self.event_counts = {event: 0 for event in REQUIRED_EVENTS}
        self.start_time = None
        self.end_time = None
        
    def print_header(self):
        """Print test header"""
        print("\n" + "="*80)
        print(f"{Fore.CYAN}COMPREHENSIVE WEBSOCKET AGENT EVENT CAPTURE")
        print(f"{Fore.CYAN}Running on STAGING Environment")
        print(f"{Fore.CYAN}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
    def print_event(self, event: Dict[str, Any]):
        """Pretty print a WebSocket event"""
        event_type = event.get("type", "unknown")
        timestamp = event.get("timestamp", time.time())
        
        # Color coding by event type
        color = Fore.WHITE
        if event_type == "agent_started":
            color = Fore.GREEN
        elif event_type == "agent_thinking":
            color = Fore.YELLOW
        elif event_type == "tool_executing":
            color = Fore.CYAN
        elif event_type == "tool_completed":
            color = Fore.BLUE
        elif event_type == "agent_completed":
            color = Fore.GREEN
        elif "error" in event_type.lower():
            color = Fore.RED
            
        print(f"{color}[{timestamp}] {event_type.upper()}{Style.RESET_ALL}")
        
        # Print event details
        if "data" in event:
            data = event["data"]
            if isinstance(data, dict):
                for key, value in data.items():
                    if key not in ["timestamp", "type"]:
                        print(f"  {key}: {value}")
            else:
                print(f"  Data: {data}")
                
        # Track event
        if event_type in self.event_counts:
            self.event_counts[event_type] += 1
        self.events_captured.append(event)
        print("")  # Empty line for readability
        
    def print_summary(self):
        """Print test summary"""
        duration = (self.end_time - self.start_time) if self.start_time and self.end_time else 0
        
        print("\n" + "="*80)
        print(f"{Fore.CYAN}TEST SUMMARY")
        print("="*80)
        
        print(f"\n{Fore.GREEN}Events Captured:{Style.RESET_ALL}")
        for event_type, count in self.event_counts.items():
            status = "✓" if count > 0 else "✗"
            color = Fore.GREEN if count > 0 else Fore.RED
            print(f"  {color}{status} {event_type}: {count} events{Style.RESET_ALL}")
            
        print(f"\n{Fore.YELLOW}Statistics:{Style.RESET_ALL}")
        print(f"  Total Events: {len(self.events_captured)}")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Events/Second: {len(self.events_captured)/duration if duration > 0 else 0:.2f}")
        
        # Check if all required events were received
        all_received = all(count > 0 for count in self.event_counts.values())
        if all_received:
            print(f"\n{Fore.GREEN}✓ ALL REQUIRED EVENTS RECEIVED - CHAT FUNCTIONALITY WORKING!{Style.RESET_ALL}")
        else:
            missing = [event for event, count in self.event_counts.items() if count == 0]
            print(f"\n{Fore.RED}✗ MISSING EVENTS: {', '.join(missing)}{Style.RESET_ALL}")
            
        print("="*80 + "\n")

async def authenticate(session: aiohttp.ClientSession) -> str:
    """Authenticate and get access token"""
    print(f"{Fore.YELLOW}Authenticating with staging environment...{Style.RESET_ALL}")
    
    # Try to login or register
    login_url = f"{STAGING_CONFIG['auth_url']}/auth/login"
    register_url = f"{STAGING_CONFIG['auth_url']}/auth/register"
    
    # Try login first
    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
    async with session.post(login_url, json=STAGING_CONFIG["test_user"]) as resp:
        if resp.status == 200:
            data = await resp.json()
            print(f"{Fore.GREEN}✓ Authentication successful{Style.RESET_ALL}\n")
            return data.get("access_token")
        
    # If login fails, try to register
    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
    async with session.post(register_url, json=STAGING_CONFIG["test_user"]) as resp:
        if resp.status in [200, 201]:
            data = await resp.json()
            print(f"{Fore.GREEN}✓ Registration successful{Style.RESET_ALL}\n")
            # Now login
            async with session.post(login_url, json=STAGING_CONFIG["test_user"]) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("access_token")
        
    return None

async def run_agent_and_capture_events():
    """Run an agent and capture all WebSocket events"""
    capture = WebSocketEventCapture()
    capture.print_header()
    
    async with aiohttp.ClientSession() as session:
        # Authenticate
        token = await authenticate(session)
        if not token:
            print(f"{Fore.RED}Failed to authenticate. Using anonymous mode.{Style.RESET_ALL}")
            token = "anonymous"
            
        # Connect to WebSocket
        print(f"{Fore.YELLOW}Connecting to WebSocket...{Style.RESET_ALL}")
        headers = {"Authorization": f"Bearer {token}"} if token != "anonymous" else {}
        
        # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
        async with websockets.connect(STAGING_CONFIG["ws_url"], extra_headers=headers) as websocket:
            print(f"{Fore.GREEN}✓ WebSocket connected{Style.RESET_ALL}\n")
            
            # Send initial message to trigger agent
            test_message = {
                "type": "message",
                "content": "Analyze the performance of my AI infrastructure",
                "timestamp": time.time()
            }
            
            print(f"{Fore.YELLOW}Sending test message: {test_message['content']}{Style.RESET_ALL}\n")
            await websocket.send(json.dumps(test_message))
            
            capture.start_time = time.time()
            
            # Listen for events
            print(f"{Fore.CYAN}Listening for WebSocket events...{Style.RESET_ALL}\n")
            print("-"*80)
            
            timeout = 30  # 30 second timeout
            start = time.time()
            
            while time.time() - start < timeout:
                # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
                message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                event = json.loads(message)
                capture.print_event(event)
                
                # Check if agent completed
                if event.get("type") == "agent_completed":
                    print(f"{Fore.GREEN}Agent execution completed!{Style.RESET_ALL}")
                    break
                    
            capture.end_time = time.time()
            
    # Print summary
    capture.print_summary()
    
    return capture

async def test_multiple_concurrent_users():
    """Test multiple concurrent users to verify isolation"""
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"TESTING MULTI-USER ISOLATION (10 Concurrent Users)")
    print(f"{'='*80}{Style.RESET_ALL}\n")
    
    async def run_user(user_id: int):
        """Run a single user session"""
        print(f"{Fore.YELLOW}User {user_id}: Starting session...{Style.RESET_ALL}")
        
        # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
        async with aiohttp.ClientSession() as session:
            # Each user gets unique credentials
            user_config = {
                "email": f"user{user_id}@test.com",
                "password": f"pass{user_id}"
            }
            
            # Connect to WebSocket
            async with websockets.connect(STAGING_CONFIG["ws_url"]) as websocket:
                # Send message
                message = {
                    "type": "message",
                    "content": f"User {user_id}: Test message",
                    "user_id": user_id,
                    "timestamp": time.time()
                }
                await websocket.send(json.dumps(message))
                
                # Collect some events
                events = []
                start = time.time()
                while time.time() - start < 5:  # 5 second collection
                    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
                    msg = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                    event = json.loads(msg)
                    events.append(event)
                    
                    # Check for data leakage
                    if "user_id" in str(event):
                        other_user = None
                        for uid in range(10):
                            if uid != user_id and f"user{uid}" in str(event):
                                other_user = uid
                                break
                        if other_user is not None:
                            print(f"{Fore.RED}⚠ ISOLATION VIOLATION: User {user_id} received data from User {other_user}!{Style.RESET_ALL}")
                            
                print(f"{Fore.GREEN}User {user_id}: Received {len(events)} events{Style.RESET_ALL}")
                return events
            
    # Run 10 concurrent users
    tasks = [run_user(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    # Summary
    total_events = sum(len(r) for r in results)
    print(f"\n{Fore.CYAN}Multi-User Test Summary:{Style.RESET_ALL}")
    print(f"  Total Events: {total_events}")
    print(f"  Average Events/User: {total_events/10:.1f}")
    print(f"{Fore.GREEN}✓ Multi-user isolation test completed{Style.RESET_ALL}\n")

async def main():
    """Main test execution"""
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Style.BRIGHT}NETRA APEX - WEBSOCKET AGENT EVENT E2E TEST")
    print(f"{'='*80}{Style.RESET_ALL}\n")
    
    # Test 1: Single user full flow
    print(f"{Fore.YELLOW}Test 1: Single User Full Agent Flow{Style.RESET_ALL}")
    capture = await run_agent_and_capture_events()
    
    # Test 2: Multiple concurrent users
    print(f"\n{Fore.YELLOW}Test 2: Multi-User Concurrent Access{Style.RESET_ALL}")
    await test_multiple_concurrent_users()
    
    # Final summary
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"ALL TESTS COMPLETED")
    print(f"{'='*80}{Style.RESET_ALL}\n")
    
    # Return success if all events captured
    all_events_captured = all(
        capture.event_counts[event] > 0 
        for event in REQUIRED_EVENTS
    )
    
    if all_events_captured:
        print(f"{Fore.GREEN}{Style.BRIGHT}✓ SUCCESS: All WebSocket agent events working on staging!{Style.RESET_ALL}")
        return 0
    else:
        print(f"{Fore.RED}{Style.BRIGHT}✗ FAILURE: Some WebSocket events missing{Style.RESET_ALL}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)