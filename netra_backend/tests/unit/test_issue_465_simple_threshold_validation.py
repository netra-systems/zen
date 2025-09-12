"""
Simple Issue #465 Test: Token Reuse Threshold Too Strict

PURPOSE: Direct test of token reuse detection logic to prove Issue #465 exists
APPROACH: Test the actual _validate_token_with_auth_service function with mocked auth service

Business Impact: $500K+ ARR at risk from legitimate users being blocked
"""

import asyncio
import time
import pytest
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Direct import of the function containing the problematic threshold
from netra_backend.app.auth_integration.auth import (
    _validate_token_with_auth_service,
    _active_token_sessions,
    _token_usage_stats
)


class TestIssue465SimpleThresholdValidation(SSotAsyncTestCase):
    """
    Simple, direct tests for Issue #465 token reuse threshold problem
    
    These tests directly call _validate_token_with_auth_service to prove the issue
    """

    def setUp(self):
        super().setUp()
        # Clear token state for clean tests
        _active_token_sessions.clear()
        _token_usage_stats.update({
            'reuse_attempts_blocked': 0,
            'sessions_validated': 0,
            'validation_errors': 0
        })
        print(f"\n🧪 Test setup complete - token sessions cleared")

    async def test_threshold_blocks_legitimate_usage(self):
        """
        CORE TEST: Prove that 1.0s threshold blocks legitimate usage
        
        BUSINESS IMPACT: Users clicking "Send" twice quickly get authentication error
        EXPECTED: This test should PASS, proving the issue exists
        """
        print("🔍 Testing core Issue #465: 1.0s threshold too strict")
        
        test_token = "issue-465-test-token"
        
        # Mock auth service to return valid response (focus on threshold logic)
        mock_auth_response = {
            'user_id': 'legitimate-user',
            'email': 'user@company.com',
            'sub': 'legitimate-user',
            'session_id': 'legitimate-session-123'
        }
        
        with patch('netra_backend.app.auth_integration.auth.auth_client.validate_token') as mock_validate:
            mock_validate.return_value = mock_auth_response
            
            # First request - should always succeed
            print("   📤 Making first request...")
            result1 = await _validate_token_with_auth_service(test_token)
            self.assertIsNotNone(result1)
            print("   ✅ First request: SUCCESS")
            
            # Wait 0.8 seconds (typical user double-click timing)
            print("   ⏳ Waiting 0.8 seconds (realistic user timing)...")
            time.sleep(0.8)
            
            # Second request - should fail with current 1.0s threshold
            print("   📤 Making second request after 0.8s...")
            try:
                result2 = await _validate_token_with_auth_service(test_token)
                self.fail("❌ TEST FAILED: Expected HTTPException due to strict 1.0s threshold, but request succeeded")
            except HTTPException as e:
                # This proves Issue #465 exists
                self.assertEqual(e.status_code, 401)
                self.assertIn("Token reuse detected", e.detail)
                print("   ✅ Second request: BLOCKED (as expected with current threshold)")
                print("   🎯 ISSUE #465 CONFIRMED: Legitimate 0.8s interval blocked by 1.0s threshold")
                return
            
            self.fail("Expected HTTPException to prove Issue #465, but none was raised")

    async def test_just_over_threshold_succeeds(self):
        """
        Test that requests just over 1.0s threshold succeed
        
        PURPOSE: Verify current threshold behavior is exactly 1.0s
        """
        print("🔍 Testing threshold boundary: 1.1s interval")
        
        test_token = "boundary-test-token"
        mock_auth_response = {
            'user_id': 'boundary-user',
            'email': 'boundary@company.com', 
            'sub': 'boundary-user',
            'session_id': 'boundary-session-123'
        }
        
        with patch('netra_backend.app.auth_integration.auth.auth_client.validate_token') as mock_validate:
            mock_validate.return_value = mock_auth_response
            
            # First request
            print("   📤 Making first request...")
            result1 = await _validate_token_with_auth_service(test_token)
            self.assertIsNotNone(result1)
            print("   ✅ First request: SUCCESS")
            
            # Wait 1.1 seconds (just over threshold)
            print("   ⏳ Waiting 1.1 seconds (just over current threshold)...")
            time.sleep(1.1)
            
            # Second request - should succeed
            print("   📤 Making second request after 1.1s...")
            try:
                result2 = await _validate_token_with_auth_service(test_token)
                self.assertIsNotNone(result2)
                print("   ✅ Second request: SUCCESS (1.1s > 1.0s threshold)")
                print("   📊 Threshold boundary behavior confirmed")
            except HTTPException as e:
                self.fail(f"❌ Request at 1.1s should succeed with 1.0s threshold, but got: {e.detail}")

    async def test_stats_tracking_works(self):
        """
        Test that blocked attempts are tracked in statistics
        
        PURPOSE: Verify monitoring is working for Issue #465 impact analysis
        """
        print("🔍 Testing statistics tracking for blocked requests")
        
        initial_blocked = _token_usage_stats['reuse_attempts_blocked']
        print(f"   📊 Initial blocked count: {initial_blocked}")
        
        test_token = "stats-test-token"
        mock_auth_response = {
            'user_id': 'stats-user',
            'email': 'stats@company.com',
            'sub': 'stats-user', 
            'session_id': 'stats-session-123'
        }
        
        with patch('netra_backend.app.auth_integration.auth.auth_client.validate_token') as mock_validate:
            mock_validate.return_value = mock_auth_response
            
            # First request
            result1 = await _validate_token_with_auth_service(test_token)
            print("   ✅ First request: SUCCESS")
            
            # Quick second request (will be blocked)
            time.sleep(0.3)
            print("   📤 Making blocked request after 0.3s...")
            
            try:
                result2 = await _validate_token_with_auth_service(test_token)
                self.fail("Expected request to be blocked for stats test")
            except HTTPException:
                print("   ✅ Second request: BLOCKED (as expected)")
            
            # Check stats were updated
            final_blocked = _token_usage_stats['reuse_attempts_blocked']
            print(f"   📊 Final blocked count: {final_blocked}")
            
            self.assertEqual(final_blocked, initial_blocked + 1, 
                           f"Expected blocked count to increase by 1, got {final_blocked - initial_blocked}")
            print("   ✅ Statistics tracking: WORKING")

    async def test_different_users_dont_interfere(self):
        """
        Test that different users don't interfere with each other
        
        PURPOSE: Verify Issue #465 fix won't break multi-user functionality
        """
        print("🔍 Testing different users can make concurrent requests")
        
        user1_token = "user1-token"
        user2_token = "user2-token"
        
        user1_response = {
            'user_id': 'user-1',
            'email': 'user1@company.com',
            'sub': 'user-1',
            'session_id': 'user1-session'
        }
        
        user2_response = {
            'user_id': 'user-2', 
            'email': 'user2@company.com',
            'sub': 'user-2',
            'session_id': 'user2-session'
        }
        
        with patch('netra_backend.app.auth_integration.auth.auth_client.validate_token') as mock_validate:
            # Set up different responses for different tokens
            def side_effect(token):
                if token == user1_token:
                    return user1_response
                elif token == user2_token:
                    return user2_response
                else:
                    return None
            
            mock_validate.side_effect = side_effect
            
            # Both users make requests
            print("   👤 User 1 making request...")
            result1 = await _validate_token_with_auth_service(user1_token)
            print("   ✅ User 1: SUCCESS")
            
            print("   👤 User 2 making request immediately after...")
            result2 = await _validate_token_with_auth_service(user2_token)
            print("   ✅ User 2: SUCCESS")
            
            self.assertIsNotNone(result1)
            self.assertIsNotNone(result2)
            print("   🎯 Multi-user concurrent access: WORKING")


