#!/usr/bin/env python3
"""
Fix WebSocket imports across the codebase.

This script updates all references from ws_manager to websocket_core.
"""

import os
import re
from pathlib import Path

def main():
    """Remove ws_manager references except in historical/learning contexts."""
    base_path = Path('C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend')
    
    # Files that reference ws_manager (from grep results)
    files_to_check = [
        'tests/critical/test_websocket_circular_import_regression.py',
        'tests/websocket/test_websocket_regression_prevention.py',
        'tests/unit/test_websocket_connection_paradox_regression.py',
        'tests/services/test_ws_connection_performance.py',
        'tests/services/test_ws_connection_basic.py',
        'tests/services/test_ws_connection_mocks.py',
        'tests/integration/critical_paths/test_websocket_rate_limiting_per_client.py',
        'tests/integration/critical_paths/test_websocket_reconnection_state_recovery.py',
        'tests/integration/critical_paths/test_websocket_message_compression.py',
        'tests/integration/critical_paths/test_websocket_message_delivery_guarantee.py',
        'tests/integration/critical_paths/test_websocket_health_check.py',
        'tests/integration/critical_paths/test_websocket_heartbeat_monitoring.py',
        'tests/integration/critical_paths/test_websocket_connection_draining.py',
        'tests/integration/critical_paths/test_websocket_connection_pooling.py',
        'tests/integration/critical_paths/test_websocket_circuit_breaker.py',
        'tests/integration/critical_paths/test_websocket_binary_message_handling.py',
        'tests/integration/critical_paths/test_websocket_broadcast_performance.py',
        'tests/integration/test_websocket_redis_pubsub.py',
        'tests/critical/test_websocket_message_regression.py',
        'tests/e2e/conftest.py',
        'tests/e2e/first_time_user/real_critical_auth_helpers.py',
        'app/routes/utils/thread_title_generator.py',
        'app/core/degradation_strategies.py',
        'app/agents/synthetic_data_progress_tracker.py',
        'tests/integration/test_websocket_agent_integration.py',
        'tests/critical/test_websocket_agent_startup.py',
    ]
    
    for file_path in files_to_check:
        full_path = base_path / file_path
        if not full_path.exists():
            continue
            
        # Skip files that are about historical regressions/learnings
        if 'regression' in file_path or 'circular_import' in file_path:
            print(f"Skipping historical file: {file_path}")
            continue
            
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = content
            
            # Remove ws_manager imports
            content = re.sub(r'from netra_backend\.app\.ws_manager import .*\n', '', content)
            content = re.sub(r'from netra_backend\.app import ws_manager\n', '', content)
            content = re.sub(r'import netra_backend\.app\.ws_manager.*\n', '', content)
            
            # Replace ws_manager usage with websocket_core
            if 'ws_manager' in content:
                # Add websocket_core import if needed
                if 'from netra_backend.app.websocket_core import' not in content:
                    # Find where to add import
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if line.startswith('from netra_backend'):
                            lines.insert(i+1, 'from netra_backend.app.websocket_core import get_websocket_manager')
                            content = '\n'.join(lines)
                            break
                
                # Replace usage
                content = re.sub(r'ws_manager\.manager', 'get_websocket_manager()', content)
                content = re.sub(r'ws_manager\.get_manager\(\)', 'get_websocket_manager()', content)
                content = re.sub(r'ws_manager\b', 'websocket_manager', content)
            
            if content != original:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Updated: {file_path}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

if __name__ == '__main__':
    main()