"""
ID Format Sample Data for Testing ID System Inconsistencies

This module provides sample data that demonstrates the dual ID format
problem in the Netra codebase, where both uuid.uuid4() and UnifiedIDManager
are used, causing type confusion and validation inconsistencies.

Business Impact:
- Prevents proper audit trails
- Causes validation failures across modules
- Breaks type safety guarantees
- Leads to business logic errors in production
"""

import uuid
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class IDFormatSample:
    """Sample ID with metadata for testing purposes."""
    id_value: str
    format_type: str  # 'uuid' or 'unified'
    expected_validation: bool
    business_context: str
    generation_method: str


# Raw UUID Format Samples (Current Problem)
UUID_FORMAT_SAMPLES = [
    IDFormatSample(
        id_value=str(uuid.uuid4()),
        format_type="uuid",
        expected_validation=True,
        business_context="user_id from ExecutionContext line 70",
        generation_method="uuid.uuid4()"
    ),
    IDFormatSample(
        id_value=str(uuid.uuid4()),
        format_type="uuid", 
        expected_validation=True,
        business_context="execution_id from agent base",
        generation_method="uuid.uuid4()"
    ),
    IDFormatSample(
        id_value=str(uuid.uuid4()),
        format_type="uuid",
        expected_validation=True,
        business_context="websocket connection_id",
        generation_method="uuid.uuid4()"
    ),
]

# UnifiedIDManager Format Samples (Target Format)
UNIFIED_FORMAT_SAMPLES = [
    IDFormatSample(
        id_value="user_1_a1b2c3d4",
        format_type="unified",
        expected_validation=True,
        business_context="user_id from UnifiedIDManager",
        generation_method="UnifiedIDManager.generate_id(IDType.USER)"
    ),
    IDFormatSample(
        id_value="execution_1_e5f6g7h8",
        format_type="unified",
        expected_validation=True,
        business_context="execution_id from UnifiedIDManager",
        generation_method="UnifiedIDManager.generate_id(IDType.EXECUTION)"
    ),
    IDFormatSample(
        id_value="websocket_1_i9j0k1l2",
        format_type="unified",
        expected_validation=True,
        business_context="websocket_id from UnifiedIDManager",
        generation_method="UnifiedIDManager.generate_id(IDType.WEBSOCKET)"
    ),
    IDFormatSample(
        id_value="thread_1_m3n4o5p6",
        format_type="unified",
        expected_validation=True,
        business_context="thread_id from UnifiedIDManager",
        generation_method="UnifiedIDManager.generate_id(IDType.THREAD)"
    ),
]

# Mixed Format Scenarios (The Core Problem)
MIXED_FORMAT_SCENARIOS = [
    {
        "scenario_name": "uuid_passed_to_unified_validator",
        "uuid_id": str(uuid.uuid4()),
        "unified_validator_expects": "structured_format",
        "should_fail": True,
        "business_impact": "Validation fails unexpectedly in production"
    },
    {
        "scenario_name": "unified_id_passed_to_uuid_validator", 
        "unified_id": "user_1_a1b2c3d4",
        "uuid_validator_expects": "pure_uuid_format",
        "should_fail": True,
        "business_impact": "Type confusion in business logic"
    },
    {
        "scenario_name": "cross_service_id_contamination",
        "service_a_id": str(uuid.uuid4()),
        "service_b_expects": "unified_format",
        "should_fail": True,
        "business_impact": "Services cannot communicate properly"
    },
]

# Malformed ID Edge Cases
MALFORMED_ID_SAMPLES = [
    IDFormatSample(
        id_value="",
        format_type="empty",
        expected_validation=False,
        business_context="empty string edge case",
        generation_method="direct_assignment"
    ),
    IDFormatSample(
        id_value="not-a-uuid-or-structured",
        format_type="invalid",
        expected_validation=False,
        business_context="random string edge case",
        generation_method="direct_assignment"
    ),
    IDFormatSample(
        id_value="user_abc_def", # Missing numeric counter
        format_type="malformed_unified",
        expected_validation=False,
        business_context="incomplete unified format",
        generation_method="manual_construction"
    ),
]

# Business Requirement Validation Samples
BUSINESS_AUDIT_REQUIREMENTS = [
    {
        "requirement": "user_identification_traceability",
        "uuid_sample": str(uuid.uuid4()),
        "unified_sample": "user_1_a1b2c3d4",
        "audit_metadata_available": {
            "uuid": False,  # No metadata available
            "unified": True  # Has creation time, type, context
        },
        "business_compliance": {
            "uuid": False,  # Cannot meet audit requirements
            "unified": True  # Meets all audit requirements
        }
    },
    {
        "requirement": "execution_context_tracking",
        "uuid_sample": str(uuid.uuid4()),
        "unified_sample": "execution_1_e5f6g7h8",
        "context_embedding": {
            "uuid": False,  # No context information
            "unified": True  # Contains type and counter information
        },
        "debugging_capability": {
            "uuid": False,  # Cannot trace execution patterns
            "unified": True  # Can trace execution sequence
        }
    },
]

# Type Safety Violation Samples
TYPE_SAFETY_VIOLATIONS = [
    {
        "violation_type": "user_id_thread_id_mixing",
        "user_id_uuid": str(uuid.uuid4()),
        "thread_id_uuid": str(uuid.uuid4()),
        "problem": "Both are plain UUIDs, no type distinction",
        "business_risk": "User data leak to wrong thread"
    },
    {
        "violation_type": "execution_id_session_id_mixing",
        "execution_id_uuid": str(uuid.uuid4()),
        "session_id_uuid": str(uuid.uuid4()),
        "problem": "Cannot distinguish execution from session",
        "business_risk": "Security boundary violations"
    },
]

def get_uuid_samples() -> List[IDFormatSample]:
    """Get UUID format samples for testing."""
    return UUID_FORMAT_SAMPLES.copy()


def get_unified_samples() -> List[IDFormatSample]:
    """Get UnifiedIDManager format samples for testing."""
    return UNIFIED_FORMAT_SAMPLES.copy()


def get_mixed_scenarios() -> List[Dict[str, Any]]:
    """Get mixed format scenarios that should fail."""
    return MIXED_FORMAT_SCENARIOS.copy()


def get_malformed_samples() -> List[IDFormatSample]:
    """Get malformed ID samples for edge case testing."""
    return MALFORMED_ID_SAMPLES.copy()


def get_business_audit_samples() -> List[Dict[str, Any]]:
    """Get business audit requirement samples."""
    return BUSINESS_AUDIT_REQUIREMENTS.copy()


def get_type_safety_violations() -> List[Dict[str, Any]]:
    """Get type safety violation samples."""
    return TYPE_SAFETY_VIOLATIONS.copy()


def generate_fresh_uuid_sample() -> str:
    """Generate a fresh UUID for testing (demonstrates the problem)."""
    return str(uuid.uuid4())


def generate_unified_sample(id_type: str, counter: int = 1) -> str:
    """Generate a UnifiedIDManager-style sample (demonstrates the solution)."""
    uuid_part = str(uuid.uuid4())[:8]
    return f"{id_type}_{counter}_{uuid_part}"


# Constants for test validation
EXPECTED_UUID_PATTERN = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
EXPECTED_UNIFIED_PATTERN = r'^[a-z_]+_\d+_[0-9a-f]{8}$'

# Critical business scenarios that must be tested
CRITICAL_BUSINESS_SCENARIOS = [
    "multi_user_session_isolation",
    "agent_execution_traceability", 
    "websocket_connection_tracking",
    "audit_trail_compliance",
    "cross_service_id_validation",
    "type_safety_enforcement"
]