import sys
import os
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Set staging environment
os.environ['ENVIRONMENT'] = 'staging'

def run_single_test():
    """Run a single staging test to verify setup"""
    try:
        import asyncio
        from tests.staging.test_staging_agent_execution import StagingAgentExecutionTestRunner

        async def main():
            runner = StagingAgentExecutionTestRunner()
            results = await runner.run_all_tests()

            print("\n" + "="*60)
            print("STAGING AGENT EXECUTION TEST RESULTS")
            print("="*60)

            summary = results.get('summary', {})
            print(f"Core agent functionality working: {summary.get('core_agent_functionality_working', False)}")
            print(f"Agent status working: {summary.get('agent_status_working', False)}")
            print(f"HTTP execution working: {summary.get('http_execution_working', False)}")
            print(f"WebSocket execution working: {summary.get('websocket_execution_working', False)}")
            print(f"WebSocket events complete: {summary.get('websocket_events_complete', False)}")

            # Print detailed results for debugging
            for key, value in results.items():
                if key != 'summary' and isinstance(value, dict):
                    success = value.get('success', False)
                    error = value.get('error', '')
                    print(f"{key}: {'PASS' if success else 'FAIL'}")
                    if error and not success:
                        print(f"  Error: {error}")

            return results

        return asyncio.run(main())

    except Exception as e:
        print(f"Error running test: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = run_single_test()