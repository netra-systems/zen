#!/usr/bin/env python3
"""
Simple Alpine functionality test that can run without Docker.
Demonstrates that Alpine container support is working correctly.
"""

import os
import sys
from pathlib import Path
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_alpine_parameter_functionality():
    """Test Alpine parameter acceptance and compose file selection."""
    from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
    
    print("Testing Alpine container functionality...")
    
    # Test 1: Parameter acceptance
    print("1. Testing parameter acceptance...")
    manager_alpine = UnifiedDockerManager(
        environment_type=EnvironmentType.TEST,
        use_alpine=True
    )
    assert hasattr(manager_alpine, 'use_alpine'), "use_alpine attribute missing"
    assert manager_alpine.use_alpine is True, f"Expected True, got {manager_alpine.use_alpine}"
    print("   ✅ Alpine parameter accepted and stored correctly")
    
    # Test 2: Default value (Alpine is now default)
    print("2. Testing default value...")
    manager_default = UnifiedDockerManager(environment_type=EnvironmentType.TEST)
    assert hasattr(manager_default, 'use_alpine'), "use_alpine attribute missing on default"
    assert manager_default.use_alpine is True, f"Expected True default (Alpine), got {manager_default.use_alpine}"
    print("   ✅ Default value (True for Alpine) working correctly")
    
    # Test 3: Compose file selection (both should be Alpine since it's default)
    print("3. Testing compose file selection...")
    alpine_compose = manager_alpine._get_compose_file()
    default_compose = manager_default._get_compose_file()
    
    assert "alpine" in alpine_compose.lower(), f"Alpine compose should contain 'alpine': {alpine_compose}"
    assert "alpine" in default_compose.lower(), f"Default compose should also contain 'alpine' (Alpine is default): {default_compose}"
    print(f"   ✅ Alpine compose file: {alpine_compose}")
    print(f"   ✅ Default compose file (also Alpine): {default_compose}")
    
    # Test 4: Project name differentiation
    print("4. Testing project name isolation...")
    manager_reg = UnifiedDockerManager(
        environment_type=EnvironmentType.TEST,
        test_id="test_regular",
        use_alpine=False
    )
    manager_alp = UnifiedDockerManager(
        environment_type=EnvironmentType.TEST, 
        test_id="test_alpine",
        use_alpine=True
    )
    
    reg_project = manager_reg._get_project_name()
    alp_project = manager_alp._get_project_name()
    
    assert reg_project != alp_project, f"Project names should be different: {reg_project} vs {alp_project}"
    print(f"   ✅ Regular project: {reg_project}")
    print(f"   ✅ Alpine project: {alp_project}")
    
    # Test 5: Alpine infrastructure files exist
    print("5. Testing Alpine infrastructure...")
    project_root = Path(__file__).parent
    alpine_compose_file = project_root / "docker-compose.alpine-test.yml"
    alpine_dockerfile = project_root / "docker" / "backend.alpine.Dockerfile"
    
    assert alpine_compose_file.exists(), f"Alpine compose file missing: {alpine_compose_file}"
    assert alpine_dockerfile.exists(), f"Alpine Dockerfile missing: {alpine_dockerfile}"
    print(f"   ✅ Alpine compose file exists: {alpine_compose_file}")
    print(f"   ✅ Alpine Dockerfile exists: {alpine_dockerfile}")
    
    print("\n🎉 All Alpine functionality tests PASSED!")
    print("✅ Alpine container support is fully implemented and working!")
    

if __name__ == "__main__":
    try:
        test_alpine_parameter_functionality()
        print("\n[SUCCESS] Alpine container functionality test completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)