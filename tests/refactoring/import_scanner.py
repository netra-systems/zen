"""
Import Scanner for Legacy Code Detection
=========================================
CRITICAL: Scans entire codebase to find and report ALL legacy imports.
Ensures no references to removed legacy files remain after refactoring.
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import datetime
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

class LegacyImportScanner:
    """Comprehensive scanner for legacy imports in the codebase."""
    
    def __init__(self):
        self.project_root = project_root
        self.scan_timestamp = datetime.now()
        
        # Legacy modules that should NOT be imported anywhere
        self.legacy_modules = {
            # Factory violations
            'agent_instance_factory_optimized',
            'agent_instance_factory_legacy',
            'agent_instance_factory_old',
            'agent_factory_v1',
            'agent_factory_v2',
            
            # Agent violations  
            'agent_core_legacy',
            'agent_legacy_massive',
            'data_agent_old',
            'data_sub_agent_legacy',
            'optimization_agent_legacy',
            'analysis_agent_old',
            'legacy_analyzer',
            'research_agent_v1',
            'old_research',
            
            # Tool dispatcher violations
            'tool_dispatcher_core',
            'request_scoped_tool_dispatcher',
            'modernized_wrapper',
            'tool_dispatcher_legacy',
            'tool_executor_old',
            
            # Execution engine violations
            'execution_engine_legacy',
            'execution_engine_v1',
            'execution_engine_old',
            'enhanced_tool_execution_legacy',
            
            # Infrastructure violations
            'legacy_managers',
            'old_session_manager',
            'duplicate_id_generator',
            'session_manager_v1',
            'context_manager_legacy',
            
            # WebSocket violations
            'websocket_manager_old',
            'legacy_event_handler',
            'ws_manager_v1'
        }
        
        # Legacy import patterns (regex)
        self.legacy_patterns = [
            # Direct imports
            r'from\s+[\w.]*agent_instance_factory_optimized',
            r'from\s+[\w.]*agent_instance_factory_legacy',
            r'from\s+[\w.]*agent_core_legacy',
            r'from\s+[\w.]*agent_legacy_massive',
            r'from\s+[\w.]*tool_dispatcher_core',
            r'from\s+[\w.]*request_scoped_tool_dispatcher',
            r'import\s+[\w.]*agent_instance_factory_optimized',
            r'import\s+[\w.]*agent_core_legacy',
            
            # Relative imports
            r'from\s+\.+[\w.]*legacy',
            r'from\s+\.+[\w.]*_old\b',
            r'from\s+\.+[\w.]*_v1\b',
            r'from\s+\.+[\w.]*_v2\b',
            
            # String references (dynamic imports)
            r'["\']agent_instance_factory_optimized["\']',
            r'["\']agent_core_legacy["\']',
            r'["\']tool_dispatcher_core["\']'
        ]
        
        self.violations = []
        self.scanned_files = []
        self.error_files = []
        
    def scan_file_ast(self, file_path: Path) -> List[Dict]:
        """Use AST to find import violations in a Python file."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                # Check Import nodes
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        if any(legacy in module_name for legacy in self.legacy_modules):
                            violations.append({
                                'type': 'import',
                                'module': module_name,
                                'line': node.lineno,
                                'col': node.col_offset
                            })
                            
                # Check ImportFrom nodes
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    if any(legacy in module for legacy in self.legacy_modules):
                        violations.append({
                            'type': 'from_import',
                            'module': module,
                            'line': node.lineno,
                            'col': node.col_offset,
                            'names': [alias.name for alias in node.names]
                        })
                        
                # Check for string literals that might be dynamic imports
                elif isinstance(node, ast.Str):
                    if any(legacy in node.s for legacy in self.legacy_modules):
                        violations.append({
                            'type': 'string_reference',
                            'content': node.s,
                            'line': node.lineno,
                            'col': node.col_offset
                        })
                        
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            self.error_files.append(str(file_path))
        except Exception as e:
            logger.error(f"Error scanning {file_path}: {e}")
            self.error_files.append(str(file_path))
            
        return violations
        
    def scan_file_regex(self, file_path: Path) -> List[Dict]:
        """Use regex to find import violations (catches more edge cases)."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                for pattern in self.legacy_patterns:
                    match = re.search(pattern, line)
                    if match:
                        violations.append({
                            'type': 'regex_match',
                            'pattern': pattern,
                            'line': line_num,
                            'content': line.strip(),
                            'match': match.group()
                        })
                        
        except Exception as e:
            logger.error(f"Error scanning {file_path} with regex: {e}")
            
        return violations
        
    def scan_directory(self, directory: Path, exclude_dirs: Set[str] = None) -> Dict[str, Any]:
        """Scan a directory recursively for legacy imports."""
        if exclude_dirs is None:
            exclude_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'backups'}
            
        results = {
            'directory': str(directory),
            'files_scanned': 0,
            'violations_found': 0,
            'violations_by_file': {}
        }
        
        for py_file in directory.rglob('*.py'):
            # Skip excluded directories
            if any(excluded in py_file.parts for excluded in exclude_dirs):
                continue
                
            relative_path = py_file.relative_to(self.project_root)
            self.scanned_files.append(str(relative_path))
            results['files_scanned'] += 1
            
            # Scan with both AST and regex
            ast_violations = self.scan_file_ast(py_file)
            regex_violations = self.scan_file_regex(py_file)
            
            # Combine and deduplicate
            all_violations = ast_violations + regex_violations
            
            if all_violations:
                results['violations_by_file'][str(relative_path)] = all_violations
                results['violations_found'] += len(all_violations)
                
                # Add to global violations list
                for violation in all_violations:
                    self.violations.append({
                        'file': str(relative_path),
                        **violation
                    })
                    
        return results
        
    def scan_entire_codebase(self) -> Dict[str, Any]:
        """Scan the entire codebase for legacy imports."""
        logger.info("="*80)
        logger.info("SCANNING CODEBASE FOR LEGACY IMPORTS")
        logger.info("="*80)
        
        # Directories to scan
        scan_dirs = [
            'netra_backend',
            'auth_service',
            'frontend',
            'shared',
            'tests'
        ]
        
        all_results = {
            'scan_timestamp': self.scan_timestamp.isoformat(),
            'total_files_scanned': 0,
            'total_violations': 0,
            'violations_by_directory': {},
            'error_files': [],
            'summary': {}
        }
        
        for dir_name in scan_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                logger.info(f"\nScanning {dir_name}/...")
                results = self.scan_directory(dir_path)
                
                all_results['violations_by_directory'][dir_name] = results
                all_results['total_files_scanned'] += results['files_scanned']
                all_results['total_violations'] += results['violations_found']
                
                logger.info(f"  Files scanned: {results['files_scanned']}")
                logger.info(f"  Violations found: {results['violations_found']}")
                
        all_results['error_files'] = self.error_files
        
        # Generate summary
        all_results['summary'] = self.generate_summary()
        
        return all_results
        
    def generate_summary(self) -> Dict[str, Any]:
        """Generate a summary of all violations found."""
        summary = {
            'total_violations': len(self.violations),
            'unique_files_with_violations': len(set(v['file'] for v in self.violations)),
            'violation_types': {},
            'most_common_legacy_modules': {},
            'critical_violations': []
        }
        
        # Count violation types
        for violation in self.violations:
            vtype = violation.get('type', 'unknown')
            summary['violation_types'][vtype] = summary['violation_types'].get(vtype, 0) + 1
            
            # Track module references
            module = violation.get('module') or violation.get('match', '')
            for legacy_module in self.legacy_modules:
                if legacy_module in module:
                    summary['most_common_legacy_modules'][legacy_module] = \
                        summary['most_common_legacy_modules'].get(legacy_module, 0) + 1
                        
        # Identify critical violations (in production code vs tests)
        for violation in self.violations:
            if not violation['file'].startswith('tests/'):
                summary['critical_violations'].append(violation)
                
        return summary
        
    def generate_fix_script(self) -> List[Dict[str, str]]:
        """Generate automated fix suggestions for each violation."""
        fixes = []
        
        # Map legacy modules to their correct replacements
        replacement_map = {
            'agent_instance_factory_optimized': 'netra_backend.app.agents.agent_instance_factory',
            'agent_instance_factory_legacy': 'netra_backend.app.agents.agent_instance_factory',
            'agent_core_legacy': 'netra_backend.app.agents.data_sub_agent.agent',
            'tool_dispatcher_core': 'netra_backend.app.agents.tool_dispatcher',
            'request_scoped_tool_dispatcher': 'netra_backend.app.agents.tool_dispatcher',
            'execution_engine_legacy': 'netra_backend.app.agents.supervisor.execution_engine',
            'execution_engine_old': 'netra_backend.app.agents.supervisor.execution_engine'
        }
        
        processed_files = set()
        
        for violation in self.violations:
            file_path = violation['file']
            
            if file_path not in processed_files:
                processed_files.add(file_path)
                
                # Find appropriate replacement
                for old_module, new_module in replacement_map.items():
                    if old_module in str(violation.get('module', '')) or \
                       old_module in str(violation.get('match', '')):
                        fixes.append({
                            'file': file_path,
                            'old_import': violation.get('content', violation.get('module', '')),
                            'new_import': f"from {new_module} import ...",
                            'line': violation.get('line', 0)
                        })
                        break
                        
        return fixes
        
    def save_report(self, output_dir: Optional[Path] = None) -> Path:
        """Save comprehensive scan report."""
        if output_dir is None:
            output_dir = self.project_root / 'tests/refactoring'
            
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate comprehensive report
        report = {
            'scan_timestamp': self.scan_timestamp.isoformat(),
            'scan_results': self.scan_entire_codebase(),
            'all_violations': self.violations,
            'fix_suggestions': self.generate_fix_script()
        }
        
        # Save JSON report
        report_file = output_dir / f'import_scan_report_{self.scan_timestamp:%Y%m%d_%H%M%S}.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"\nReport saved to: {report_file}")
        
        # Also save a quick-fix script
        fix_script = output_dir / f'import_fixes_{self.scan_timestamp:%Y%m%d_%H%M%S}.txt'
        with open(fix_script, 'w') as f:
            f.write("# Import Fix Suggestions\n")
            f.write("# " + "="*78 + "\n\n")
            
            for fix in report['fix_suggestions'][:50]:  # First 50 fixes
                f.write(f"# File: {fix['file']}, Line: {fix['line']}\n")
                f.write(f"# OLD: {fix['old_import']}\n")
                f.write(f"# NEW: {fix['new_import']}\n\n")
                
        logger.info(f"Fix script saved to: {fix_script}")
        
        return report_file
        
    def validate_clean(self) -> bool:
        """Validate that the codebase is clean of legacy imports."""
        results = self.scan_entire_codebase()
        
        is_clean = results['total_violations'] == 0
        
        if is_clean:
            logger.success("[U+2713] Codebase is CLEAN - no legacy imports found!")
        else:
            logger.error(f"[U+2717] Codebase has {results['total_violations']} legacy import violations")
            
            # Show top violations
            summary = results['summary']
            if summary['critical_violations']:
                logger.error(f"\nCritical violations in production code: {len(summary['critical_violations'])}")
                for violation in summary['critical_violations'][:5]:
                    logger.error(f"  {violation['file']}:{violation.get('line', '?')} - {violation.get('module', violation.get('match', ''))}")
                    
        return is_clean


def main():
    """Main entry point for import scanning."""
    scanner = LegacyImportScanner()
    
    # Run comprehensive scan
    logger.info("Starting comprehensive import scan...")
    report_file = scanner.save_report()
    
    # Validate if clean
    is_clean = scanner.validate_clean()
    
    if not is_clean:
        logger.warning("\nRun the generated fix script to update imports")
        logger.warning("Then re-run this scanner to verify all violations are resolved")
        
    return is_clean


if __name__ == "__main__":
    sys.exit(0 if main() else 1)