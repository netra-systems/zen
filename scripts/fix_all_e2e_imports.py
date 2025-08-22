#!/usr/bin/env python3
"""Fix all E2E test import issues systematically."""

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
    """Main function to fix all import issues."""
    
    root = Path(".")
    
    # Define replacements
    replacements = [
        # Fix ModernConnectionManager imports
        (r'from netra_backend\.app\.websocket\.connection_manager import \(\s*ModernConnectionManager\s*(?:,|\))',
         'from netra_backend.app.websocket.connection_manager import (\n    ConnectionManager'),
        (r'from netra_backend\.app\.websocket\.connection_manager import ModernConnectionManager',
         'from netra_backend.app.websocket.connection_manager import ConnectionManager'),
        (r'ModernConnectionManager as ConnectionManager',
         'ConnectionManager'),
        (r'from netra_backend\.app\.websocket\.connection import \(\s*ModernConnectionManager',
         'from netra_backend.app.websocket.connection_manager import (\n    ConnectionManager'),
        
        # Fix ConnectionManager (double Modern)
        (r'ConnectionManager', 'ConnectionManager'),
        
        # Fix test harness imports
        (r'from tests\.test_harness import', 'from tests.e2e.unified_e2e_harness import'),
        (r'from tests\.harness_complete import', 'from tests.e2e.harness_complete import'),
        
        # Fix network failure simulator
        (r'from tests\.network_failure_simulator import', 'from tests.e2e.network_failure_simulator import'),
        
        # Fix real client imports
        (r'from tests\.real_websocket_client import', 'from tests.e2e.real_websocket_client import'),
        (r'from tests\.real_client_types import', 'from tests.e2e.real_client_types import'),
        (r'from tests\.real_http_client import', 'from tests.e2e.real_http_client import'),
        
        # Fix service manager imports
        (r'from tests\.service_manager import', 'from tests.e2e.service_manager import'),
        (r'from tests\.real_services_manager import', 'from tests.e2e.real_services_manager import'),
        
        # Fix other test imports that should be under e2e
        (r'from tests\.oauth_flow_manager import', 'from tests.e2e.oauth_flow_manager import'),
        (r'from tests\.config import', 'from tests.e2e.config import'),
        (r'from tests\.test_utils import', 'from tests.e2e.test_utils import'),
        (r'from tests\.test_data_factory import', 'from tests.e2e.data_factory import'),
        
        # Fix agent startup imports
        (r'from tests\.agent_startup_helpers import', 'from tests.e2e.agent_startup_helpers import'),
        (r'from tests\.agent_startup_validators import', 'from tests.e2e.agent_startup_validators import'),
        (r'from tests\.agent_orchestration_fixtures import', 'from tests.e2e.agent_orchestration_fixtures import'),
        
        # Fix relative imports in integration tests
        (r'from tests\.e2e\.integration\.helpers import', 'from tests.e2e.helpers import'),
        (r'from tests\.e2e\.integration\.fixtures import', 'from tests.e2e.fixtures import'),
        
        # Fix helpers path
        (r'from tests\.e2e\.helpers\.service_orchestrator import', 'from tests.e2e.service_orchestrator import'),
        
        # Fix conftest import
        (r'from tests\.e2e\.conftest import', 'from conftest import'),
        
        # Fix double path components
        (r'from tests\.e2e\.integration\.(\w+)_helpers import', r'from tests.e2e.\1_helpers import'),
        (r'from tests\.e2e\.integration\.(\w+)_core import', r'from tests.e2e.\1_core import'),
        (r'from tests\.e2e\.integration\.(\w+)_manager import', r'from tests.e2e.\1_manager import'),
        (r'from tests\.e2e\.integration\.(\w+)_fixtures import', r'from tests.e2e.\1_fixtures import'),
        
        # Fix websocket resilience imports
        (r'from tests\.e2e\.websocket_resilience\.test_\d+_(\w+)_core import',
         r'from tests.e2e.websocket_resilience.\1 import'),
         
        # Fix auth flow manager path
        (r'from tests\.e2e\.integration\.auth_flow_manager import', 'from tests.e2e.auth_flow_manager import'),
        
        # Fix TestClient import
        (r"from tests\.e2e import TestClient", "from tests.e2e.real_client_types import TestClient"),
        
        # Fix config imports
        (r"from tests\.e2e\.config import TestEnvironmentConfig", 
         "from tests.e2e.test_environment_config import TestEnvironmentConfig"),
    ]
    
    # Process all Python files in tests/e2e
    test_files = list(Path("tests/e2e").rglob("*.py"))
    
    fixed_count = 0
    for file_path in test_files:
        if fix_file(file_path, replacements):
            fixed_count += 1
    
    # Also fix files that import from netra_backend
    backend_files = list(Path("netra_backend").rglob("*.py"))
    for file_path in backend_files:
        if fix_file(file_path, replacements[:6]):  # Only fix ConnectionManager issues
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")
    
    # Now fix syntax errors (files with invalid import statements)
    syntax_fix_files = [
        "tests/e2e/integration/test_agent_orchestration_real_llm.py",
        "tests/e2e/integration/test_auth_jwt_refresh.py", 
        "tests/e2e/integration/test_auth_jwt_security.py",
    ]
    
    for file_path in syntax_fix_files:
        fix_syntax_error(Path(file_path))

def fix_syntax_error(file_path: Path):
    """Fix syntax errors in import statements."""
    if not file_path.exists():
        return
        
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        fixed_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Check for incomplete docstring before import
            if i > 0 and lines[i-1].strip().endswith('"""') and line.startswith('from '):
                # This is fine
                fixed_lines.append(line)
            elif i > 0 and not lines[i-1].strip() and line.startswith('from '):
                # This is also fine
                fixed_lines.append(line)
            elif i > 0 and lines[i-1].strip() and not lines[i-1].strip().endswith(('"""', "'''", ')', '}', ']')) and line.startswith('from '):
                # Previous line might be incomplete
                if not lines[i-1].strip().endswith(':'):
                    # Add proper line ending
                    fixed_lines[-1] = fixed_lines[-1] + '"""' if '"""' in fixed_lines[-1] else fixed_lines[-1]
                    fixed_lines.append('')
                fixed_lines.append(line)
            else:
                fixed_lines.append(line)
            i += 1
        
        file_path.write_text('\n'.join(fixed_lines), encoding='utf-8')
        print(f"Fixed syntax in: {file_path}")
    except Exception as e:
        print(f"Error fixing syntax in {file_path}: {e}")

if __name__ == "__main__":
    main()