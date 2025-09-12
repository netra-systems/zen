"""
CRITICAL E2E Test #7: Free Tier Limit Enforcement  ->  Upgrade Prompt
Business Value: $300K+ MRR - Free-to-paid conversion through strategic limit enforcement

BVJ (Business Value Justification):
1. Segment: Free  ->  Paid conversion (100% of new revenue generation)
2. Business Goal: Optimize conversion timing at moment users see value
3. Value Impact: Well-timed limits convert 25-35% free users to paid
4. Revenue Impact: Each conversion = $348-3588/year in recurring revenue

REQUIREMENTS:
- Free user hits daily/request limits (10 requests/day)
- Further requests blocked with contextual upgrade prompt
- Upgrade prompt shows pricing and value proposition
- User completes upgrade to paid tier
- Limits removed immediately post-upgrade
- Service resumes normal operation
- Performance validation (<30 seconds total)
- 450-line file limit, 25-line function limit

This test protects the entire free-to-paid conversion funnel.
Without effective limit enforcement, free users never convert.
"""
import pytest
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.auth_flow_manager import AuthCompleteFlowManager
from tests.e2e.free_tier_limit_managers import LimitEnforcementManager
from tests.e2e.free_tier_limit_tester import FreeTierLimitTester


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_free_tier_limit_enforcement_upgrade_flow():
    """
    CRITICAL E2E Test #7: Free Tier Limit Enforcement  ->  Upgrade Prompt
    
    Validates complete free-to-paid conversion flow:
    1. Free user operates normally within daily limits
    2. Warning shown when approaching limit (80% usage)
    3. Hard enforcement when limit exceeded
    4. Contextual upgrade prompt at optimal conversion moment
    5. Successful tier upgrade transaction
    6. Immediate service restoration with unlimited usage
    
    Must complete in <30 seconds for CI/CD pipeline compatibility.
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        limit_tester = FreeTierLimitTester(auth_tester)
        
        # Execute complete limit enforcement and upgrade flow
        results = await limit_tester.execute_complete_limit_enforcement_flow()
        
        # Validate all steps completed successfully
        assert results["success"], f"Limit enforcement flow failed: {results}"
        assert len(results["steps"]) == 7, f"Expected 7 steps, got {len(results['steps'])}"
        
        # Verify business critical validations
        step_results = {step["step"]: step for step in results["steps"]}
        
        # Free user creation with proper limits
        user_step = step_results["free_user_created"]["data"]
        assert user_step["free_tier_confirmed"], "Free tier not properly configured"
        
        # Normal usage pattern validated
        usage_step = step_results["normal_usage"]["data"]
        assert usage_step["successful_requests"] == 7, "Normal usage pattern failed"
        
        # Warning triggered at appropriate threshold
        warning_step = step_results["limit_warning"]["data"]
        assert warning_step["warning_triggered"], "Limit warning not triggered"
        
        # Enforcement activated correctly
        enforcement_step = step_results["limit_enforcement"]["data"]
        assert enforcement_step["enforcement_active"], "Limit enforcement failed"
        
        # Upgrade prompt quality validation
        prompt_step = step_results["upgrade_prompt"]["data"]
        assert prompt_step["timing_optimal"]["timing_optimized"], "Upgrade prompt timing not optimal"
        
        # Successful tier upgrade
        upgrade_step = step_results["tier_upgraded"]["data"]
        assert upgrade_step["upgrade_successful"], "Tier upgrade failed"
        assert upgrade_step["new_tier"] == "pro", "Tier not upgraded to Pro"
        
        # Service restored with unlimited usage
        restored_step = step_results["service_restored"]["data"]
        assert restored_step["unlimited_confirmed"], "Unlimited usage not confirmed"
        assert restored_step["service_restored"], "Service not properly restored"
        
        # Performance validation
        assert results["execution_time"] < 30.0, f"E2E test exceeded 30s limit: {results['execution_time']}"
        
        print(f"[SUCCESS] Free Tier Limit Enforcement Flow: {results['execution_time']:.2f}s")
        print(f"[PROTECTED] Free-to-paid conversion pipeline")
        print(f"[REVENUE] $348-3588/year per successful conversion")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_limit_enforcement_different_usage_patterns():
    """Test limit enforcement with different usage patterns."""
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        # Test burst usage pattern
        burst_tester = FreeTierLimitTester(auth_tester)
        limit_manager = LimitEnforcementManager(burst_tester)
        
        # Create user and validate limits
        await burst_tester._create_free_user_with_limits()
        
        # Test rapid burst of requests
        for i in range(10):
            await burst_tester._send_single_request(f"Burst request {i+1}")
            await limit_manager.track_usage_against_limits("burst_request")
        
        # Next request should be blocked
        try:
            await burst_tester._send_single_request("Over limit burst")
            assert False, "Burst request should have been blocked"
        except Exception as e:
            assert "limit exceeded" in str(e).lower(), "Burst limit not enforced"
        
        print("[SUCCESS] Burst usage pattern limit enforcement validated")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_limit_enforcement_edge_cases():
    """Test limit enforcement edge cases and boundary conditions."""
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        edge_tester = FreeTierLimitTester(auth_tester)
        
        # Create user
        await edge_tester._create_free_user_with_limits()
        
        # Test exactly at limit boundary (10 requests)
        for i in range(10):
            result = await edge_tester._send_single_request(f"Boundary request {i+1}")
            assert result["success"], f"Request {i+1} should succeed"
        
        # 11th request should fail
        try:
            await edge_tester._send_single_request("Should fail")
            assert False, "11th request should have been blocked"
        except Exception as e:
            assert "Daily limit exceeded" in str(e), "Expected limit exceeded error"
        
        print("[SUCCESS] Boundary condition limit enforcement validated")


if __name__ == "__main__":
    # Allow direct execution for debugging
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
