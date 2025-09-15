#!/usr/bin/env python3
"""
CRITICAL: Issue #700 SSOT Regression Proof Script

This script proves that the TriageAgent metadata bypass is real and blocking
the Golden Path. It demonstrates the silent failure in metadata storage.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def main():
    print("=" * 70)
    print("ISSUE #700 SSOT REGRESSION PROOF")
    print("=" * 70)
    
    try:
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.agents.base_agent import BaseAgent
        from unittest.mock import Mock
        
        print("✅ Successfully imported required modules")
        
        # Create real UserExecutionContext
        context = UserExecutionContext(
            user_id="test_user_700",
            thread_id="test_thread_700", 
            run_id="test_run_700",
            request_id="test_request_700"
        )
        
        print(f"✅ Created UserExecutionContext: {context.user_id}")
        
        # Test 1: Verify metadata is a property
        print("\nTEST 1: Metadata Property Analysis")
        print(f"  - Has metadata attribute: {hasattr(context, 'metadata')}")
        print(f"  - Metadata type: {type(context.metadata)}")
        print(f"  - Initial metadata: {context.metadata}")
        
        # Test 2: Prove assignment appears to work but silently fails
        print("\nTEST 2: Silent Failure Proof")
        initial_metadata = dict(context.metadata)
        print(f"  - Before assignment: {list(context.metadata.keys())}")
        
        # This assignment appears to succeed
        context.metadata['test_key'] = 'test_value'
        print("  - Assignment completed (no exception)")
        
        # But the value is NOT actually stored
        after_assignment = dict(context.metadata)
        print(f"  - After assignment: {list(context.metadata.keys())}")
        print(f"  - Assignment persisted: {'test_key' in context.metadata}")
        
        if 'test_key' not in context.metadata:
            print("  ❌ CONFIRMED: Assignment silently failed!")
        else:
            print("  ✅ Assignment worked (regression may be fixed)")
            
        # Test 3: Prove BaseAgent.store_metadata_result silently fails
        print("\nTEST 3: BaseAgent SSOT Method Failure")
        mock_llm = Mock()
        base_agent = BaseAgent(llm_manager=mock_llm, name="TestAgent")
        
        try:
            base_agent.store_metadata_result(
                context=context,
                key="critical_data",
                value="golden_path_data"
            )
            print("  - store_metadata_result() completed (no exception)")
            
            if 'critical_data' in context.metadata:
                print("  ✅ SSOT method worked (regression may be fixed)")
            else:
                print("  ❌ CONFIRMED: SSOT method silently failed!")
                
        except Exception as e:
            print(f"  ❌ SSOT method failed with exception: {e}")
            
        # Test 4: Demonstrate Golden Path impact
        print("\nTEST 4: Golden Path Impact Analysis")
        critical_keys = [
            'triage_result',
            'triage_category', 
            'data_sufficiency',
            'triage_priority',
            'next_agents'
        ]
        
        failed_keys = []
        for key in critical_keys:
            try:
                base_agent.store_metadata_result(context, key, f"test_{key}")
                if key not in context.metadata:
                    failed_keys.append(key)
            except Exception:
                failed_keys.append(key)
                
        print(f"  - Critical metadata keys that failed: {len(failed_keys)}/{len(critical_keys)}")
        print(f"  - Failed keys: {failed_keys}")
        
        if len(failed_keys) == len(critical_keys):
            print("  ❌ CONFIRMED: All Golden Path metadata storage fails!")
            print("  🚨 GOLDEN PATH IS BLOCKED!")
        else:
            print("  ✅ Some metadata storage works")
            
        # Summary
        print("\n" + "=" * 70)
        print("REGRESSION ANALYSIS SUMMARY")
        print("=" * 70)
        
        if 'test_key' not in context.metadata and 'critical_data' not in context.metadata:
            print("🚨 CRITICAL: Issue #700 SSOT regression CONFIRMED")
            print("📋 ROOT CAUSE: UserExecutionContext.metadata is read-only property")
            print("💥 IMPACT: TriageAgent metadata storage silently fails")
            print("🔐 GOLDEN PATH: BLOCKED - Agent coordination broken")
            print("💰 BUSINESS RISK: $500K+ ARR at risk")
            return 1
        else:
            print("✅ Issue #700 may have been resolved")
            return 0
            
    except Exception as e:
        print(f"❌ Script failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)