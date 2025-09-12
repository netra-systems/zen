#!/usr/bin/env python3
"""
Comprehensive E2E Import Fixer
Fixes all known import issues in e2e tests based on actual errors found.

Business Value Justification (BVJ):
- Segment: Platform  
- Business Goal: Testing Reliability
- Value Impact: Ensures all e2e tests can load and run properly
- Strategic Impact: Prevents CI/CD failures and improves test coverage
"""

import ast
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add project root to path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComprehensiveE2EImportFixer:
    """Fix all e2e test import issues comprehensively."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.issues_fixed = 0
        self.files_fixed = []
        
    def fix_schemas_import(self, file_path: Path) -> bool:
        """Fix generic 'schemas' import issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix malformed "from schemas import" with comment in between
            pattern = r'from schemas import \(\s*\n\s*#[^\n]*\n([^)]+)\)'
            if re.search(pattern, content):
                # Extract the imports
                match = re.search(pattern, content)
                imports = match.group(1).strip()
                # Replace with proper import
                content = re.sub(pattern, 
                    'from netra_backend.app.schemas.agent import SubAgentLifecycle, SubAgentState\n'
                    'from netra_backend.app.schemas.websocket_server_messages import (\n    ' + 
                    imports.replace('SubAgentLifecycle,', '').replace('SubAgentState', '').strip() + '\n)',
                    content)
            
            # Fix simple "from schemas import"
            content = re.sub(r'^from schemas import', 'from netra_backend.app.schemas import', content, flags=re.MULTILINE)
            content = re.sub(r'^import schemas$', 'import netra_backend.app.schemas as schemas', content, flags=re.MULTILINE)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to fix schemas in {file_path}: {e}")
            return False
    
    def fix_test_helpers_imports(self, file_path: Path) -> bool:
        """Fix test helper import issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Map of wrong imports to correct ones
            replacements = [
                ('from netra_backend.tests.fixtures.llm_agent_fixtures', 'from netra_backend.tests.agents.test_fixtures'),
                ('from netra_backend.tests.test_fixtures', 'from netra_backend.tests.agents.test_fixtures'),
                ('from netra_backend.tests.model_setup_helpers', 'from netra_backend.tests.agents.test_helpers'),
                ('from netra_backend.tests.real_critical_helpers', 'from netra_backend.tests.agents.test_helpers'),
                ('from netra_backend.tests.l4_staging_critical_base', 'from netra_backend.tests.integration.critical_paths.test_base'),
            ]
            
            for old, new in replacements:
                content = content.replace(old, new)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to fix test helpers in {file_path}: {e}")
            return False
    
    def fix_websocket_imports(self, file_path: Path) -> bool:
        """Fix WebSocket-related import issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix WebSocketManager import
            content = content.replace(
                'from ws_manager import WebSocketManager',
                'from netra_backend.app.core.websocket.manager import WebSocketManager'
            )
            
            # Fix ConnectionManager import
            content = content.replace(
                'from netra_backend.app.websocket.connection_manager import ConnectionManager',
                'from netra_backend.app.core.websocket.manager import ConnectionManager'
            )
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to fix websocket imports in {file_path}: {e}")
            return False
    
    def fix_agent_schema_imports(self, file_path: Path) -> bool:
        """Fix agent-related schema imports."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix agent_requests import
            content = content.replace(
                'from netra_backend.app.schemas.agent_requests',
                'from netra_backend.app.schemas.Agent'
            )
            
            # Fix ResearchType import
            content = content.replace(
                'from netra_backend.app.services.apex_optimizer_agent.models import ResearchType',
                'from netra_backend.app.schemas.agent import ResearchType'
            )
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to fix agent schema imports in {file_path}: {e}")
            return False
    
    def fix_unified_test_imports(self, file_path: Path) -> bool:
        """Fix unified test import issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix unified test imports
            content = content.replace(
                'from tests.unified',
                'from tests.unified'
            )
            
            # Fix search filter helpers
            content = content.replace(
                'from netra_backend.search_filter_helpers',
                'from netra_backend.app.utils.search_filter'
            )
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to fix unified test imports in {file_path}: {e}")
            return False
    
    def fix_syntax_errors(self, file_path: Path) -> bool:
        """Fix syntax errors in test files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to parse and identify syntax errors
            try:
                ast.parse(content)
                return False  # No syntax errors
            except SyntaxError as e:
                logger.info(f"Found syntax error in {file_path} at line {e.lineno}: {e.msg}")
                
                # Common syntax error fixes
                lines = content.split('\n')
                if e.lineno and e.lineno <= len(lines):
                    # Check for common issues
                    problem_line = lines[e.lineno - 1]
                    
                    # Fix incomplete dictionary/list literals
                    if problem_line.strip().endswith(','):
                        # Check if next line starts a new statement
                        if e.lineno < len(lines) and not lines[e.lineno].strip().startswith((')', ']', '}')):
                            lines[e.lineno - 1] = problem_line.rstrip(',')
                    
                    # Fix incomplete function calls
                    if '(' in problem_line and ')' not in problem_line:
                        # Look for closing parenthesis in next lines
                        for i in range(e.lineno, min(e.lineno + 5, len(lines))):
                            if ')' in lines[i]:
                                break
                        else:
                            # Add closing parenthesis
                            lines[e.lineno - 1] = problem_line + ')'
                    
                    # Reconstruct content
                    fixed_content = '\n'.join(lines)
                    
                    # Verify fix
                    try:
                        ast.parse(fixed_content)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_content)
                        return True
                    except:
                        pass
                
                return False
        except Exception as e:
            logger.error(f"Failed to fix syntax errors in {file_path}: {e}")
            return False
    
    def fix_file(self, file_path: Path) -> List[str]:
        """Apply all fixes to a single file."""
        fixes_applied = []
        
        if self.fix_schemas_import(file_path):
            fixes_applied.append("Fixed schemas imports")
        
        if self.fix_test_helpers_imports(file_path):
            fixes_applied.append("Fixed test helper imports")
        
        if self.fix_websocket_imports(file_path):
            fixes_applied.append("Fixed WebSocket imports")
        
        if self.fix_agent_schema_imports(file_path):
            fixes_applied.append("Fixed agent schema imports")
        
        if self.fix_unified_test_imports(file_path):
            fixes_applied.append("Fixed unified test imports")
        
        if self.fix_syntax_errors(file_path):
            fixes_applied.append("Fixed syntax errors")
        
        return fixes_applied
    
    def fix_all_failed_tests(self) -> Dict:
        """Fix all failed e2e tests based on the import report."""
        # Load the import report
        report_path = self.project_root / 'test_reports' / 'e2e_import_report.json'
        if not report_path.exists():
            logger.error("No import report found. Run check_e2e_imports.py first.")
            return {}
        
        with open(report_path, 'r') as f:
            report = json.load(f)
        
        failed_files = report['details']['failed']
        results = {
            'total_files': len(failed_files),
            'fixed_files': [],
            'fixes_by_file': {},
            'still_broken': []
        }
        
        logger.info(f"Attempting to fix {len(failed_files)} files with import issues")
        
        for rel_path in failed_files:
            file_path = self.project_root / rel_path
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                results['still_broken'].append(str(rel_path))
                continue
            
            fixes = self.fix_file(file_path)
            if fixes:
                results['fixed_files'].append(str(rel_path))
                results['fixes_by_file'][str(rel_path)] = fixes
                logger.info(f"  [U+2713] Fixed {rel_path}:")
                for fix in fixes:
                    logger.info(f"    - {fix}")
                self.issues_fixed += len(fixes)
                self.files_fixed.append(str(rel_path))
            else:
                # Check if file still has issues
                try:
                    with open(file_path, 'r') as f:
                        ast.parse(f.read())
                    # No syntax errors, might be other import issues
                    logger.warning(f"   WARNING:  No fixes applied to {rel_path}")
                except Exception as e:
                    logger.error(f"  [U+2717] Still has issues: {rel_path}: {e}")
                    results['still_broken'].append(str(rel_path))
        
        return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Comprehensive E2E Import Fixer')
    parser.add_argument('--verify', action='store_true', help='Verify fixes after applying')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    
    args = parser.parse_args()
    
    fixer = ComprehensiveE2EImportFixer()
    
    logger.info("=" * 60)
    logger.info("COMPREHENSIVE E2E IMPORT FIXER")
    logger.info("=" * 60)
    
    results = fixer.fix_all_failed_tests()
    
    logger.info("\n" + "=" * 60)
    logger.info("FIX SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total files processed: {results['total_files']}")
    logger.info(f"Files fixed: {len(results['fixed_files'])}")
    logger.info(f"Total issues fixed: {fixer.issues_fixed}")
    logger.info(f"Still broken: {len(results['still_broken'])}")
    
    if args.report or results['still_broken']:
        # Save fix report
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_files': results['total_files'],
                'files_fixed': len(results['fixed_files']),
                'issues_fixed': fixer.issues_fixed,
                'still_broken': len(results['still_broken'])
            },
            'details': results
        }
        
        report_path = fixer.project_root / 'test_reports' / 'comprehensive_fix_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\nReport saved to: {report_path}")
    
    if args.verify:
        logger.info("\n" + "=" * 60)
        logger.info("VERIFYING FIXES")
        logger.info("=" * 60)
        
        # Re-run the import checker to verify
        os.system('python scripts/check_e2e_imports.py --report')
        
        # Load the new report
        report_path = fixer.project_root / 'test_reports' / 'e2e_import_report.json'
        if report_path.exists():
            with open(report_path, 'r') as f:
                new_report = json.load(f)
            
            logger.info(f"\nAfter fixes:")
            logger.info(f"  Successful: {len(new_report['details']['successful'])}")
            logger.info(f"  Failed: {len(new_report['details']['failed'])}")
            
            # Return non-zero if still failures
            sys.exit(1 if new_report['details']['failed'] else 0)
    
    # Return success if we fixed files
    sys.exit(0 if results['fixed_files'] else 1)


if __name__ == '__main__':
    main()