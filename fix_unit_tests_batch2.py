#!/usr/bin/env python3
"""
Fix remaining unit test files with DeepAgentState imports
"""
import os
import re

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # Skip the import detection test file - it needs to keep strings intact
        if 'test_deepagentstate_import_detection.py' in filepath:
            print(f"Skipped (import detection test): {filepath}")
            return False

        # Handle multi-imports
        content = re.sub(
            r'from netra_backend\.app\.agents\.state import DeepAgentState, OptimizationsResult, ActionPlanResult',
            'from netra_backend.app.agents.state import OptimizationsResult, ActionPlanResult\nfrom netra_backend.app.schemas.agent_models import DeepAgentState',
            content
        )

        # Handle the special alias case
        content = re.sub(
            r'from netra_backend\.app\.agents\.state import DeepAgentState as AgentsDeepAgentState',
            'from netra_backend.app.schemas.agent_models import DeepAgentState as AgentsDeepAgentState',
            content
        )

        # Handle indented imports (inside functions/classes)
        content = re.sub(
            r'(\s+)from netra_backend\.app\.agents\.state import DeepAgentState',
            r'\1from netra_backend.app.schemas.agent_models import DeepAgentState',
            content
        )

        # Basic replacement
        content = re.sub(
            r'from netra_backend\.app\.agents\.state import DeepAgentState',
            'from netra_backend.app.schemas.agent_models import DeepAgentState',
            content
        )

        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {filepath}")
            return True
        return False
    except Exception as e:
        print(f"Error with {filepath}: {e}")
        return False

# Remaining unit test files
files = [
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_tool_dispatcher_execution_business_logic_comprehensive.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_tool_dispatcher_execution_phase2_batch1.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_tool_dispatcher_execution_unit_batch2.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_tool_dispatcher_integration_phase2_batch1.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_tool_execution_engines_comprehensive_focused.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_workflow_orchestrator_comprehensive_golden_path.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_workflow_orchestrator_ssot_validation.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/performance/test_comprehensive_performance_unit.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/race_conditions/test_agent_execution_state_races.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/test_actions_to_meet_goals_agent_state.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/test_agent.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/test_agent_execution_core_business_logic.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/test_agent_execution_core_unit.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/test_agent_execution_state_flow_cycle2.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/test_agent_reliability_regression.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/test_key_parameters_pydantic_access.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/test_state_model_regression.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/test_state_persistence_user_fk_fix.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/test_subagent_logging.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/test_tool_dispatcher_core_business_logic.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/test_tool_dispatcher_execution.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/test_tool_dispatcher_execution_business_logic.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/test_websocket_event_generation_cycle2.py",
    # Skip this one intentionally
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/migration/test_deepagentstate_import_detection.py"
]

fixed_count = 0
for filepath in files:
    if os.path.exists(filepath) and fix_file(filepath):
        fixed_count += 1

print(f"Fixed {fixed_count} unit test files (batch 2)")