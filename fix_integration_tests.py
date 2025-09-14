#!/usr/bin/env python3
"""
Batch fix for integration tests with DeepAgentState imports
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

# Integration test files
files = [
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/integration/agents/supervisor/test_agent_execution_core_websocket_integration.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/integration/agents/supervisor/test_agent_execution_core_working_integration.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/integration/agents/test_agent_communication_comprehensive_golden_path.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/integration/agents/test_base_agent_integration_comprehensive.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/integration/agents/test_tool_dispatcher_core_integration_phase2_batch1.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/integration/agents/test_tool_dispatcher_execution_integration_batch2.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/integration/agents/test_tool_dispatcher_execution_integration_phase2_batch1.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/integration/agents/test_tool_dispatcher_integration_comprehensive_batch2.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/integration/agents/test_tool_dispatcher_integration_phase2_batch1.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/integration/agents/test_workflow_orchestrator_user_isolation.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/integration/agent_execution/test_agent_execution_orchestration.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/integration/agent_execution/test_agent_failure_recovery_integration.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/integration/agent_execution/test_agent_websocket_events_integration.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/integration/agent_execution/test_concurrent_agent_execution_integration.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/integration/agent_execution/test_multi_agent_workflow_integration.py"
]

fixed_count = 0
for filepath in files:
    if os.path.exists(filepath) and fix_file(filepath):
        fixed_count += 1

print(f"Fixed {fixed_count} files")