#!/usr/bin/env python3
"""
Find import issues in unit test files.
"""

import os
import re

def find_import_issues():
    """Find problematic imports in test files."""
    
    issues = []
    
    # Specific test files mentioned in the problem
    test_files = [
        'netra_backend/tests/unit/agents/test_tool_execution_error_handling_resilience.py',
        'netra_backend/tests/unit/agents/test_unified_tool_execution_websocket_notifications.py', 
        'netra_backend/tests/unit/core/registry/test_tool_registry_dynamic_discovery.py'
    ]
    
    # Problematic import patterns
    bad_patterns = [
        (r'from shared\.session_context\.session_factory import', 'from netra_backend.app.database.request_scoped_session_factory import'),
        (r'from.*StructuredMessageBridge', 'from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge'),
        (r'import.*StructuredMessageBridge', 'from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge'),
    ]
    
    for file_path in test_files:
        if not os.path.exists(file_path):
            issues.append(f" FAIL:  File not found: {file_path}")
            continue
            
        with open(file_path, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            
        for line_num, line in enumerate(lines, 1):
            for bad_pattern, suggestion in bad_patterns:
                if re.search(bad_pattern, line):
                    issues.append(f" FAIL:  {file_path}:{line_num} - {line.strip()}")
                    issues.append(f"   Suggested fix: {suggestion}")
    
    # Check for missing langchain dependencies
    for file_path in test_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                if 'from langchain_core' in content:
                    issues.append(f" WARNING: [U+FE0F]  {file_path} requires langchain_core (missing dependency)")
                if 'import pytest' in content:
                    issues.append(f" WARNING: [U+FE0F]  {file_path} requires pytest (missing dependency)")
    
    return issues

if __name__ == '__main__':
    issues = find_import_issues()
    
    if not issues:
        print(" PASS:  No import issues found!")
    else:
        print("Found import issues:")
        for issue in issues:
            print(issue)