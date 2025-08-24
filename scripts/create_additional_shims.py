#!/usr/bin/env python3
"""
Create additional shim modules for remaining import errors.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Additional module mappings for remaining errors
ADDITIONAL_MAPPINGS = {
    # Database and core modules
    "netra_backend/app/clickhouse/__init__.py": """
# Shim module for backward compatibility
from netra_backend.app.db.clickhouse import *
""",
    
    "netra_backend/app/core/database.py": """
# Shim module for backward compatibility
from netra_backend.app.db.database_manager import *
from netra_backend.app.db.postgres_async import AsyncDatabase
""",
    
    "netra_backend/app/db/models.py": """
# Shim module for backward compatibility
from netra_backend.app.models import *
""",
    
    "netra_backend/app/core/transaction_core.py": """
# Shim module for backward compatibility
from netra_backend.app.db.transaction_manager import *
""",
    
    "netra_backend/app/database/migration_manager.py": """
# Shim module for backward compatibility
from netra_backend.app.db.migrations import *
""",
    
    # Services
    "netra_backend/app/services/file_storage_service.py": """
# Shim module for backward compatibility
from netra_backend.app.services.storage import FileStorageService
""",
    
    "netra_backend/app/services/external_service_client.py": """
# Shim module for backward compatibility
from netra_backend.app.services.http_client import ExternalServiceClient
""",
    
    "netra_backend/app/services/tenant_service.py": """
# Shim module for backward compatibility
from netra_backend.app.services.multi_tenant import TenantService
""",
    
    # Monitoring
    "netra_backend/app/monitoring/prometheus_exporter.py": """
# Shim module for backward compatibility
from netra_backend.app.monitoring.metrics_exporter import PrometheusExporter
""",
    
    # WebSocket additional modules
    "netra_backend/app/websocket_core/reconnection_types.py": """
# Shim module for backward compatibility
from netra_backend.app.websocket_core.types import ReconnectionConfig, ReconnectionState
""",
    
    "netra_backend/app/websocket_core/batch_message_handler.py": """
# Shim module for backward compatibility
from netra_backend.app.websocket_core.handlers import BatchMessageHandler
""",
    
    "netra_backend/app/websocket_core/connection_info.py": """
# Shim module for backward compatibility
from netra_backend.app.websocket_core.types import ConnectionInfo
""",
    
    "netra_backend/app/websocket_core/error_recovery_handler.py": """
# Shim module for backward compatibility
from netra_backend.app.websocket_core.recovery import ErrorRecoveryHandler
""",
    
    "netra_backend/app/websocket_core/connection_executor.py": """
# Shim module for backward compatibility
from netra_backend.app.websocket_core.manager import ConnectionExecutor
""",
    
    "netra_backend/app/websocket_core_info.py": """
# Shim module for backward compatibility
from netra_backend.app.websocket_core.types import *
""",
    
    "netra_backend/app/websocket_core/broadcast_core.py": """
# Shim module for backward compatibility
from netra_backend.app.websocket_core.manager import broadcast_message
""",
    
    "netra_backend/app/websocket_core/state_synchronizer.py": """
# Shim module for backward compatibility
from netra_backend.app.websocket_core.manager import StateSynchronizer
""",
    
    "netra_backend/app/websocket_core/performance_monitor_core.py": """
# Shim module for backward compatibility
from netra_backend.app.monitoring.metrics_collector import PerformanceMonitor
""",
    
    "netra_backend/app/websocket_core/compression.py": """
# Shim module for backward compatibility
from netra_backend.app.websocket_core.utils import compress, decompress
""",
    
    "netra_backend/app/websocket_core/broadcast.py": """
# Shim module for backward compatibility
from netra_backend.app.websocket_core.manager import broadcast_message, BroadcastManager
""",
    
    "netra_backend/app/error_aggregator.py": """
# Shim module for backward compatibility
from netra_backend.app.core.error_handler import ErrorAggregator
""",
    
    # Test helpers and fixtures
    "netra_backend/tests/integration/integration.py": """
# Shim module for test backward compatibility
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures import *
""",
    
    "netra_backend/tests/integration/deployment_config_fixtures.py": """
# Shim module for test fixtures
from test_framework.fixtures.deployment import *
""",
    
    "netra_backend/tests/integration/sso_saml_components.py": """
