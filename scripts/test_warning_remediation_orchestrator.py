#!/usr/bin/env python3
"""
Test Warning Remediation Orchestrator

Business Value Justification (BVJ):
- Segment: Platform/All Services
- Business Goal: Golden Path stability and operational excellence
- Value Impact: Eliminates test warnings that could mask $500K+ ARR infrastructure issues
- Strategic Impact: Ensures reliable test infrastructure supports rapid incident response

This orchestrator manages the phased remediation of test warnings while maintaining
system stability and supporting Golden Path operations.
"""

import os
import subprocess
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import tempfile
import shutil

class TestWarningRemediationOrchestrator:
    """Orchestrates phased test warning remediation with validation and rollback"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backup_root = self.project_root / "backups" / f"test_remediation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.backup_root.mkdir(parents=True, exist_ok=True)
        
        # Phase configuration
        self.phases = {
            'phase1': {
                'name': 'Logging SSOT Migration',
                'priority': 'P0_CRITICAL',
                'script': 'scripts/migrate_deprecated_logging_imports.py',
                'business_impact': 'HIGH - Supports Issue #1278 infrastructure debugging',
                'estimated_time': '30 minutes',
                'validation_commands': [
                    'python3 tests/unified_test_runner.py --category unit --fast-fail',
                    'python3 scripts/check_architecture_compliance.py',
                ],
                'success_criteria': [
                    'Zero import logging violations',
                    'SSOT compliance maintained',
                    'Unit tests pass'
                ]
            },
            'phase2': {
                'name': 'Async Test Cleanup',
                'priority': 'P1_HIGH',
                'script': 'scripts/fix_async_test_patterns.py',
                'business_impact': 'MEDIUM - Test reliability for CI/CD',
                'estimated_time': '45 minutes',
                'validation_commands': [
                    'python3 tests/unified_test_runner.py --category integration --fast-fail',
                    'python3 -m pytest netra_backend/tests/mission_critical/ -v --tb=short'
                ],
                'success_criteria': [
                    'No unawaited coroutine warnings',
                    'Integration tests stable',
                    'Mission critical tests pass'
                ]
            },
            'phase3': {
                'name': 'Test Return Value Cleanup',
                'priority': 'P2_LOW',
                'script': 'scripts/fix_test_return_values.py',
                'business_impact': 'LOW - Code hygiene improvement',
                'estimated_time': '20 minutes',
                'validation_commands': [
                    'python3 tests/unified_test_runner.py --category unit --no-coverage'
                ],
                'success_criteria': [
                    'Test methods use assertions not returns',
                    'Framework compliance improved'
                ]
            }
        }
    
    def create_system_snapshot(self) -> str:
        """Create complete system snapshot before remediation"""
        snapshot_dir = self.backup_root / "system_snapshot"
        snapshot_dir.mkdir(exist_ok=True)
        
        print("Creating system snapshot...")
        
        # Backup critical directories
        critical_dirs = ['tests', 'netra_backend/tests', 'auth_service/tests', 'shared/tests']
        for dir_name in critical_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                try:
                    shutil.copytree(dir_path, snapshot_dir / dir_name)
                except Exception as e:
                    print(f"Warning: Could not backup {dir_name}: {e}")
        
        # Create git state snapshot
        try:
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True, cwd=self.project_root)
            with open(snapshot_dir / 'git_status.txt', 'w') as f:
                f.write(result.stdout)
            
            result = subprocess.run(['git', 'log', '--oneline', '-10'], 
                                  capture_output=True, text=True, cwd=self.project_root)
            with open(snapshot_dir / 'git_log.txt', 'w') as f:
                f.write(result.stdout)
        except Exception as e:
            print(f"Warning: Could not capture git state: {e}")
        
        # Run baseline tests and capture results
        baseline_results = self.run_baseline_tests()
        with open(snapshot_dir / 'baseline_test_results.json', 'w') as f:
            json.dump(baseline_results, f, indent=2)
        
        print(f"System snapshot created at: {snapshot_dir}")
        return str(snapshot_dir)
    
    def run_baseline_tests(self) -> Dict:
        """Run baseline tests to establish current state"""
        print("Running baseline tests...")
        baseline = {
            'timestamp': datetime.now().isoformat(),
            'test_results': {},
            'warnings_count': {}
        }
        
        # Quick unit test run
        try:
            result = subprocess.run([
                'python3', 'tests/unified_test_runner.py', 
                '--category', 'unit', '--fast-fail', '--no-coverage'
            ], capture_output=True, text=True, cwd=self.project_root, timeout=300)
            
            baseline['test_results']['unit'] = {
                'exit_code': result.returncode,
                'passed': result.returncode == 0,
                'output_lines': len(result.stdout.split('\n'))
            }
        except Exception as e:
            baseline['test_results']['unit'] = {
                'exit_code': -1,
                'passed': False,
                'error': str(e)
            }
        
        # Count current warnings
        try:
            # Count deprecated logging imports
            result = subprocess.run([
                'grep', '-r', '--include=*.py', 'import logging', 'tests/', 'netra_backend/tests/'
            ], capture_output=True, text=True, cwd=self.project_root)
            baseline['warnings_count']['deprecated_logging'] = len(result.stdout.split('\n')) if result.stdout else 0
        except:
            baseline['warnings_count']['deprecated_logging'] = 0
        
        return baseline
    
    def execute_phase(self, phase_name: str, dry_run: bool = False) -> Dict:
        """Execute a single remediation phase"""
        phase_config = self.phases[phase_name]
        
        print(f"\n{'='*60}")
        print(f"EXECUTING {phase_config['name'].upper()}")
        print(f"Priority: {phase_config['priority']}")
        print(f"Business Impact: {phase_config['business_impact']}")
        print(f"Estimated Time: {phase_config['estimated_time']}")
        print(f"{'='*60}")
        
        result = {
            'phase': phase_name,
            'started_at': datetime.now().isoformat(),
            'success': False,
            'script_output': '',
            'validation_results': [],
            'errors': []
        }
        
        try:
            # Execute the remediation script
            script_path = self.project_root / phase_config['script']
            cmd = ['python3', str(script_path)]
            if not dry_run:
                cmd.append('--execute')
            
            print(f"Running: {' '.join(cmd)}")
            script_result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root, timeout=600)
            
            result['script_output'] = script_result.stdout
            result['script_exit_code'] = script_result.returncode
            
            if script_result.returncode != 0:
                result['errors'].append(f"Script failed with exit code {script_result.returncode}")
                result['errors'].append(f"Error output: {script_result.stderr}")
                return result
            
            # Run validation commands if not dry run
            if not dry_run:
                for validation_cmd in phase_config['validation_commands']:
                    validation_result = self.run_validation_command(validation_cmd)
                    result['validation_results'].append(validation_result)
                    
                    if not validation_result['passed']:
                        result['errors'].append(f"Validation failed: {validation_cmd}")
                        # Don't continue with remaining validations if one fails
                        break
            
            # Mark as successful if no errors
            result['success'] = len(result['errors']) == 0
            
        except subprocess.TimeoutExpired:
            result['errors'].append("Phase execution timed out")
        except Exception as e:
            result['errors'].append(f"Unexpected error: {str(e)}")
        
        result['completed_at'] = datetime.now().isoformat()
        return result
    
    def run_validation_command(self, command: str) -> Dict:
        """Run a validation command and return results"""
        print(f"Validating: {command}")
        
        try:
            result = subprocess.run(
                command.split(), 
                capture_output=True, 
                text=True, 
                cwd=self.project_root, 
                timeout=600
            )
            
            return {
                'command': command,
                'exit_code': result.returncode,
                'passed': result.returncode == 0,
                'output_lines': len(result.stdout.split('\n')),
                'has_stderr': bool(result.stderr.strip())
            }
        except subprocess.TimeoutExpired:
            return {
                'command': command,
                'exit_code': -1,
                'passed': False,
                'error': 'Validation timed out'
            }
        except Exception as e:
            return {
                'command': command,
                'exit_code': -1,
                'passed': False,
                'error': str(e)
            }
    
    def rollback_phase(self, phase_name: str, snapshot_dir: str) -> bool:
        """Rollback a phase using system snapshot"""
        print(f"\nROLLBACK: Restoring {phase_name} from snapshot...")
        
        try:
            snapshot_path = Path(snapshot_dir)
            
            # Restore test directories
            critical_dirs = ['tests', 'netra_backend/tests', 'auth_service/tests', 'shared/tests']
            for dir_name in critical_dirs:
                source = snapshot_path / dir_name
                target = self.project_root / dir_name
                
                if source.exists() and target.exists():
                    # Remove current directory and restore from snapshot
                    shutil.rmtree(target)
                    shutil.copytree(source, target)
                    print(f"Restored: {dir_name}")
            
            # Verify rollback with quick test
            validation_result = self.run_validation_command('python3 tests/unified_test_runner.py --category unit --fast-fail --no-coverage')
            
            if validation_result['passed']:
                print("✅ Rollback successful - tests passing")
                return True
            else:
                print("❌ Rollback validation failed")
                return False
                
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return False
    
    def execute_remediation_plan(self, phases_to_run: List[str], dry_run: bool = False) -> Dict:
        """Execute complete remediation plan with validation and rollback"""
        
        execution_log = {
            'started_at': datetime.now().isoformat(),
            'dry_run': dry_run,
            'phases_planned': phases_to_run,
            'system_snapshot': None,
            'phase_results': [],
            'overall_success': False,
            'recommendations': []
        }
        
        print("🚀 STARTING TEST WARNING REMEDIATION")
        print(f"Phases to execute: {', '.join(phases_to_run)}")
        print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTION'}")
        
        # Create system snapshot
        execution_log['system_snapshot'] = self.create_system_snapshot()
        
        # Execute phases in order
        phases_completed = []
        for phase_name in phases_to_run:
            if phase_name not in self.phases:
                print(f"❌ Unknown phase: {phase_name}")
                continue
            
            phase_result = self.execute_phase(phase_name, dry_run)
            execution_log['phase_results'].append(phase_result)
            
            if phase_result['success']:
                phases_completed.append(phase_name)
                print(f"✅ {self.phases[phase_name]['name']} - SUCCESS")
            else:
                print(f"❌ {self.phases[phase_name]['name']} - FAILED")
                print("Errors:")
                for error in phase_result['errors']:
                    print(f"  - {error}")
                
                # For critical phases, offer rollback
                if self.phases[phase_name]['priority'].startswith('P0') and not dry_run:
                    print(f"\n⚠️  Critical phase failed. Initiating rollback...")
                    rollback_success = self.rollback_phase(phase_name, execution_log['system_snapshot'])
                    if rollback_success:
                        execution_log['recommendations'].append(f"Rollback successful for {phase_name}")
                    else:
                        execution_log['recommendations'].append(f"MANUAL INTERVENTION REQUIRED: Rollback failed for {phase_name}")
                
                # Stop execution on critical phase failure (unless dry run)
                if self.phases[phase_name]['priority'].startswith('P0') and not dry_run:
                    execution_log['recommendations'].append("Critical phase failed - halting remediation")
                    break
        
        # Determine overall success
        critical_phases = [p for p in phases_to_run if self.phases[p]['priority'].startswith('P0')]
        critical_passed = all(
            result['success'] for result in execution_log['phase_results'] 
            if result['phase'] in critical_phases
        )
        
        execution_log['overall_success'] = critical_passed
        execution_log['completed_at'] = datetime.now().isoformat()
        
        # Generate final recommendations
        if execution_log['overall_success']:
            execution_log['recommendations'].append("✅ All critical phases completed successfully")
            execution_log['recommendations'].append("Golden Path debugging capability improved")
            if not dry_run:
                execution_log['recommendations'].append("Run full test suite to validate changes")
        else:
            execution_log['recommendations'].append("❌ Critical phase failures detected")
            execution_log['recommendations'].append("System stability may be compromised")
            execution_log['recommendations'].append("Consider manual review before proceeding")
        
        return execution_log
    
    def generate_report(self, execution_log: Dict) -> str:
        """Generate comprehensive remediation report"""
        report = f"""
