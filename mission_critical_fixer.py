#!/usr/bin/env python3
"""
Mission Critical Test File Syntax Fixer
Handles specific patterns found in mission critical tests
"""

import os
import re
from pathlib import Path

def fix_mission_critical_file(file_path):
    """Fix specific patterns in mission critical test files."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Pattern 1: Fix the common pattern with WebSocket closed check
        pattern1 = r'if self\._closed:\s*raise RuntimeError\("WebSocket is closed"\)'
        replacement1 = 'if self._closed:\n            raise RuntimeError("WebSocket is closed")'
        content = re.sub(pattern1, replacement1, content)

        # Pattern 2: Fix common indentation after if statements
        pattern2 = r'if [^:]*:\s*([A-Za-z])'
        def fix_indentation(match):
            full_match = match.group(0)
            statement = match.group(1)
            # Find the line and add proper indentation
            if_part = full_match.replace(statement, '').strip()
            return if_part + '\n            ' + statement

        # Only apply if the pattern indicates missing indentation
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            # Check for if statements that need indentation fixes
            if (line.strip().endswith(':') and
                i + 1 < len(lines) and
                lines[i + 1].strip() and
                not lines[i + 1].startswith('    ') and
                not lines[i + 1].startswith('\t') and
                ('if ' in line or 'except' in line or 'try:' in line)):

                # Fix the indentation
                fixed_lines.append(line)
                next_line = lines[i + 1].strip()
                if next_line:
                    # Calculate proper indentation
                    current_indent = len(line) - len(line.lstrip())
                    fixed_lines.append(' ' * (current_indent + 4) + next_line)
                    # Mark next line as processed
                    lines[i + 1] = ""
            elif lines[i]:  # Only add non-empty lines (unless they were marked as processed)
                fixed_lines.append(line)

        content = '\n'.join(fixed_lines)

        # Pattern 3: Fix unterminated string literals
        content = re.sub(r'print\("\s*\)', 'print("")', content)

        # Pattern 4: Fix unmatched parentheses in specific contexts
        content = re.sub(r'\{\s*\)\)', '}', content)
        content = re.sub(r'\[\s*\)', ']', content)
        content = re.sub(r'\{\s*\)', '}', content)

        # Pattern 5: Fix function definitions missing colons
        content = re.sub(r'def ([^:]*)\s*$', r'def \1:', content, flags=re.MULTILINE)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Fix mission critical test files."""

    # Mission critical files with the common patterns
    mission_critical_files = [
        "tests/mission_critical/test_agent_death_after_triage.py",
        "tests/mission_critical/test_agent_death_fix_complete.py",
        "tests/mission_critical/test_agent_error_context_handling.py",
        "tests/mission_critical/test_baseagent_edge_cases_comprehensive.py",
        "tests/mission_critical/test_data_sub_agent_golden_ssot.py",
        "tests/mission_critical/test_data_sub_agent_ssot_compliance.py",
        "tests/mission_critical/test_database_session_isolation.py",
        "tests/mission_critical/test_discover_all_message_types.py",
        "tests/mission_critical/test_docker_lifecycle_management.py",
        "tests/mission_critical/test_docker_unified_fixes_validation.py",
        "tests/mission_critical/test_eliminate_placeholder_values.py",
        "tests/mission_critical/test_final_validation.py",
        "tests/mission_critical/test_goals_triage_golden.py",
        "tests/mission_critical/test_mcp_initialization_fix.py",
        "tests/mission_critical/test_orchestration_system_suite.py",
        "tests/mission_critical/test_reliability_consolidation_ssot.py",
        "tests/mission_critical/test_reporting_agent_ssot_violations.py",
        "tests/mission_critical/test_security_boundaries_comprehensive.py",
        "tests/mission_critical/test_service_factory_websocket_bug.py",
        "tests/mission_critical/test_service_secret_dependency.py",
        "tests/mission_critical/test_ssot_orchestration_consolidation.py",
        "tests/mission_critical/test_supervisor_golden_compliance_comprehensive.py",
        "tests/mission_critical/test_supervisor_golden_pattern.py",
        "tests/mission_critical/test_supervisor_websocket_validation.py",
        "tests/mission_critical/test_threads_500_error_fix.py",
        "tests/mission_critical/test_tool_discovery_golden.py",
        "tests/mission_critical/test_triage_agent_ssot_compliance.py",
        "tests/mission_critical/test_triage_agent_ssot_violations.py",
        "tests/mission_critical/test_unified_id_manager_validation.py",
        "tests/mission_critical/test_unified_websocket_events.py",
        "tests/mission_critical/test_websocket_bridge_consistency.py",
        "tests/mission_critical/test_websocket_context_refactor.py",
        "tests/mission_critical/test_websocket_e2e_proof.py",
        "tests/mission_critical/test_websocket_edge_cases.py",
        "tests/mission_critical/test_websocket_initialization_order.py",
        "tests/mission_critical/test_websocket_runid_fix.py",
        "tests/mission_critical/test_websocket_simple.py",
        "tests/mission_critical/test_websocket_ssot_fix_validation.py",
        "tests/mission_critical/test_websocket_ssot_validation.py",
        "tests/mission_critical/test_websocket_unified_json_handler.py",
        "tests/mission_critical/validate_docker_stability.py"
    ]

    root = Path(".")
    fixed_count = 0

    print("MISSION CRITICAL SYNTAX FIXER")
    print("="*50)

    for file_path_str in mission_critical_files:
        file_path = root / file_path_str
        if file_path.exists():
            print(f"Fixing: {file_path}")
            if fix_mission_critical_file(file_path):
                fixed_count += 1
                print(f"  FIXED")
            else:
                print(f"  OK")
        else:
            print(f"  NOT FOUND: {file_path}")

    print(f"\nFixed {fixed_count} mission critical files")
    return fixed_count

if __name__ == "__main__":
    main()