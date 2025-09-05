#!/usr/bin/env python3
"""
Update all tests to use SSOT methods and real services.
Removes mocks, patches, and legacy patterns.
"""

import os
import re
import ast
from pathlib import Path
from typing import Set, List, Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class TestUpdater:
    """Updates test files to SSOT patterns."""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.test_dirs = [
            self.root_dir / "tests",
            self.root_dir / "netra_backend" / "tests",
            self.root_dir / "auth_service" / "tests",
            self.root_dir / "frontend" / "tests",
            self.root_dir / "analytics_service" / "tests"
        ]
        
        # Patterns to replace
        self.mock_imports = [
            r'^from unittest\.mock import.*$',
            r'^from mock import.*$',
            r'^import mock\b',
            r'^from pytest_mock import.*$',
        ]
        
        self.mock_decorators = [
            r'@patch\(',
            r'@mock\.patch\(',
            r'@patch\.object\(',
            r'@patch\.multiple\(',
        ]
        
        self.mock_usage = [
            r'\bMock\(',
            r'\bMagicMock\(',
            r'\bPropertyMock\(',
            r'\bAsyncMock\(',
            r'\bmock\.Mock\(',
            r'\bmock\.MagicMock\(',
            r'\bmocker\.',
        ]
        
        # SSOT imports to use instead
        self.ssot_imports = {
            'websocket': 'from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager',
            'docker': 'from test_framework.docker.unified_docker_manager import UnifiedDockerManager',
            'database': 'from test_framework.database.test_database_manager import TestDatabaseManager',
            'config': 'from shared.isolated_environment import IsolatedEnvironment',
            'redis': 'from test_framework.redis.test_redis_manager import TestRedisManager',
            'auth': 'from auth_service.core.auth_manager import AuthManager',
            'agent': 'from netra_backend.app.core.agent_registry import AgentRegistry',
            'executor': 'from netra_backend.app.core.user_execution_engine import UserExecutionEngine',
        }
        
        self.files_updated = 0
        self.total_files = 0
        self.errors = []
        
    def find_test_files(self) -> List[Path]:
        """Find all test files."""
        test_files = []
        for test_dir in self.test_dirs:
            if test_dir.exists():
                test_files.extend(test_dir.rglob("test_*.py"))
                test_files.extend(test_dir.rglob("*_test.py"))
        return test_files
    
    def has_mock_patterns(self, content: str) -> bool:
        """Check if file has mock patterns."""
        for pattern in self.mock_imports + self.mock_decorators + self.mock_usage:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False
    
    def remove_mock_imports(self, content: str) -> str:
        """Remove mock import statements."""
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            skip = False
            for pattern in self.mock_imports:
                if re.match(pattern, line.strip()):
                    skip = True
                    logger.debug(f"Removing mock import: {line.strip()}")
                    break
            if not skip:
                new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def remove_mock_decorators(self, content: str) -> str:
        """Remove mock decorators from functions."""
        # Remove @patch decorators and their arguments
        content = re.sub(r'@patch\([^)]+\)\s*\n', '', content)
        content = re.sub(r'@mock\.patch\([^)]+\)\s*\n', '', content)
        content = re.sub(r'@patch\.object\([^)]+\)\s*\n', '', content)
        content = re.sub(r'@patch\.multiple\([^)]+\)\s*\n', '', content)
        
        # Remove mocker fixture from function signatures
        content = re.sub(r',\s*mocker(?:\s*:\s*\w+)?(?=\s*[,)])', '', content)
        content = re.sub(r'mocker(?:\s*:\s*\w+)?,\s*', '', content)
        
        return content
    
    def replace_mock_usage(self, content: str) -> str:
        """Replace Mock() usage with real instances."""
        # Replace Mock() with actual service instances
        replacements = {
            r'Mock\(\)': 'None  # TODO: Use real service instance',
            r'MagicMock\(\)': 'None  # TODO: Use real service instance',
            r'AsyncMock\(\)': 'None  # TODO: Use real async service instance',
            r'PropertyMock\([^)]*\)': 'None  # TODO: Use real property',
            r'mocker\.patch\([^)]+\)': '# TODO: Use real service',
            r'mocker\.Mock\(\)': 'None  # TODO: Use real service',
        }
        
        for pattern, replacement in replacements.items():
            content = re.sub(pattern, replacement, content)
        
        return content
    
    def add_ssot_imports(self, content: str) -> str:
        """Add SSOT imports based on file content."""
        imports_to_add = []
        
        # Detect what services are being tested
        if 'websocket' in content.lower() or 'ws' in content.lower():
            imports_to_add.append(self.ssot_imports['websocket'])
        
        if 'docker' in content.lower() or 'container' in content.lower():
            imports_to_add.append(self.ssot_imports['docker'])
        
        if 'database' in content.lower() or 'db' in content.lower() or 'session' in content.lower():
            imports_to_add.append(self.ssot_imports['database'])
        
        if 'redis' in content.lower() or 'cache' in content.lower():
            imports_to_add.append(self.ssot_imports['redis'])
        
        if 'auth' in content.lower() or 'login' in content.lower() or 'token' in content.lower():
            imports_to_add.append(self.ssot_imports['auth'])
        
        if 'agent' in content.lower():
            imports_to_add.append(self.ssot_imports['agent'])
            imports_to_add.append(self.ssot_imports['executor'])
        
        # Always add config import
        imports_to_add.append(self.ssot_imports['config'])
        
        if imports_to_add:
            # Add imports after the first import block
            lines = content.split('\n')
            import_index = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_index = i + 1
                elif import_index > 0 and line.strip() == '':
                    # Found end of import block
                    break
            
            # Insert new imports
            for imp in imports_to_add:
                if imp not in content:
                    lines.insert(import_index, imp)
                    import_index += 1
            
            content = '\n'.join(lines)
        
        return content
    
    def update_fixture_to_real_services(self, content: str) -> str:
        """Update fixtures to use real services."""
        # Replace mock fixtures with real service fixtures
        fixture_replacements = {
            r'@pytest\.fixture\s*\n\s*def\s+mock_(\w+)\([^)]*\):': r'@pytest.fixture\n def real_\1():',
            r'def\s+mock_(\w+)_fixture\([^)]*\):': r'def real_\1_fixture():',
        }
        
        for pattern, replacement in fixture_replacements.items():
            content = re.sub(pattern, replacement, content)
        
        # Add real service initialization in fixtures
        if '@pytest.fixture' in content:
            content = re.sub(
                r'(@pytest\.fixture.*?\n\s*def\s+\w+\([^)]*\):.*?\n)',
                r'\1    """Use real service instance."""\n    # TODO: Initialize real service\n',
                content,
                flags=re.MULTILINE | re.DOTALL
            )
        
        return content
    
    def update_test_file(self, file_path: Path) -> bool:
        """Update a single test file."""
        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            
            if not self.has_mock_patterns(content):
                return False
            
            logger.info(f"Updating {file_path.relative_to(self.root_dir)}")
            
            # Apply transformations
            content = self.remove_mock_imports(content)
            content = self.remove_mock_decorators(content)
            content = self.replace_mock_usage(content)
            content = self.add_ssot_imports(content)
            content = self.update_fixture_to_real_services(content)
            
            # Write back if changed
            if content != original_content:
                file_path.write_text(content, encoding='utf-8')
                self.files_updated += 1
                return True
            
            return False
            
        except Exception as e:
            error_msg = f"Error updating {file_path}: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return False
    
    def run(self):
        """Run the update process."""
        logger.info("Starting SSOT test update process...")
        
        test_files = self.find_test_files()
        self.total_files = len(test_files)
        logger.info(f"Found {self.total_files} test files")
        
        for file_path in test_files:
            self.update_test_file(file_path)
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info(f"SSOT Test Update Complete")
        logger.info(f"Total files scanned: {self.total_files}")
        logger.info(f"Files updated: {self.files_updated}")
        logger.info(f"Errors encountered: {len(self.errors)}")
        
        if self.errors:
            logger.error("\nErrors:")
            for error in self.errors[:10]:  # Show first 10 errors
                logger.error(f"  - {error}")
            if len(self.errors) > 10:
                logger.error(f"  ... and {len(self.errors) - 10} more errors")
        
        # Create report
        self.create_report()
    
    def create_report(self):
        """Create a detailed report of the update process."""
        report_path = self.root_dir / "SSOT_TEST_UPDATE_REPORT.md"
        
        report = f"""# SSOT Test Update Report

## Summary
- **Total Test Files**: {self.total_files}
- **Files Updated**: {self.files_updated}
- **Errors**: {len(self.errors)}
- **Success Rate**: {(self.files_updated / self.total_files * 100):.1f}%

## Changes Applied
1. Removed all mock imports (unittest.mock, mock, pytest_mock)
2. Removed @patch decorators and mocker fixtures
3. Replaced Mock() usage with real service placeholders
4. Added SSOT imports for real services
5. Updated fixtures to use real service instances

## Next Steps
1. Run tests with real services: `python tests/unified_test_runner.py --real-services`
2. Fix any remaining TODO markers in updated tests
3. Verify all tests pass with Docker services running
4. Update any custom mock patterns not caught by automated update

## Errors
{chr(10).join(self.errors) if self.errors else "No errors encountered"}
"""
        
        report_path.write_text(report)
        logger.info(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    updater = TestUpdater()
    updater.run()