TEST WARNING REMEDIATION REPORT
Generated: {datetime.now().isoformat()}
Mode: {'DRY RUN' if execution_log['dry_run'] else 'EXECUTION'}

EXECUTIVE SUMMARY
Overall Success: {'✅ YES' if execution_log['overall_success'] else '❌ NO'}
Phases Planned: {len(execution_log['phases_planned'])}
Phases Executed: {len(execution_log['phase_results'])}
System Snapshot: {execution_log['system_snapshot']}

BUSINESS IMPACT ASSESSMENT
- P0 Critical: Logging SSOT migration for Golden Path debugging
- P1 High: Async test stability for CI/CD reliability  
- P2 Low: Code hygiene improvements

PHASE EXECUTION RESULTS
"""
        
        for result in execution_log['phase_results']:
            phase_config = self.phases[result['phase']]
            status = '✅ SUCCESS' if result['success'] else '❌ FAILED'
            
            report += f"""
Phase: {phase_config['name']}
Priority: {phase_config['priority']}
Status: {status}
Duration: {result.get('started_at', 'Unknown')} - {result.get('completed_at', 'Unknown')}
"""
            
            if result['errors']:
                report += "Errors:\n"
                for error in result['errors']:
                    report += f"  - {error}\n"
            
            if result['validation_results']:
                report += "Validations:\n"
                for validation in result['validation_results']:
                    validation_status = '✅' if validation['passed'] else '❌'
                    report += f"  {validation_status} {validation['command']}\n"
        
        report += f"""
