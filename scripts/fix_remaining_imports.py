"""Fix remaining import statement indentation errors."""

import re
from pathlib import Path

def fix_import_indents(file_path):
    """Fix malformed multi-line import statements."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match broken imports
        pattern = r'(from\s+[\w\.]+\s+import\s+[\w\s,]+)\n(\s+[\w\s,]+\n)+\)'
        
        def fix_import(match):
            lines = match.group(0).split('\n')
            base_line = lines[0]
            items = []
            for line in lines[1:]:
                line = line.strip()
                if line and line != ')':
                    items.append(line.rstrip(','))
            
            if items:
                all_imports = base_line.split('import')[1].strip().rstrip(',')
                if all_imports:
                    items.insert(0, all_imports)
                return f"{base_line.split('import')[0]}import (\n    " + ",\n    ".join(items) + "\n)"
            return match.group(0)
        
        fixed_content = re.sub(pattern, fix_import, content)
        
        if fixed_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix import indents in remaining test files with syntax errors."""
    test_files_with_errors = [
        "tests/unified/e2e/test_quota_management.py",
        "tests/unified/e2e/test_service_failure_recovery.py",
        "tests/unified/e2e/test_database_consistency.py",
        "tests/unified/e2e/test_auth_websocket_connection.py",
        "tests/unified/e2e/test_export_pipeline.py",
        "tests/unified/e2e/file_upload_pipeline_test_suite.py",
        "tests/unified/test_load_performance.py",
        "tests/unified/e2e/test_websocket_message_guarantees.py",
        "tests/unified/e2e/test_error_cascade_prevention.py",
        "tests/unified/e2e/test_cost_tracking_accuracy.py",
        "tests/unified/e2e/test_token_expiry_refresh.py",
        "tests/unified/e2e/test_auth_websocket_performance.py",
        "tests/unified/e2e/test_real_rate_limiting.py",
        "tests/unified/e2e/test_agent_orchestration_real_llm.py",
        "tests/unified/e2e/test_session_state_synchronization.py",
        "tests/unified/e2e/test_workspace_isolation.py",
        "tests/unified/e2e/test_agent_billing_flow.py",
        "tests/unified/e2e/test_websocket_guarantees.py",
        "tests/unified/e2e/test_session_persistence.py",
        "tests/unified/e2e/test_ai_supply_chain_failover.py",
        "tests/unified/health_service_checker.py",
        "tests/unified/oauth_flow_manager.py",
        "tests/unified/e2e/concurrent_user_simulators.py",
        "tests/unified/e2e/onboarding_flow_executor.py",
        "tests/unified/e2e/session_persistence_manager.py",
        "tests/unified/e2e/websocket_message_guarantee_helpers.py",
        "tests/unified/e2e/helpers/service_independence_helpers.py",
        "tests/unified/e2e/helpers/error_propagation/__init__.py",
        "tests/unified/e2e/helpers/service_independence/__init__.py",
        "tests/e2e/websocket_resilience/test_websocket_security_audit.py",
        "tests/e2e/websocket_resilience/test_websocket_token_refresh_advanced.py",
        "tests/e2e/websocket_resilience/test_websocket_security_attacks.py",
        "tests/e2e/websocket_resilience/test_websocket_token_refresh_flow.py",
        "tests/e2e/test_helpers/throughput_helpers.py",
        "tests/e2e/websocket_resilience/test_websocket_connection_concurrent.py",
        "tests/e2e/resource_isolation/test_infrastructure.py"
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