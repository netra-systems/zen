"""
MISSION CRITICAL: SSOT Message Repository Compliance Test Suite

This test suite is designed to EXPOSE and VALIDATE the SSOT violation in:
test_framework/ssot/database.py:596 - Direct session.add() instead of MessageRepository.create_message()

CRITICAL: These tests are designed to FAIL initially (before remediation) to expose the violation.
After proper SSOT remediation, these tests should PASS.

Business Value:
- Ensures consistent message creation across the entire platform
- Validates proper message structure and metadata handling
- Prevents data corruption from bypassing repository patterns
- Maintains audit trails and business logic consistency

SSOT Reference: netra_backend/app/services/database/message_repository.py
Violation Location: test_framework/ssot/database.py:596
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
import pytest

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

# SSOT Imports - Absolute imports only
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.database import DatabaseTestUtility
from netra_backend.app.services.database.message_repository import MessageRepository
from netra_backend.app.db.models_postgres import Message, Thread
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestSSotMessageRepositoryCompliance:
    """
    Mission Critical Test Suite: SSOT Message Repository Compliance
    
    These tests are designed to FAIL when the SSOT violation exists,
    and PASS after proper remediation is applied.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) if hasattr(super(), '__init__') else None
        self.message_repository = MessageRepository()
        self.db_helper = DatabaseTestUtility(service="netra_backend")
        
    async def setup_method(self):
        """Setup for each test with clean database state."""
        # Ensure we have a test thread for message operations
        self.test_thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        
        # Clean up any existing test data
        await self._cleanup_test_data()
        
        logger.info(f"SSOT Test Setup Complete - Thread ID: {self.test_thread_id}")
        
    async def teardown_method(self):
        """Clean up test data."""
        await self._cleanup_test_data()
        
    async def _cleanup_test_data(self):
        """Remove test data from database."""
        async with self.db_helper.get_async_session() as session:
            # Clean messages
            await session.execute(
                text("DELETE FROM message WHERE thread_id LIKE :pattern"),
                {"pattern": f"{self.test_thread_id}%"}
            )
            # Clean threads  
            await session.execute(
                text("DELETE FROM thread WHERE id LIKE :pattern"),
                {"pattern": f"{self.test_thread_id}%"}
            )
            await session.commit()
            
    @pytest.mark.asyncio
    async def test_ssot_message_creation_structure_compliance(self):
        """
        CRITICAL TEST: Validate SSOT message creation produces proper structure.
        
        This test EXPOSES the violation by comparing:
        1. Messages created via proper SSOT MessageRepository.create_message()
        2. Messages created via test framework's direct session.add() violation
        
        EXPECTED BEHAVIOR: Test should FAIL initially due to structure differences.
        """
        logger.info("=== SSOT MESSAGE STRUCTURE COMPLIANCE TEST ===")
        
        async with self.db_helper.get_async_session() as session:
            # 1. Create message using PROPER SSOT method (MessageRepository)
            ssot_message = await self.message_repository.create_message(
                db=session,
                thread_id=self.test_thread_id,
                role="user",
                content="SSOT test message",
                metadata={"test_source": "ssot_repository"}
            )
            await session.commit()
            
            # 2. Create message using TEST FRAMEWORK (which has SSOT violation)
            # This will use the violating code path in test_framework/ssot/database.py:596
            violation_message = await self.db_helper.create_test_message(
                session=session,
                thread_id=self.test_thread_id,
                role="user", 
                content=[{"type": "text", "text": {"value": "Test framework violation message"}}],
                metadata_={"test_source": "test_framework"}
            )
            
            # 3. CRITICAL COMPARISON - These should be IDENTICAL in structure
            # If they differ, it exposes the SSOT violation
            
            # Validate SSOT message structure (proper format)
            self.assertIsNotNone(ssot_message, "SSOT repository should create message")
            self.assertEqual(ssot_message.object, "thread.message", "SSOT message should have proper object type")
            self.assertIsInstance(ssot_message.content, list, "SSOT message content should be list")
            self.assertEqual(len(ssot_message.content), 1, "SSOT message should have one content item")
            self.assertEqual(ssot_message.content[0]["type"], "text", "SSOT content should be text type")
            self.assertIn("value", ssot_message.content[0]["text"], "SSOT text should have value field")
            
            # Validate violation message structure (will be different due to violation)
            # This part will expose the violation by showing structural differences
            violation_result = await session.execute(
                select(Message).where(Message.thread_id == self.test_thread_id)
                .where(Message.content.op('->>')('0') != None)  # Look for messages with content
            )
            violation_messages = violation_result.scalars().all()
            
            # Find the violation message (not created by SSOT repository)
            violation_db_message = None
            for msg in violation_messages:
                if msg.id != ssot_message.id:
                    violation_db_message = msg
                    break
                    
            self.assertIsNotNone(violation_db_message, "Test framework should create message")
            
            # CRITICAL ASSERTION: Structure should be IDENTICAL (will FAIL due to violation)
            self.assertEqual(
                ssot_message.object, 
                violation_db_message.object,
                "SSOT VIOLATION DETECTED: object field mismatch between SSOT and test framework"
            )
            
            self.assertEqual(
                type(ssot_message.content),
                type(violation_db_message.content),
                "SSOT VIOLATION DETECTED: content type mismatch between SSOT and test framework"
            )
            
            # This assertion will FAIL and expose the violation
            self.assertEqual(
                ssot_message.content[0]["type"] if ssot_message.content else None,
                violation_db_message.content[0]["type"] if violation_db_message.content else None,
                "SSOT VIOLATION DETECTED: content structure differs between SSOT repository and test framework"
            )
            
        logger.info("SSOT Message Structure Compliance Test Completed")
        
    @pytest.mark.asyncio  
    async def test_ssot_message_metadata_consistency(self):
        """
        CRITICAL TEST: Validate metadata handling consistency.
        
        This test exposes violations in metadata field handling between
        the proper SSOT repository and the test framework violation.
        """
        logger.info("=== SSOT MESSAGE METADATA CONSISTENCY TEST ===")
        
        test_metadata = {
            "source": "compliance_test",
            "priority": "high",
            "tags": ["ssot", "validation"]
        }
        
        async with self.db_helper.get_async_session() as session:
            # 1. Create via SSOT repository (proper method)
            ssot_message = await self.message_repository.create_message(
                db=session,
                thread_id=self.test_thread_id,
                role="assistant", 
                content="SSOT metadata test",
                metadata=test_metadata
            )
            await session.commit()
            
            # 2. Create via test framework (violation)
            await self.db_helper.create_message(
                thread_id=self.test_thread_id,
                role="assistant",
                content="Violation metadata test", 
                metadata=test_metadata
            )
            
            # 3. Compare metadata handling
            all_messages = await session.execute(
                select(Message).where(Message.thread_id == self.test_thread_id)
                .where(Message.role == "assistant")
            )
            messages = all_messages.scalars().all()
            
            self.assertEqual(len(messages), 2, "Should have two assistant messages")
            
            # Find SSOT vs violation messages
            ssot_msg = next(msg for msg in messages if msg.id == ssot_message.id)
            violation_msg = next(msg for msg in messages if msg.id != ssot_message.id)
            
            # CRITICAL: Metadata should be handled identically (will FAIL due to violation)
            self.assertEqual(
                ssot_msg.metadata_,
                violation_msg.metadata_,
                "SSOT VIOLATION DETECTED: Metadata handling differs between SSOT and test framework"
            )
            
            # Validate specific metadata fields
            for key, value in test_metadata.items():
                ssot_value = ssot_msg.metadata_.get(key) if ssot_msg.metadata_ else None
                violation_value = violation_msg.metadata_.get(key) if violation_msg.metadata_ else None
                
                self.assertEqual(
                    ssot_value,
                    violation_value, 
                    f"SSOT VIOLATION DETECTED: Metadata field '{key}' differs between SSOT and test framework"
                )
                
        logger.info("SSOT Message Metadata Consistency Test Completed")
        
    @pytest.mark.asyncio
    async def test_ssot_message_field_completeness(self):
        """
        CRITICAL TEST: Validate all required fields are set properly.
        
        This test ensures the SSOT repository creates complete message records
        while exposing any field omissions in the test framework violation.
        """
        logger.info("=== SSOT MESSAGE FIELD COMPLETENESS TEST ===")
        
        required_fields = [
            "id", "object", "created_at", "thread_id", "role", 
            "content", "assistant_id", "run_id", "file_ids", "metadata_"
        ]
        
        async with self.db_helper.get_async_session() as session:
            # Create via SSOT repository (proper method)
            ssot_message = await self.message_repository.create_message(
                db=session,
                thread_id=self.test_thread_id,
                role="user",
                content="Field completeness test",
                assistant_id="asst_test",
                run_id="run_test"
            )
            await session.commit()
            
            # Validate all required fields are present and properly typed
            for field in required_fields:
                field_value = getattr(ssot_message, field, None)
                
                # Critical assertions for proper SSOT structure
                if field == "object":
                    self.assertEqual(field_value, "thread.message", f"Field '{field}' should be 'thread.message'")
                elif field == "content":
                    self.assertIsInstance(field_value, list, f"Field '{field}' should be list")
                    self.assertGreater(len(field_value), 0, f"Field '{field}' should not be empty")
                elif field == "file_ids":
                    self.assertIsInstance(field_value, list, f"Field '{field}' should be list")
                elif field == "metadata_":
                    self.assertIsInstance(field_value, dict, f"Field '{field}' should be dict")
                elif field in ["id", "thread_id"]:
                    self.assertIsNotNone(field_value, f"Field '{field}' should not be None")
                    self.assertIsInstance(field_value, str, f"Field '{field}' should be string")
                elif field == "created_at":
                    self.assertIsNotNone(field_value, f"Field '{field}' should not be None")
                    self.assertIsInstance(field_value, int, f"Field '{field}' should be integer timestamp")
                    
            # Now test the framework violation path
            await self.db_helper.create_message(
                thread_id=self.test_thread_id,
                role="user",
                content="Framework violation test",
                assistant_id="asst_test",
                run_id="run_test"
            )
            
            # Get the violation message
            violation_result = await session.execute(
                select(Message).where(Message.thread_id == self.test_thread_id)
                .where(Message.id != ssot_message.id)
            )
            violation_message = violation_result.scalar_one_or_none()
            
            self.assertIsNotNone(violation_message, "Test framework should create message")
            
            # CRITICAL: Compare field completeness (will expose violation)
            for field in required_fields:
                ssot_value = getattr(ssot_message, field, None)
                violation_value = getattr(violation_message, field, None)
                
                # Type consistency check
                self.assertEqual(
                    type(ssot_value),
                    type(violation_value),
                    f"SSOT VIOLATION DETECTED: Field '{field}' type differs between SSOT and test framework"
                )
                
                # Special validation for critical fields
                if field == "object":
                    self.assertEqual(
                        ssot_value,
                        violation_value,
                        f"SSOT VIOLATION DETECTED: Critical field '{field}' differs between SSOT and test framework"
                    )
                    
        logger.info("SSOT Message Field Completeness Test Completed")
        
    @pytest.mark.asyncio
    async def test_ssot_message_creation_audit_trail(self):
        """
        CRITICAL TEST: Validate audit trail and business logic consistency.
        
        This test ensures the SSOT repository maintains proper audit trails
        while exposing any business logic bypassing in the violation.
        """
        logger.info("=== SSOT MESSAGE AUDIT TRAIL TEST ===")
        
        async with self.db_helper.get_async_session() as session:
            # Track creation timestamps before operations
            before_time = int(time.time())
            
            # Create via SSOT repository (with proper business logic)
            ssot_message = await self.message_repository.create_message(
                db=session,
                thread_id=self.test_thread_id,
                role="user",
                content="Audit trail test SSOT"
            )
            await session.commit()
            
            after_ssot_time = int(time.time())
            
            # Small delay to ensure timestamp difference
            await asyncio.sleep(0.1)
            
            # Create via test framework (violation - may bypass business logic)
            await self.db_helper.create_message(
                thread_id=self.test_thread_id,
                role="user", 
                content="Audit trail test violation"
            )
            
            after_violation_time = int(time.time())
            
            # Validate audit trail consistency
            
            # 1. SSOT message should have proper timestamp
            self.assertGreaterEqual(ssot_message.created_at, before_time)
            self.assertLessEqual(ssot_message.created_at, after_ssot_time)
            
            # 2. Get violation message for comparison
            violation_result = await session.execute(
                select(Message).where(Message.thread_id == self.test_thread_id)
                .where(Message.id != ssot_message.id)
            )
            violation_message = violation_result.scalar_one_or_none()
            
            self.assertIsNotNone(violation_message, "Test framework should create message")
            
            # 3. CRITICAL: Timestamp handling should be consistent (may expose violation)
            timestamp_difference = abs(ssot_message.created_at - violation_message.created_at)
            
            # Both should use similar timestamp generation logic
            self.assertLess(
                timestamp_difference, 
                60,  # Should be within 60 seconds
                "SSOT VIOLATION DETECTED: Timestamp generation differs significantly between SSOT and test framework"
            )
            
            # 4. ID generation pattern should be consistent
            self.assertTrue(
                ssot_message.id.startswith("msg_"),
                "SSOT message ID should follow proper pattern"
            )
            
            self.assertTrue(
                violation_message.id.startswith("msg_"),
                "SSOT VIOLATION DETECTED: Test framework message ID should follow SSOT pattern"
            )
            
        logger.info("SSOT Message Audit Trail Test Completed")


