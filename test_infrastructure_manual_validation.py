#!/usr/bin/env python
"""
Manual Infrastructure Validation for Issue #1176 Phase 3
=========================================================

This script runs infrastructure validation without external dependencies
and provides immediate feedback on system state.
"""

import sys
import os
from pathlib import Path

# Setup path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_basic_imports():
    """Test basic imports to validate Python path setup."""
    print("🔍 Testing Basic Imports...")
    
    results = {}
    
    # Test basic system imports
    try:
        import json
        import time
        import subprocess
        results["basic_system"] = True
        print("  ✅ Basic system imports working")
    except ImportError as e:
        results["basic_system"] = False
        print(f"  ❌ Basic system imports failed: {e}")
    
    # Test project structure
    required_dirs = ["tests", "test_framework", "netra_backend", "shared", "scripts"]
    missing_dirs = []
    
    for dir_name in required_dirs:
        if not (project_root / dir_name).exists():
            missing_dirs.append(dir_name)
    
    if missing_dirs:
        results["project_structure"] = False
        print(f"  ❌ Missing directories: {missing_dirs}")
    else:
        results["project_structure"] = True
        print("  ✅ Project structure intact")
    
    # Test critical file existence
    critical_files = [
        "tests/unified_test_runner.py",
        "test_framework/ssot/base_test_case.py",
        "netra_backend/app/config.py"
    ]
    
    missing_files = []
    for file_path in critical_files:
        if not (project_root / file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        results["critical_files"] = False
        print(f"  ❌ Missing critical files: {missing_files}")
    else:
        results["critical_files"] = True
        print("  ✅ Critical files present")
    
    return results

def test_ssot_imports():
    """Test SSOT framework imports."""
    print("\n🔍 Testing SSOT Framework...")
    
    results = {}
    
    # Test SSOT base test case
    try:
        from test_framework.ssot.base_test_case import SSotBaseTestCase
        results["ssot_base"] = True
        print("  ✅ SSOT BaseTestCase import successful")
    except ImportError as e:
        results["ssot_base"] = False
        print(f"  ❌ SSOT BaseTestCase import failed: {e}")
    
    # Test SSOT mock factory
    try:
        from test_framework.ssot.mock_factory import SSotMockFactory
        results["ssot_mock"] = True
        print("  ✅ SSOT MockFactory import successful")
    except ImportError as e:
        results["ssot_mock"] = False
        print(f"  ❌ SSOT MockFactory import failed: {e}")
    
    # Test unified test runner
    try:
        from tests.unified_test_runner import UnifiedTestRunner
        results["unified_runner"] = True
        print("  ✅ UnifiedTestRunner import successful")
    except ImportError as e:
        results["unified_runner"] = False
        print(f"  ❌ UnifiedTestRunner import failed: {e}")
    
    return results

def test_application_imports():
    """Test core application imports."""
    print("\n🔍 Testing Application Imports...")
    
    results = {}
    
    # Test config system
    try:
        from netra_backend.app.config import get_config
        config = get_config()
        results["config_system"] = True
        print("  ✅ Config system import successful")
    except ImportError as e:
        results["config_system"] = False
        print(f"  ❌ Config system import failed: {e}")
    except Exception as e:
        results["config_system"] = False
        print(f"  ❌ Config system instantiation failed: {e}")
    
    # Test database manager
    try:
        from netra_backend.app.db.database_manager import DatabaseManager
        results["database_manager"] = True
        print("  ✅ DatabaseManager import successful")
    except ImportError as e:
        results["database_manager"] = False
        print(f"  ❌ DatabaseManager import failed: {e}")
    
    # Test WebSocket manager
    try:
        from netra_backend.app.websocket_core.manager import WebSocketManager
        results["websocket_manager"] = True
        print("  ✅ WebSocketManager import successful")
    except ImportError as e:
        results["websocket_manager"] = False
        print(f"  ❌ WebSocketManager import failed: {e}")
    
    # Test agent system
    try:
        from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
        results["supervisor_agent"] = True
        print("  ✅ SupervisorAgent import successful")
    except ImportError as e:
        results["supervisor_agent"] = False
        print(f"  ❌ SupervisorAgent import failed: {e}")
    
    # Test CORS config
    try:
        from shared.cors_config import get_cors_config
        results["cors_config"] = True
        print("  ✅ CORS config import successful")
    except ImportError as e:
        results["cors_config"] = False
        print(f"  ❌ CORS config import failed: {e}")
    
    return results

def test_environment_setup():
    """Test environment setup."""
    print("\n🔍 Testing Environment Setup...")
    
    results = {}
    
    # Test isolated environment
    try:
        from dev_launcher.isolated_environment import IsolatedEnvironment
        env = IsolatedEnvironment()
        test_val = env.get("HOME", "default")
        results["isolated_environment"] = True
        print("  ✅ IsolatedEnvironment working")
    except ImportError as e:
        results["isolated_environment"] = False
        print(f"  ❌ IsolatedEnvironment import failed: {e}")
    except Exception as e:
        results["isolated_environment"] = False
        print(f"  ❌ IsolatedEnvironment instantiation failed: {e}")
    
    # Test Python path
    current_path = sys.path
    has_project_root = any(str(project_root) in path for path in current_path)
    
    results["python_path"] = has_project_root
    if has_project_root:
        print("  ✅ Python path includes project root")
    else:
        print("  ❌ Python path missing project root")
    
    return results

def generate_validation_report(all_results):
    """Generate validation report."""
    print("\n" + "="*60)
    print("📊 INFRASTRUCTURE VALIDATION REPORT")
    print("="*60)
    
    total_tests = 0
    passed_tests = 0
    
    for category, results in all_results.items():
        print(f"\n🔧 {category.upper()}:")
        
        for test_name, result in results.items():
            total_tests += 1
            if result:
                passed_tests += 1
                print(f"  ✅ {test_name}")
            else:
                print(f"  ❌ {test_name}")
    
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"\n📈 SUMMARY:")
    print(f"  • Total Tests: {total_tests}")
    print(f"  • Passed: {passed_tests}")
    print(f"  • Failed: {total_tests - passed_tests}")
    print(f"  • Success Rate: {success_rate:.1f}%")
    
    # Determine overall health
    if success_rate >= 90:
        health_status = "HEALTHY 🟢"
    elif success_rate >= 75:
        health_status = "STABLE WITH ISSUES 🟡"
    elif success_rate >= 50:
        health_status = "DEGRADED 🟠"
    else:
        health_status = "CRITICAL 🔴"
    
    print(f"  • Overall Health: {health_status}")
    
    # Critical recommendations
    print(f"\n💡 CRITICAL NEXT STEPS:")
    
    if not all_results.get("basic_imports", {}).get("project_structure", True):
        print("  1. Fix missing project directories")
    
    if not all_results.get("basic_imports", {}).get("critical_files", True):
        print("  2. Restore missing critical files")
    
    if not all_results.get("ssot_imports", {}).get("unified_runner", True):
        print("  3. Fix UnifiedTestRunner import issues")
    
    if not all_results.get("application_imports", {}).get("config_system", True):
        print("  4. Fix configuration system")
    
    if success_rate < 75:
        print("  5. Focus on infrastructure fixes before feature development")
    
    print("\n" + "="*60)
    
    return success_rate

def main():
    """Run manual infrastructure validation."""
    print("🚀 Starting Manual Infrastructure Validation for Issue #1176")
    print(f"📁 Project Root: {project_root}")
    print(f"🐍 Python Version: {sys.version}")
    
    # Run all validation tests
    all_results = {
        "basic_imports": test_basic_imports(),
        "ssot_imports": test_ssot_imports(), 
        "application_imports": test_application_imports(),
        "environment_setup": test_environment_setup()
    }
    
    # Generate report
    success_rate = generate_validation_report(all_results)
    
    # Save results for documentation update
    import json
    evidence_file = project_root / "manual_validation_evidence_issue_1176.json"
    
    evidence_data = {
        "timestamp": str(Path(__file__).stat().st_mtime),
        "validation_results": all_results,
        "success_rate": success_rate,
        "total_tests": sum(len(results) for results in all_results.values()),
        "passed_tests": sum(sum(results.values()) for results in all_results.values())
    }
    
    with open(evidence_file, 'w') as f:
        json.dump(evidence_data, f, indent=2)
    
    print(f"\n📄 Evidence saved to: {evidence_file}")
    
    # Return appropriate exit code
    return 0 if success_rate >= 75 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)