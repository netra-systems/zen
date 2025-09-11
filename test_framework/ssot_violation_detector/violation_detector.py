"""
SSOT Violation Detector

Core utility for detecting SSOT violations in message creation patterns.
Compares test framework message creation against canonical SSOT repository patterns.

Business Value:
- Prevents data corruption from bypassing repository patterns
- Ensures consistent message structure across platform
- Maintains audit trails and business logic integrity
- Provides automated detection of SSOT compliance violations
"""

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

# SSOT Imports - Absolute imports only
from test_framework.database_test_utilities import DatabaseTestUtilities
from netra_backend.app.services.database.message_repository import MessageRepository
from netra_backend.app.db.models_postgres import Message
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ViolationType(Enum):
    """Types of SSOT violations that can be detected."""
    STRUCTURE_MISMATCH = "structure_mismatch"
    FIELD_TYPE_MISMATCH = "field_type_mismatch"
    METADATA_INCONSISTENCY = "metadata_inconsistency"
    BUSINESS_LOGIC_BYPASS = "business_logic_bypass"
    TRANSACTION_HANDLING = "transaction_handling"
    AUDIT_TRAIL_MISSING = "audit_trail_missing"


@dataclass
class ViolationResult:
    """Result of SSOT violation detection."""
    violation_type: ViolationType
    severity: str  # "critical", "high", "medium", "low"
    description: str
    expected_value: Any
    actual_value: Any
    field_name: Optional[str] = None
    message_id: Optional[str] = None
    
    @property
    def is_critical(self) -> bool:
        """Check if this is a critical violation."""
        return self.severity == "critical"


@dataclass
class ComparisonReport:
    """Complete comparison report between SSOT and violation patterns."""
    ssot_message_id: str
    violation_message_id: str
    violations: List[ViolationResult]
    summary: Dict[str, Any]
    timestamp: float
    
    @property
    def has_critical_violations(self) -> bool:
        """Check if report contains critical violations."""
        return any(v.is_critical for v in self.violations)
    
    @property
    def violation_count_by_severity(self) -> Dict[str, int]:
        """Count violations by severity level."""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for violation in self.violations:
            counts[violation.severity] += 1
        return counts


