from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
AUTOMATED OS.ENVIRON VIOLATIONS REMEDIATION SCRIPT

Automatically fixes os.environ violations per CLAUDE.md requirements.
This script applies systematic fixes to convert direct os.environ access 
to proper IsolatedEnvironment usage patterns.

Focus Areas:
1. Test files (bulk of violations)
2. Service configuration files
3. Scripts and utilities

Business Value: Platform/Internal - Environment Management Compliance
Automates the remediation of 2000+ violations to achieve CLAUDE.md compliance.
"""
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import shutil
from dataclasses import dataclass

@dataclass
class RemediationResult:
    """Results of remediation attempt"""
    file_path: Path
    original_violations: int
    fixed_violations: int
    errors: List[str]
    success: bool

class OSEnvironRemediator:
    """Automated remediation of os.environ violations"""
    
    # Mapping of file categories to appropriate environment imports (SSOT-compliant)
    ENV_IMPORTS = {
        'test': 'from shared.isolated_environment import get_env',
        'netra_backend': 'from shared.isolated_environment import get_env',
        'auth_service': 'from shared.isolated_environment import get_env',
        'analytics_service': 'from shared.isolated_environment import get_env',
        'dev_launcher': 'from shared.isolated_environment import get_env',
        'scripts': 'from shared.isolated_environment import get_env',
        'shared': 'from shared.isolated_environment import get_env'
    }
    
    # Patterns for os.environ usage and their replacements
    REMEDIATION_PATTERNS = [
        # os.environ['key'] -> env.get('key')
        (r"os\.environ\[(['\"])(.+?)\1\]", r"env.get('\2')"),
        
        # os.environ.get('key') -> env.get('key')
        (r"os\.environ\.get\((['\"])(.+?)\1\)", r"env.get('\2')"),
        
        # os.environ.get('key', default) -> env.get('key', default)
        (r"os\.environ\.get\((['\"])(.+?)\1,\s*(.+?)\)", r"env.get('\2', \3)"),
        
        # os.environ['key'] = 'value' -> env.set('key', 'value', 'source')
        (r"os\.environ\[(['\"])(.+?)\1\]\s*=\s*(.+)", r"env.set('\2', \3, 'test_fixture')"),
        
        # del os.environ['key'] -> env.unset('key')
        (r"del\s+os\.environ\[(['\"])(.+?)\1\]", r"env.unset('\2')"),
        
        # os.environ.pop('key') -> env.pop('key') 
        (r"os\.environ\.pop\((['\"])(.+?)\1\)", r"env.pop('\2')"),
        
        # os.environ.pop('key', default) -> env.pop('key', default)
        (r"os\.environ\.pop\((['\"])(.+?)\1,\s*(.+?)\)", r"env.pop('\2', \3)"),
        
        # os.environ.setdefault('key', default) -> env.setdefault('key', default)
        (r"os\.environ\.setdefault\((['\"])(.+?)\1,\s*(.+?)\)", r"env.setdefault('\2', \3)"),
        
        # os.environ.update(dict) -> env.update(dict)
        (r"os\.environ\.update\((.+?)\)", r"env.update(\1)")
    ]
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: List[RemediationResult] = []
        self.dry_run = False
    
    def determine_file_category(self, file_path: Path) -> str:
        """Determine which environment management category a file belongs to"""
        path_str = str(file_path).replace('\\', '/')
        
        # Test files (most common)
        if '/test' in path_str or 'test_' in file_path.name or path_str.startswith('tests/'):
            return 'test'
        
        # Service-specific files
        if '/netra_backend/' in path_str:
            return 'netra_backend'
        elif '/auth_service/' in path_str:
            return 'auth_service'
        elif '/analytics_service/' in path_str:
            return 'analytics_service'
        elif '/dev_launcher/' in path_str:
            return 'dev_launcher'
        elif '/scripts/' in path_str:
            return 'scripts'
        elif '/shared/' in path_str:
            return 'shared'
        
        # Default fallback
        return 'scripts'
    
    def add_environment_import(self, content: str, file_category: str) -> str:
        """Add appropriate environment import to file"""
        import_line = self.ENV_IMPORTS[file_category]
        
        # Check if import already exists
        if 'get_env' in content and ('isolated_environment' in content or 'environment_isolation' in content):
            return content
        
        # Find a good place to insert the import
        lines = content.split('\n')
        insert_index = 0
        
        # Look for existing imports section
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                insert_index = i + 1
            elif line.strip() == '' and insert_index > 0:
                # Found end of imports section
                break
        
        # If no imports found, add after docstrings/comments
        if insert_index == 0:
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith(('"""', "'''", '#')):
                    insert_index = i
                    break
        
        # Insert the import
        lines.insert(insert_index, import_line)
        lines.insert(insert_index + 1, '')  # Add blank line
        
        return '\n'.join(lines)
    
    def add_env_initialization(self, content: str) -> str:
        """Add env = get_env() initialization if not present"""
        if 'env = get_env()' in content or 'env=get_env()' in content:
            return content
        
        lines = content.split('\n')
        
        # Look for a good place to add initialization (after imports, before first usage)
        insert_index = len(lines)
        
        # Find the first os.environ usage
        for i, line in enumerate(lines):
            if 'os.environ' in line:
                insert_index = i
                break
        
        # Look backwards for a good insertion point (after imports/docstrings)
        for i in range(insert_index - 1, -1, -1):
            line = lines[i]
            if (line.strip().startswith(('import ', 'from ')) or 
                line.strip() == '' or 
                line.strip().startswith(('"""', "'''", '#'))):
                insert_index = i + 1
                break
        
        # Insert environment initialization
        lines.insert(insert_index, '# Initialize isolated environment')
        lines.insert(insert_index + 1, 'env = get_env()')
        lines.insert(insert_index + 2, '')
        
        return '\n'.join(lines)
    
    def apply_remediation_patterns(self, content: str) -> Tuple[str, int]:
        """Apply all remediation patterns to content"""
        fixes_applied = 0
        
        for pattern, replacement in self.REMEDIATION_PATTERNS:
            original_content = content
            content = re.sub(pattern, replacement, content)
            
            # Count fixes by comparing before/after
            fixes_applied += len(re.findall(pattern, original_content))
        
        return content, fixes_applied
    
    def remediate_file(self, file_path: Path) -> RemediationResult:
        """Remediate a single file"""
        relative_path = file_path.relative_to(self.project_root)
        
        try:
            # Read original content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                original_content = f.read()
        
            # Count original violations
            original_violations = sum(len(re.findall(pattern, original_content)) 
                                    for pattern, _ in self.REMEDIATION_PATTERNS)
            
            if original_violations == 0:
                return RemediationResult(
                    file_path=relative_path,
                    original_violations=0,
                    fixed_violations=0, 
                    errors=[],
                    success=True
                )
            
            # Determine file category and add appropriate imports
            file_category = self.determine_file_category(file_path)
            
            # Apply remediation
            content = original_content
            content = self.add_environment_import(content, file_category)
            content = self.add_env_initialization(content)
            content, fixes_applied = self.apply_remediation_patterns(content)
            
            # Write remediated content (unless dry run)
            if not self.dry_run:
                # Backup original file
                backup_path = file_path.with_suffix(file_path.suffix + '.backup')
                shutil.copy2(file_path, backup_path)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            return RemediationResult(
                file_path=relative_path,
                original_violations=original_violations,
                fixed_violations=fixes_applied,
                errors=[],
                success=True
            )
            
        except Exception as e:
            return RemediationResult(
                file_path=relative_path,
                original_violations=0,
                fixed_violations=0,
                errors=[str(e)],
                success=False
            )
    
    def remediate_all_files(self, file_list: List[Path] = None) -> None:
        """Remediate all files with violations"""
        if file_list is None:
            # Get list from violation scanner
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "scan_os_environ_violations", 
                self.project_root / "scripts" / "scan_os_environ_violations.py"
            )
            scanner_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(scanner_module)
            
            scanner = scanner_module.OSEnvironViolationScanner(self.project_root)
            scanner.scan_all_python_files()
            
            # Extract unique file paths
            file_paths = set()
            for violation in scanner.violations:
                file_paths.add(self.project_root / violation.file_path)
            file_list = list(file_paths)
        
        print(f"Remediating {len(file_list)} files with os.environ violations...")
        
        for file_path in file_list:
            result = self.remediate_file(file_path)
            self.results.append(result)
            
            if result.success:
                if result.fixed_violations > 0:
                    print(f"  OK {result.file_path}: {result.fixed_violations}/{result.original_violations} violations fixed")
            else:
                print(f"  FAIL {result.file_path}: {', '.join(result.errors)}")
    
    def generate_report(self) -> Dict:
        """Generate remediation summary report"""
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        total_original = sum(r.original_violations for r in successful)
        total_fixed = sum(r.fixed_violations for r in successful)
        
        return {
            'summary': {
                'files_processed': len(self.results),
                'files_successful': len(successful),
                'files_failed': len(failed),
                'total_original_violations': total_original,
                'total_fixed_violations': total_fixed,
                'remediation_rate': (total_fixed / total_original * 100) if total_original > 0 else 0
            },
            'failures': failed
        }
    
    def print_summary(self) -> None:
        """Print remediation summary"""
        report = self.generate_report()
        summary = report['summary']
        
        print("\n" + "="*80)
        print("OS.ENVIRON REMEDIATION SUMMARY")
        print("="*80)
        
        print(f"\nFiles processed: {summary['files_processed']}")
        print(f"Successful: {summary['files_successful']}")
        print(f"Failed: {summary['files_failed']}")
        print(f"\nViolations:")
        print(f"  Original: {summary['total_original_violations']}")
        print(f"  Fixed: {summary['total_fixed_violations']}")
        print(f"  Success rate: {summary['remediation_rate']:.1f}%")
        
        if report['failures']:
            print(f"\nFailed files:")
            for failure in report['failures'][:10]:  # Show first 10 failures
                print(f"  {failure.file_path}: {', '.join(failure.errors)}")

def main():
    """Main remediation entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == '--dry-run':
        dry_run = True
        print("DRY RUN MODE - No files will be modified")
    else:
        dry_run = False
    
    project_root = Path(__file__).parent.parent
    remediator = OSEnvironRemediator(project_root)
    remediator.dry_run = dry_run
    
    # Run remediation
    remediator.remediate_all_files()
    
    # Print summary
    remediator.print_summary()
    
    # Exit with appropriate code
    report = remediator.generate_report()
    if report['summary']['files_failed'] > 0:
        sys.exit(1)
    else:
        print(f"\nRemediation completed successfully!")
        sys.exit(0)

if __name__ == '__main__':
    main()
