#!/usr/bin/env python3
"""Fix remaining E2E test import issues."""

import os
import re
from pathlib import Path
from typing import List, Tuple

def fix_file(file_path: Path, replacements: List[Tuple[str, str]]) -> bool:
    """Fix imports in a single file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        for old, new in replacements:
            content = re.sub(old, new, content, flags=re.MULTILINE)
        
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            print(f"Fixed: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Main function to fix remaining import issues."""
    
    root = Path(".")
    
    # Define replacements for remaining issues
    replacements = [
        # Fix supervisor agent imports
        (r'from netra_backend\.app\.agents\.supervisor\.supervisor_agent import SupervisorAgent',
         'from netra_backend.app.agents.supervisor_ssot import SupervisorAgent'),
        (r'from netra_backend\.app\.agents\.supervisor import SupervisorAgent',
         'from netra_backend.app.agents.supervisor_ssot import SupervisorAgent'),
         
        # Fix unified harness imports
        (r'from tests\.e2e\.unified_e2e_harness import UnifiedTestHarness',
         'from tests.e2e.harness_complete import UnifiedTestHarness'),
        
        # Fix data factory imports
        (r'from tests\.e2e\.data_factory import', 'from tests.e2e.test_data_factory import'),
        
        # Fix real services manager imports
        (r'from tests\.e2e\.real_services_manager import', 'from tests.e2e.service_manager import'),
        
        # Fix conftest relative imports in test files
        (r'^from conftest import', 'from tests.conftest import'),
        
        # Fix missing test utilities
        (r'from tests\.e2e\.test_utils import', 'from tests.e2e.test_helpers import'),
        
        # Fix agent conversation helpers
        (r'from netra_backend\.agent_conversation_helpers import',
         'from tests.e2e.agent_conversation_helpers import'),
         
        # Fix example message handler
        (r'from netra_backend\.app\.example_message_handler import',
         'from netra_backend.app.websocket.message_handler import'),
         
        # Fix PerformanceMetric import
        (r"from netra_backend\.app\.monitoring\.models import.*PerformanceMetric",
         "from netra_backend.app.monitoring.models import MetricData as PerformanceMetric"),
         
        # Fix search filter imports
        (r'from netra_backend\.app\.utils\.search_filter import',
         'from netra_backend.app.services.search.search_filter import'),
         
        # Fix quality imports
        (r'from netra_backend\.app\.quality import',
         'from netra_backend.app.services.quality import'),
         
        # Fix test factories
        (r'from netra_backend\.tests\.factories import',
         'from tests.factories import'),
    ]
    
    # Process all Python files in tests/e2e
    test_files = list(Path("tests/e2e").rglob("*.py"))
    
    fixed_count = 0
    for file_path in test_files:
        if fix_file(file_path, replacements):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")
    
    # Create missing helper files if they don't exist
    create_missing_helpers()

def create_missing_helpers():
    """Create any missing helper files."""
    helpers_to_create = [
        ("tests/e2e/test_helpers.py", """\"\"\"Test helpers for E2E tests.\"\"\"

from typing import Any, Dict, List
import asyncio
from unittest.mock import MagicMock

def create_mock_response(status: int = 200, json_data: Dict = None):
    \"\"\"Create a mock HTTP response.\"\"\"
    response = MagicMock()
    response.status_code = status
    response.json.return_value = json_data or {}
    return response

async def wait_for_condition(condition, timeout: float = 5.0):
    \"\"\"Wait for a condition to become true.\"\"\"
    start = asyncio.get_event_loop().time()
    while not condition():
        if asyncio.get_event_loop().time() - start > timeout:
            raise TimeoutError("Condition not met within timeout")
        await asyncio.sleep(0.1)
"""),
        ("tests/e2e/test_data_factory.py", """\"\"\"Test data factory for E2E tests.\"\"\"

from typing import Dict, Any
import uuid
from datetime import datetime, timezone

class TestDataFactory:
    \"\"\"Factory for creating test data.\"\"\"
    
    @staticmethod
    def create_user(email: str = None, **kwargs) -> Dict[str, Any]:
        \"\"\"Create test user data.\"\"\"
        return {
            "id": str(uuid.uuid4()),
            "email": email or f"test_{uuid.uuid4().hex[:8]}@example.com",
            "created_at": datetime.now(timezone.utc).isoformat(),
            **kwargs
        }
    
    @staticmethod
    def create_thread(**kwargs) -> Dict[str, Any]:
        \"\"\"Create test thread data.\"\"\"
        return {
            "id": str(uuid.uuid4()),
            "name": f"Thread {uuid.uuid4().hex[:8]}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            **kwargs
        }
    
    @staticmethod
    def create_message(content: str = None, **kwargs) -> Dict[str, Any]:
        \"\"\"Create test message data.\"\"\"
        return {
            "id": str(uuid.uuid4()),
            "content": content or "Test message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs
        }
"""),
        ("tests/factories.py", """\"\"\"Test factories for unit tests.\"\"\"

from tests.e2e.test_data_factory import TestDataFactory

# Re-export for compatibility
__all__ = ['TestDataFactory']
"""),
    ]
    
    for file_path, content in helpers_to_create:
        path = Path(file_path)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            print(f"Created: {file_path}")

if __name__ == "__main__":
    main()