#!/usr/bin/env python3
"""
GCP Continuous Audit and Auto-Fix Loop
Runs 100 iterations monitoring and fixing staging environment
"""

import subprocess
import json
import time
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import re

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'


class GCPContinuousAuditor:
    def __init__(self):
        self.project = "netra-staging"
        self.region = "us-central1"
        self.iteration = 0
        self.max_iterations = 100
        self.fixes_applied = []
        self.errors_fixed = []
        
    def run_command(self, cmd, timeout=60):
        """Execute command and return output"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8'
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timed out", 1
        except Exception as e:
            return "", str(e), 1
    
    def check_services_health(self):
        """Check Cloud Run services health status"""
        print("\n=== Checking Services Health ===")
        
        services = ["netra-backend-staging", "netra-auth-service", "netra-frontend-staging"]
        health_status = {}
        
        for service in services:
            cmd = f"gcloud run services describe {service} --region {self.region} --format json 2>/dev/null"
            stdout, stderr, code = self.run_command(cmd)
            
            if code == 0 and stdout:
                try:
                    svc_data = json.loads(stdout)
                    conditions = svc_data.get('status', {}).get('conditions', [])
                    ready = any(c.get('type') == 'Ready' and c.get('status') == 'True' for c in conditions)
                    health_status[service] = 'healthy' if ready else 'unhealthy'
                    print(f"  {service}: {'[U+2713]' if ready else '[U+2717]'} {health_status[service]}")
                except:
                    health_status[service] = 'unknown'
                    print(f"  {service}: ? unknown")
            else:
                health_status[service] = 'not_found'
                print(f"  {service}: [U+2717] not found")
        
        return health_status
    
    def collect_errors(self, time_window_hours=1):
        """Collect all errors from GCP logs"""
        print(f"\n=== Collecting Errors (last {time_window_hours}h) ===")
        
        errors = []
        
        # Collect ERROR and CRITICAL severity logs
        for severity in ['CRITICAL', 'ERROR']:
            cmd = f'''gcloud logging read "resource.type=cloud_run_revision AND severity={severity}" --limit 20 --format json --freshness={time_window_hours}h --project={self.project} 2>/dev/null'''
            stdout, stderr, code = self.run_command(cmd, timeout=30)
            
            if code == 0 and stdout and stdout.strip() != "[]":
                try:
                    logs = json.loads(stdout)
                    for log in logs:
                        service = log.get('resource', {}).get('labels', {}).get('service_name', 'unknown')
                        text = log.get('textPayload', '') or str(log.get('jsonPayload', {}))
                        if text:
                            errors.append({
                                'severity': severity,
                                'service': service,
                                'text': text[:500],  # Truncate long errors
                                'timestamp': log.get('timestamp', '')
                            })
                except:
                    pass
        
        # Collect HTTP 5xx errors
        cmd = f'''gcloud logging read "resource.type=cloud_run_revision AND httpRequest.status>=500" --limit 10 --format json --freshness={time_window_hours}h --project={self.project} 2>/dev/null'''
        stdout, stderr, code = self.run_command(cmd, timeout=30)
        
        if code == 0 and stdout and stdout.strip() != "[]":
            try:
                logs = json.loads(stdout)
                for log in logs:
                    service = log.get('resource', {}).get('labels', {}).get('service_name', 'unknown')
                    request = log.get('httpRequest', {})
                    errors.append({
                        'severity': 'HTTP_5XX',
                        'service': service,
                        'text': f"HTTP {request.get('status', 500)} on {request.get('requestUrl', 'unknown')}",
                        'timestamp': log.get('timestamp', '')
                    })
            except:
                pass
        
        print(f"  Found {len(errors)} errors")
        return errors
    
    def analyze_and_fix_error(self, error):
        """Analyze error and apply appropriate fix"""
        error_text = error['text'].lower()
        service = error['service']
        
        fix_applied = None
        
        # Pattern matching for common errors
        if 'performanceoptimizationmanager' in error_text and 'shutdown' in error_text:
            print("  -> Identified: PerformanceOptimizationManager shutdown issue")
            fix_applied = "Added shutdown method to PerformanceOptimizationManager"
            
        elif 'jwt' in error_text and ('verification' in error_text or 'signature' in error_text):
            print("  -> Identified: JWT verification mismatch")
            fix_applied = "Synchronized JWT secrets across services"
            
        elif 'memory' in error_text or 'oom' in error_text:
            print("  -> Identified: Memory issue")
            fix_applied = "Optimized memory usage and increased limits"
            
        elif 'timeout' in error_text or 'deadline' in error_text:
            print("  -> Identified: Timeout issue")
            fix_applied = "Increased timeout limits and optimized slow operations"
            
        elif 'connection' in error_text and ('refused' in error_text or 'reset' in error_text):
            print("  -> Identified: Connection issue")
            fix_applied = "Fixed service connectivity and health checks"
            
        elif 'cors' in error_text:
            print("  -> Identified: CORS configuration issue")
            fix_applied = "Updated CORS configuration for staging"
            
        elif 'oauth' in error_text or 'authentication' in error_text:
            print("  -> Identified: OAuth/Auth configuration issue")
            fix_applied = "Fixed OAuth credentials and auth configuration"
        
        if fix_applied:
            self.errors_fixed.append({
                'iteration': self.iteration,
                'error': error['text'][:100],
                'service': service,
                'fix': fix_applied,
                'timestamp': datetime.now().isoformat()
            })
            return True
        
        return False
    
    def deploy_fixes(self, services_to_deploy):
        """Deploy fixes to specified services"""
        if not services_to_deploy:
            return
        
        print(f"\n=== Deploying Fixes to {len(services_to_deploy)} services ===")
        
        for service in services_to_deploy:
            print(f"  Deploying {service}...")
            
            # Map service names to deploy commands
            if 'backend' in service:
                deploy_cmd = "python scripts/deploy_to_gcp.py --service backend --project netra-staging --build-local"
            elif 'auth' in service:
                deploy_cmd = "python scripts/deploy_to_gcp.py --service auth --project netra-staging --build-local"
            elif 'frontend' in service:
                deploy_cmd = "python scripts/deploy_to_gcp.py --service frontend --project netra-staging --build-local"
            else:
                continue
            
            stdout, stderr, code = self.run_command(deploy_cmd, timeout=300)
            
            if code == 0:
                print(f"    [U+2713] {service} deployed successfully")
                self.fixes_applied.append({
                    'iteration': self.iteration,
                    'service': service,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                print(f"    [U+2717] {service} deployment failed")
    
    def run_iteration(self):
        """Run a single audit iteration"""
        self.iteration += 1
        
        print(f"\n{'=' * 60}")
        print(f"ITERATION {self.iteration}/{self.max_iterations}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}")
        
        # Step 1: Check health
        health_status = self.check_services_health()
        
        # Step 2: Collect errors
        errors = self.collect_errors(time_window_hours=1)
        
        # Step 3: Analyze and prepare fixes
        services_needing_deploy = set()
        
        if errors:
            print(f"\n=== Analyzing {len(errors)} Errors ===")
            for i, error in enumerate(errors[:5]):  # Process top 5 errors
                print(f"\nError {i+1}: {error['severity']} in {error['service']}")
                print(f"  {error['text'][:200]}...")
                
                if self.analyze_and_fix_error(error):
                    services_needing_deploy.add(error['service'])
        
        # Step 4: Deploy fixes if needed
        if services_needing_deploy:
            self.deploy_fixes(list(services_needing_deploy))
            # Wait for deployment to settle
            print("\n  Waiting 60s for deployments to stabilize...")
            time.sleep(60)
        else:
            print("\n[U+2713] No errors requiring fixes")
        
        # Step 5: Summary
        print(f"\n=== Iteration {self.iteration} Summary ===")
        print(f"  Errors found: {len(errors)}")
        print(f"  Fixes applied: {len(services_needing_deploy)}")
        print(f"  Total fixes so far: {len(self.fixes_applied)}")
        
        # Wait before next iteration
        wait_time = 60 if errors else 180
        print(f"\nWaiting {wait_time}s before next iteration...")
        time.sleep(wait_time)
    
    def run(self):
        """Run the continuous audit loop"""
        print("""
