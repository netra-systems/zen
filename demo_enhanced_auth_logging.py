#!/usr/bin/env python
"""Demo Enhanced Authentication Logging

This script demonstrates the 10x enhanced authentication debug logging
that helps diagnose 403 "Not authenticated" errors with comprehensive context.

Run this to see the improved logging output:
    python demo_enhanced_auth_logging.py
"""

import logging
import asyncio
from datetime import datetime, timezone

# Set up logging to see our enhanced output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('auth_debug_demo.log')
    ]
)

logger = logging.getLogger(__name__)

async def demo_enhanced_auth_logging():
    """Demonstrate enhanced authentication logging."""
    print("🚀 DEMO: Enhanced Authentication Debug Logging")
    print("=" * 60)
    
    try:
        # Import our enhanced auth tracer
        from netra_backend.app.logging.auth_trace_logger import (
            auth_tracer, 
            log_authentication_context_dump,
            AuthTraceContext
        )
        
        print("✅ Auth trace logger imported successfully")
        
        # Demo 1: Basic context dump without error
        print("\n📍 Demo 1: Successful authentication context")
        log_authentication_context_dump(
            user_id="demo_user",
            request_id="demo_req_001",
            operation="demo_successful_operation",
            session_id="demo_session_123",
            auth_status="success",
            demo_note="This shows what successful auth context looks like"
        )
        
        # Demo 2: System user authentication failure (the main issue)
        print("\n🔴 Demo 2: System user 403 'Not authenticated' error")
        context = AuthTraceContext(
            user_id="system",
            request_id="system_req_002", 
            correlation_id="system_corr_456",
            operation="create_request_scoped_session"
        )
        
        # Simulate the exact 403 error you're seeing
        auth_error = Exception("403: Not authenticated")
        
        auth_tracer.log_failure(context, auth_error, {
            "session_id": "system_session_789",
            "function_location": "netra_backend.app.dependencies.get_request_scoped_db_session",
            "user_id_source": "hardcoded_system_placeholder", 
            "auth_failure_stage": "session_factory_call"
        })
        
        # Demo 3: Comprehensive context dump
        print("\n📊 Demo 3: Comprehensive context dump")
        comprehensive_dump = auth_tracer.dump_all_context_safely(
            context, 
            auth_error,
            {
                "thread_id": "demo_thread_101",
                "correlation_id": "demo_corr_202",
                "session_creation_stage": "database_factory",
                "potential_root_cause": "authentication_middleware_rejection"
            }
        )
        
        print("Comprehensive dump keys:", list(comprehensive_dump.keys()))
        print("Auth indicators:", comprehensive_dump["auth_state"]["auth_indicators"])
        print("Debug hints count:", len(comprehensive_dump.get("debug_hints", [])))
        
        # Demo 4: Environment detection
        print("\n🌍 Demo 4: Environment detection") 
        print(f"Development: {auth_tracer._is_development_env()}")
        print(f"Staging: {auth_tracer._is_staging_env()}")
        print(f"Production: {auth_tracer._is_production_env()}")
        
        print("\n✅ Demo completed successfully!")
        print("📄 Check 'auth_debug_demo.log' for detailed log output")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running from the project root directory")
    except Exception as e:
        print(f"❌ Demo error: {e}")
        import traceback
        traceback.print_exc()

async def demo_dependencies_logging():
    """Demo the enhanced logging in dependencies.py."""
    print("\n🔧 DEMO: Dependencies Enhanced Logging")
    print("=" * 60)
    
    try:
        # This will demonstrate the enhanced logging we added to dependencies.py
        from netra_backend.app.dependencies import get_request_scoped_db_session
        
        print("Attempting to create request-scoped session (this may fail but will show enhanced logs)...")
        
        try:
            async for session in get_request_scoped_db_session():
                print(f"✅ Session created successfully: {type(session)}")
                break
        except Exception as e:
            print(f"⚠️  Session creation failed (expected): {e}")
            print("💡 Check the logs above for enhanced debugging context")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main():
    """Main demo function."""
    print("🎯 Enhanced Authentication Debug Logging Demo")
    print("This demonstrates 10x better debugging for 403 'Not authenticated' errors")
    print()
    
    # Run async demos
    asyncio.run(demo_enhanced_auth_logging())
    
    print("\n" + "=" * 60)
    asyncio.run(demo_dependencies_logging())
    
    print("\n🎉 Demo completed!")
    print("💡 Key improvements:")
    print("   - Comprehensive context dumps with all IDs")
    print("   - Authentication failure analysis")  
    print("   - System user detection and debugging")
    print("   - Cross-service correlation tracking")
    print("   - Actionable debugging steps")
    print("   - Safe null value handling")

if __name__ == "__main__":
    main()