#!/usr/bin/env python3
"""
Find the most critical WebSocket test files for Golden Path validation.
Focus on essential files first to get maximum impact.
"""

import ast
from pathlib import Path
from typing import List, Tuple

def find_golden_path_critical_files(root_dir: str) -> List[Path]:
    """Find the most critical test files for Golden Path validation."""
    root_path = Path(root_dir)
    
    # Golden Path Critical Files (must work for user login → AI responses)
    golden_path_files = [
        # Core WebSocket agent events (90% of platform value)
        "tests/mission_critical/test_websocket_agent_events_suite.py",
        
        # E2E WebSocket authentication flow
        "tests/e2e/test_websocket_authentication.py",
        
        # Agent orchestration with WebSocket events
        "tests/e2e/test_agent_orchestration_real_llm.py",
        
        # WebSocket connection handling
        "tests/e2e/test_websocket_real_connection.py",
        
        # Integration tests for WebSocket bridge
        "tests/integration/test_websocket_bridge_startup_integration.py",
    ]
    
    critical_files = []
    for file_path_str in golden_path_files:
        file_path = root_path / file_path_str
        if file_path.exists():
            critical_files.append(file_path)
        else:
            print(f"WARNING: Critical file not found: {file_path_str}")
    
    return critical_files

def check_syntax_error(file_path: Path) -> Tuple[bool, str]:
    """Check if a file has syntax errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse the file
        ast.parse(content, filename=str(file_path))
        return False, ""
    
    except SyntaxError as e:
        error_msg = f"Line {e.lineno}: {e.msg}"
        if e.text:
            error_msg += f" - '{e.text.strip()}'"
        return True, error_msg
    
    except Exception as e:
        return True, f"Unexpected error: {e}"

def main():
    """Check Golden Path critical files."""
    print("🎯 GOLDEN PATH CRITICAL FILES SYNTAX CHECK")
    print("=" * 60)
    
    critical_files = find_golden_path_critical_files("/Users/anthony/Desktop/netra-apex")
    print(f"Found {len(critical_files)} Golden Path critical files")
    
    files_with_errors = []
    files_clean = []
    
    for file_path in critical_files:
        has_error, error_msg = check_syntax_error(file_path)
        
        rel_path = str(file_path).replace("/Users/anthony/Desktop/netra-apex/", "")
        
        if has_error:
            files_with_errors.append((file_path, error_msg))
            print(f"❌ {rel_path}")
            print(f"   Error: {error_msg}")
        else:
            files_clean.append(file_path)
            print(f"✅ {rel_path}")
    
    print(f"\n📊 GOLDEN PATH RESULTS:")
    print(f"  Total critical files: {len(critical_files)}")
    print(f"  Files with syntax errors: {len(files_with_errors)}")
    print(f"  Clean files: {len(files_clean)}")
    
    if files_with_errors:
        print(f"\n🔥 CRITICAL FILES TO FIX IMMEDIATELY:")
        for i, (file_path, error) in enumerate(files_with_errors):
            rel_path = str(file_path).replace("/Users/anthony/Desktop/netra-apex/", "")
            print(f"{i+1}. {rel_path}")
            print(f"   {error}")
    
    # Return status for scripting
    return len(files_with_errors) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)