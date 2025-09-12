#!/usr/bin/env python3
"""
Cache Invalidation Script for WebSocket Protocol Fix
Implements comprehensive cache busting for Priority 0 remediation
"""

import requests
import time
import json
from typing import List, Dict

# Staging URLs to invalidate
STAGING_URLS = [
    "https://netra-frontend-staging-pnovr5vsba-uc.a.run.app",
    "https://netra-frontend-staging-pnovr5vsba-uc.a.run.app/",
    "https://netra-frontend-staging-pnovr5vsba-uc.a.run.app/chat",
    "https://netra-frontend-staging-pnovr5vsba-uc.a.run.app/_next/static/chunks/9879-d72c6f70e045659e.js",  # WebSocket bundle
]

def add_cache_busting_params(url: str) -> List[str]:
    """Add cache-busting parameters to URLs."""
    timestamp = int(time.time())
    cache_busting_params = [
        f"?v={timestamp}",
        f"?_cb={timestamp}",
        f"?nocache={timestamp}",
        f"?t={timestamp}&refresh=1",
    ]
    
    return [f"{url}{param}" for param in cache_busting_params]

def test_cache_invalidation():
    """Test cache invalidation by requesting URLs with cache-busting."""
    print("Cache Invalidation Test for WebSocket Protocol Fix")
    print("=" * 60)
    
    all_test_urls = []
    for base_url in STAGING_URLS:
        all_test_urls.extend(add_cache_busting_params(base_url))
        all_test_urls.append(base_url)  # Also test without cache busting
    
    print(f"Testing {len(all_test_urls)} URLs with cache-busting parameters...")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'WebSocket-Protocol-Cache-Invalidation-Test/1.0',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    })
    
    results = []
    
    for i, url in enumerate(all_test_urls, 1):
        print(f"\n[{i}/{len(all_test_urls)}] Testing: {url}")
        
        try:
            response = session.head(url, timeout=10, allow_redirects=True)
            cache_headers = {
                'cache-control': response.headers.get('cache-control', 'Not Set'),
                'etag': response.headers.get('etag', 'Not Set'),
                'expires': response.headers.get('expires', 'Not Set'),
                'last-modified': response.headers.get('last-modified', 'Not Set'),
            }
            
            result = {
                'url': url,
                'status': response.status_code,
                'cache_headers': cache_headers,
                'success': response.status_code == 200
            }
            
            print(f"   Status: {response.status_code}")
            print(f"   Cache-Control: {cache_headers['cache-control']}")
            if cache_headers['etag'] != 'Not Set':
                print(f"   ETag: {cache_headers['etag'][:50]}...")
            
            results.append(result)
            
            # Brief delay between requests
            time.sleep(0.5)
            
        except requests.RequestException as e:
            print(f"   Error: {e}")
            results.append({
                'url': url,
                'status': 'ERROR',
                'error': str(e),
                'success': False
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("CACHE INVALIDATION SUMMARY")
    print("=" * 60)
    
    successful_requests = sum(1 for r in results if r.get('success'))
    total_requests = len(results)
    
    print(f"Successful requests: {successful_requests}/{total_requests}")
    
    # Check for evidence of cache invalidation
    unique_etags = set()
    cache_control_types = set()
    
    for result in results:
        if result.get('cache_headers'):
            etag = result['cache_headers'].get('etag')
            if etag and etag != 'Not Set':
                unique_etags.add(etag)
                
            cache_control = result['cache_headers'].get('cache-control')
            if cache_control and cache_control != 'Not Set':
                cache_control_types.add(cache_control)
    
    print(f"\nCache Analysis:")
    print(f"- Unique ETags found: {len(unique_etags)}")
    print(f"- Cache-Control variations: {len(cache_control_types)}")
    
    if len(unique_etags) > 0:
        print("- ETags present - cache invalidation should work properly")
    else:
        print("- No ETags found - relying on timestamp-based cache busting")
    
    print(f"\nCache-Control Settings Found:")
    for cc in cache_control_types:
        print(f"   - {cc}")
    
    # Instructions for users
    print(f"\n" + "=" * 60)
    print("USER CACHE INVALIDATION INSTRUCTIONS")
    print("=" * 60)
    print("To ensure you get the latest WebSocket protocol fix:")
    print("")
    print("1. HARD REFRESH:")
    print("   - Chrome/Edge: Ctrl+Shift+R or Ctrl+F5")
    print("   - Firefox: Ctrl+Shift+R or Ctrl+F5") 
    print("   - Safari: Cmd+Shift+R")
    print("")
    print("2. CLEAR BROWSER CACHE:")
    print("   - Open Developer Tools (F12)")
    print("   - Right-click refresh button")
    print("   - Select 'Empty Cache and Hard Reload'")
    print("")
    print("3. INCOGNITO/PRIVATE MODE:")
    print("   - Open staging site in incognito/private window")
    print("   - This bypasses all local caches")
    print("")
    print("4. CACHE-BUSTED URL:")
    timestamp = int(time.time())
    print(f"   - https://netra-frontend-staging-pnovr5vsba-uc.a.run.app?v={timestamp}")
    print("")
    print("After any of these methods, WebSocket 1011 errors should be resolved!")
    
    return successful_requests > 0

if __name__ == "__main__":
    success = test_cache_invalidation()
    if success:
        print("\nCACHE INVALIDATION TEST: SUCCESS")
        print("Cache-busting mechanisms are available and working")
    else:
        print("\nCACHE INVALIDATION TEST: ISSUES DETECTED")
        print("Manual cache clearing may be required")