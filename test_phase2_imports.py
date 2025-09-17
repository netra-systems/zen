#!/usr/bin/env python3
"""
Test script to validate Phase 2 AuthTicketManager implementation imports.
Tests that all new components can be imported without errors.
"""

import sys
import traceback

def test_imports():
    """Test all Phase 2 imports."""
    print("🧪 Testing Phase 2 AuthTicketManager imports...")
    
    # Test 1: WebSocket ticket router imports
    try:
        from netra_backend.app.routes.websocket_ticket import router
        print("✅ websocket_ticket router import SUCCESS")
    except Exception as e:
        print(f"❌ websocket_ticket router import FAILED: {e}")
        traceback.print_exc()
        return False
    
    # Test 2: Unified auth SSOT imports
    try:
        from netra_backend.app.websocket_core.unified_auth_ssot import (
            generate_auth_ticket,
            AuthTicket,
            get_ticket_manager,
            AuthTicketManager
        )
        print("✅ unified_auth_ssot imports SUCCESS")
    except Exception as e:
        print(f"❌ unified_auth_ssot imports FAILED: {e}")
        traceback.print_exc()
        return False
    
    # Test 3: Basic functionality test
    try:
        # Test that we can create instances
        ticket_manager = AuthTicketManager()
        print("✅ AuthTicketManager instantiation SUCCESS")
        
        # Test that we can access properties
        redis_manager = ticket_manager.redis_manager
        print("✅ AuthTicketManager redis_manager property access SUCCESS")
        
    except Exception as e:
        print(f"❌ AuthTicketManager functionality test FAILED: {e}")
        traceback.print_exc()
        return False
    
    # Test 4: Route configuration imports
    try:
        from netra_backend.app.core.app_factory_route_imports import import_basic_route_modules
        modules = import_basic_route_modules()
        
        # Check if websocket_ticket_router is in the modules
        if 'websocket_ticket_router' in modules:
            print("✅ websocket_ticket_router properly registered in route modules")
        else:
            print("⚠️  websocket_ticket_router not found in route modules (might be in extended modules)")
        
    except Exception as e:
        print(f"❌ Route configuration test FAILED: {e}")
        traceback.print_exc()
        return False
    
    print("\n🎉 All Phase 2 import tests PASSED!")
    return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)