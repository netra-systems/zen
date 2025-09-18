#!/usr/bin/env python3
"""
Simple staging environment check for golden path and e2e tests
"""
import sys
import asyncio
import aiohttp
import time
from datetime import datetime

STAGING_URLS = [
    "https://staging.netrasystems.ai",
    "https://staging.netrasystems.ai/health", 
    "https://api-staging.netrasystems.ai/health"
]

async def check_endpoint(session, url, name):
    """Check a single endpoint."""
    start_time = time.time()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            duration = time.time() - start_time
            status = response.status
            content_type = response.headers.get('content-type', 'unknown')
            
            # Try to get content preview
            try:
                if 'json' in content_type:
                    content = await response.json()
                else:
                    content = await response.text()
                    content = content[:200] if content else ""
            except:
                content = "Could not parse content"
            
            print(f"✅ {name}: HTTP {status} in {duration:.2f}s")
            print(f"   Content-Type: {content_type}")
            print(f"   Content: {str(content)[:100]}...")
            return True, status, duration
            
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ {name}: Failed after {duration:.2f}s - {str(e)}")
        return False, None, duration

async def main():
    print("=" * 60)
    print("SIMPLE STAGING ENVIRONMENT HEALTH CHECK")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = []
    timeout = aiohttp.ClientTimeout(total=10)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for url in STAGING_URLS:
            name = url.split("/")[-1] if "/" in url else "root"
            result = await check_endpoint(session, url, f"{name} ({url})")
            results.append(result)
            print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    successful = sum(1 for r in results if r[0])
    total = len(results)
    
    print(f"Successful checks: {successful}/{total} ({successful/total*100:.1f}%)")
    
    if successful == 0:
        print("🚨 CRITICAL: All staging endpoints are down")
        return 1
    elif successful < total:
        print("⚠️  WARNING: Some staging endpoints are having issues")
        return 0
    else:
        print("✅ SUCCESS: All staging endpoints are responding")
        return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)