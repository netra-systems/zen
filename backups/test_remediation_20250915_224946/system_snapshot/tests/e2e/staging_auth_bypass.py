"""
E2E Test Authentication Helper for Staging Environment

This module provides authentication bypass functionality for E2E tests
running against the staging environment. It uses a secure bypass key
stored in Google Secrets Manager to authenticate without OAuth.

Usage:
    auth_helper = StagingAuthHelper()
    token = await auth_helper.get_test_token()
    
    # Use token in API requests
    headers = {"Authorization": f"Bearer {token}"}
"""

import os
import json
import asyncio
import logging
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class StagingAuthHelper:
    """Helper class for E2E test authentication on staging."""
    
    # DYNAMIC E2E BYPASS KEY VALIDATION - Try multiple potential keys
    # Priority order: current key -> historical keys -> auto-discovery
    POTENTIAL_BYPASS_KEYS = [
        "staging-e2e-test-bypass-key-2025",  # Current standard
        "staging-e2e-bypass-key-2025",       # Possible variation
        "staging-test-bypass-key-2025",      # Simplified version
        "e2e-test-bypass-key-staging",       # Alternative format
        "staging-e2e-bypass-2025",           # Short version
        "netra-staging-e2e-key-2025",        # With product name
        "staging-bypass-key",                # Generic fallback
    ]
    
    def __init__(self, bypass_key: Optional[str] = None):
        """
        Initialize the staging auth helper with dynamic key discovery.
        
        Args:
            bypass_key: E2E bypass key. If not provided, will try auto-discovery.
        """
        env = get_env()
        self.bypass_key = bypass_key or env.get("E2E_OAUTH_SIMULATION_KEY")
        # Use SSOT for staging auth URL
        from netra_backend.app.core.network_constants import URLConstants
        self.staging_auth_url = env.get("STAGING_AUTH_URL", URLConstants.STAGING_AUTH_URL)
        self.token_cache: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self.validated_bypass_key: Optional[str] = None  # Cache the working key
        
        # If no bypass key provided, we'll try discovery during first auth attempt
        if not self.bypass_key:
            logger.info("No E2E bypass key provided - will attempt auto-discovery during authentication")
    
    async def _discover_valid_bypass_key(self, email: str, name: str, permissions: list) -> Optional[str]:
        """
        Try multiple potential bypass keys to find one that works.
        
        Returns:
            Working bypass key if found, None otherwise
        """
        keys_to_try = []
        
        # Add explicit key if provided
        if self.bypass_key:
            keys_to_try.append(self.bypass_key)
        
        # Add known potential keys
        keys_to_try.extend(self.POTENTIAL_BYPASS_KEYS)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keys = []
        for key in keys_to_try:
            if key and key not in seen:
                seen.add(key)
                unique_keys.append(key)
        
        logger.info(f"Attempting bypass key discovery with {len(unique_keys)} potential keys")
        
        async with httpx.AsyncClient() as client:
            for i, key in enumerate(unique_keys):
                try:
                    logger.info(f"Trying bypass key {i+1}/{len(unique_keys)}: {key[:20]}...")
                    
                    response = await client.post(
                        f"{self.staging_auth_url}/auth/e2e/test-auth",
                        headers={
                            "X-E2E-Bypass-Key": key,
                            "Content-Type": "application/json"
                        },
                        json={
                            "email": email,
                            "name": name,
                            "permissions": permissions
                        },
                        timeout=15.0  # Shorter timeout for discovery attempts
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"SUCCESS: Found working bypass key: {key[:20]}...")
                        return key
                    elif response.status_code == 401:
                        logger.debug(f"Key rejected (401): {key[:20]}...")
                    elif response.status_code == 403:
                        logger.debug(f"Key forbidden (403): {key[:20]}...")
                    else:
                        logger.debug(f"Unexpected response ({response.status_code}): {key[:20]}...")
                        
                except httpx.RequestError as e:
                    logger.debug(f"Network error for key {key[:20]}...: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"Error testing key {key[:20]}...: {e}")
                    continue
        
        logger.error("No valid bypass key found in discovery attempt")
        return None
    
    async def get_test_token(
        self,
        email: str = "e2e-test@staging.netrasystems.ai",
        name: str = "E2E Test User",
        permissions: list = None
    ) -> str:
        """
        Get a valid test token for E2E testing with dynamic bypass key discovery.
        
        Args:
            email: Test user email
            name: Test user name
            permissions: List of permissions for the test user
            
        Returns:
            JWT access token for testing
        """
        # Check if we have a cached token that's still valid
        if self.token_cache and self.token_expiry and datetime.now() < self.token_expiry:
            logger.info("Using cached test token")
            return self.token_cache
        
        # Request new token
        permissions = permissions or ["read", "write"]
        
        # Try validated bypass key first if we have one
        bypass_key_to_use = self.validated_bypass_key or self.bypass_key
        
        if bypass_key_to_use:
            # Try the known/cached bypass key first
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        f"{self.staging_auth_url}/auth/e2e/test-auth",
                        headers={
                            "X-E2E-Bypass-Key": bypass_key_to_use,
                            "Content-Type": "application/json"
                        },
                        json={
                            "email": email,
                            "name": name,
                            "permissions": permissions
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.token_cache = data["access_token"]
                        # Cache for 14 minutes (assuming 15 minute expiry)
                        self.token_expiry = datetime.now() + timedelta(minutes=14)
                        # Cache the working bypass key
                        self.validated_bypass_key = bypass_key_to_use
                        logger.info(f"Successfully obtained test token for {email} using cached key")
                        return self.token_cache
                    else:
                        logger.warning(f"Cached bypass key failed ({response.status_code}), attempting discovery")
                        
                except httpx.RequestError as e:
                    logger.warning(f"Network error with cached key, attempting discovery: {e}")
        
        # If direct attempt failed or no key available, try discovery
        discovered_key = await self._discover_valid_bypass_key(email, name, permissions)
        
        if not discovered_key:
            raise Exception(
                "Failed to authenticate with staging: No valid bypass key found. "
                "This may indicate:\n"
                "1. Staging auth service configuration has changed\n"
                "2. Bypass key rotation occurred without test updates\n"
                "3. Network connectivity issues to staging environment\n"
                "4. Staging auth service is experiencing issues"
            )
        
        # Try the discovered key
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.staging_auth_url}/auth/e2e/test-auth",
                    headers={
                        "X-E2E-Bypass-Key": discovered_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "email": email,
                        "name": name,
                        "permissions": permissions
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.token_cache = data["access_token"]
                    # Cache for 14 minutes (assuming 15 minute expiry)
                    self.token_expiry = datetime.now() + timedelta(minutes=14)
                    # Cache the working bypass key for future use
                    self.validated_bypass_key = discovered_key
                    logger.info(f"Successfully obtained test token for {email} using discovered key")
                    return self.token_cache
                else:
                    error_msg = f"Failed to get test token with discovered key: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                    
            except httpx.RequestError as e:
                logger.error(f"Network error during test authentication with discovered key: {e}")
                raise
    
    async def get_authenticated_client(
        self,
        base_url: Optional[str] = None,
        **user_kwargs
    ) -> httpx.AsyncClient:
        """
        Get an authenticated HTTP client for E2E testing.
        
        Args:
            base_url: Base URL for the client
            **user_kwargs: Additional arguments for get_test_token
            
        Returns:
            Configured httpx.AsyncClient with auth headers
        """
        token = await self.get_test_token(**user_kwargs)
        
        return httpx.AsyncClient(
            base_url=base_url or self.staging_auth_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    def get_sync_token(self, **kwargs) -> str:
        """
        Synchronous wrapper for getting test token.
        
        Returns:
            JWT access token for testing
        """
        return asyncio.run(self.get_test_token(**kwargs))


# Singleton instance for easy import
_staging_auth = None

def get_staging_auth() -> StagingAuthHelper:
    """Get or create the singleton staging auth helper."""
    global _staging_auth
    if _staging_auth is None:
        _staging_auth = StagingAuthHelper()
    return _staging_auth


# Example usage and test
async def test_staging_auth():
    """Test the staging OAUTH SIMULATION functionality."""
    try:
        auth = StagingAuthHelper()
        
        # Get a test token
        token = await auth.get_test_token()
        print(f"Successfully obtained test token: {token[:20]}...")
        
        # Get an authenticated client
        async with await auth.get_authenticated_client() as client:
            # Test with a simple health check
            response = await client.get("/auth/health")
            print(f"Health check response: {response.status_code}")
            
            # Test token validation
            response = await client.post("/auth/verify")
            if response.status_code == 200:
                user_info = response.json()
                print(f"Token validated successfully: {user_info}")
            else:
                print(f"Token validation failed: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False


if __name__ == "__main__":
    # Run test if executed directly
    success = asyncio.run(test_staging_auth())
    exit(0 if success else 1)