RECOMMENDATIONS
"""
        for rec in execution_log['recommendations']:
            report += f"- {rec}\n"
        
        report += f"""
NEXT STEPS
1. Review detailed logs for any manual intervention requirements
2. Validate Golden Path functionality if critical phases succeeded
3. Monitor test stability in CI/CD pipeline
4. Consider deferring low-priority phases during critical periods

ROLLBACK INFORMATION
System snapshot available at: {execution_log['system_snapshot']}
Use snapshot for emergency rollback if needed.
"""
        
        return report

def main():
    parser = argparse.ArgumentParser(description='Orchestrate test warning remediation')
    parser.add_argument('--phases', nargs='+', 
                       choices=['phase1', 'phase2', 'phase3', 'all'],
                       default=['all'],
                       help='Phases to execute')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Run in dry-run mode (default)')
    parser.add_argument('--execute', action='store_true',
                       help='Execute actual changes (overrides dry-run)')
    parser.add_argument('--project-root', default='.',
                       help='Project root directory')
    parser.add_argument('--report-file', default='test_remediation_report.txt',
                       help='Output file for detailed report')
    
    args = parser.parse_args()
    
    # Determine execution mode
    dry_run = not args.execute  # Default to dry run unless --execute specified
    
    # Expand 'all' to specific phases
    if 'all' in args.phases:
        phases_to_run = ['phase1', 'phase2', 'phase3']
    else:
        phases_to_run = args.phases
    
    orchestrator = TestWarningRemediationOrchestrator(args.project_root)
    
    # Execute remediation plan
    execution_log = orchestrator.execute_remediation_plan(phases_to_run, dry_run)
    
    # Generate and save report
    report = orchestrator.generate_report(execution_log)
    with open(args.report_file, 'w') as f:
        f.write(report)
    
    # Print summary
    print(f"\n{'='*60}")
    print("REMEDIATION COMPLETE")
    print(f"Overall Success: {'✅ YES' if execution_log['overall_success'] else '❌ NO'}")
    print(f"Detailed Report: {args.report_file}")
    print(f"System Snapshot: {execution_log['system_snapshot']}")
    print(f"{'='*60}")
    
    # Return appropriate exit code
    exit_code = 0 if execution_log['overall_success'] else 1
    exit(exit_code)

if __name__ == "__main__":
    main()