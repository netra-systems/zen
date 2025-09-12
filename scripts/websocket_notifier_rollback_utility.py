#!/usr/bin/env python3
"""
Emergency rollback utility for WebSocketNotifier SSOT migration.
Provides quick rollback capabilities for each migration phase.

Usage:
    python scripts/websocket_notifier_rollback_utility.py --phase [1|2|3|all]

Part of GitHub Issue #216 SSOT Remediation Plan - Risk Mitigation
"""

import os
import sys
import shutil
import subprocess
import argparse
from typing import List, Dict, Optional
from pathlib import Path
import glob

class WebSocketNotifierRollback:
    """Emergency rollback utility for WebSocketNotifier SSOT migration."""
    
    def __init__(self):
        self.project_root = "/Users/anthony/Desktop/netra-apex"
        self.backup_suffixes = {
            'phase1': '.backup_pre_ssot_migration',
            'phase2': '.backup_pre_factory_migration',
            'phase3': '.backup_pre_interface_migration'
        }
        
    def find_backup_files(self, phase: str) -> List[str]:
        """Find all backup files for a specific phase."""
        if phase not in self.backup_suffixes:
            raise ValueError(f"Invalid phase: {phase}. Must be one of {list(self.backup_suffixes.keys())}")
        
        suffix = self.backup_suffixes[phase]
        backup_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            if any(skip in root for skip in ['.git', '__pycache__', '.pytest_cache']):
                continue
                
            for file in files:
                if file.endswith(suffix):
                    backup_path = os.path.join(root, file)
                    original_path = backup_path.replace(suffix, '')
                    backup_files.append((backup_path, original_path))
        
        return backup_files
    
    def rollback_phase1_imports(self) -> bool:
        """Rollback Phase 1: Import path migration."""
        print(" CYCLE:  Rolling back Phase 1: Import path migration...")
        
        backup_files = self.find_backup_files('phase1')
        if not backup_files:
            print(" WARNING: [U+FE0F]  No Phase 1 backup files found - using git rollback")
            return self._git_rollback_imports()
        
        success_count = 0
        for backup_path, original_path in backup_files:
            try:
                if os.path.exists(original_path):
                    # Restore from backup
                    shutil.copy2(backup_path, original_path)
                    print(f" PASS:  Restored: {original_path}")
                    success_count += 1
                else:
                    print(f" WARNING: [U+FE0F]  Original file not found: {original_path}")
            except Exception as e:
                print(f" FAIL:  Failed to restore {original_path}: {e}")
        
        print(f" CHART:  Phase 1 rollback: {success_count}/{len(backup_files)} files restored")
        return success_count == len(backup_files)
    
    def rollback_phase2_factory(self) -> bool:
        """Rollback Phase 2: Factory pattern migration."""
        print(" CYCLE:  Rolling back Phase 2: Factory pattern migration...")
        
        backup_files = self.find_backup_files('phase2')
        if not backup_files:
            print(" WARNING: [U+FE0F]  No Phase 2 backup files found - using git rollback")
            return self._git_rollback_factory()
        
        success_count = 0
        for backup_path, original_path in backup_files:
            try:
                if os.path.exists(original_path):
                    # Restore from backup
                    shutil.copy2(backup_path, original_path)
                    print(f" PASS:  Restored: {original_path}")
                    success_count += 1
                else:
                    print(f" WARNING: [U+FE0F]  Original file not found: {original_path}")
            except Exception as e:
                print(f" FAIL:  Failed to restore {original_path}: {e}")
        
        # Special handling for canonical implementation
        canonical_file = "/Users/anthony/Desktop/netra-apex/netra_backend/app/services/agent_websocket_bridge.py"
        canonical_backup = f"{canonical_file}.backup_pre_factory_migration"
        
        if os.path.exists(canonical_backup):
            try:
                shutil.copy2(canonical_backup, canonical_file)
                print(f" PASS:  Restored canonical implementation: {canonical_file}")
                success_count += 1
            except Exception as e:
                print(f" FAIL:  Failed to restore canonical implementation: {e}")
        
        print(f" CHART:  Phase 2 rollback: {success_count}/{len(backup_files) + 1} files restored")
        return success_count == len(backup_files) + 1
    
    def rollback_phase3_interface(self) -> bool:
        """Rollback Phase 3: Interface standardization."""
        print(" CYCLE:  Rolling back Phase 3: Interface standardization...")
        
        backup_files = self.find_backup_files('phase3')
        if not backup_files:
            print(" WARNING: [U+FE0F]  No Phase 3 backup files found - using git rollback")
            return self._git_rollback_interface()
        
        success_count = 0
        for backup_path, original_path in backup_files:
            try:
                if os.path.exists(original_path):
                    # Restore from backup
                    shutil.copy2(backup_path, original_path)
                    print(f" PASS:  Restored: {original_path}")
                    success_count += 1
                else:
                    print(f" WARNING: [U+FE0F]  Original file not found: {original_path}")
            except Exception as e:
                print(f" FAIL:  Failed to restore {original_path}: {e}")
        
        print(f" CHART:  Phase 3 rollback: {success_count}/{len(backup_files)} files restored")
        return success_count == len(backup_files)
    
    def _git_rollback_imports(self) -> bool:
        """Git-based rollback for import changes."""
        try:
            # Find commits related to import migration
            cmd = ['git', 'log', '--oneline', '--grep=WebSocketNotifier.*import', '-n', '5']
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0 and result.stdout.strip():
                commits = result.stdout.strip().split('\n')
                if commits:
                    # Revert the most recent import-related commit
                    commit_hash = commits[0].split()[0]
                    print(f" CYCLE:  Reverting import commit: {commit_hash}")
                    
                    revert_cmd = ['git', 'revert', '--no-edit', commit_hash]
                    revert_result = subprocess.run(revert_cmd, capture_output=True, text=True, cwd=self.project_root)
                    
                    if revert_result.returncode == 0:
                        print(" PASS:  Git rollback successful")
                        return True
                    else:
                        print(f" FAIL:  Git revert failed: {revert_result.stderr}")
                        return False
            
            print(" WARNING: [U+FE0F]  No import-related commits found for rollback")
            return False
            
        except Exception as e:
            print(f" FAIL:  Git rollback failed: {e}")
            return False
    
    def _git_rollback_factory(self) -> bool:
        """Git-based rollback for factory pattern changes."""
        try:
            # Find commits related to factory migration
            cmd = ['git', 'log', '--oneline', '--grep=factory.*pattern', '-n', '5']
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0 and result.stdout.strip():
                commits = result.stdout.strip().split('\n')
                if commits:
                    # Revert factory-related commits
                    for commit_line in commits[:3]:  # Revert up to 3 recent commits
                        commit_hash = commit_line.split()[0]
                        print(f" CYCLE:  Reverting factory commit: {commit_hash}")
                        
                        revert_cmd = ['git', 'revert', '--no-edit', commit_hash]
                        revert_result = subprocess.run(revert_cmd, capture_output=True, text=True, cwd=self.project_root)
                        
                        if revert_result.returncode != 0:
                            print(f" WARNING: [U+FE0F]  Failed to revert {commit_hash}: {revert_result.stderr}")
                    
                    print(" PASS:  Git rollback completed")
                    return True
            
            print(" WARNING: [U+FE0F]  No factory-related commits found for rollback")
            return False
            
        except Exception as e:
            print(f" FAIL:  Git rollback failed: {e}")
            return False
    
    def _git_rollback_interface(self) -> bool:
        """Git-based rollback for interface changes."""
        try:
            # Find commits related to interface standardization
            cmd = ['git', 'log', '--oneline', '--grep=interface.*standard', '-n', '3']
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0 and result.stdout.strip():
                commits = result.stdout.strip().split('\n')
                if commits:
                    # Revert interface-related commits
                    for commit_line in commits:
                        commit_hash = commit_line.split()[0]
                        print(f" CYCLE:  Reverting interface commit: {commit_hash}")
                        
                        revert_cmd = ['git', 'revert', '--no-edit', commit_hash]
                        revert_result = subprocess.run(revert_cmd, capture_output=True, text=True, cwd=self.project_root)
                        
                        if revert_result.returncode != 0:
                            print(f" WARNING: [U+FE0F]  Failed to revert {commit_hash}: {revert_result.stderr}")
                    
                    print(" PASS:  Git rollback completed")
                    return True
            
            print(" WARNING: [U+FE0F]  No interface-related commits found for rollback")
            return False
            
        except Exception as e:
            print(f" FAIL:  Git rollback failed: {e}")
            return False
    
    def validate_rollback(self, phase: str) -> bool:
        """Validate that rollback was successful."""
        print(f"\n SEARCH:  Validating rollback for phase {phase}...")
        
        validation_commands = {
            'phase1': [
                # Test mission critical functionality
                ['python', 'tests/mission_critical/test_websocket_agent_events_suite.py'],
                # Check for import errors
                ['python', '-c', 'from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier; print("Import OK")']
            ],
            'phase2': [
                # Test WebSocket basic events
                ['python', 'tests/integration/test_websocket_basic_events.py'],
                # Test user isolation
                ['python', 'tests/integration/test_websocket_user_isolation.py']
            ],
            'phase3': [
                # Test interface consistency
                ['python', 'tests/unit/test_websocket_notifier_business_logic.py'],
                # Test Golden Path compliance
                ['python', 'tests/integration/test_websocket_ssot_golden_path.py']
            ]
        }
        
        commands = validation_commands.get(phase, [])
        if not commands:
            print(f" WARNING: [U+FE0F]  No validation commands defined for {phase}")
            return True
        
        success_count = 0
        for cmd in commands:
            try:
                print(f"  [U+1F9EA] Running: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root, timeout=300)
                
                if result.returncode == 0:
                    print(f"     PASS:  Passed")
                    success_count += 1
                else:
                    print(f"     FAIL:  Failed: {result.stderr.strip()}")
                    
            except subprocess.TimeoutExpired:
                print(f"    [U+23F0] Timeout")
            except Exception as e:
                print(f"     FAIL:  Error: {e}")
        
        validation_success = success_count == len(commands)
        print(f" CHART:  Validation: {success_count}/{len(commands)} tests passed")
        
        return validation_success
    
    def cleanup_backup_files(self, phase: str) -> bool:
        """Clean up backup files after successful rollback."""
        print(f"[U+1F9F9] Cleaning up backup files for {phase}...")
        
        backup_files = self.find_backup_files(phase)
        if not backup_files:
            print("[U+2139][U+FE0F]  No backup files to clean up")
            return True
        
        cleaned_count = 0
        for backup_path, original_path in backup_files:
            try:
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                    print(f"[U+1F5D1][U+FE0F]  Removed backup: {backup_path}")
                    cleaned_count += 1
            except Exception as e:
                print(f" FAIL:  Failed to remove {backup_path}: {e}")
        
        print(f" CHART:  Cleanup: {cleaned_count}/{len(backup_files)} backup files removed")
        return cleaned_count == len(backup_files)
    
    def emergency_full_rollback(self) -> bool:
        """Emergency full rollback of all SSOT migration changes."""
        print(" ALERT:  EMERGENCY FULL ROLLBACK INITIATED")
        print("=" * 60)
        
        # Rollback in reverse order (Phase 3 -> 2 -> 1)
        phases = ['phase3', 'phase2', 'phase1']
        rollback_success = True
        
        for phase in phases:
            print(f"\n CYCLE:  Rolling back {phase.upper()}...")
            
            if phase == 'phase1':
                success = self.rollback_phase1_imports()
            elif phase == 'phase2':
                success = self.rollback_phase2_factory()
            elif phase == 'phase3':
                success = self.rollback_phase3_interface()
            else:
                success = False
            
            if not success:
                print(f" WARNING: [U+FE0F]  {phase.upper()} rollback had issues")
                rollback_success = False
            
            # Validate each phase
            validation_success = self.validate_rollback(phase)
            if not validation_success:
                print(f" WARNING: [U+FE0F]  {phase.upper()} validation failed")
                rollback_success = False
        
        # Final system validation
        print(f"\n SEARCH:  Running final system validation...")
        final_validation = self._run_final_validation()
        
        if rollback_success and final_validation:
            print(f"\n CELEBRATION:  EMERGENCY ROLLBACK COMPLETED SUCCESSFULLY")
            print(f"   All phases rolled back and validated")
            return True
        else:
            print(f"\n FAIL:  EMERGENCY ROLLBACK COMPLETED WITH ISSUES")
            print(f"   Manual intervention may be required")
            return False
    
    def _run_final_validation(self) -> bool:
        """Run final validation after complete rollback."""
        validation_commands = [
            ['python', 'tests/mission_critical/test_websocket_agent_events_suite.py'],
            ['python', 'tests/integration/test_websocket_basic_events.py'],
            ['python', '-c', 'from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier; print("WebSocketNotifier import successful")']
        ]
        
        success_count = 0
        for cmd in validation_commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root, timeout=300)
                if result.returncode == 0:
                    success_count += 1
                else:
                    print(f" FAIL:  Final validation failed: {' '.join(cmd)}")
            except Exception as e:
                print(f" FAIL:  Final validation error: {e}")
        
        return success_count == len(validation_commands)