# Shim module for SSO test components
from test_framework.fixtures.auth import SSOTestComponents
""",
    
    "netra_backend/tests/integration/test_ws_connection_mocks.py": """
# Shim module for WebSocket test mocks
from test_framework.mocks.websocket import *
""",
    
    "netra_backend/tests/llm_mocks.py": """
# Shim module for LLM test mocks
from test_framework.mocks.llm import *
""",
    
    "netra_backend/tests/test_performance_batching.py": """
# Shim module for performance test helpers
from test_framework.performance import BatchingTestHelper
""",
    
    "netra_backend/tests/test_utilities.py": """
# Shim module for test utilities
from test_framework.utils import *
""",
    
    "netra_backend/tests/test_config_core.py": """
# Shim module for config test helpers
from test_framework.fixtures.config import *
""",
    
    "netra_backend/tests/test_health_monitor_adaptive.py": """
# Shim module for health monitor tests
from test_framework.fixtures.health import AdaptiveHealthMonitor
""",
    
    "netra_backend/tests/test_compression_auth.py": """
# Shim module for compression auth tests
from test_framework.fixtures.compression import CompressionAuthTestHelper
""",
    
    "netra_backend/tests/test_websocket_bidirectional_types.py": """
# Shim module for WebSocket type tests
from test_framework.fixtures.websocket_types import BidirectionalTypeTest
""",
    
    "netra_backend/tests/datetime_string_test_helpers.py": """
# Shim module for datetime test helpers
from test_framework.utils.datetime import *
""",
    
    "netra_backend/tests/json_file_crypto_test_helpers.py": """
# Shim module for crypto test helpers
from test_framework.utils.crypto import *
""",
    
    "netra_backend/tests/network_pagination_test_helpers.py": """
# Shim module for pagination test helpers
from test_framework.utils.pagination import *
""",
    
    "netra_backend/tests/debug_migration_test_helpers.py": """
# Shim module for migration test helpers
from test_framework.utils.migration import *
""",
    
    # Framework modules
    "test_framework/real_services_test_fixtures.py": """
# Shim module for real services test fixtures
from test_framework.fixtures.real_services import *
""",
    
    # Global imports (for tests in /tests directory)
    "test_unified_first_time_user.py": """
# Shim module for first time user tests
from test_framework.fixtures.user_onboarding import FirstTimeUserTestCase
""",
    
    "netra_backend/app/models/message.py": """
# Shim module for message models
from netra_backend.app.models import Message, MessageType
""",
    
    # Special cases
    "netra_mcp/__init__.py": """
# Shim module for MCP integration
from netra_backend.app.services.mcp_integration import *
""",
    
    "background_jobs/__init__.py": """
# Shim module for background jobs
from netra_backend.app.services.background_task_manager import *
""",
    
    "caching/__init__.py": """
# Shim module for caching
from netra_backend.app.services.cache import *
""",
    
    "payments/__init__.py": """
# Shim module for payments
from netra_backend.app.services.billing import *
""",
    
    "discovery/__init__.py": """
# Shim module for service discovery
from netra_backend.app.services.discovery import *
""",
    
    "tracing/__init__.py": """
# Shim module for tracing
from netra_backend.app.monitoring.tracing import *
""",
    
    # Dev launcher modules
    "dev_launcher/secret_loader.py": """
# Shim module for secret loading - functionality moved to isolated_environment
from dev_launcher.isolated_environment import load_secrets, SecretLoader
""",
}

def create_shim_module(filepath: str, content: str) -> bool:
    """Create a shim module with the given content."""
    try:
        # Create directory if needed
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Check if file already exists
        if os.path.exists(filepath):
            print(f"  [SKIP] File already exists: {filepath}")
            return False
            
        # Write the shim module
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content.strip() + '\n')
        
        print(f"  [OK] Created: {filepath}")
        return True
    except Exception as e:
        print(f"  [FAIL] Failed to create {filepath}: {e}")
        return False

def main():
    """Create additional shim modules."""
    print("Creating Additional Import Shim Modules")
    print("=" * 60)
    print()
    
    created = 0
    skipped = 0
    failed = 0
    
    for module_path, content in ADDITIONAL_MAPPINGS.items():
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
        print("[SUCCESS] Additional shim modules created!")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())