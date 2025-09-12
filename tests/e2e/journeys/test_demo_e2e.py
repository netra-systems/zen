"""
Demo E2E Test - Validates Unified Harness Functionality
Business Value: Demonstrates E2E testing capabilities for stakeholders
Shows service orchestration, user journeys, and WebSocket flows.
"""
import asyncio
import logging
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.integration.unified_e2e_harness import create_e2e_harness

logger = logging.getLogger(__name__)


async def demo_basic_e2e_flow():
    """Demonstrate basic E2E flow with service orchestration."""
    print("[U+1F680] Starting Unified E2E Demo")
    
    async with create_e2e_harness().test_environment() as harness:
        print(" PASS:  Test environment started")
        
        # Check environment status
        status = await harness.get_environment_status()
        print(f" CHART:  Environment ready: {harness.is_environment_ready()}")
        print(f" CHART:  Session ID: {status['session_id']}")
        
        # Create test user
        user = await harness.create_test_user(
            email="demo@example.com"
        )
        print(f"[U+1F464] Created test user: {user.email}")
        
        # Simulate user journey
        journey_result = await harness.simulate_user_journey(user)
        print(f" TARGET:  User journey completed: {len(journey_result['steps_completed'])} steps")
        
        if journey_result['errors']:
            print(f" WARNING: [U+FE0F]  Journey errors: {journey_result['errors']}")
        else:
            print(" PASS:  Journey completed successfully")
        
        # Test concurrent users
        concurrent_results = await harness.run_concurrent_user_test(user_count=2)
        successful_journeys = sum(
            1 for result in concurrent_results 
            if isinstance(result, dict) and not result.get('errors')
        )
        print(f"[U+1F465] Concurrent test: {successful_journeys}/2 users successful")
    
    print("[U+1F9F9] Test environment cleaned up")
    print(" PASS:  Demo completed successfully")


async def demo_service_health_monitoring():
    """Demonstrate service health monitoring capabilities."""
    print("[U+1F3E5] Service Health Monitoring Demo")
    
    harness = create_e2e_harness()
    
    try:
        await harness.start_test_environment()
        
        # Monitor service health
        status = await harness.get_environment_status()
        print(f" CHART:  Services status: {list(status['services'].keys())}")
        
        for service_name, service_status in status['services'].items():
            health = " PASS:  Healthy" if service_status.get('ready') else " FAIL:  Unhealthy"
            print(f"  {service_name}: {health} (Port: {service_status.get('port')})")
        
        print(f"[U+1F517] Available service URLs:")
        auth_url = harness.get_service_url("auth")
        backend_url = harness.get_service_url("backend") 
        websocket_url = harness.get_websocket_url()
        
        print(f"  Auth Service: {auth_url}")
        print(f"  Backend Service: {backend_url}")
        print(f"  WebSocket: {websocket_url}")
        
    finally:
        await harness.cleanup_test_environment()


if __name__ == "__main__":
    # Configure logging for demo
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("[U+1F3AD] Unified E2E Test Harness Demo")
    print("=" * 50)
    
    try:
        # Run basic flow demo
        asyncio.run(demo_basic_e2e_flow())
        print("\n")
        
        # Run health monitoring demo  
        asyncio.run(demo_service_health_monitoring())
        
    except KeyboardInterrupt:
        print("\n[U+1F6D1] Demo interrupted by user")
    except Exception as e:
        print(f"\n FAIL:  Demo failed: {e}")
        logger.exception("Demo execution failed")
    
    print("\n[U+1F3C1] Demo session ended")
