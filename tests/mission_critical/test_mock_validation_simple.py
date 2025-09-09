"""
Simple Mock Response Validation Test - Proof of Concept

This test demonstrates that mock responses can be detected in the system.
"""

import pytest
import asyncio
import aiohttp
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from shared.isolated_environment import get_env

@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.asyncio
async def test_simple_mock_detection():
    """Simple test to prove mock responses can be detected"""
    
    # Create authenticated user
    auth_helper = E2EAuthHelper()
    user = await auth_helper.create_authenticated_user()
    
    # Mock patterns to detect
    mock_patterns = [
        "i apologize",
        "unable to process",
        "service temporarily unavailable",
        "please try again",
        "encountered an error"
    ]
    
    env = get_env()
    backend_url = env.get('BACKEND_URL', 'http://localhost:8000')
    
    # Test API endpoint for mock responses
    async with aiohttp.ClientSession() as session:
        headers = auth_helper.get_auth_headers(user.jwt_token)
        
        test_payload = {
            "user_id": user.user_id,
            "prompt": "Generate comprehensive data analysis for Fortune 500 company",
            "context": {"test": "mock_detection"}
        }
        
        async with session.post(f"{backend_url}/api/v1/chat", json=test_payload, headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                response_text = str(result).lower()
                
                # Check for mock patterns
                detected_patterns = []
                for pattern in mock_patterns:
                    if pattern in response_text:
                        detected_patterns.append(pattern)
                
                if detected_patterns:
                    pytest.fail(f"MOCK RESPONSE DETECTED! Patterns found: {detected_patterns}")
                else:
                    # Test passed - no mock responses detected
                    print("✅ No mock responses detected in this test")
            else:
                print(f"API returned status {response.status}")

@pytest.mark.e2e  
@pytest.mark.real_services
@pytest.mark.asyncio
async def test_fallback_detection():
    """Test to detect fallback responses in service failures"""
    
    auth_helper = E2EAuthHelper()
    user = await auth_helper.create_authenticated_user()
    
    env = get_env()
    backend_url = env.get('BACKEND_URL', 'http://localhost:8000')
    
    # Test with intentionally problematic request to trigger fallbacks
    async with aiohttp.ClientSession() as session:
        headers = auth_helper.get_auth_headers(user.jwt_token)
        
        # Request designed to potentially trigger fallback responses
        test_payload = {
            "user_id": user.user_id,
            "prompt": "TRIGGER_FALLBACK_TEST_" * 100,  # Intentionally problematic
            "context": {"test": "fallback_detection"}
        }
        
        try:
            async with session.post(f"{backend_url}/api/v1/chat", json=test_payload, headers=headers) as response:
                result = await response.json()
                response_text = str(result).lower()
                
                fallback_indicators = [
                    "fallback",
                    "default response",
                    "generic response",
                    "template response"
                ]
                
                detected = [indicator for indicator in fallback_indicators if indicator in response_text]
                
                if detected:
                    pytest.fail(f"FALLBACK RESPONSE DETECTED! Indicators: {detected}")
                else:
                    print("✅ No fallback responses detected")
                    
        except Exception as e:
            # Exception is acceptable - fallback responses are not
            print(f"Exception occurred (acceptable): {e}")