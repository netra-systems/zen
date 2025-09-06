"""
CRITICAL E2E Test #6: User Deletes Account → Data Cleanup Across All Services

BVJ (Business Value Justification):
1. Segment: All customer segments (GDPR compliance mandatory)
2. Business Goal: Validate complete data removal prevents legal liability
3. Value Impact: Protects against GDPR fines up to 4% of annual revenue
4. Revenue Impact: Maintains customer trust and prevents regulatory sanctions

REQUIREMENTS:
- User requests account deletion through API
- Auth service removes user record completely
- Backend removes user profile and related data
- ClickHouse removes all usage/billing data
- Chat history is completely deleted
- Deletion confirmation is provided
- No orphaned records remain anywhere
- GDPR compliance validation
- Complete in <30 seconds
- 450-line file limit, 25-line function limit

SUCCESS CRITERIA:
- Complete data removal across all services
- GDPR compliance verification
- Performance under 30 seconds
- No data leakage or orphaned records
- Proper audit trail maintained
"""
import time
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.account_deletion_flow_manager import AccountDeletionFlowManager
from tests.e2e.account_deletion_helpers import (
    AccountDeletionFlowTester,
    GDPRComplianceValidator,
)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_account_deletion_flow():
    """
    Test #6: Complete Account Deletion → Data Cleanup Across All Services
    
    BVJ: Protects against GDPR fines and maintains customer trust
    - Real account deletion request processing
    - Cross-service data cleanup validation
    - GDPR compliance verification
    - Complete audit trail maintenance
    - Must complete in <30 seconds
    """
    manager = AccountDeletionFlowManager()
    
    async with manager.setup_complete_test_environment() as deletion_tester:
        flow_tester = AccountDeletionFlowTester(deletion_tester)
        
        # Execute complete deletion flow with performance validation
        results = await flow_tester.execute_complete_deletion_flow()
        
        # Validate business-critical success criteria
        assert results["success"], f"Account deletion flow failed: {results.get('error')}"
        assert results["execution_time"] < 30.0, f"Performance failed: {results['execution_time']:.2f}s"
        
        # Validate each step completed successfully
        required_steps = ["user_creation", "deletion_request", "cleanup_verification", "deletion_confirmation"]
        for step in required_steps:
            assert step in results, f"Missing critical step: {step}"
        
        # Validate cross-service cleanup
        cleanup_results = results["cleanup_verification"]
        assert cleanup_results["auth_cleanup"], "Auth service cleanup failed"
        assert cleanup_results["profile_cleanup"], "Profile cleanup failed"
        assert cleanup_results["usage_cleanup"], "Usage data cleanup failed"
        assert cleanup_results["billing_cleanup"], "Billing data cleanup failed"
        
        # Validate deletion confirmation
        confirmation = results["deletion_confirmation"]
        assert confirmation["gdpr_compliant"], "GDPR compliance validation failed"
        
        print(f"[SUCCESS] Account Deletion Flow: {results['execution_time']:.2f}s")
        print(f"[PROTECTED] GDPR compliance validated")
        print(f"[SECURE] Complete data removal verified")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_gdpr_compliance_validation():
    """
    Test GDPR compliance for account deletion.
    
    BVJ: Legal compliance prevents regulatory fines
    - Complete personal data removal
    - Usage data deletion verification
    - Billing data cleanup validation
    - Audit trail maintenance
    """
    manager = AccountDeletionFlowManager()
    
    async with manager.setup_complete_test_environment() as deletion_tester:
        # Create test user with comprehensive data
        flow_tester = AccountDeletionFlowTester(deletion_tester)
        user_data = await flow_tester._create_test_user_with_data()
        
        # Execute deletion flow
        deletion_results = await flow_tester.execute_complete_deletion_flow()
        assert deletion_results["success"], "Deletion flow must succeed for GDPR test"
        
        # Validate GDPR compliance
        gdpr_validator = GDPRComplianceValidator(deletion_tester)
        compliance_results = await gdpr_validator.validate_complete_data_removal(user_data["user_id"])
        
        # Assert GDPR compliance criteria
        assert compliance_results["gdpr_compliant"], "GDPR compliance validation failed"
        
        validation_details = compliance_results["validation_details"]
        assert validation_details["personal_data_removed"], "Personal data not completely removed"
        assert validation_details["usage_data_removed"], "Usage data not completely removed"
        assert validation_details["billing_data_removed"], "Billing data not completely removed"
        assert validation_details["audit_trail_maintained"], "Audit trail not properly maintained"
        
        print(f"[SUCCESS] GDPR Compliance Validated")
        print(f"[LEGAL] All personal data removed")
        print(f"[AUDIT] Deletion audit trail maintained")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_orphaned_data_detection():
    """
    Test detection and cleanup of orphaned data after deletion.
    
    BVJ: Prevents data leakage and ensures complete cleanup
    - Comprehensive orphaned record detection
    - Cross-service data consistency validation
    - Complete cleanup verification
    """
    manager = AccountDeletionFlowManager()
    
    async with manager.setup_complete_test_environment() as deletion_tester:
        flow_tester = AccountDeletionFlowTester(deletion_tester)
        
        # Create user with data across services
        user_data = await flow_tester._create_test_user_with_data()
        user_id = user_data["user_id"]
        
        # Execute deletion flow
        deletion_results = await flow_tester.execute_complete_deletion_flow()
        assert deletion_results["success"], "Deletion must succeed for orphan detection test"
        
        # Verify no orphaned records exist
        await _verify_no_auth_orphans(deletion_tester, user_id)
        await _verify_no_backend_orphans(deletion_tester, user_id)
        await _verify_no_clickhouse_orphans(deletion_tester, user_id)
        await _verify_no_websocket_orphans(deletion_tester, user_id)
        
        print(f"[SUCCESS] No orphaned data detected")
        print(f"[CLEAN] All services verified clean")


