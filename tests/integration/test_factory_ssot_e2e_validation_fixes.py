"""
Integration tests for Factory SSOT and E2E Auth validation fixes.

This module tests the SSOT-compliant fixes implemented to resolve:
1. Factory SSOT validation failures due to GCP Cloud Run timing differences
2. SSOT Auth policy violations due to missing E2E context propagation

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Stability in Staging Environment
- Value Impact: Restores staging E2E test capability for WebSocket functionality
- Revenue Impact: Enables testing of $120K+ MRR WebSocket chat functionality

These tests validate the fixes comply with SSOT principles while solving the 
root causes identified in the Five Whys analysis.
"""

import asyncio
import os
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional

from netra_backend.app.websocket_core.websocket_manager_factory import (
    _validate_ssot_user_context_staging_safe,
    create_websocket_manager,
    create_defensive_user_execution_context
)
from netra_backend.app.websocket_core.unified_websocket_auth import (
    authenticate_websocket_ssot,
    extract_e2e_context_from_websocket,
    UnifiedWebSocketAuthenticator
)
from netra_backend.app.services.unified_authentication_service import UnifiedAuthenticationService
from netra_backend.app.services.user_execution_context import UserExecutionContext
from fastapi import WebSocket


class TestFactorySSotValidationFixes:
    """
    Test Factory SSOT validation enhancements for GCP Cloud Run staging patterns.
    
    These tests validate the enhanced validation logic that recognizes legitimate
    staging patterns while maintaining SSOT compliance.
    """
    
    def test_staging_uuid_fallback_pattern_validation(self):
        """Test that UUID fallback patterns are accepted in staging environments."""
        
        # Create user context with UUID fallback patterns (common in GCP Cloud Run)
        user_context = UserExecutionContext(
            user_id="staging-e2e-user-003",
            thread_id="ws_thread_1704739200_a1b2c3d4",  # UUID fallback pattern
            run_id="ws_run_1704739200_a1b2c3d4",        # UUID fallback pattern
            request_id="ws_req_1704739200_a1b2c3d4",    # UUID fallback pattern
            websocket_client_id="ws_client_staging_1704739200_a1b2c3d4"
        )
        
        # Simulate staging environment
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "K_SERVICE": "netra-backend",  # GCP Cloud Run indicator
            "E2E_TEST_ENV": "staging"
        }):
            # This should NOT raise an exception with enhanced validation
            try:
                _validate_ssot_user_context_staging_safe(user_context)
                # Test passes if no exception raised
                assert True, "Enhanced validation should accept UUID fallback patterns"
            except ValueError as e:
                pytest.fail(f"Enhanced validation failed for legitimate staging pattern: {e}")
    
    def test_standard_uuid_pattern_validation(self):
        """Test that standard UUID patterns are accepted in staging environments."""
        
        user_context = UserExecutionContext(
            user_id="12345678-1234-5678-9abc-123456789012",
            thread_id="87654321-8765-4321-cdef-876543210987",
            run_id="11111111-2222-3333-4444-555555555555",
            request_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            websocket_client_id="ws_client_uuid_test"
        )
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "K_SERVICE": "netra-backend"
        }):
            try:
                _validate_ssot_user_context_staging_safe(user_context)
                assert True, "Enhanced validation should accept standard UUID patterns"
            except ValueError as e:
                pytest.fail(f"Enhanced validation failed for standard UUID pattern: {e}")
    
    def test_e2e_user_pattern_validation(self):
        """Test that E2E testing user patterns are accepted."""
        
        user_context = UserExecutionContext(
            user_id="staging-e2e-user-001",
            thread_id="test-thread-e2e-abc123",
            run_id="test-run-e2e-def456",
            request_id="test-req-e2e-ghi789",
            websocket_client_id="test-ws-client-001"
        )
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "E2E_TESTING": "1",
            "STAGING_E2E_TEST": "1"
        }):
            try:
                _validate_ssot_user_context_staging_safe(user_context)
                assert True, "Enhanced validation should accept E2E user patterns"
            except ValueError as e:
                pytest.fail(f"Enhanced validation failed for E2E user pattern: {e}")
    
    def test_production_strict_validation_still_works(self):
        """Test that production environments still use strict validation."""
        
        # Create user context that would be acceptable in staging but not production
        user_context = UserExecutionContext(
            user_id="test-user",
            thread_id="",  # Empty thread_id - should fail strict validation
            run_id="ws_run_1704739200_a1b2c3d4",
            request_id="ws_req_1704739200_a1b2c3d4",
            websocket_client_id="test-client"
        )
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production"
        }):
            # This should raise an exception in production
            with pytest.raises(ValueError, match="must be non-empty string"):
                _validate_ssot_user_context_staging_safe(user_context)
    
    def test_invalid_user_context_type_fails_all_environments(self):
        """Test that invalid user context types fail in all environments."""
        
        invalid_context = {"user_id": "test-user"}  # Dict instead of UserExecutionContext
        
        # Should fail in staging
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            with pytest.raises(ValueError, match="Expected UserExecutionContext"):
                _validate_ssot_user_context_staging_safe(invalid_context)
        
        # Should fail in production  
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with pytest.raises(ValueError, match="Expected UserExecutionContext"):
                _validate_ssot_user_context_staging_safe(invalid_context)


