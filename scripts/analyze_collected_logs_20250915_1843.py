#!/usr/bin/env python3
"""
GCP Log Analysis for Issue Clustering
Analyzes collected logs and clusters them into actionable groups for GitHub issues
"""

import json
import re
import sys
import os
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

class LogAnalyzer:
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.logs = []
        self.clusters = {}

    def load_logs(self):
        """Load logs from JSON file"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                self.logs = json.load(f)
            print(f"✅ Loaded {len(self.logs)} log entries from {self.log_file}")
            return True
        except Exception as e:
            print(f"❌ Error loading logs: {e}")
            return False

    def extract_message(self, log: Dict[str, Any]) -> str:
        """Extract message from log entry"""
        if 'textPayload' in log:
            return log['textPayload']
        elif 'jsonPayload' in log:
            jp = log['jsonPayload']
            if isinstance(jp, dict):
                return jp.get('message', str(jp))
            else:
                return str(jp)
        return "No message"

    def categorize_error(self, message: str, log: Dict[str, Any]) -> str:
        """Categorize error based on message content"""
        message_lower = message.lower()

        # Critical infrastructure failures
        if "modulenotfounderror: no module named 'netra_backend.app.services.monitoring'" in message_lower:
            return "CRITICAL_MISSING_MONITORING_MODULE"

        # HTTP/Connection issues
        if "malformed response or connection to the instance had an error" in message_lower:
            return "CRITICAL_HTTP_CONNECTION_FAILURE"

        # Container exit issues
        if "container called exit" in message_lower:
            return "CRITICAL_CONTAINER_EXIT"

        # Middleware setup failures
        if "middleware setup" in message_lower and "failed" in message_lower:
            return "CRITICAL_MIDDLEWARE_SETUP_FAILURE"

        # Database connectivity issues
        if any(db_term in message_lower for db_term in ["database", "postgres", "connection refused", "timeout"]):
            return "HIGH_DATABASE_CONNECTIVITY"

        # WebSocket issues
        if any(ws_term in message_lower for ws_term in ["websocket", "ws://", "wss://", "connection upgrade"]):
            return "HIGH_WEBSOCKET_CONNECTIVITY"

        # Auth/JWT issues
        if any(auth_term in message_lower for auth_term in ["jwt", "token", "authentication", "unauthorized"]):
            return "MEDIUM_AUTHENTICATION_ISSUES"

        # Sentry SDK issues
        if "sentry" in message_lower:
            return "LOW_SENTRY_CONFIGURATION"

        # Service ID issues
        if "service_id" in message_lower and "whitespace" in message_lower:
            return "LOW_SERVICE_ID_WHITESPACE"

        # Configuration issues
        if any(config_term in message_lower for config_term in ["config", "environment", "missing"]):
            return "MEDIUM_CONFIGURATION_ISSUES"

        # Generic errors
        return "MEDIUM_GENERIC_ERRORS"

    def cluster_logs(self):
        """Cluster logs by error patterns"""
        print("\n📊 Clustering logs by error patterns...")

        clusters = defaultdict(list)
        severity_filter = ['ERROR', 'CRITICAL', 'WARNING']

        for log in self.logs:
            severity = log.get('severity', 'UNKNOWN')
            if severity in severity_filter:
                message = self.extract_message(log)
                category = self.categorize_error(message, log)
                clusters[category].append({
                    'log': log,
                    'message': message,
                    'timestamp': log.get('timestamp', ''),
                    'severity': severity
                })

        # Sort clusters by priority and count
        priority_order = [
            'CRITICAL_MISSING_MONITORING_MODULE',
            'CRITICAL_HTTP_CONNECTION_FAILURE',
            'CRITICAL_CONTAINER_EXIT',
            'CRITICAL_MIDDLEWARE_SETUP_FAILURE',
            'HIGH_DATABASE_CONNECTIVITY',
            'HIGH_WEBSOCKET_CONNECTIVITY',
            'MEDIUM_AUTHENTICATION_ISSUES',
            'MEDIUM_CONFIGURATION_ISSUES',
            'MEDIUM_GENERIC_ERRORS',
            'LOW_SENTRY_CONFIGURATION',
            'LOW_SERVICE_ID_WHITESPACE'
        ]

        self.clusters = {}
        for category in priority_order:
            if category in clusters:
                self.clusters[category] = clusters[category]

        # Add any remaining categories
        for category, logs in clusters.items():
            if category not in self.clusters:
                self.clusters[category] = logs

        return self.clusters

    def get_priority_level(self, category: str) -> str:
        """Get priority level for category"""
        if category.startswith('CRITICAL_'):
            return 'P0'
        elif category.startswith('HIGH_'):
            return 'P1'
        elif category.startswith('MEDIUM_'):
            return 'P2'
        elif category.startswith('LOW_'):
            return 'P3'
        else:
            return 'P2'

    def get_category_description(self, category: str) -> str:
        """Get human-readable description for category"""
        descriptions = {
            'CRITICAL_MISSING_MONITORING_MODULE': 'Missing Monitoring Module Exports',
            'CRITICAL_HTTP_CONNECTION_FAILURE': 'HTTP Connection/Response Failures',
            'CRITICAL_CONTAINER_EXIT': 'Container Exit Failures',
            'CRITICAL_MIDDLEWARE_SETUP_FAILURE': 'Middleware Setup Failures',
            'HIGH_DATABASE_CONNECTIVITY': 'Database Connectivity Issues',
            'HIGH_WEBSOCKET_CONNECTIVITY': 'WebSocket Connectivity Issues',
            'MEDIUM_AUTHENTICATION_ISSUES': 'Authentication/JWT Issues',
            'MEDIUM_CONFIGURATION_ISSUES': 'Configuration Issues',
            'MEDIUM_GENERIC_ERRORS': 'Generic Application Errors',
            'LOW_SENTRY_CONFIGURATION': 'Sentry SDK Configuration',
            'LOW_SERVICE_ID_WHITESPACE': 'Service ID Whitespace Issues'
        }
        return descriptions.get(category, category.replace('_', ' ').title())

    def generate_analysis_report(self) -> str:
        """Generate detailed analysis report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        report = f"""# GCP Log Analysis Report
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Log File:** {self.log_file}
**Total Logs:** {len(self.logs)}
**Error/Warning Logs:** {sum(len(logs) for logs in self.clusters.values())}

## Cluster Summary

"""

        for i, (category, logs) in enumerate(self.clusters.items(), 1):
            priority = self.get_priority_level(category)
            description = self.get_category_description(category)

            report += f"""### Cluster {i}: {priority} {priority.upper()} - {description} ({len(logs)} incidents)
**Category:** `{category}`
**Priority:** {priority}
**Incident Count:** {len(logs)}

**Sample Error:**
```json
{{
  "timestamp": "{logs[0]['timestamp']}",
  "severity": "{logs[0]['severity']}",
  "message": "{logs[0]['message'][:200]}..."
}}
```

**Full Sample Log:**
```json
{json.dumps(logs[0]['log'], indent=2)[:1000]}...
```

---

"""

        # Add recommendations
        report += """## Recommended Actions

"""

        for category, logs in self.clusters.items():
            priority = self.get_priority_level(category)
            description = self.get_category_description(category)

            if priority in ['P0', 'P1']:
                report += f"### {priority} URGENT: {description}\n"
                report += f"- **Action Required:** Immediate investigation and fix\n"
                report += f"- **Business Impact:** Service availability at risk\n"
                report += f"- **Incidents:** {len(logs)} in last hour\n\n"

        return report

    def save_analysis_report(self, report: str) -> str:
        """Save analysis report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"GCP_LOG_ANALYSIS_REPORT_{timestamp}.md"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"📄 Analysis report saved to: {filename}")
        return filename

    def print_summary(self):
        """Print summary of clusters"""
        print("\n" + "="*60)
        print("LOG CLUSTER ANALYSIS SUMMARY")
        print("="*60)

        total_issues = sum(len(logs) for logs in self.clusters.values())
        print(f"Total Error/Warning Logs: {total_issues}")
        print(f"Clusters Identified: {len(self.clusters)}")

        print("\n🚨 CLUSTERS BY PRIORITY:")

        for category, logs in self.clusters.items():
            priority = self.get_priority_level(category)
            description = self.get_category_description(category)

            print(f"\n{priority} {description} ({len(logs)} incidents)")
            print(f"   Category: {category}")

            # Show sample message
            if logs:
                sample_msg = logs[0]['message'][:100] + "..." if len(logs[0]['message']) > 100 else logs[0]['message']
                print(f"   Sample: {sample_msg}")

        print("\n" + "="*60)

def main():
    """Main analysis function"""
    log_file = "gcp_logs_last_hour_20250915_184401.json"

    analyzer = LogAnalyzer(log_file)

    if not analyzer.load_logs():
        return

    clusters = analyzer.cluster_logs()
    analyzer.print_summary()

    # Generate and save report
    report = analyzer.generate_analysis_report()
    report_file = analyzer.save_analysis_report(report)

    print(f"\n✅ Analysis complete!")
    print(f"📊 Found {len(clusters)} distinct issue clusters")
    print(f"📄 Detailed report: {report_file}")

    return clusters, report_file

if __name__ == "__main__":
    main()