#!/usr/bin/env python3
"""
Batch fix script for DeepAgentState imports - handling multi-imports
"""
import os
import re

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # Handle multi-import case like: DeepAgentState, OptimizationsResult
        content = re.sub(
            r'from netra_backend\.app\.agents\.state import DeepAgentState, OptimizationsResult',
            'from netra_backend.app.agents.state import OptimizationsResult\nfrom netra_backend.app.schemas.agent_models import DeepAgentState',
            content
        )

        # Handle basic case
        content = re.sub(
            r'from netra_backend\.app\.agents\.state import DeepAgentState',
            'from netra_backend.app.schemas.agent_models import DeepAgentState',
            content
        )

        # Handle cases with AgentMetadata
        content = re.sub(
            r'from netra_backend\.app\.agents\.state import AgentMetadata, DeepAgentState',
            'from netra_backend.app.agents.state import AgentMetadata\nfrom netra_backend.app.schemas.agent_models import DeepAgentState',
            content
        )

        content = re.sub(
            r'from netra_backend\.app\.agents\.state import DeepAgentState, AgentMetadata',
            'from netra_backend.app.agents.state import AgentMetadata\nfrom netra_backend.app.schemas.agent_models import DeepAgentState',
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

files = [
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/agent_response_test_utilities.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/agent_startup_integration.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/isolation/test_multi_user_agent_execution_isolation.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/isolation/test_user_authentication_websocket_binding.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/journeys/test_agent_response_flow.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/performance/test_agent_orchestration_production.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/state/test_multi_browser_state_isolation.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/state/test_user_session_state_continuity.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/test_actions_to_meet_goals_user_experience_failure.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/test_agent_compensation_integration_fixtures.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/test_agent_compensation_integration_helpers.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/test_agent_context_accumulation.py"
]

fixed_count = 0
for filepath in files:
    if os.path.exists(filepath) and fix_file(filepath):
        fixed_count += 1

print(f"Fixed {fixed_count} files")