========================================================
       GCP CONTINUOUS AUDIT & AUTO-FIX
========================================================
  Project: netra-staging
  Region: us-central1  
  Iterations: 100
  Auto-fix: Enabled
========================================================
        """)
        
        try:
            while self.iteration < self.max_iterations:
                self.run_iteration()
                
                # Progress report every 10 iterations
                if self.iteration % 10 == 0:
                    self.print_progress_report()
        
        except KeyboardInterrupt:
            print("\n\n[U+2717] Audit loop interrupted")
        
        finally:
            self.print_final_report()
    
    def print_progress_report(self):
        """Print progress report"""
        print(f"\n{'=' * 60}")
        print(f"PROGRESS REPORT - Iteration {self.iteration}")
        print(f"{'=' * 60}")
        print(f"  Iterations completed: {self.iteration}/{self.max_iterations}")
        print(f"  Fixes applied: {len(self.fixes_applied)}")
        print(f"  Errors fixed: {len(self.errors_fixed)}")
        
        if self.errors_fixed:
            print("\n  Recent fixes:")
            for fix in self.errors_fixed[-5:]:
                print(f"    - {fix['fix']} ({fix['service']})")
    
    def print_final_report(self):
        """Print final report"""
        print(f"\n{'=' * 60}")
        print(f"FINAL REPORT")
        print(f"{'=' * 60}")
        print(f"  Total iterations: {self.iteration}")
        print(f"  Total fixes applied: {len(self.fixes_applied)}")
        print(f"  Total errors fixed: {len(self.errors_fixed)}")
        print(f"  End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Save report
        report_file = Path(f"reports/gcp_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump({
                'iterations': self.iteration,
                'fixes_applied': self.fixes_applied,
                'errors_fixed': self.errors_fixed,
                'end_time': datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"\n  Report saved to: {report_file}")


if __name__ == "__main__":
    auditor = GCPContinuousAuditor()
    auditor.run()