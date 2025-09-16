#!/usr/bin/env python3
"""
Basic staging connectivity test using httpx instead of websockets
This will test if the staging environment is reachable at all.
"""
import httpx
import time
from datetime import datetime

def test_staging_connectivity():
    """Test basic HTTP connectivity to staging"""
    print("=" * 60)
    print("STAGING CONNECTIVITY TEST")
    print("=" * 60)
    
    endpoints = [
        "https://staging.netrasystems.ai/health",
        "https://api-staging.netrasystems.ai/health", 
        "https://staging.netrasystems.ai",
        "https://api-staging.netrasystems.ai"
    ]
    
    for url in endpoints:
        print(f"\n[{datetime.now()}] Testing: {url}")
        start_time = time.time()
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                elapsed = time.time() - start_time
                
                print(f"[{datetime.now()}] ✅ Status: {response.status_code} in {elapsed:.2f}s")
                if response.status_code == 200:
                    content = response.text[:200]
                    print(f"Response: {content}...")
                    
        except httpx.TimeoutException:
            elapsed = time.time() - start_time
            print(f"[{datetime.now()}] ❌ Timeout after {elapsed:.2f}s")
            
        except httpx.ConnectError as e:
            elapsed = time.time() - start_time
            print(f"[{datetime.now()}] ❌ Connection error after {elapsed:.2f}s: {e}")
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[{datetime.now()}] ❌ Error after {elapsed:.2f}s: {e}")

if __name__ == "__main__":
    test_staging_connectivity()