class TestSSotMessageRepositoryIntegration:
    """
    Additional integration tests for SSOT message repository compliance
    that require broader system integration.
    """
    
    @pytest.mark.asyncio
    async def test_ssot_message_repository_transaction_consistency(self):
        """
        CRITICAL TEST: Validate transaction consistency between SSOT and test framework.
        
        This test ensures both creation methods handle transactions properly
        and expose any transaction handling differences.
        """
        db_helper = DatabaseTestUtility(service="netra_backend")
        message_repository = MessageRepository()
        test_thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        
        async with db_helper.get_async_session() as session:
            try:
                # Create multiple messages in transaction
                ssot_msg1 = await message_repository.create_message(
                    db=session,
                    thread_id=test_thread_id,
                    role="user",
                    content="Transaction test 1"
                )
                
                # Don't commit yet - test transaction state
                violation_msg = await db_helper.create_message(
                    thread_id=test_thread_id,
                    role="assistant",
                    content="Transaction test 2"
                )
                
                # Both should be in same transaction state
                uncommitted_count = await session.execute(
                    select(text("count(*)")).select_from(
                        select(Message).where(Message.thread_id == test_thread_id)
                    )
                )
                count = uncommitted_count.scalar()
                
                # CRITICAL: Both creation methods should participate in same transaction
                assert count >= 2, "SSOT VIOLATION: Transaction isolation differs between SSOT and test framework"
                
                await session.commit()
                
                # Verify final state
                final_result = await session.execute(
                    select(Message).where(Message.thread_id == test_thread_id)
                )
                final_messages = final_result.scalars().all()
                
                assert len(final_messages) == 2, "Both messages should be committed"
                
            finally:
                # Cleanup
                await session.execute(
                    text("DELETE FROM message WHERE thread_id = :thread_id"),
                    {"thread_id": test_thread_id}
                )
                await session.commit()


if __name__ == "__main__":
    # Run the compliance test suite
    import sys
    import os
    
    # Add project root to path for imports
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sys.path.insert(0, project_root)
    
    # Configure logging for test execution
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run tests
    pytest.main([__file__, "-v", "-s"])