#!/usr/bin/env python3
"""
OAuth Health Monitor for Cloud Armor

Continuously monitors OAuth callback health and alerts on issues.
Can be run as a cron job or continuous monitoring service.

Usage:
    python scripts/monitor_oauth_health.py --once          # Single check
    python scripts/monitor_oauth_health.py --continuous    # Run continuously
    python scripts/monitor_oauth_health.py --alert-webhook <URL>  # Send alerts
"""

import argparse
import json
import subprocess
import time
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import requests
from pathlib import Path


class OAuthHealthMonitor:
    """Monitor OAuth health and Cloud Armor blocks."""
    
    def __init__(
        self,
        environment: str = "staging",
        alert_webhook: Optional[str] = None,
        alert_threshold: int = 5
    ):
        """Initialize the monitor.
        
        Args:
            environment: Environment to monitor (staging/production)
            alert_webhook: Webhook URL for alerts (Slack, Discord, etc.)
            alert_threshold: Number of blocks before alerting
        """
        self.environment = environment
        self.alert_webhook = alert_webhook
        self.alert_threshold = alert_threshold
        self.project = "netra-staging" if environment == "staging" else "netra-production"
        
        # Track state for rate limiting alerts
        self.last_alert_time = None
        self.alert_cooldown = 300  # 5 minutes between alerts
        
    def check_oauth_blocks(self, minutes: int = 5) -> Dict:
        """Check for recent OAuth blocks in Cloud Armor.
        
        Args:
            minutes: How many minutes back to check
            
        Returns:
            Dictionary with block information
        """
        # Calculate time window
        start_time = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
        
        # Query for OAuth blocks
        filter_expr = (
            f'resource.type="http_load_balancer" '
            f'AND jsonPayload.statusDetails="denied_by_security_policy" '
            f'AND httpRequest.requestUrl=~"/auth/callback" '
            f'AND timestamp>="{start_time}"'
        )
        
        cmd = [
            "gcloud", "logging", "read",
            filter_expr,
            "--limit=100",
            "--format=json",
            f"--project={self.project}"
        ]
        
        try:
            # Use shell=True on Windows
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=(os.name == 'nt'),
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                logs = json.loads(result.stdout)
                
                # Analyze blocks
                blocks = []
                for log in logs:
                    http_request = log.get("httpRequest", {})
                    json_payload = log.get("jsonPayload", {})
                    security_policy = json_payload.get("enforcedSecurityPolicy", {})
                    
                    blocks.append({
                        "timestamp": log.get("timestamp"),
                        "url": http_request.get("requestUrl"),
                        "status": http_request.get("status"),
                        "remote_ip": http_request.get("remoteIp"),
                        "rule": security_policy.get("preconfiguredExprIds", []),
                        "user_agent": http_request.get("userAgent")
                    })
                
                return {
                    "status": "WARNING" if len(blocks) > 0 else "OK",
                    "blocks_count": len(blocks),
                    "blocks": blocks[:10],  # Limit to 10 for readability
                    "time_window_minutes": minutes
                }
            else:
                return {
                    "status": "OK",
                    "blocks_count": 0,
                    "blocks": [],
                    "time_window_minutes": minutes
                }
                
        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "blocks_count": 0,
                "time_window_minutes": minutes
            }
    
    def check_oauth_success_rate(self, minutes: int = 60) -> Dict:
        """Calculate OAuth success rate.
        
        Args:
            minutes: Time window to check
            
        Returns:
            Dictionary with success rate information
        """
        start_time = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
        
        # Query for all OAuth callbacks
        filter_all = (
            f'resource.type="http_load_balancer" '
            f'AND httpRequest.requestUrl=~"/auth/callback" '
            f'AND timestamp>="{start_time}"'
        )
        
        # Query for successful OAuth callbacks
        filter_success = (
            f'resource.type="http_load_balancer" '
            f'AND httpRequest.requestUrl=~"/auth/callback" '
            f'AND (httpRequest.status=200 OR httpRequest.status=302) '
            f'AND timestamp>="{start_time}"'
        )
        
        try:
            # Count total attempts
            cmd_all = [
                "gcloud", "logging", "read",
                filter_all,
                "--format=value(timestamp)",
                f"--project={self.project}"
            ]
            
            result_all = subprocess.run(
                cmd_all,
                capture_output=True,
                text=True,
                shell=(os.name == 'nt'),
                timeout=30
            )
            
            total_count = len(result_all.stdout.strip().split('\n')) if result_all.stdout.strip() else 0
            
            # Count successful attempts
            cmd_success = [
                "gcloud", "logging", "read",
                filter_success,
                "--format=value(timestamp)",
                f"--project={self.project}"
            ]
            
            result_success = subprocess.run(
                cmd_success,
                capture_output=True,
                text=True,
                shell=(os.name == 'nt'),
                timeout=30
            )
            
            success_count = len(result_success.stdout.strip().split('\n')) if result_success.stdout.strip() else 0
            
            # Calculate success rate
            if total_count > 0:
                success_rate = (success_count / total_count) * 100
            else:
                success_rate = 100.0  # No attempts means no failures
            
            return {
                "status": "OK" if success_rate >= 95 else "WARNING" if success_rate >= 90 else "CRITICAL",
                "success_rate": round(success_rate, 2),
                "total_attempts": total_count,
                "successful_attempts": success_count,
                "failed_attempts": total_count - success_count,
                "time_window_minutes": minutes
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "success_rate": 0,
                "time_window_minutes": minutes
            }
    
    def check_security_rule_status(self) -> Dict:
        """Verify OAuth exception rule is active.
        
        Returns:
            Dictionary with rule status
        """
        cmd = [
            "gcloud", "compute", "security-policies", "rules", "describe", "50",
            "--security-policy=staging-security-policy",
            f"--project={self.project}",
            "--format=json"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=(os.name == 'nt'),
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                rule = json.loads(result.stdout)[0] if json.loads(result.stdout) else {}
                
                # Verify rule configuration
                is_correct = (
                    rule.get("priority") == 50 and
                    rule.get("action") == "allow" and
                    "/auth/callback" in str(rule.get("match", {}))
                )
                
                return {
                    "status": "OK" if is_correct else "CRITICAL",
                    "rule_exists": True,
                    "priority": rule.get("priority"),
                    "action": rule.get("action"),
                    "description": rule.get("description"),
                    "configuration_correct": is_correct
                }
            else:
                return {
                    "status": "CRITICAL",
                    "rule_exists": False,
                    "error": "OAuth exception rule not found"
                }
                
        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e)
            }
    
    def send_alert(self, message: str, severity: str = "warning") -> bool:
        """Send alert to configured webhook.
        
        Args:
            message: Alert message
            severity: Alert severity (info/warning/critical)
            
        Returns:
            True if alert sent successfully
        """
        if not self.alert_webhook:
            return False
        
        # Rate limit alerts
        now = datetime.now(timezone.utc)
        if self.last_alert_time:
            time_since_last = (now - self.last_alert_time).total_seconds()
            if time_since_last < self.alert_cooldown:
                return False
        
        # Format for common webhook formats
        payload = {
            "text": f"[ALERT] OAuth Monitor Alert ({self.environment})",
            "attachments": [{
                "color": "danger" if severity == "critical" else "warning",
                "text": message,
                "footer": f"Environment: {self.environment}",
                "ts": int(now.timestamp())
            }]
        }
        
        try:
            response = requests.post(
                self.alert_webhook,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self.last_alert_time = now
                return True
            
        except Exception as e:
            print(f"Failed to send alert: {e}")
        
        return False
    
    def generate_health_report(self) -> Dict:
        """Generate comprehensive health report.
        
        Returns:
            Complete health status dictionary
        """
        print(f"\n{'='*60}")
        print(f"OAuth Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Environment: {self.environment}")
        print(f"{'='*60}")
        
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": self.environment,
            "checks": {}
        }
        
        # Check 1: Recent OAuth blocks (5 min window)
        print("\n[*] Checking recent OAuth blocks...")
        blocks_check = self.check_oauth_blocks(minutes=5)
        report["checks"]["recent_blocks"] = blocks_check
        
        status_icon = "[OK]" if blocks_check["status"] == "OK" else "[WARNING]" if blocks_check["status"] == "WARNING" else "[ERROR]"
        print(f"{status_icon} Blocks in last 5 min: {blocks_check['blocks_count']}")
        
        # Check 2: OAuth success rate (1 hour window)
        print("\n[*] Checking OAuth success rate...")
        success_check = self.check_oauth_success_rate(minutes=60)
        report["checks"]["success_rate"] = success_check
        
        if "error" not in success_check:
            status_icon = "[OK]" if success_check["status"] == "OK" else "[WARNING]" if success_check["status"] == "WARNING" else "[ERROR]"
            print(f"{status_icon} Success rate (1hr): {success_check['success_rate']}%")
            print(f"   Total attempts: {success_check['total_attempts']}")
            print(f"   Successful: {success_check['successful_attempts']}")
            print(f"   Failed: {success_check['failed_attempts']}")
        
        # Check 3: Security rule status
        print("\n[*] Checking security rule configuration...")
        rule_check = self.check_security_rule_status()
        report["checks"]["security_rule"] = rule_check
        
        status_icon = "[OK]" if rule_check["status"] == "OK" else "[ERROR]"
        print(f"{status_icon} OAuth exception rule: {'Active' if rule_check.get('rule_exists') else 'Missing'}")
        
        # Overall health status
        all_statuses = [check.get("status", "ERROR") for check in report["checks"].values()]
        
        if "CRITICAL" in all_statuses or "ERROR" in all_statuses:
            report["overall_status"] = "CRITICAL"
        elif "WARNING" in all_statuses:
            report["overall_status"] = "WARNING"
        else:
            report["overall_status"] = "OK"
        
        print(f"\n{'='*60}")
        print(f"Overall Status: {report['overall_status']}")
        print(f"{'='*60}")
        
        # Send alert if needed
        if report["overall_status"] in ["CRITICAL", "WARNING"]:
            alert_msg = self._format_alert_message(report)
            if self.send_alert(alert_msg, severity=report["overall_status"].lower()):
                print("[!] Alert sent to webhook")
        
        return report
    
    def _format_alert_message(self, report: Dict) -> str:
        """Format alert message from report.
        
        Args:
            report: Health report dictionary
            
        Returns:
            Formatted alert message
        """
        lines = []
        
        if report["overall_status"] == "CRITICAL":
            lines.append("[CRITICAL] OAuth authentication is impacted!")
        else:
            lines.append("[WARNING] Potential OAuth issues detected")
        
        # Add specific issues
        blocks = report["checks"].get("recent_blocks", {})
        if blocks.get("blocks_count", 0) > 0:
            lines.append(f"[U+2022] {blocks['blocks_count']} OAuth callbacks blocked in last 5 min")
        
        success = report["checks"].get("success_rate", {})
        if success.get("success_rate", 100) < 95:
            lines.append(f"[U+2022] OAuth success rate: {success.get('success_rate')}%")
        
        rule = report["checks"].get("security_rule", {})
        if not rule.get("rule_exists"):
            lines.append("[U+2022] OAuth exception rule is missing!")
        
        return "\n".join(lines)
    
    def run_continuous(self, interval: int = 300):
        """Run continuous monitoring.
        
        Args:
            interval: Seconds between checks
        """
        print(f"Starting continuous monitoring (checking every {interval} seconds)")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                report = self.generate_health_report()
                
                # Save report
                report_file = f"oauth_health_{self.environment}_{datetime.now().strftime('%Y%m%d')}.jsonl"
                with open(report_file, "a") as f:
                    f.write(json.dumps(report) + "\n")
                
                # Sleep until next check
                print(f"\nNext check in {interval} seconds...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Monitor OAuth health and Cloud Armor blocks",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--environment",
        default="staging",
        choices=["staging", "production"],
        help="Environment to monitor"
    )
    
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run single check and exit"
    )
    
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuous monitoring"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Seconds between checks in continuous mode (default: 300)"
    )
    
    parser.add_argument(
        "--alert-webhook",
        help="Webhook URL for alerts (Slack, Discord, etc.)"
    )
    
    parser.add_argument(
        "--alert-threshold",
        type=int,
        default=5,
        help="Number of blocks before alerting (default: 5)"
    )
    
    args = parser.parse_args()
    
    # Create monitor
    monitor = OAuthHealthMonitor(
        environment=args.environment,
        alert_webhook=args.alert_webhook,
        alert_threshold=args.alert_threshold
    )
    
    # Run appropriate mode
    if args.continuous:
        monitor.run_continuous(interval=args.interval)
    else:
        # Run once
        report = monitor.generate_health_report()
        
        # Exit with error if health is not OK
        if report["overall_status"] != "OK":
            sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()