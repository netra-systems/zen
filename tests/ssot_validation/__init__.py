"""
SSOT Validation Test Suite

This test suite validates SERVICE_ID Single Source of Truth (SSOT) implementation
to prevent authentication cascade failures that affect $500K+ ARR.

Test Structure:

PHASE 1: FAILING TESTS (Expose Current SSOT Violations)
- test_service_id_ssot_violation_detection.py: Detect mixed hardcoded vs environment patterns
- test_service_id_cross_service_inconsistency.py: Expose auth/backend SERVICE_ID mismatches  
- test_service_id_environment_cascade_failure.py: Reproduce 60-second auth failures

PHASE 2: PASSING TESTS (Validate Ideal SSOT State)
- test_service_id_ssot_compliance.py: Validate single source of truth
- test_service_id_hardcoded_consistency.py: Verify all services use same constant
- test_service_id_auth_flow_stability.py: Confirm auth works with SSOT
- test_service_id_environment_independence.py: Validate independence from env vars
- test_golden_path_post_ssot_remediation.py: End-to-end login → AI responses

Business Value: Platform/Critical - Protects Golden Path user journey that delivers
90% of platform value through reliable authentication and AI response delivery.

Usage:
    # Run all SSOT validation tests
    python -m pytest tests/ssot_validation/ -v
    
    # Run only failing tests (Phase 1)
    python -m pytest tests/ssot_validation/test_service_id_*violation*.py -v
    
    # Run only passing tests (Phase 2)  
    python -m pytest tests/ssot_validation/test_service_id_*compliance*.py -v
"""

__version__ = "1.0.0"
__author__ = "Netra Systems SSOT Validation Team"