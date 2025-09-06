#!/usr/bin/env python3
"""Test GTM loading in dev and staging environments"""

import requests
import re
import json
from typing import Dict, List, Optional, Tuple
import sys
from shared.isolated_environment import IsolatedEnvironment

def test_gtm_loading(url: str, env_name: str) -> Tuple[bool, Dict[str, any]]:
    """Test if GTM is properly loaded on a given URL"""
    
    results = {
        "environment": env_name,
        "url": url,
        "gtm_found": False,
        "container_id": None,
        "script_tag_found": False,
        "noscript_tag_found": False,
        "data_layer_found": False,
        "errors": []
    }
    
    try:
        # Make request to the frontend
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        content = response.text
        
        # Check for GTM container ID in the HTML
        container_pattern = r'GTM-[A-Z0-9]+'
        container_match = re.search(container_pattern, content)
        if container_match:
            results["container_id"] = container_match.group()
            results["gtm_found"] = True
        
        # Check for GTM script tag
        script_pattern = r'googletagmanager\.com/gtm\.js\?id=GTM-[A-Z0-9]+'
        if re.search(script_pattern, content):
            results["script_tag_found"] = True
        
        # Check for noscript iframe
        noscript_pattern = r'googletagmanager\.com/ns\.html\?id=GTM-[A-Z0-9]+'
        if re.search(noscript_pattern, content):
            results["noscript_tag_found"] = True
        
        # Check for dataLayer initialization
        datalayer_pattern = r'window\.dataLayer\s*=\s*window\.dataLayer\s*\|\|\s*\[\]|dataLayer\s*=\s*\[\]'
        if re.search(datalayer_pattern, content):
            results["data_layer_found"] = True
        
        # Check for GTM environment variables in inline scripts
        env_pattern = r'NEXT_PUBLIC_GTM_CONTAINER_ID|NEXT_PUBLIC_GTM_ENABLED'
        if re.search(env_pattern, content):
            results["env_vars_referenced"] = True
        
        # Success if all critical elements are found
        success = (results["gtm_found"] and 
                  results["script_tag_found"] and 
                  results["container_id"] == "GTM-WKP28PNQ")
        
        return success, results
        
    except requests.exceptions.RequestException as e:
        results["errors"].append(f"Request failed: {str(e)}")
        return False, results
    except Exception as e:
        results["errors"].append(f"Unexpected error: {str(e)}")
        return False, results

def test_gtm_api(base_url: str, env_name: str) -> Dict[str, any]:
    """Test GTM-related API endpoints if they exist"""
    
    results = {
        "environment": env_name,
        "health_check": False,
        "gtm_config_endpoint": False
    }
    
    # Test health endpoint
    try:
        health_url = f"{base_url}/health" if "3000" not in base_url else f"{base_url.replace(':3000', ':8000')}/health"
        response = requests.get(health_url, timeout=5)
        results["health_check"] = response.status_code == 200
    except:
        pass
    
    return results

def main():
    """Main test runner"""
    
    print("="*60)
    print("GTM Loading Test Report")
    print("="*60)
    
    environments = [
        ("Development", "http://localhost:3001"),
        ("Staging", "https://frontend-fzr7uxqpxq-uc.a.run.app")  # Update with actual staging URL
    ]
    
    all_results = []
    
    for env_name, url in environments:
        print(f"\nTesting {env_name} environment...")
        print(f"URL: {url}")
        print("-" * 40)
        
        # Skip staging if not accessible
        if "staging" in env_name.lower() and "run.app" in url:
            print("Note: Replace with actual staging URL from GCP deployment")
            continue
        
        success, results = test_gtm_loading(url, env_name)
        all_results.append(results)
        
        # Print results
        print(f"[OK] GTM Found: {results['gtm_found']}")
        print(f"[OK] Container ID: {results['container_id']}")
        print(f"[OK] Script Tag: {results['script_tag_found']}")
        print(f"[OK] NoScript Tag: {results['noscript_tag_found']}")
        print(f"[OK] DataLayer: {results['data_layer_found']}")
        
        if results["errors"]:
            print(f"[ERROR] Errors: {', '.join(results['errors'])}")
        
        # Test API endpoints
        api_results = test_gtm_api(url, env_name)
        print(f"[OK] Health Check: {api_results['health_check']}")
        
        # Overall status
        if success:
            print(f"\n[SUCCESS] {env_name} GTM Configuration: WORKING")
        else:
            print(f"\n[FAIL] {env_name} GTM Configuration: ISSUES DETECTED")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for result in all_results:
        status = "PASS" if (result["gtm_found"] and result["script_tag_found"]) else "FAIL"
        print(f"{result['environment']}: {status}")
        if result["container_id"]:
            print(f"  Container ID: {result['container_id']}")
        if result["errors"]:
            print(f"  Errors: {', '.join(result['errors'])}")
    
    # Expected container ID check
    print("\n" + "-"*60)
    print("Expected Container ID: GTM-WKP28PNQ")
    print("This should match across all environments")
    
    # Exit with appropriate code
    all_passed = all(r["gtm_found"] and r["script_tag_found"] for r in all_results)
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()