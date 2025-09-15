#!/usr/bin/env python3
"""
Test script to reproduce Issue #1174 using E2E test endpoint
This script tests the auth service with E2E test authentication
"""
import asyncio
import json
import logging
import os
import sys
import requests
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_auth_with_e2e_endpoint():
    """Test using the E2E test auth endpoint"""

    auth_base_url = "https://auth.staging.netrasystems.ai"
    e2e_endpoint = f"{auth_base_url}/auth/e2e/test-auth"
    validate_endpoint = f"{auth_base_url}/auth/validate-token-and-get-user"

    # Try to get E2E bypass key from environment or use a test value
    e2e_bypass_key = os.environ.get("E2E_OAUTH_SIMULATION_KEY", "test-key-for-e2e")

    logger.info(f"Testing E2E endpoint: {e2e_endpoint}")

    try:
        # Get token from E2E test endpoint
        headers = {"X-E2E-Bypass-Key": e2e_bypass_key}
        e2e_data = {
            "email": "test@staging.netrasystems.ai",
            "name": "Test User",
            "permissions": ["read", "write"]
        }

        logger.info(f"Getting E2E token...")
        e2e_response = requests.post(e2e_endpoint, json=e2e_data, headers=headers, timeout=10)
        logger.info(f"E2E response status: {e2e_response.status_code}")
        logger.info(f"E2E response: {e2e_response.text[:300]}...")

        if e2e_response.status_code == 200:
            e2e_result = e2e_response.json()
            access_token = e2e_result.get("access_token")

            if access_token:
                logger.info(f"Got access token: {access_token[:20]}...")

                # Now test the validate-token-and-get-user endpoint that's failing in issue #1174
                validate_data = {"token": access_token}

                logger.info(f"Testing validate endpoint with token...")
                validate_response = requests.post(
                    validate_endpoint,
                    json=validate_data,
                    timeout=10
                )

                logger.info(f"Validate response status: {validate_response.status_code}")
                logger.info(f"Validate response: {validate_response.text}")

                # Parse the response
                if validate_response.status_code == 200:
                    try:
                        validate_data = validate_response.json()
                        logger.info(f"Validation result: {json.dumps(validate_data, indent=2)}")

                        if validate_data.get("valid") == False:
                            logger.error(f"ISSUE #1174 REPRODUCED: {validate_data.get('error')}")
                        else:
                            logger.info("Validation successful!")
                    except Exception as e:
                        logger.error(f"Failed to parse validation response: {e}")
                else:
                    logger.error(f"HTTP {validate_response.status_code} but issue says 200 - possible status code bug")

            else:
                logger.error("No access token in E2E response")
        else:
            logger.error(f"E2E auth failed: {e2e_response.status_code} - {e2e_response.text}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

async def test_simple_validate_endpoint():
    """Test the validate endpoint with a clearly invalid token to see response format"""

    auth_base_url = "https://auth.staging.netrasystems.ai"
    validate_endpoint = f"{auth_base_url}/auth/validate-token-and-get-user"

    logger.info(f"Testing validate endpoint with invalid token...")

    try:
        # Test with invalid token
        validate_data = {"token": "invalid-token-test"}

        validate_response = requests.post(
            validate_endpoint,
            json=validate_data,
            timeout=10
        )

        logger.info(f"Invalid token response status: {validate_response.status_code}")
        logger.info(f"Invalid token response: {validate_response.text}")

        # Check if this matches the issue description
        if validate_response.status_code == 200:
            try:
                response_data = validate_response.json()
                if response_data.get("valid") == False and "Invalid token or user not found" in response_data.get("error", ""):
                    logger.info("✓ This matches the issue description format")
                else:
                    logger.info(f"Different error format: {response_data}")
            except Exception as e:
                logger.error(f"Failed to parse response: {e}")

    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    logger.info("=== Testing Issue #1174: Authentication Problem with E2E Endpoint ===")

    # Test with invalid token first to see format
    logger.info("\n1. Testing with invalid token to see response format...")
    asyncio.run(test_simple_validate_endpoint())

    # Test with E2E endpoint
    logger.info("\n2. Testing with E2E test authentication...")
    asyncio.run(test_auth_with_e2e_endpoint())

    logger.info("\n=== Test Complete ===")