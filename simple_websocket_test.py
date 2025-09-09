"""
Simple WebSocket Service Test
Tests basic WebSocket connectivity and service status
"""

import asyncio
import json
import requests


class SimpleWebSocketTest:
    def __init__(self):
        self.auth_service_url = "http://localhost:8083"
        self.backend_service_url = "http://localhost:8000"
        
    def test_infrastructure_services(self):
        """Test that infrastructure services are running."""
        print("=== Testing Infrastructure Services ===")
        
        # Test auth service
        try:
            auth_response = requests.get(f"{self.auth_service_url}/health", timeout=5)
            print(f"Auth Service: {auth_response.status_code} - {auth_response.json()}")
            auth_healthy = auth_response.status_code == 200
        except Exception as e:
            print(f"Auth Service: FAILED - {e}")
            auth_healthy = False
            
        # Test backend service  
        try:
            backend_response = requests.get(f"{self.backend_service_url}/health", timeout=5)
            print(f"Backend Service: {backend_response.status_code} - {backend_response.json()}")
            backend_healthy = backend_response.status_code == 200
        except Exception as e:
            print(f"Backend Service: EXPECTED FAILURE - {e}")
            backend_healthy = False
            
        return auth_healthy, backend_healthy
    
    async def test_websocket_connection(self):
        """Test WebSocket connection attempt."""
        print("=== Testing WebSocket Connection ===")
        
        try:
            import websockets
            async with websockets.connect("ws://localhost:8000/ws", timeout=5) as ws:
                print("WebSocket connection successful!")
                return True
        except Exception as e:
            print(f"WebSocket connection failed (EXPECTED): {e}")
            return False
    
    def generate_report(self, auth_healthy, backend_healthy, websocket_connected):
        """Generate test report."""
        print("\n=== WEBSOCKET REMEDIATION TEST REPORT ===")
        print(f"Auth Service:       {'PASS' if auth_healthy else 'FAIL'}")
        print(f"Backend Service:    {'PASS' if backend_healthy else 'EXPECTED FAIL'}")  
        print(f"WebSocket Connect:  {'PASS' if websocket_connected else 'EXPECTED FAIL'}")
        
        print("\n=== CURRENT STATUS ===")
        if auth_healthy:
            print("✓ Infrastructure services are running correctly")
        else:
            print("✗ Infrastructure services need attention")
            
        if not backend_healthy:
            print("! Backend service not running - this is the expected issue")
            print("! Need to fix Alpine lz4 dependency and restart backend")
            
        print("\n=== NEXT STEPS FOR REMEDIATION ===")
        print("1. Fix Alpine backend image lz4 dependency issue")
        print("2. Start backend service on port 8000")
        print("3. Test WebSocket endpoint /ws with real connection")
        print("4. Validate authentication integration")
        print("5. Test error event delivery")


async def main():
    tester = SimpleWebSocketTest()
    
    # Test services
    auth_healthy, backend_healthy = tester.test_infrastructure_services()
    
    # Test WebSocket
    websocket_connected = await tester.test_websocket_connection()
    
    # Generate report
    tester.generate_report(auth_healthy, backend_healthy, websocket_connected)


if __name__ == "__main__":
    asyncio.run(main())