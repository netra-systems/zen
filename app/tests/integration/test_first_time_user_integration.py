"""
Integration test wrapper for the unified first-time user test.
Allows the comprehensive first-time user test to be run as part of the standard test suite.

BVJ (Business Value Justification):
1. Segment: Free → Early (Primary conversion funnel)
2. Business Goal: Ensure first-time user success in CI/CD pipeline
3. Value Impact: Prevents deployment of broken user onboarding
4. Revenue Impact: Catches issues before they affect real users
"""

import asyncio
import pytest
import sys
from pathlib import Path

# Add project root to path for test imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from test_unified_first_time_user import FirstTimeUserTester

@pytest.mark.integration
@pytest.mark.first_time_user
@pytest.mark.timeout(45)  # 45-second timeout for full flow
async def test_complete_first_time_user_flow():
    """
    Test complete first-time user flow from registration to chat.
    
    This is the most critical business test - validates the entire
    user journey that generates revenue.
    """
    tester = FirstTimeUserTester()
    results = await tester.run_complete_test()
    
    # Assert success criteria
    assert results['success'], f"First-time user flow failed: {results['errors']}"
    assert results['user_verified_in_dbs'], "User not verified in databases"
    assert results['chat_response_received'], "No chat response received"
    assert results['duration'] <= 30, f"Test took too long: {results['duration']:.2f}s"
    
    # Verify all expected steps completed
    expected_steps = ['services_started', 'user_registered', 'database_verified', 'chat_completed']
    for step in expected_steps:
        assert step in results['steps_completed'], f"Step not completed: {step}"

@pytest.mark.smoke
@pytest.mark.first_time_user_validation
def test_first_time_user_components():
    """
    Smoke test for first-time user test components.
    Validates test structure without running full flow.
    """
    # Test that components can be initialized
    tester = FirstTimeUserTester()
    
    # Verify test data structure
    assert 'email' in tester.test_user_data
    assert 'password' in tester.test_user_data
    assert '@netratest.com' in tester.test_user_data['email']
    
    # Verify response validation logic
    valid_response = {
        'type': 'agent_response',
        'message': 'I can help you with various tasks and questions.'
    }
    assert tester._is_meaningful_response(valid_response)
    
    invalid_response = {
        'type': 'system_message',
        'message': 'System message'
    }
    assert not tester._is_meaningful_response(invalid_response)

def test_first_time_user_sync():
    """Synchronous wrapper for the async first-time user test."""
    return asyncio.run(test_complete_first_time_user_flow())

if __name__ == "__main__":
    # Allow running this test directly
    import pytest
    pytest.main([__file__, "-v"])