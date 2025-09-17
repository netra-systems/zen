#!/usr/bin/env python3
"""
Bulk Import Modification Safeguards

This script adds validation and safety checks to prevent future bulk import
modification disasters like the one that corrupted 1,381 test files.
"""

import os
import ast
import importlib.util
import tempfile
import shutil
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime

class ImportValidationError(Exception):
    """Exception raised when import validation fails."""
    pass

class BulkImportSafeguards:
    """Safety wrapper for bulk import modifications."""
    
    def __init__(self):
        self.protected_directories = {
            'tests',
            'test_framework', 
            'netra_backend/tests',
            'auth_service/tests',
            'frontend/tests'
        }
        self.critical_files = {
            'tests/unified_test_runner.py',
            'test_framework/ssot/base_test_case.py'
        }
        
    def validate_import_works(self, import_statement: str, file_path: str = "<string>") -> bool:
        """Validate that an import statement works."""
        try:
            # Create a temporary module to test the import
            module_code = f"""
try:
    {import_statement}
    _import_test_success = True
except ImportError as e:
    _import_test_success = False
    _import_error = str(e)
"""
            
            # Compile and execute in isolated namespace
            namespace = {}
            exec(compile(module_code, file_path, 'exec'), namespace)
            
            success = namespace.get('_import_test_success', False)
            if not success:
                error = namespace.get('_import_error', 'Unknown import error')
                print(f"Import validation failed for '{import_statement}': {error}")
            
            return success
            
        except Exception as e:
            print(f"Import validation error for '{import_statement}': {e}")
            return False
    
    def analyze_file_imports(self, file_path: str) -> Dict[str, List[str]]:
        """Analyze all imports in a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=file_path)
            imports = {
                'from_imports': [],
                'direct_imports': [],
                'all_import_statements': []
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module:
                        for alias in node.names:
                            import_stmt = f"from {node.module} import {alias.name}"
                            imports['from_imports'].append(import_stmt)
                            imports['all_import_statements'].append(import_stmt)
                
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        import_stmt = f"import {alias.name}"
                        imports['direct_imports'].append(import_stmt)
                        imports['all_import_statements'].append(import_stmt)
            
            return imports
            
        except Exception as e:
            print(f"Error analyzing imports in {file_path}: {e}")
            return {'from_imports': [], 'direct_imports': [], 'all_import_statements': []}
    
    def validate_file_imports_work(self, file_path: str) -> Tuple[bool, List[str]]:
        """Validate that all imports in a file work."""
        imports = self.analyze_file_imports(file_path)
        failed_imports = []
        
        for import_stmt in imports['all_import_statements']:
            if not self.validate_import_works(import_stmt, file_path):
                failed_imports.append(import_stmt)
        
        return len(failed_imports) == 0, failed_imports
    
    def is_protected_file(self, file_path: str) -> bool:
        """Check if a file is in a protected directory or is a critical file."""
        normalized_path = file_path.replace('\\', '/').lstrip('./')
        
        # Check critical files
        if normalized_path in self.critical_files:
            return True
        
        # Check protected directories
        for protected_dir in self.protected_directories:
            if normalized_path.startswith(protected_dir + '/'):
                return True
        
        return False
    
    def create_safe_backup(self, file_path: str) -> str:
        """Create a safe backup with validation metadata."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{file_path}.safe_backup_{timestamp}"
        
        # Copy file
        shutil.copy2(file_path, backup_path)
        
        # Create metadata file
        metadata_path = f"{backup_path}.metadata"
        with open(metadata_path, 'w') as f:
            f.write(f"Original file: {file_path}\n")
            f.write(f"Backup created: {datetime.now().isoformat()}\n")
            f.write(f"Protected file: {self.is_protected_file(file_path)}\n")
            
            # Validate imports
            works, failed = self.validate_file_imports_work(file_path)
            f.write(f"Import validation: {'PASS' if works else 'FAIL'}\n")
            if failed:
                f.write(f"Failed imports: {failed}\n")
        
        return backup_path
    
    def safe_bulk_replace(self, 
                         file_paths: List[str], 
                         old_pattern: str, 
                         new_pattern: str,
                         require_approval: bool = True) -> Dict[str, any]:
        """Safely perform bulk replacements with validation."""
        
        stats = {
            'total_files': len(file_paths),
            'protected_files_skipped': 0,
            'validation_failures': 0,
            'successful_replacements': 0,
            'failed_replacements': 0,
            'backups_created': 0,
            'errors': [],
            'protected_files': [],
            'validation_failures_list': []
        }
        
        # Phase 1: Analyze files and check protection
        files_to_process = []
        for file_path in file_paths:
            if self.is_protected_file(file_path):
                stats['protected_files_skipped'] += 1
                stats['protected_files'].append(file_path)
                print(f"PROTECTED: Skipping protected file {file_path}")
            else:
                files_to_process.append(file_path)
        
        print(f"\nAnalysis complete:")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Protected files skipped: {stats['protected_files_skipped']}")
        print(f"  Files to process: {len(files_to_process)}")
        
        if require_approval and len(files_to_process) > 10:
            response = input(f"\nProceed with modifying {len(files_to_process)} files? (y/N): ")
            if response.lower() != 'y':
                print("Operation cancelled by user.")
                return stats
        
        # Phase 2: Validate current imports work
        print("\nPhase 2: Validating current imports...")
        for file_path in files_to_process[:]:  # Copy list for safe modification
            works, failed = self.validate_file_imports_work(file_path)
            if not works:
                stats['validation_failures'] += 1
                stats['validation_failures_list'].append((file_path, failed))
                files_to_process.remove(file_path)
                print(f"VALIDATION FAILED: {file_path} has broken imports: {failed}")
        
        # Phase 3: Create backups and perform replacements
        print(f"\nPhase 3: Processing {len(files_to_process)} files...")
        for file_path in files_to_process:
            try:
                # Create safe backup
                backup_path = self.create_safe_backup(file_path)
                stats['backups_created'] += 1
                
                # Read file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Perform replacement
                new_content = content.replace(old_pattern, new_pattern)
                
                if new_content != content:
                    # Write to temporary file first
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as temp_file:
                        temp_file.write(new_content)
                        temp_path = temp_file.name
                    
                    # Validate new imports work
                    works, failed = self.validate_file_imports_work(temp_path)
                    
                    if works:
                        # Replace original file
                        shutil.move(temp_path, file_path)
                        stats['successful_replacements'] += 1
                        print(f"SUCCESS: {file_path}")
                    else:
                        # Restore from backup
                        shutil.copy2(backup_path, file_path)
                        stats['failed_replacements'] += 1
                        stats['errors'].append(f"{file_path}: New imports failed validation: {failed}")
                        print(f"FAILED: {file_path} - restored from backup")
                    
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                
            except Exception as e:
                stats['failed_replacements'] += 1
                stats['errors'].append(f"{file_path}: {str(e)}")
                print(f"ERROR: {file_path}: {e}")
        
        return stats
    
    def print_summary(self, stats: Dict[str, any]):
        """Print operation summary."""
        print("\n" + "="*60)
        print("SAFE BULK REPLACEMENT SUMMARY")
        print("="*60)
        print(f"Total files analyzed: {stats['total_files']}")
        print(f"Protected files skipped: {stats['protected_files_skipped']}")
        print(f"Validation failures: {stats['validation_failures']}")
        print(f"Successful replacements: {stats['successful_replacements']}")
        print(f"Failed replacements: {stats['failed_replacements']}")
        print(f"Backups created: {stats['backups_created']}")
        
        success_rate = (stats['successful_replacements'] / 
                       max(1, stats['total_files'] - stats['protected_files_skipped'] - stats['validation_failures'])) * 100
        print(f"Success rate: {success_rate:.1f}%")
        
        if stats['errors']:
            print(f"\nErrors ({len(stats['errors'])}):")
            for error in stats['errors'][:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(stats['errors']) > 10:
                print(f"  ... and {len(stats['errors']) - 10} more")

def main():
    """Example usage of bulk import safeguards."""
    safeguards = BulkImportSafeguards()
    
    print("Bulk Import Safeguards - Example Usage")
    print("="*40)
    
    # Example: Find Python files that might need import fixes
    example_files = []
    for root, dirs, files in os.walk('.'):
        # Skip problematic directories
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.pytest_cache'}]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                example_files.append(file_path)
    
    print(f"Found {len(example_files)} Python files")
    
    # Example validation
    test_file = example_files[0] if example_files else None
    if test_file:
        print(f"\nTesting validation on: {test_file}")
        works, failed = safeguards.validate_file_imports_work(test_file)
        print(f"Import validation: {'PASS' if works else 'FAIL'}")
        if failed:
            print(f"Failed imports: {failed}")

if __name__ == '__main__':
    main()