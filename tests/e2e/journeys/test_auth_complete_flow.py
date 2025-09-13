"""
CRITICAL E2E Authentication Flow Tests - Main Test Suite

BVJ (Business Value Justification):
1. Segment: All customer segments (Free  ->  Paid conversion critical)
2. Business Goal: Protect $200K+ MRR through authentication funnel validation
3. Value Impact: Prevents authentication failures that cost user conversions
4. Revenue Impact: Each test failure caught saves $10K+ MRR monthly

REQUIREMENTS:
- Real authentication logic and JWT operations
- Controlled service dependencies for reliability
- Must complete in <5 seconds
- 450-line file limit, 25-line function limit
- Multi-device session security validation
"""
import time
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.auth_flow_manager import AuthCompleteFlowManager
from tests.e2e.integration.new_user_flow_tester import CompleteNewUserFlowTester
from tests.e2e.integration.session_security_tester import SessionSecurityLogoutTester


# Pytest Test Implementations
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_new_user_registration_to_first_chat():
    """
    Test #1: Complete New User Registration  ->  First Chat
    
    BVJ: Protects $50K+ MRR new user funnel conversion
    - Real JWT token creation and validation
    - Real authentication logic flow
    - Real WebSocket connection simulation
    - Real chat message and AI response simulation
    - Must complete in <5 seconds
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        flow_tester = CompleteNewUserFlowTester(auth_tester)
        
        # Execute complete flow with performance validation
        results = await flow_tester.execute_complete_flow()
        
        # Validate business-critical success criteria
        assert results["success"], f"New user flow failed: {results.get('error')}"
        assert results["execution_time"] < 5.0, f"Performance failed: {results['execution_time']:.2f}s"
        
        # Validate each step completed successfully
        required_steps = ["signup", "profile_creation", "websocket_connection", "first_chat"]
        for step in required_steps:
            assert step in results, f"Missing critical step: {step}"
        
        # Business value validation - JWT token quality
        signup_result = results["signup"]
        assert "access_token" in signup_result, "Missing access token"
        assert signup_result["token_type"] == "Bearer", "Invalid token type"
        
        # Business value validation - chat response quality
        chat_result = results["first_chat"]
        assert len(chat_result.get("content", "")) > 50, "AI response quality insufficient"
        assert "cost" in chat_result["content"].lower(), "Response not addressing cost optimization"
        
        print(f"[SUCCESS] New User Flow: {results['execution_time']:.2f}s")
        print(f"[PROTECTED] $50K+ MRR funnel")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_session_security_and_logout_propagation():
    """
    Test #10: Session Security and Logout
    
    BVJ: Prevents security breaches that cost user trust and compliance
    - Multi-device login with real JWT tokens
    - Logout propagation with real token invalidation
    - Token security validation
    - Must complete in <5 seconds
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        security_tester = SessionSecurityLogoutTester(auth_tester)
        
        # Execute security validation flow
        results = await security_tester.execute_security_flow()
        
        # Validate security-critical success criteria
        assert results["success"], f"Security flow failed: {results.get('error')}"
        assert results["execution_time"] < 5.0, f"Security performance failed: {results['execution_time']:.2f}s"
        
        # Validate multi-device functionality with real JWTs
        assert results["multi_device_login"]["session_count"] >= 3, "Multi-device login failed"
        assert results["sessions_validated"] >= 3, "Session validation failed"
        
        # Validate logout security with real token invalidation
        assert results["logout_executed"], "Logout execution failed"
        assert results["logout_propagation"] == "verified", "Logout propagation failed"
        assert results["token_invalidation_verified"], "Token invalidation failed"
        
        # Additional security validation - ensure no session leakage
        assert len(security_tester.session_store) > 0, "Session store should contain sessions"
        active_sessions = [s for s in security_tester.session_store.values() if s.get("active")]
        assert len(active_sessions) == 2, "Should have exactly 2 active sessions after logout"
        
        print(f"[SUCCESS] Session Security: {results['execution_time']:.2f}s")
        print(f"[SECURE] Multi-device logout")
        print(f"[PROTECTED] User trust and compliance")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_auth_e2e_performance_validation():
    """
    Performance validation for critical authentication flows.
    BVJ: User experience directly impacts conversion rates.
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        total_start_time = time.time()
        
        # Test new user flow performance (with fresh instances)
        flow_tester1 = CompleteNewUserFlowTester(auth_tester)
        flow_results1 = await flow_tester1.execute_complete_flow()
        assert flow_results1["execution_time"] < 5.0, f"Flow 1 performance failed: {flow_results1['execution_time']:.2f}s"
        
        # Test security flow performance (with fresh instances)
        security_tester1 = SessionSecurityLogoutTester(auth_tester)
        security_results1 = await security_tester1.execute_security_flow()
        assert security_results1["execution_time"] < 5.0, f"Security 1 performance failed: {security_results1['execution_time']:.2f}s"
        
        # Test second iteration for consistency
        flow_tester2 = CompleteNewUserFlowTester(auth_tester)
        flow_results2 = await flow_tester2.execute_complete_flow()
        assert flow_results2["execution_time"] < 5.0, f"Flow 2 performance failed: {flow_results2['execution_time']:.2f}s"
        
        total_time = time.time() - total_start_time
        avg_flow_time = (flow_results1["execution_time"] + flow_results2["execution_time"]) / 2
        
        print(f"[PASSED] E2E Performance validation")
        print(f"[METRICS] Average flow time: {avg_flow_time:.2f}s")
        print(f"[METRICS] Total test time: {total_time:.2f}s")
        print(f"[OPTIMIZED] User conversion experience")
