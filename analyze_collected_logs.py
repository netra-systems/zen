#!/usr/bin/env python3
"""
GCP Log Analysis Script for Clustered Issue Tracking
Analyzes the collected logs and provides structured issue clustering
"""

import json
import re
from collections import defaultdict, Counter
from datetime import datetime

class LogAnalyzer:
    def __init__(self, log_file):
        self.log_file = log_file
        self.logs = []
        self.error_logs = []
        self.clusters = {}

    def load_logs(self):
        """Load logs from JSON file"""
        with open(self.log_file, 'r', encoding='utf-8') as f:
            self.logs = json.load(f)

        # Filter error/warning logs
        self.error_logs = [
            log for log in self.logs
            if log.get('severity') in ['ERROR', 'WARNING', 'CRITICAL']
        ]

        print(f"Loaded {len(self.logs)} total logs, {len(self.error_logs)} error/warning logs")

    def extract_error_message(self, log):
        """Extract meaningful error message from log entry"""
        # Try jsonPayload.message first
        if 'jsonPayload' in log:
            jp = log['jsonPayload']
            if 'message' in jp:
                return jp['message']
            elif 'error' in jp:
                error = jp['error']
                if isinstance(error, dict):
                    return error.get('message', str(error))
                else:
                    return str(error)

        # Fall back to textPayload
        if 'textPayload' in log:
            return log['textPayload']

        return str(log)

    def cluster_errors(self):
        """Cluster errors by pattern"""
        error_patterns = defaultdict(list)

        for log in self.error_logs:
            message = self.extract_error_message(log)

            # Define clustering patterns
            cluster_key = self.classify_error(message)
            error_patterns[cluster_key].append({
                'log': log,
                'message': message,
                'timestamp': log.get('timestamp', ''),
                'severity': log.get('severity', 'UNKNOWN')
            })

        # Sort clusters by frequency
        self.clusters = dict(sorted(
            error_patterns.items(),
            key=lambda x: len(x[1]),
            reverse=True
        ))

        return self.clusters

    def classify_error(self, message):
        """Classify error message into cluster"""
        message_lower = message.lower()

        # Module import errors
        if 'modulenotfounderror' in message_lower or 'no module named' in message_lower:
            if 'monitoring' in message_lower:
                return "Missing Monitoring Module"
            elif 'uvicorn_protocol' in message_lower:
                return "Missing UVicorn Protocol Module"
            elif 'middleware' in message_lower:
                return "Missing Middleware Module"
            else:
                return "Module Import Errors"

        # Container/deployment issues
        if 'container called exit' in message_lower:
            return "Container Exit Issues"

        # Middleware setup issues
        if 'middleware setup' in message_lower:
            return "Middleware Setup Failures"

        # Sentry issues
        if 'sentry' in message_lower:
            return "Sentry SDK Issues"

        # Service ID issues
        if 'service_id' in message_lower and 'whitespace' in message_lower:
            return "Service ID Configuration Issues"

        # Database issues
        if any(db in message_lower for db in ['database', 'postgresql', 'connection pool', 'sql']):
            return "Database Connectivity Issues"

        # WebSocket issues
        if any(ws in message_lower for ws in ['websocket', 'ws', '1011']):
            return "WebSocket Connection Issues"

        # Authentication issues
        if any(auth in message_lower for auth in ['auth', 'jwt', 'token', 'session']):
            return "Authentication Issues"

        # Configuration issues
        if any(config in message_lower for config in ['config', 'environment', 'cors']):
            return "Configuration Issues"

        # Startup/initialization issues
        if any(startup in message_lower for startup in ['startup', 'initialization', 'init_process']):
            return "Startup/Initialization Issues"

        # Gunicorn/worker issues
        if any(worker in message_lower for worker in ['gunicorn', 'worker', 'spawn_worker']):
            return "Worker Process Issues"

        # Default classification
        return "Other Errors"

    def generate_report(self):
        """Generate comprehensive analysis report"""
        report = []
        report.append("# GCP Log Analysis Report - Last 1 Hour")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} PDT")
        report.append(f"**Time Range:** 4:43 PM PDT to 5:43 PM PDT (Sept 15, 2025)")
        report.append(f"**Service:** netra-backend-staging")
        report.append(f"**Total Logs:** {len(self.logs)}")
        report.append(f"**Error/Warning Logs:** {len(self.error_logs)}")
        report.append("")

        # Executive Summary
        report.append("## Executive Summary")
        report.append("")

        # Severity breakdown
        severity_counts = Counter(log.get('severity', 'UNKNOWN') for log in self.error_logs)
        report.append("### Severity Breakdown:")
        for severity, count in severity_counts.most_common():
            report.append(f"- **{severity}:** {count} incidents")
        report.append("")

        # Cluster analysis
        report.append("## Clustered Issue Analysis")
        report.append("")

        priority_map = {
            "Missing Monitoring Module": "P0 CRITICAL",
            "Container Exit Issues": "P0 CRITICAL",
            "Worker Process Issues": "P0 CRITICAL",
            "Startup/Initialization Issues": "P1 HIGH",
            "Middleware Setup Failures": "P1 HIGH",
            "Missing UVicorn Protocol Module": "P1 HIGH",
            "Missing Middleware Module": "P1 HIGH",
            "Module Import Errors": "P1 HIGH",
            "Database Connectivity Issues": "P0 CRITICAL",
            "WebSocket Connection Issues": "P1 HIGH",
            "Authentication Issues": "P1 HIGH",
            "Service ID Configuration Issues": "P2 MEDIUM",
            "Sentry SDK Issues": "P3 LOW",
            "Configuration Issues": "P2 MEDIUM",
            "Other Errors": "P2 MEDIUM"
        }

        for i, (cluster_name, cluster_logs) in enumerate(self.clusters.items(), 1):
            priority = priority_map.get(cluster_name, "P2 MEDIUM")
            severity_icon = "🚨" if "P0" in priority else "🟠" if "P1" in priority else "🟡" if "P2" in priority else "🟢"

            report.append(f"### {severity_icon} CLUSTER {i}: {cluster_name} ({priority})")
            report.append(f"**Issue Count:** {len(cluster_logs)} incidents")
            report.append(f"**Severity:** {priority}")
            report.append("")

            # Show sample messages
            report.append("#### Key Log Patterns:")
            report.append("```")
            for j, error in enumerate(cluster_logs[:3]):  # Show first 3
                report.append(f"{error['severity']} [{error['timestamp']}] - {error['message'][:200]}")
            if len(cluster_logs) > 3:
                report.append(f"... and {len(cluster_logs) - 3} more similar incidents")
            report.append("```")
            report.append("")

            # Business impact assessment
            if cluster_name == "Missing Monitoring Module":
                report.append("#### Business Impact:")
                report.append("- Service startup failures preventing chat functionality")
                report.append("- Revenue impact: Complete service unavailability")
                report.append("- User experience: Chat interface inaccessible")
                report.append("")

            elif cluster_name == "Container Exit Issues":
                report.append("#### Business Impact:")
                report.append("- Service containers crashing, causing intermittent outages")
                report.append("- Load balancer routing issues")
                report.append("- User experience degradation during container restarts")
                report.append("")

            # Show full JSON for first error in cluster
            if cluster_logs:
                first_error = cluster_logs[0]['log']
                report.append("#### Sample Full JSON Log:")
                report.append("```json")
                report.append(json.dumps(first_error, indent=2)[:2000])
                if len(json.dumps(first_error, indent=2)) > 2000:
                    report.append("... (truncated)")
                report.append("```")
            report.append("")
            report.append("---")
            report.append("")

        # Timeline analysis
        report.append("## Timeline Analysis")
        report.append("")

        # Extract timestamps and create timeline
        timeline_events = []
        for log in self.error_logs:
            timestamp = log.get('timestamp', '')
            if timestamp:
                message = self.extract_error_message(log)
                cluster = self.classify_error(message)
                timeline_events.append({
                    'time': timestamp,
                    'cluster': cluster,
                    'severity': log.get('severity', 'UNKNOWN'),
                    'message': message[:100]
                })

        # Sort by timestamp
        timeline_events.sort(key=lambda x: x['time'])

        report.append("### Error Timeline (Last 1 Hour):")
        report.append("```")
        for event in timeline_events[:20]:  # Show first 20 events
            time_str = event['time'][-12:-4] if len(event['time']) > 12 else event['time']  # Extract HH:MM:SS
            report.append(f"{time_str} - {event['severity']} - {event['cluster'][:30]}")
        if len(timeline_events) > 20:
            report.append(f"... and {len(timeline_events) - 20} more events")
        report.append("```")
        report.append("")

        # Recommendations
        report.append("## Immediate Action Items")
        report.append("")
        report.append("### P0 CRITICAL (Fix Immediately):")
        p0_clusters = [name for name, _ in self.clusters.items() if priority_map.get(name, "").startswith("P0")]
        for cluster in p0_clusters:
            if cluster in self.clusters:
                count = len(self.clusters[cluster])
                report.append(f"- **{cluster}** ({count} incidents) - Service startup failures")
        report.append("")

        report.append("### P1 HIGH (Fix Today):")
        p1_clusters = [name for name, _ in self.clusters.items() if priority_map.get(name, "").startswith("P1")]
        for cluster in p1_clusters:
            if cluster in self.clusters:
                count = len(self.clusters[cluster])
                report.append(f"- **{cluster}** ({count} incidents)")
        report.append("")

        # Raw data location
        report.append("## Raw Data Access")
        report.append("")
        report.append(f"**Full log file:** `{self.log_file}`")
        report.append(f"**Total entries:** {len(self.logs)}")
        report.append(f"**Error entries:** {len(self.error_logs)}")
        report.append("")
        report.append("### GCloud Command Used:")
        report.append("```bash")
        report.append("gcloud logging read \"resource.type=cloud_run_revision AND")
        report.append("  resource.labels.service_name=netra-backend-staging AND")
        report.append("  timestamp>=\\\"2025-09-15T23:43:00.000Z\\\" AND")
        report.append("  timestamp<=\\\"2025-09-16T00:43:00.000Z\\\"\"")
        report.append("  --limit=1000 --format=json --project=netra-staging")
        report.append("```")

        return "\n".join(report)

def main():
    analyzer = LogAnalyzer('gcp_logs_last_hour_20250915_175001.json')
    analyzer.load_logs()
    analyzer.cluster_errors()

    report = analyzer.generate_report()

    # Save report
    report_file = f"GCP_LOG_ANALYSIS_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"Analysis complete! Report saved to: {report_file}")
    print(f"Found {len(analyzer.clusters)} distinct error clusters")
    print("\n" + "="*60)
    print("TOP 5 ISSUE CLUSTERS:")
    print("="*60)

    for i, (cluster_name, cluster_logs) in enumerate(list(analyzer.clusters.items())[:5], 1):
        print(f"{i}. {cluster_name}: {len(cluster_logs)} incidents")

    return report_file

if __name__ == "__main__":
    main()