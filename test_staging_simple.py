"""Simple staging environment test script"""
import asyncio
import aiohttp
import json
from typing import Dict, Any

class StagingTester:
    def __init__(self):
        self.backend_url = "https://netra-backend-staging-701982941522.us-central1.run.app"
        self.auth_url = "https://netra-auth-service-701982941522.us-central1.run.app"
        self.frontend_url = "https://netra-frontend-staging-701982941522.us-central1.run.app"
        self.results = []
    
    async def test_service_health(self, name: str, url: str) -> Dict[str, Any]:
        """Test if a service is healthy"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{url}/health", timeout=10) as response:
                    status = response.status
                    body = await response.text()
                    try:
                        data = json.loads(body)
                    except:
                        data = body
                    
                    result = {
                        "service": name,
                        "url": url,
                        "status": status,
                        "healthy": status == 200,
                        "response": data
                    }
                    self.results.append(result)
                    return result
        except Exception as e:
            result = {
                "service": name,
                "url": url,
                "status": "error",
                "healthy": False,
                "error": str(e)
            }
            self.results.append(result)
            return result
    
    async def test_websocket_connection(self) -> Dict[str, Any]:
        """Test WebSocket connection"""
        import websockets
        ws_url = f"wss://netra-backend-staging-701982941522.us-central1.run.app/ws"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Send a test message
                await websocket.send(json.dumps({"type": "ping"}))
                
                # Wait for response with timeout
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                
                result = {
                    "service": "WebSocket",
                    "url": ws_url,
                    "status": "connected",
                    "healthy": True,
                    "response": response
                }
                self.results.append(result)
                return result
        except Exception as e:
            result = {
                "service": "WebSocket",
                "url": ws_url,
                "status": "error",
                "healthy": False,
                "error": str(e)
            }
            self.results.append(result)
            return result
    
    async def run_all_tests(self):
        """Run all staging tests"""
        print("=" * 60)
        print("STAGING ENVIRONMENT E2E TEST")
        print("=" * 60)
        
        # Test health endpoints
        print("\n1. Testing Service Health Endpoints...")
        print("-" * 40)
        
        backend_result = await self.test_service_health("Backend", self.backend_url)
        print(f"[OK] Backend: {'HEALTHY' if backend_result['healthy'] else 'FAILED'} (Status: {backend_result['status']})")
        
        auth_result = await self.test_service_health("Auth", self.auth_url)
        print(f"[OK] Auth: {'HEALTHY' if auth_result['healthy'] else 'FAILED'} (Status: {auth_result['status']})")
        
        frontend_result = await self.test_service_health("Frontend", self.frontend_url)
        print(f"[OK] Frontend: {'HEALTHY' if frontend_result['healthy'] else 'FAILED'} (Status: {frontend_result['status']})")
        
        # Test WebSocket
        print("\n2. Testing WebSocket Connection...")
        print("-" * 40)
        ws_result = await self.test_websocket_connection()
        print(f"[OK] WebSocket: {'CONNECTED' if ws_result['healthy'] else 'FAILED'}")
        if not ws_result['healthy'] and 'error' in ws_result:
            print(f"  Error: {ws_result['error']}")
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['healthy'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        
        if failed_tests > 0:
            print("\nFailed Services:")
            for result in self.results:
                if not result['healthy']:
                    print(f"  - {result['service']}: {result.get('error', result['status'])}")
        
        print("\n" + "=" * 60)
        
        # Return overall status
        return {
            "success": failed_tests == 0,
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "results": self.results
        }

async def main():
    tester = StagingTester()
    result = await tester.run_all_tests()
    
    # Exit with appropriate code
    exit(0 if result['success'] else 1)

if __name__ == "__main__":
    asyncio.run(main())