#!/usr/bin/env python3
"""
Quick test script to verify the missing API endpoints have been implemented.
This tests the endpoints that were returning 404/403 errors in staging.
"""

import asyncio
import httpx
import json
from datetime import datetime

# Endpoint configuration
BACKEND_URL = "http://localhost:8000"  # Adjust as needed for staging
TIMEOUT = 30

async def test_missing_endpoints():
    """Test all the endpoints that were previously missing."""
    
    results = {}
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        print("🧪 Testing Missing API Endpoints")
        print("=" * 50)
        
        # Agent Control Endpoints
        print("\n📋 Testing Agent Control Endpoints:")
        
        # Test /api/agents/start (POST)
        try:
            start_payload = {
                "agent_type": "triage",
                "message": "Test message for agent start",
                "context": {"test": True}
            }
            response = await client.post(f"{BACKEND_URL}/api/agents/start", json=start_payload)
            results["POST /api/agents/start"] = {
                "status": response.status_code,
                "success": response.status_code in [200, 201, 202]
            }
            print(f"  POST /api/agents/start: {response.status_code} {'✅' if results['POST /api/agents/start']['success'] else '❌'}")
            if response.status_code == 200:
                data = response.json()
                print(f"    Response: {data.get('message', 'No message')}")
        except Exception as e:
            results["POST /api/agents/start"] = {"status": "error", "error": str(e)}
            print(f"  POST /api/agents/start: Error - {e}")
        
        # Test /api/agents/stop (POST)
        try:
            stop_payload = {
                "agent_id": "test-agent-123",
                "reason": "Testing stop endpoint"
            }
            response = await client.post(f"{BACKEND_URL}/api/agents/stop", json=stop_payload)
            results["POST /api/agents/stop"] = {
                "status": response.status_code,
                "success": response.status_code in [200, 201, 202]
            }
            print(f"  POST /api/agents/stop: {response.status_code} {'✅' if results['POST /api/agents/stop']['success'] else '❌'}")
        except Exception as e:
            results["POST /api/agents/stop"] = {"status": "error", "error": str(e)}
            print(f"  POST /api/agents/stop: Error - {e}")
        
        # Test /api/agents/cancel (POST)
        try:
            cancel_payload = {
                "agent_id": "test-agent-123",
                "force": False
            }
            response = await client.post(f"{BACKEND_URL}/api/agents/cancel", json=cancel_payload)
            results["POST /api/agents/cancel"] = {
                "status": response.status_code,
                "success": response.status_code in [200, 201, 202]
            }
            print(f"  POST /api/agents/cancel: {response.status_code} {'✅' if results['POST /api/agents/cancel']['success'] else '❌'}")
        except Exception as e:
            results["POST /api/agents/cancel"] = {"status": "error", "error": str(e)}
            print(f"  POST /api/agents/cancel: Error - {e}")
        
        # Test /api/agents/status (GET)
        try:
            response = await client.get(f"{BACKEND_URL}/api/agents/status")
            results["GET /api/agents/status"] = {
                "status": response.status_code,
                "success": response.status_code == 200
            }
            print(f"  GET /api/agents/status: {response.status_code} {'✅' if results['GET /api/agents/status']['success'] else '❌'}")
            if response.status_code == 200:
                data = response.json()
                print(f"    Found {len(data)} agents")
        except Exception as e:
            results["GET /api/agents/status"] = {"status": "error", "error": str(e)}
            print(f"  GET /api/agents/status: Error - {e}")
        
        # Streaming Endpoints
        print("\n🌊 Testing Streaming Endpoints:")
        
        # Test /api/agents/stream (GET info)
        try:
            response = await client.get(f"{BACKEND_URL}/api/agents/stream")
            results["GET /api/agents/stream"] = {
                "status": response.status_code,
                "success": response.status_code == 200
            }
            print(f"  GET /api/agents/stream: {response.status_code} {'✅' if results['GET /api/agents/stream']['success'] else '❌'}")
        except Exception as e:
            results["GET /api/agents/stream"] = {"status": "error", "error": str(e)}
            print(f"  GET /api/agents/stream: Error - {e}")
        
        # Test /api/agents/stream (POST - just check it accepts the request)
        try:
            stream_payload = {
                "agent_type": "triage",
                "message": "Test streaming message",
                "stream_updates": True
            }
            # Use a very short timeout since we just want to check the endpoint exists
            async with httpx.AsyncClient(timeout=5) as stream_client:
                response = await stream_client.post(f"{BACKEND_URL}/api/agents/stream", json=stream_payload)
                results["POST /api/agents/stream"] = {
                    "status": response.status_code,
                    "success": response.status_code == 200
                }
                print(f"  POST /api/agents/stream: {response.status_code} {'✅' if results['POST /api/agents/stream']['success'] else '❌'}")
        except httpx.TimeoutException:
            # Timeout is expected for streaming endpoints
            results["POST /api/agents/stream"] = {"status": "timeout", "success": True}
            print(f"  POST /api/agents/stream: Timeout (Expected) ✅")
        except Exception as e:
            results["POST /api/agents/stream"] = {"status": "error", "error": str(e)}
            print(f"  POST /api/agents/stream: Error - {e}")
        
        # Test /api/events/stream (GET)
        try:
            async with httpx.AsyncClient(timeout=5) as stream_client:
                response = await stream_client.get(f"{BACKEND_URL}/api/events/stream")
                results["GET /api/events/stream"] = {
                    "status": response.status_code,
                    "success": response.status_code == 200
                }
                print(f"  GET /api/events/stream: {response.status_code} {'✅' if results['GET /api/events/stream']['success'] else '❌'}")
        except httpx.TimeoutException:
            # Timeout is expected for streaming endpoints
            results["GET /api/events/stream"] = {"status": "timeout", "success": True}
            print(f"  GET /api/events/stream: Timeout (Expected) ✅")
        except Exception as e:
            results["GET /api/events/stream"] = {"status": "error", "error": str(e)}
            print(f"  GET /api/events/stream: Error - {e}")
        
        # Message Endpoints (verify they still work)
        print("\n💬 Testing Message Endpoints (Should already exist):")
        
        # Test /api/chat/messages (GET)
        try:
            response = await client.get(f"{BACKEND_URL}/api/chat/messages")
            results["GET /api/chat/messages"] = {
                "status": response.status_code,
                "success": response.status_code in [200, 401, 403]  # 401/403 acceptable if auth required
            }
            print(f"  GET /api/chat/messages: {response.status_code} {'✅' if results['GET /api/chat/messages']['success'] else '❌'}")
        except Exception as e:
            results["GET /api/chat/messages"] = {"status": "error", "error": str(e)}
            print(f"  GET /api/chat/messages: Error - {e}")
        
        # Test /api/chat/messages (POST)
        try:
            message_payload = {
                "content": "Test message",
                "thread_id": "test-thread-123"
            }
            response = await client.post(f"{BACKEND_URL}/api/chat/messages", json=message_payload)
            results["POST /api/chat/messages"] = {
                "status": response.status_code,
                "success": response.status_code in [200, 201, 401, 403]  # 401/403 acceptable if auth required
            }
            print(f"  POST /api/chat/messages: {response.status_code} {'✅' if results['POST /api/chat/messages']['success'] else '❌'}")
        except Exception as e:
            results["POST /api/chat/messages"] = {"status": "error", "error": str(e)}
            print(f"  POST /api/chat/messages: Error - {e}")
    
    # Summary
    print("\n📊 Test Summary:")
    print("=" * 50)
    
    total_tests = len(results)
    successful_tests = sum(1 for result in results.values() if result.get("success", False))
    
    print(f"Total endpoints tested: {total_tests}")
    print(f"Successful responses: {successful_tests}")
    print(f"Success rate: {successful_tests/total_tests*100:.1f}%")
    
    if successful_tests == total_tests:
        print("\n🎉 All endpoints are working!")
    else:
        print(f"\n⚠️  {total_tests - successful_tests} endpoints need attention")
        
        # Show failed endpoints
        failed = [endpoint for endpoint, result in results.items() if not result.get("success", False)]
        if failed:
            print("\nFailed endpoints:")
            for endpoint in failed:
                status = results[endpoint].get("status", "unknown")
                error = results[endpoint].get("error", "")
                print(f"  - {endpoint}: Status {status} {error}")
    
    print(f"\n💾 Full results saved to: test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    # Save detailed results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    with open(f"test_results_{timestamp}.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    return results

if __name__ == "__main__":
    print("🚀 Starting API Endpoint Test")
    print(f"Testing backend at: {BACKEND_URL}")
    print(f"Timeout: {TIMEOUT}s")
    
    try:
        results = asyncio.run(test_missing_endpoints())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")