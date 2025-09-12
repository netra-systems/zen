"""
Legacy File Tracking and Removal System
========================================
CRITICAL: Tracks and verifies removal of ALL legacy files during SSOT refactoring.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import datetime
import json
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

class LegacyFileTracker:
    """Comprehensive tracking of legacy files to be removed."""
    
    def __init__(self):
        self.project_root = project_root
        self.tracking_start = datetime.now()
        
        # COMPREHENSIVE list of legacy files from SSOT violations
        self.legacy_files = {
            'factory_duplicates': [
                'netra_backend/app/agents/agent_instance_factory_optimized.py',
                'netra_backend/app/agents/agent_instance_factory_legacy.py',
                'netra_backend/app/agents/agent_instance_factory_old.py',
                'netra_backend/app/agents/agent_factory_v1.py',
                'netra_backend/app/agents/agent_factory_v2.py'
            ],
            'agent_duplicates': [
                # Data agent duplicates
                'netra_backend/app/agents/data_sub_agent/agent_core_legacy.py',
                'netra_backend/app/agents/data_sub_agent/agent_legacy_massive.py',
                'netra_backend/app/agents/data_sub_agent/data_agent_old.py',
                'netra_backend/app/agents/data_sub_agent_legacy.py',
                
                # Optimization agent duplicates
                'netra_backend/app/agents/optimization_sub_agent/optimization_agent_legacy.py',
                'netra_backend/app/agents/optimization_sub_agent/agent_legacy.py',
                
                # Analysis agent duplicates
                'netra_backend/app/agents/analysis_sub_agent/analysis_agent_old.py',
                'netra_backend/app/agents/analysis_sub_agent/legacy_analyzer.py',
                
                # Research agent duplicates
                'netra_backend/app/agents/research_sub_agent/research_agent_v1.py',
                'netra_backend/app/agents/research_sub_agent/old_research.py'
            ],
            'tool_dispatcher_duplicates': [
                'netra_backend/app/agents/tool_dispatcher_core.py',
                'netra_backend/app/agents/request_scoped_tool_dispatcher.py',
                'netra_backend/app/agents/admin_tool_dispatcher/modernized_wrapper.py',
                'netra_backend/app/agents/tool_dispatcher_legacy.py',
                'netra_backend/app/agents/tool_executor_old.py'
            ],
            'execution_engine_duplicates': [
                'netra_backend/app/agents/execution_engine_legacy.py',
                'netra_backend/app/agents/execution_engine_v1.py',
                'netra_backend/app/agents/supervisor/execution_engine_old.py',
                'netra_backend/app/agents/enhanced_tool_execution_legacy.py'
            ],
            'infrastructure_duplicates': [
                'netra_backend/app/infrastructure/legacy_managers/',
                'netra_backend/app/infrastructure/old_session_manager.py',
                'netra_backend/app/infrastructure/duplicate_id_generator.py',
                'netra_backend/app/infrastructure/session_manager_v1.py',
                'netra_backend/app/infrastructure/context_manager_legacy.py'
            ],
            'websocket_duplicates': [
                'netra_backend/app/websocket_core/websocket_manager_old.py',
                'netra_backend/app/websocket_core/legacy_event_handler.py',
                'netra_backend/app/websocket_core/ws_manager_v1.py'
            ],
            'test_duplicates': [
                'tests/legacy/',
                'tests/old_integration/',
                'tests/deprecated/',
                'tests/test_agent_factory_old.py',
                'tests/test_execution_legacy.py'
            ]
        }
        
        # Files to backup before deletion (critical ones)
        self.files_to_backup = [
            'netra_backend/app/agents/agent_instance_factory_optimized.py',
            'netra_backend/app/agents/data_sub_agent/agent_core_legacy.py'
        ]
        
        self.removal_log = []
        self.backup_dir = project_root / 'backups' / f'legacy_backup_{datetime.now():%Y%m%d_%H%M%S}'
        
    def scan_for_legacy_files(self) -> Dict[str, List[str]]:
        """Scan and identify all legacy files that exist."""
        existing_legacy = {}
        
        for category, files in self.legacy_files.items():
            existing = []
            for file_path in files:
                full_path = self.project_root / file_path
                
                if full_path.exists():
                    if full_path.is_file():
                        existing.append(str(file_path))
                        logger.warning(f"Legacy file exists: {file_path}")
                    elif full_path.is_dir():
                        # Count Python files in legacy directory
                        py_files = list(full_path.glob('**/*.py'))
                        if py_files:
                            existing.append(f"{file_path} ({len(py_files)} files)")
                            logger.warning(f"Legacy directory exists: {file_path} with {len(py_files)} Python files")
                            
            if existing:
                existing_legacy[category] = existing
                
        return existing_legacy
        
    def backup_critical_files(self) -> List[str]:
        """Backup critical legacy files before deletion."""
        backed_up = []
        
        logger.info(f"Creating backup directory: {self.backup_dir}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path in self.files_to_backup:
            full_path = self.project_root / file_path
            
            if full_path.exists() and full_path.is_file():
                backup_path = self.backup_dir / file_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                
                try:
                    shutil.copy2(full_path, backup_path)
                    backed_up.append(str(file_path))
                    logger.info(f"Backed up: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to backup {file_path}: {e}")
                    
        return backed_up
        
    def remove_legacy_file(self, file_path: str, dry_run: bool = True) -> bool:
        """Remove a legacy file with logging."""
        full_path = self.project_root / file_path
        
        if not full_path.exists():
            logger.info(f"Already removed: {file_path}")
            return True
            
        if dry_run:
            logger.info(f"[DRY RUN] Would remove: {file_path}")
            return False
            
        try:
            if full_path.is_file():
                full_path.unlink()
                logger.success(f"Removed file: {file_path}")
            elif full_path.is_dir():
                shutil.rmtree(full_path)
                logger.success(f"Removed directory: {file_path}")
                
            self.removal_log.append({
                'file': file_path,
                'timestamp': datetime.now().isoformat(),
                'success': True
            })
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove {file_path}: {e}")
            self.removal_log.append({
                'file': file_path,
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'error': str(e)
            })
            return False
            
    def remove_all_legacy_files(self, dry_run: bool = True) -> Dict[str, Any]:
        """Remove all tracked legacy files."""
        logger.info("="*80)
        logger.info(f"LEGACY FILE REMOVAL {'[DRY RUN]' if dry_run else '[EXECUTING]'}")
        logger.info("="*80)
        
        # First backup critical files if not dry run
        backed_up = []
        if not dry_run:
            backed_up = self.backup_critical_files()
            
        # Scan for existing legacy files
        existing_legacy = self.scan_for_legacy_files()
        
        # Remove files
        removed = []
        failed = []
        
        for category, files in existing_legacy.items():
            logger.info(f"\nProcessing category: {category}")
            
            for file_entry in files:
                # Handle directory entries with file count
                if '(' in file_entry:
                    file_path = file_entry.split('(')[0].strip()
                else:
                    file_path = file_entry
                    
                if self.remove_legacy_file(file_path, dry_run):
                    removed.append(file_path)
                else:
                    if not dry_run:
                        failed.append(file_path)
                        
        # Generate report
        report = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'backed_up_files': backed_up,
            'total_legacy_identified': sum(len(files) for files in existing_legacy.values()),
            'categories': existing_legacy,
            'removed': removed,
            'failed': failed,
            'removal_log': self.removal_log
        }
        
        # Save report
        report_file = self.project_root / f'tests/refactoring/legacy_removal_report_{datetime.now():%Y%m%d_%H%M%S}.json'
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"\nReport saved to: {report_file}")
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("REMOVAL SUMMARY")
        logger.info("="*80)
        logger.info(f"Total legacy files found: {report['total_legacy_identified']}")
        if dry_run:
            logger.info(f"Files that would be removed: {len(removed)}")
            logger.info("Run with dry_run=False to actually remove files")
        else:
            logger.success(f"Files removed: {len(removed)}")
            if failed:
                logger.error(f"Files failed to remove: {len(failed)}")
                for f in failed:
                    logger.error(f"  - {f}")
                    
        return report
        
    def verify_removal(self) -> Dict[str, Any]:
        """Verify all legacy files have been removed."""
        remaining = self.scan_for_legacy_files()
        
        verification = {
            'timestamp': datetime.now().isoformat(),
            'all_removed': len(remaining) == 0,
            'remaining_categories': list(remaining.keys()),
            'remaining_files': remaining,
            'total_remaining': sum(len(files) for files in remaining.values())
        }
        
        if verification['all_removed']:
            logger.success("[U+2713] All legacy files successfully removed!")
        else:
            logger.error(f"[U+2717] {verification['total_remaining']} legacy files still remain")
            
        return verification
        
    def generate_git_commands(self) -> List[str]:
        """Generate git commands to remove legacy files from repository."""
        commands = []
        
        existing = self.scan_for_legacy_files()
        
        for category, files in existing.items():
            for file_entry in files:
                if '(' in file_entry:
                    file_path = file_entry.split('(')[0].strip()
                else:
                    file_path = file_entry
                    
                commands.append(f"git rm -rf {file_path}")
                
        # Add commit command
        if commands:
            commands.append('git commit -m "refactor: remove legacy SSOT violation files"')
            
        return commands


def main():
    """Main entry point for legacy file tracking."""
    tracker = LegacyFileTracker()
    
    # First do a dry run
    logger.info("Performing dry run scan...")
    dry_run_report = tracker.remove_all_legacy_files(dry_run=True)
    
    # Ask for confirmation
    if dry_run_report['total_legacy_identified'] > 0:
        logger.info("\n" + "="*80)
        logger.info("Ready to remove legacy files?")
        logger.info(f"This will remove {dry_run_report['total_legacy_identified']} files/directories")
        logger.info("Critical files will be backed up first")
        logger.info("="*80)
        
        # Generate git commands for reference
        git_commands = tracker.generate_git_commands()
        if git_commands:
            logger.info("\nGit commands to execute:")
            for cmd in git_commands[:10]:  # Show first 10
                logger.info(f"  {cmd}")
            if len(git_commands) > 10:
                logger.info(f"  ... and {len(git_commands) - 10} more")
                
    # Verify removal
    logger.info("\nVerifying removal status...")
    verification = tracker.verify_removal()
    
    return verification


if __name__ == "__main__":
    main()