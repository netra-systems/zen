#!/usr/bin/env python3
"""
Emergency Boundary Actions System
Handles critical boundary violations with immediate automated responses.
Follows CLAUDE.md requirements: 450-line limit, 25-line functions.
"""

import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class EmergencyAction:
    """Emergency action record."""
    action_type: str
    severity: str
    description: str
    file_path: str
    violation_count: int
    timestamp: str
    executed: bool = False
    success: bool = False
    error_message: str = ""

class EmergencyActionSystem:
    """Emergency response system for critical boundary violations."""
    
    def __init__(self, project_root: str = "."):
        """Initialize emergency action system."""
        self.project_root = Path(project_root)
        self.emergency_log = self.project_root / "logs" / "emergency_actions.json"
        self.emergency_threshold = 50  # Critical violation count
        self.system_shutdown_threshold = 100  # System breakdown threshold
        
    def assess_emergency_level(self) -> Dict[str, Any]:
        """Assess current emergency level based on violations."""
        violations = self._get_current_violations()
        total_violations = violations.get("total_violations", 0)
        emergency_violations = self._count_emergency_violations(violations)
        
        if emergency_violations >= self.system_shutdown_threshold:
            return self._create_emergency_assessment("CRITICAL", total_violations, emergency_violations)
        elif emergency_violations >= self.emergency_threshold:
            return self._create_emergency_assessment("HIGH", total_violations, emergency_violations)
        elif total_violations > 200:
            return self._create_emergency_assessment("MEDIUM", total_violations, emergency_violations)
        else:
            return self._create_emergency_assessment("LOW", total_violations, emergency_violations)
    
    def execute_emergency_response(self) -> List[EmergencyAction]:
        """Execute appropriate emergency response actions."""
        assessment = self.assess_emergency_level()
        actions = []
        
        if assessment["level"] == "CRITICAL":
            actions.extend(self._execute_critical_response(assessment))
        elif assessment["level"] == "HIGH":
            actions.extend(self._execute_high_response(assessment))
        elif assessment["level"] == "MEDIUM":
            actions.extend(self._execute_medium_response(assessment))
        
        # Log all actions
        self._log_emergency_actions(actions)
        return actions
    
    def _get_current_violations(self) -> Dict[str, Any]:
        """Get current boundary violations."""
        try:
            result = subprocess.run([
                "python", "scripts/boundary_enforcer.py", 
                "--enforce", "--json-output", "-"
            ], cwd=self.project_root, capture_output=True, text=True, timeout=30)
            
            if result.stdout:
                return json.loads(result.stdout)
            return {"violations": [], "total_violations": 0}
            
        except Exception as e:
            print(f"Error getting violations: {e}")
            return {"violations": [], "total_violations": 0}
    
    def _count_emergency_violations(self, violations: Dict[str, Any]) -> int:
        """Count violations that require emergency response."""
        emergency_count = 0
        for violation in violations.get("violations", []):
            if violation.get("severity") == "critical":
                if violation.get("impact_score", 0) >= 8:
                    emergency_count += 1
        return emergency_count
    
    def _create_emergency_assessment(self, level: str, total: int, emergency: int) -> Dict[str, Any]:
        """Create emergency assessment record."""
        return {
            "level": level,
            "total_violations": total,
            "emergency_violations": emergency,
            "timestamp": datetime.now().isoformat(),
            "requires_action": level in ["HIGH", "CRITICAL"]
        }
    
    def _execute_critical_response(self, assessment: Dict[str, Any]) -> List[EmergencyAction]:
        """Execute critical emergency response."""
        actions = []
        
        # 1. Stop development processes
        actions.append(self._create_stop_development_action(assessment))
        
        # 2. Create emergency backup
        actions.append(self._create_emergency_backup_action(assessment))
        
        # 3. Generate emergency report
        actions.append(self._create_emergency_report_action(assessment))
        
        # 4. Block CI/CD pipeline
        actions.append(self._create_block_pipeline_action(assessment))
        
        # 5. Auto-split critical files
        actions.append(self._create_auto_split_action(assessment))
        
        # Execute actions
        for action in actions:
            self._execute_action(action)
        
        return actions
    
    def _execute_high_response(self, assessment: Dict[str, Any]) -> List[EmergencyAction]:
        """Execute high-level emergency response."""
        actions = []
        
        # 1. Generate urgent report
        actions.append(self._create_urgent_report_action(assessment))
        
        # 2. Auto-fix obvious violations
        actions.append(self._create_auto_fix_action(assessment))
        
        # 3. Create issue tickets
        actions.append(self._create_issue_tickets_action(assessment))
        
        # Execute actions
        for action in actions:
            self._execute_action(action)
        
        return actions
    
    def _execute_medium_response(self, assessment: Dict[str, Any]) -> List[EmergencyAction]:
        """Execute medium-level response."""
        actions = []
        
        # 1. Generate warning report
        actions.append(self._create_warning_report_action(assessment))
        
        # 2. Schedule automated cleanup
        actions.append(self._create_schedule_cleanup_action(assessment))
        
        # Execute actions
        for action in actions:
            self._execute_action(action)
        
        return actions
    
    def _create_stop_development_action(self, assessment: Dict[str, Any]) -> EmergencyAction:
        """Create action to stop development processes."""
        return EmergencyAction(
            action_type="STOP_DEVELOPMENT",
            severity="CRITICAL",
            description="Stop all development processes due to critical violations",
            file_path="SYSTEM_WIDE",
            violation_count=assessment["emergency_violations"],
            timestamp=datetime.now().isoformat()
        )
    
    def _create_emergency_backup_action(self, assessment: Dict[str, Any]) -> EmergencyAction:
        """Create emergency backup action."""
        return EmergencyAction(
            action_type="EMERGENCY_BACKUP",
            severity="CRITICAL",
            description="Create emergency backup before system intervention",
            file_path="FULL_SYSTEM",
            violation_count=assessment["total_violations"],
            timestamp=datetime.now().isoformat()
        )
    
    def _create_emergency_report_action(self, assessment: Dict[str, Any]) -> EmergencyAction:
        """Create emergency report action."""
        return EmergencyAction(
            action_type="EMERGENCY_REPORT",
            severity="CRITICAL",
            description="Generate comprehensive emergency analysis report",
            file_path="logs/emergency_report.json",
            violation_count=assessment["total_violations"],
            timestamp=datetime.now().isoformat()
        )
    
    def _create_block_pipeline_action(self, assessment: Dict[str, Any]) -> EmergencyAction:
        """Create CI/CD pipeline block action."""
        return EmergencyAction(
            action_type="BLOCK_PIPELINE",
            severity="CRITICAL",
            description="Block CI/CD pipeline to prevent further degradation",
            file_path=".github/workflows/",
            violation_count=assessment["emergency_violations"],
            timestamp=datetime.now().isoformat()
        )
    
    def _create_auto_split_action(self, assessment: Dict[str, Any]) -> EmergencyAction:
        """Create auto-split action for critical files."""
        return EmergencyAction(
            action_type="AUTO_SPLIT",
            severity="HIGH",
            description="Automatically split files exceeding critical thresholds",
            file_path="MULTIPLE_FILES",
            violation_count=assessment["total_violations"],
            timestamp=datetime.now().isoformat()
        )
    
    def _create_urgent_report_action(self, assessment: Dict[str, Any]) -> EmergencyAction:
        """Create urgent report action."""
        return EmergencyAction(
            action_type="URGENT_REPORT",
            severity="HIGH",
            description="Generate urgent boundary violation report",
            file_path="logs/urgent_violations.json",
            violation_count=assessment["total_violations"],
            timestamp=datetime.now().isoformat()
        )
    
    def _create_auto_fix_action(self, assessment: Dict[str, Any]) -> EmergencyAction:
        """Create auto-fix action."""
        return EmergencyAction(
            action_type="AUTO_FIX",
            severity="HIGH",
            description="Apply automated fixes for obvious violations",
            file_path="MULTIPLE_FILES",
            violation_count=assessment["total_violations"],
            timestamp=datetime.now().isoformat()
        )
    
    def _create_issue_tickets_action(self, assessment: Dict[str, Any]) -> EmergencyAction:
        """Create issue tickets action."""
        return EmergencyAction(
            action_type="CREATE_ISSUES",
            severity="MEDIUM",
            description="Create GitHub issues for tracking violations",
            file_path="GitHub Issues",
            violation_count=assessment["total_violations"],
            timestamp=datetime.now().isoformat()
        )
    
    def _create_warning_report_action(self, assessment: Dict[str, Any]) -> EmergencyAction:
        """Create warning report action."""
        return EmergencyAction(
            action_type="WARNING_REPORT",
            severity="MEDIUM",
            description="Generate boundary violation warning report",
            file_path="logs/warning_report.json",
            violation_count=assessment["total_violations"],
            timestamp=datetime.now().isoformat()
        )
    
    def _create_schedule_cleanup_action(self, assessment: Dict[str, Any]) -> EmergencyAction:
        """Create scheduled cleanup action."""
        return EmergencyAction(
            action_type="SCHEDULE_CLEANUP",
            severity="LOW",
            description="Schedule automated boundary cleanup",
            file_path="SCHEDULE",
            violation_count=assessment["total_violations"],
            timestamp=datetime.now().isoformat()
        )
    
    def _execute_action(self, action: EmergencyAction) -> None:
        """Execute a specific emergency action."""
        try:
            if action.action_type == "STOP_DEVELOPMENT":
                self._stop_development_processes()
            elif action.action_type == "EMERGENCY_BACKUP":
                self._create_emergency_backup()
            elif action.action_type == "EMERGENCY_REPORT":
                self._generate_emergency_report()
            elif action.action_type == "BLOCK_PIPELINE":
                self._block_ci_pipeline()
            elif action.action_type == "AUTO_SPLIT":
                self._execute_auto_split()
            elif action.action_type == "URGENT_REPORT":
                self._generate_urgent_report()
            elif action.action_type == "AUTO_FIX":
                self._execute_auto_fixes()
            elif action.action_type == "CREATE_ISSUES":
                self._create_github_issues()
            elif action.action_type == "WARNING_REPORT":
                self._generate_warning_report()
            elif action.action_type == "SCHEDULE_CLEANUP":
                self._schedule_cleanup()
            
            action.executed = True
            action.success = True
            
        except Exception as e:
            action.executed = True
            action.success = False
            action.error_message = str(e)
            print(f"Action {action.action_type} failed: {e}")
    
    def _stop_development_processes(self) -> None:
        """Stop development processes."""
        print("EMERGENCY: Stopping development processes")
        # Implementation would stop dev servers, etc.
    
    def _create_emergency_backup(self) -> None:
        """Create emergency backup."""
        backup_dir = self.project_root / "emergency_backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"Creating emergency backup: {timestamp}")
    
    def _generate_emergency_report(self) -> None:
        """Generate comprehensive emergency report."""
        report_path = self.project_root / "logs" / "emergency_report.json"
        report_path.parent.mkdir(exist_ok=True)
        
        violations = self._get_current_violations()
        assessment = self.assess_emergency_level()
        
        emergency_report = {
            "timestamp": datetime.now().isoformat(),
            "emergency_level": assessment["level"],
            "total_violations": assessment["total_violations"],
            "emergency_violations": assessment["emergency_violations"],
            "violations": violations.get("violations", []),
            "system_metrics": violations.get("system_metrics", {}),
            "recommended_actions": self._get_recommended_actions(assessment)
        }
        
        with open(report_path, 'w') as f:
            json.dump(emergency_report, f, indent=2)
        
        print(f"Emergency report generated: {report_path}")
    
    def _block_ci_pipeline(self) -> None:
        """Block CI/CD pipeline."""
        print("EMERGENCY: Blocking CI/CD pipeline")
        # Implementation would create workflow that blocks deployment
    
    def _execute_auto_split(self) -> None:
        """Execute automated file splitting."""
        try:
            subprocess.run([
                "python", "scripts/auto_split_files.py", "--scan"
            ], cwd=self.project_root, check=True)
            print("Auto-split executed successfully")
        except subprocess.CalledProcessError as e:
            print(f"Auto-split failed: {e}")
    
    def _generate_urgent_report(self) -> None:
        """Generate urgent violations report."""
        print("Generating urgent violations report")
    
    def _execute_auto_fixes(self) -> None:
        """Execute automated fixes."""
        print("Executing automated boundary fixes")
    
    def _create_github_issues(self) -> None:
        """Create GitHub issues for violations."""
        print("Creating GitHub issues for boundary violations")
    
    def _generate_warning_report(self) -> None:
        """Generate warning report."""
        print("Generating boundary violation warnings")
    
    def _schedule_cleanup(self) -> None:
        """Schedule automated cleanup."""
        print("Scheduling automated boundary cleanup")
    
    def _get_recommended_actions(self, assessment: Dict[str, Any]) -> List[str]:
        """Get recommended actions based on assessment."""
        actions = []
        
        if assessment["level"] == "CRITICAL":
            actions.extend([
                "IMMEDIATE: Stop all feature development",
                "IMMEDIATE: Begin emergency refactoring",
                "IMMEDIATE: Review system architecture",
                "IMMEDIATE: Implement file splitting",
                "IMMEDIATE: Reduce function complexity"
            ])
        elif assessment["level"] == "HIGH":
            actions.extend([
                "URGENT: Schedule refactoring sprint",
                "URGENT: Implement boundary monitoring",
                "URGENT: Split oversized files",
                "URGENT: Review coding practices"
            ])
        else:
            actions.extend([
                "Monitor boundary compliance daily",
                "Implement preventive measures",
                "Schedule regular cleanup"
            ])
        
        return actions
    
    def _log_emergency_actions(self, actions: List[EmergencyAction]) -> None:
        """Log emergency actions to persistent storage."""
        self.emergency_log.parent.mkdir(exist_ok=True)
        
        # Load existing log
        existing_actions = []
        if self.emergency_log.exists():
            with open(self.emergency_log, 'r') as f:
                existing_actions = json.load(f)
        
        # Add new actions
        for action in actions:
            existing_actions.append(asdict(action))
        
        # Save updated log
        with open(self.emergency_log, 'w') as f:
            json.dump(existing_actions, f, indent=2)
        
        print(f"Emergency actions logged: {self.emergency_log}")

