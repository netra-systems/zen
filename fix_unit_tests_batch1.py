#!/usr/bin/env python3
"""
Fix unit test files batch 1 with DeepAgentState imports
"""
import os
import re

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

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

# Unit test files batch 1
files = [
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/supervisor/test_agent_execution_core_enhanced_unit.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/supervisor/test_agent_execution_core_metrics_unit.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/supervisor/test_execution_engine_complete.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/supervisor/test_execution_engine_comprehensive.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/supervisor/test_execution_engine_race_conditions.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/supervisor/test_user_execution_engine_comprehensive.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_agent_execution_core_comprehensive.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_corpus_admin_production_fix.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_execution_engine_consolidated_comprehensive.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_execution_engine_consolidated_comprehensive_focused.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_execution_engine_lifecycle.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_pipeline_executor_comprehensive_golden_path.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_supervisor_missing_attributes_issue_408.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_tool_dispatcher_core.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_tool_dispatcher_core_batch2.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_tool_dispatcher_core_business_logic_comprehensive.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_tool_dispatcher_core_comprehensive_unit.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_tool_dispatcher_core_phase2_batch1.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_tool_dispatcher_execution.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/test_tool_dispatcher_execution_batch2.py"
]

fixed_count = 0
for filepath in files:
    if os.path.exists(filepath) and fix_file(filepath):
        fixed_count += 1

print(f"Fixed {fixed_count} unit test files (batch 1)")