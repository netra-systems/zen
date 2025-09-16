#!/usr/bin/env python3
"""
Automated migration from DeepAgentState to UserExecutionContext.

This script addresses Phase 2 of the unit test remediation plan by:
1. Finding all deprecated DeepAgentState imports
2. Replacing with approved SSOT imports
3. Converting deprecated usage patterns to UserExecutionContext
4. Fixing non-existent method calls

Business Value: Platform/Internal - Security & SSOT Compliance
Prevents user data leakage through deprecated global shared state patterns.
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Set

class DeepAgentStateMigrator:
    """Migrates DeepAgentState usage to UserExecutionContext SSOT patterns."""
    
    FORBIDDEN_IMPORTS = [
        r'from netra_backend\.app\.agents\.state import.*DeepAgentState',
        r'from netra_backend\.app\.agents\.state import DeepAgentState',
        r'import.*DeepAgentState.*from.*agents\.state'
    ]
    
    APPROVED_IMPORTS = [
        'from netra_backend.app.schemas.agent_models import DeepAgentState',
        'from netra_backend.app.core.user_execution_context import UserExecutionContext'
    ]
    
    def __init__(self):
        self.migration_stats = {
            'files_processed': 0,
            'files_changed': 0,
            'forbidden_imports_fixed': 0,
            'deprecated_usage_fixed': 0,
            'method_calls_fixed': 0
        }
    
    def migrate_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Migrate a single file from DeepAgentState to UserExecutionContext."""
        if not file_path.exists():
            return False, [f"File not found: {file_path}"]
            
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            return False, [f"Unable to read file (encoding issue): {file_path}"]
            
        original_content = content
        changes = []
        
        # 1. Fix forbidden imports
        for pattern in self.FORBIDDEN_IMPORTS:
            if re.search(pattern, content):
                # Replace with approved SSOT import
                content = re.sub(
                    pattern,
                    'from netra_backend.app.schemas.agent_models import DeepAgentState',
                    content
                )
                changes.append(f"Fixed forbidden import: {pattern}")
                self.migration_stats['forbidden_imports_fixed'] += 1
                
        # 2. Replace DeepAgentState instantiation with UserExecutionContext
        deprecated_usage = re.findall(r'DeepAgentState\([^)]*\)', content)
        for usage in deprecated_usage:
            # Convert to UserExecutionContext pattern
            replacement = self._convert_to_user_context(usage)
            content = content.replace(usage, replacement)
            changes.append(f"Migrated instantiation: {usage} -> {replacement}")
            self.migration_stats['deprecated_usage_fixed'] += 1
            
        # 3. Fix method calls that don't exist
        # Replace .set_agent_output() with proper field assignment
        method_fixes = re.findall(r'(\w+)\.set_agent_output\(([^)]+)\)', content)
        for var_name, output_value in method_fixes:
            old_call = f'{var_name}.set_agent_output({output_value})'
            new_call = f'{var_name}.triage_result = {output_value}'
            content = content.replace(old_call, new_call)
            changes.append(f"Fixed method call: {old_call} -> {new_call}")
            self.migration_stats['method_calls_fixed'] += 1
        
        # 4. Add UserExecutionContext import if needed
        if 'UserExecutionContext' in content and 'from netra_backend.app.core.user_execution_context import UserExecutionContext' not in content:
            # Add import at top
            lines = content.split('\n')
            import_line = 'from netra_backend.app.core.user_execution_context import UserExecutionContext'
            
            # Find good place to insert (after other imports)
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('from ') or line.startswith('import '):
                    insert_idx = i + 1
                    
            lines.insert(insert_idx, import_line)
            content = '\n'.join(lines)
            changes.append("Added UserExecutionContext import")
            
        # Write back if changed
        if content != original_content:
            try:
                file_path.write_text(content, encoding='utf-8')
                self.migration_stats['files_changed'] += 1
                return True, changes
            except Exception as e:
                return False, [f"Failed to write file: {e}"]
        else:
            return False, []
            
    def _convert_to_user_context(self, deep_agent_state_usage: str) -> str:
        """Convert DeepAgentState usage to UserExecutionContext."""
        # Extract parameters from DeepAgentState(...)
        params_match = re.search(r'DeepAgentState\(([^)]*)\)', deep_agent_state_usage)
        if not params_match:
            return deep_agent_state_usage
            
        params = params_match.group(1)
        
        # Convert to UserExecutionContext pattern
        return f'UserExecutionContext.create_isolated_context(user_id="test_user", {params})'
        
    def scan_and_migrate_directory(self, directory: Path) -> Dict[str, List[str]]:
        """Scan directory and migrate all files with DeepAgentState violations."""
        results = {}
        
        if not directory.exists():
            print(f"Warning: Directory {directory} does not exist")
            return results
        
        for file_path in directory.rglob("*.py"):
            self.migration_stats['files_processed'] += 1
            
            if self._should_migrate_file(file_path):
                migrated, changes = self.migrate_file(file_path)
                if migrated:
                    results[str(file_path)] = changes
                    
        return results
        
    def _should_migrate_file(self, file_path: Path) -> bool:
        """Check if file needs migration."""
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            return False
        
        # Check for forbidden imports
        for pattern in self.FORBIDDEN_IMPORTS:
            if re.search(pattern, content):
                return True
                
        # Check for deprecated usage patterns
        if re.search(r'\.set_agent_output\(', content):
            return True
            
        return False
    
    def verify_no_violations(self, directories: List[Path]) -> Tuple[bool, List[str]]:
        """Verify no DeepAgentState violations remain in specified directories."""
        violations = []
        
        for directory in directories:
            if not directory.exists():
                continue
                
            for file_path in directory.rglob("*.py"):
                try:
                    content = file_path.read_text(encoding='utf-8')
                except UnicodeDecodeError:
                    continue
                
                # Check for forbidden imports
                for pattern in self.FORBIDDEN_IMPORTS:
                    if re.search(pattern, content):
                        violations.append(f"{file_path}: Forbidden import pattern: {pattern}")
                
                # Check for deprecated method calls
                if re.search(r'\.set_agent_output\(', content):
                    violations.append(f"{file_path}: Deprecated method call: .set_agent_output()")
        
        return len(violations) == 0, violations
    
    def print_migration_report(self):
        """Print a comprehensive migration report."""
        print("=" * 60)
        print("DEEPAGENTSTATE MIGRATION REPORT")
        print("=" * 60)
        print(f"Files Processed: {self.migration_stats['files_processed']}")
        print(f"Files Changed: {self.migration_stats['files_changed']}")
        print(f"Forbidden Imports Fixed: {self.migration_stats['forbidden_imports_fixed']}")
        print(f"Deprecated Usage Fixed: {self.migration_stats['deprecated_usage_fixed']}")
        print(f"Method Calls Fixed: {self.migration_stats['method_calls_fixed']}")
        print("=" * 60)

