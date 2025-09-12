#!/usr/bin/env python3
"""
Complete remaining mock cleanup for files missed in first pass
"""

import re
from pathlib import Path

def cleanup_remaining_mocks():
    """Clean up remaining mock references."""
    
    base_dir = Path('/Users/anthony/Documents/GitHub/netra-apex')
    
    # Files with remaining issues
    remaining_files = [
        "websocket_performance_standalone_test.py",
        "test_framework/websocket_helpers.py", 
        "test_framework/decorators.py",
        "tests/websocket/test_secure_websocket.py",
        "tests/mission_critical/test_websocket_reliability_focused.py",
        "tests/mission_critical/test_websocket_basic_events.py",
        "tests/mission_critical/test_websocket_subagent_events.py",
        "tests/e2e/real_services_manager.py",
        "tests/e2e/reconnection_test_helpers.py",
        "tests/e2e/test_quality_gate_response_validation.py",
        "tests/e2e/test_multi_agent_collaboration_response.py",
        "tests/unit/scripts/test_deploy_to_gcp.py",
        "tests/e2e/resilience/test_response_persistence_recovery.py",
        "netra_backend/tests/unified_system/test_websocket_state.py",
        "netra_backend/tests/unit/test_health_checkers_core.py",
        "netra_backend/tests/unit/test_subagent_logging.py",
        "netra_backend/tests/unit/test_websocket_memory_leaks.py",
        "netra_backend/tests/unit/test_mcp_service_core.py",
        "netra_backend/tests/config/test_unified_config_integration.py",
        "netra_backend/tests/integration/websocket_recovery_fixtures.py",
        "netra_backend/tests/integration/agent_pipeline_mocks.py",
        "netra_backend/tests/integration/test_free_to_paid_conversion.py",
        "netra_backend/tests/agents/test_data_sub_agent_core.py",
        "netra_backend/tests/e2e/test_websocket_integration_core.py",
        "netra_backend/tests/e2e/test_websocket_integration_fixtures.py",
        "netra_backend/tests/helpers/websocket_test_helpers.py",
        "netra_backend/tests/services/test_ws_connection_mocks.py",
        "netra_backend/tests/services/test_generation_service_comprehensive.py",
        "netra_backend/tests/unit/db/test_database_manager.py",
        "netra_backend/tests/unit/agents/data_sub_agent/test_clickhouse_client.py",
        "netra_backend/tests/integration/critical_paths/test_websocket_jwt_encoding.py",
        "netra_backend/tests/integration/critical_paths/test_high_performance_websocket_stress.py",
        "scripts/compliance/mock_justification_checker.py",
        "test_framework/mocks/websocket_mocks.py"
    ]
    
    cleaned_count = 0
    
    for file_rel in remaining_files:
        file_path = base_dir / file_rel
        
        if not file_path.exists():
            print(f"[U+23ED][U+FE0F]  Skipping {file_rel} - file doesn't exist")
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Remove @mock_justified decorators
            content = re.sub(r'@mock_justified\([^)]*\)\s*\n', '', content)
            
            # Comment out MockWebSocket class definitions
            content = re.sub(
                r'(class\s+MockWebSocket.*?(?=\n\n@|\nclass|\ndef|\nasync def|\Z))',
                r'# COMMENTED OUT: MockWebSocket class - using real WebSocket connections per CLAUDE.md "MOCKS = Abomination"\n# \1',
                content,
                flags=re.DOTALL
            )
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f" PASS:  Cleaned {file_rel}")
                cleaned_count += 1
            else:
                print(f"[U+23ED][U+FE0F]  No changes needed for {file_rel}")
                
        except Exception as e:
            print(f" FAIL:  Error processing {file_rel}: {e}")
            
    print(f"\n TARGET:  Cleaned {cleaned_count} additional files")

if __name__ == "__main__":
    cleanup_remaining_mocks()