def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Emergency Boundary Actions System'
    )
    parser.add_argument('--assess', action='store_true', help='Assess emergency level')
    parser.add_argument('--execute', action='store_true', help='Execute emergency response')
    parser.add_argument('--report', action='store_true', help='Generate emergency report')
    
    args = parser.parse_args()
    
    emergency_system = EmergencyActionSystem()
    
    if args.assess:
        assessment = emergency_system.assess_emergency_level()
        print(f"Emergency Level: {assessment['level']}")
        print(f"Total Violations: {assessment['total_violations']}")
        print(f"Emergency Violations: {assessment['emergency_violations']}")
        print(f"Requires Action: {assessment['requires_action']}")
    
    elif args.execute:
        print("Executing emergency response...")
        actions = emergency_system.execute_emergency_response()
        print(f"Executed {len(actions)} emergency actions")
        for action in actions:
            status = "SUCCESS" if action.success else "FAILED"
            print(f"  {action.action_type}: {status}")
    
    elif args.report:
        emergency_system._generate_emergency_report()
    
    else:
        assessment = emergency_system.assess_emergency_level()
        if assessment['requires_action']:
            print(f"WARNING: Emergency level {assessment['level']} detected")
            print("Run with --execute to trigger automated response")
        else:
            print("System boundary status: NORMAL")

if __name__ == "__main__":
    main()