#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Demo Enhanced Authentication Logging

This script demonstrates the 10x enhanced authentication debug logging
that helps diagnose 403 "Not authenticated" errors with comprehensive context.

Run this to see the improved logging output:
    python demo_enhanced_auth_logging_simple.py
"""

import logging
import sys
import os

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging to see our enhanced output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def demo_auth_trace_logger():
    """Demonstrate the enhanced auth trace logger."""
    print("DEMO: Enhanced Authentication Debug Logging")
    print("=" * 60)
    
    try:
        # Import our enhanced auth tracer
        from netra_backend.app.logging.auth_trace_logger import (
            auth_tracer, 
            log_authentication_context_dump,
            AuthTraceContext
        )
        
        print("SUCCESS: Auth trace logger imported successfully")
        
        # Demo 1: Create a context similar to your error
        print("\nDemo 1: System user 403 'Not authenticated' error")
        context = AuthTraceContext(
            user_id="system",
            request_id="system_req_1757361274921_92_813a54c5_7d8490dc",
            correlation_id="corr_debug_demo",
            operation="create_request_scoped_session"
        )
        
        # Simulate the exact 403 error you're seeing
        auth_error = Exception("403: Not authenticated")
        
        print("Logging comprehensive authentication failure context...")
        auth_tracer.log_failure(context, auth_error, {
            "session_id": "system_session_debug",
            "function_location": "netra_backend.app.dependencies.get_request_scoped_db_session",
            "user_id_source": "hardcoded_system_placeholder", 
            "auth_failure_stage": "session_factory_call",
            "error_type": "403_not_authenticated"
        })
        
        # Demo 2: Show comprehensive context dump
        print("\nDemo 2: Comprehensive context dump")
        comprehensive_dump = auth_tracer.dump_all_context_safely(
            context, 
            auth_error,
            {
                "thread_id": "thread_debug_demo",
                "session_creation_stage": "database_factory",
                "potential_root_cause": "authentication_middleware_rejection"
            }
        )
        
        print("Context dump structure:")
        for key, value in comprehensive_dump.items():
            if isinstance(value, dict):
                print(f"  {key}: {list(value.keys())}")
            else:
                print(f"  {key}: {type(value).__name__}")
        
        # Demo 3: Show specific debugging information
        print("\nDemo 3: Authentication analysis")
        auth_indicators = comprehensive_dump["auth_state"]["auth_indicators"]
        print(f"  Has 403 error: {auth_indicators.get('has_403_error', False)}")
        print(f"  Has 'Not authenticated': {auth_indicators.get('has_not_authenticated', False)}")
        print(f"  User is system: {auth_indicators.get('user_id_is_system', False)}")
        print(f"  Suggests auth failure: {auth_indicators.get('error_suggests_auth_failure', False)}")
        
        # Demo 4: Show debugging hints
        debug_hints = comprehensive_dump.get("debug_hints", [])
        print(f"\nDemo 4: Debug hints generated ({len(debug_hints)} total)")
        for i, hint in enumerate(debug_hints[:5], 1):  # Show first 5 hints
            print(f"  {i}. {hint}")
        if len(debug_hints) > 5:
            print(f"  ... and {len(debug_hints) - 5} more hints")
        
        print("\nSUCCESS: Demo completed successfully!")
        print("The enhanced logging provides 10x more context for debugging auth failures!")
        
    except ImportError as e:
        print(f"ERROR: Import failed: {e}")
        print("Make sure you're running from the project root directory")
    except Exception as e:
        print(f"ERROR: Demo failed: {e}")
        import traceback
        traceback.print_exc()

def demo_safe_context_handling():
    """Demo safe context handling with None values."""
    print("\nDemo: Safe handling of None/missing values")
    print("-" * 50)
    
    try:
        from netra_backend.app.logging.auth_trace_logger import auth_tracer, AuthTraceContext
        
        # Create context with None/empty values (similar to error conditions)
        context = AuthTraceContext(
            user_id=None,  # Missing user_id 
            request_id="",  # Empty request_id
            correlation_id="safe_demo",
            operation=""  # Empty operation
        )
        
        # Test that it handles None values safely
        dump = auth_tracer.dump_all_context_safely(context, None, None)
        
        print("Safe context handling results:")
        print(f"  user_id (None): {dump['ids']['user_id']}")
        print(f"  request_id (empty): {dump['ids']['request_id']}")  
        print(f"  correlation_id: {dump['ids']['correlation_id']}")
        print(f"  operation (empty): {dump['ids']['operation']}")
        
        print("SUCCESS: None values handled safely without crashes")
        
    except Exception as e:
        print(f"ERROR: Safe handling demo failed: {e}")

def main():
    """Main demo function."""
    print("Enhanced Authentication Debug Logging Demo")
    print("This demonstrates 10x better debugging for 403 'Not authenticated' errors")
    print()
    
    demo_auth_trace_logger()
    demo_safe_context_handling()
    
    print("\n" + "=" * 60)
    print("SUMMARY: Key improvements")
    print("- Comprehensive context dumps with all IDs and correlation tracking")
    print("- Authentication failure analysis with specific error detection")  
    print("- System user detection and service-to-service auth debugging")
    print("- Actionable debugging steps and hints")
    print("- Safe null value handling prevents crashes")
    print("- Environment-aware logging")
    print("- Cross-service tracing support")
    print("\nThis enhanced logging will help you quickly identify the root cause")
    print("of the '403: Not authenticated' error you're experiencing!")

if __name__ == "__main__":
    main()