#!/usr/bin/env python3
"""
Quick directory fix script
"""
import os
import sys
import re

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content
        # Replace the problematic import
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

if __name__ == "__main__":
    files = [
        "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/e2e/chat_optimization_tests.py",
        "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/e2e/example_prompts_core.py",
        "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/e2e/example_prompts_tests.py",
        "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/e2e/latency_optimization_helpers.py",
        "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/e2e/multi_constraint_test_helpers.py",
        "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/e2e/scaling_test_helpers.py",
        "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/e2e/state_validation_utils.py",
        "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/e2e/test_agent_execution_core_complete_flow.py",
        "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/e2e/test_capacity_planning.py",
        "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/e2e/test_kv_cache_audit.py",
        "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/e2e/test_rate_limit_analysis.py",
        "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/e2e/test_usage_increase_analysis.py",
        "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/e2e/validators/data_integrity_validator.py",
        "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/e2e/validators/example_usage.py"
    ]

    fixed_count = 0
    for filepath in files:
        if os.path.exists(filepath) and fix_file(filepath):
            fixed_count += 1

    print(f"Fixed {fixed_count} files")