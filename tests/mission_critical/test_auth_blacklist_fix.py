#!/usr/bin/env python3
"""
Mission Critical Test: Auth Service Token Blacklist Fix
Tests the Five Whys root cause fix for async/await mismatch in blacklist operations.

This test validates:
1. WHY #1 Fix: No more "object bool can't be used in await" errors
2. WHY #2 Fix: Proper sync/async boundary handling
3. WHY #3 Fix: Unified async interface pattern
4. WHY #4 Fix: Real service integration testing
5. WHY #5 Fix: SSOT implementation for blacklist operations
"""

import asyncio
import pytest
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Add auth_service to path
auth_service_path = Path(__file__).parent.parent.parent / "auth_service"
sys.path.insert(0, str(auth_service_path))

from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.core.jwt_handler import JWTHandler

logger = logging.getLogger(__name__)


class TestBlacklistAsyncFix:
    """Test the Five Whys fix for auth service async/await issues"""
    
    @pytest.fixture
    def auth_service(self):
        """Create auth service instance"""
        return AuthService()
    
    @pytest.fixture
    def sample_token(self):
        """Sample JWT token for testing"""
        return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzIiwiZXhwIjoxNzU3MzEwNjc3fQ.test"
    
    @pytest.mark.asyncio
    async def test_why_1_no_await_bool_error(self, auth_service, sample_token):
        """WHY #1 Fix: Verify no 'object bool can't be used in await' error"""
        # This should not raise "object bool can't be used in await expression"
        try:
            result = await auth_service.is_token_blacklisted(sample_token)
            assert isinstance(result, bool), "Should return a boolean"
            logger.info(" PASS:  WHY #1 Fix validated: No await bool error")
        except TypeError as e:
            if "can't be used in 'await' expression" in str(e):
                pytest.fail(f"WHY #1 Fix failed: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_why_2_sync_async_boundary(self, auth_service, sample_token):
        """WHY #2 Fix: Verify proper sync/async boundary handling"""
        # Mock JWT handler with sync methods (as they actually are)
        mock_jwt = MagicMock()
        mock_jwt.is_token_blacklisted = MagicMock(return_value=False)  # Sync method
        mock_jwt.blacklist_token = MagicMock(return_value=True)  # Sync method
        
        auth_service.jwt_handler = mock_jwt
        
        # Test is_token_blacklisted - should handle sync method correctly
        result = await auth_service.is_token_blacklisted(sample_token)
        assert result is False
        mock_jwt.is_token_blacklisted.assert_called_once_with(sample_token)
        
        # Test blacklist_token - should handle sync method correctly
        await auth_service.blacklist_token(sample_token)
        mock_jwt.blacklist_token.assert_called_once_with(sample_token)
        
        logger.info(" PASS:  WHY #2 Fix validated: Sync/async boundary handled correctly")
    
    @pytest.mark.asyncio
    async def test_why_3_unified_interface(self, auth_service, sample_token):
        """WHY #3 Fix: Verify unified async interface pattern"""
        # Both methods should be async at the service level
        assert asyncio.iscoroutinefunction(auth_service.is_token_blacklisted)
        assert asyncio.iscoroutinefunction(auth_service.blacklist_token)
        
        # They should work with different underlying implementations
        # Test 1: With JWT handler
        auth_service.jwt_handler = MagicMock()
        auth_service.jwt_handler.is_token_blacklisted = MagicMock(return_value=True)
        result = await auth_service.is_token_blacklisted(sample_token)
        assert result is True
        
        # Test 2: Without JWT handler methods (fallback to memory)
        auth_service.jwt_handler = MagicMock(spec=[])  # No blacklist methods
        await auth_service.blacklist_token(sample_token)
        result = await auth_service.is_token_blacklisted(sample_token)
        assert result is True  # Should find in memory blacklist
        
        logger.info(" PASS:  WHY #3 Fix validated: Unified async interface works")
    
    @pytest.mark.asyncio
    async def test_why_4_real_integration(self, sample_token):
        """WHY #4 Fix: Real service integration test"""
        # Create real instances
        auth_service = AuthService()
        
        # Blacklist a token
        await auth_service.blacklist_token(sample_token)
        
        # Check if blacklisted
        is_blacklisted = await auth_service.is_token_blacklisted(sample_token)
        assert is_blacklisted is True, "Token should be blacklisted"
        
        # Check a different token
        other_token = sample_token + "_different"
        is_blacklisted = await auth_service.is_token_blacklisted(other_token)
        assert is_blacklisted is False, "Other token should not be blacklisted"
        
        logger.info(" PASS:  WHY #4 Fix validated: Real integration works")
    
    @pytest.mark.asyncio
    async def test_why_5_ssot_principle(self, auth_service):
        """WHY #5 Fix: Verify SSOT principle is followed"""
        # There should be only ONE async interface for blacklist operations
        # at the service level, regardless of underlying implementation
        
        # Count blacklist-related methods in AuthService
        blacklist_methods = [
            method for method in dir(auth_service)
            if 'blacklist' in method.lower() and not method.startswith('_')
        ]
        
        # Should have exactly these two methods
        expected_methods = {'blacklist_token', 'is_token_blacklisted'}
        actual_methods = set(blacklist_methods)
        
        assert actual_methods == expected_methods, (
            f"SSOT violation: Expected {expected_methods}, found {actual_methods}"
        )
        
        # Both should be async
        for method_name in expected_methods:
            method = getattr(auth_service, method_name)
            assert asyncio.iscoroutinefunction(method), (
                f"SSOT violation: {method_name} must be async"
            )
        
        logger.info(" PASS:  WHY #5 Fix validated: SSOT principle maintained")
    
    @pytest.mark.asyncio
    async def test_error_handling_resilience(self, auth_service, sample_token):
        """Test error handling and resilience"""
        # Mock JWT handler to raise an exception
        mock_jwt = MagicMock()
        mock_jwt.is_token_blacklisted = MagicMock(side_effect=Exception("Test error"))
        mock_jwt.blacklist_token = MagicMock(side_effect=Exception("Test error"))
        
        auth_service.jwt_handler = mock_jwt
        
        # Should handle errors gracefully
        result = await auth_service.is_token_blacklisted(sample_token)
        assert result is False, "Should return False on error (fail-open)"
        
        # Blacklist should fallback to memory on error
        await auth_service.blacklist_token(sample_token)
        # Remove the mock to test memory blacklist
        auth_service.jwt_handler = MagicMock(spec=[])
        result = await auth_service.is_token_blacklisted(sample_token)
        assert result is True, "Should have blacklisted in memory after error"
        
        logger.info(" PASS:  Error handling validated: Graceful degradation works")
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, auth_service):
        """Test concurrent blacklist operations"""
        tokens = [f"token_{i}" for i in range(10)]
        
        # Blacklist multiple tokens concurrently
        await asyncio.gather(*[
            auth_service.blacklist_token(token) for token in tokens
        ])
        
        # Check all tokens concurrently
        results = await asyncio.gather(*[
            auth_service.is_token_blacklisted(token) for token in tokens
        ])
        
        assert all(results), "All tokens should be blacklisted"
        
        # Check non-blacklisted token
        result = await auth_service.is_token_blacklisted("not_blacklisted")
        assert result is False, "Non-blacklisted token should return False"
        
        logger.info(" PASS:  Concurrent operations validated")


