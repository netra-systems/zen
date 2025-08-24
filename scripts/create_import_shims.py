#!/usr/bin/env python3
"""
Create shim modules for backward compatibility after WebSocket refactoring.
Maps old imports to new locations based on the consolidation done in commit 760dfcfb3.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Define module mappings based on refactoring history
MODULE_MAPPINGS = {
    # WebSocket consolidation - batch modules removed, functionality moved to core
    "netra_backend/app/websocket_core/unified.py": """
# Shim module for backward compatibility
# Functionality consolidated into websocket_core manager
from netra_backend.app.websocket_core.manager import *
from netra_backend.app.websocket_core.handlers import *
from netra_backend.app.websocket_core.types import *
""",
    
    "netra_backend/app/websocket_core/batch_message_core.py": """
# Shim module for backward compatibility
# Batch functionality integrated into main manager
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.websocket_core.handlers import handle_message
from netra_backend.app.websocket_core.types import MessageBatch, BatchConfig

# Legacy aliases
BatchMessageHandler = WebSocketManager
process_batch = handle_message
""",
    
    "netra_backend/app/websocket_core/rate_limiter.py": """
# Shim module for backward compatibility
# Rate limiting integrated into WebSocket auth
from netra_backend.app.websocket_core.auth import RateLimiter
from netra_backend.app.websocket_core.utils import check_rate_limit

__all__ = ['RateLimiter', 'check_rate_limit']
""",
    
    "netra_backend/app/websocket_core/enhanced_rate_limiter.py": """
# Shim module for backward compatibility
from netra_backend.app.websocket_core.auth import RateLimiter as EnhancedRateLimiter
from netra_backend.app.websocket_core.utils import check_rate_limit

__all__ = ['EnhancedRateLimiter', 'check_rate_limit']
""",
    
    "netra_backend/app/websocket_core/state_synchronization_manager.py": """
# Shim module for backward compatibility
from netra_backend.app.websocket_core.manager import WebSocketManager as StateSynchronizationManager
from netra_backend.app.websocket_core.manager import sync_state

__all__ = ['StateSynchronizationManager', 'sync_state']
""",
    
    "netra_backend/app/routes/websocket_unified.py": """
# Shim module for backward compatibility
# Unified routes consolidated into main websocket.py
from netra_backend.app.routes.websocket import *
""",
    
    "netra_backend/app/services/user_auth_service.py": """
# Shim module for backward compatibility
# User auth consolidated into auth_failover_service
from netra_backend.app.services.auth_failover_service import *
from netra_backend.app.core.user_service import UserService

# Legacy aliases
UserAuthService = UserService
authenticate_user = UserService.authenticate
validate_token = UserService.validate_token
""",
    
    # WebSocket directory shim (entire module removed)
    "netra_backend/app/websocket/__init__.py": """
# Shim module for backward compatibility
# WebSocket functionality moved to websocket_core
from netra_backend.app.websocket_core import *
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.websocket_core.handlers import handle_message
from netra_backend.app.websocket_core.types import *
""",
    
    # Test helper modules
    "netra_backend/tests/integration/base.py": """
# Shim module for test backward compatibility
from test_framework.fixtures import *
from test_framework.base import BaseIntegrationTest
from test_framework.utils import setup_test_environment

__all__ = ['BaseIntegrationTest', 'setup_test_environment']
""",
    
    "netra_backend/tests/test_route_fixtures.py": """
# Shim module for test fixtures
from test_framework.fixtures import *
from test_framework.fixtures.routes import *
""",
    
    "netra_backend/tests/integration/test_unified_message_flow.py": """
# Shim module for test helpers
from test_framework.fixtures.message_flow import *
from test_framework.utils.websocket import create_test_message
""",
}

def create_shim_module(filepath: str, content: str) -> bool:
    """Create a shim module with the given content."""
    try:
        # Create directory if needed
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Check if file already exists
        if os.path.exists(filepath):
            print(f"  [SKIP] File already exists, skipping: {filepath}")
            return False
            
        # Write the shim module
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content.strip() + '\n')
        
        print(f"  [OK] Created shim: {filepath}")
        return True
    except Exception as e:
        print(f"  [FAIL] Failed to create {filepath}: {e}")
        return False

def main():
    """Create all shim modules for backward compatibility."""
    print("Creating Import Shim Modules")
    print("=" * 60)
    print("This will create compatibility modules for the WebSocket refactoring")
    print()
    
    created = 0
    skipped = 0
    failed = 0
    
    for module_path, content in MODULE_MAPPINGS.items():
        if create_shim_module(module_path, content):
            created += 1
        elif os.path.exists(module_path):
            skipped += 1
        else:
            failed += 1
    
    print()
    print("Summary:")
    print(f"  Created: {created} shim modules")
    print(f"  Skipped: {skipped} (already exist)")
    print(f"  Failed:  {failed}")
    
    if created > 0:
        print()
        print("[SUCCESS] Shim modules created successfully!")
        print("Run tests to verify: python unified_test_runner.py --fast-fail")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())