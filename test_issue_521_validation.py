#!/usr/bin/env python3
"""
Issue #521 Quick Validation Script

Rapid validation script to test if service authentication 403 errors are resolved
in the staging environment. This script can be run independently to quickly
assess the current status of Issue #521.

Usage:
    python test_issue_521_validation.py

Expected Results:
- PASS: Issue #521 is resolved, service authentication working
- FAIL: Issue #521 persists, 403 errors still occurring
"""

import requests
import json
import sys
import time
from typing import Dict, Any

# Staging environment configuration
STAGING_CONFIG = {
    'backend_url': 'https://netra-backend-staging-1234567890-uc.a.run.app',  # Update with actual URL
    'auth_url': 'https://netra-auth-staging-1234567890-uc.a.run.app',       # Update with actual URL
    'timeout': 30
}

def log_result(test_name: str, success: bool, details: str = ""):
    """Log test result with consistent formatting."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {test_name}")
    if details:
        print(f"    Details: {details}")

def test_service_health() -> bool:
    """Test that staging services are accessible and healthy."""
    print("\n🔍 Testing staging service health...")
    
    services = {
        'backend': f"{STAGING_CONFIG['backend_url']}/health",
        'auth': f"{STAGING_CONFIG['auth_url']}/health"
    }
    
    all_healthy = True
    
    for service_name, health_url in services.items():
        try:
            response = requests.get(health_url, timeout=STAGING_CONFIG['timeout'])
            success = response.status_code == 200
            
            log_result(f"{service_name.capitalize()} Service Health", 
                      success, 
                      f"Status: {response.status_code}")
            
            if not success:
                all_healthy = False
                print(f"    Response: {response.text[:200]}")
                
        except requests.exceptions.RequestException as e:
            log_result(f"{service_name.capitalize()} Service Health", False, f"Error: {str(e)}")
            all_healthy = False
    
    return all_healthy

def test_service_authentication() -> bool:
    """Test service-to-service authentication for Issue #521."""
    print("\n🔐 Testing service authentication (Issue #521 core test)...")
    
    # Test internal service endpoint that would trigger 403 if Issue #521 persists
    internal_endpoint = f"{STAGING_CONFIG['backend_url']}/internal/auth/validate"
    
    service_headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'service:netra-backend',
        'X-Service-Auth': 'internal'
    }
    
    try:
        response = requests.post(
            internal_endpoint,
            headers=service_headers,
            json={'test': 'issue_521_validation'},
            timeout=STAGING_CONFIG['timeout']
        )
        
        # Issue #521 specific check - MUST NOT be 403
        if response.status_code == 403:
            log_result("Service Authentication (Issue #521)", False,
                      f"Got 403 'Not authenticated' - Issue #521 PERSISTS")
            print(f"    Response: {response.text[:300]}")
            return False
        
        # Success codes or non-403 errors are acceptable
        success = response.status_code in [200, 201, 202, 401, 404]
        status_detail = f"Status: {response.status_code}"
        
        if response.status_code == 401:
            status_detail += " (401 Unauthorized - different from Issue #521 403 error)"
        elif response.status_code == 404:
            status_detail += " (Endpoint not found - auth layer working)"
        
        log_result("Service Authentication (Issue #521)", success, status_detail)
        
        return success
        
    except requests.exceptions.RequestException as e:
        log_result("Service Authentication (Issue #521)", False, f"Network error: {str(e)}")
        return False

def test_database_session_cascade() -> bool:
    """Test if Issue #5 (database sessions) is resolved after Issue #521 fix."""
    print("\n🗄️  Testing database session cascade resolution (Issue #5)...")
    
    # Test endpoint requiring database session creation
    db_endpoint = f"{STAGING_CONFIG['backend_url']}/api/v1/agents/status"
    
    try:
        response = requests.get(db_endpoint, timeout=STAGING_CONFIG['timeout'])
        
        # Should not get 403 (service auth) or 503 (database session failures)
        success = response.status_code not in [403, 503]
        
        details = f"Status: {response.status_code}"
        if response.status_code == 403:
            details += " (Service auth still failing - Issue #521 not resolved)"
        elif response.status_code == 503:
            details += " (Database sessions failing - Issue #5 cascade not resolved)"
        elif response.status_code in [200, 401, 404]:
            details += " (Database layer accessible)"
        
        log_result("Database Session Cascade (Issue #5)", success, details)
        
        return success
        
    except requests.exceptions.RequestException as e:
        log_result("Database Session Cascade (Issue #5)", False, f"Network error: {str(e)}")
        return False

def test_golden_path_validation() -> bool:
    """Test Golden Path endpoints to validate business functionality."""
    print("\n🎯 Testing Golden Path business functionality...")
    
    endpoints = [
        ('/api/v1/agents/list', 'Agent List'),
        ('/api/v1/health/comprehensive', 'Health Check'),
        ('/websocket/status', 'WebSocket Status')
    ]
    
    success_count = 0
    total_count = len(endpoints)
    
    for endpoint_path, endpoint_name in endpoints:
        endpoint_url = f"{STAGING_CONFIG['backend_url']}{endpoint_path}"
        
        try:
            response = requests.get(endpoint_url, timeout=15)
            
            # Success if not 403 (service auth) or 503 (service failure)
            success = response.status_code not in [403, 503]
            
            details = f"Status: {response.status_code}"
            if response.status_code == 403:
                details += " (Issue #521 service auth still failing)"
            
            log_result(f"Golden Path - {endpoint_name}", success, details)
            
            if success:
                success_count += 1
                
        except requests.exceptions.RequestException as e:
            log_result(f"Golden Path - {endpoint_name}", False, f"Error: {str(e)}")
    
    # Require majority success for overall Golden Path health
    golden_path_healthy = success_count / total_count >= 0.6
    
    log_result("Golden Path Overall", golden_path_healthy, 
              f"{success_count}/{total_count} endpoints healthy")
    
    return golden_path_healthy

def main():
    """Run Issue #521 validation suite."""
    print("🚀 Issue #521 Service Authentication Validation")
    print("=" * 60)
    
    start_time = time.time()
    
    # Run validation tests
    tests = [
        ("Service Health", test_service_health),
        ("Service Authentication", test_service_authentication),
        ("Database Cascade", test_database_session_cascade),
        ("Golden Path", test_golden_path_validation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ ERROR in {test_name}: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed_tests = [name for name, result in results if result]
    failed_tests = [name for name, result in results if not result]
    
    print(f"✅ Passed: {len(passed_tests)}")
    print(f"❌ Failed: {len(failed_tests)}")
    
    if failed_tests:
        print(f"\nFailed Tests: {', '.join(failed_tests)}")
    
    overall_success = len(failed_tests) == 0
    execution_time = time.time() - start_time
    
    print(f"\n🎯 OVERALL RESULT: {'✅ ISSUE #521 RESOLVED' if overall_success else '❌ ISSUE #521 PERSISTS'}")
    print(f"⏱️  Execution Time: {execution_time:.2f} seconds")
    
    # Exit with appropriate code
    sys.exit(0 if overall_success else 1)

if __name__ == '__main__':
    main()