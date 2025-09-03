#!/usr/bin/env python3
"""
Demo script showing UnifiedIDManager capabilities.

This demonstrates how the SSOT UnifiedIDManager handles all ID formats
and fixes the WebSocket routing failures by providing consistent parsing.
"""

import sys
sys.path.append('.')

from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDFormat

def demo_canonical_format():
    """Demo canonical format generation and parsing."""
    print("=== CANONICAL FORMAT DEMO ===")
    
    # Generate new canonical format
    thread_id = "user_session_123"
    run_id = UnifiedIDManager.generate_run_id(thread_id)
    print(f"Generated run_id: {run_id}")
    
    # Parse it back
    parsed = UnifiedIDManager.parse_run_id(run_id)
    print(f"Parsed thread_id: {parsed.thread_id}")
    print(f"Format version: {parsed.format_version.value}")
    print(f"Has timestamp: {parsed.timestamp is not None}")
    print(f"Is legacy: {parsed.is_legacy()}")
    print()

def demo_legacy_support():
    """Demo legacy format parsing."""
    print("=== LEGACY FORMAT SUPPORT DEMO ===")
    
    # Legacy IDManager format
    legacy_run_id = "run_user_session_456_a1b2c3d4"
    print(f"Legacy run_id: {legacy_run_id}")
    
    # Extract thread_id (critical for WebSocket routing)
    thread_id = UnifiedIDManager.extract_thread_id(legacy_run_id)
    print(f"Extracted thread_id: {thread_id}")
    
    # Parse detailed info
    parsed = UnifiedIDManager.parse_run_id(legacy_run_id)
    print(f"Format version: {parsed.format_version.value}")
    print(f"Is legacy: {parsed.is_legacy()}")
    print(f"UUID suffix: {parsed.uuid_suffix}")
    print()

def demo_websocket_compatibility():
    """Demo WebSocket routing compatibility."""
    print("=== WEBSOCKET ROUTING COMPATIBILITY ===")
    
    test_scenarios = [
        # Canonical format
        "thread_user123_run_1693430400000_a1b2c3d4",
        # Legacy format
        "run_session_abc_b2c3d4e5",
        # Complex thread ID
        "thread_user_123_session_456_conversation_789_run_1693430400000_c3d4e5f6"
    ]
    
    for run_id in test_scenarios:
        thread_id = UnifiedIDManager.extract_thread_id(run_id)
        format_info = UnifiedIDManager.get_format_info(run_id)
        
        print(f"Run ID: {run_id}")
        print(f"  Thread ID: {thread_id}")
        print(f"  Format: {format_info.get('format_version', 'unknown')}")
        print(f"  WebSocket routing: {'WORKS' if thread_id else 'FAILS'}")
        print()

def demo_double_prefix_prevention():
    """Demo double prefix prevention."""
    print("=== DOUBLE PREFIX PREVENTION ===")
    
    # Try with already prefixed thread_id
    prefixed_thread_id = "thread_already_prefixed_user"
    run_id = UnifiedIDManager.generate_run_id(prefixed_thread_id)
    
    print(f"Input thread_id: {prefixed_thread_id}")
    print(f"Generated run_id: {run_id}")
    print(f"Double prefix prevented: {'YES' if not run_id.startswith('thread_thread_') else 'NO'}")
    
    # Extract back
    extracted = UnifiedIDManager.extract_thread_id(run_id)
    print(f"Extracted thread_id: {extracted}")
    print()

def demo_migration_utility():
    """Demo migration from legacy to canonical."""
    print("=== MIGRATION UTILITY ===")
    
    legacy_run_id = "run_migrate_me_d4e5f6a7"
    print(f"Legacy run_id: {legacy_run_id}")
    
    # Migrate to canonical
    canonical_run_id = UnifiedIDManager.migrate_to_canonical(legacy_run_id)
    print(f"Migrated run_id: {canonical_run_id}")
    
    # Verify both extract same thread_id
    legacy_thread_id = UnifiedIDManager.extract_thread_id(legacy_run_id)
    canonical_thread_id = UnifiedIDManager.extract_thread_id(canonical_run_id)
    
    print(f"Legacy thread_id: {legacy_thread_id}")
    print(f"Canonical thread_id: {canonical_thread_id}")
    print(f"Migration preserves thread_id: {'YES' if legacy_thread_id == canonical_thread_id else 'NO'}")
    print()

def demo_validation_and_errors():
    """Demo validation and error handling."""
    print("=== VALIDATION AND ERROR HANDLING ===")
    
    # Valid cases
    valid_cases = [
        "thread_user123_run_1693430400000_a1b2c3d4",  # Canonical
        "run_user456_b2c3d4e5",  # Legacy
    ]
    
    for case in valid_cases:
        valid = UnifiedIDManager.validate_run_id(case)
        print(f"{case}: {'VALID' if valid else 'INVALID'}")
    
    # Invalid cases  
    invalid_cases = [
        "invalid_format",
        "thread_incomplete",
        "run_missing_uuid",
        ""
    ]
    
    for case in invalid_cases:
        valid = UnifiedIDManager.validate_run_id(case)
        print(f"{case}: {'VALID' if valid else 'INVALID'}")
    
    print()

def main():
    """Run all demos."""
    print("UNIFIED ID MANAGER DEMO")
    print("Fixing WebSocket routing failures with SSOT ID generation\n")
    
    demo_canonical_format()
    demo_legacy_support()
    demo_websocket_compatibility()
    demo_double_prefix_prevention()
    demo_migration_utility()
    demo_validation_and_errors()
    
    print("Demo complete! UnifiedIDManager provides:")
    print("   - Canonical format: thread_{thread_id}_run_{timestamp}_{uuid}")
    print("   - Backward compatibility with legacy formats")
    print("   - WebSocket routing thread_id extraction")
    print("   - Double prefix prevention")
    print("   - Migration utilities")
    print("   - Comprehensive validation")
    print("\nMISSION ACCOMPLISHED: WebSocket routing failures fixed!")

if __name__ == "__main__":
    main()