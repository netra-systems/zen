#!/usr/bin/env python3
"""
Cloud Armor Log Analyzer for Netra Staging

This script provides easy access to Cloud Armor security logs, particularly useful for:
- Investigating 403 errors and blocked requests
- Analyzing OWASP rule triggers
- Debugging OAuth callback issues
- Understanding security policy enforcement

Usage:
    python scripts/analyze_cloud_armor_logs.py --help
    python scripts/analyze_cloud_armor_logs.py --denied  # Show all denied requests
    python scripts/analyze_cloud_armor_logs.py --oauth   # Show OAuth-related blocks
    python scripts/analyze_cloud_armor_logs.py --url "/auth/callback"  # Filter by URL
"""

import argparse
import json
import subprocess
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import sys
import os


class CloudArmorLogAnalyzer:
    """Analyzer for Cloud Armor security logs."""
    
    def __init__(self, project: str = "netra-staging"):
        """Initialize the analyzer.
        
        Args:
            project: GCP project ID
        """
        self.project = project
        
    def fetch_logs(
        self, 
        filter_expr: str,
        limit: int = 20,
        hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """Fetch logs from Cloud Logging.
        
        Args:
            filter_expr: GCP logging filter expression
            limit: Maximum number of logs to return
            hours_back: How many hours back to search
            
        Returns:
            List of log entries
        """
        # Add time filter
        time_filter = f'timestamp>="{(datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat()}"'
        full_filter = f'{filter_expr} AND {time_filter}'
        
        # Build command - handle Windows shell=True requirement for gcloud
        cmd = [
            "gcloud", "logging", "read",
            full_filter,
            f"--limit={limit}",
            "--format=json",
            f"--project={self.project}"
        ]
        
        # Use shell=True on Windows for gcloud to work properly
        use_shell = os.name == 'nt'
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=use_shell)
            return json.loads(result.stdout) if result.stdout else []
        except subprocess.CalledProcessError as e:
            print(f"Error fetching logs: {e.stderr}", file=sys.stderr)
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing logs: {e}", file=sys.stderr)
            return []
    
    def get_denied_requests(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get all requests denied by Cloud Armor.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List of denied requests
        """
        filter_expr = (
            'resource.type="http_load_balancer" AND '
            'jsonPayload.statusDetails="denied_by_security_policy" AND '
            'httpRequest.status=403'
        )
        return self.fetch_logs(filter_expr, limit)
    
    def get_oauth_blocks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get OAuth-related blocked requests.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List of blocked OAuth requests
        """
        filter_expr = (
            'resource.type="http_load_balancer" AND '
            'jsonPayload.statusDetails="denied_by_security_policy" AND '
            '(httpRequest.requestUrl=~"callback" OR '
            'httpRequest.requestUrl=~"redirect" OR '
            'httpRequest.requestUrl=~"auth") AND '
            'httpRequest.status=403'
        )
        return self.fetch_logs(filter_expr, limit)
    
    def get_by_url_pattern(self, url_pattern: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get blocked requests matching a URL pattern.
        
        Args:
            url_pattern: URL pattern to match
            limit: Maximum number of logs to return
            
        Returns:
            List of blocked requests matching the pattern
        """
        filter_expr = (
            f'resource.type="http_load_balancer" AND '
            f'jsonPayload.statusDetails="denied_by_security_policy" AND '
            f'httpRequest.requestUrl=~"{url_pattern}" AND '
            f'httpRequest.status=403'
        )
        return self.fetch_logs(filter_expr, limit)
    
    def get_by_rule(self, rule_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get requests blocked by a specific OWASP rule.
        
        Args:
            rule_id: OWASP rule ID (e.g., "owasp-crs-v030001-id942432-sqli")
            limit: Maximum number of logs to return
            
        Returns:
            List of requests blocked by the specified rule
        """
        filter_expr = (
            f'resource.type="http_load_balancer" AND '
            f'jsonPayload.enforcedSecurityPolicy.preconfiguredExprIds="{rule_id}"'
        )
        return self.fetch_logs(filter_expr, limit)
    
    def format_log_entry(self, entry: Dict[str, Any]) -> str:
        """Format a log entry for display.
        
        Args:
            entry: Log entry
            
        Returns:
            Formatted string
        """
        output = []
        output.append("=" * 80)
        
        # Timestamp
        timestamp = entry.get("timestamp", "Unknown")
        output.append(f"Time: {timestamp}")
        
        # Request details
        http_request = entry.get("httpRequest", {})
        output.append(f"Method: {http_request.get('requestMethod', 'Unknown')}")
        output.append(f"URL: {http_request.get('requestUrl', 'Unknown')}")
        output.append(f"Status: {http_request.get('status', 'Unknown')}")
        output.append(f"User-Agent: {http_request.get('userAgent', 'Unknown')}")
        output.append(f"Remote IP: {http_request.get('remoteIp', 'Unknown')}")
        
        # Security policy details
        json_payload = entry.get("jsonPayload", {})
        security_policy = json_payload.get("enforcedSecurityPolicy", {})
        if security_policy:
            output.append(f"\nSecurity Policy: {security_policy.get('name', 'Unknown')}")
            output.append(f"Action: {security_policy.get('configuredAction', 'Unknown')}")
            output.append(f"Priority: {security_policy.get('priority', 'Unknown')}")
            
            # OWASP rules triggered
            rules = security_policy.get("preconfiguredExprIds", [])
            if rules:
                output.append("Triggered Rules:")
                for rule in rules:
                    output.append(f"  - {rule}")
        
        return "\n".join(output)
    
    def analyze_rule_frequency(self, logs: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze frequency of triggered OWASP rules.
        
        Args:
            logs: List of log entries
            
        Returns:
            Dictionary of rule IDs and their frequency
        """
        rule_counts = {}
        for entry in logs:
            json_payload = entry.get("jsonPayload", {})
            security_policy = json_payload.get("enforcedSecurityPolicy", {})
            rules = security_policy.get("preconfiguredExprIds", [])
            
            for rule in rules:
                rule_counts[rule] = rule_counts.get(rule, 0) + 1
        
        return rule_counts
    
    def print_summary(self, logs: List[Dict[str, Any]]) -> None:
        """Print a summary of the logs.
        
        Args:
            logs: List of log entries
        """
        if not logs:
            print("No matching logs found.")
            return
        
        print(f"\nFound {len(logs)} blocked requests\n")
        
        # Analyze rule frequency
        rule_counts = self.analyze_rule_frequency(logs)
        if rule_counts:
            print("Most Triggered Rules:")
            for rule, count in sorted(rule_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {count:3d} - {rule}")
            print()
        
        # URL patterns
        url_patterns = {}
        for entry in logs:
            url = entry.get("httpRequest", {}).get("requestUrl", "")
            # Extract path from URL
            if "://" in url:
                path = "/" + url.split("://", 1)[1].split("/", 1)[1] if "/" in url.split("://", 1)[1] else "/"
                path = path.split("?")[0]  # Remove query params
                url_patterns[path] = url_patterns.get(path, 0) + 1
        
        if url_patterns:
            print("Blocked URL Paths:")
            for path, count in sorted(url_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {count:3d} - {path}")
            print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze Cloud Armor security logs for Netra Staging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --denied                    # Show all denied requests
  %(prog)s --oauth                     # Show OAuth-related blocks
  %(prog)s --url "/auth/callback"      # Filter by URL pattern
  %(prog)s --rule "id942432"           # Filter by OWASP rule
  %(prog)s --summary --limit 100       # Show summary of last 100 blocks
        """
    )
    
    parser.add_argument(
        "--project",
        default="netra-staging",
        help="GCP project ID (default: netra-staging)"
    )
    
    parser.add_argument(
        "--denied",
        action="store_true",
        help="Show all denied requests"
    )
    
    parser.add_argument(
        "--oauth",
        action="store_true",
        help="Show OAuth-related blocked requests"
    )
    
    parser.add_argument(
        "--url",
        help="Filter by URL pattern"
    )
    
    parser.add_argument(
        "--rule",
        help="Filter by OWASP rule ID"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of logs to fetch (default: 20)"
    )
    
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="How many hours back to search (default: 24)"
    )
    
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary instead of individual logs"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed log entries"
    )
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = CloudArmorLogAnalyzer(project=args.project)
    
    # Fetch logs based on arguments
    logs = []
    
    if args.denied or (not args.oauth and not args.url and not args.rule):
        # Default to showing all denied requests
        logs = analyzer.get_denied_requests(limit=args.limit)
    elif args.oauth:
        logs = analyzer.get_oauth_blocks(limit=args.limit)
    elif args.url:
        logs = analyzer.get_by_url_pattern(args.url, limit=args.limit)
    elif args.rule:
        logs = analyzer.get_by_rule(args.rule, limit=args.limit)
    
    # Display results
    if args.summary:
        analyzer.print_summary(logs)
    else:
        for entry in logs:
            if args.verbose:
                print(json.dumps(entry, indent=2))
            else:
                print(analyzer.format_log_entry(entry))
        
        if logs:
            print(f"\nTotal: {len(logs)} blocked requests")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())