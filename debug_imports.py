#!/usr/bin/env python3
"""Debug imports to see what's happening with MessageRouter"""

def debug_message_router_imports():
    """Debug MessageRouter import behavior"""
    
    print("🔍 Debugging MessageRouter imports...")
    
    try:
        # First import handlers module and inspect it
        import netra_backend.app.websocket_core.handlers as handlers_module
        print(f"\n📦 Handlers Module: {handlers_module}")
        
        # Check what MessageRouter is in the module
        if hasattr(handlers_module, 'MessageRouter'):
            mr = handlers_module.MessageRouter
            print(f"   MessageRouter found: {mr}")
            print(f"   MessageRouter ID: {id(mr)}")
            print(f"   MessageRouter type: {type(mr)}")
            print(f"   MessageRouter MRO: {mr.__mro__ if hasattr(mr, '__mro__') else 'N/A'}")
            
            # Try to inspect source
            import inspect
            try:
                source_info = inspect.getsourcefile(mr)
                print(f"   Source file: {source_info}")
                line_no = inspect.getsourcelines(mr)[1] if hasattr(mr, '__name__') else 'N/A'
                print(f"   Line number: {line_no}")
            except Exception as e:
                print(f"   Source inspection failed: {e}")
        else:
            print("   MessageRouter NOT FOUND in handlers module")
            
        # List all attributes that contain "MessageRouter"
        router_attrs = [attr for attr in dir(handlers_module) if 'MessageRouter' in attr]
        print(f"   All Router attributes: {router_attrs}")
        
        # Now check quality router
        print(f"\n📦 Quality Message Router:")
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        print(f"   QualityMessageRouter: {QualityMessageRouter}")
        print(f"   QualityMessageRouter ID: {id(QualityMessageRouter)}")
        print(f"   QualityMessageRouter MRO: {QualityMessageRouter.__mro__}")
        
        # Check canonical router directly
        print(f"\n📦 Canonical Message Router:")
        from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
        print(f"   CanonicalMessageRouter: {CanonicalMessageRouter}")
        print(f"   CanonicalMessageRouter ID: {id(CanonicalMessageRouter)}")
        
    except Exception as e:
        print(f"❌ Debug error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_message_router_imports()