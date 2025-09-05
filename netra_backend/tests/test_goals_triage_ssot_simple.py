"""
Simple SSOT Violation Detection Test for GoalsTriageSubAgent

This test directly checks the source code for SSOT violations.
"""

import ast
import re
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment


def test_goals_triage_json_violations():
    """
    Test that detects direct json.loads/dumps usage in GoalsTriageSubAgent.
    This test will FAIL with current implementation and PASS after fixes.
    """
    # Read the source file
    agent_file = Path(__file__).parent.parent / "app" / "agents" / "goals_triage_sub_agent.py"
    source_code = agent_file.read_text()
    
    # Parse the AST
    tree = ast.parse(source_code)
    
    violations = []
    
    # Walk through all nodes in the AST
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check for json.loads()
            if (isinstance(node.func, ast.Attribute) and
                isinstance(node.func.value, ast.Name) and
                node.func.value.id == 'json' and
                node.func.attr in ['loads', 'dumps']):
                violations.append({
                    'line': node.lineno,
                    'method': f"json.{node.func.attr}",
                    'violation': 'Direct json usage instead of LLMResponseParser'
                })
    
    # Print violations found
    if violations:
        print("\n=== SSOT VIOLATIONS FOUND ===")
        for v in violations:
            print(f"Line {v['line']}: {v['method']} - {v['violation']}")
        print(f"\nTotal violations: {len(violations)}")
        print("\nExpected fixes:")
        print("- Line 340: Replace json.loads() with LLMResponseParser.safe_json_parse()")
        print("- Line 365: Replace json.loads() with LLMResponseParser.ensure_agent_response_is_json()")
    
    # This assertion will FAIL with current code (which is expected)
    assert len(violations) == 0, f"Found {len(violations)} SSOT violations using direct json methods"


def test_goals_triage_missing_imports():
    """
    Test that required SSOT imports are present.
    This test will FAIL with current implementation.
    """
    # Read the source file
    agent_file = Path(__file__).parent.parent / "app" / "agents" / "goals_triage_sub_agent.py"
    source_code = agent_file.read_text()
    
    required_imports = [
        ('LLMResponseParser', 'from netra_backend.app.core.serialization.unified_json_handler'),
        ('JSONErrorFixer', 'from netra_backend.app.core.serialization.unified_json_handler'),
        ('UnifiedJSONHandler', 'from netra_backend.app.core.serialization.unified_json_handler'),
    ]
    
    missing_imports = []
    for class_name, expected_import in required_imports:
        if class_name not in source_code:
            missing_imports.append(class_name)
    
    if missing_imports:
        print("\n=== MISSING REQUIRED IMPORTS ===")
        for imp in missing_imports:
            print(f"- {imp}")
        print("\nThese classes from unified_json_handler.py should be imported and used")
    
    assert len(missing_imports) == 0, f"Missing {len(missing_imports)} required SSOT imports"


def test_goals_triage_error_handling_violations():
    """
    Test for proper error handling patterns.
    """
    agent_file = Path(__file__).parent.parent / "app" / "agents" / "goals_triage_sub_agent.py"
    source_code = agent_file.read_text()
    
    # Check if unified error handler is imported
    has_error_handler = 'agent_error_handler' in source_code
    
    # Find basic exception handling that should use unified handler
    basic_except_pattern = re.compile(r'except\s+Exception\s+as\s+\w+:', re.MULTILINE)
    basic_excepts = list(basic_except_pattern.finditer(source_code))
    
    if not has_error_handler:
        print("\n=== ERROR HANDLING VIOLATIONS ===")
        print("- Missing import: agent_error_handler from unified_error_handler")
        print(f"- Found {len(basic_excepts)} basic exception handlers that should use unified patterns")
        
        # Show line numbers
        lines = source_code.split('\n')
        for match in basic_excepts[:3]:  # Show first 3
            line_num = source_code[:match.start()].count('\n') + 1
            print(f"  Line ~{line_num}: Basic exception handling found")
    
    assert has_error_handler, "Should use agent_error_handler for unified error handling"


if __name__ == "__main__":
    print("=" * 60)
    print("SSOT VIOLATION TESTS FOR GoalsTriageSubAgent")
    print("=" * 60)
    
    # Run each test
    tests = [
        test_goals_triage_json_violations,
        test_goals_triage_missing_imports,
        test_goals_triage_error_handling_violations
    ]
    
    failed_tests = []
    for test in tests:
        print(f"\nRunning {test.__name__}...")
        try:
            test()
            print(f"[PASSED] {test.__name__}")
        except AssertionError as e:
            print(f"[FAILED] {test.__name__}: {e}")
            failed_tests.append(test.__name__)
    
    print("\n" + "=" * 60)
    if failed_tests:
        print(f"EXPECTED: {len(failed_tests)} tests failed (violations detected)")
        print("These failures indicate SSOT violations that need to be fixed.")
    else:
        print("All tests passed - SSOT compliance achieved!")
    print("=" * 60)