def main():
    """Main migration execution function."""
    migrator = DeepAgentStateMigrator()
    
    # Define directories to migrate
    test_dirs = [
        Path("tests/unit"),
        Path("netra_backend/tests/unit"),
        Path("netra_backend/tests/core"),
        Path("test_framework/tests")
    ]
    
    print("🔄 Starting DeepAgentState to UserExecutionContext migration...")
    print(f"Target directories: {[str(d) for d in test_dirs if d.exists()]}")
    
    all_results = {}
    for test_dir in test_dirs:
        if test_dir.exists():
            print(f"\n📁 Processing directory: {test_dir}")
            results = migrator.scan_and_migrate_directory(test_dir)
            all_results.update(results)
        else:
            print(f"⚠️  Directory not found: {test_dir}")
            
    # Print results
    print(f"\n✅ Migration completed!")
    print(f"📊 Migrated {len(all_results)} files")
    
    for file_path, changes in all_results.items():
        print(f"\n📁 {file_path}")
        for change in changes:
            print(f"    ✓ {change}")
    
    # Print comprehensive report
    migrator.print_migration_report()
    
    # Verify no violations remain
    print("\n🔍 Verifying no violations remain...")
    clean, remaining_violations = migrator.verify_no_violations(test_dirs)
    
    if clean:
        print("✅ No DeepAgentState violations found - migration successful!")
        return 0
    else:
        print(f"❌ {len(remaining_violations)} violations still exist:")
        for violation in remaining_violations:
            print(f"  - {violation}")
        return 1

if __name__ == "__main__":
    sys.exit(main())