def main():
    """Main rollback execution."""
    parser = argparse.ArgumentParser(description='WebSocketNotifier SSOT Migration Rollback Utility')
    parser.add_argument('--phase', choices=['1', '2', '3', 'all'], required=True,
                       help='Phase to rollback (1=imports, 2=factory, 3=interface, all=emergency full rollback)')
    parser.add_argument('--validate', action='store_true', default=True,
                       help='Run validation after rollback (default: True)')
    parser.add_argument('--cleanup', action='store_true', default=False,
                       help='Clean up backup files after successful rollback')
    
    args = parser.parse_args()
    
    print(" CYCLE:  WebSocketNotifier SSOT Migration Rollback Utility")
    print("[U+1F4CB] GitHub Issue #216 - Emergency Rollback")
    print("=" * 60)
    
    rollback = WebSocketNotifierRollback()
    
    # Confirm rollback
    if args.phase == 'all':
        response = input(" WARNING: [U+FE0F]  EMERGENCY FULL ROLLBACK - Are you sure? Type 'ROLLBACK' to confirm: ")
        if response != 'ROLLBACK':
            print(" FAIL:  Emergency rollback cancelled")
            return 1
    else:
        response = input(f"[U+2753] Rollback Phase {args.phase}? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print(" FAIL:  Rollback cancelled")
            return 1
    
    # Execute rollback
    if args.phase == 'all':
        success = rollback.emergency_full_rollback()
    elif args.phase == '1':
        success = rollback.rollback_phase1_imports()
        if success and args.validate:
            success = rollback.validate_rollback('phase1')
    elif args.phase == '2':
        success = rollback.rollback_phase2_factory()
        if success and args.validate:
            success = rollback.validate_rollback('phase2')
    elif args.phase == '3':
        success = rollback.rollback_phase3_interface()
        if success and args.validate:
            success = rollback.validate_rollback('phase3')
    else:
        print(f" FAIL:  Invalid phase: {args.phase}")
        return 1
    
    # Cleanup if requested and successful
    if success and args.cleanup and args.phase != 'all':
        phase_name = f"phase{args.phase}"
        rollback.cleanup_backup_files(phase_name)
    
    # Final status
    if success:
        print(f"\n CELEBRATION:  Rollback completed successfully!")
        print(f"[U+1F4CB] Next Steps:")
        print(f"   1. Verify system functionality manually")
        print(f"   2. Review rollback logs for any issues")
        print(f"   3. Plan remediation strategy if needed")
        return 0
    else:
        print(f"\n FAIL:  Rollback completed with issues!")
        print(f"[U+1F4CB] Manual intervention required:")
        print(f"   1. Check backup files in project directory")
        print(f"   2. Review git history for commit-based rollback")
        print(f"   3. Contact development team if issues persist")
        return 1

if __name__ == "__main__":
    sys.exit(main())