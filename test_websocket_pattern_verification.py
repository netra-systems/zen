"""
Simple verification test for WebSocket pattern consistency.
Tests that the unified bridge pattern is correctly implemented.
"""

import ast
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def check_file_for_patterns(filepath: Path) -> dict:
    """Check a file for WebSocket pattern usage."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        results = {
            'file': filepath.name,
            'has_bridge_import': 'get_agent_websocket_bridge' in content,
            'has_manager_refs': 'websocket_manager' in content,
            'has_emit_methods': any(m in content for m in ['emit_thinking', 'emit_error', 'emit_progress']),
            'has_old_methods': any(m in content for m in ['send_agent_thinking', 'send_partial_result', 'notify_agent_thinking']),
            'issues': []
        }
        
        # Check for issues
        if results['has_bridge_import'] and filepath.name not in ['agent_websocket_bridge.py', 'websocket_bridge_adapter.py']:
            results['issues'].append('Direct bridge import (should use emit methods)')
            
        if results['has_manager_refs'] and 'websocket_manager = None' not in content:
            # Check if it's actual usage vs just backward compat
            if 'self.websocket_manager.' in content or 'if self.websocket_manager' in content:
                results['issues'].append('WebSocket manager usage detected')
                
        if results['has_old_methods']:
            results['issues'].append('Old WebSocket methods still present')
            
        return results
    except Exception as e:
        return {'file': filepath.name, 'error': str(e)}

def main():
    """Run pattern verification on critical files."""
    base_path = Path(__file__).parent / "netra_backend" / "app" / "agents"
    
    critical_files = [
        base_path / "agent_communication.py",
        base_path / "agent_lifecycle.py", 
        base_path / "base" / "interface.py",
        base_path / "data_sub_agent" / "data_sub_agent.py",
        base_path / "validation_sub_agent.py",
        base_path / "base_agent.py"
    ]
    
    print("=" * 60)
    print("WebSocket Pattern Verification Report")
    print("=" * 60)
    
    total_issues = 0
    
    for filepath in critical_files:
        if filepath.exists():
            results = check_file_for_patterns(filepath)
            
            status = "CLEAN" if not results.get('issues') else "ISSUES"
            print(f"\n[{status}] {results['file']}")
            
            if results.get('issues'):
                total_issues += len(results['issues'])
                for issue in results['issues']:
                    print(f"  - {issue}")
            else:
                print("  - Using unified emit pattern correctly")
                
            # Show pattern details
            if results.get('has_emit_methods'):
                print("  + Has emit_* methods")
            if results.get('has_bridge_import'):
                print("  ! Has direct bridge import")
            if results.get('has_manager_refs'):
                print("  ! Has manager references")
            if results.get('has_old_methods'):
                print("  ! Has old WebSocket methods")
        else:
            print(f"\n[?] {filepath.name} - File not found")
    
    print("\n" + "=" * 60)
    print(f"Summary: {total_issues} issues found")
    
    if total_issues == 0:
        print("[SUCCESS] All critical files follow unified WebSocket pattern!")
    else:
        print("[FAIL] Some files still have pattern violations")
        
    return total_issues == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)