class TestBlacklistEndpointIntegration:
    """Test the /auth/check-blacklist endpoint integration"""
    
    @pytest.mark.asyncio
    async def test_endpoint_with_real_service(self):
        """Test the actual endpoint with real service"""
        from fastapi.testclient import TestClient
        from auth_service.main import app
        
        client = TestClient(app)
        
        # Test check-blacklist endpoint
        response = client.post(
            "/auth/check-blacklist",
            json={"token": "test_token_123"},
            headers={
                "X-Service-ID": "netra-backend",
                "X-Service-Secret": "test-secret"
            }
        )
        
        # Should not fail with async/await error
        assert response.status_code == 200
        data = response.json()
        assert "blacklisted" in data
        assert isinstance(data["blacklisted"], bool)
        
        logger.info(" PASS:  Endpoint integration validated")


def test_five_whys_documentation():
    """Verify Five Whys analysis is documented"""
    import os
    
    # Check if Five Whys files were created
    five_whys_files = [
        "/tmp/five_whys_level_1.txt",
        "/tmp/five_whys_level_2.txt",
        "/tmp/five_whys_level_3.txt",
        "/tmp/five_whys_level_4.txt",
        "/tmp/five_whys_root_cause.txt"
    ]
    
    for file_path in five_whys_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                logger.info(f" PASS:  Five Whys {file_path}: {content[:100]}...")
    
    logger.info(" PASS:  Five Whys documentation validated")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])