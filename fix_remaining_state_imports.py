#!/usr/bin/env python3
"""
Fix remaining DeepAgentState imports that were missed by linter modifications
"""
import os
import re

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # Basic replacement for any remaining state imports
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

# Files that were modified by linter but still have wrong imports
files = [
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/test_minimal_3agent_workflow.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/test_agent_tool_websocket_flow_e2e.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/test_real_agent_pipeline.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/test_corpus_admin_e2e.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/test_real_agent_execution_engine.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/e2e/test_critical_agent_chat_flow.py"
]

fixed_count = 0
for filepath in files:
    if os.path.exists(filepath) and fix_file(filepath):
        fixed_count += 1

print(f"Fixed {fixed_count} files")