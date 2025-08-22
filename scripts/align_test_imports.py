#!/usr/bin/env python
"""
Align Test Imports and Configuration Script
Fixes all test-related import issues and configuration misalignments.
"""

import ast
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestImportAligner:
    """Aligns test imports and fixes configuration issues."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.backend_path = self.project_root / "netra_backend"
        self.test_dirs = {
            "backend": self.backend_path / "tests",
            "framework": self.project_root / "test_framework",
            "frontend": self.project_root / "frontend" / "__tests__"
        }
        self.import_fixes = []
        self.config_fixes = []
        self.file_fixes = []
        
    def run(self):
        """Main execution method."""
        logger.info("Starting test import alignment...")
        
        # 1. Scan for test files and issues
        test_files = self.scan_test_files()
        logger.info(f"Found {len(test_files)} test files")
        
        # 2. Fix import issues
        self.fix_import_issues(test_files)
        
        # 3. Fix test runner configuration
        self.fix_test_runner_config()
        
        # 4. Fix test discovery paths
        self.fix_test_discovery_paths()
        
        # 5. Fix syntax and structure issues
        self.fix_syntax_issues(test_files)
        
        # 6. Generate report
        self.generate_report()
        
        logger.info("Test alignment complete!")
        
    def scan_test_files(self) -> List[Path]:
        """Scan for all test files in the project."""
        test_files = []
        
        # Backend tests
        if self.test_dirs["backend"].exists():
            test_files.extend(self.test_dirs["backend"].rglob("test_*.py"))
            test_files.extend(self.test_dirs["backend"].rglob("*_test.py"))
            
        # Test framework files
        if self.test_dirs["framework"].exists():
            test_files.extend(self.test_dirs["framework"].rglob("test_*.py"))
            
        # Filter out __pycache__ and .venv
        test_files = [f for f in test_files if "__pycache__" not in str(f) and ".venv" not in str(f)]
        
        return test_files
        
    def fix_import_issues(self, test_files: List[Path]):
        """Fix import issues in test files."""
        logger.info("Fixing import issues...")
        
        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')
                original_content = content
                fixed = False
                
                # Fix relative imports
                content, rel_fixed = self.fix_relative_imports(content, test_file)
                fixed = fixed or rel_fixed
                
                # Fix missing sys.path additions
                content, path_fixed = self.fix_sys_path(content, test_file)
                fixed = fixed or path_fixed
                
                # Fix module imports
                content, mod_fixed = self.fix_module_imports(content, test_file)
                fixed = fixed or mod_fixed
                
                if fixed:
                    test_file.write_text(content, encoding='utf-8')
                    self.import_fixes.append(str(test_file.relative_to(self.project_root)))
                    logger.info(f"Fixed imports in: {test_file.name}")
                    
            except Exception as e:
                logger.error(f"Error fixing {test_file}: {e}")
                
    def fix_relative_imports(self, content: str, file_path: Path) -> Tuple[str, bool]:
        """Fix relative imports in a file."""
        fixed = False
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            # Convert relative imports to absolute
            if re.match(r'^from \.\. import', line):
                # Calculate proper import path
                rel_path = file_path.relative_to(self.backend_path)
                parts = rel_path.parts[:-1]  # Remove filename
                
                if len(parts) >= 2:
                    parent_module = '.'.join(parts[:-1])
                    import_part = line.split('import')[1].strip()
                    new_line = f"from netra_backend.{parent_module} import {import_part}"
                    new_lines.append(new_line)
                    fixed = True
                else:
                    new_lines.append(line)
            elif re.match(r'^from \. import', line):
                # Same directory import
                rel_path = file_path.relative_to(self.backend_path)
                parts = rel_path.parts[:-1]
                
                if parts:
                    current_module = '.'.join(parts)
                    import_part = line.split('import')[1].strip()
                    new_line = f"from netra_backend.{current_module} import {import_part}"
                    new_lines.append(new_line)
                    fixed = True
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
                
        return '\n'.join(new_lines), fixed
        
    def fix_sys_path(self, content: str, file_path: Path) -> Tuple[str, bool]:
        """Ensure proper sys.path setup."""
        if 'sys.path' in content:
            return content, False
            
        # Check if file needs sys.path addition
        needs_path = False
        if 'from netra_backend' in content or 'import netra_backend' in content:
            needs_path = True
            
        if not needs_path:
            return content, False
            
        # Add sys.path setup after imports
        lines = content.split('\n')
        import_end = 0
        
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_end = i + 1
            elif import_end > 0 and line and not line.startswith(' '):
                break
                
        path_setup = [
            "",
            "# Add project root to path",
            "import sys",
            "from pathlib import Path",
            ""
        ]
        
        lines[import_end:import_end] = path_setup
        return '\n'.join(lines), True
        
    def fix_module_imports(self, content: str, file_path: Path) -> Tuple[str, bool]:
        """Fix incorrect module imports."""
        fixed = False
        
        # Common import fixes
        replacements = [
            # Fix test framework imports
            (r'from test_framework\.(\w+) import', r'from test_framework.\1 import'),
            # Fix netra_backend imports
            (r'from app\.', r'from netra_backend.app.'),
            (r'import app\.', r'import netra_backend.app.'),
            # Fix helpers imports
            (r'from tests\.helpers', r'from netra_backend.tests.helpers'),
            (r'from tests\.fixtures', r'from netra_backend.tests.fixtures'),
            # Fix conftest imports
            (r'from conftest import', r'from netra_backend.tests.conftest import'),
        ]
        
        for pattern, replacement in replacements:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                fixed = True
                
        return content, fixed
        
    def fix_test_runner_config(self):
        """Fix test runner configuration."""
        logger.info("Fixing test runner configuration...")
        
        config_file = self.project_root / "test_framework" / "test_config.py"
        
        if not config_file.exists():
            logger.warning(f"Test config file not found: {config_file}")
            return
            
        try:
            content = config_file.read_text(encoding='utf-8')
            original_content = content
            
            # Fix test directories
            content = self.update_test_directories(content)
            
            # Fix component mappings
            content = self.update_component_mappings(content)
            
            if content != original_content:
                config_file.write_text(content, encoding='utf-8')
                self.config_fixes.append("test_config.py")
                logger.info("Updated test runner configuration")
                
        except Exception as e:
            logger.error(f"Error fixing test config: {e}")
            
    def update_test_directories(self, content: str) -> str:
        """Update test directory paths in config."""
        # Update TEST_DIRECTORIES mapping
        test_dirs_pattern = r'TEST_DIRECTORIES\s*=\s*\{[^}]+\}'
        
        new_test_dirs = '''TEST_DIRECTORIES = {
    "unit": ["netra_backend/tests/unit"],
    "integration": ["netra_backend/tests/integration"],
    "e2e": ["netra_backend/tests/e2e"],
    "agents": ["netra_backend/tests/agents"],
    "critical": ["netra_backend/tests/critical"],
    "routes": ["netra_backend/tests/routes"],
    "services": ["netra_backend/tests/services"],
    "database": ["netra_backend/tests/database"],
    "websocket": ["netra_backend/tests/websocket"],
    "auth": ["netra_backend/tests/auth_integration"],
    "performance": ["netra_backend/tests/performance"],
    "security": ["netra_backend/tests/security"],
    "mcp": ["netra_backend/tests/mcp"],
    "utils": ["netra_backend/tests/utils"],
    "validation": ["netra_backend/tests/validation"],
    "config": ["netra_backend/tests/config"],
    "startup": ["netra_backend/tests/startup"],
    "llm": ["netra_backend/tests/llm"],
    "core": ["netra_backend/tests/core"],
    "unified_system": ["netra_backend/tests/unified_system"],
    "test_framework": ["test_framework/tests"]
}'''
        
        if re.search(test_dirs_pattern, content):
            content = re.sub(test_dirs_pattern, new_test_dirs, content)
        
        return content
        
    def update_component_mappings(self, content: str) -> str:
        """Update component mappings in config."""
        # Update COMPONENT_MAPPINGS
        comp_pattern = r'COMPONENT_MAPPINGS\s*=\s*\{[^}]+\}'
        
        new_mappings = '''COMPONENT_MAPPINGS = {
    "backend": {
        "paths": ["netra_backend/tests"],
        "exclude": ["frontend", "auth_service"]
    },
    "frontend": {
        "paths": ["frontend/__tests__"],
        "exclude": []
    },
    "auth": {
        "paths": ["netra_backend/tests/auth_integration", "auth_service/tests"],
        "exclude": []
    },
    "agents": {
        "paths": ["netra_backend/tests/agents"],
        "exclude": []
    },
    "database": {
        "paths": ["netra_backend/tests/database", "netra_backend/tests/clickhouse"],
        "exclude": []
    },
    "websocket": {
        "paths": ["netra_backend/tests/websocket", "netra_backend/tests/ws_manager"],
        "exclude": []
    }
}'''
        
        if re.search(comp_pattern, content):
            content = re.sub(comp_pattern, new_mappings, content)
            
        return content
        
    def fix_test_discovery_paths(self):
        """Fix test discovery configuration."""
        logger.info("Fixing test discovery paths...")
        
        discovery_file = self.project_root / "test_framework" / "test_discovery.py"
        
        if not discovery_file.exists():
            logger.warning(f"Test discovery file not found: {discovery_file}")
            return
            
        try:
            content = discovery_file.read_text(encoding='utf-8')
            original_content = content
            
            # Fix default test paths
            pattern = r'DEFAULT_TEST_PATHS\s*=\s*\[[^\]]+\]'
            new_paths = '''DEFAULT_TEST_PATHS = [
        "netra_backend/tests",
        "test_framework/tests",
        "frontend/__tests__",
        "auth_service/tests"
    ]'''
            
            if re.search(pattern, content):
                content = re.sub(pattern, new_paths, content)
                
            if content != original_content:
                discovery_file.write_text(content, encoding='utf-8')
                self.config_fixes.append("test_discovery.py")
                logger.info("Updated test discovery configuration")
                
        except Exception as e:
            logger.error(f"Error fixing test discovery: {e}")
            
    def fix_syntax_issues(self, test_files: List[Path]):
        """Fix syntax and structure issues in test files."""
        logger.info("Checking for syntax issues...")
        
        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')
                
                # Try to parse the file
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    logger.warning(f"Syntax error in {test_file.name}: {e}")
                    
                    # Try to fix common issues
                    fixed_content = self.fix_common_syntax_issues(content)
                    
                    try:
                        ast.parse(fixed_content)
                        test_file.write_text(fixed_content, encoding='utf-8')
                        self.file_fixes.append(str(test_file.relative_to(self.project_root)))
                        logger.info(f"Fixed syntax in: {test_file.name}")
                    except SyntaxError:
                        logger.error(f"Could not auto-fix syntax in: {test_file.name}")
                        
            except Exception as e:
                logger.error(f"Error processing {test_file}: {e}")
                
    def fix_common_syntax_issues(self, content: str) -> str:
        """Fix common syntax issues in Python code."""
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Fix unclosed strings
            if line.count('"') % 2 != 0:
                line = line + '"'
            if line.count("'") % 2 != 0:
                line = line + "'"
                
            # Fix unclosed parentheses
            open_parens = line.count('(')
            close_parens = line.count(')')
            if open_parens > close_parens:
                line = line + ')' * (open_parens - close_parens)
                
            # Fix unclosed brackets
            open_brackets = line.count('[')
            close_brackets = line.count(']')
            if open_brackets > close_brackets:
                line = line + ']' * (open_brackets - close_brackets)
                
            fixed_lines.append(line)
            
        return '\n'.join(fixed_lines)
        
    def generate_report(self):
        """Generate alignment report."""
        from datetime import datetime
        report = {
            "timestamp": datetime.now().isoformat(),
            "import_fixes": self.import_fixes,
            "config_fixes": self.config_fixes,
            "file_fixes": self.file_fixes,
            "summary": {
                "total_import_fixes": len(self.import_fixes),
                "total_config_fixes": len(self.config_fixes),
                "total_file_fixes": len(self.file_fixes)
            }
        }
        
        report_file = self.project_root / "test_reports" / "alignment_report.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Report saved to: {report_file}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("TEST ALIGNMENT SUMMARY")
        print("=" * 60)
        print(f"Import fixes applied: {len(self.import_fixes)}")
        print(f"Configuration fixes applied: {len(self.config_fixes)}")
        print(f"Syntax fixes applied: {len(self.file_fixes)}")
        print("=" * 60)
        
        if self.import_fixes:
            print("\nFixed imports in:")
            for file in self.import_fixes[:10]:
                print(f"  - {file}")
            if len(self.import_fixes) > 10:
                print(f"  ... and {len(self.import_fixes) - 10} more")
                
        if self.config_fixes:
            print("\nUpdated configurations:")
            for config in self.config_fixes:
                print(f"  - {config}")
                
        if self.file_fixes:
            print("\nFixed syntax issues in:")
            for file in self.file_fixes[:10]:
                print(f"  - {file}")
            if len(self.file_fixes) > 10:
                print(f"  ... and {len(self.file_fixes) - 10} more")


def main():
    """Main entry point."""
    aligner = TestImportAligner()
    aligner.run()


if __name__ == "__main__":
    main()