#!/usr/bin/env python3
"""
SAFE GCP Log Fetcher - Last 1 Hour
CRITICAL MISSION: Safely fetch netra-backend logs with FIRST DO NO HARM principle
READ-ONLY operations only - NO modifications to infrastructure
"""

import subprocess
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# Set UTF-8 encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

class SafeGCPLogFetcher:
    """SAFE READ-ONLY GCP log fetcher with comprehensive error checking"""
    
    def __init__(self):
        self.project = "netra-staging"
        self.service_name = "netra-backend"
        self.current_time = datetime.now(timezone.utc).replace(tzinfo=None)  # Remove timezone for GCP format
        self.one_hour_ago = self.current_time - timedelta(hours=1)
        
        print("🛡️ SAFETY FIRST: READ-ONLY GCP LOG OPERATION")
        print("=" * 60)
        print(f"Current UTC Time: {self.current_time.isoformat()}Z")
        print(f"Fetching logs from: {self.one_hour_ago.isoformat()}Z")
        print(f"Project: {self.project}")
        print(f"Service: {self.service_name}")
        print("=" * 60)

    def run_safe_command(self, cmd, timeout=120):
        """Execute READ-ONLY command safely with error handling"""
        try:
            # SAFETY CHECK: Ensure this is a read-only operation (allow auth check too)
            allowed_commands = ["gcloud logging read", "gcloud auth list"]
            if not any(cmd.strip().startswith(allowed_cmd) for allowed_cmd in allowed_commands):
                raise ValueError(f"SAFETY VIOLATION: Only safe read-only commands allowed. Got: {cmd[:50]}")
            
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
            return "", "Command timed out after 120 seconds", 1
        except Exception as e:
            return "", f"Safe execution error: {str(e)}", 1

    def check_authentication(self):
        """Safely check GCP authentication status"""
        print("\n🔐 SAFETY CHECK: Verifying GCP Authentication...")
        
        auth_cmd = "gcloud auth list --filter=status:ACTIVE --format=\"value(account)\""
        stdout, stderr, code = self.run_safe_command(auth_cmd)
        
        if code == 0 and stdout.strip():
            account = stdout.strip()
            print(f"✅ Authenticated as: {account}")
            
            # Verify we have the staging service account
            if "netra-staging" in account:
                print("✅ Using staging service account - SAFE to proceed")
                return True
            else:
                print(f"⚠️ WARNING: Using account {account} - not staging service account")
                print("This may have limited permissions")
                return True
        else:
            print("❌ NOT AUTHENTICATED")
            print("Please run: gcloud auth login")
            if stderr:
                print(f"Error: {stderr}")
            return False

    def fetch_recent_log_sample(self):
        """First get a recent log sample to understand timezone and format"""
        print("\n🔍 STEP 1: Getting recent log sample for timezone verification...")
        
        cmd = f'''gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name={self.service_name}" --limit=1 --format=json --project={self.project}'''
        
        stdout, stderr, code = self.run_safe_command(cmd)
        
        if code == 0 and stdout.strip():
            try:
                logs = json.loads(stdout)
                if logs:
                    sample_log = logs[0]
                    sample_timestamp = sample_log.get('timestamp', '')
                    print(f"✅ Recent log found - Timestamp: {sample_timestamp}")
                    print(f"   Service: {sample_log.get('resource', {}).get('labels', {}).get('service_name', 'unknown')}")
                    print(f"   Severity: {sample_log.get('severity', 'unknown')}")
                    return True
                else:
                    print("⚠️ No recent logs found")
                    return False
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
                return False
        else:
            if stderr:
                print(f"❌ Error: {stderr}")
            else:
                print("❌ No logs returned")
            return False

    def fetch_logs_last_hour(self):
        """Safely fetch logs from the last hour with comprehensive filtering"""
        print("\n📊 STEP 2: Fetching logs from last 1 hour...")
        
        # Format timestamps for GCP (RFC3339 format without timezone suffix since we're using UTC)
        start_time = self.one_hour_ago.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        end_time = self.current_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        print(f"Time range: {start_time} to {end_time}")
        
        # Try multiple service name patterns to ensure we catch all logs
        service_patterns = [
            self.service_name,
            f"{self.service_name}-staging", 
            "netra-backend-staging",
            "netra-service"
        ]
        
        all_logs = []
        
        for service_pattern in service_patterns:
            print(f"\n🔍 Searching for service pattern: {service_pattern}")
            
            # Comprehensive query for all severity levels
            cmd = f'''gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name={service_pattern} AND timestamp>=\\"{start_time}\\" AND timestamp<=\\"{end_time}\\"" --limit=500 --format=json --project={self.project}'''
            
            stdout, stderr, code = self.run_safe_command(cmd, timeout=180)
            
            if code == 0 and stdout.strip():
                try:
                    logs = json.loads(stdout)
                    if logs:
                        print(f"  ✅ Found {len(logs)} logs for {service_pattern}")
                        all_logs.extend(logs)
                    else:
                        print(f"  📝 No logs for {service_pattern}")
                except json.JSONDecodeError as e:
                    print(f"  ❌ JSON decode error for {service_pattern}: {e}")
            else:
                if stderr:
                    print(f"  ⚠️ Query error for {service_pattern}: {stderr}")
                else:
                    print(f"  📝 No data returned for {service_pattern}")
        
        return all_logs

    def analyze_logs_comprehensive(self, logs):
        """Comprehensive analysis of fetched logs organized by severity"""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE LOG ANALYSIS - LAST 1 HOUR")
        print("=" * 80)
        
        if not logs:
            print("⚠️ NO LOGS FOUND")
            print("Possible reasons:")
            print("  • Service was not active in the last hour")
            print("  • Service name pattern doesn't match")
            print("  • Network or permission issues")
            return None
        
        # Organize logs by severity
        logs_by_severity = defaultdict(list)
        service_counts = defaultdict(int)
        timestamp_range = {"earliest": None, "latest": None}
        
        for log in logs:
            severity = log.get('severity', 'UNKNOWN')
            service = log.get('resource', {}).get('labels', {}).get('service_name', 'unknown')
            timestamp = log.get('timestamp', '')
            
            logs_by_severity[severity].append(log)
            service_counts[service] += 1
            
            # Track timestamp range
            if timestamp:
                if not timestamp_range["earliest"] or timestamp < timestamp_range["earliest"]:
                    timestamp_range["earliest"] = timestamp
                if not timestamp_range["latest"] or timestamp > timestamp_range["latest"]:
                    timestamp_range["latest"] = timestamp
        
        # Summary statistics
        total_logs = len(logs)
        error_count = len(logs_by_severity.get('ERROR', [])) + len(logs_by_severity.get('CRITICAL', []))
        warning_count = len(logs_by_severity.get('WARNING', []))
        info_count = len(logs_by_severity.get('INFO', []))
        
        print(f"\n📈 SUMMARY STATISTICS:")
        print(f"  Total logs collected: {total_logs}")
        print(f"  ERROR/CRITICAL count: {error_count}")
        print(f"  WARNING count: {warning_count}")
        print(f"  INFO count: {info_count}")
        print(f"  Timestamp range: {timestamp_range['earliest']} to {timestamp_range['latest']}")
        print(f"  Timezone: UTC")
        
        print(f"\n🏷️ SERVICE BREAKDOWN:")
        for service, count in sorted(service_counts.items()):
            print(f"  {service}: {count} logs")
        
        # Detailed analysis by severity level
        severity_order = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'UNKNOWN']
        
        for severity in severity_order:
            if severity in logs_by_severity:
                severity_logs = logs_by_severity[severity]
                print(f"\n{'🚨' if severity in ['CRITICAL', 'ERROR'] else '⚠️' if severity == 'WARNING' else '📋'} {severity} LOGS ({len(severity_logs)} found):")
                
                # Show detailed context for errors and warnings
                for i, log in enumerate(severity_logs[:5]):  # Show first 5 of each severity
                    timestamp = log.get('timestamp', 'No timestamp')
                    service = log.get('resource', {}).get('labels', {}).get('service_name', 'unknown')
                    
                    # Extract message from various payload types
                    message = ""
                    context = {}
                    
                    if 'textPayload' in log:
                        message = log['textPayload']
                    elif 'jsonPayload' in log:
                        jp = log['jsonPayload']
                        message = jp.get('message', '')
                        context = {
                            'context': jp.get('context', {}),
                            'labels': jp.get('labels', {}),
                            'module': jp.get('context', {}).get('module', ''),
                            'function': jp.get('context', {}).get('function', ''),
                            'line': jp.get('context', {}).get('line', ''),
                        }
                    
                    print(f"\n  [{i+1}] {timestamp}")
                    print(f"      Service: {service}")
                    if message:
                        print(f"      Message: {message[:300]}{'...' if len(message) > 300 else ''}")
                    if context.get('context'):
                        print(f"      Context: {context['context']}")
                    if 'httpRequest' in log:
                        http_req = log['httpRequest']
                        print(f"      HTTP: {http_req.get('requestMethod', '')} {http_req.get('requestUrl', '')} -> {http_req.get('status', '')}")
                    
                    # Show traceback for errors
                    if severity in ['CRITICAL', 'ERROR'] and 'jsonPayload' in log:
                        jp = log['jsonPayload']
                        if 'traceback' in jp or 'stack_trace' in jp:
                            traceback = jp.get('traceback', jp.get('stack_trace', ''))
                            if traceback:
                                print(f"      Traceback: {traceback[:200]}{'...' if len(traceback) > 200 else ''}")
                
                if len(severity_logs) > 5:
                    print(f"      ... and {len(severity_logs) - 5} more {severity} logs")
        
        # Save raw JSON for further analysis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"netra_backend_logs_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 RAW DATA SAVED:")
        print(f"  File: {output_file}")
        print(f"  Size: {len(logs)} log entries")
        print(f"  Format: Complete GCP JSON payloads")
        
        return {
            'total_logs': total_logs,
            'error_count': error_count,
            'warning_count': warning_count,
            'info_count': info_count,
            'logs_by_severity': dict(logs_by_severity),
            'service_counts': dict(service_counts),
            'timestamp_range': timestamp_range,
            'output_file': output_file
        }

    def run_safe_fetch(self):
        """Main safe execution method with comprehensive error handling"""
        print("🛡️ STARTING SAFE GCP LOG FETCH OPERATION")
        print("SAFETY PROTOCOL: READ-ONLY OPERATIONS ONLY")
        
        # Step 1: Authentication check
        if not self.check_authentication():
            print("\n❌ SAFETY ABORT: Authentication failed")
            return None
        
        # Step 2: Get recent sample for verification
        if not self.fetch_recent_log_sample():
            print("\n⚠️ WARNING: No recent logs found, but continuing...")
        
        # Step 3: Fetch logs from last hour
        logs = self.fetch_logs_last_hour()
        
        # Step 4: Comprehensive analysis
        analysis = self.analyze_logs_comprehensive(logs)
        
        if analysis:
            print("\n✅ SAFE FETCH COMPLETED SUCCESSFULLY")
            print(f"📊 Analysis complete: {analysis['total_logs']} logs processed")
            if analysis['error_count'] > 0:
                print(f"🚨 ATTENTION: {analysis['error_count']} errors found requiring investigation")
            if analysis['warning_count'] > 0:
                print(f"⚠️ ATTENTION: {analysis['warning_count']} warnings found")
            return analysis
        else:
            print("\n📝 FETCH COMPLETED - No logs found in time range")
            return None

if __name__ == "__main__":
    print("🛡️ SAFE GCP LOG FETCHER - NETRA BACKEND")
    print("READ-ONLY OPERATION - FIRST DO NO HARM")
    print("=" * 60)
    
    fetcher = SafeGCPLogFetcher()
    result = fetcher.run_safe_fetch()
    
    if result:
        print(f"\n🎯 MISSION COMPLETE:")
        print(f"  ✅ Safely fetched and analyzed {result['total_logs']} logs")
        print(f"  📁 Raw data saved to: {result['output_file']}")
        print(f"  🕐 Time range: Last 1 hour UTC")
        print(f"  🏷️ Services: {list(result['service_counts'].keys())}")
        
        if result['error_count'] > 0 or result['warning_count'] > 0:
            print(f"\n🔍 NEXT ACTIONS RECOMMENDED:")
            print(f"  • Review {result['error_count']} errors for critical issues")
            print(f"  • Investigate {result['warning_count']} warnings for potential problems")
            print(f"  • Use saved JSON file for detailed root cause analysis")
    else:
        print(f"\n📝 NO LOGS FOUND - System may be quiet or service inactive")