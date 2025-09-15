#!/usr/bin/env python3
"""
Fix script files with DeepAgentState imports
"""
import os
import re

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

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

        # Handle the validation script special case
        content = re.sub(
            r"if 'from netra_backend\.app\.agents\.state import DeepAgentState' in source:",
            r"if 'from netra_backend.app.agents.state import DeepAgentState' in source:",
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

# Script files
files = [
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/demo_optimized_persistence.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/test_agent_execution_websocket_integration.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/test_agent_pipeline_simple.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/test_async_serialization_direct.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/test_blocking_analysis.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/test_corpus_admin_direct.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/test_corpus_admin_simple.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/test_execution_engine_fix_validation.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/test_supervisor_websocket_integration.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/test_triage_flow.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/test_websocket_direct.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/validate_agent_coordination_fixes.py",
    # Files with conditional imports need special handling
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/debug_supervisor_test.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/p0_security_stability_validation.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/test_websocket_standalone.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/validate_critical_tests.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/verify_performance_metrics.py",
    "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/validate_datahelperagent_migration.py"
]

fixed_count = 0
for filepath in files:
    if os.path.exists(filepath) and fix_file(filepath):
        fixed_count += 1

print(f"Fixed {fixed_count} script files")