"""
Unit tests for UserUpdate schema regression prevention.

This test suite specifically targets the regression fixed in commit 7a9f176cb:
- UserUpdate schema must have all optional fields (not inherit required fields from UserBase)
- CRUDUser initialization must include required service_name and model_class parameters

The regression occurred because:
1. UserUpdate inherited from UserBase, making email field required for updates
2. CRUDUser instances were created without required constructor parameters

These tests ensure that the UserUpdate schema behaves correctly for partial updates
and that CRUDUser can be properly initialized in test scenarios.
"""

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.db.models_postgres import User
from netra_backend.app.schemas.user import UserUpdate
from netra_backend.app.services.user_service import CRUDUser


class TestUserUpdateSchemaRegression:
    """Test UserUpdate schema regression prevention."""

    def test_user_update_all_fields_optional(self):
        """Test that all UserUpdate fields are optional (regression prevention)."""
        # This should not raise any validation errors - all fields are optional
        update_data = UserUpdate()
        assert update_data.email is None
        assert update_data.full_name is None
        assert update_data.picture is None
        assert update_data.is_active is None

    def test_user_update_partial_fields(self):
        """Test UserUpdate with only some fields provided."""
        # Test with only email
        update_data = UserUpdate(email="new@example.com")
        assert update_data.email == "new@example.com"
        assert update_data.full_name is None
        assert update_data.picture is None
        assert update_data.is_active is None

        # Test with only full_name
        update_data = UserUpdate(full_name="New Name")
        assert update_data.email is None
        assert update_data.full_name == "New Name"
        assert update_data.picture is None
        assert update_data.is_active is None

        # Test with only is_active
        update_data = UserUpdate(is_active=False)
        assert update_data.email is None
        assert update_data.full_name is None
        assert update_data.picture is None
        assert update_data.is_active is False

    def test_user_update_model_dump_exclude_unset(self):
        """Test that UserUpdate.model_dump(exclude_unset=True) works correctly for partial updates."""
        # Create update with only some fields
        update_data = UserUpdate(email="test@example.com", full_name="Test User")
        
        # Dump only the set fields
        dumped = update_data.model_dump(exclude_unset=True)
        
        # Should only include the fields that were explicitly set
        assert dumped == {
            "email": "test@example.com",
            "full_name": "Test User"
        }
        
        # Should not include unset fields
        assert "picture" not in dumped
        assert "is_active" not in dumped

    def test_user_update_empty_construction_valid(self):
        """Test that UserUpdate can be constructed with no parameters (regression test)."""
        # This was the core issue - UserUpdate inherited from UserBase which had required fields
        # Now UserUpdate should be constructible with no parameters
        try:
            update_data = UserUpdate()
            # If we reach this point, construction succeeded
            assert isinstance(update_data, UserUpdate)
        except ValidationError as e:
            pytest.fail(f"UserUpdate() construction failed with validation error: {e}")

    def test_user_update_serialization_deserialization(self):
        """Test UserUpdate serialization and deserialization preserves optional nature."""
        # Create update with mixed data
        original = UserUpdate(
            email="test@example.com",
            full_name=None,  # Explicitly None
            picture="https://example.com/pic.jpg",
            is_active=True
        )
        
        # Serialize and deserialize
        serialized = original.model_dump()
        deserialized = UserUpdate(**serialized)
        
        # All fields should match
        assert deserialized.email == "test@example.com"
        assert deserialized.full_name is None
        assert deserialized.picture == "https://example.com/pic.jpg"
        assert deserialized.is_active is True


class TestCRUDUserInitializationRegression:
    """Test CRUDUser initialization regression prevention."""

    def test_crud_user_initialization_with_required_params(self):
        """Test that CRUDUser can be initialized with required parameters (regression prevention)."""
        # The regression was that CRUDUser() was called without required parameters
        # CRUDUser extends EnhancedCRUDService which requires service_name and model_class
        
        try:
            crud_user = CRUDUser("test_user_service", User)
            assert crud_user is not None
            assert hasattr(crud_user, 'get_by_email')
            assert hasattr(crud_user, 'create')
            assert hasattr(crud_user, 'update')
        except Exception as e:
            pytest.fail(f"CRUDUser initialization failed: {e}")

    def test_crud_user_initialization_fails_without_params(self):
        """Test that CRUDUser fails when initialized without required parameters."""
        # This confirms that the regression would be caught
        with pytest.raises(TypeError):
            # This should fail because service_name and model_class are required
            CRUDUser()

    def test_crud_user_service_name_stored(self):
        """Test that CRUDUser stores the service name correctly."""
        service_name = "test_crud_service"
        crud_user = CRUDUser(service_name, User)
        
        # The service should store the service name for identification
        assert hasattr(crud_user, 'service_name')
        assert crud_user.service_name == service_name

    def test_crud_user_model_class_stored(self):
        """Test that CRUDUser stores the model class correctly."""
        crud_user = CRUDUser("test_service", User)
        
        # The service should have access to the model class
        # Check through the base class attributes (stored as _model_class)
        assert hasattr(crud_user, '_model_class')
        assert crud_user._model_class == User

    def test_crud_user_has_expected_methods(self):
        """Test that CRUDUser has all expected CRUD methods."""
        crud_user = CRUDUser("test_service", User)
        
        # Core CRUD methods that should be available
        expected_methods = [
            'get_by_email',
            'create',
            'update',
            'get',
            'remove',
            'get_multi',
            'get_or_create'
        ]
        
        for method_name in expected_methods:
            assert hasattr(crud_user, method_name), f"Missing method: {method_name}"
            assert callable(getattr(crud_user, method_name)), f"Method not callable: {method_name}"


class TestUserUpdateSchemaCompatibility:
    """Test UserUpdate schema compatibility with update operations."""

    def test_user_update_works_with_dict_conversion(self):
        """Test that UserUpdate works correctly when converted to dict for database updates."""
        update_data = UserUpdate(
            email="updated@example.com",
            full_name="Updated Name"
        )
        
        # Test model_dump with exclude_unset (used in update operations)
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # Should only contain the fields that were set
        expected_fields = {"email", "full_name"}
        assert set(update_dict.keys()) == expected_fields
        
        # Values should be correct
        assert update_dict["email"] == "updated@example.com"
        assert update_dict["full_name"] == "Updated Name"

    def test_user_update_none_values_handled_correctly(self):
        """Test that UserUpdate handles None values correctly in updates."""
        # Create update that explicitly sets some fields to None
        update_data = UserUpdate(
            email="test@example.com",
            full_name=None,  # Explicitly set to None
            is_active=False
        )
        
        # When excluding unset, None values that were explicitly set should be included
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # Should include explicitly set None values
        assert "email" in update_dict
        assert "full_name" in update_dict
        assert "is_active" in update_dict
        
        # Values should be correct
        assert update_dict["email"] == "test@example.com"
        assert update_dict["full_name"] is None
        assert update_dict["is_active"] is False

    def test_user_update_empty_update_safe(self):
        """Test that empty UserUpdate objects are safe for update operations."""
        update_data = UserUpdate()
        
        # Empty update should result in empty dict when excluding unset
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # Should be empty - no fields were set
        assert update_dict == {}
        
        # This should be safe for database update operations
        # (no fields to update means no changes made)