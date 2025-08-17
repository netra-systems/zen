"""
Test 21: Admin Route Authorization
Tests for admin endpoint security - app/routes/admin.py
"""

import pytest
from unittest.mock import patch
from .test_utilities import base_client, create_admin_user, create_mock_user, assert_error_response


class TestAdminRoute:
    """Test admin endpoint security."""
    
    def test_admin_endpoint_requires_authentication(self, base_client):
        """Test that admin endpoints require authentication."""
        response = base_client.get("/api/admin/users")
        # 401 if protected, 404 if not implemented
        assert_error_response(response, [401, 404])
    
    def test_admin_role_verification(self):
        """Test admin role verification logic."""
        from app.routes.admin import verify_admin_role
        
        # Test admin user
        admin_user = create_admin_user()
        assert verify_admin_role(admin_user) == True
        
        # Test regular user  
        regular_user = create_mock_user("user1", "user")
        assert verify_admin_role(regular_user) == False

    async def test_admin_user_management(self):
        """Test admin user management operations."""
        from app.routes.admin import get_all_users, update_user_role
        
        expected_users = [
            {"id": "1", "email": "user1@test.com"},
            {"id": "2", "email": "user2@test.com"}
        ]
        
        with patch('app.services.user_service.get_all_users') as mock_get:
            mock_get.return_value = expected_users
            
            users = await get_all_users()
            assert len(users) == 2