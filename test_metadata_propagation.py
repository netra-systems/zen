"""Test to verify metadata propagation fix for agent workflow.

This test verifies that the supervisor correctly propagates metadata
from child contexts back to parent context for the reporting agent.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent))

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


async def test_metadata_propagation():
    """Test that metadata is correctly propagated from child to parent contexts."""
    
    # Create parent context
    parent_context = UserExecutionContext(
        user_id="test_user",
        thread_id="test_thread",
        run_id="test_run",
        metadata={
            "user_request": "Test request for metadata propagation"
        }
    )
    
    # Create supervisor agent
    supervisor = SupervisorAgent(llm_manager=None, websocket_bridge=None)
    
    # Test the metadata merge method with mock child contexts
    logger.info("Testing metadata propagation from child contexts...")
    
    # Simulate triage agent child context
    triage_child = UserExecutionContext(
        user_id="test_user",
        thread_id="test_thread", 
        run_id="test_run_triage",
        metadata={
            "triage_result": {
                "category": "Test",
                "confidence_score": 0.9
            }
        }
    )
    supervisor._merge_child_metadata_to_parent(parent_context, triage_child, "triage")
    
    # Simulate data agent child context
    data_child = UserExecutionContext(
        user_id="test_user",
        thread_id="test_thread",
        run_id="test_run_data",
        metadata={
            "data_result": {
                "analysis_type": "performance",
                "data_points": 100
            }
        }
    )
    supervisor._merge_child_metadata_to_parent(parent_context, data_child, "data")
    
    # Simulate optimization agent child context
    optimization_child = UserExecutionContext(
        user_id="test_user",
        thread_id="test_thread",
        run_id="test_run_optimization",
        metadata={
            "optimizations_result": {
                "strategies": ["cache", "parallel"],
                "potential_savings": 0.3
            }
        }
    )
    supervisor._merge_child_metadata_to_parent(parent_context, optimization_child, "optimization")
    
    # Simulate actions agent child context
    actions_child = UserExecutionContext(
        user_id="test_user",
        thread_id="test_thread",
        run_id="test_run_actions",
        metadata={
            "action_plan_result": {
                "plan_steps": ["step1", "step2", "step3"],
                "priority": "high"
            }
        }
    )
    supervisor._merge_child_metadata_to_parent(parent_context, actions_child, "actions")
    
    # Verify all metadata is now in parent context
    logger.info("Verifying metadata in parent context...")
    
    required_keys = ["triage_result", "data_result", "optimizations_result", "action_plan_result"]
    missing_keys = []
    
    for key in required_keys:
        if key in parent_context.metadata:
            logger.info(f"✅ Found {key} in parent metadata: {parent_context.metadata[key]}")
        else:
            logger.error(f"❌ Missing {key} in parent metadata")
            missing_keys.append(key)
    
    # Test reporting agent with the propagated metadata
    logger.info("\nTesting ReportingSubAgent with propagated metadata...")
    
    reporting_agent = ReportingSubAgent()
    
    # Try validation - should pass now with all metadata present
    try:
        reporting_agent._validate_analysis_results(parent_context)
        logger.info("✅ ReportingSubAgent validation passed with propagated metadata!")
    except Exception as e:
        logger.error(f"❌ ReportingSubAgent validation failed: {e}")
        return False
    
    if missing_keys:
        logger.error(f"\n❌ Test failed. Missing metadata keys: {missing_keys}")
        return False
    else:
        logger.info("\n✅ All tests passed! Metadata propagation is working correctly.")
        return True


if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_metadata_propagation())
    
    if success:
        print("\n✅ METADATA PROPAGATION TEST PASSED")
        print("The fix successfully propagates metadata from child contexts to parent context.")
        print("The reporting agent will now have access to all required analysis results.")
    else:
        print("\n❌ METADATA PROPAGATION TEST FAILED")
        print("Please review the implementation.")
    
    sys.exit(0 if success else 1)