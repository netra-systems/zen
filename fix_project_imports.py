#!/usr/bin/env python3
"""
Project Import Fixer
Fixes import issues in project test files only (excludes venv/virtual environment files)
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Set

class ProjectImportFixer:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.fixes_applied = []
        self.failed_fixes = []
        
        # Known correct import mappings
        self.import_mappings = {
            # ConnectionManager patterns
            'from netra_backend.app.websocket.connection_manager import ConnectionManager': 
                'from netra_backend.app.websocket.connection import ConnectionManager',
            'from netra_backend.websocket.connection_manager import ConnectionManager':
                'from netra_backend.app.websocket.connection import ConnectionManager',
            'from websocket.connection_manager import ConnectionManager':
                'from netra_backend.app.websocket.connection import ConnectionManager',
            'from ..websocket.connection_manager import ConnectionManager':
                'from netra_backend.app.websocket.connection import ConnectionManager',
            'from ...websocket.connection_manager import ConnectionManager':
                'from netra_backend.app.websocket.connection import ConnectionManager',
                
            # Service imports
            'from services.thread_service': 'from netra_backend.app.services.thread_service',
            'from netra_backend.services.thread_service': 'from netra_backend.app.services.thread_service',
            'from ..services.thread_service': 'from netra_backend.app.services.thread_service',
            'from ...services.thread_service': 'from netra_backend.app.services.thread_service',
            
            # WebSocket Manager
            'from netra_backend.app.websocket.ws_manager': 'from netra_backend.app.ws_manager',
            'from websocket.ws_manager': 'from netra_backend.app.ws_manager',
            'from ..websocket.ws_manager': 'from netra_backend.app.ws_manager',
            
            # Agent imports
            'from agents.': 'from netra_backend.app.agents.',
            'from netra_backend.agents.': 'from netra_backend.app.agents.',
            
            # Core imports  
            'from core.': 'from netra_backend.app.core.',
            'from netra_backend.core.': 'from netra_backend.app.core.',
            
            # Schema imports
            'from schemas.': 'from netra_backend.app.schemas.',
            'from netra_backend.schemas.': 'from netra_backend.app.schemas.',
        }
        
    def is_project_file(self, file_path: Path) -> bool:
        """Check if file is part of the actual project (not venv/dependencies)"""
        path_str = str(file_path).lower()
        
        # Exclude virtual environment directories
        exclude_patterns = [
            'venv', '.venv', 'site-packages', '__pycache__',
            'node_modules', '.git', 'build', 'dist'
        ]
        
        for pattern in exclude_patterns:
            if pattern in path_str:
                return False
                
        # Only include actual project test directories
        project_test_paths = [
            'netra_backend/tests',
            'auth_service/tests', 
            'tests/e2e',
            'test_framework',
            'dev_launcher/tests'
        ]
        
        for test_path in project_test_paths:
            if test_path.replace('/', os.sep) in str(file_path):
                return True
                
        return False
    
    def load_issues(self) -> List[Dict[str, Any]]:
        """Load issues from the scan report, filtering for project files only"""
        
        try:
            with open('import_issues_report.json', 'r') as f:
                report = json.load(f)
                
            project_issues = []
            for issue in report['detailed_issues']:
                file_path = Path(issue['file'])
                if self.is_project_file(file_path):
                    project_issues.append(issue)
                    
            return project_issues
            
        except Exception as e:
            print(f"Failed to load issues report: {e}")
            return []
    
    def fix_file_imports(self, file_path: Path, issues: List[Dict[str, Any]]) -> bool:
        """Fix all import issues in a single file"""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            lines = content.split('\n')
            fixed_lines = []
            lines_fixed = []
            
            for i, line in enumerate(lines):
                line_num = i + 1
                fixed_line = line
                
                # Check if this line has an issue
                line_issues = [issue for issue in issues if issue.get('line') == line_num]
                
                for issue in line_issues:
                    if issue['issue_type'] == 'incorrect_connection_manager_import':
                        # Fix ConnectionManager imports
                        if 'from netra_backend.app.websocket.connection_manager import ConnectionManager' in line:
                            fixed_line = line.replace(
                                'from netra_backend.app.websocket.connection_manager import ConnectionManager',
                                'from netra_backend.app.websocket.connection import ConnectionManager'
                            )
                        elif 'from netra_backend.websocket.connection_manager import ConnectionManager' in line:
                            fixed_line = line.replace(
                                'from netra_backend.websocket.connection_manager import ConnectionManager',
                                'from netra_backend.app.websocket.connection import ConnectionManager'
                            )
                        elif 'from websocket.connection_manager import ConnectionManager' in line:
                            fixed_line = line.replace(
                                'from websocket.connection_manager import ConnectionManager',
                                'from netra_backend.app.websocket.connection import ConnectionManager'
                            )
                            
                    elif issue['issue_type'] == 'missing_service_prefix':
                        # Fix service imports missing netra_backend.app prefix
                        if re.search(r'from (services|websocket|agents|core|schemas)\b', line):
                            # Replace with netra_backend.app prefix
                            patterns = [
                                (r'from services\.', 'from netra_backend.app.services.'),
                                (r'from websocket\.', 'from netra_backend.app.websocket.'),
                                (r'from agents\.', 'from netra_backend.app.agents.'),
                                (r'from core\.', 'from netra_backend.app.core.'),
                                (r'from schemas\.', 'from netra_backend.app.schemas.'),
                            ]
                            
                            for pattern, replacement in patterns:
                                if re.search(pattern, line):
                                    fixed_line = re.sub(pattern, replacement, line)
                                    break
                                    
                if fixed_line != line:
                    lines_fixed.append({
                        'line_num': line_num,
                        'original': line.strip(),
                        'fixed': fixed_line.strip()
                    })
                    
                fixed_lines.append(fixed_line)
            
            # Write back if changes were made
            if lines_fixed:
                new_content = '\n'.join(fixed_lines)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                    
                self.fixes_applied.append({
                    'file': str(file_path),
                    'fixes': lines_fixed
                })
                
                print(f"Fixed {len(lines_fixed)} imports in {file_path}")
                return True
            else:
                print(f"No fixes needed for {file_path}")
                return False
                
        except Exception as e:
            self.failed_fixes.append({
                'file': str(file_path),
                'error': str(e)
            })
            print(f"Failed to fix {file_path}: {e}")
            return False
    
    def fix_all_imports(self):
        """Fix imports in all project files with issues"""
        
        issues = self.load_issues()
        if not issues:
            print("No issues found to fix")
            return
            
        print(f"Found {len(issues)} issues in project files")
        
        # Group issues by file
        issues_by_file = {}
        for issue in issues:
            file_path = issue['file']
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append(issue)
        
        print(f"Processing {len(issues_by_file)} files...")
        
        for file_path, file_issues in issues_by_file.items():
            path_obj = Path(file_path)
            if path_obj.exists():
                self.fix_file_imports(path_obj, file_issues)
            else:
                print(f"File not found: {file_path}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a report of all fixes applied"""
        
        total_fixes = sum(len(fix['fixes']) for fix in self.fixes_applied)
        
        return {
            'files_processed': len(self.fixes_applied),
            'total_fixes_applied': total_fixes,
            'failed_fixes': len(self.failed_fixes),
            'fixes_by_file': self.fixes_applied,
            'failures': self.failed_fixes,
            'summary': {
                'most_fixes_in_file': max(self.fixes_applied, key=lambda x: len(x['fixes']))['file'] if self.fixes_applied else None,
                'success_rate': len(self.fixes_applied) / (len(self.fixes_applied) + len(self.failed_fixes)) * 100 if (self.fixes_applied or self.failed_fixes) else 0
            }
        }

def main():
    root_dir = os.getcwd()
    fixer = ProjectImportFixer(root_dir)
    
    print("Starting project import fixes...")
    fixer.fix_all_imports()
    
    report = fixer.generate_report()
    
    # Save detailed report
    with open('import_fixes_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print(f"\n=== Import Fixes Summary ===")
    print(f"Files processed: {report['files_processed']}")
    print(f"Total fixes applied: {report['total_fixes_applied']}")
    print(f"Failed fixes: {report['failed_fixes']}")
    print(f"Success rate: {report['summary']['success_rate']:.1f}%")
    
    if report['fixes_by_file']:
        print(f"\nFiles fixed:")
        for fix in report['fixes_by_file']:
            print(f"  {fix['file']}: {len(fix['fixes'])} fixes")
    
    if report['failures']:
        print(f"\nFailed files:")
        for failure in report['failures']:
            print(f"  {failure['file']}: {failure['error']}")
    
    print(f"\nDetailed report saved to: import_fixes_report.json")

if __name__ == '__main__':
    main()