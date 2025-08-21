"""Fix import statement indentation errors in test files."""

import ast
import re
from pathlib import Path

def fix_import_indents(file_path):
    """Fix malformed multi-line import statements."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match broken imports like:
        # from module import something
        #     something_else,
        #     another_thing
        # )
        pattern = r'(from\s+[\w\.]+\s+import\s+[\w\s,]+)\n(\s+[\w\s,]+\n)+\)'
        
        def fix_import(match):
            lines = match.group(0).split('\n')
            # Extract the base import line
            base_line = lines[0]
            # Extract imported items from subsequent lines
            items = []
            for line in lines[1:]:
                line = line.strip()
                if line and line != ')':
                    items.append(line.rstrip(','))
            
            # If we found items on subsequent lines, create proper import
            if items:
                all_imports = base_line.split('import')[1].strip().rstrip(',')
                if all_imports:
                    items.insert(0, all_imports)
                return f"{base_line.split('import')[0]}import (\n    " + ",\n    ".join(items) + "\n)"
            return match.group(0)
        
        # Apply the fix
        fixed_content = re.sub(pattern, fix_import, content)
        
        # Check if anything changed
        if fixed_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix import indents in all test files with syntax errors."""
    test_files_with_errors = [
        "tests/unified/e2e/test_data_crud_unified.py",
        "tests/unified/e2e/test_memory_leak_detection.py",
        "tests/e2e/websocket_resilience/test_websocket_security_audit.py",
        "tests/e2e/websocket_resilience/test_websocket_token_refresh_advanced.py",
        "tests/unified/e2e/test_thread_management_websocket.py",
        "tests/unified/e2e/test_agent_collaboration_real.py",
        "tests/unified/e2e/test_token_lifecycle.py",
        "tests/e2e/websocket_resilience/test_websocket_security_attacks.py",
        "tests/unified/e2e/test_websocket_resilience.py",
        "tests/unified/test_oauth_flow.py",
        "tests/e2e/websocket_resilience/test_websocket_token_refresh_flow.py",
        "tests/unified/e2e/test_websocket_message_format_validation.py",
        "tests/e2e/test_helpers/throughput_helpers.py",
        "tests/unified/e2e/test_websocket_event_completeness.py",
        "tests/unified/e2e/test_health_monitoring_recovery.py",
        "tests/unified/test_transaction_consistency.py",
        "tests/e2e/websocket_resilience/test_websocket_connection_concurrent.py",
        "tests/unified/e2e/test_cross_service_transaction.py",
        "tests/unified/e2e/test_agent_failure_websocket_recovery.py",
        "tests/unified/e2e/test_auth_websocket_recovery.py",
        "tests/unified/e2e/test_disaster_recovery.py",
        "tests/e2e/resource_isolation/test_infrastructure.py",
        "tests/unified/e2e/test_auth_token_expiry.py"
    ]
    
    fixed_count = 0
    for file_path in test_files_with_errors:
        full_path = Path(file_path)
        if full_path.exists():
            if fix_import_indents(full_path):
                print(f"Fixed: {file_path}")
                fixed_count += 1
        else:
            print(f"Not found: {file_path}")
    
    print(f"\nFixed {fixed_count} files")

if __name__ == "__main__":
    main()