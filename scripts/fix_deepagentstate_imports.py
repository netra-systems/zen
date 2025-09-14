#!/usr/bin/env python3
"""
Fix DeepAgentState import errors across all test files.

This script fixes the SSOT migration issue where DeepAgentState was moved
from netra_backend.app.agents.state to netra_backend.app.schemas.agent_models.

Business Impact: Enables discovery of 133+ test files that are currently
failing collection due to import errors.
"""

import os
import sys
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def fix_deepagentstate_imports(file_path: Path) -> bool:
    """Fix DeepAgentState import in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match the deprecated import
        old_pattern = r'from netra_backend\.app\.agents\.state import DeepAgentState'
        new_import = 'from netra_backend.app.schemas.agent_models import DeepAgentState'
        
        # Check if the file needs fixing
        if re.search(old_pattern, content):
            # Replace the import
            new_content = re.sub(old_pattern, new_import, content)
            
            # Write back the fixed content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"✅ Fixed: {file_path}")
            return True
        
        return False
            
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def main():
    """Fix all DeepAgentState imports across the codebase"""
    print("🔧 Fixing DeepAgentState import errors...")
    
    # Files to process (from grep results)
    target_files = [
        "tests/test_websocket_critical_fix_validation.py",
        "tests/stress/test_supervisor_stress.py", 
        "tests/performance/websocket/test_websocket_agent_event_load.py",
        "tests/performance/test_agent_performance_metrics.py",
        "tests/netra_backend/agents/test_execution_isolation.py",
        "tests/mission_critical/test_websocket_mission_critical_fixed.py",
        "tests/mission_critical/test_websocket_json_performance.py",
        "tests/mission_critical/test_websocket_final.py",
        "tests/mission_critical/test_websocket_events_advanced.py",
        "tests/mission_critical/test_websocket_bridge_integration.py",
        "tests/mission_critical/test_websocket_basic.py",
        "tests/mission_critical/test_websocket_agent_performance_benchmarks.py",
        "tests/mission_critical/test_tool_discovery_golden.py",
        "tests/mission_critical/test_supervisor_websocket_validation.py",
        "tests/mission_critical/test_supervisor_golden_pattern.py",
        "tests/mission_critical/test_supervisor_golden_compliance_comprehensive.py",
        "tests/mission_critical/test_database_session_isolation.py",
        "tests/mission_critical/test_data_sub_agent_golden_ssot.py",
        "tests/mission_critical/test_circuit_breaker_comprehensive.py",
        "tests/mission_critical/test_chat_responsiveness_under_load.py",
        "tests/mission_critical/test_baseagent_edge_cases_comprehensive.py",
        "tests/mission_critical/test_agent_resilience_patterns.py",
        "tests/mission_critical/test_agent_error_context_handling.py",
        "tests/mission_critical/test_actions_to_meet_goals_golden.py",
        "tests/integration/test_split_architecture_integration.py",
        "tests/integration/test_agent_websocket_ssot.py",
        "tests/integration/test_agent_instance_factory_isolation.py",
        "tests/enhanced_error_handling_tests.py",
        "tests/e2e/websocket_e2e_tests/test_websocket_reconnection_during_agent_execution.py",
        "tests/e2e/websocket_e2e_tests/test_multi_user_concurrent_agent_execution.py",
        "tests/e2e/websocket_e2e_tests/test_complete_chat_business_value_flow.py",
        "tests/e2e/websocket_e2e_tests/test_complete_agent_execution_with_events.py",
        "tests/e2e/websocket_e2e_tests/test_agent_execution_websocket_integration.py",
        "tests/e2e/websocket/test_websocket_reconnection_during_agent_execution.py",
        "tests/e2e/websocket/test_multi_user_concurrent_agent_execution.py",
        "tests/e2e/websocket/test_complete_chat_business_value_flow.py",
        "tests/e2e/websocket/test_complete_agent_execution_with_events.py",
        "tests/e2e/websocket/test_agent_execution_websocket_integration.py",
        "tests/e2e/test_user_message_agent_pipeline.py",
        "tests/e2e/test_supervisor_real_llm_integration.py",
        "tests/e2e/test_supervisor_orchestration_e2e.py",
        "tests/e2e/test_primary_chat_websocket_flow.py",
        "tests/e2e/test_multi_agent_collaboration_response.py",
        "tests/e2e/test_minimal_3agent_workflow.py",
        "tests/e2e/test_chat_ui_flow_comprehensive.py",
        "tests/e2e/test_agent_context_isolation_integration.py",
        "tests/e2e/test_actions_to_meet_goals_user_experience_failure.py",
        "tests/e2e/state/test_user_session_state_continuity.py",
        "tests/e2e/state/test_multi_browser_state_isolation.py",
        "tests/e2e/resilience/test_response_persistence_recovery.py",
        "tests/e2e/journeys/test_agent_response_flow.py",
        "tests/e2e/agent_startup_integration.py",
        "tests/critical/test_websocket_notification_failures_comprehensive.py",
        "tests/critical/phase1/test_triage_context_migration.py",
        "tests/critical/phase1/test_supervisor_context_migration.py",
        "tests/critical/phase1/test_data_context_migration.py",
        "tests/chat_system/test_nacis_standalone.py",
        "tests/e2e/test_cold_start_critical_issues.py",
        "tests/e2e/performance/test_agent_orchestration_production.py",
        "tests/e2e/test_agent_context_accumulation.py",
        "tests/e2e/test_agent_pipeline_critical.py",
        "tests/e2e/test_multi_agent_collaboration_integration.py",
        "tests/e2e/test_agent_tool_websocket_flow_e2e.py",
        "tests/e2e/test_real_agent_pipeline.py",
        "tests/e2e/test_agent_orchestration.py",
        "tests/e2e/agent_orchestration_fixtures.py",
        "tests/e2e/agent_response_test_utilities.py",
        "tests/e2e/test_websocket_events_during_execution.py",
        "tests/e2e/agents/test_tool_dispatcher_core_e2e_phase2_batch1.py",
        "tests/e2e/agents/test_tool_dispatcher_execution_e2e_phase2_batch1.py",
        "tests/e2e/test_agent_compensation_integration_fixtures.py",
        "tests/e2e/integration/test_agent_orchestration.py",
        "tests/e2e/test_agent_compensation_integration_helpers.py",
        "tests/e2e/test_critical_agent_chat_flow.py",
        "tests/e2e/test_corpus_admin_e2e.py",
        "tests/e2e/test_real_agent_execution_engine.py",
        "tests/e2e/test_synthetic_data_e2e.py",
        "tests/e2e/test_tool_dispatcher_execution_e2e_batch2.py",
        "tests/fixtures/golden_datasets.py",
        "tests/mission_critical/test_deepagentstate_business_protection.py",
        "tests/mission_critical/test_websocket_agent_events_suite.py",
        "tests/mission_critical/test_inheritance_refactor_validation.py",
        "tests/mission_critical/test_baseagent_inheritance_violations.py",
        "tests/mission_critical/test_websocket_event_guarantees.py",
        "tests/mission_critical/test_websocket_bridge_lifecycle_audit_20250902.py",
        "tests/mission_critical/test_agent_type_safety_comprehensive.py",
        "tests/mission_critical/test_orchestration_partial_data_handling.py",
        "tests/mission_critical/test_inheritance_architecture_violations.py",
        "tests/mission_critical/test_agent_death_fix_complete.py",
        "tests/mission_critical/test_agent_execution_llm_failure_websocket_events.py",
        "tests/mission_critical/test_websocket_json_agent_events.py",
        "tests/load/test_production_load_persistence.py",
        "tests/unit/ssot/test_deepagentstate_production_imports.py",
        "netra_backend/app/agents/supervisor/user_execution_engine.py",
        "netra_backend/app/agents/request_scoped_tool_dispatcher.py",
        "test_framework/fixtures/agent_fixtures.py",
        "test_framework/examples/unified_agent_test_example.py",
        "netra_backend/app/agents/supervisor/pipeline_executor.py",
        "netra_backend/app/agents/supervisor/execution_context.py",
        "netra_backend/app/agents/supervisor/mcp_execution_engine.py"
    ]
    
    fixed_count = 0
    total_count = 0
    
    for relative_path in target_files:
        file_path = PROJECT_ROOT / relative_path
        if file_path.exists():
            total_count += 1
            if fix_deepagentstate_imports(file_path):
                fixed_count += 1
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print(f"\n📊 Summary:")
    print(f"   Total files processed: {total_count}")
    print(f"   Files fixed: {fixed_count}")
    print(f"   Performance improvement: {fixed_count} files now available for test collection")
    
    return fixed_count > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)