"""
Test to validate Issue #1176 Phase 3 AuthService import fix.

This test ensures that AuthService can be imported correctly from the auth integration module,
preventing import errors that block auth integration and golden path functionality.
"""
import pytest


class TestAuthServiceImportFix:
    """Test AuthService import compatibility after Issue #1176 Phase 3 fix."""
    
    def test_auth_service_import_success(self):
        """Test that AuthService can be imported successfully."""
        try:
            from netra_backend.app.auth_integration.auth import AuthService
            assert AuthService is not None
            assert callable(AuthService)  # Should be a class
        except ImportError as e:
            pytest.fail(f"AuthService import failed: {e}")
    
    def test_auth_service_is_backend_auth_integration(self):
        """Test that AuthService is properly aliased to BackendAuthIntegration."""
        from netra_backend.app.auth_integration.auth import AuthService, BackendAuthIntegration
        
        # AuthService should be an alias for BackendAuthIntegration
        assert AuthService is BackendAuthIntegration
    
    def test_auth_service_instantiation(self):
        """Test that AuthService can be instantiated."""
        from netra_backend.app.auth_integration.auth import AuthService
        
        # Should be able to create an instance
        auth_service = AuthService()
        assert auth_service is not None
        assert hasattr(auth_service, 'validate_request_token')
        assert hasattr(auth_service, 'refresh_user_token')
    
    def test_auth_service_in_all_exports(self):
        """Test that AuthService is included in __all__ exports."""
        from netra_backend.app.auth_integration import auth
        
        # AuthService should be in the __all__ list
        assert hasattr(auth, '__all__')
        assert 'AuthService' in auth.__all__
    
    def test_backward_compatibility_imports(self):
        """Test that all expected auth components can be imported."""
        try:
            from netra_backend.app.auth_integration.auth import (
                AuthService,
                AuthUser,
                BackendAuthIntegration,
                AuthIntegrationService,
                auth_client,
                get_current_user,
                get_auth_client
            )
            
            # All imports should succeed
            assert AuthService is not None
            assert AuthUser is not None
            assert BackendAuthIntegration is not None
            assert AuthIntegrationService is not None
            assert auth_client is not None
            assert get_current_user is not None
            assert get_auth_client is not None
            
        except ImportError as e:
            pytest.fail(f"Backward compatibility import failed: {e}")
    
    def test_auth_user_is_user_alias(self):
        """Test that AuthUser is properly aliased to User."""
        from netra_backend.app.auth_integration.auth import AuthUser
        from netra_backend.app.db.models_postgres import User
        
        # AuthUser should be an alias for User
        assert AuthUser is User
    
    def test_auth_service_methods_available(self):
        """Test that AuthService has expected methods for auth integration."""
        from netra_backend.app.auth_integration.auth import AuthService
        
        auth_service = AuthService()
        
        # Check that key methods are available
        assert hasattr(auth_service, 'validate_request_token')
        assert hasattr(auth_service, 'refresh_user_token')
        assert hasattr(auth_service, 'auth_client')
        
        # Methods should be callable
        assert callable(auth_service.validate_request_token)
        assert callable(auth_service.refresh_user_token)


if __name__ == "__main__":
    # Simple direct test execution
    test_instance = TestAuthServiceImportFix()
    
    try:
        test_instance.test_auth_service_import_success()
        print("✅ AuthService import test passed")
        
        test_instance.test_auth_service_is_backend_auth_integration()
        print("✅ AuthService alias test passed")
        
        test_instance.test_auth_service_instantiation()
        print("✅ AuthService instantiation test passed")
        
        test_instance.test_auth_service_in_all_exports()
        print("✅ AuthService exports test passed")
        
        test_instance.test_backward_compatibility_imports()
        print("✅ Backward compatibility imports test passed")
        
        test_instance.test_auth_user_is_user_alias()
        print("✅ AuthUser alias test passed")
        
        test_instance.test_auth_service_methods_available()
        print("✅ AuthService methods test passed")
        
        print("\n🎉 All AuthService import fix tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise