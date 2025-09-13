#!/usr/bin/env python3
"""
Batch migration script for Issue #565: ExecutionEngine to UserExecutionEngine SSOT migration
Migrates the 32 files identified by the validation test.
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple

# Files to migrate from the test output
FILES_TO_MIGRATE = [
    "netra_backend/tests/integration/test_execution_engine_advanced_scenarios.py",
    "netra_backend/tests/integration/test_execution_engine_workflow.py", 
    "netra_backend/tests/integration/agent_execution/test_agent_execution_lifecycle_comprehensive_integration.py",
    "netra_backend/tests/integration/agent_execution/test_agent_execution_orchestration.py",
    "netra_backend/tests/unit/agents/test_execution_engine_comprehensive.py",
    "netra_backend/tests/unit/agents/supervisor/test_execution_engine_complete.py",
    "netra_backend/tests/unit/agents/supervisor/test_execution_engine_comprehensive.py",
    "tests/e2e/test_real_agent_execution_engine.py",
    "tests/integration/test_issue_565_compatibility_bridge_issue_620.py",
    "tests/integration/agent_execution_flows/test_agent_failure_recovery_patterns.py",
    "tests/integration/agent_execution_flows/test_agent_rollback_transaction_consistency.py",
    "tests/integration/agent_execution_flows/test_agent_timeout_resource_exhaustion.py",
    "tests/integration/agent_execution_flows/test_comprehensive_agent_resilience_disaster_recovery.py",
    "tests/integration/agent_execution_flows/test_distributed_agent_failure_coordination.py",
    "tests/integration/concurrency/test_user_isolation_concurrency_issue_620.py",
    "tests/integration/edge_cases_error_scenarios/test_agent_execution_concurrency_limits.py",
    "tests/integration/edge_cases_error_scenarios/test_automatic_retry_backoff_mechanisms.py",
    "tests/integration/edge_cases_error_scenarios/test_cascade_failure_prevention.py",
    "tests/integration/edge_cases_error_scenarios/test_circuit_breaker_failure_recovery.py",
    "tests/integration/edge_cases_error_scenarios/test_database_transaction_boundary_conditions.py",
    "tests/integration/edge_cases_error_scenarios/test_graceful_degradation_under_load.py",
    "tests/integration/edge_cases_error_scenarios/test_service_health_monitoring_recovery.py",
    "tests/integration/edge_cases_error_scenarios/test_shared_resource_synchronization.py",
    "tests/integration/edge_cases_error_scenarios/test_thread_safety_race_condition_boundaries.py",
    "tests/integration/edge_cases_error_scenarios/test_user_session_isolation_boundaries.py",
    "tests/integration/ssot_validation/test_factory_pattern_migration.py",
    "tests/integration/websocket/test_websocket_event_delivery_issue_620.py",
    "tests/unit/agents/test_execution_engine_migration_validation.py",
    "tests/unit/execution_engine_ssot/test_deprecated_engine_import_analysis.py",
    "tests/unit/ssot_validation/test_execution_engine_ssot_migration_issue_620.py",
    "tests/validation/test_execution_engine_ssot_validation_565.py",
    "tests/validation/test_user_execution_engine_security_fixes_565.py"
]

MIGRATION_PATTERNS = [
    # Import statement migrations - ExecutionEngine
    (
        r'from netra_backend\.app\.agents\.supervisor\.execution_engine import ExecutionEngine',
        r'from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine'
    ),
    # Import statement migrations - UserExecutionEngine 
    (
        r'from netra_backend\.app\.agents\.supervisor\.execution_engine import UserExecutionEngine',
        r'from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine'
    ),
    # Import statement migrations - UserExecutionContext (wrong location)
    (
        r'from netra_backend\.app\.agents\.supervisor\.execution_engine import UserExecutionContext',
        r'from netra_backend.app.services.user_execution_context import UserExecutionContext'
    ),
    # Multi-import blocks
    (
        r'from netra_backend\.app\.agents\.supervisor\.execution_engine import \(\s*ExecutionEngine,',
        r'from netra_backend.app.agents.supervisor.user_execution_engine import (\n    UserExecutionEngine as ExecutionEngine,'
    ),
    (
        r'from netra_backend\.app\.agents\.supervisor\.execution_engine import \(\s*ExecutionEngine\s*\)',
        r'from netra_backend.app.agents.supervisor.user_execution_engine import (\n    UserExecutionEngine as ExecutionEngine\n)'
    ),
    # Multi-line import block migration
    (
        r'from netra_backend\.app\.agents\.supervisor\.execution_engine import \(\s*\n\s*ExecutionEngine,',
        r'from netra_backend.app.agents.supervisor.user_execution_engine import (\n    UserExecutionEngine as ExecutionEngine,'
    )
]

def migrate_file(file_path: Path) -> Tuple[bool, List[str]]:
    """Migrate a single file. Returns (success, changes_made)."""
    if not file_path.exists():
        print(f"WARNING: File does not exist: {file_path}")
        return False, [f"File does not exist: {file_path}"]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        for pattern, replacement in MIGRATION_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                content = re.sub(pattern, replacement, content)
                changes_made.append(f"Replaced '{pattern}' with '{replacement}'")
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"MIGRATED: {file_path}")
            for change in changes_made:
                print(f"   - {change}")
            return True, changes_made
        else:
            print(f"NO CHANGES NEEDED: {file_path}")
            return True, []
            
    except Exception as e:
        print(f"ERROR migrating {file_path}: {e}")
        return False, [f"Error: {e}"]

def main():
    """Run the batch migration."""
    project_root = Path.cwd()
    
    print("Starting Issue #565 ExecutionEngine to UserExecutionEngine migration")
    print(f"Project root: {project_root}")
    print(f"Files to migrate: {len(FILES_TO_MIGRATE)}")
    print()
    
    successful_migrations = 0
    failed_migrations = 0
    total_changes = 0
    
    for file_relative_path in FILES_TO_MIGRATE:
        file_path = project_root / file_relative_path.replace('/', os.sep)
        
        success, changes = migrate_file(file_path)
        
        if success:
            successful_migrations += 1
            total_changes += len(changes)
        else:
            failed_migrations += 1
    
    print()
    print("MIGRATION SUMMARY:")
    print(f"   Successful migrations: {successful_migrations}")
    print(f"   Failed migrations: {failed_migrations}")
    print(f"   Total changes made: {total_changes}")
    
    if failed_migrations == 0:
        print("\nAll files migrated successfully!")
        print("\nNext steps:")
        print("   1. Run validation tests: python -m pytest tests/validation/test_execution_engine_ssot_validation_565.py")
        print("   2. Run mission critical tests: python -m pytest tests/mission_critical/test_websocket_agent_events_suite.py")
        print("   3. Remove deprecated file: rm netra_backend/app/agents/supervisor/execution_engine.py")
        return 0
    else:
        print(f"\n{failed_migrations} files failed to migrate. Review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())