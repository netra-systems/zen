#!/usr/bin/env python3
"""Test staging site browsing and login functionality."""

import requests
import json
import time
from typing import Dict, List, Tuple
import sys
import io

# Set up UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_staging_endpoints() -> Dict[str, any]:
    """Test all staging endpoints and report status."""
    
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "endpoints": {},
        "errors": [],
        "warnings": []
    }
    
    # Define endpoints to test
    endpoints = [
        ("Frontend App", "https://app.staging.netrasystems.ai", "GET"),
        ("Frontend Login", "https://app.staging.netrasystems.ai/login", "GET"),
        ("Frontend Dashboard", "https://app.staging.netrasystems.ai/dashboard", "GET"),
        ("API Health", "https://api.staging.netrasystems.ai/health", "GET"),
        ("API Docs", "https://api.staging.netrasystems.ai/docs", "GET"),
        ("API Version", "https://api.staging.netrasystems.ai/api/version", "GET"),
        ("Auth Health", "https://auth.staging.netrasystems.ai/health", "GET"),
        ("Auth Google OAuth", "https://auth.staging.netrasystems.ai/auth/google", "GET"),
        ("WebSocket Endpoint", "https://api.staging.netrasystems.ai/ws", "GET"),
    ]
    
    print("=" * 70)
    print("STAGING SITE BROWSER TEST REPORT")
    print("=" * 70)
    print(f"Test Time: {results['timestamp']}")
    print("-" * 70)
    
    for name, url, method in endpoints:
        print(f"\nTesting: {name}")
        print(f"URL: {url}")
        
        try:
            response = requests.request(
                method, 
                url, 
                timeout=10,
                allow_redirects=False,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            
            status_code = response.status_code
            
            # Check response details
            endpoint_result = {
                "url": url,
                "status_code": status_code,
                "response_time": response.elapsed.total_seconds(),
                "headers": dict(response.headers),
                "content_type": response.headers.get("Content-Type", ""),
            }
            
            # Handle different status codes
            if status_code == 200:
                print(f"✓ SUCCESS: {status_code} - Response time: {response.elapsed.total_seconds():.2f}s")
                
                # Check for specific content
                if "application/json" in endpoint_result["content_type"]:
                    try:
                        json_data = response.json()
                        endpoint_result["json_response"] = json_data
                        print(f"  JSON Response: {json.dumps(json_data, indent=2)[:200]}...")
                    except:
                        pass
                        
            elif status_code in [301, 302, 303, 307, 308]:
                redirect_to = response.headers.get("Location", "Unknown")
                print(f"↻ REDIRECT: {status_code} -> {redirect_to}")
                endpoint_result["redirect_to"] = redirect_to
                
            elif status_code == 401:
                print(f"⚠ UNAUTHORIZED: {status_code} - Authentication required")
                results["warnings"].append(f"{name}: Requires authentication")
                
            elif status_code == 404:
                print(f"✗ NOT FOUND: {status_code}")
                results["errors"].append(f"{name}: Endpoint not found")
                
            elif status_code >= 500:
                print(f"✗ SERVER ERROR: {status_code}")
                results["errors"].append(f"{name}: Server error {status_code}")
                
            else:
                print(f"? UNEXPECTED: {status_code}")
                results["warnings"].append(f"{name}: Unexpected status {status_code}")
                
            results["endpoints"][name] = endpoint_result
            
        except requests.exceptions.Timeout:
            print(f"✗ TIMEOUT: Request timed out after 10 seconds")
            results["errors"].append(f"{name}: Timeout")
            results["endpoints"][name] = {"error": "timeout"}
            
        except requests.exceptions.ConnectionError as e:
            print(f"✗ CONNECTION ERROR: {str(e)[:100]}")
            results["errors"].append(f"{name}: Connection failed")
            results["endpoints"][name] = {"error": "connection_failed"}
            
        except Exception as e:
            print(f"✗ ERROR: {str(e)[:100]}")
            results["errors"].append(f"{name}: {str(e)[:50]}")
            results["endpoints"][name] = {"error": str(e)[:100]}
    
    # Test authentication flow
    print("\n" + "=" * 70)
    print("AUTHENTICATION FLOW TEST")
    print("-" * 70)
    
    # Test OAuth initiation
    print("\nTesting OAuth Flow:")
    try:
        oauth_response = requests.get(
            "https://auth.staging.netrasystems.ai/auth/google",
            allow_redirects=False,
            timeout=10
        )
        
        if oauth_response.status_code in [302, 303]:
            redirect_url = oauth_response.headers.get("Location", "")
            if "accounts.google.com" in redirect_url:
                print("✓ OAuth redirect to Google successful")
                print(f"  Redirect URL contains: accounts.google.com/o/oauth2/v2/auth")
                
                # Extract OAuth parameters
                if "client_id=" in redirect_url:
                    client_id_start = redirect_url.find("client_id=") + 10
                    client_id_end = redirect_url.find("&", client_id_start)
                    client_id = redirect_url[client_id_start:client_id_end]
                    print(f"  Client ID: {client_id[:20]}...")
                    
                if "redirect_uri=" in redirect_url:
                    redirect_uri_start = redirect_url.find("redirect_uri=") + 13
                    redirect_uri_end = redirect_url.find("&", redirect_uri_start)
                    redirect_uri = redirect_url[redirect_uri_start:redirect_uri_end]
                    print(f"  Callback URI: {redirect_uri}")
                    
            else:
                print(f"⚠ OAuth redirect unexpected: {redirect_url[:100]}")
                results["warnings"].append("OAuth redirect to unexpected location")
        else:
            print(f"✗ OAuth initiation failed: Status {oauth_response.status_code}")
            results["errors"].append("OAuth initiation failed")
            
    except Exception as e:
        print(f"✗ OAuth test failed: {str(e)[:100]}")
        results["errors"].append(f"OAuth test: {str(e)[:50]}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("-" * 70)
    print(f"Total Endpoints Tested: {len(endpoints)}")
    print(f"Successful: {sum(1 for r in results['endpoints'].values() if r.get('status_code') == 200)}")
    print(f"Redirects: {sum(1 for r in results['endpoints'].values() if r.get('status_code', 0) in [301, 302, 303, 307, 308])}")
    print(f"Errors: {len(results['errors'])}")
    print(f"Warnings: {len(results['warnings'])}")
    
    if results['errors']:
        print("\n❌ ERRORS FOUND:")
        for error in results['errors']:
            print(f"  - {error}")
    
    if results['warnings']:
        print("\n⚠️ WARNINGS:")
        for warning in results['warnings']:
            print(f"  - {warning}")
    
    # Check critical services
    print("\n" + "-" * 70)
    print("CRITICAL SERVICE STATUS:")
    
    api_healthy = results['endpoints'].get('API Health', {}).get('json_response', {}).get('status') == 'healthy'
    auth_healthy = results['endpoints'].get('Auth Health', {}).get('json_response', {}).get('status') == 'healthy'
    frontend_accessible = results['endpoints'].get('Frontend App', {}).get('status_code') == 200
    
    print(f"  API Service: {'✓ HEALTHY' if api_healthy else '✗ UNHEALTHY'}")
    print(f"  Auth Service: {'✓ HEALTHY' if auth_healthy else '✗ UNHEALTHY'}")
    print(f"  Frontend App: {'✓ ACCESSIBLE' if frontend_accessible else '✗ INACCESSIBLE'}")
    
    overall_health = api_healthy and auth_healthy and frontend_accessible
    
    print("\n" + "=" * 70)
    print(f"OVERALL STATUS: {'✓ STAGING OPERATIONAL' if overall_health else '✗ ISSUES DETECTED'}")
    print("=" * 70)
    
    return results

if __name__ == "__main__":
    try:
        results = test_staging_endpoints()
        sys.exit(0 if not results['errors'] else 1)
    except Exception as e:
        print(f"\n✗ CRITICAL ERROR: {e}")
        sys.exit(1)