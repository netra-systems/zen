#!/usr/bin/env python3
"""
Test compilation of multiple files to assess progress
"""

import os
import ast
from pathlib import Path

def test_compilation_batch():
    """Test compilation of key files"""

    # Priority files for testing
    test_files = [
        "tests/mission_critical/conftest_isolated.py",
        "tests/mission_critical/conftest_isolated_websocket.py",
        "tests/mission_critical/test_websocket_agent_events_suite.py",
        "tests/test_websocket_simple.py",
        "tests/test_websocket_fix_validation.py",
        "tests/e2e/test_websocket_auth_ssot_fix.py" if Path("tests/e2e/test_websocket_auth_ssot_fix.py").exists() else None,
        "tests/mission_critical/test_agent_execution_business_value.py",
        "tests/mission_critical/test_agent_factory_ssot_validation.py",
        "tests/mission_critical/test_docker_stability_suite.py"
    ]

    # Filter out None entries
    test_files = [f for f in test_files if f and Path(f).exists()]

    compiled_successfully = []
    failed_compilation = []

    for file_path in test_files:
        print(f"Testing {file_path}...", end=" ")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content, filename=file_path)
            compiled_successfully.append(file_path)
            print("PASS")
        except SyntaxError as e:
            failed_compilation.append((file_path, f"Line {e.lineno}: {e.msg}"))
            print(f"FAIL - Line {e.lineno}: {e.msg}")
        except Exception as e:
            failed_compilation.append((file_path, str(e)))
            print(f"ERROR - {e}")

    print(f"\n--- COMPILATION RESULTS ---")
    print(f"Successful: {len(compiled_successfully)}/{len(test_files)}")
    print(f"Failed: {len(failed_compilation)}/{len(test_files)}")

    if compiled_successfully:
        print(f"\nWORKING FILES:")
        for file_path in compiled_successfully:
            print(f"  {file_path}")

    if failed_compilation:
        print(f"\nFAILED FILES:")
        for file_path, error in failed_compilation:
            print(f"  {file_path}: {error}")

    return compiled_successfully, failed_compilation

if __name__ == "__main__":
    compiled_successfully, failed_compilation = test_compilation_batch()
    print(f"\nPROGRESS: {len(compiled_successfully)} files now compile successfully!")