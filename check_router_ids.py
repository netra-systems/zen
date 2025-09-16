#!/usr/bin/env python3
"""
Quick script to check MessageRouter object IDs for Issue #220 SSOT consolidation
"""

def check_router_object_ids():
    """Check object IDs of different MessageRouter imports"""
    
    print("🔍 Checking MessageRouter object IDs for SSOT consolidation...")
    
    try:
        # Import from handlers.py
        from netra_backend.app.websocket_core.handlers import MessageRouter
        print(f"MessageRouter from handlers.py: ID {id(MessageRouter)}")
        
        # Import from quality_message_router.py  
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        print(f"QualityMessageRouter from quality_message_router.py: ID {id(QualityMessageRouter)}")
        
        # Import canonical router
        try:
            from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
            print(f"CanonicalMessageRouter from canonical_message_router.py: ID {id(CanonicalMessageRouter)}")
        except Exception as e:
            print(f"⚠️ Could not import CanonicalMessageRouter: {e}")
            CanonicalMessageRouter = None
        
        # Check if they are the same objects
        print("\n📊 SSOT Analysis:")
        if id(MessageRouter) == id(QualityMessageRouter):
            print("✅ MessageRouter and QualityMessageRouter are the SAME object (SSOT compliant)")
        else:
            print("❌ MessageRouter and QualityMessageRouter are DIFFERENT objects (SSOT violation)")
            print(f"   MessageRouter ID: {id(MessageRouter)}")
            print(f"   QualityMessageRouter ID: {id(QualityMessageRouter)}")
            
        # Check inheritance hierarchy
        if CanonicalMessageRouter:
            print("\n🏗️ Inheritance Analysis:")
            print(f"MessageRouter inherits from CanonicalMessageRouter: {issubclass(MessageRouter, CanonicalMessageRouter)}")
            print(f"QualityMessageRouter inherits from CanonicalMessageRouter: {issubclass(QualityMessageRouter, CanonicalMessageRouter)}")
            print(f"MessageRouter is CanonicalMessageRouter: {MessageRouter is CanonicalMessageRouter}")
            print(f"QualityMessageRouter is CanonicalMessageRouter: {QualityMessageRouter is CanonicalMessageRouter}")
        
        # Show class names for clarity
        print("\n🏷️ Class Names:")
        print(f"MessageRouter.__name__: {MessageRouter.__name__}")
        print(f"QualityMessageRouter.__name__: {QualityMessageRouter.__name__}")
        if CanonicalMessageRouter:
            print(f"CanonicalMessageRouter.__name__: {CanonicalMessageRouter.__name__}")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    check_router_object_ids()