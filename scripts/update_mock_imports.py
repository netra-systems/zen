#!/usr/bin/env python3
"""
Mock Import Update Script

Updates imports to use SSOT MockFactory while maintaining backward compatibility.
Critical for ensuring no test regressions during consolidation.
"""

import re
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent

class MockImportUpdater:
    """Updates mock imports to use SSOT patterns."""
    
    def __init__(self):
        self.import_mappings = {
            # Update these common patterns to use compatibility bridge first
            "from .mock_classes import MockAgent": "from test_framework.ssot.compatibility_bridge import MockAgent",
            "from mock_classes import MockAgent": "from test_framework.ssot.compatibility_bridge import MockAgent",
            "from .test_agent_service_mock_classes import MockAgent": "from test_framework.ssot.compatibility_bridge import MockAgent",
            
            # WebSocket imports
            "from .websocket_mocks import MockWebSocket": "from test_framework.ssot.compatibility_bridge import MockWebSocket",
            "from websocket_mocks import MockWebSocket": "from test_framework.ssot.compatibility_bridge import MockWebSocket",
            
            # Service imports
            "from .mock_services import MockLLMService": "from test_framework.ssot.compatibility_bridge import MockLLMService",
            "from mock_services import MockLLMService": "from test_framework.ssot.compatibility_bridge import MockLLMService",
        }
        
        # Files that should get direct factory usage (new approach)
        self.direct_factory_files = [
            "test_framework/tests/",
            "tests/unit/test_ssot_",
            "tests/integration/test_ssot_"
        ]
    
    def should_use_direct_factory(self, file_path: Path) -> bool:
        """Determine if file should use direct factory instead of compatibility."""
        path_str = str(file_path)
        return any(pattern in path_str for pattern in self.direct_factory_files)
    
    def update_file_imports(self, file_path: Path) -> bool:
        """Update mock imports in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            
            if self.should_use_direct_factory(file_path):
                content = self._apply_direct_factory_updates(content)
            else:
                content = self._apply_compatibility_updates(content)
                
            if content != original_content:
                # Backup original
                backup_path = file_path.with_suffix(f"{file_path.suffix}.mock_backup")
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                    
                # Write updated version
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                logger.info(f"Updated imports in {file_path.relative_to(PROJECT_ROOT)}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update {file_path}: {e}")
            return False
    
    def _apply_compatibility_updates(self, content: str) -> str:
        """Apply compatibility bridge updates."""
        updated_content = content
        
        # Add compatibility import if mock classes are used
        mock_classes_used = []
        for pattern in ["MockAgent", "MockWebSocket", "MockLLMService", "MockServiceManager", 
                       "MockOrchestrator", "MockWebSocketManager", "MockWebSocketConnection",
                       "MockAuthService", "MockAgentService"]:
            if pattern in content and f"class {pattern}" not in content:  # Used but not defined
                mock_classes_used.append(pattern)
        
        if mock_classes_used:
            # Add import at top after other imports
            import_line = f"from test_framework.ssot.compatibility_bridge import {', '.join(mock_classes_used)}"
            
            # Find a good place to insert the import
            lines = updated_content.split('\\n')
            insert_index = 0
            
            # Look for existing imports
            for i, line in enumerate(lines):
                if line.strip().startswith('from ') or line.strip().startswith('import '):
                    insert_index = i + 1
                elif line.strip() and not line.strip().startswith('#'):
                    break
            
            # Check if import already exists
            if import_line not in updated_content:
                lines.insert(insert_index, import_line)
                updated_content = '\\n'.join(lines)
        
        return updated_content
    
    def _apply_direct_factory_updates(self, content: str) -> str:
        """Apply direct MockFactory updates for modern test files."""
        updated_content = content
        
        # Replace mock instantiations with factory calls
        replacements = [
            (r'MockAgent\\([^)]*\\)', 'get_mock_factory().create_agent_mock()'),
            (r'MockWebSocket\\([^)]*\\)', 'get_mock_factory().create_websocket_connection_mock()'),
            (r'MockWebSocketManager\\([^)]*\\)', 'get_mock_factory().create_websocket_manager_mock()'),
            (r'MockLLMService\\([^)]*\\)', 'get_mock_factory().create_llm_client_mock()'),
            (r'MockServiceManager\\([^)]*\\)', 'get_mock_factory().create_service_manager_mock()'),
            (r'MockAuthService\\([^)]*\\)', 'get_mock_factory().create_auth_service_mock()'),
        ]
        
        for pattern, replacement in replacements:
            updated_content = re.sub(pattern, replacement, updated_content)
        
        # Add factory import if factory calls are used
        if 'get_mock_factory()' in updated_content:
            factory_import = "from test_framework.ssot.mocks import get_mock_factory"
            if factory_import not in updated_content:
                lines = updated_content.split('\\n')
                # Insert after other imports
                insert_index = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('from ') or line.strip().startswith('import '):
                        insert_index = i + 1
                    elif line.strip() and not line.strip().startswith('#'):
                        break
                
                lines.insert(insert_index, factory_import)
                updated_content = '\\n'.join(lines)
        
        return updated_content
    
    def update_critical_files(self) -> int:
        """Update imports in the most critical files first."""
        # Priority files to update first (high-impact, commonly used)
        critical_patterns = [
            "netra_backend/tests/test_agent_service_mock_classes.py",
            "test_framework/mocks/*.py",
            "tests/mission_critical/test_websocket_*.py",
            "netra_backend/tests/conftest.py"
        ]
        
        updated_count = 0
        
        for pattern in critical_patterns:
            for file_path in PROJECT_ROOT.rglob(pattern):
                if file_path.is_file() and file_path.suffix == '.py':
                    if self.update_file_imports(file_path):
                        updated_count += 1
        
        return updated_count


def main():
    """Main import update process."""
    print("Mock Import Update Process")
    print("=" * 40)
    
    updater = MockImportUpdater()
    
    # First update critical files
    print("Updating critical files...")
    critical_count = updater.update_critical_files()
    print(f"Updated {critical_count} critical files")
    
    print("\\nImport updates complete!")
    print("Next: Run test suite to verify compatibility")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    main()