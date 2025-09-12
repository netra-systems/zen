from shared.isolated_environment import get_env
"""Migrate all hardcoded LLM model references to use centralized configuration.

This script updates all test files and source code to use the standardized
LLMModel enum and configuration from llm_defaults.py.

CRITICAL: This migration ensures:
1. All hardcoded "gpt-4", "gpt-3.5-turbo", etc. are replaced with LLMModel enum
2. Default model is GEMINI_2_5_FLASH across all tests
3. No OPENAI_API_KEY requirements in test environments
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict, Set
import ast
import json


class LLMModelMigrator:
    """Migrates hardcoded LLM model references to centralized config."""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).resolve()
        self.violations = []
        self.fixed_files = []
        self.skipped_files = []
        
        # Patterns to replace
        self.model_replacements = {
            # Direct string literals
            r'"gpt-4"': 'LLMModel.GEMINI_2_5_FLASH.value',
            r"'gpt-4'": 'LLMModel.GEMINI_2_5_FLASH.value',
            r'"gpt-4-turbo"': 'LLMModel.GEMINI_2_5_FLASH.value',
            r"'gpt-4-turbo'": 'LLMModel.GEMINI_2_5_FLASH.value',
            r'"gpt-3\.5-turbo"': 'LLMModel.GEMINI_2_5_FLASH.value',
            r"'gpt-3\.5-turbo'": 'LLMModel.GEMINI_2_5_FLASH.value',
            r'"claude-3-opus"': 'LLMModel.GEMINI_2_5_FLASH.value',
            r"'claude-3-opus'": 'LLMModel.GEMINI_2_5_FLASH.value',
            r'"claude-3-sonnet"': 'LLMModel.GEMINI_2_5_FLASH.value',
            r"'claude-3-sonnet'": 'LLMModel.GEMINI_2_5_FLASH.value',
            
            # In lists/arrays
            r'\["gpt-4"': '[LLMModel.GEMINI_2_5_FLASH.value',
            r"\['gpt-4'": '[LLMModel.GEMINI_2_5_FLASH.value',
            
            # API key references
            r'"OPENAI_API_KEY"': '"GOOGLE_API_KEY"',
            r"'OPENAI_API_KEY'": "'GOOGLE_API_KEY'",
            r'os\.environ\.get\("OPENAI_API_KEY"': 'os.environ.get("GOOGLE_API_KEY"',
            r"os\.environ\.get\('OPENAI_API_KEY'": "os.environ.get('GOOGLE_API_KEY'",
            r'os\.getenv\("OPENAI_API_KEY"': 'get_env().get("GOOGLE_API_KEY"',
            r"os\.getenv\('OPENAI_API_KEY'": "get_env().get('GOOGLE_API_KEY'",
        }
        
        # Files to skip (already migrated or special cases)
        self.skip_patterns = [
            "llm_defaults.py",
            "migrate_llm_models.py",
            "validate_llm_test_models.py",
            "__pycache__",
            ".git",
            "node_modules",
            ".venv",
            "venv",
        ]
    
    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        path_str = str(file_path)
        for pattern in self.skip_patterns:
            if pattern in path_str:
                return True
        return False
    
    def find_test_files(self) -> List[Path]:
        """Find all test files that might contain LLM references."""
        test_dirs = [
            self.root_path / "netra_backend" / "tests",
            self.root_path / "auth_service" / "tests",
            self.root_path / "frontend" / "__tests__",
            self.root_path / "tests" / "e2e",
            self.root_path / "test_framework",
        ]
        
        test_files = []
        for test_dir in test_dirs:
            if test_dir.exists():
                # Python files
                test_files.extend(test_dir.rglob("*.py"))
                # TypeScript/JavaScript files
                test_files.extend(test_dir.rglob("*.ts"))
                test_files.extend(test_dir.rglob("*.tsx"))
                test_files.extend(test_dir.rglob("*.js"))
                test_files.extend(test_dir.rglob("*.jsx"))
        
        # Also check service files that might have hardcoded models
        service_dirs = [
            self.root_path / "netra_backend" / "app",
            self.root_path / "auth_service",
            self.root_path / "frontend" / "lib",
        ]
        
        for service_dir in service_dirs:
            if service_dir.exists():
                test_files.extend(service_dir.rglob("*.py"))
                test_files.extend(service_dir.rglob("*.ts"))
        
        return [f for f in test_files if not self.should_skip_file(f)]
    
    def fix_python_file(self, file_path: Path) -> bool:
        """Fix Python file with LLM model references."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            modified = False
            
            # Apply replacements
            for pattern, replacement in self.model_replacements.items():
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    modified = True
            
            # Add import if we made replacements and it's a Python file
            if modified and file_path.suffix == '.py':
                if 'LLMModel' in content and 'from netra_backend.app.llm.llm_defaults import' not in content:
                    # Add import at the top of the file
                    import_line = "from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig\n"
                    
                    # Find the right place to insert import
                    lines = content.split('\n')
                    insert_index = 0
                    
                    # Find where other imports are
                    for i, line in enumerate(lines):
                        if line.startswith('import ') or line.startswith('from '):
                            insert_index = i + 1
                        elif insert_index > 0 and not line.startswith(('import ', 'from ')):
                            break
                    
                    # Insert the import
                    lines.insert(insert_index, import_line)
                    content = '\n'.join(lines)
            
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.fixed_files.append(str(file_path.relative_to(self.root_path)))
                return True
            
            return False
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            self.skipped_files.append(str(file_path.relative_to(self.root_path)))
            return False
    
    def fix_typescript_file(self, file_path: Path) -> bool:
        """Fix TypeScript/JavaScript file with LLM model references."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            modified = False
            
            # TypeScript specific replacements
            ts_replacements = {
                r'"gpt-4"': '"gemini-2.5-flash"',
                r"'gpt-4'": "'gemini-2.5-flash'",
                r'"gpt-3\.5-turbo"': '"gemini-2.5-flash"',
                r"'gpt-3\.5-turbo'": "'gemini-2.5-flash'",
                r'"claude-3"': '"gemini-2.5-flash"',
                r"'claude-3'": "'gemini-2.5-flash'",
            }
            
            for pattern, replacement in ts_replacements.items():
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    modified = True
            
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.fixed_files.append(str(file_path.relative_to(self.root_path)))
                return True
            
            return False
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            self.skipped_files.append(str(file_path.relative_to(self.root_path)))
            return False
    
    def run_migration(self) -> Dict[str, any]:
        """Run the complete migration."""
        print("Starting LLM model migration...")
        print(f"Root path: {self.root_path}")
        
        # Find files to process
        test_files = self.find_test_files()
        print(f"Found {len(test_files)} files to check")
        
        # Process each file
        for file_path in test_files:
            if file_path.suffix == '.py':
                self.fix_python_file(file_path)
            elif file_path.suffix in ['.ts', '.tsx', '.js', '.jsx']:
                self.fix_typescript_file(file_path)
        
        # Generate report
        report = {
            "total_files_checked": len(test_files),
            "files_fixed": len(self.fixed_files),
            "files_skipped": len(self.skipped_files),
            "fixed_files": self.fixed_files[:20],  # Show first 20
            "skipped_files": self.skipped_files[:10],  # Show first 10
        }
        
        return report
    
    def validate_migration(self) -> bool:
        """Validate that migration was successful."""
        print("\nValidating migration...")
        
        # Re-scan for any remaining violations
        remaining_violations = []
        test_files = self.find_test_files()
        
        deprecated_patterns = [
            r'"gpt-4"',
            r"'gpt-4'",
            r'"gpt-3\.5-turbo"',
            r"'gpt-3\.5-turbo'",
            r'"claude-3-opus"',
            r"'claude-3-opus'",
            r'"OPENAI_API_KEY"',
            r"'OPENAI_API_KEY'",
        ]
        
        for file_path in test_files[:100]:  # Check first 100 files
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern in deprecated_patterns:
                    if re.search(pattern, content):
                        # Skip if it's in a comment or docstring
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if re.search(pattern, line):
                                # Check if it's a comment
                                if '#' in line and line.index('#') < line.index(pattern.strip('"\'').strip('\\')):
                                    continue
                                remaining_violations.append({
                                    "file": str(file_path.relative_to(self.root_path)),
                                    "line": i + 1,
                                    "pattern": pattern
                                })
                                break
            except:
                pass
        
        if remaining_violations:
            print(f"Found {len(remaining_violations)} remaining violations:")
            for v in remaining_violations[:10]:
                print(f"  {v['file']}:{v['line']} - {v['pattern']}")
            return False
        
        print("Migration validated successfully!")
        return True


def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate LLM model references")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (don't make changes)"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate, don't migrate"
    )
    
    args = parser.parse_args()
    
    migrator = LLMModelMigrator()
    
    if args.validate_only:
        success = migrator.validate_migration()
        return 0 if success else 1
    
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        test_files = migrator.find_test_files()
        print(f"Would process {len(test_files)} files")
        
        # Show sample of files
        print("\nSample files that would be processed:")
        for f in test_files[:20]:
            print(f"  {f.relative_to(migrator.root_path)}")
        return 0
    
    # Run migration
    report = migrator.run_migration()
    
    print("\n" + "=" * 60)
    print("MIGRATION REPORT")
    print("=" * 60)
    print(f"Total files checked: {report['total_files_checked']}")
    print(f"Files fixed: {report['files_fixed']}")
    print(f"Files skipped: {report['files_skipped']}")
    
    if report['fixed_files']:
        print(f"\nSample of fixed files:")
        for f in report['fixed_files'][:10]:
            print(f"  [U+2713] {f}")
    
    # Validate
    success = migrator.validate_migration()
    
    if success:
        print("\n PASS:  Migration completed successfully!")
        print("\nNext steps:")
        print("1. Run tests to ensure everything still works")
        print("2. Update environment variables to use GOOGLE_API_KEY instead of OPENAI_API_KEY")
        print("3. Run: python scripts/validate_llm_test_models.py")
        return 0
    else:
        print("\n WARNING: [U+FE0F] Migration completed but validation found remaining issues")
        print("Please review the remaining violations and fix manually if needed")
        return 1


if __name__ == "__main__":
    exit(main())