class SSotViolationDetector:
    """
    SSOT Violation Detector
    
    Detects and analyzes SSOT violations by comparing message creation
    patterns between the proper SSOT repository and test framework violations.
    """
    
    def __init__(self):
        self.db_helper = DatabaseTestUtilities(service="netra_backend")
        self.message_repository = MessageRepository()
        
    async def detect_message_creation_violations(
        self, 
        thread_id: str,
        test_content: str = "SSOT violation detection test",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ComparisonReport:
        """
        Detect SSOT violations in message creation patterns.
        
        Creates identical messages using both SSOT repository and test framework,
        then compares the results to identify violations.
        
        Args:
            thread_id: Thread ID to create messages in
            test_content: Content for test messages
            metadata: Optional metadata for test messages
            
        Returns:
            ComparisonReport with detected violations
        """
        logger.info(f"Starting SSOT violation detection for thread: {thread_id}")
        
        test_metadata = metadata or {"test": "ssot_violation_detection"}
        violations = []
        
        async with self.db_helper.get_async_session() as session:
            # 1. Create message using SSOT repository (proper method)
            ssot_message = await self.message_repository.create_message(
                db=session,
                thread_id=thread_id,
                role="user",
                content=test_content,
                metadata=test_metadata
            )
            await session.commit()
            
            # 2. Create message using test framework (violation method)
            violation_message = await self.db_helper.create_message(
                thread_id=thread_id,
                role="user",
                content=test_content,
                metadata=test_metadata
            )
            
            # 3. Retrieve both messages from database for comparison
            ssot_db_msg = await session.get(Message, ssot_message.id)
            
            violation_db_result = await session.execute(
                select(Message).where(Message.thread_id == thread_id)
                .where(Message.id != ssot_message.id)
                .where(Message.role == "user")
            )
            violation_db_msg = violation_db_result.scalar_one_or_none()
            
            if not violation_db_msg:
                violations.append(ViolationResult(
                    violation_type=ViolationType.BUSINESS_LOGIC_BYPASS,
                    severity="critical",
                    description="Test framework failed to create message",
                    expected_value="Message created",
                    actual_value="No message created"
                ))
                
                return ComparisonReport(
                    ssot_message_id=ssot_message.id,
                    violation_message_id="none",
                    violations=violations,
                    summary={"fatal_error": "Test framework message creation failed"},
                    timestamp=time.time()
                )
            
            # 4. Perform detailed comparison
            violations.extend(await self._compare_message_structure(ssot_db_msg, violation_db_msg))
            violations.extend(await self._compare_message_fields(ssot_db_msg, violation_db_msg))
            violations.extend(await self._compare_message_metadata(ssot_db_msg, violation_db_msg))
            violations.extend(await self._compare_business_logic(ssot_db_msg, violation_db_msg))
            
            # 5. Generate summary
            summary = {
                "total_violations": len(violations),
                "critical_violations": len([v for v in violations if v.is_critical]),
                "ssot_object_type": ssot_db_msg.object,
                "violation_object_type": violation_db_msg.object,
                "content_structure_match": type(ssot_db_msg.content) == type(violation_db_msg.content),
                "metadata_structure_match": type(ssot_db_msg.metadata_) == type(violation_db_msg.metadata_)
            }
            
            return ComparisonReport(
                ssot_message_id=ssot_message.id,
                violation_message_id=violation_db_msg.id,
                violations=violations,
                summary=summary,
                timestamp=time.time()
            )
            
    async def _compare_message_structure(
        self, 
        ssot_msg: Message, 
        violation_msg: Message
    ) -> List[ViolationResult]:
        """Compare basic message structure between SSOT and violation."""
        violations = []
        
        # Object type comparison
        if ssot_msg.object != violation_msg.object:
            violations.append(ViolationResult(
                violation_type=ViolationType.STRUCTURE_MISMATCH,
                severity="critical",
                description="Message object type differs between SSOT and test framework",
                expected_value=ssot_msg.object,
                actual_value=violation_msg.object,
                field_name="object",
                message_id=violation_msg.id
            ))
            
        # Content structure comparison
        if type(ssot_msg.content) != type(violation_msg.content):
            violations.append(ViolationResult(
                violation_type=ViolationType.STRUCTURE_MISMATCH,
                severity="critical",
                description="Message content type differs between SSOT and test framework",
                expected_value=str(type(ssot_msg.content)),
                actual_value=str(type(violation_msg.content)),
                field_name="content",
                message_id=violation_msg.id
            ))
        elif isinstance(ssot_msg.content, list) and isinstance(violation_msg.content, list):
            # Deep content structure validation
            if len(ssot_msg.content) != len(violation_msg.content):
                violations.append(ViolationResult(
                    violation_type=ViolationType.STRUCTURE_MISMATCH,
                    severity="high",
                    description="Content array length differs",
                    expected_value=len(ssot_msg.content),
                    actual_value=len(violation_msg.content),
                    field_name="content.length",
                    message_id=violation_msg.id
                ))
            elif len(ssot_msg.content) > 0 and len(violation_msg.content) > 0:
                ssot_first = ssot_msg.content[0]
                violation_first = violation_msg.content[0]
                
                if isinstance(ssot_first, dict) and isinstance(violation_first, dict):
                    # Check content item structure
                    if ssot_first.get("type") != violation_first.get("type"):
                        violations.append(ViolationResult(
                            violation_type=ViolationType.STRUCTURE_MISMATCH,
                            severity="high",
                            description="Content item type differs",
                            expected_value=ssot_first.get("type"),
                            actual_value=violation_first.get("type"),
                            field_name="content[0].type",
                            message_id=violation_msg.id
                        ))
                        
        return violations
        
    async def _compare_message_fields(
        self, 
        ssot_msg: Message, 
        violation_msg: Message
    ) -> List[ViolationResult]:
        """Compare individual message fields between SSOT and violation."""
        violations = []
        
        # Required fields that should be consistent
        required_fields = ["id", "thread_id", "role", "file_ids", "metadata_"]
        
        for field in required_fields:
            ssot_value = getattr(ssot_msg, field, None)
            violation_value = getattr(violation_msg, field, None)
            
            # Type consistency check
            if type(ssot_value) != type(violation_value):
                violations.append(ViolationResult(
                    violation_type=ViolationType.FIELD_TYPE_MISMATCH,
                    severity="high",
                    description=f"Field '{field}' type differs between SSOT and test framework",
                    expected_value=str(type(ssot_value)),
                    actual_value=str(type(violation_value)),
                    field_name=field,
                    message_id=violation_msg.id
                ))
                
            # Special validations for specific fields
            if field == "file_ids":
                if not isinstance(violation_value, list):
                    violations.append(ViolationResult(
                        violation_type=ViolationType.STRUCTURE_MISMATCH,
                        severity="medium",
                        description="file_ids should be a list",
                        expected_value="list",
                        actual_value=str(type(violation_value)),
                        field_name=field,
                        message_id=violation_msg.id
                    ))
                    
        return violations
        
    async def _compare_message_metadata(
        self, 
        ssot_msg: Message, 
        violation_msg: Message
    ) -> List[ViolationResult]:
        """Compare metadata handling between SSOT and violation."""
        violations = []
        
        # Metadata structure check
        if type(ssot_msg.metadata_) != type(violation_msg.metadata_):
            violations.append(ViolationResult(
                violation_type=ViolationType.METADATA_INCONSISTENCY,
                severity="high",
                description="Metadata type differs between SSOT and test framework",
                expected_value=str(type(ssot_msg.metadata_)),
                actual_value=str(type(violation_msg.metadata_)),
                field_name="metadata_",
                message_id=violation_msg.id
            ))
            
        # If both are dicts, compare content handling
        if isinstance(ssot_msg.metadata_, dict) and isinstance(violation_msg.metadata_, dict):
            # Check if test metadata is preserved
            test_keys = ["test", "source", "created_by"]
            for key in test_keys:
                if key in ssot_msg.metadata_ and key in violation_msg.metadata_:
                    if ssot_msg.metadata_[key] != violation_msg.metadata_[key]:
                        violations.append(ViolationResult(
                            violation_type=ViolationType.METADATA_INCONSISTENCY,
                            severity="medium",
                            description=f"Metadata key '{key}' value differs",
                            expected_value=ssot_msg.metadata_[key],
                            actual_value=violation_msg.metadata_[key],
                            field_name=f"metadata_.{key}",
                            message_id=violation_msg.id
                        ))
                        
        return violations
        
    async def _compare_business_logic(
        self, 
        ssot_msg: Message, 
        violation_msg: Message
    ) -> List[ViolationResult]:
        """Compare business logic compliance between SSOT and violation."""
        violations = []
        
        # ID format validation - both should follow same pattern
        if ssot_msg.id.startswith("msg_") and not violation_msg.id.startswith("msg_"):
            violations.append(ViolationResult(
                violation_type=ViolationType.BUSINESS_LOGIC_BYPASS,
                severity="high",
                description="Message ID format differs - test framework not following SSOT pattern",
                expected_value="msg_* format",
                actual_value=violation_msg.id,
                field_name="id",
                message_id=violation_msg.id
            ))
            
        # Timestamp validation - should be recent and reasonable
        current_time = int(time.time())
        time_diff_ssot = abs(current_time - ssot_msg.created_at)
        time_diff_violation = abs(current_time - violation_msg.created_at)
        
        # Both should have reasonable timestamps (within last hour)
        if time_diff_ssot > 3600:
            violations.append(ViolationResult(
                violation_type=ViolationType.AUDIT_TRAIL_MISSING,
                severity="medium",
                description="SSOT message timestamp is too old",
                expected_value="Recent timestamp",
                actual_value=ssot_msg.created_at,
                field_name="created_at",
                message_id=ssot_msg.id
            ))
            
        if time_diff_violation > 3600:
            violations.append(ViolationResult(
                violation_type=ViolationType.AUDIT_TRAIL_MISSING,
                severity="medium",
                description="Test framework message timestamp is too old",
                expected_value="Recent timestamp",
                actual_value=violation_msg.created_at,
                field_name="created_at",
                message_id=violation_msg.id
            ))
            
        return violations
        
    async def batch_detect_violations(
        self, 
        thread_ids: List[str],
        parallel_limit: int = 5
    ) -> List[ComparisonReport]:
        """
        Detect violations across multiple threads in parallel.
        
        Args:
            thread_ids: List of thread IDs to test
            parallel_limit: Maximum parallel detections
            
        Returns:
            List of ComparisonReports for each thread
        """
        logger.info(f"Starting batch violation detection for {len(thread_ids)} threads")
        
        semaphore = asyncio.Semaphore(parallel_limit)
        
        async def detect_single(thread_id: str) -> ComparisonReport:
            async with semaphore:
                try:
                    return await self.detect_message_creation_violations(
                        thread_id=thread_id,
                        test_content=f"Batch detection test for {thread_id}"
                    )
                except Exception as e:
                    logger.error(f"Violation detection failed for thread {thread_id}: {e}")
                    return ComparisonReport(
                        ssot_message_id="error",
                        violation_message_id="error",
                        violations=[ViolationResult(
                            violation_type=ViolationType.BUSINESS_LOGIC_BYPASS,
                            severity="critical",
                            description=f"Detection failed: {str(e)}",
                            expected_value="Successful detection",
                            actual_value=f"Error: {str(e)}"
                        )],
                        summary={"error": str(e)},
                        timestamp=time.time()
                    )
                    
        tasks = [detect_single(thread_id) for thread_id in thread_ids]
        reports = await asyncio.gather(*tasks)
        
        logger.info(f"Batch violation detection completed - {len(reports)} reports generated")
        return reports