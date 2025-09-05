#!/usr/bin/env python3
"""
Fix automated replacements and complete SSOT migration.
"""

import os
import re
import ast
from pathlib import Path
from typing import List, Dict, Set
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedTestFixer:
    """Advanced fixes for test files to complete SSOT migration."""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.files_fixed = 0
        self.total_files = 0
        self.errors = []
        
        # More patterns to fix
        self.todo_markers = [
            r'# TODO: Use real service instance',
            r'# TODO: Use real async service instance',
            r'# TODO: Use real property',
            r'# TODO: Use real service',
            r'# TODO: Initialize real service',
        ]
        
        # Real service initializations
        self.service_replacements = {
            'websocket_manager': 'UnifiedWebSocketManager()',
            'docker_manager': 'UnifiedDockerManager()',
            'database_manager': 'TestDatabaseManager()',
            'redis_manager': 'TestRedisManager()',
            'auth_manager': 'AuthManager()',
            'agent_registry': 'AgentRegistry()',
            'execution_engine': 'UserExecutionEngine()',
        }
        
        # Common mock patterns that need more specific fixes
        self.mock_patterns = {
            r'mock_response\s*=\s*None': 'response = await real_service.execute()',
            r'mock_session\s*=\s*None': 'session = database_manager.get_session()',
            r'mock_redis\s*=\s*None': 'redis = redis_manager.get_client()',
            r'mock_websocket\s*=\s*None': 'websocket = websocket_manager.get_connection()',
            r'mock_agent\s*=\s*None': 'agent = agent_registry.get_agent("supervisor")',
        }
    
    def find_test_files(self) -> List[Path]:
        """Find all Python test files."""
        test_files = []
        for root, dirs, files in os.walk(self.root_dir):
            # Skip virtual environments
            if '.venv' in root or '__pycache__' in root:
                continue
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(Path(root) / file)
        return test_files
    
    def fix_todo_markers(self, content: str) -> str:
        """Replace TODO markers with real service initializations."""
        for marker in self.todo_markers:
            if marker in content:
                # Determine what service this is for
                lines = content.split('\n')
                new_lines = []
                
                for i, line in enumerate(lines):
                    if marker in line:
                        # Look at the variable name being assigned
                        var_match = re.search(r'(\w+)\s*=\s*None\s*' + re.escape(marker), line)
                        if var_match:
                            var_name = var_match.group(1)
                            # Find appropriate replacement
                            replacement = self.get_service_replacement(var_name)
                            new_line = line.replace(f'None  {marker}', replacement)
                            new_lines.append(new_line)
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
                
                content = '\n'.join(new_lines)
        
        return content
    
    def get_service_replacement(self, var_name: str) -> str:
        """Get appropriate service replacement based on variable name."""
        var_lower = var_name.lower()
        
        if 'websocket' in var_lower or 'ws' in var_lower:
            return 'UnifiedWebSocketManager()'
        elif 'docker' in var_lower or 'container' in var_lower:
            return 'UnifiedDockerManager()'
        elif 'database' in var_lower or 'db' in var_lower or 'session' in var_lower:
            return 'TestDatabaseManager().get_session()'
        elif 'redis' in var_lower or 'cache' in var_lower:
            return 'TestRedisManager().get_client()'
        elif 'auth' in var_lower or 'token' in var_lower:
            return 'AuthManager()'
        elif 'agent' in var_lower:
            return 'AgentRegistry().get_agent("supervisor")'
        elif 'executor' in var_lower or 'engine' in var_lower:
            return 'UserExecutionEngine()'
        else:
            return f'{var_name}_instance  # Initialize appropriate service'
    
    def fix_mock_patterns(self, content: str) -> str:
        """Fix common mock patterns with real implementations."""
        for pattern, replacement in self.mock_patterns.items():
            content = re.sub(pattern, replacement, content)
        
        return content
    
    def add_missing_imports(self, content: str) -> str:
        """Ensure all necessary imports are present."""
        required_imports = []
        
        # Check what services are used
        if 'UnifiedWebSocketManager' in content and 'from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager' not in content:
            required_imports.append('from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager')
        
        if 'UnifiedDockerManager' in content and 'from test_framework.docker.unified_docker_manager import UnifiedDockerManager' not in content:
            required_imports.append('from test_framework.docker.unified_docker_manager import UnifiedDockerManager')
        
        if 'TestDatabaseManager' in content and 'from test_framework.database.test_database_manager import TestDatabaseManager' not in content:
            required_imports.append('from test_framework.database.test_database_manager import TestDatabaseManager')
        
        if 'TestRedisManager' in content and 'from test_framework.redis.test_redis_manager import TestRedisManager' not in content:
            required_imports.append('from test_framework.redis.test_redis_manager import TestRedisManager')
        
        if 'AuthManager' in content and 'from auth_service.core.auth_manager import AuthManager' not in content:
            required_imports.append('from auth_service.core.auth_manager import AuthManager')
        
        if 'AgentRegistry' in content and 'from netra_backend.app.core.agent_registry import AgentRegistry' not in content:
            required_imports.append('from netra_backend.app.core.agent_registry import AgentRegistry')
        
        if 'UserExecutionEngine' in content and 'from netra_backend.app.core.user_execution_engine import UserExecutionEngine' not in content:
            required_imports.append('from netra_backend.app.core.user_execution_engine import UserExecutionEngine')
        
        # Always ensure IsolatedEnvironment is imported
        if 'IsolatedEnvironment' not in content:
            required_imports.append('from shared.isolated_environment import IsolatedEnvironment')
        
        if required_imports:
            # Add imports after existing imports
            lines = content.split('\n')
            import_index = 0
            
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_index = i + 1
                elif import_index > 0 and line.strip() == '':
                    break
            
            for imp in required_imports:
                lines.insert(import_index, imp)
                import_index += 1
            
            content = '\n'.join(lines)
        
        return content
    
    def fix_test_file(self, file_path: Path) -> bool:
        """Fix a single test file."""
        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            
            # Apply all fixes
            content = self.fix_todo_markers(content)
            content = self.fix_mock_patterns(content)
            content = self.add_missing_imports(content)
            
            # Remove any remaining mock imports
            content = self.remove_remaining_mocks(content)
            
            # Write back if changed
            if content != original_content:
                file_path.write_text(content, encoding='utf-8')
                self.files_fixed += 1
                logger.info(f"Fixed {file_path.relative_to(self.root_dir)}")
                return True
            
            return False
            
        except Exception as e:
            error_msg = f"Error fixing {file_path}: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return False
    
    def remove_remaining_mocks(self, content: str) -> str:
        """Remove any remaining mock references."""
        # Remove mock-related imports
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            # Skip lines with mock imports
            if any(word in line for word in ['unittest.mock', 'pytest_mock', 'from mock', 'import mock']):
                continue
            # Skip lines with @patch decorators
            if '@patch' in line:
                continue
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def run(self):
        """Run the fixing process."""
        logger.info("Starting advanced SSOT fixes...")
        
        test_files = self.find_test_files()
        self.total_files = len(test_files)
        logger.info(f"Found {self.total_files} test files")
        
        for file_path in test_files:
            self.fix_test_file(file_path)
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info(f"Advanced SSOT Fixes Complete")
        logger.info(f"Total files scanned: {self.total_files}")
        logger.info(f"Files fixed: {self.files_fixed}")
        logger.info(f"Errors encountered: {len(self.errors)}")
        
        if self.errors:
            logger.error("\nErrors:")
            for error in self.errors[:10]:
                logger.error(f"  - {error}")
            if len(self.errors) > 10:
                logger.error(f"  ... and {len(self.errors) - 10} more errors")
        
        self.create_report()
    
    def create_report(self):
        """Create a report of the fixes."""
        report_path = self.root_dir / "ADVANCED_SSOT_FIX_REPORT.md"
        
        report = f"""# Advanced SSOT Fix Report

## Summary
- **Total Test Files**: {self.total_files}
- **Files Fixed**: {self.files_fixed}
- **Errors**: {len(self.errors)}

## Fixes Applied
1. Replaced TODO markers with real service initializations
2. Fixed common mock patterns with real implementations
3. Added missing service imports
4. Removed remaining mock references

## Next Steps
1. Run syntax validation: `python fix_syntax_errors.py`
2. Run tests with real services: `python tests/unified_test_runner.py --real-services`
3. Fix any remaining test failures

## Errors
{chr(10).join(self.errors) if self.errors else "No errors encountered"}
"""
        
        report_path.write_text(report)
        logger.info(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    fixer = AdvancedTestFixer()
    fixer.run()