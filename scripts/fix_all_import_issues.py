#!/usr/bin/env python3
"""
Comprehensive Import Issue Fixer for Netra Backend
Systematically fixes all import path issues between services and agents
"""

import ast
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveImportFixer:
    """Systematically fixes all import issues between services and agents."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.fixes_applied = 0
        self.files_modified = set()
        self.import_errors: Dict[str, List[str]] = {}
        self.fix_patterns: List[Tuple[re.Pattern, str, str]] = []
        
        # Load known import errors from test reports
        self._load_import_errors()
        
        # Build comprehensive fix patterns
        self._build_fix_patterns()
    
    def _load_import_errors(self) -> None:
        """Load import errors from test results."""
        # Load from test report JSON if available
        test_report_path = PROJECT_ROOT / 'test_reports' / 'import_test_results.json'
        if test_report_path.exists():
            try:
                with open(test_report_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for module_name, result in data.get('results', {}).items():
                        if result.get('status') == 'error' and result.get('error_type') == 'ImportError':
                            error_msg = result.get('error_message', '')
                            if module_name not in self.import_errors:
                                self.import_errors[module_name] = []
                            self.import_errors[module_name].append(error_msg)
                logger.info(f"Loaded {len(self.import_errors)} import errors from test results")
            except Exception as e:
                logger.warning(f"Could not load test results: {e}")
    
    def _build_fix_patterns(self) -> None:
        """Build comprehensive fix patterns based on known issues."""
        # Pattern 1: Fix factory_status imports
        self.fix_patterns.append((
            re.compile(r'from netra_backend\.app\.services\.apex_optimizer_agent\.models import (.*?)(?:ReportResponse|MetricResponse|GenerateReportRequest)(.*?)'),
            r'from netra_backend.app.routes.factory_status.models import \1ReportResponse, MetricResponse, GenerateReportRequest\2',
            "Fix factory_status model imports"
        ))
        
        # Pattern 2: Fix missing classes from apex_optimizer_agent.models
        missing_classes = [
            'CorpusOperation', 'QualityTrend', 'MCPClientCreateRequest',
            'SubAgentUpdate', 'SubAgentLifecycle'
        ]
        for cls in missing_classes:
            self.fix_patterns.append((
                re.compile(rf'from netra_backend\.app\.services\.apex_optimizer_agent\.models import (.*?){cls}(.*?)'),
                f'# TODO: Fix import - {cls} not found in apex_optimizer_agent.models\n# \\g<0>',
                f"Comment out missing {cls} import"
            ))
        
        # Pattern 3: Fix DataSubAgentClickHouseOperations
        self.fix_patterns.append((
            re.compile(r'from netra_backend\.app\.services\.corpus\.clickhouse_operations import DataSubAgentClickHouseOperations'),
            r'from netra_backend.app.services.corpus.clickhouse_operations import ClickHouseOperations as DataSubAgentClickHouseOperations',
            "Alias ClickHouseOperations as DataSubAgentClickHouseOperations"
        ))
        
        # Pattern 4: Fix ExecutionEngine import
        self.fix_patterns.append((
            re.compile(r'from netra_backend\.app\.services\.unified_tool_registry\.execution_engine import ExecutionEngine'),
            r'from netra_backend.app.services.unified_tool_registry.tool_execution_engine import ToolExecutionEngine as ExecutionEngine',
            "Fix ExecutionEngine import path"
        ))
        
        # Pattern 5: Fix Metric import from metrics_collector
        self.fix_patterns.append((
            re.compile(r'from netra_backend\.app\.monitoring\.metrics_collector import (.*?)Metric(.*?)'),
            r'from netra_backend.app.monitoring.models import \1Metric\2',
            "Fix Metric import path"
        ))
        
        # Pattern 6: Fix ClickHouseQueryError import
        self.fix_patterns.append((
            re.compile(r'from netra_backend\.app\.core\.error_types import (.*?)ClickHouseQueryError(.*?)'),
            r'from netra_backend.app.core.exceptions import \1ClickHouseQueryError\2',
            "Fix ClickHouseQueryError import path"
        ))
        
        # Pattern 7: Fix map_content_type import
        self.fix_patterns.append((
            re.compile(r'from netra_backend\.app\.services\.quality\.quality_validators import (.*?)map_content_type(.*?)'),
            r'from netra_backend.app.services.quality.content_mappers import \1map_content_type\2',
            "Fix map_content_type import path"
        ))
        
        # Pattern 8: Fix unified_tools.schemas imports
        self.fix_patterns.append((
            re.compile(r'from netra_backend\.app\.routes\.unified_tools\.schemas import (.*?)'),
            r'from netra_backend.app.routes.unified_tools.models import \1',
            "Fix unified_tools schemas import path"
        ))
        
        # Pattern 9: Fix relative imports in value_based_corpus
        self.fix_patterns.append((
            re.compile(r'^from value_corpus_to_xml import', re.MULTILINE),
            r'from netra_backend.app.agents.corpus_admin.value_based_corpus.value_corpus_to_xml import',
            "Fix relative import in value_based_corpus"
        ))
        
        self.fix_patterns.append((
            re.compile(r'^from value_corpus_validation import', re.MULTILINE),
            r'from netra_backend.app.agents.corpus_admin.value_based_corpus.value_corpus_validation import',
            "Fix relative import in value_based_corpus"
        ))
        
        logger.info(f"Built {len(self.fix_patterns)} fix patterns")
    
    def fix_file(self, filepath: Path) -> bool:
        """Fix imports in a single file."""
        try:
            content = filepath.read_text(encoding='utf-8')
            original_content = content
            fixes_in_file = []
            
            # Apply all fix patterns
            for pattern, replacement, description in self.fix_patterns:
                matches = pattern.findall(content)
                if matches:
                    new_content = pattern.sub(replacement, content)
                    if new_content != content:
                        content = new_content
                        fixes_in_file.append(description)
                        self.fixes_applied += 1
            
            # Check if we made any changes
            if content != original_content:
                if not self.dry_run:
                    filepath.write_text(content, encoding='utf-8')
                    logger.info(f"Fixed {len(fixes_in_file)} issues in {filepath.relative_to(PROJECT_ROOT)}:")
                    for fix in fixes_in_file:
                        logger.info(f"  - {fix}")
                else:
                    logger.info(f"Would fix {len(fixes_in_file)} issues in {filepath.relative_to(PROJECT_ROOT)}")
                self.files_modified.add(str(filepath))
                return True
                
        except Exception as e:
            logger.error(f"Error fixing {filepath}: {e}")
            
        return False
    
    def fix_all_imports(self) -> Dict[str, any]:
        """Fix all import issues systematically."""
        logger.info("Starting systematic import fix...")
        logger.info(f"Found {len(self.import_errors)} modules with import errors")
        
        results = {
            'files_checked': 0,
            'files_modified': 0,
            'fixes_applied': 0,
            'errors': []
        }
        
        # Get all Python files that need fixing
        target_dirs = [
            'netra_backend/app/agents',
            'netra_backend/app/services',
            'netra_backend/app/routes',
            'netra_backend/app/core',
            'netra_backend/app/monitoring',
            'netra_backend/tests'
        ]
        
        all_files = set()
        for dir_path in target_dirs:
            full_dir = PROJECT_ROOT / dir_path
            if full_dir.exists():
                all_files.update(full_dir.rglob('*.py'))
        
        logger.info(f"Scanning {len(all_files)} Python files for import issues...")
        
        # Process all files
        for filepath in sorted(all_files):
            results['files_checked'] += 1
            if self.fix_file(filepath):
                results['files_modified'] += 1
        
        results['fixes_applied'] = self.fixes_applied
        results['modified_files'] = list(self.files_modified)
        
        return results
    
    def verify_fixes(self) -> bool:
        """Verify that imports can be resolved after fixes."""
        logger.info("Verifying import fixes...")
        
        verification_passed = True
        test_imports = [
            "netra_backend.app.main",
            "netra_backend.app.agents.supervisor.agent",
            "netra_backend.app.agents.corpus_admin.agent",
            "netra_backend.app.services.thread_service",
            "netra_backend.app.routes.factory_status"
        ]
        
        for module_path in test_imports:
            try:
                __import__(module_path)
                logger.info(f"✓ {module_path} import successful")
            except ImportError as e:
                logger.error(f"✗ {module_path} import failed: {e}")
                verification_passed = False
        
        return verification_passed
    
    def generate_report(self) -> None:
        """Generate a detailed report of import issues and fixes."""
        report_path = PROJECT_ROOT / 'test_reports' / 'import_fix_report.md'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Import Fix Report\n\n")
            f.write(f"## Summary\n\n")
            f.write(f"- Total files modified: {len(self.files_modified)}\n")
            f.write(f"- Total fixes applied: {self.fixes_applied}\n\n")
            
            if self.files_modified:
                f.write("## Modified Files\n\n")
                for file_path in sorted(self.files_modified):
                    rel_path = Path(file_path).relative_to(PROJECT_ROOT)
                    f.write(f"- {rel_path}\n")
                f.write("\n")
            
            if self.import_errors:
                f.write("## Known Import Errors\n\n")
                for module, errors in self.import_errors.items():
                    f.write(f"### {module}\n")
                    for error in errors:
                        f.write(f"- {error}\n")
                    f.write("\n")
        
        logger.info(f"Report saved to {report_path}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix all import issues in Netra Backend')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be fixed without modifying files')
    parser.add_argument('--verify', action='store_true', help='Verify fixes after applying')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    
    args = parser.parse_args()
    
    fixer = ComprehensiveImportFixer(dry_run=args.dry_run)
    results = fixer.fix_all_imports()
    
    # Print summary
    print("\n" + "="*60)
    print("IMPORT FIX SUMMARY")
    print("="*60)
    print(f"Files checked: {results['files_checked']}")
    print(f"Files modified: {results['files_modified']}")
    print(f"Fixes applied: {results['fixes_applied']}")
    
    if results['modified_files']:
        print(f"\nModified {len(results['modified_files'])} files")
        if len(results['modified_files']) <= 20:
            for file in sorted(results['modified_files'])[:20]:
                rel_path = Path(file).relative_to(PROJECT_ROOT)
                print(f"  - {rel_path}")
        else:
            print(f"  (showing first 20 of {len(results['modified_files'])} files)")
            for file in sorted(results['modified_files'])[:20]:
                rel_path = Path(file).relative_to(PROJECT_ROOT)
                print(f"  - {rel_path}")
    
    if args.report:
        fixer.generate_report()
        print("\nDetailed report saved to test_reports/import_fix_report.md")
    
    if args.verify and not args.dry_run:
        print("\nVerifying fixes...")
        if fixer.verify_fixes():
            print("✓ Core imports verified successfully!")
        else:
            print("✗ Some imports still have issues")
            sys.exit(1)
    
    if args.dry_run:
        print("\n[DRY RUN] No files were actually modified")
    
    return 0 if results['files_modified'] > 0 or args.dry_run else 1


if __name__ == '__main__':
    sys.exit(main())