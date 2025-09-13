#!/usr/bin/env python3
"""
Simple validation test for Issue #803 fix.
This test verifies that the Thread/Run ID mismatch has been resolved.
"""

from shared.id_generation.unified_id_generator import UnifiedIdGenerator


def test_issue_803_fix_validation():
    """Test that thread_id and run_id now use consistent counters and shared UUIDs."""
    print("Issue #803 Fix Validation Test")
    print("=" * 40)

    # Generate multiple sets of IDs to test consistency
    test_cases = [
        ("user123", "operation1"),
        ("user456", "operation2"),
        ("user789", "operation3"),
    ]

    all_consistent = True

    for user_id, operation in test_cases:
        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(user_id, operation)

        print(f"\nTest Case: user_id={user_id}, operation={operation}")
        print(f"  thread_id:  {thread_id}")
        print(f"  run_id:     {run_id}")
        print(f"  request_id: {request_id}")

        # Parse the IDs to extract components
        thread_parts = thread_id.split('_')
        run_parts = run_id.split('_')

        # Expecting format: type_operation_counter_uuid
        thread_counter = int(thread_parts[2])
        run_counter = int(run_parts[2])
        thread_uuid = thread_parts[3]
        run_uuid = run_parts[3]

        print(f"  thread_counter: {thread_counter}")
        print(f"  run_counter:    {run_counter}")
        print(f"  thread_uuid:    {thread_uuid}")
        print(f"  run_uuid:       {run_uuid}")

        # Verify fix: counters should be the same
        counter_consistent = (thread_counter == run_counter)
        # Verify fix: UUIDs should be the same
        uuid_consistent = (thread_uuid == run_uuid)

        print(f"  Counter consistent: {counter_consistent}")
        print(f"  UUID consistent:    {uuid_consistent}")

        if not counter_consistent:
            print(f"  ERROR: COUNTER MISMATCH: thread={thread_counter}, run={run_counter}")
            all_consistent = False

        if not uuid_consistent:
            print(f"  ERROR: UUID MISMATCH: thread={thread_uuid}, run={run_uuid}")
            all_consistent = False

        if counter_consistent and uuid_consistent:
            print(f"  SUCCESS: IDs are properly consistent!")

    print("\n" + "=" * 40)
    if all_consistent:
        print("SUCCESS: Issue #803 fix is working correctly!")
        print("   All thread_id and run_id pairs use consistent counters and shared UUIDs.")
        return True
    else:
        print("FAILURE: Issue #803 fix is not working properly.")
        print("   Some thread_id and run_id pairs still have mismatched counters or UUIDs.")
        return False


if __name__ == "__main__":
    success = test_issue_803_fix_validation()
    exit(0 if success else 1)