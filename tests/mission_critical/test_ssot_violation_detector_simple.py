"""
Simple SSOT Violation Detection Test

This is a simplified test to validate the SSOT violation detection concept.
It directly tests the violation at test_framework/ssot/database.py:596.

EXPECTED BEHAVIOR: This test should FAIL initially, exposing the SSOT violation.
After remediation, the test should PASS.
"""

import asyncio
import sys
import time
import uuid
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from test_framework.ssot.database import DatabaseTestUtility
from netra_backend.app.services.database.message_repository import MessageRepository
from netra_backend.app.db.models_postgres import Message


class TestSSOTViolationDetection:
    """
    Simple SSOT Violation Detection Test
    
    This test compares message creation between:
    1. Proper SSOT MessageRepository (correct method)
    2. Test framework DatabaseTestUtility (violation method)
    """
    
    def __init__(self):
        self.message_repository = MessageRepository()
        self.db_helper = DatabaseTestUtility(service="netra_backend")
        self.test_thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        
    @pytest.mark.asyncio
    async def test_ssot_violation_structure_difference(self):
        """
        CRITICAL TEST: Expose SSOT violation through structure comparison.
        
        This test should FAIL initially because the test framework
        bypasses SSOT repository patterns at line 596.
        """
        print("=== SSOT VIOLATION DETECTION TEST ===")
        
        # Get database session from test utility
        await self.db_helper.initialize()
        session = await self.db_helper.get_test_session()
        
        try:
            # 1. Create message using PROPER SSOT repository
            ssot_message = await self.message_repository.create_message(
                db=session,
                thread_id=self.test_thread_id,
                role="user",
                content="SSOT test message",
                metadata={"source": "ssot_repository"}
            )
            await session.commit()
            
            print(f"SSOT Message Created: {ssot_message.id}")
            print(f"SSOT Message Object: {ssot_message.object}")
            print(f"SSOT Message Content Type: {type(ssot_message.content)}")
            print(f"SSOT Message Content: {ssot_message.content}")
            
            # 2. Create message using TEST FRAMEWORK (VIOLATION)
            # This will trigger the violation at test_framework/ssot/database.py:596
            violation_message = await self.db_helper.create_test_message(
                session=session,
                thread_id=self.test_thread_id,
                role="user",
                content=[{"type": "text", "text": {"value": "Test framework violation message"}}],
                metadata_={"source": "test_framework"}
            )
            await session.commit()
            
            print(f"Violation Message Created: {violation_message.id}")
            print(f"Violation Message Object: {violation_message.object}")
            print(f"Violation Message Content Type: {type(violation_message.content)}")
            print(f"Violation Message Content: {violation_message.content}")
            
            # 3. CRITICAL COMPARISON - Structure should be identical
            # If this assertion fails, it exposes the SSOT violation
            
            print("\n=== CRITICAL COMPARISON ===")
            
            # Object type consistency
            print(f"Object Type Match: {ssot_message.object} == {violation_message.object}")
            assert ssot_message.object == violation_message.object, (
                f"SSOT VIOLATION DETECTED: object field differs - SSOT: '{ssot_message.object}' vs Violation: '{violation_message.object}'"
            )
            
            # Content structure consistency
            print(f"Content Type Match: {type(ssot_message.content)} == {type(violation_message.content)}")
            assert type(ssot_message.content) == type(violation_message.content), (
                f"SSOT VIOLATION DETECTED: content type differs - SSOT: {type(ssot_message.content)} vs Violation: {type(violation_message.content)}"
            )
            
            # Content format validation
            if isinstance(ssot_message.content, list) and isinstance(violation_message.content, list):
                if len(ssot_message.content) > 0 and len(violation_message.content) > 0:
                    ssot_content_item = ssot_message.content[0]
                    violation_content_item = violation_message.content[0]
                    
                    print(f"Content Structure Match: {ssot_content_item} == {violation_content_item}")
                    assert ssot_content_item.get("type") == violation_content_item.get("type"), (
                        f"SSOT VIOLATION DETECTED: content structure differs - SSOT: {ssot_content_item} vs Violation: {violation_content_item}"
                    )
            
            # Metadata handling consistency
            print(f"Metadata Type Match: {type(ssot_message.metadata_)} == {type(violation_message.metadata_)}")
            assert type(ssot_message.metadata_) == type(violation_message.metadata_), (
                f"SSOT VIOLATION DETECTED: metadata type differs - SSOT: {type(ssot_message.metadata_)} vs Violation: {type(violation_message.metadata_)}"
            )
            
            print("\n✅ ALL SSOT COMPLIANCE CHECKS PASSED")
            print("If you see this message, the SSOT violation has been fixed!")
            
            # Clean up test data
            await session.execute(
                text("DELETE FROM message WHERE thread_id = :thread_id"),
                {"thread_id": self.test_thread_id}
            )
            await session.commit()
            
        finally:
            # Clean up session
            await self.db_helper.close_session(session)
            await self.db_helper.cleanup()


if __name__ == "__main__":
    # Simple test runner
    test_instance = TestSSOTViolationDetection()
    
    async def run_test():
        try:
            await test_instance.test_ssot_violation_structure_difference()
            print("\n🎉 TEST PASSED - SSOT compliance verified!")
        except AssertionError as e:
            print(f"\n🚨 TEST FAILED - SSOT violation detected: {e}")
            print("\nThis is EXPECTED behavior before remediation!")
            return False
        except Exception as e:
            print(f"\n💥 TEST ERROR: {e}")
            return False
        return True
    
    # Run the test
    print("Running SSOT Violation Detection Test...")
    result = asyncio.run(run_test())
    
    if not result:
        print("\n📋 REMEDIATION REQUIRED:")
        print("1. Fix test_framework/ssot/database.py:596")
        print("2. Replace 'session.add(message_data)' with MessageRepository.create_message()")
        print("3. Re-run this test to validate the fix")
    
    exit(0 if result else 1)