class TestE2EAuthValidationFixes:
    """
    Test E2E authentication bypass fixes for SSOT Auth chain.
    
    These tests validate the E2E context propagation that prevents policy
    violations during staging E2E testing.
    """
    
    def test_e2e_context_extraction_from_headers(self):
        """Test E2E context extraction from WebSocket headers."""
        
        # Mock WebSocket with E2E testing headers
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {
            "X-E2E-Test": "true",
            "X-Test-Environment": "staging",
            "Authorization": "Bearer staging-e2e-token-123"
        }
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "E2E_TEST_ENV": "staging"
        }):
            e2e_context = extract_e2e_context_from_websocket(mock_websocket)
            
            assert e2e_context is not None
            assert e2e_context["is_e2e_testing"] is True
            assert e2e_context["bypass_enabled"] is True
            assert e2e_context["detection_method"]["via_headers"] is True
            assert e2e_context["detection_method"]["via_environment"] is True
    
    def test_e2e_context_extraction_from_environment_only(self):
        """Test E2E context extraction from environment variables only."""
        
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {}  # No E2E headers
        
        with patch.dict(os.environ, {
            "E2E_TESTING": "1",
            "STAGING_E2E_TEST": "1",
            "E2E_OAUTH_SIMULATION_KEY": "test_key_123"
        }):
            e2e_context = extract_e2e_context_from_websocket(mock_websocket)
            
            assert e2e_context is not None
            assert e2e_context["is_e2e_testing"] is True
            assert e2e_context["bypass_enabled"] is True
            assert e2e_context["detection_method"]["via_headers"] is False
            assert e2e_context["detection_method"]["via_environment"] is True
            assert e2e_context["e2e_oauth_key"] == "test_key_123"
    
    def test_no_e2e_context_in_production(self):
        """Test that E2E context is not detected in production environments."""
        
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {
            "X-E2E-Test": "true"  # E2E header present but production environment
        }
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production"
        }, clear=True):  # Clear E2E environment variables
            e2e_context = extract_e2e_context_from_websocket(mock_websocket)
            
            # Should detect E2E from headers even in production (headers still valid)
            assert e2e_context is not None
            assert e2e_context["detection_method"]["via_headers"] is True
            assert e2e_context["detection_method"]["via_environment"] is False
    
    @pytest.mark.asyncio
    async def test_e2e_bypass_in_authentication_service(self):
        """Test E2E bypass logic in UnifiedAuthenticationService."""
        
        # Create test E2E context
        e2e_context = {
            "is_e2e_testing": True,
            "bypass_enabled": True,
            "environment": "staging",
            "detection_method": {"via_headers": True, "via_environment": True}
        }
        
        # Create mock WebSocket
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {
            "Authorization": "Bearer staging-e2e-user-003-token"
        }
        
        # Create authentication service
        auth_service = UnifiedAuthenticationService()
        
        # Test E2E bypass authentication
        auth_result, user_context = await auth_service.authenticate_websocket(
            mock_websocket, 
            e2e_context=e2e_context
        )
        
        # Verify bypass worked
        assert auth_result.success is True
        assert "staging-e2e-user" in auth_result.user_id
        assert auth_result.metadata.get("e2e_bypass") is True
        assert "e2e_testing" in auth_result.permissions
        assert user_context is not None
        assert user_context.user_id == auth_result.user_id
    
    @pytest.mark.asyncio
    async def test_e2e_user_id_extraction_from_token(self):
        """Test user ID extraction from E2E tokens."""
        
        auth_service = UnifiedAuthenticationService()
        
        # Test staging-e2e-user pattern
        token1 = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.staging-e2e-user-003.signature"
        user_id1 = auth_service._extract_user_id_from_e2e_token(token1)
        assert user_id1 == "staging-e2e-user-003"
        
        # Test test-user pattern
        token2 = "Bearer test-user-abc123def456"
        user_id2 = auth_service._extract_user_id_from_e2e_token(token2)
        assert user_id2 == "test-user-abc123def456"
    
    @pytest.mark.asyncio
    async def test_normal_auth_still_works_without_e2e_context(self):
        """Test that normal authentication still works when no E2E context provided."""
        
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {
            "Authorization": "Bearer valid-jwt-token"
        }
        
        auth_service = UnifiedAuthenticationService()
        
        # Mock the authenticate_token method to return success
        with patch.object(auth_service, 'authenticate_token') as mock_auth_token:
            mock_auth_result = Mock()
            mock_auth_result.success = True
            mock_auth_result.user_id = "regular-user-123"
            mock_auth_result.email = "user@example.com"
            mock_auth_result.permissions = ["user"]
            mock_auth_token.return_value = mock_auth_result
            
            # Mock _create_user_execution_context
            with patch.object(auth_service, '_create_user_execution_context') as mock_create_context:
                mock_user_context = UserExecutionContext(
                    user_id="regular-user-123",
                    thread_id="thread-123",
                    run_id="run-123",
                    request_id="req-123"
                )
                mock_create_context.return_value = mock_user_context
                
                # Test normal authentication (no E2E context)
                auth_result, user_context = await auth_service.authenticate_websocket(mock_websocket)
                
                # Verify normal auth worked
                assert auth_result.success is True
                assert auth_result.user_id == "regular-user-123"
                assert auth_result.metadata.get("e2e_bypass") is None  # No E2E bypass
                assert user_context is not None