class TestBusinessImpactScenarios(SSotAsyncTestCase):
    """
    Business impact scenarios that demonstrate real-world Issue #465 problems
    """

    def setUp(self):
        super().setUp()
        _active_token_sessions.clear()
        _token_usage_stats.update({
            'reuse_attempts_blocked': 0,
            'sessions_validated': 0,
            'validation_errors': 0
        })

    async def test_chat_user_double_click_scenario(self):
        """
        BUSINESS SCENARIO: User double-clicks "Send" in chat interface
        
        IMPACT: 90% of platform value (chat) broken for users who click quickly
        """
        print("💬 BUSINESS SCENARIO: Chat user double-clicks Send button")
        
        chat_token = "chat-user-token"
        mock_response = {
            'user_id': 'chat-user-enterprise',
            'email': 'enterprise.user@bigcorp.com',
            'sub': 'chat-user-enterprise',
            'session_id': 'chat-session-enterprise'
        }
        
        with patch('netra_backend.app.auth_integration.auth.auth_client.validate_token', return_value=mock_response):
            # First click
            print("   🖱️ User clicks 'Send' button...")
            result1 = await _validate_token_with_auth_service(chat_token)
            print("   ✅ First click: Message sending started")
            
            # User double-clicks (0.4s later - common user behavior)
            time.sleep(0.4)
            print("   🖱️ User double-clicks (0.4s later)...")
            
            try:
                result2 = await _validate_token_with_auth_service(chat_token)
                self.fail("❌ Expected double-click to be blocked by current threshold")
            except HTTPException as e:
                print("   ❌ Second click: BLOCKED - User sees authentication error!")
                print("   💰 BUSINESS IMPACT: Chat functionality (90% of value) broken")
                print("   👔 ENTERPRISE IMPACT: $50K+ ARR customer frustrated")
                self.assertIn("Token reuse detected", e.detail)

    async def test_browser_tab_refresh_scenario(self):
        """
        BUSINESS SCENARIO: User refreshes browser tab or opens multiple tabs
        """
        print("🌐 BUSINESS SCENARIO: User refreshes browser tab")
        
        browser_token = "browser-refresh-token"
        mock_response = {
            'user_id': 'browser-user',
            'email': 'user@startup.com',
            'sub': 'browser-user', 
            'session_id': 'browser-session'
        }
        
        with patch('netra_backend.app.auth_integration.auth.auth_client.validate_token', return_value=mock_response):
            # Initial page load
            print("   🌍 Initial page load...")
            result1 = await _validate_token_with_auth_service(browser_token)
            print("   ✅ Page loaded successfully")
            
            # User hits F5 to refresh (0.6s later)
            time.sleep(0.6)
            print("   🔄 User hits F5 to refresh (0.6s later)...")
            
            try:
                result2 = await _validate_token_with_auth_service(browser_token)
                self.fail("❌ Expected page refresh to be blocked by current threshold")
            except HTTPException as e:
                print("   ❌ Page refresh: BLOCKED - User sees authentication error!")
                print("   📱 USER IMPACT: Normal browser behavior broken")
                print("   🚀 STARTUP IMPACT: User churn risk for normal usage")
                self.assertIn("Token reuse detected", e.detail)


if __name__ == "__main__":
    print("🧪 Running Issue #465 Simple Threshold Validation Tests")
    print("🎯 Purpose: Directly prove that 1.0s threshold blocks legitimate usage")
    print("📊 Expected: Tests should PASS, confirming Issue #465 exists")
    print("💰 Business Impact: $500K+ ARR at risk from false positives")
    print()
    
    import unittest
    unittest.main()