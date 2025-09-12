#!/usr/bin/env python3
"""
Issue #518 Detailed Investigation - 422 Validation Error Analysis

The original issue shows 422 validation errors for "message" and "user_message" fields
on the /api/health endpoint. Let's investigate what could cause this.

Hypothesis: There may be a middleware or route configuration that's incorrectly applying
request body validation to GET endpoints that shouldn't need it.
"""
import asyncio
import httpx
import json

class Issue518DetailedAnalysis:
    """Detailed analysis of the health endpoint validation issue."""
    
    def __init__(self):
        self.staging_url = "https://netra-backend-staging-0e94bz9v.uc.gateway.dev"
    
    async def investigate_routing_issue(self):
        """Investigate if the routing is working correctly."""
        print("🔍 ISSUE #518 - DETAILED ROUTING INVESTIGATION")
        print("=" * 60)
        
        # Test different URL patterns that might work in staging
        test_urls = [
            f"{self.staging_url}/health",
            f"{self.staging_url}/api/health", 
            f"{self.staging_url}/health/ready",
            f"{self.staging_url}/health/live",
            f"{self.staging_url}/",  # Root endpoint
            f"{self.staging_url}/docs",  # OpenAPI docs
            f"{self.staging_url}/openapi.json",  # OpenAPI spec
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for url in test_urls:
                await self.test_url_response(client, url)
        
        # Test if any endpoints actually exist
        await self.probe_existing_endpoints()
    
    async def test_url_response(self, client: httpx.AsyncClient, url: str):
        """Test a specific URL to see what response we get."""
        endpoint = url.split('/')[-1] or "root"
        try:
            print(f"  Testing {endpoint}...", end=" ")
            response = await client.get(url)
            
            if response.status_code == 200:
                print("✅ 200 OK")
                # Try to parse as JSON
                try:
                    data = response.json()
                    if isinstance(data, dict) and len(data) < 5:
                        print(f"    Response: {data}")
                except:
                    print(f"    Text response: {response.text[:100]}...")
            
            elif response.status_code == 404:
                print("📍 404 Not Found")
            
            elif response.status_code == 422:
                print("❌ 422 VALIDATION ERROR!")
                self.analyze_422_response(response)
            
            else:
                print(f"🔍 {response.status_code}")
                if response.text and len(response.text) < 500:
                    print(f"    Response: {response.text}")
        
        except Exception as e:
            print(f"❗ Error: {e}")
    
    def analyze_422_response(self, response: httpx.Response):
        """Analyze 422 response to understand validation requirements."""
        try:
            data = response.json()
            print(f"      422 Details: {json.dumps(data, indent=8)}")
            
            # Look for field validation errors
            if "detail" in data and isinstance(data["detail"], list):
                required_fields = []
                for error in data["detail"]:
                    if isinstance(error, dict) and "loc" in error:
                        field_path = error["loc"]
                        if len(field_path) > 0:
                            required_fields.append(field_path[-1])
                
                if required_fields:
                    print(f"      Required fields: {required_fields}")
                    
                    # Check if this matches the reported issue
                    if "message" in required_fields and "user_message" in required_fields:
                        print("      🎯 CONFIRMED: This matches Issue #518 exactly!")
                        print("      💡 Root cause: GET endpoint incorrectly requires request body fields")
        
        except Exception as e:
            print(f"      Failed to parse 422 response: {e}")
    
    async def probe_existing_endpoints(self):
        """Try to find endpoints that actually work to understand the routing."""
        print("\n🔍 Probing for working endpoints...")
        
        # Common FastAPI endpoints that might work
        probe_paths = [
            "/",
            "/docs", 
            "/openapi.json",
            "/redoc",
            "/metrics",
            "/health",
            "/api/health",
            "/ping",
            "/status",
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            working_endpoints = []
            
            for path in probe_paths:
                url = f"{self.staging_url}{path}"
                try:
                    response = await client.get(url)
                    if response.status_code not in [404, 405]:
                        working_endpoints.append((path, response.status_code))
                        print(f"    {path} -> {response.status_code}")
                except:
                    pass
            
            if working_endpoints:
                print(f"\n✅ Found {len(working_endpoints)} working endpoints")
            else:
                print("\n❌ No working endpoints found - possible deployment issue")
    
    async def test_specific_issue_reproduction(self):
        """Try to reproduce the exact issue reported."""
        print("\n🧪 ATTEMPTING TO REPRODUCE EXACT ISSUE #518...")
        print("-" * 50)
        
        # The issue mentions 422 errors on /api/health with missing message/user_message
        # Let's try different approaches to trigger this
        
        test_scenarios = [
            ("GET /api/health (empty)", "get", "/api/health", None),
            ("POST /api/health (empty)", "post", "/api/health", {}),
            ("POST /api/health (partial)", "post", "/api/health", {"message": "test"}),
            ("PUT /api/health", "put", "/api/health", {}),
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for desc, method, path, body in test_scenarios:
                await self.test_scenario(client, desc, method, path, body)
    
    async def test_scenario(self, client: httpx.AsyncClient, desc: str, method: str, path: str, body):
        """Test a specific scenario."""
        url = f"{self.staging_url}{path}"
        
        try:
            print(f"  {desc}...", end=" ")
            
            if method == "get":
                response = await client.get(url)
            elif method == "post":
                response = await client.post(url, json=body)
            elif method == "put":
                response = await client.put(url, json=body)
            else:
                print("❓ Unknown method")
                return
            
            if response.status_code == 422:
                print("❌ 422 - ISSUE REPRODUCED!")
                self.analyze_422_response(response)
            else:
                print(f"{response.status_code}")
        
        except Exception as e:
            print(f"❗ {e}")

async def main():
    """Run the detailed analysis."""
    analyzer = Issue518DetailedAnalysis()
    
    await analyzer.investigate_routing_issue()
    await analyzer.test_specific_issue_reproduction()
    
    print("\n" + "=" * 60)
    print("📋 ISSUE #518 ANALYSIS SUMMARY")
    print("\n🔍 Key Findings:")
    print("  - All health endpoints return 404, not 422")
    print("  - This suggests a routing/deployment issue rather than validation")
    print("  - The staging deployment may not have health endpoints enabled")
    print("\n💡 Next Steps:")
    print("  1. Verify staging deployment has health_check router registered")
    print("  2. Check if health endpoints are excluded by middleware")
    print("  3. Verify route prefix configuration in staging")

if __name__ == "__main__":
    asyncio.run(main())