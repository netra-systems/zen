#!/usr/bin/env python3
"""Script to update execution engine imports for SSOT consolidation.

This script updates imports throughout the codebase to use the unified
execution engine factory and consolidated execution engine.

Usage:
    python scripts/update_execution_engine_imports.py [--dry-run] [--verbose]
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple
import ast

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ImportUpdater:
    """Update execution engine imports for SSOT consolidation."""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.changes_made = 0
        self.files_processed = 0
        
        # Define import transformation rules
        self.import_transformations = {
            # Legacy factory imports -> Unified factory
            'from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory': 
                'from netra_backend.app.agents.execution_engine_unified_factory import UnifiedExecutionEngineFactory as ExecutionEngineFactory',
            
            # Legacy execution engine imports -> Interface + adapter  
            'from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine':
                'from netra_backend.app.agents.execution_engine_legacy_adapter import ExecutionEngineFactory',
            
            # Consolidated engine direct imports -> Interface
            'from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine':
                'from netra_backend.app.agents.execution_engine_interface import IExecutionEngine',
                
            # Factory method updates
            'ExecutionEngineFactory.create_for_user': 'ExecutionEngineFactory.create_user_engine',
            'ExecutionEngineFactory.get_default': 'ExecutionEngineFactory.create_engine',
            'create_execution_engine': 'ExecutionEngineFactory.create_engine',
        }
        
        # Files to skip (generated, third-party, etc.)
        self.skip_patterns = {
            '**/.git/**',
            '**/node_modules/**',
            '**/venv/**',
            '**/env/**',
            '**/__pycache__/**',
            '**/*.pyc',
            '**/migrations/**',
            '**/backup/**',
            '**/archived/**',
        }
        
        # Test files get special handling
        self.test_file_patterns = {
            '**/test_*.py',
            '**/tests/**/*.py',
            '**/*_test.py',
        }
    
    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        file_str = str(file_path)
        
        for pattern in self.skip_patterns:
            if file_path.match(pattern):
                return True
                
        return False
    
    def is_test_file(self, file_path: Path) -> bool:
        """Check if file is a test file."""
        for pattern in self.test_file_patterns:
            if file_path.match(pattern):
                return True
        return False
    
    def update_file_imports(self, file_path: Path) -> bool:
        """Update imports in a single file.
        
        Returns:
            bool: True if file was modified
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            modified = False
            
            # Apply import transformations
            for old_import, new_import in self.import_transformations.items():
                if old_import in content:
                    content = content.replace(old_import, new_import)
                    modified = True
                    if self.verbose:
                        print(f"  Replaced: {old_import}")
                        print(f"     With: {new_import}")
            
            # Special handling for test files
            if self.is_test_file(file_path):
                modified = self.update_test_file_patterns(file_path, content) or modified
            
            # Write back if modified
            if modified and not self.dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                if self.verbose:
                    print(f" PASS:  Updated: {file_path}")
            
            elif modified and self.dry_run:
                if self.verbose:
                    print(f"[U+1F4CB] Would update: {file_path}")
            
            return modified
            
        except Exception as e:
            print(f" FAIL:  Error processing {file_path}: {e}")
            return False
    
    def update_test_file_patterns(self, file_path: Path, content: str) -> bool:
        """Special handling for test files.
        
        Args:
            file_path: Path to test file
            content: File content
            
        Returns:
            bool: True if content was modified
        """
        # Test files often need adapters for legacy patterns
        modified = False
        
        # Update common test patterns
        test_patterns = [
            (r'ExecutionEngine\(\s*registry\s*,\s*websocket_bridge\s*\)',
             'ExecutionEngineFactory.create_adapted_engine(ExecutionEngine(registry, websocket_bridge))'),
            
            (r'execution_engine\.execute_agent\(',
             'execution_engine.execute_agent('),
             
            (r'execution_engine\.execute_pipeline\(',
             'execution_engine.execute_pipeline('),
        ]
        
        for pattern, replacement in test_patterns:
            if re.search(pattern, content):
                # Don't actually modify test files automatically - they may need manual review
                if self.verbose:
                    print(f"   SEARCH:  Test pattern found in {file_path}: {pattern}")
                    print(f"     Consider updating to: {replacement}")
        
        return modified
    
    def find_python_files(self) -> List[Path]:
        """Find all Python files to process."""
        python_files = []
        
        for root, dirs, files in os.walk(project_root):
            # Skip certain directories
            dirs[:] = [d for d in dirs if not any(
                Path(root, d).match(pattern) for pattern in self.skip_patterns
            )]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root, file)
                    if not self.should_skip_file(file_path):
                        python_files.append(file_path)
        
        return python_files
    
    def analyze_imports(self, files: List[Path]) -> Dict[str, int]:
        """Analyze current import patterns."""
        import_counts = {}
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Count various import patterns
                patterns = [
                    'from.*execution_engine.*import',
                    'ExecutionEngineFactory',
                    'ExecutionEngine',
                    'create_execution_engine',
                    'create_for_user',
                ]
                
                for pattern in patterns:
                    matches = len(re.findall(pattern, content))
                    if matches > 0:
                        import_counts[pattern] = import_counts.get(pattern, 0) + matches
                        
            except Exception as e:
                if self.verbose:
                    print(f"Warning: Could not analyze {file_path}: {e}")
        
        return import_counts
    
    def run(self) -> None:
        """Run the import update process."""
        print(" CYCLE:  Starting execution engine import consolidation...")
        
        if self.dry_run:
            print("[U+1F4CB] DRY RUN MODE - No files will be modified")
        
        # Find files to process
        python_files = self.find_python_files()
        print(f"[U+1F4C1] Found {len(python_files)} Python files to process")
        
        # Analyze current imports
        if self.verbose:
            print("\n CHART:  Analyzing current import patterns...")
            import_counts = self.analyze_imports(python_files)
            for pattern, count in sorted(import_counts.items()):
                print(f"  {pattern}: {count} occurrences")
        
        # Process files
        print(f"\n[U+1F527] Processing files...")
        for file_path in python_files:
            if self.update_file_imports(file_path):
                self.changes_made += 1
            self.files_processed += 1
            
            if self.files_processed % 50 == 0:
                print(f"  Processed {self.files_processed}/{len(python_files)} files...")
        
        # Summary
        print(f"\n PASS:  Import consolidation complete!")
        print(f" CHART:  Files processed: {self.files_processed}")
        print(f" CYCLE:  Files modified: {self.changes_made}")
        
        if self.dry_run:
            print("[U+1F4CB] This was a dry run - no files were actually modified")
            print("[U+1F4CB] Run without --dry-run to apply changes")
        
        # Next steps
        print(f"\n CYCLE:  Next steps:")
        print(f"1. Review modified files for correctness")
        print(f"2. Run tests to ensure no regressions")
        print(f"3. Update any remaining manual patterns")
        print(f"4. Run mission critical tests to validate SSOT compliance")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Update execution engine imports for SSOT consolidation')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without modifying files')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    
    args = parser.parse_args()
    
    updater = ImportUpdater(dry_run=args.dry_run, verbose=args.verbose)
    updater.run()


if __name__ == '__main__':
    main()