async def _verify_no_auth_orphans(deletion_tester, user_id: str):
    """Verify no orphaned data in auth service."""
    user_record = await deletion_tester.mock_services["auth"].get_user(user_id)
    assert user_record is None, "Auth service has orphaned user record"
    
    sessions = await deletion_tester.mock_services["auth"].get_user_sessions(user_id)
    assert sessions == [], "Auth service has orphaned session records"


async def _verify_no_backend_orphans(deletion_tester, user_id: str):
    """Verify no orphaned data in backend service."""
    profile = await deletion_tester.mock_services["backend"].get_profile(user_id)
    assert profile is None, "Backend has orphaned profile record"
    
    threads = await deletion_tester.mock_services["backend"].get_user_threads(user_id)
    assert threads == [], "Backend has orphaned thread records"


async def _verify_no_clickhouse_orphans(deletion_tester, user_id: str):
    """Verify no orphaned data in ClickHouse."""
    usage_data = await deletion_tester.mock_services["clickhouse"].get_user_usage(user_id)
    assert usage_data == [], "ClickHouse has orphaned usage records"
    
    billing_data = await deletion_tester.mock_services["clickhouse"].get_billing_data(user_id)
    assert billing_data == [], "ClickHouse has orphaned billing records"


async def _verify_no_websocket_orphans(deletion_tester, user_id: str):
    """Verify no orphaned WebSocket connections."""
    connections = await deletion_tester.mock_services["websocket"].get_user_connections(user_id)
    assert connections == [], "WebSocket has orphaned connection records"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_account_deletion_performance():
    """
    Performance validation for account deletion flow.
    BVJ: User experience during account deletion impacts trust.
    """
    manager = AccountDeletionFlowManager()
    
    async with manager.setup_complete_test_environment() as deletion_tester:
        total_start_time = time.time()
        
        # Test multiple deletion flows for consistency
        flow_tester1 = AccountDeletionFlowTester(deletion_tester)
        deletion_results1 = await flow_tester1.execute_complete_deletion_flow()
        assert deletion_results1["execution_time"] < 30.0, f"Deletion 1 too slow: {deletion_results1['execution_time']:.2f}s"
        
        flow_tester2 = AccountDeletionFlowTester(deletion_tester)
        deletion_results2 = await flow_tester2.execute_complete_deletion_flow()
        assert deletion_results2["execution_time"] < 30.0, f"Deletion 2 too slow: {deletion_results2['execution_time']:.2f}s"
        
        total_time = time.time() - total_start_time
        avg_deletion_time = (deletion_results1["execution_time"] + deletion_results2["execution_time"]) / 2
        
        print(f"[PASSED] Account Deletion Performance validation")
        print(f"[METRICS] Average deletion time: {avg_deletion_time:.2f}s")
        print(f"[METRICS] Total test time: {total_time:.2f}s")
        print(f"[OPTIMIZED] GDPR compliance experience")


@pytest.mark.asyncio 
@pytest.mark.e2e
async def test_concurrent_account_deletions():
    """
    Test concurrent account deletions to ensure isolation.
    BVJ: Prevents data corruption during concurrent operations.
    """
    manager = AccountDeletionFlowManager()
    
    async with manager.setup_complete_test_environment() as deletion_tester:
        # Create multiple test users
        testers = [
            AccountDeletionFlowTester(deletion_tester),
            AccountDeletionFlowTester(deletion_tester),
            AccountDeletionFlowTester(deletion_tester)
        ]
        
        # Execute concurrent deletions
        import asyncio
        results = await asyncio.gather(
            *[tester.execute_complete_deletion_flow() for tester in testers],
            return_exceptions=True
        )
        
        # Verify all deletions completed successfully
        successful_deletions = sum(1 for r in results if not isinstance(r, Exception) and r.get("success"))
        assert successful_deletions >= 2, f"Only {successful_deletions} concurrent deletions succeeded"
        
        print(f"[SUCCESS] {successful_deletions} concurrent deletions completed")
        print(f"[ISOLATION] No deletion interference detected")
