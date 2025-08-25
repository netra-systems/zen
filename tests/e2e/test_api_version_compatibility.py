"""
E2E Test: API Version Compatibility and Backward Compatibility

This test validates that API versioning works correctly and maintains backward
compatibility for existing client integrations.

Business Value Justification (BVJ):
- Segment: All customer segments (affects existing integrations)
- Business Goal: Maintain customer trust through stable API contracts
- Value Impact: Prevents breaking changes that would disrupt customer workflows
- Strategic/Revenue Impact: API stability essential for customer retention and enterprise sales
"""

import asyncio
import aiohttp
import pytest
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from packaging import version

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_api_version_negotiation():
    """Test API version negotiation and header handling.
    
    This test should FAIL until proper API versioning is implemented.
    """
    
    backend_url = "http://localhost:8000"
    auth_service_url = "http://localhost:8001"
    
    versioning_failures = []
    
    # Test different API version formats
    version_test_cases = [
        {
            "version": "current",
            "header_format": "Accept-Version",
            "expected_response_header": "API-Version"
        },
        {
            "version": "1.0",
            "header_format": "API-Version", 
            "expected_response_header": "API-Version"
        },
        {
            "version": "2024-08-01",
            "header_format": "Accept-Version",
            "expected_response_header": "API-Version"
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        print("🔄 Testing API version negotiation...")
        
        for test_case in version_test_cases:
            version_str = test_case["version"]
            header_format = test_case["header_format"]
            expected_header = test_case["expected_response_header"]
            
            print(f"📋 Testing version {version_str} with {header_format} header...")
            
            # Test main backend API
            try:
                headers = {header_format: version_str}
                async with session.get(
                    f"{backend_url}/api/health",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    # Check if server acknowledges version
                    if expected_header not in response.headers:
                        versioning_failures.append(f"Backend missing {expected_header} header for version {version_str}")
                    else:
                        returned_version = response.headers[expected_header]
                        print(f"✅ Backend returned version: {returned_version}")
                    
                    # Check response format based on version
                    if response.status == 200:
                        data = await response.json()
                        
                        # Current API should have proper format
                        if version_str == "current":
                            if "status" not in data:
                                versioning_failures.append("Current API should include 'status' field")
                        
                        # Newer versions should have extended format
                        elif version_str in ["1.0", "2024-08-01"]:
                            if "version_info" not in data:
                                versioning_failures.append(f"Version {version_str} should include 'version_info' field")
                    else:
                        versioning_failures.append(f"Backend health endpoint failed for version {version_str}: {response.status}")
                        
            except Exception as e:
                versioning_failures.append(f"Backend version negotiation failed for {version_str}: {e}")
            
            # Test auth service API
            try:
                headers = {header_format: version_str}
                async with session.get(
                    f"{auth_service_url}/health",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if expected_header not in response.headers:
                        versioning_failures.append(f"Auth service missing {expected_header} header for version {version_str}")
                    else:
                        auth_version = response.headers[expected_header]
                        print(f"✅ Auth service returned version: {auth_version}")
                        
            except Exception as e:
                versioning_failures.append(f"Auth service version negotiation failed for {version_str}: {e}")
    
    if versioning_failures:
        failure_report = ["🔄 API Version Negotiation Failures:"]
        for failure in versioning_failures:
            failure_report.append(f"  - {failure}")
        
        pytest.fail(f"API version negotiation test failed:\n" + "\n".join(failure_report))
    
    print("✅ API version negotiation test passed")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_backward_compatibility_endpoints():
    """Test that deprecated endpoints still work with proper warnings.
    
    This test should FAIL until backward compatibility is properly implemented.
    """
    
    backend_url = "http://localhost:8000"
    compatibility_failures = []
    
    # Define deprecated endpoints that should still work
    deprecated_endpoints = [
        {
            "path": "/api/user/profile",
            "method": "GET",
            "new_path": "/api/user/profile",
            "deprecated_version": "legacy",
            "current_version": "current"
        },
        {
            "path": "/api/threads",
            "method": "GET", 
            "new_path": "/api/threads",
            "deprecated_version": "legacy",
            "current_version": "current"
        },
        {
            "path": "/api/agent/run_agent",
            "method": "POST",
            "new_path": "/api/agent/run_agent",
            "deprecated_version": "legacy",
            "current_version": "current"
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        print("⚠️ Testing backward compatibility for deprecated endpoints...")
        
        for endpoint in deprecated_endpoints:
            path = endpoint["path"]
            method = endpoint["method"].upper()
            new_path = endpoint["new_path"]
            
            print(f"🔍 Testing deprecated endpoint: {method} {path}")
            
            try:
                # Test deprecated endpoint
                if method == "GET":
                    async with session.get(
                        f"{backend_url}{path}",
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        await _check_deprecated_response(response, endpoint, compatibility_failures)
                        
                elif method == "POST":
                    test_data = {"test": "data"}
                    async with session.post(
                        f"{backend_url}{path}",
                        json=test_data,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        await _check_deprecated_response(response, endpoint, compatibility_failures)
                        
            except Exception as e:
                compatibility_failures.append(f"Deprecated endpoint {path} completely broken: {e}")
            
            # Test that new endpoint also works
            try:
                if method == "GET":
                    async with session.get(
                        f"{backend_url}{new_path}",
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 404:
                            compatibility_failures.append(f"New endpoint {new_path} not implemented")
                        else:
                            print(f"✅ New endpoint {new_path} working")
                            
            except Exception as e:
                compatibility_failures.append(f"New endpoint {new_path} failed: {e}")
    
    if compatibility_failures:
        failure_report = ["⚠️ Backward Compatibility Failures:"]
        for failure in compatibility_failures:
            failure_report.append(f"  - {failure}")
        
        pytest.fail(f"Backward compatibility test failed:\n" + "\n".join(failure_report))
    
    print("✅ Backward compatibility test passed")


async def _check_deprecated_response(response, endpoint, compatibility_failures):
    """Helper to check deprecated endpoint response."""
    path = endpoint["path"]
    
    # Should include deprecation warning header
    if "Deprecation" not in response.headers and "X-API-Deprecation" not in response.headers:
        compatibility_failures.append(f"Deprecated endpoint {path} missing deprecation warning header")
    
    # Should include sunset/replacement information
    if "Sunset" not in response.headers and "X-API-Replacement" not in response.headers:
        compatibility_failures.append(f"Deprecated endpoint {path} missing replacement information")
    
    # Should still return valid response (not just error)
    if response.status >= 500:
        compatibility_failures.append(f"Deprecated endpoint {path} returning server error: {response.status}")
    elif response.status == 410:  # Gone
        compatibility_failures.append(f"Deprecated endpoint {path} already removed (should be phased out gradually)")
    elif response.status in [200, 201, 202, 401, 403, 404]:  # Valid responses
        print(f"✅ Deprecated endpoint {path} still functional")
    else:
        compatibility_failures.append(f"Deprecated endpoint {path} unexpected status: {response.status}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_api_schema_evolution():
    """Test that API schemas evolve correctly without breaking existing clients.
    
    This test should FAIL until schema evolution is properly implemented.
    """
    
    backend_url = "http://localhost:8000"
    schema_failures = []
    
    # Test different API versions with schema changes
    schema_test_cases = [
        {
            "endpoint": "/api/user/profile",
            "version": "current",
            "required_fields": ["id", "email", "name"],
            "optional_fields": [],
            "forbidden_fields": ["internal_id", "password_hash"]
        },
        {
            "endpoint": "/api/user/profile", 
            "version": "v2",
            "required_fields": ["id", "email", "name", "created_at"],
            "optional_fields": ["preferences", "subscription"],
            "forbidden_fields": ["password_hash", "internal_notes"]
        },
        {
            "endpoint": "/api/threads",
            "version": "current",
            "required_fields": ["id", "title", "created_at"],
            "optional_fields": ["messages"],
            "forbidden_fields": ["internal_metadata"]
        },
        {
            "endpoint": "/api/threads",
            "version": "v2", 
            "required_fields": ["id", "title", "created_at", "status"],
            "optional_fields": ["messages", "agents", "metadata"],
            "forbidden_fields": ["internal_metadata", "debug_info"]
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        print("📋 Testing API schema evolution...")
        
        for test_case in schema_test_cases:
            endpoint = test_case["endpoint"]
            version = test_case["version"]
            required_fields = test_case["required_fields"]
            optional_fields = test_case["optional_fields"]
            forbidden_fields = test_case["forbidden_fields"]
            
            print(f"🔍 Testing {endpoint} schema for version {version}")
            
            try:
                headers = {"Accept-Version": version}
                async with session.get(
                    f"{backend_url}{endpoint}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Handle both single object and array responses
                        if isinstance(data, list) and len(data) > 0:
                            item = data[0]
                        elif isinstance(data, dict):
                            item = data
                        else:
                            schema_failures.append(f"{endpoint} v{version}: Invalid response format")
                            continue
                        
                        # Check required fields
                        for field in required_fields:
                            if field not in item:
                                schema_failures.append(f"{endpoint} v{version}: Missing required field '{field}'")
                        
                        # Check forbidden fields are not present
                        for field in forbidden_fields:
                            if field in item:
                                schema_failures.append(f"{endpoint} v{version}: Contains forbidden field '{field}'")
                        
                        # Ensure backward compatibility (current fields work)
                        if version == "v2":
                            current_case = next((tc for tc in schema_test_cases if tc["endpoint"] == endpoint and tc["version"] == "current"), None)
                            if current_case:
                                for current_field in current_case["required_fields"]:
                                    if current_field not in item:
                                        schema_failures.append(f"{endpoint} v2: Backward compatibility broken - missing current field '{current_field}'")
                        
                        print(f"✅ Schema validation passed for {endpoint} v{version}")
                        
                    elif response.status == 404:
                        schema_failures.append(f"{endpoint} v{version}: Endpoint not found")
                    elif response.status == 401:
                        print(f"⚠️ {endpoint} v{version}: Requires authentication (acceptable)")
                    else:
                        schema_failures.append(f"{endpoint} v{version}: Unexpected status {response.status}")
                        
            except Exception as e:
                schema_failures.append(f"{endpoint} v{version}: Request failed - {e}")
    
    if schema_failures:
        failure_report = ["📋 API Schema Evolution Failures:"]
        for failure in schema_failures:
            failure_report.append(f"  - {failure}")
        
        pytest.fail(f"API schema evolution test failed:\n" + "\n".join(failure_report))
    
    print("✅ API schema evolution test passed")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_content_negotiation():
    """Test API content negotiation for different response formats.
    
    This test should FAIL until content negotiation is properly implemented.
    """
    
    backend_url = "http://localhost:8000"
    negotiation_failures = []
    
    # Test different content types
    content_test_cases = [
        {
            "accept_header": "application/json",
            "expected_content_type": "application/json",
            "should_work": True
        },
        {
            "accept_header": "application/vnd.api+json",
            "expected_content_type": "application/vnd.api+json", 
            "should_work": False  # May not be implemented yet
        },
        {
            "accept_header": "text/xml",
            "expected_content_type": "text/xml",
            "should_work": False  # May not be implemented yet
        },
        {
            "accept_header": "application/hal+json",
            "expected_content_type": "application/hal+json",
            "should_work": False  # May not be implemented yet
        }
    ]
    
    test_endpoints = [
        "/api/health",
        "/api/user/profile", 
        "/api/threads"
    ]
    
    async with aiohttp.ClientSession() as session:
        print("🔄 Testing content negotiation...")
        
        for endpoint in test_endpoints:
            for test_case in content_test_cases:
                accept_header = test_case["accept_header"]
                expected_content_type = test_case["expected_content_type"]
                should_work = test_case["should_work"]
                
                print(f"📋 Testing {endpoint} with Accept: {accept_header}")
                
                try:
                    headers = {"Accept": accept_header}
                    async with session.get(
                        f"{backend_url}{endpoint}",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        
                        actual_content_type = response.headers.get("Content-Type", "").split(";")[0]
                        
                        if should_work:
                            if response.status == 406:  # Not Acceptable
                                negotiation_failures.append(f"{endpoint}: Should support {accept_header} but returned 406")
                            elif actual_content_type != expected_content_type:
                                negotiation_failures.append(f"{endpoint}: Expected {expected_content_type}, got {actual_content_type}")
                            else:
                                print(f"✅ {endpoint} correctly negotiated {accept_header}")
                        else:
                            if response.status == 406:
                                print(f"ℹ️ {endpoint} correctly rejected unsupported {accept_header}")
                            elif response.status == 200 and actual_content_type == expected_content_type:
                                print(f"🎉 {endpoint} unexpectedly supports {accept_header}!")
                            else:
                                # Default behavior is acceptable for unsupported types
                                print(f"ℹ️ {endpoint} handled unsupported {accept_header} gracefully")
                                
                except Exception as e:
                    if should_work:
                        negotiation_failures.append(f"{endpoint} content negotiation failed for {accept_header}: {e}")
    
    if negotiation_failures:
        failure_report = ["🔄 Content Negotiation Failures:"]
        for failure in negotiation_failures:
            failure_report.append(f"  - {failure}")
        
        pytest.fail(f"Content negotiation test failed:\n" + "\n".join(failure_report))
    
    print("✅ Content negotiation test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])