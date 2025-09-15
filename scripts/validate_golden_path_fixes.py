#!/usr/bin/env python3
"""
Golden Path Integration Test Validation Script
Validates that the remediation fixes work correctly
"""

import os
import subprocess
import sys
import asyncio
from pathlib import Path


async def run_command(command, description, check=True):
    """Run a command and return success/failure."""
    print(f"🔍 {description}...")
    try:
        if isinstance(command, str):
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=check)
        else:
            result = subprocess.run(command, capture_output=True, text=True, check=check)
        
        if result.returncode == 0:
            print(f"  ✅ SUCCESS")
            if result.stdout.strip():
                print(f"     Output: {result.stdout.strip()[:200]}...")
            return True
        else:
            print(f"  ❌ FAILED (exit code: {result.returncode})")
            if result.stderr.strip():
                print(f"     Error: {result.stderr.strip()[:200]}...")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"  ❌ FAILED: {e}")
        return False
    except Exception as e:
        print(f"  ❌ EXCEPTION: {e}")
        return False


def setup_environment():
    """Setup the environment for testing."""
    print("🔧 Setting up test environment...")
    
    # Set Python path
    project_root = "/Users/anthony/Desktop/netra-apex"
    os.environ["PYTHONPATH"] = project_root
    
    # Load test environment file
    env_file = Path(project_root) / ".env.test.local"
    if env_file.exists():
        print(f"✅ Loading environment from {env_file}")
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        
        # Ensure USE_REAL_SERVICES is set
        os.environ["USE_REAL_SERVICES"] = "true"
        print("✅ USE_REAL_SERVICES=true set")
    else:
        print(f"❌ Environment file not found: {env_file}")
        return False
    
    return True


async def validate_services():
    """Validate that required services are running."""
    print("\n🏥 Validating service health...")
    
    # Check PostgreSQL
    postgres_ok = await run_command(
        'psql -h localhost -p 5432 -U netra_user -d netra_test -c "SELECT version();"',
        "Testing PostgreSQL connection",
        check=False
    )
    
    # Check Redis
    redis_ok = await run_command(
        'redis-cli -h localhost -p 6379 ping',
        "Testing Redis connection", 
        check=False
    )
    
    return postgres_ok and redis_ok


async def test_individual_components():
    """Test individual components that were fixed."""
    print("\n🧪 Testing individual fixed components...")
    
    results = []
    
    # Test 1: SupervisorAgent with user_context
    test1_ok = await run_command([
        "python3", "-c", """
import asyncio
from unittest.mock import AsyncMock, MagicMock
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext

async def test():
    mock_llm = MagicMock()
    user_context = UserExecutionContext(
        user_id='test-user',
        thread_id='test-thread', 
        run_id='test-run',
        request_id='test-request',
        websocket_client_id='test-ws'
    )
    supervisor = SupervisorAgent(llm_manager=mock_llm, user_context=user_context)
    print('SupervisorAgent created successfully with user_context')

asyncio.run(test())
        """
    ], "SupervisorAgent instantiation with user_context", check=False)
    results.append(("SupervisorAgent Fix", test1_ok))
    
    # Test 2: Local services fixture
    test2_ok = await run_command([
        "python3", "-c", """
import asyncio
from test_framework.fixtures.local_real_services import local_real_services_fixture
print('Local services fixture imported successfully')
        """
    ], "Local services fixture import", check=False)
    results.append(("Local Services Fixture", test2_ok))
    
    return results


async def run_specific_failing_tests():
    """Run the specific failing tests that were identified."""
    print("\n🎯 Running specific failing tests...")
    
    failing_tests = [
        "tests/integration/golden_path/test_agent_orchestration_execution_comprehensive.py::TestAgentOrchestrationExecution::test_supervisor_agent_orchestration_basic_flow",
        "tests/integration/golden_path/test_agent_orchestration_execution_comprehensive.py::TestAgentOrchestrationExecution::test_sub_agent_execution_pipeline_sequencing", 
        "tests/integration/golden_path/test_agent_orchestration_execution_comprehensive.py::TestAgentOrchestrationExecution::test_agent_tool_execution_integration",
        "tests/integration/golden_path/test_agent_orchestration_execution_comprehensive.py::TestAgentOrchestrationExecution::test_websocket_event_integration_comprehensive"
    ]
    
    results = []
    
    for test in failing_tests:
        test_name = test.split("::")[-1]
        test_ok = await run_command([
            "python3", "-m", "pytest", test, "-v", "-s", "--tb=short"
        ], f"Running {test_name}", check=False)
        results.append((test_name, test_ok))
        
        if test_ok:
            print(f"    🎉 {test_name} now PASSING!")
        else:
            print(f"    ⚠️ {test_name} still failing - may need additional fixes")
    
    return results


async def run_skipped_tests():
    """Check if previously skipped tests now run."""
    print("\n📋 Checking previously skipped tests...")
    
    # Run one of the tests that was skipped due to "Database not available"
    skipped_test = "tests/integration/golden_path/test_agent_execution_pipeline_comprehensive.py::TestAgentExecutionPipelineComprehensive::test_execution_engine_factory_user_isolation"
    
    test_ok = await run_command([
        "python3", "-m", "pytest", skipped_test, "-v", "-s", "--tb=short"
    ], "Running previously skipped test", check=False)
    
    return [("Previously Skipped Test", test_ok)]


async def main():
    """Main validation function."""
    print("🚀 Golden Path Integration Test Validation")
    print("=" * 50)
    
    # Setup environment
    if not setup_environment():
        print("❌ Environment setup failed")
        sys.exit(1)
    
    # Validate services
    services_ok = await validate_services()
    if not services_ok:
        print("\n❌ Service validation failed!")
        print("Please run: python3 scripts/setup_local_test_services.py")
        sys.exit(1)
    
    # Test individual components
    component_results = await test_individual_components()
    
    # Run failing tests
    test_results = await run_specific_failing_tests()
    
    # Check skipped tests
    skipped_results = await run_skipped_tests()
    
    # Summary
    print("\n📊 VALIDATION SUMMARY")
    print("=" * 30)
    
    all_results = component_results + test_results + skipped_results
    
    passed = sum(1 for _, result in all_results if result)
    total = len(all_results)
    
    print(f"Overall Success Rate: {passed}/{total} ({passed/total*100:.1f}%)")
    print()
    
    for test_name, result in all_results:
        status = "✅ PASS" if result else "❌ FAIL" 
        print(f"  {status} {test_name}")
    
    if passed == total:
        print("\n🎉 ALL VALIDATIONS PASSED! Golden Path tests should now work.")
        print("\nTo run all Golden Path tests:")
        print("export USE_REAL_SERVICES=true")
        print("python3 -m pytest tests/integration/golden_path/ -v")
    else:
        print(f"\n⚠️ {total - passed} validations still failing.")
        print("Additional debugging may be needed.")
        
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)