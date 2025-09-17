#!/usr/bin/env python3
"""
Validation script for Issue #1296 Phase 2 implementation

Tests:
- WebSocket ticket endpoint implementation
- Route registration and configuration 
- AuthTicketManager integration
- Pydantic model validation
"""

import sys
import traceback


def test_endpoint_imports():
    """Test that endpoint modules can be imported successfully."""
    print("🔍 Testing endpoint imports...")
    
    try:
        from netra_backend.app.routes.websocket_ticket import (
            generate_websocket_ticket,
            validate_websocket_ticket,
            revoke_websocket_ticket,
            get_ticket_system_status,
            TicketGenerationRequest,
            TicketGenerationResponse,
            TicketValidationResponse
        )
        print("✅ All endpoint functions imported successfully")
        return True
    except Exception as e:
        print(f"❌ Endpoint import failed: {e}")
        traceback.print_exc()
        return False


def test_route_registration():
    """Test that the router is properly registered in the app factory system."""
    print("🔍 Testing route registration...")
    
    try:
        from netra_backend.app.core.app_factory_route_imports import import_all_route_modules
        modules = import_all_route_modules()
        
        if 'websocket_ticket_router' in modules:
            print("✅ WebSocket ticket router found in import system")
            
            # Test route configuration
            from netra_backend.app.core.app_factory_route_configs import get_all_route_configurations
            configs = get_all_route_configurations(modules)
            
            if 'websocket_ticket' in configs:
                router, prefix, tags = configs['websocket_ticket']
                print(f"✅ Router configuration found: prefix='{prefix}', tags={tags}")
                return True
            else:
                print("❌ Router configuration not found")
                return False
        else:
            print("❌ WebSocket ticket router not found in import system")
            print(f"Available routers: {list(modules.keys())}")
            return False
            
    except Exception as e:
        print(f"❌ Route registration test failed: {e}")
        traceback.print_exc()
        return False


def test_auth_integration():
    """Test AuthTicketManager integration works correctly."""
    print("🔍 Testing AuthTicketManager integration...")
    
    try:
        from netra_backend.app.websocket_core.unified_auth_ssot import (
            generate_auth_ticket,
            validate_auth_ticket,
            revoke_auth_ticket,
            get_ticket_manager,
            ticket_manager,
            AuthTicket
        )
        print("✅ AuthTicketManager integration imports successful")
        
        # Test that ticket manager instance exists
        manager = get_ticket_manager()
        if manager:
            print("✅ Ticket manager instance accessible")
            return True
        else:
            print("❌ Ticket manager instance not found")
            return False
            
    except Exception as e:
        print(f"❌ AuthTicketManager integration test failed: {e}")
        traceback.print_exc()
        return False


def test_pydantic_models():
    """Test Pydantic model validation works correctly."""
    print("🔍 Testing Pydantic model validation...")
    
    try:
        from netra_backend.app.routes.websocket_ticket import (
            TicketGenerationRequest,
            TicketGenerationResponse,
            TicketValidationResponse
        )
        import time
        
        # Test request model with defaults
        default_request = TicketGenerationRequest()
        assert default_request.ttl_seconds == 300
        assert default_request.single_use == True
        print("✅ Default request model validation works")
        
        # Test request model with custom values
        custom_request = TicketGenerationRequest(
            ttl_seconds=600,
            single_use=False,
            permissions=["read", "write"],
            metadata={"test": "data"}
        )
        assert custom_request.ttl_seconds == 600
        assert custom_request.single_use == False
        print("✅ Custom request model validation works")
        
        # Test response model
        response = TicketGenerationResponse(
            ticket_id="test_ticket_123",
            expires_at=time.time() + 300,
            created_at=time.time(),
            ttl_seconds=300,
            single_use=True,
            websocket_url="wss://example.com/ws?ticket=test_ticket_123"
        )
        assert response.ticket_id == "test_ticket_123"
        assert "test_ticket_123" in response.websocket_url
        print("✅ Response model validation works")
        
        # Test validation response model
        validation_response = TicketValidationResponse(
            valid=True,
            user_id="test_user",
            email="test@example.com",
            permissions=["read"],
            expires_at=time.time() + 300
        )
        assert validation_response.valid == True
        print("✅ Validation response model works")
        
        return True
        
    except Exception as e:
        print(f"❌ Pydantic model test failed: {e}")
        traceback.print_exc()
        return False


def test_websocket_integration():
    """Test WebSocket authentication integration."""
    print("🔍 Testing WebSocket authentication integration...")
    
    try:
        from netra_backend.app.websocket_core.unified_auth_ssot import (
            UnifiedWebSocketAuthenticator,
            websocket_authenticator
        )
        
        # Check that authenticator exists and has ticket methods
        if hasattr(websocket_authenticator, '_validate_ticket_auth'):
            print("✅ WebSocket authenticator has ticket validation method")
            
        if hasattr(websocket_authenticator, '_extract_ticket_from_query_params'):
            print("✅ WebSocket authenticator has ticket extraction method")
            
        if hasattr(websocket_authenticator, '_ticket_manager'):
            print("✅ WebSocket authenticator has ticket manager")
            return True
        else:
            print("❌ WebSocket authenticator missing ticket manager")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket integration test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("🚀 Starting Issue #1296 Phase 2 Implementation Validation")
    print("="*60)
    
    tests = [
        test_endpoint_imports,
        test_route_registration,
        test_auth_integration,
        test_pydantic_models,
        test_websocket_integration
    ]
    
    results = []
    for test in tests:
        print()
        result = test()
        results.append(result)
        
    print()
    print("="*60)
    print("📊 VALIDATION SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✅ ALL TESTS PASSED! Phase 2 implementation is ready.")
        print()
        print("🎯 Ready for:")
        print("  - Staging deployment testing")
        print("  - End-to-end WebSocket authentication with tickets")
        print("  - Integration with frontend WebSocket connections")
        print("  - Redis functionality validation in live environment")
        
        return 0
    else:
        print(f"❌ {total - passed} tests failed. Implementation needs fixes.")
        return 1


if __name__ == "__main__":
    sys.exit(main())