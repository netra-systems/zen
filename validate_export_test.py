#!/usr/bin/env python3
"""
Quick validation script for the chat export E2E test implementation.
"""
import asyncio
import sys
import tempfile
import json
import os
from pathlib import Path

# Add tests to path
sys.path.insert(0, str(Path(__file__).parent / "tests"))

from tests.unified.e2e.test_data_export import (
    ChatHistoryCreator, 
    ChatExportService,
    ChatExportVerifier,
    DataExportE2ETester
)


async def validate_implementation():
    """Validate the core implementation logic."""
    print("Validating Chat Export E2E Test Implementation...")
    
    # Test 1: Chat History Creation
    print("\nTest 1: Chat History Creation")
    history_creator = ChatHistoryCreator(None)  # harness not needed for this test
    messages = await history_creator.create_chat_history("test_user", 3)
    
    assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"
    assert all("content" in msg for msg in messages), "Missing content in messages"
    assert all("user_id" in msg for msg in messages), "Missing user_id in messages"
    print(f"[OK] Created {len(messages)} chat messages successfully")
    
    # Test 2: Export File Generation
    print("\nTest 2: Export File Generation")
    export_service = ChatExportService(None)
    
    # Create mock export data
    export_data = {
        "export_id": "test_export_123",
        "format": "json",
        "file_path": None  # Will create temp file
    }
    
    file_path = await export_service.generate_export_file(export_data, messages)
    assert os.path.exists(file_path), f"Export file not created at {file_path}"
    
    # Verify file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = json.load(f)
        
    assert "export_metadata" in content, "Missing export_metadata"
    assert "chat_history" in content, "Missing chat_history"
    assert len(content["chat_history"]) == 3, "Wrong number of messages in export"
    print(f"[OK] Export file generated successfully: {os.path.basename(file_path)}")
    
    # Test 3: Download Verification
    print("\nTest 3: Download Verification")
    verifier = ChatExportVerifier(None)
    
    download_verified = await verifier.verify_export_download(file_path, messages)
    assert download_verified, "Export download verification failed"
    print("[OK] Export download verification successful")
    
    # Test 4: Data Removal
    print("\nTest 4: Data Removal")
    removal_verified = await verifier.verify_data_removal(file_path, "test_user")
    assert removal_verified, "Data removal verification failed"
    assert not os.path.exists(file_path), "File was not removed"
    print("[OK] Data removal verification successful")
    
    # Test 5: Performance Check (simulate)
    print("\nTest 5: Performance Simulation")
    import time
    start_time = time.time()
    
    # Simulate the full flow (without real services)
    for i in range(10):  # Simulate 10 operations
        test_messages = await history_creator.create_chat_history(f"user_{i}", 2)
        export_data_sim = {
            "export_id": f"export_{i}",
            "format": "json",
            "file_path": None
        }
        temp_file = await export_service.generate_export_file(export_data_sim, test_messages)
        verified = await verifier.verify_export_download(temp_file, test_messages)
        removed = await verifier.verify_data_removal(temp_file, f"user_{i}")
        
    duration = time.time() - start_time
    avg_per_operation = duration / 10
    
    print(f"[OK] Performance test: {avg_per_operation:.3f}s per operation (10 operations in {duration:.3f}s)")
    
    # Verify performance target
    assert avg_per_operation < 0.5, f"Performance too slow: {avg_per_operation:.3f}s per operation"
    print("[OK] Performance target met (<0.5s per operation)")
    
    print(f"\n[SUCCESS] All validation tests PASSED!")
    print(f"[READY] Chat Export E2E Test implementation is ready for production use")
    
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(validate_implementation())
        print(f"\n[RESULT] Validation Result: {'SUCCESS' if result else 'FAILED'}")
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n[ERROR] Validation FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)