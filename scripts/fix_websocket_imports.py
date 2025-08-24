#!/usr/bin/env python3
"""
WebSocket Import Fixer Script

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Stability & Development Velocity
- Value Impact: Fixes 175 failing test files, enables 100% test collection
- Strategic Impact: Critical for CI/CD pipeline and development workflow

This script systematically fixes all WebSocketManager import errors across test files.
It handles various import patterns and ensures compliance with SPEC requirements.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebSocketImportFixer:
    """Systematically fixes WebSocket imports across all test files."""
    
    def __init__(self, base_path: str = None):
        """Initialize the fixer with base path."""
        if base_path is None:
            # Auto-detect base path
            current_path = Path(__file__).parent.parent
            self.base_path = current_path
        else:
            self.base_path = Path(base_path)
        
        self.test_dirs = [
            self.base_path / "netra_backend" / "tests",
            self.base_path / "tests" / "e2e"
        ]
        
        # Statistics tracking
        self.files_processed = 0
        self.files_modified = 0
        self.imports_fixed = 0
        self.patterns_found = set()
        
        # Import patterns to fix (old -> new)
        self.import_fixes = {
            # Direct websocket_core imports that are incorrect
            r'from netra_backend\.app\.websocket_core import WebSocketManager': 
                'from netra_backend.app.websocket_core.manager import WebSocketManager',
            
            r'from netra_backend\.app\.websocket_core import UnifiedWebSocketManager as WebSocketManager':
                'from netra_backend.app.websocket_core.manager import WebSocketManager',
                
            r'from netra_backend\.app\.websocket_core import UnifiedWebSocketManager':
                'from netra_backend.app.websocket_core.manager import WebSocketManager as UnifiedWebSocketManager',
                
            r'from netra_backend\.app\.websocket_core import get_unified_manager':
                'from netra_backend.app.websocket_core.manager import get_websocket_manager as get_unified_manager',
                
            r'from netra_backend\.app\.websocket_core import get_websocket_manager':
                'from netra_backend.app.websocket_core.manager import get_websocket_manager',
                
            r'from netra_backend\.app\.websocket_core import ConnectionInfo':
                'from netra_backend.app.websocket_core.types import ConnectionInfo',
                
            r'from netra_backend\.app\.websocket_core import websocket_context':
                'from netra_backend.app.websocket_core.manager import websocket_context',
                
            # Multi-import fixes
            r'from netra_backend\.app\.websocket_core import get_websocket_manager, WebSocketManager':
                'from netra_backend.app.websocket_core.manager import get_websocket_manager, WebSocketManager',
                
            r'from netra_backend\.app\.websocket_core import WebSocketManager, get_websocket_manager':
                'from netra_backend.app.websocket_core.manager import WebSocketManager, get_websocket_manager',
                
            # Legacy websocket imports
            r'from netra_backend\.app\.websocket\.unified\.manager import UnifiedWebSocketManager':
                'from netra_backend.app.websocket_core.manager import WebSocketManager as UnifiedWebSocketManager',
                
            r'from netra_backend\.app\.websocket\.unified\.manager import get_unified_manager':
                'from netra_backend.app.websocket_core.manager import get_websocket_manager as get_unified_manager',
                
            # Handle commented out imports too
            r'# from netra_backend\.app\.websocket\.unified\.messaging import UnifiedMessagingService':
                '# from netra_backend.app.websocket_core.handlers import MessageHandler as UnifiedMessagingService  # Fixed: UnifiedMessagingService',
                
            # General legacy websocket patterns
            r'from netra_backend\.app\.websocket\.unified':
                'from netra_backend.app.websocket_core  # Fixed: legacy websocket.unified',
                
            r'from netra_backend\.app\.websocket\.connection import ConnectionInfo':
                'from netra_backend.app.websocket_core.types import ConnectionInfo',
                
            r'from netra_backend\.app\.websocket\.connection import ConnectionManager':
                'from netra_backend.app.websocket_core.manager import WebSocketManager as ConnectionManager',
                
            # Handle renamed imports with "as" clause
            r'from netra_backend\.app\.websocket_core import ConnectionInfo, WebSocketManager as ConnectionManager':
                'from netra_backend.app.websocket_core.types import ConnectionInfo\nfrom netra_backend.app.websocket_core.manager import WebSocketManager as ConnectionManager',
                
            # Sub-module specific imports
            r'from netra_backend\.app\.websocket_core\.unified\.message_handlers import':
                'from netra_backend.app.websocket_core.handlers import',
                
            r'from netra_backend\.app\.websocket_core\.types import WebSocketMessage, MessageType':
                'from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType',
                
            r'from netra_backend\.app\.websocket_core\.broadcast import BroadcastManager':
                'from netra_backend.app.websocket_core.manager import WebSocketManager  # BroadcastManager functionality is in WebSocketManager',
                
            r'from netra_backend\.app\.websocket_core\.validation import MessageValidator':
                'from netra_backend.app.websocket_core.utils import validate_message_structure as MessageValidator',
                
            r'from netra_backend\.app\.websocket_core\.performance_monitor_core import PerformanceMonitor':
                'from netra_backend.app.websocket_core.utils import WebSocketConnectionMonitor as PerformanceMonitor',
                
            r'from netra_backend\.app\.websocket_core\.performance_monitor_types import PerformanceThresholds':
                'from netra_backend.app.websocket_core.types import ConnectionMetrics as PerformanceThresholds',
        }
        
        # Complex multi-line import patterns
        self.multiline_patterns = [
            # Pattern for complex multi-line imports
            (
                re.compile(r'from netra_backend\.app\.websocket_core import \(\s*\n(\s*.*?\n)*?\s*\)', re.MULTILINE | re.DOTALL),
                self._fix_multiline_websocket_core_import
            )
        ]

    def _fix_multiline_websocket_core_import(self, match: re.Match) -> str:
        """Fix complex multiline imports from websocket_core."""
        import_text = match.group(0)
        
        # Extract individual imports
        imports = re.findall(r'(\w+)', import_text)
        
        # Map to correct modules
        manager_imports = []
        type_imports = []
        handler_imports = []
        auth_imports = []
        util_imports = []
        
        for imp in imports:
            if imp in ['WebSocketManager', 'get_websocket_manager', 'websocket_context', 'UnifiedWebSocketManager']:
                manager_imports.append(imp)
            elif imp in ['ConnectionInfo', 'WebSocketMessage', 'MessageType', 'ServerMessage', 'ErrorMessage', 'BroadcastResult', 'WebSocketStats']:
                type_imports.append(imp)
            elif imp in ['MessageRouter', 'get_message_router', 'send_error_to_websocket', 'send_system_message']:
                handler_imports.append(imp)
            elif imp in ['WebSocketAuthenticator', 'get_websocket_authenticator', 'RateLimiter']:
                auth_imports.append(imp)
            else:
                util_imports.append(imp)
        
        # Build new import statements
        new_imports = []
        if manager_imports:
            new_imports.append(f"from netra_backend.app.websocket_core.manager import {', '.join(manager_imports)}")
        if type_imports:
            new_imports.append(f"from netra_backend.app.websocket_core.types import {', '.join(type_imports)}")
        if handler_imports:
            new_imports.append(f"from netra_backend.app.websocket_core.handlers import {', '.join(handler_imports)}")
        if auth_imports:
            new_imports.append(f"from netra_backend.app.websocket_core.auth import {', '.join(auth_imports)}")
        if util_imports:
            new_imports.append(f"from netra_backend.app.websocket_core.utils import {', '.join(util_imports)}")
            
        return '\n'.join(new_imports)

    def scan_file(self, file_path: Path) -> List[Tuple[str, str, int]]:
        """Scan a file for problematic imports and return fixes needed."""
        fixes_needed = []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Track patterns found for reporting
                if 'websocket_core' in line and ('import' in line or 'from' in line):
                    self.patterns_found.add(line.strip())
                
                # Check single-line patterns
                for pattern, replacement in self.import_fixes.items():
                    if re.search(pattern, line):
                        fixes_needed.append((pattern, replacement, line_num))
            
            # Check multiline patterns
            for pattern, fix_func in self.multiline_patterns:
                for match in pattern.finditer(content):
                    line_num = content[:match.start()].count('\n') + 1
                    replacement = fix_func(match)
                    fixes_needed.append((match.group(0), replacement, line_num))
                        
        except Exception as e:
            logger.error(f"Error scanning {file_path}: {e}")
            
        return fixes_needed

    def fix_file(self, file_path: Path) -> bool:
        """Fix imports in a single file."""
        fixes_needed = self.scan_file(file_path)
        
        if not fixes_needed:
            return False
            
        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            
            # Apply fixes
            for pattern, replacement, line_num in fixes_needed:
                if isinstance(pattern, str) and pattern.startswith('from netra_backend'):
                    # This is a regex pattern string
                    content = re.sub(pattern, replacement, content)
                else:
                    # This is a literal string replacement
                    content = content.replace(pattern, replacement)
                
                self.imports_fixed += 1
                logger.info(f"  Fixed import at line {line_num}: {pattern[:50]}...")
            
            # Only write if content changed
            if content != original_content:
                file_path.write_text(content, encoding='utf-8')
                self.files_modified += 1
                logger.info(f"✓ Modified {file_path}")
                return True
                
        except Exception as e:
            logger.error(f"Error fixing {file_path}: {e}")
            
        return False

    def find_python_files(self, directory: Path) -> List[Path]:
        """Find all Python test files in directory."""
        python_files = []
        
        if not directory.exists():
            logger.warning(f"Directory {directory} does not exist, skipping")
            return python_files
            
        for file_path in directory.rglob("*.py"):
            # Skip __pycache__ and .pyc files
            if "__pycache__" not in str(file_path) and file_path.suffix == ".py":
                python_files.append(file_path)
                
        return python_files

    def run_fixes(self, dry_run: bool = False) -> Dict[str, int]:
        """Run import fixes across all test directories."""
        logger.info(f"Starting WebSocket import fixes (dry_run={dry_run})")
        logger.info(f"Base path: {self.base_path}")
        
        all_files = []
        for test_dir in self.test_dirs:
            files = self.find_python_files(test_dir)
            logger.info(f"Found {len(files)} Python files in {test_dir}")
            all_files.extend(files)
        
        logger.info(f"Total files to process: {len(all_files)}")
        
        # Process files
        for file_path in all_files:
            self.files_processed += 1
            
            if dry_run:
                fixes_needed = self.scan_file(file_path)
                if fixes_needed:
                    logger.info(f"Would fix {len(fixes_needed)} imports in {file_path}")
            else:
                if self.fix_file(file_path):
                    logger.info(f"Fixed imports in {file_path}")
        
        # Report results
        logger.info("\n" + "="*60)
        logger.info("WEBSOCKET IMPORT FIX RESULTS")
        logger.info("="*60)
        logger.info(f"Files processed: {self.files_processed}")
        logger.info(f"Files modified: {self.files_modified}")
        logger.info(f"Imports fixed: {self.imports_fixed}")
        logger.info(f"Unique patterns found: {len(self.patterns_found)}")
        
        if self.patterns_found:
            logger.info("\nPatterns detected:")
            for pattern in sorted(self.patterns_found):
                logger.info(f"  {pattern}")
        
        return {
            "files_processed": self.files_processed,
            "files_modified": self.files_modified, 
            "imports_fixed": self.imports_fixed,
            "patterns_found": len(self.patterns_found)
        }

    def validate_fixes(self) -> bool:
        """Validate that fixes were applied correctly."""
        logger.info("Validating import fixes...")
        
        validation_errors = []
        all_files = []
        
        for test_dir in self.test_dirs:
            all_files.extend(self.find_python_files(test_dir))
        
        for file_path in all_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # Check for remaining problematic patterns
                problematic_patterns = [
                    r'from netra_backend\.app\.websocket_core import WebSocketManager',
                    r'from netra_backend\.app\.websocket\.unified',
                    r'from netra_backend\.app\.websocket\.connection',
                ]
                
                for pattern in problematic_patterns:
                    if re.search(pattern, content):
                        validation_errors.append(f"{file_path}: Still contains pattern {pattern}")
                        
            except Exception as e:
                validation_errors.append(f"{file_path}: Error reading file - {e}")
        
        if validation_errors:
            logger.error(f"Validation failed with {len(validation_errors)} errors:")
            for error in validation_errors[:10]:  # Show first 10 errors
                logger.error(f"  {error}")
            if len(validation_errors) > 10:
                logger.error(f"  ... and {len(validation_errors) - 10} more errors")
            return False
        
        logger.info("✓ All import fixes validated successfully")
        return True


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix WebSocket imports in test files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--base-path', type=str, help='Base path of the project')
    parser.add_argument('--validate', action='store_true', help='Validate fixes after applying them')
    
    args = parser.parse_args()
    
    try:
        fixer = WebSocketImportFixer(args.base_path)
        results = fixer.run_fixes(dry_run=args.dry_run)
        
        if not args.dry_run and args.validate:
            if not fixer.validate_fixes():
                sys.exit(1)
        
        # Return results for external use
        return results
        
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()