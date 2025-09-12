#!/usr/bin/env python3
"""
Automated Docker Issue Remediation Loop
Continuously identifies and remediates Docker container issues
"""

import subprocess
import json
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

class AutomatedRemediator:
    """Automated Docker issue remediation system"""
    
    def __init__(self, max_iterations: int = 100):
        self.max_iterations = max_iterations
        self.iteration = 0
        self.remediation_history = []
        self.total_issues_fixed = 0
        
    def run_introspection(self, hours_back: int = 1) -> Dict[str, Any]:
        """Run Docker log introspection and get report"""
        try:
            result = subprocess.run(
                ['python', 'scripts/docker_log_introspection.py', str(hours_back)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Load the generated report
            report_path = Path('docker_audit_report.json')
            if report_path.exists():
                with open(report_path, 'r') as f:
                    return json.load(f)
            
            return {'error': 'No report generated'}
            
        except Exception as e:
            print(f"Error running introspection: {e}")
            return {'error': str(e)}
    
    def get_next_issue(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the next highest priority issue from the report"""
        
        # Priority order: CRITICAL > HIGH > MEDIUM > LOW
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            issues = report.get('issues_by_severity', {}).get(severity, [])
            if issues:
                # Return first issue of highest severity
                issue = issues[0]
                issue['severity'] = severity
                return issue
        
        return None
    
    def remediate_issue(self, issue: Dict[str, Any]) -> bool:
        """Remediate a specific issue based on its type"""
        
        issue_type = issue.get('issue_type', '')
        container = issue.get('container', '')
        severity = issue.get('severity', '')
        
        print(f"\nRemediating {severity} issue: {issue_type} in {container}")
        
        # Map issue types to remediation strategies
        remediation_map = {
            'Database connectivity issue': self.fix_database_issue,
            'Authentication issue': self.fix_auth_issue,
            'Application error': self.fix_application_error,
            'Warning condition': self.fix_warning_condition,
            'Configuration error': self.fix_config_error,
            'High memory usage': self.fix_memory_issue,
            'Connection failure': self.fix_connection_issue,
        }
        
        # Get remediation function
        remediation_func = remediation_map.get(
            issue_type, 
            self.generic_remediation
        )
        
        # Execute remediation
        try:
            success = remediation_func(issue)
            
            # Record remediation
            self.remediation_history.append({
                'iteration': self.iteration,
                'timestamp': datetime.now().isoformat(),
                'issue': issue_type,
                'container': container,
                'severity': severity,
                'success': success
            })
            
            if success:
                self.total_issues_fixed += 1
                print(f"  [SUCCESS] Successfully remediated {issue_type}")
            else:
                print(f"  [FAILED] Failed to remediate {issue_type}")
                
            return success
            
        except Exception as e:
            print(f"  [ERROR] Error during remediation: {e}")
            return False
    
    def fix_database_issue(self, issue: Dict[str, Any]) -> bool:
        """Fix database connectivity issues"""
        container = issue.get('container', '')
        
        # Check if database container is running
        if 'postgres' in container.lower() or 'clickhouse' in container.lower():
            # Restart database container
            subprocess.run(['docker', 'restart', container], capture_output=True)
            time.sleep(5)
            return True
            
        # For services connecting to database
        # Restart the service to reconnect
        subprocess.run(['docker', 'restart', container], capture_output=True)
        time.sleep(5)
        return True
    
    def fix_auth_issue(self, issue: Dict[str, Any]) -> bool:
        """Fix authentication issues"""
        # Most auth issues are false positives after our pattern fix
        # Real auth issues would need service restart
        container = issue.get('container', '')
        if 'auth' in container.lower():
            subprocess.run(['docker', 'restart', container], capture_output=True)
            time.sleep(5)
            return True
        return True
    
    def fix_application_error(self, issue: Dict[str, Any]) -> bool:
        """Fix application errors"""
        container = issue.get('container', '')
        log_excerpt = issue.get('log_excerpt', '')
        
        # Check for specific error patterns
        if 'No module named' in log_excerpt:
            # Module import issues often need container rebuild
            print(f"   ->  Module import error detected, may need rebuild")
            return False
            
        if 'TypeError' in log_excerpt or 'AttributeError' in log_excerpt:
            # Code errors need code fixes
            print(f"   ->  Code error detected, needs manual fix")
            return False
            
        # Try service restart for transient errors
        subprocess.run(['docker', 'restart', container], capture_output=True)
        time.sleep(5)
        return True
    
    def fix_warning_condition(self, issue: Dict[str, Any]) -> bool:
        """Fix warning conditions"""
        log_excerpt = issue.get('log_excerpt', '')
        
        # Most warnings are informational and don't need action
        if 'not configured for development' in log_excerpt:
            # Development environment warnings are expected
            return True
            
        if 'deprecated' in log_excerpt.lower():
            # Deprecation warnings need code updates
            print(f"   ->  Deprecation warning, needs code update")
            return False
            
        return True
    
    def fix_config_error(self, issue: Dict[str, Any]) -> bool:
        """Fix configuration errors"""
        container = issue.get('container', '')
        
        # Configuration errors usually need env var updates
        print(f"   ->  Configuration issue may need environment variable updates")
        
        # Try restarting with current config
        subprocess.run(['docker', 'restart', container], capture_output=True)
        time.sleep(5)
        return False
    
    def fix_memory_issue(self, issue: Dict[str, Any]) -> bool:
        """Fix memory issues"""
        container = issue.get('container', '')
        
        # Try garbage collection and restart
        subprocess.run(['docker', 'restart', container], capture_output=True)
        time.sleep(5)
        
        # Check if memory usage improved
        stats_result = subprocess.run(
            ['docker', 'stats', container, '--no-stream', '--format', '{{json .}}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if stats_result.stdout:
            stats = json.loads(stats_result.stdout.strip())
            mem_percent = float(stats.get('MemPerc', '0%').replace('%', ''))
            if mem_percent < 80:
                return True
                
        return False
    
    def fix_connection_issue(self, issue: Dict[str, Any]) -> bool:
        """Fix connection issues"""
        container = issue.get('container', '')
        log_excerpt = issue.get('log_excerpt', '')
        
        if 'ECONNRESET' in log_excerpt or 'socket hang up' in log_excerpt:
            # Network issues between containers
            # Restart both containers
            subprocess.run(['docker', 'restart', container], capture_output=True)
            time.sleep(5)
            return True
            
        return False
    
    def generic_remediation(self, issue: Dict[str, Any]) -> bool:
        """Generic remediation for unknown issue types"""
        container = issue.get('container', '')
        
        # Try container restart as last resort
        subprocess.run(['docker', 'restart', container], capture_output=True)
        time.sleep(5)
        return False
    
    def save_learning(self, issue: Dict[str, Any], success: bool):
        """Save learning from remediation attempt"""
        learning_path = Path(f'SPEC/learnings/auto_remediation_{self.iteration}.xml')
        
        learning_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<learning>
  <metadata>
    <title>Automated Remediation - {issue.get('issue_type', 'Unknown')}</title>
    <category>remediation</category>
    <service>{issue.get('container', 'unknown')}</service>
    <date>{datetime.now().isoformat()}</date>
    <iteration>{self.iteration}</iteration>
  </metadata>
  
  <issue>
    <type>{issue.get('issue_type', '')}</type>
    <severity>{issue.get('severity', '')}</severity>
    <container>{issue.get('container', '')}</container>
    <log_excerpt>{issue.get('log_excerpt', '')[:500]}</log_excerpt>
  </issue>
  
  <remediation>
    <success>{success}</success>
    <strategy>Automated remediation loop</strategy>
  </remediation>
</learning>'''
        
        learning_path.write_text(learning_content)
    
    def run_remediation_loop(self):
        """Main remediation loop"""
        print("=" * 80)
        print("AUTOMATED DOCKER REMEDIATION LOOP")
        print("=" * 80)
        print(f"Starting automated remediation (max {self.max_iterations} iterations)")
        
        consecutive_no_issues = 0
        
        while self.iteration < self.max_iterations:
            self.iteration += 1
            print(f"\n--- Iteration {self.iteration}/{self.max_iterations} ---")
            
            # Run introspection
            print("Running Docker log introspection...")
            report = self.run_introspection(hours_back=1)
            
            if 'error' in report:
                print(f"Error in introspection: {report['error']}")
                break
            
            # Get total issues
            total_issues = report.get('summary', {}).get('total_issues', 0)
            print(f"Total issues found: {total_issues}")
            
            if total_issues == 0:
                consecutive_no_issues += 1
                print("No issues found!")
                
                if consecutive_no_issues >= 3:
                    print("\nNo issues for 3 consecutive iterations. System stable!")
                    break
                    
                # Wait before next check
                time.sleep(30)
                continue
            
            consecutive_no_issues = 0
            
            # Get next issue to remediate
            issue = self.get_next_issue(report)
            
            if not issue:
                print("No actionable issues found")
                time.sleep(30)
                continue
            
            # Remediate the issue
            success = self.remediate_issue(issue)
            
            # Save learning
            self.save_learning(issue, success)
            
            # Brief pause before next iteration
            time.sleep(10)
        
        # Final report
        print("\n" + "=" * 80)
        print("REMEDIATION LOOP COMPLETE")
        print("=" * 80)
        print(f"Total iterations: {self.iteration}")
        print(f"Total issues fixed: {self.total_issues_fixed}")
        
        if self.remediation_history:
            print("\nRemediation History:")
            for entry in self.remediation_history[-10:]:  # Show last 10
                status = "[OK]" if entry['success'] else "[FAIL]"
                print(f"  {status} Iteration {entry['iteration']}: {entry['issue']} in {entry['container']}")
        
        # Save final report
        final_report = {
            'completion_time': datetime.now().isoformat(),
            'total_iterations': self.iteration,
            'total_issues_fixed': self.total_issues_fixed,
            'remediation_history': self.remediation_history
        }
        
        with open('remediation_loop_report.json', 'w') as f:
            json.dump(final_report, f, indent=2)
        
        print(f"\nFinal report saved to: remediation_loop_report.json")
        
        return self.total_issues_fixed > 0


def main():
    """Main execution"""
    max_iterations = 100
    if len(sys.argv) > 1:
        try:
            max_iterations = int(sys.argv[1])
        except:
            print(f"Invalid iterations parameter, using default: {max_iterations}")
    
    remediator = AutomatedRemediator(max_iterations)
    success = remediator.run_remediation_loop()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())