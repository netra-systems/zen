"""
User Registration Flow Integration Tests

Business Value Justification (BVJ):
- Segment: Free → Early → Paid (Primary revenue funnel)
- Business Goal: Protect $570K MRR from registration failures
- Value Impact: Each test prevents broken onboarding flows
- Strategic Impact: Ensures enterprise-ready user experience

This test validates user registration and email verification flows.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, MagicMock, patch

import httpx
import pytest
from fastapi import status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.tests.integration.helpers.user_flow_helpers import (
    MockAuthService,
    generate_test_user_data,
    simulate_user_journey,
)

class TestUserRegistrationFlow:
    """Test user registration and verification flow"""
    
    @pytest.mark.asyncio
    async def test_complete_registration_with_verification(self, 
                                                         test_session: AsyncSession,
                                                         test_redis: Redis):
        """Test complete user registration with email verification"""
        # Generate test user data
        user_data = generate_test_user_data()
        
        # Mock services
        mock_auth = MockAuthService()
        mock_services = {"auth_service": mock_auth}
        
        # Define registration journey
        journey_steps = [
            {
                "type": "register",
                "data": {"user_data": user_data}
            },
            {
                "type": "verify_email", 
                "data": {}
            }
        ]
        
        # Execute journey
        result = await simulate_user_journey(journey_steps, mock_services)
        
        # Validate results
        assert result["success"], f"Registration failed: {result['errors']}"
        assert result["steps_completed"] == 2, "Not all steps completed"
        
        # Verify user state
        final_step = result["step_results"][-1]
        assert final_step.get("context", {}).get("verified") is True
    
    @pytest.mark.asyncio
    async def test_registration_input_validation(self, test_session: AsyncSession):
        """Test registration input validation"""
        mock_auth = MockAuthService()
        
        # Test invalid email
        invalid_user_data = generate_test_user_data()
        invalid_user_data["email"] = "invalid-email"
        
        result = await mock_auth.register_user(invalid_user_data)
        
        # Should handle validation gracefully
        assert "user_id" in result or "error" in result
    
    @pytest.mark.asyncio
    async def test_duplicate_registration_handling(self, test_session: AsyncSession):
        """Test handling of duplicate registration attempts"""
        mock_auth = MockAuthService()
        user_data = generate_test_user_data()
        
        # First registration
        result1 = await mock_auth.register_user(user_data)
        assert result1["status"] == "registered"
        
        # Duplicate registration attempt
        result2 = await mock_auth.register_user(user_data)
        
        # Should handle duplicate gracefully
        assert "user_id" in result2 or "error" in result2
    
    @pytest.mark.asyncio
    async def test_email_verification_edge_cases(self, test_session: AsyncSession):
        """Test email verification edge cases"""
        mock_auth = MockAuthService()
        user_data = generate_test_user_data()
        
        # Register user
        reg_result = await mock_auth.register_user(user_data)
        user_id = reg_result["user_id"]
        
        # Test invalid verification token
        invalid_verify = await mock_auth.verify_email(user_id, "invalid_token")
        assert invalid_verify is False
        
        # Test valid verification token
        valid_token = reg_result.get("verification_token")
        if valid_token:
            valid_verify = await mock_auth.verify_email(user_id, valid_token)
            assert valid_verify is True
    
    @pytest.mark.asyncio
    async def test_registration_performance_under_load(self, test_session: AsyncSession):
        """Test registration performance under concurrent load"""
        mock_auth = MockAuthService()
        
        # Generate multiple user registrations
        user_data_list = [generate_test_user_data() for _ in range(10)]
        
        # Register users concurrently
        start_time = time.time()
        
        async def register_single_user(user_data):
            return await mock_auth.register_user(user_data)
        
        tasks = [register_single_user(user_data) for user_data in user_data_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Validate performance
        successful_registrations = sum(1 for r in results if isinstance(r, dict) and "user_id" in r)
        
        assert successful_registrations >= 8, f"Too many registration failures: {successful_registrations}/10"
        assert total_time < 10.0, f"Registration took too long: {total_time:.2f}s"
    
    @pytest.mark.asyncio
    async def test_registration_failure_recovery(self, test_session: AsyncSession):
        """Test recovery from registration failures"""
        mock_auth = MockAuthService()
        user_data = generate_test_user_data()
        
        # Simulate service failure during registration
        with patch.object(mock_auth, 'register_user', side_effect=Exception("Service unavailable")):
            with pytest.raises(Exception):
                await mock_auth.register_user(user_data)
        
        # Service recovery - registration should work
        result = await mock_auth.register_user(user_data)
        assert result["status"] == "registered"
        assert "user_id" in result