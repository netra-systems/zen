"""
Critical test for refresh token fix - ensures the exact staging bug is resolved
"""
import pytest
import time
from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.core.jwt_handler import JWTHandler
from shared.isolated_environment import IsolatedEnvironment


class TestRefreshCriticalFix:
    """Critical test suite focused on the specific refresh token bug"""
    
    @pytest.fixture
    def auth_service(self):
        """Create auth service with minimal setup"""
        service = AuthService()
        return service
    
    @pytest.fixture  
    def jwt_handler(self):
        """Create JWT handler for testing"""
        return JWTHandler()
        
    @pytest.mark.asyncio
    async def test_refresh_tokens_are_unique_critical(self, auth_service):
        """CRITICAL: Test that refresh operations generate unique tokens each time"""
        # Create initial refresh token with real user data (not placeholders)
        user_id = "test-user-123"
        user_email = "test@staging.netrasystems.ai"
        user_permissions = ["read", "write"]
        
        # Create refresh token with embedded user data
        initial_refresh = auth_service.jwt_handler.create_refresh_token(
            user_id, user_email, user_permissions
        )
        
        # First refresh
        result1 = await auth_service.refresh_tokens(initial_refresh)
        assert result1 is not None, "First refresh should succeed"
        access1, refresh1 = result1
        
        # Ensure timestamps are different
        time.sleep(0.001)
        
        # Second refresh (this is where the bug was - same token returned)
        result2 = await auth_service.refresh_tokens(refresh1)
        assert result2 is not None, "Second refresh should succeed"
        access2, refresh2 = result2
        
        # CRITICAL ASSERTIONS - these were failing in staging
        assert access1 != access2, "Access tokens MUST be different on each refresh"
        assert refresh1 != refresh2, "Refresh tokens MUST be different on each refresh"
        assert initial_refresh != refresh1, "New refresh token MUST differ from original"
        assert initial_refresh != refresh2, "All refresh tokens MUST be unique"
        
        # Verify tokens contain real user data, not placeholders
        access1_payload = auth_service.jwt_handler.validate_token(access1, "access")
        access2_payload = auth_service.jwt_handler.validate_token(access2, "access")
        
        assert access1_payload["email"] == "test@staging.netrasystems.ai"
        assert access2_payload["email"] == "test@staging.netrasystems.ai" 
        assert access1_payload["email"] != "user@example.com"
        assert access2_payload["email"] != "user@example.com"
    
    def test_jwt_handler_refresh_not_hardcoded(self, jwt_handler):
        """Test JWT handler doesn't use hardcoded placeholder values"""
        # Create refresh token with real user data
        user_id = "jwt-test-user"
        user_email = "jwt@staging.netrasystems.ai"
        user_permissions = ["admin"]
        
        refresh_token = jwt_handler.create_refresh_token(user_id, user_email, user_permissions)
        
        # Use JWT handler refresh method directly
        result = jwt_handler.refresh_access_token(refresh_token)
        assert result is not None
        
        new_access, new_refresh = result
        
        # Validate new tokens have real data
        access_payload = jwt_handler.validate_token(new_access, "access")
        refresh_payload = jwt_handler.validate_token(new_refresh, "refresh")
        
        # CRITICAL: These should not be placeholder values
        assert access_payload["email"] == "jwt@staging.netrasystems.ai"
        assert access_payload["email"] != "user@example.com", "Must not use hardcoded placeholder"
        assert refresh_payload["email"] == "jwt@staging.netrasystems.ai"
        assert refresh_payload["email"] != "user@example.com", "Must not use hardcoded placeholder"
    
    def test_refresh_token_contains_user_data_in_payload(self, jwt_handler):
        """Test that refresh tokens now contain user data needed for refresh"""
        user_id = "payload-test"
        user_email = "payloadtest@staging.netrasystems.ai"
        user_permissions = ["read", "write", "admin"]
        
        # Create refresh token
        refresh_token = jwt_handler.create_refresh_token(user_id, user_email, user_permissions)
        
        # Decode and verify it contains user data
        payload = jwt_handler.validate_token(refresh_token, "refresh")
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["email"] == user_email
        assert payload["permissions"] == user_permissions
        
        # This is what was missing before - refresh tokens need user data for proper refresh
    
    @pytest.mark.asyncio
    async def test_no_infinite_loop_scenario(self, auth_service):
        """Test the exact infinite loop scenario that was happening in staging"""
        # Simulate staging user
        user_id = "staging-user-001"
        user_email = "user@staging.netrasystems.ai"
        user_permissions = ["read", "write"]
        
        # Create initial refresh token
        original_refresh = auth_service.jwt_handler.create_refresh_token(
            user_id, user_email, user_permissions
        )
        
        # Perform 5 sequential refresh operations (simulating frontend retry loop)
        current_refresh = original_refresh
        all_tokens = []
        
        for i in range(5):
            result = await auth_service.refresh_tokens(current_refresh)
            assert result is not None, f"Refresh {i+1} should succeed"
            
            access, new_refresh = result
            all_tokens.extend([access, new_refresh])
            
            # CRITICAL: New refresh token must be different
            assert new_refresh != current_refresh, f"Refresh {i+1} must generate new token"
            
            # Use new refresh token for next iteration
            current_refresh = new_refresh
            time.sleep(0.001)  # Ensure different timestamps
        
        # All tokens should be unique (no duplicates that cause infinite loops)
        assert len(all_tokens) == len(set(all_tokens)), "All generated tokens must be unique"
        print(f"Successfully generated {len(all_tokens)} unique tokens - no infinite loop")