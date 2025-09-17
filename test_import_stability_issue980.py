#!/usr/bin/env python3
"""
Import stability test for Issue #980 verification
Tests that all modified modules can be imported successfully after migration
"""

import sys
import traceback
from typing import List, Tuple

def test_import(module_name: str) -> Tuple[bool, str]:
    """Test if a module can be imported successfully"""
    try:
        __import__(module_name)
        return True, f"✅ {module_name}"
    except Exception as e:
        return False, f"❌ {module_name}: {str(e)}"

def main():
    """Test imports for all modules modified in Issue #980"""

    print("🔍 Testing imports for Issue #980 modified modules...")
    print("=" * 60)

    # Modules modified in Phase 1: BaseExecutionEngine → UserExecutionEngine
    phase1_modules = [
        "netra_backend.app.agents.supervisor.execution_engine",
        "netra_backend.app.agents.registry",
        "netra_backend.app.agents.supervisor_agent_modern",
        "netra_backend.app.routes.websocket",
        "netra_backend.app.websocket_core.manager"
    ]

    # Key modules modified in Phase 2: datetime.utcnow() → datetime.now(UTC)
    phase2_modules = [
        "netra_backend.app.db.models_auth",
        "netra_backend.app.db.models_corpus",
        "netra_backend.app.db.models_metrics",
        "netra_backend.app.services.state_persistence_optimized",
        "netra_backend.app.agents.supervisor.workflow_orchestrator",
        "netra_backend.app.agents.data_helper_agent",
        "netra_backend.app.agents.apex_optimizer_agent",
        "netra_backend.app.tools.enhanced_dispatcher",
        "netra_backend.app.websocket_core.auth",
        "netra_backend.app.auth_integration.auth"
    ]

    # Additional critical modules to verify
    critical_modules = [
        "netra_backend.app.core.app_state_contracts",
        "netra_backend.app.core.configuration.base",
        "netra_backend.app.agents.prompts.supervisor_prompts"
    ]

    all_modules = phase1_modules + phase2_modules + critical_modules

    results = []
    failed_imports = []

    print("Testing Phase 1 modules (BaseExecutionEngine → UserExecutionEngine):")
    for module in phase1_modules:
        success, message = test_import(module)
        results.append((success, message))
        if not success:
            failed_imports.append(module)
        print(f"  {message}")

    print("\nTesting Phase 2 modules (datetime.utcnow() → datetime.now(UTC)):")
    for module in phase2_modules:
        success, message = test_import(module)
        results.append((success, message))
        if not success:
            failed_imports.append(module)
        print(f"  {message}")

    print("\nTesting critical modules:")
    for module in critical_modules:
        success, message = test_import(module)
        results.append((success, message))
        if not success:
            failed_imports.append(module)
        print(f"  {message}")

    print("\n" + "=" * 60)

    total_modules = len(all_modules)
    successful_imports = len([r for r in results if r[0]])

    print(f"📊 IMPORT TEST SUMMARY:")
    print(f"   Total modules tested: {total_modules}")
    print(f"   Successful imports: {successful_imports}")
    print(f"   Failed imports: {len(failed_imports)}")

    if failed_imports:
        print(f"\n❌ FAILED IMPORTS:")
        for module in failed_imports:
            print(f"   - {module}")
        return False
    else:
        print(f"\n✅ ALL IMPORTS SUCCESSFUL!")
        print(f"   System stability maintained after Issue #980 changes")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)