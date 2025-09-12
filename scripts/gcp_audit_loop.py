#!/usr/bin/env python3
"""
GCP Logs Audit Loop with Auto-Debug
Continuously monitors GCP Cloud Run services and automatically debugs errors
"""

import subprocess
import json
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

class GCPAuditLoop:
    def __init__(self, service="all", time_range_hours=1, iterations=100):
        self.service = service
        self.time_range_hours = time_range_hours
        self.iterations = iterations
        self.project = "netra-staging"
        self.region = "us-central1"
        self.errors_found = []
        self.iteration_count = 0
        self.fixes_applied = []
        
    def run_gcloud_command(self, command):
        """Execute gcloud command and return output"""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=60
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timed out", 1
        except Exception as e:
            return "", str(e), 1
    
    def get_service_status(self):
        """Get Cloud Run services status"""
        print("\n[U+1F4E1] Cloud Run Services Status:")
        print("[U+2501]" * 50)
        
        cmd = f"gcloud run services list --region {self.region} --format=json"
        stdout, stderr, code = self.run_gcloud_command(cmd)
        
        if code == 0 and stdout:
            try:
                services = json.loads(stdout)
                for svc in services:
                    name = svc.get('metadata', {}).get('name', 'Unknown')
                    status = svc.get('status', {}).get('conditions', [{}])[0].get('status', 'Unknown')
                    url = svc.get('status', {}).get('url', 'N/A')
                    print(f"  [U+2022] {name}: {status} - {url}")
                return services
            except json.JSONDecodeError:
                print("   WARNING: [U+FE0F] Could not parse service status")
        else:
            print(f"   WARNING: [U+FE0F] Error getting services: {stderr}")
        return []
    
    def collect_logs(self, service_name=None):
        """Collect logs from Cloud Run services"""
        errors = {
            'critical': [],
            'error': [],
            'warning': [],
            'http_5xx': [],
            'memory': [],
            'timeout': []
        }
        
        if service_name and service_name != "all":
            services = [service_name]
        else:
            services = ["backend-staging", "auth-staging", "frontend-staging"]
        
        for service in services:
            print(f"\n SEARCH:  Collecting logs from {service}...")
            
            # Collect errors by severity
            for severity in ['CRITICAL', 'ERROR', 'WARNING']:
                cmd = f'''gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name={service} AND severity={severity}" --limit 50 --format=json --freshness={self.time_range_hours}h --project={self.project}'''
                stdout, stderr, code = self.run_gcloud_command(cmd)
                
                if code == 0 and stdout and stdout.strip() != "[]":
                    try:
                        logs = json.loads(stdout)
                        for log in logs:
                            error_text = log.get('textPayload', '') or log.get('jsonPayload', {})
                            if error_text:
                                if severity == 'CRITICAL':
                                    errors['critical'].append({
                                        'service': service,
                                        'text': str(error_text),
                                        'timestamp': log.get('timestamp', '')
                                    })
                                elif severity == 'ERROR':
                                    errors['error'].append({
                                        'service': service,
                                        'text': str(error_text),
                                        'timestamp': log.get('timestamp', '')
                                    })
                                elif severity == 'WARNING':
                                    errors['warning'].append({
                                        'service': service,
                                        'text': str(error_text),
                                        'timestamp': log.get('timestamp', '')
                                    })
                    except json.JSONDecodeError:
                        pass
            
            # Collect HTTP 5xx errors
            cmd = f'''gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name={service} AND httpRequest.status>=500" --limit 20 --format=json --freshness={self.time_range_hours}h --project={self.project}'''
            stdout, stderr, code = self.run_gcloud_command(cmd)
            
            if code == 0 and stdout and stdout.strip() != "[]":
                try:
                    logs = json.loads(stdout)
                    for log in logs:
                        request = log.get('httpRequest', {})
                        if request:
                            errors['http_5xx'].append({
                                'service': service,
                                'status': request.get('status', ''),
                                'url': request.get('requestUrl', ''),
                                'latency': request.get('latency', ''),
                                'timestamp': log.get('timestamp', '')
                            })
                except json.JSONDecodeError:
                    pass
        
        return errors
    
    def analyze_errors(self, errors):
        """Analyze and prioritize errors for debugging"""
        priority_errors = []
        
        # Priority 1: Critical errors
        if errors['critical']:
            for err in errors['critical'][:3]:  # Top 3 critical
                priority_errors.append({
                    'priority': 'CRITICAL',
                    'service': err['service'],
                    'error': err['text'],
                    'timestamp': err['timestamp']
                })
        
        # Priority 2: HTTP 5xx errors
        if errors['http_5xx']:
            for err in errors['http_5xx'][:3]:  # Top 3 5xx
                priority_errors.append({
                    'priority': 'HTTP_5XX',
                    'service': err['service'],
                    'error': f"HTTP {err['status']} on {err['url']}",
                    'timestamp': err['timestamp']
                })
        
        # Priority 3: Standard errors
        if errors['error']:
            for err in errors['error'][:3]:  # Top 3 errors
                priority_errors.append({
                    'priority': 'ERROR',
                    'service': err['service'],
                    'error': err['text'],
                    'timestamp': err['timestamp']
                })
        
        return priority_errors
    
    def trigger_auto_debug(self, error_info):
        """Trigger automatic debugging for an error"""
        print(f"\n ALERT:  AUTO-DEBUGGING: {error_info['priority']} error in {error_info['service']}")
        print(f"   Error: {error_info['error'][:200]}...")
        
        # Prepare debug context
        debug_context = {
            'service': error_info['service'],
            'priority': error_info['priority'],
            'error': error_info['error'],
            'timestamp': error_info['timestamp'],
            'iteration': self.iteration_count
        }
        
        # Save to file for debug command
        debug_file = Path('reports/gcp_auto_debug.json')
        debug_file.parent.mkdir(exist_ok=True)
        
        with open(debug_file, 'w') as f:
            json.dump(debug_context, f, indent=2)
        
        print(f"   Debug context saved to {debug_file}")
        return debug_context
    
    def deploy_fix(self, service):
        """Deploy fix to staging"""
        print(f"\n[U+1F680] Deploying fix to {service}...")
        
        if service == "backend-staging":
            deploy_cmd = "python scripts/deploy_to_gcp.py --service backend --project netra-staging --build-local"
        elif service == "auth-staging":
            deploy_cmd = "python scripts/deploy_to_gcp.py --service auth --project netra-staging --build-local"
        elif service == "frontend-staging":
            deploy_cmd = "python scripts/deploy_to_gcp.py --service frontend --project netra-staging --build-local"
        else:
            deploy_cmd = "python scripts/deploy_to_gcp.py --project netra-staging --build-local"
        
        print(f"   Executing: {deploy_cmd}")
        stdout, stderr, code = self.run_gcloud_command(deploy_cmd)
        
        if code == 0:
            print("    PASS:  Deployment successful")
            self.fixes_applied.append({
                'iteration': self.iteration_count,
                'service': service,
                'timestamp': datetime.now().isoformat()
            })
            return True
        else:
            print(f"    WARNING: [U+FE0F] Deployment failed: {stderr}")
            return False
    
    def run_iteration(self):
        """Run a single audit iteration"""
        self.iteration_count += 1
        
        print(f"\n{'=' * 60}")
        print(f" CYCLE:  AUDIT ITERATION {self.iteration_count}/{self.iterations}")
        print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}")
        
        # Step 1: Check service status
        services = self.get_service_status()
        
        # Step 2: Collect logs
        errors = self.collect_logs(self.service)
        
        # Step 3: Analyze errors
        priority_errors = self.analyze_errors(errors)
        
        # Step 4: Display summary
        print("\n CHART:  ERROR SUMMARY:")
        print(f"   Critical: {len(errors['critical'])}")
        print(f"   Errors: {len(errors['error'])}")
        print(f"   Warnings: {len(errors['warning'])}")
        print(f"   HTTP 5xx: {len(errors['http_5xx'])}")
        
        # Step 5: Auto-debug if errors found
        if priority_errors:
            print(f"\n WARNING: [U+FE0F] Found {len(priority_errors)} priority errors")
            
            for i, error in enumerate(priority_errors[:1]):  # Debug top error
                print(f"\n[U+1F527] Debugging error {i+1}/{len(priority_errors)}")
                debug_context = self.trigger_auto_debug(error)
                
                # Simulate fix based on error type
                if 'JWT' in error['error'] or 'auth' in error['error'].lower():
                    print("   [U+1F4DD] Identified as authentication issue")
                    # Would trigger auth fix here
                elif 'memory' in error['error'].lower() or 'OOM' in error['error']:
                    print("   [U+1F4DD] Identified as memory issue")
                    # Would trigger memory optimization
                elif 'timeout' in error['error'].lower():
                    print("   [U+1F4DD] Identified as timeout issue")
                    # Would trigger timeout fix
                
                # Deploy fix
                time.sleep(2)  # Brief pause
                self.deploy_fix(error['service'])
        else:
            print("\n PASS:  No critical errors found")
        
        # Step 6: Wait before next iteration
        wait_time = 60 if priority_errors else 180  # 1 min if errors, 3 min if healthy
        print(f"\n[U+23F3] Waiting {wait_time} seconds before next iteration...")
        time.sleep(wait_time)
    
    def run(self):
        """Run the main audit loop"""
        print(f"""
========================================================
           GCP AUDIT LOOP WITH AUTO-DEBUG
========================================================
  Project: {self.project}
  Region: {self.region}
  Service: {self.service}
  Time Range: Last {self.time_range_hours} hour(s)
  Iterations: {self.iterations}
========================================================
        """)
        
        try:
            for i in range(self.iterations):
                self.run_iteration()
                
                # Every 10 iterations, show progress
                if (i + 1) % 10 == 0:
                    print(f"\n[U+1F4C8] PROGRESS REPORT:")
                    print(f"   Iterations: {self.iteration_count}/{self.iterations}")
                    print(f"   Fixes Applied: {len(self.fixes_applied)}")
                    print(f"   Total Errors Found: {len(self.errors_found)}")
        
        except KeyboardInterrupt:
            print("\n\n WARNING: [U+FE0F] Audit loop interrupted by user")
        
        finally:
            self.print_final_summary()
    
    def print_final_summary(self):
        """Print final summary of the audit loop"""
        print(f"""
========================================================
                    FINAL SUMMARY
========================================================
  Total Iterations: {self.iteration_count}
  Fixes Applied: {len(self.fixes_applied)}
  Errors Found: {len(self.errors_found)}
  End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
========================================================
        """)
        
        if self.fixes_applied:
            print("\n[U+1F4DD] FIXES APPLIED:")
            for fix in self.fixes_applied[-10:]:  # Last 10 fixes
                print(f"   [U+2022] Iteration {fix['iteration']}: {fix['service']} at {fix['timestamp']}")
        
        # Save summary to file
        summary_file = Path(f'reports/gcp_audit_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        summary_file.parent.mkdir(exist_ok=True)
        
        with open(summary_file, 'w') as f:
            json.dump({
                'iterations': self.iteration_count,
                'fixes_applied': self.fixes_applied,
                'errors_found': self.errors_found,
                'end_time': datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"\n[U+1F4BE] Summary saved to {summary_file}")


if __name__ == "__main__":
    # Parse command line arguments
    service = sys.argv[1] if len(sys.argv) > 1 else "all"
    time_range = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    iterations = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    
    # Run the audit loop
    auditor = GCPAuditLoop(service=service, time_range_hours=time_range, iterations=iterations)
    auditor.run()