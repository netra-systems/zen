#!/usr/bin/env python3
"""
E2E Test Import Fixer

Automatically fixes imports in all moved test files after the test directory reorganization.
Updates imports to reflect the new test structure under tests/e2e/.

Business Value Justification (BVJ):
- Segment: Platform/Internal (Development velocity protection)
- Business Goal: Restore broken imports after test reorganization
- Value Impact: Enables test execution after directory restructuring
- Strategic Impact: Prevents development velocity loss due to import failures

This script:
1. Scans test files in tests/e2e/ subdirectories
2. Updates imports that reference old paths
3. Fixes helper imports to use new organized structure
4. Reports all changes made
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class ImportFixer:
    """Fixes imports in moved test files."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.changes_made = []
        self.files_processed = 0
        
        # Define import mappings
        self.import_mappings = {
            # Old unified paths to new paths
            r'from tests\.unified\.e2e\.helpers': 'from tests.e2e.helpers',
            r'from tests\.unified\.e2e\.fixtures': 'from tests.e2e.fixtures',
            
            # Old backend paths to new paths
            r'from netra_backend\.tests\.e2e\.helpers': 'from tests.e2e.helpers',
            r'from netra_backend\.tests\.e2e\.fixtures': 'from tests.e2e.fixtures',
            r'from netra_backend\.tests\.e2e\.data': 'from tests.e2e.data',
            r'from netra_backend\.tests\.e2e\.validators': 'from tests.e2e.validators',
            r'from netra_backend\.tests\.e2e\.infrastructure': 'from tests.e2e.infrastructure',
            
            # Legacy test_utils path
            r'from netra_backend\.tests\.test_utils': 'from tests.test_utils',
            
            # Fix missing module imports - map them to their new locations
            r'from tests\.jwt_token_helpers': 'from tests.e2e.jwt_token_helpers',
            r'from tests\.oauth_test_providers': 'from tests.e2e.oauth_test_providers', 
            r'from tests\.config': 'from tests.e2e.config',
            r'from tests\.e2e\.auth_flow_testers': 'from tests.e2e.auth_flow_testers',
            
            # Fix imports referencing old integration paths for moved files
            r'from tests\.e2e\.integration\.account_deletion_flow_manager': 'from tests.e2e.account_deletion_flow_manager',
            r'from tests\.e2e\.integration\.agent_conversation_helpers': 'from tests.e2e.agent_conversation_helpers',
            r'from tests\.e2e\.integration\.auth_flow_manager': 'from tests.e2e.integration.auth_flow_manager',
            r'from tests\.e2e\.integration\.onboarding_flow_executor': 'from tests.e2e.onboarding_flow_executor',
            
            # Fix thread_test_fixtures_core to point to fixtures/core
            r'from tests\.e2e\.integration\.thread_test_fixtures_core': 'from tests.e2e.fixtures.core.thread_test_fixtures_core',
            r'from tests\.e2e\.thread_test_fixtures_core': 'from tests.e2e.fixtures.core.thread_test_fixtures_core',
            
            # Fix high_volume_data import to point to fixtures
            r'from tests\.e2e\.high_volume_data': 'from tests.e2e.fixtures.high_volume_data',
            
            # Fix performance_base import to point to test_helpers
            r'from tests\.e2e\.performance_base': 'from tests.e2e.test_helpers.performance_base',
            
            # Fix relative helper imports that should be absolute
            r'^from helpers\.': 'from tests.e2e.helpers.',
            
            # Fix patch statements with old paths
            r'tests\.unified\.e2e\.': 'tests.e2e.',
            r'netra_backend\.tests\.e2e\.': 'tests.e2e.',
        }
        
        # Import statement patterns for common import styles
        self.import_statement_mappings = {
            # Standard import statements
            r'import tests\.jwt_token_helpers': 'import tests.e2e.jwt_token_helpers',
            r'import tests\.oauth_test_providers': 'import tests.e2e.oauth_test_providers',
            r'import tests\.config': 'import tests.e2e.config',
            r'import tests\.e2e\.auth_flow_testers': 'import tests.e2e.auth_flow_testers',
            
            # From import with specific items
            r'from tests\.jwt_token_helpers import': 'from tests.e2e.jwt_token_helpers import',
            r'from tests\.oauth_test_providers import': 'from tests.e2e.oauth_test_providers import',
            r'from tests\.config import': 'from tests.e2e.config import',
        }
        
        # Specific helper module mappings based on new organization
        self.helper_mappings = {
            'from tests.e2e.helpers.user_journey_helpers': 'from tests.e2e.helpers.journey.user_journey_helpers',
            'from tests.e2e.helpers.new_user_journey_helpers': 'from tests.e2e.helpers.journey.new_user_journey_helpers',
            'from tests.e2e.helpers.real_service_journey_helpers': 'from tests.e2e.helpers.journey.real_service_journey_helpers',
            'from tests.e2e.helpers.journey_validation_helpers': 'from tests.e2e.helpers.journey.journey_validation_helpers',
            'from tests.e2e.helpers.oauth_journey_helpers': 'from tests.e2e.helpers.auth.oauth_journey_helpers',
            'from tests.e2e.helpers.chat_helpers': 'from tests.e2e.helpers.core.chat_helpers',
            'from tests.e2e.helpers.unified_flow_helpers': 'from tests.e2e.helpers.core.unified_flow_helpers',
            'from tests.e2e.helpers.websocket_test_helpers': 'from tests.e2e.helpers.websocket.websocket_test_helpers',
            'from tests.e2e.helpers.database_sync_helpers': 'from tests.e2e.helpers.database.database_sync_helpers',
        }
    
    def scan_test_directories(self) -> List[Path]:
        """Scan for Python test files in the reorganized directories."""
        test_dirs = [
            self.project_root / "tests" / "e2e" / "journeys",
            self.project_root / "tests" / "e2e" / "integration", 
            self.project_root / "tests" / "e2e" / "performance",
            self.project_root / "tests" / "e2e" / "resilience",
            # Also include the root e2e directory for any remaining files
            self.project_root / "tests" / "e2e",
        ]
        
        python_files = []
        for test_dir in test_dirs:
            if test_dir.exists():
                if test_dir.name == "e2e":
                    # For the root e2e directory, only get direct .py files
                    python_files.extend(test_dir.glob("*.py"))
                else:
                    # For subdirectories, get all .py files recursively
                    python_files.extend(test_dir.glob("**/*.py"))
        
        return python_files
    
    def fix_imports_in_file(self, file_path: Path) -> bool:
        """Fix imports in a single file. Returns True if changes were made."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            lines = content.split('\n')
            modified_lines = []
            changes_in_file = []
            
            for line_num, line in enumerate(lines, 1):
                original_line = line
                modified_line = line
                
                # Apply general import mappings
                for old_pattern, new_replacement in self.import_mappings.items():
                    if re.search(old_pattern, modified_line):
                        new_line = re.sub(old_pattern, new_replacement, modified_line)
                        if new_line != modified_line:
                            changes_in_file.append(f"  Line {line_num}: {modified_line.strip()} -> {new_line.strip()}")
                            modified_line = new_line
                
                # Apply import statement mappings
                for old_pattern, new_replacement in self.import_statement_mappings.items():
                    if re.search(old_pattern, modified_line):
                        new_line = re.sub(old_pattern, new_replacement, modified_line)
                        if new_line != modified_line:
                            changes_in_file.append(f"  Line {line_num}: {modified_line.strip()} -> {new_line.strip()}")
                            modified_line = new_line
                
                # Apply specific helper mappings
                for old_import, new_import in self.helper_mappings.items():
                    if modified_line.strip().startswith(old_import):
                        # Replace the specific import
                        new_line = modified_line.replace(old_import, new_import)
                        if new_line != modified_line:
                            changes_in_file.append(f"  Line {line_num}: {modified_line.strip()} -> {new_line.strip()}")
                            modified_line = new_line
                
                modified_lines.append(modified_line)
            
            # Write back if changes were made
            if changes_in_file:
                new_content = '\n'.join(modified_lines)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                self.changes_made.append(f"\n{file_path}:")
                self.changes_made.extend(changes_in_file)
                return True
            
            return False
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return False
    
    def run(self) -> None:
        """Run the import fixing process."""
        print("Starting E2E test import fixing...")
        
        # Find all Python test files
        test_files = self.scan_test_directories()
        print(f"Found {len(test_files)} Python files to process")
        
        # Process each file
        files_changed = 0
        for file_path in test_files:
            self.files_processed += 1
            if self.fix_imports_in_file(file_path):
                files_changed += 1
        
        # Report results
        print(f"\nProcessing complete!")
        print(f"Files processed: {self.files_processed}")
        print(f"Files modified: {files_changed}")
        
        if self.changes_made:
            print(f"\nChanges made:")
            for change in self.changes_made:
                print(change)
        else:
            print("\nNo import changes were needed.")


def main():
    """Main entry point."""
    # Find project root
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    
    # Verify we're in the right place
    if not (project_root / "tests" / "e2e").exists():
        print("Error: Could not find tests/e2e directory. Make sure script is run from project root.")
        sys.exit(1)
    
    # Run the fixer
    fixer = ImportFixer(project_root)
    fixer.run()


if __name__ == "__main__":
    main()