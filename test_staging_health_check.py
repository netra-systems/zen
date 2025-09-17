#!/usr/bin/env python3
"""
Quick Staging Health Check - Post SSOT Test Deployment Validation
"""
import asyncio
import httpx
import json

async def check_staging_health():
    """Check staging health using correct URLs from deployment output"""
    
    # URLs from actual deployment output
    staging_urls = [
        "https://staging.netrasystems.ai",  # Load balancer URL (preferred)
        "https://netra-backend-staging-pnovr5vsba-uc.a.run.app",  # Direct Cloud Run URL from deployment
    ]
    
    health_endpoints = [
        "/health",
        "/api/health", 
    ]
    
    print("🔍 POST-DEPLOYMENT STAGING HEALTH CHECK")
    print("=" * 60)
    print("PURPOSE: Verify SSOT test upgrades didn't break staging")
    print()
    
    for base_url in staging_urls:
        print(f"Testing: {base_url}")
        print("-" * 40)
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                for endpoint in health_endpoints:
                    url = f"{base_url}{endpoint}"
                    try:
                        response = await client.get(url)
                        status = response.status_code
                        print(f"  GET {endpoint}... {status} {response.reason_phrase}")
                        
                        if status == 200:
                            try:
                                data = response.json()
                                print(f"    ✅ Health: {data.get('status', 'unknown')}")
                                if data.get('websocket'):
                                    print(f"    🔌 WebSocket: {data['websocket'].get('status', 'unknown')}")
                            except Exception as e:
                                print(f"    📝 Response: {response.text[:100]}...")
                        elif status in [503, 502]:
                            print(f"    ⚠️  Service unavailable (may be starting up)")
                        elif status == 404:
                            print(f"    ❌ Endpoint not found")
                        else:
                            print(f"    ❌ Unexpected status")
                            
                    except Exception as e:
                        print(f"  GET {endpoint}... ❌ Error: {str(e)}")
                
        except Exception as e:
            print(f"  Connection failed: {e}")
        
        print()

    print("=" * 60)
    print("ANALYSIS:")
    print("- 200 OK = Service healthy, SSOT changes didn't break staging")
    print("- 503/502 = Service starting up after deployment")
    print("- 404 = Routing issue")
    print("- Connection error = Network/DNS issue")

if __name__ == "__main__":
    asyncio.run(check_staging_health())