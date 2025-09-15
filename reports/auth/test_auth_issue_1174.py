#!/usr/bin/env python3
"""
Test script to reproduce Issue #1174: Invalid token or user not found error
This script tests the auth service endpoint to understand the exact issue
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

async def test_auth_service_validateTokenAndGetUser():
    """Test the exact endpoint mentioned in issue #1174"""

    # Test the staging auth service endpoint
    auth_base_url = "https://auth.staging.netrasystems.ai"
    validate_endpoint = f"{auth_base_url}/auth/validate-token-and-get-user"

    logger.info(f"Testing endpoint: {validate_endpoint}")

    # First, let's get a valid token from the dev login endpoint
    try:
        dev_login_url = f"{auth_base_url}/auth/dev/login"
        logger.info(f"Getting dev token from: {dev_login_url}")

        dev_response = requests.post(dev_login_url, timeout=10)
        logger.info(f"Dev login response status: {dev_response.status_code}")
        logger.info(f"Dev login response: {dev_response.text[:200]}...")

        if dev_response.status_code == 200:
            dev_data = dev_response.json()
            access_token = dev_data.get("access_token")

            if access_token:
                logger.info(f"Got access token: {access_token[:20]}...")

                # Now test the validate-token-and-get-user endpoint
                validate_data = {"token": access_token}

                logger.info(f"Testing validate endpoint with token...")
                validate_response = requests.post(
                    validate_endpoint,
                    json=validate_data,
                    timeout=10
                )

                logger.info(f"Validate response status: {validate_response.status_code}")
                logger.info(f"Validate response: {validate_response.text}")

                # Also test with Authorization header
                logger.info(f"Testing validate endpoint with Authorization header...")
                headers = {"Authorization": f"Bearer {access_token}"}
                validate_response_auth = requests.post(
                    validate_endpoint,
                    headers=headers,
                    timeout=10
                )

                logger.info(f"Validate (auth header) response status: {validate_response_auth.status_code}")
                logger.info(f"Validate (auth header) response: {validate_response_auth.text}")

            else:
                logger.error("No access token in dev login response")
        else:
            logger.error(f"Dev login failed: {dev_response.status_code} - {dev_response.text}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

async def test_auth_service_health():
    """Test auth service health to ensure it's running"""

    auth_base_url = "https://auth.staging.netrasystems.ai"
    health_endpoint = f"{auth_base_url}/auth/health"

    try:
        response = requests.get(health_endpoint, timeout=10)
        logger.info(f"Health check status: {response.status_code}")
        logger.info(f"Health check response: {response.text}")

        if response.status_code == 200:
            health_data = response.json()
            logger.info(f"Auth service status: {health_data.get('status')}")
            logger.info(f"Database status: {health_data.get('database_status')}")

    except Exception as e:
        logger.error(f"Health check failed: {e}")

if __name__ == "__main__":
    logger.info("=== Testing Issue #1174: Authentication Problem ===")

    # Test auth service health first
    logger.info("\n1. Testing auth service health...")
    asyncio.run(test_auth_service_health())

    # Test the specific endpoint mentioned in the issue
    logger.info("\n2. Testing validate-token-and-get-user endpoint...")
    asyncio.run(test_auth_service_validateTokenAndGetUser())

    logger.info("\n=== Test Complete ===")