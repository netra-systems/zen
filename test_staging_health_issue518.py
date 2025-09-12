#!/usr/bin/env python3
"""
Issue #518 Staging Health Check 422 Validation Error Reproduction Script

This script reproduces and investigates the 422 validation errors reported for
/api/health endpoints in staging environment.

Expected behavior: GET /api/health should return health status without requiring any request body
Actual behavior: Returns 422 validation errors for "message" and "user_message" fields
"""
import asyncio
import logging
import httpx
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthEndpointTester:
    """Test staging health endpoints to identify the 422 validation error source."""
    
    def __init__(self):
        self.base_urls = [
            "https://netra-backend-staging-0e94bz9v.uc.gateway.dev",
            "http://localhost:8000",  # Local testing fallback
        ]
        self.health_endpoints = [
            "/health",           # Basic health endpoint
            "/api/health",       # API health endpoint (problematic one)
            "/api/health/ready", # Readiness probe
            "/api/health/live",  # Liveness probe
            "/api/health/startup", # Startup probe
            "/api/health/database", # Database health
            "/api/health/config",   # Health config
        ]
    
    async def test_all_endpoints(self):
        """Test all health endpoints to identify which ones have validation issues."""
        print("🔍 Testing Health Endpoints for Issue #518...")
        print("=" * 60)
        
        for base_url in self.base_urls:
            print(f"\nTesting base URL: {base_url}")
            print("-" * 40)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for endpoint in self.health_endpoints:
                    await self.test_endpoint(client, base_url, endpoint)
            
            break  # Only test first available URL
    
    async def test_endpoint(self, client: httpx.AsyncClient, base_url: str, endpoint: str):
        """Test a specific health endpoint."""
        full_url = f"{base_url}{endpoint}"
        
        try:
            # Test GET request (expected method for health checks)
            print(f"  GET {endpoint}...", end=" ")
            response = await client.get(full_url)
            
            if response.status_code == 200:
                print("✅ OK")
                # Show basic response info for successful requests
                try:
                    data = response.json()
                    if "status" in data:
                        print(f"    Status: {data.get('status', 'unknown')}")
                except:
                    print(f"    Response length: {len(response.text)} chars")
            
            elif response.status_code == 422:
                print("❌ 422 VALIDATION ERROR - Issue #518 Reproduced!")
                await self.analyze_422_error(response, endpoint)
            
            elif response.status_code == 404:
                print("📍 404 Not Found")
            
            elif response.status_code >= 500:
                print(f"⚠️  {response.status_code} Server Error")
                print(f"    {response.text[:200]}...")
            
            else:
                print(f"🔍 {response.status_code}")
                if len(response.text) < 200:
                    print(f"    Response: {response.text}")
        
        except httpx.ConnectError:
            print("🚫 Connection Failed")
        except httpx.TimeoutException:
            print("⏰ Timeout")
        except Exception as e:
            print(f"❗ Error: {e}")
    
    async def analyze_422_error(self, response: httpx.Response, endpoint: str):
        """Analyze 422 validation error details to understand root cause."""
        print(f"    🔍 Analyzing 422 error for {endpoint}:")
        
        try:
            error_data = response.json()
            print(f"    Error Response: {json.dumps(error_data, indent=6)}")
            
            # Look for validation details
            if "detail" in error_data:
                detail = error_data["detail"]
                if isinstance(detail, list):
                    print("    Validation Errors:")
                    for error in detail:
                        if isinstance(error, dict):
                            field = error.get("loc", ["unknown"])[-1]  # Get field name
                            msg = error.get("msg", "unknown error")
                            print(f"      - Field '{field}': {msg}")
                
            # Check if this is a Pydantic validation error expecting request body
            if "field required" in str(error_data).lower():
                print("    🎯 ROOT CAUSE: Health endpoint incorrectly expects request body validation")
                print("    💡 SOLUTION: Remove request body validation from GET health endpoints")
        
        except Exception as e:
            print(f"    Failed to parse error response: {e}")
            print(f"    Raw error: {response.text}")
    
    async def test_with_empty_body(self):
        """Test if sending empty JSON body helps (it shouldn't be needed)."""
        print("\n🧪 Testing with empty request body (incorrect but diagnostic)...")
        
        base_url = self.base_urls[0]
        endpoint = "/api/health"
        full_url = f"{base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Test POST with empty JSON (wrong method, but might reveal the issue)
                print(f"  POST {endpoint} with empty JSON...", end=" ")
                response = await client.post(full_url, json={})
                print(f"{response.status_code}")
                
                # Test GET with empty JSON (unusual but diagnostic)
                print(f"  GET {endpoint} with JSON body...", end=" ")
                response = await client.get(full_url, json={"message": "test", "user_message": "test"})
                print(f"{response.status_code}")
                
                if response.status_code == 200:
                    print("    ⚠️  Health endpoint accepts request body (this is incorrect design)")
                
            except Exception as e:
                print(f"❗ Error: {e}")

async def main():
    """Main test execution."""
    tester = HealthEndpointTester()
    await tester.test_all_endpoints()
    await tester.test_with_empty_body()
    
    print("\n" + "=" * 60)
    print("📋 ISSUE #518 ANALYSIS COMPLETE")
    print("\nExpected Findings:")
    print("✅ /health should return 200 OK")  
    print("❌ /api/health returns 422 expecting 'message'/'user_message' fields")
    print("\n💡 Recommended Fix:")
    print("   Check for incorrect request body validation on GET /api/health endpoint")
    print("   Health endpoints should not require any request body parameters")

if __name__ == "__main__":
    asyncio.run(main())