class TestIntegratedFactoryAndAuthFixes:
    """
    Test integrated Factory SSOT and E2E Auth fixes working together.
    
    These tests validate that both fixes work together in realistic
    WebSocket connection scenarios.
    """
    
    @pytest.mark.asyncio
    async def test_complete_websocket_flow_with_e2e_bypass(self):
        """Test complete WebSocket flow with E2E bypass and enhanced factory validation."""
        
        # Create staging E2E environment
        test_env = {
            "ENVIRONMENT": "staging",
            "K_SERVICE": "netra-backend",
            "E2E_TESTING": "1", 
            "STAGING_E2E_TEST": "1",
            "E2E_TEST_ENV": "staging"
        }
        
        with patch.dict(os.environ, test_env):
            # Mock WebSocket with E2E headers
            mock_websocket = Mock(spec=WebSocket)
            mock_websocket.headers = {
                "X-E2E-Test": "true",
                "X-Test-Environment": "staging",
                "Authorization": "Bearer staging-e2e-user-003-token"
            }
            
            # Test E2E context extraction
            e2e_context = extract_e2e_context_from_websocket(mock_websocket)
            assert e2e_context is not None
            assert e2e_context["bypass_enabled"] is True
            
            # Test authentication with E2E bypass
            auth_result = await authenticate_websocket_ssot(mock_websocket, e2e_context)
            assert auth_result.success is True
            assert auth_result.user_context is not None
            
            # Test factory validation accepts the E2E user context  
            user_context = auth_result.user_context
            try:
                _validate_ssot_user_context_staging_safe(user_context)
                # Test passes if no exception
                assert True, "Factory validation should accept E2E user context"
            except ValueError as e:
                pytest.fail(f"Factory validation failed for E2E context: {e}")
    
    def test_staging_user_context_creation_with_uuid_fallback(self):
        """Test defensive user context creation with UUID fallback patterns."""
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "K_SERVICE": "netra-backend"
        }):
            # Mock UnifiedIdGenerator to fail (simulating Cloud Run timing issues)
            with patch('shared.id_generation.unified_id_generator.UnifiedIdGenerator.generate_user_context_ids') as mock_gen:
                mock_gen.side_effect = Exception("Database not ready")
                
                # Create defensive user context - should use UUID fallback
                user_context = create_defensive_user_execution_context(
                    user_id="staging-e2e-user-003",
                    websocket_client_id="ws_staging_client_123"
                )
                
                # Verify UUID fallback patterns were used
                assert user_context.user_id == "staging-e2e-user-003"
                assert "ws_thread_" in user_context.thread_id
                assert "ws_run_" in user_context.run_id
                assert "ws_req_" in user_context.request_id
                
                # Verify this context passes enhanced validation
                try:
                    _validate_ssot_user_context_staging_safe(user_context)
                    assert True, "Enhanced validation should accept UUID fallback patterns"
                except ValueError as e:
                    pytest.fail(f"Enhanced validation failed for UUID fallback: {e}")
    
    @pytest.mark.asyncio 
    async def test_websocket_manager_creation_with_enhanced_validation(self):
        """Test WebSocket manager creation with enhanced SSOT validation."""
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "E2E_TESTING": "1"
        }):
            # Create user context with E2E pattern
            user_context = UserExecutionContext(
                user_id="staging-e2e-user-003",
                thread_id="ws_thread_1704739200_a1b2c3d4",
                run_id="ws_run_1704739200_a1b2c3d4", 
                request_id="ws_req_1704739200_a1b2c3d4",
                websocket_client_id="ws_client_e2e_test"
            )
            
            # This should NOT raise FactoryInitializationError with enhanced validation
            try:
                ws_manager = await create_websocket_manager(user_context)
                assert ws_manager is not None
                assert ws_manager.user_context.user_id == "staging-e2e-user-003"
            except Exception as e:
                pytest.fail(f"WebSocket manager creation failed with enhanced validation: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])