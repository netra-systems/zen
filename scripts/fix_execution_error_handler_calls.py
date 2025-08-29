#!/usr/bin/env python3
"""
Fix ExecutionErrorHandler instantiation calls across the codebase.

The ExecutionErrorHandler is an instance, not a class, so it should not be called.
This script replaces all instances of ExecutionErrorHandler with ExecutionErrorHandler.
"""

import os
import re
from pathlib import Path

def fix_execution_error_handler_calls():
    """Fix all ExecutionErrorHandler calls in the codebase."""
    
    # Get the project root
    project_root = Path(__file__).parent.parent
    
    # Files to fix based on grep results
    files_to_fix = [
        "netra_backend/tests/critical/test_execution_context_hashable_regression.py",
        "netra_backend/app/agents/triage_sub_agent.py", 
        "netra_backend/app/agents/triage_sub_agent/processing.py",
        "netra_backend/app/agents/triage_sub_agent/executor.py",
        "netra_backend/app/agents/synthetic_data/core.py",
        "netra_backend/app/agents/supervisor_consolidated.py",
        "netra_backend/app/agents/reporting_sub_agent.py",
        "netra_backend/app/agents/optimizations_core_sub_agent.py",
        "netra_backend/app/agents/mcp_integration/mcp_intent_detector.py",
        "netra_backend/app/agents/mcp_integration/context_manager.py",
        "netra_backend/app/agents/demo_service/optimization.py",
        "netra_backend/app/agents/data_sub_agent/execution_engine.py",
        "netra_backend/app/agents/data_sub_agent/execution_core.py",
        "netra_backend/app/agents/data_sub_agent/anomaly_detector.py",
        "netra_backend/app/agents/data_sub_agent/analysis_engine.py",
        "netra_backend/app/agents/corpus_admin/agent.py",
        "netra_backend/app/agents/admin_tool_dispatcher/validation.py",
        "netra_backend/app/agents/admin_tool_dispatcher/tool_handlers_core.py",
        "netra_backend/app/agents/actions_agent_execution.py",
        "netra_backend/app/agents/actions_to_meet_goals_sub_agent.py"
    ]
    
    # Pattern to match ExecutionErrorHandler calls (with optional whitespace)
    pattern = r'ExecutionErrorHandler\s*\(\s*\)'
    replacement = 'ExecutionErrorHandler'
    
    fixed_files = []
    skipped_files = []
    
    for file_path in files_to_fix:
        full_path = project_root / file_path
        
        if not full_path.exists():
            skipped_files.append(file_path)
            continue
            
        try:
            # Read the file
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if the pattern exists
            if pattern in content:
                # Replace the pattern
                new_content = re.sub(pattern, replacement, content)
                
                # Write back the file
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                fixed_files.append(file_path)
                print(f"Fixed: {file_path}")
            else:
                print(f"No changes needed: {file_path}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            skipped_files.append(file_path)
    
    print(f"\nSummary:")
    print(f"Fixed {len(fixed_files)} files")
    print(f"Skipped {len(skipped_files)} files")
    
    if skipped_files:
        print(f"Skipped files: {skipped_files}")

if __name__ == "__main__":
    fix_execution_error_handler_calls()