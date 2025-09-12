from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
GCP OAuth Log Audit Script
Analyzes OAuth flow issues in GCP Cloud Logging

This script:
1. Fetches OAuth-related logs from GCP
2. Analyzes token generation, validation, and errors
3. Tracks OAuth flow from initiation to completion
4. Identifies common OAuth issues and failures
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path

# Fix Windows Unicode issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import centralized GCP authentication
from gcp_auth_config import GCPAuthConfig

import click
from google.cloud import logging as cloud_logging
from google.cloud.logging_v2 import DESCENDING
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

console = Console(force_terminal=True if sys.platform == 'win32' else None)


class OAuthLogAnalyzer:
    """Analyzes OAuth logs from GCP Cloud Logging"""
    
    def __init__(self, project_id: str, hours_back: int = 24):
        self.project_id = project_id
        self.hours_back = hours_back
        
        # Ensure proper authentication
        if not GCPAuthConfig.ensure_authentication():
            console.print("[red]Failed to set up GCP authentication[/red]")
            console.print("[yellow]Please ensure service account key is at: config/netra-staging-7a1059b7cf26.json[/yellow]")
            raise RuntimeError("GCP authentication failed")
        
        self.client = cloud_logging.Client(project=project_id)
        
        # OAuth patterns to search for
        self.oauth_patterns = {
            'login_initiated': r'OAuth login initiated',
            'callback_received': r'OAuth callback|callback\?code=',
            'token_exchange': r'exchanging.*code.*token|token exchange',
            'token_created': r'Token created|access_token.*created|JWT token generated',
            'token_validated': r'Token validated|token.*valid|JWT validated',
            'token_missing': r'No token|missing token|token not found',
            'auth_failed': r'Authentication failed|auth.*failed|OAuth.*failed',
            'google_api_call': r'google.*oauth|accounts\.google\.com',
            'redirect_uri': r'redirect_uri|callback URL',
            'client_id': r'client_id|GOOGLE_CLIENT_ID',
            'error_response': r'error=|error_description=',
        }
        
        # Critical OAuth endpoints
        self.oauth_endpoints = [
            '/auth/login',
            '/auth/callback',
            '/auth/token',
            '/auth/validate',
            '/auth/login',
            '/auth/callback',
            '/auth/config'
        ]
        
        # Track OAuth sessions
        self.oauth_sessions: Dict[str, List[dict]] = defaultdict(list)
        self.error_sessions: Set[str] = set()
        
    def fetch_oauth_logs(self) -> List[dict]:
        """Fetch OAuth-related logs from GCP"""
        console.print("\n[bold yellow]Fetching OAuth logs from GCP...[/bold yellow]")
        
        # Build time filter
        hours_ago = datetime.now(timezone.utc) - timedelta(hours=self.hours_back)
        time_filter = f'timestamp >= "{hours_ago.isoformat()}"'
        
        # Build OAuth-specific filter
        oauth_filters = []
        
        # Add pattern searches
        for pattern in self.oauth_patterns.values():
            oauth_filters.append(f'textPayload=~"{pattern}"')
            oauth_filters.append(f'jsonPayload.message=~"{pattern}"')
        
        # Add endpoint searches
        for endpoint in self.oauth_endpoints:
            oauth_filters.append(f'httpRequest.requestUrl=~"{endpoint}"')
            oauth_filters.append(f'jsonPayload.path=~"{endpoint}"')
        
        # Add OAuth-specific keywords
        oauth_keywords = ['oauth', 'OAuth', 'google_login', 'access_token', 'id_token', 'authorization_code']
        for keyword in oauth_keywords:
            oauth_filters.append(f'textPayload:"{keyword}"')
            oauth_filters.append(f'jsonPayload.message:"{keyword}"')
        
        # Combine filters
        oauth_filter = ' OR '.join(oauth_filters)
        full_filter = f'{time_filter} AND ({oauth_filter})'
        
        # Fetch logs
        entries = []
        try:
            for entry in self.client.list_entries(
                filter_=full_filter,
                order_by=DESCENDING,
                page_size=1000
            ):
                entries.append(self._parse_log_entry(entry))
                
            console.print(f"[green][U+2713] Fetched {len(entries)} OAuth-related log entries[/green]")
        except Exception as e:
            console.print(f"[red][U+2717] Error fetching logs: {e}[/red]")
            
        return entries
    
    def _parse_log_entry(self, entry) -> dict:
        """Parse a log entry into a structured format"""
        # Handle different payload types
        text_payload = None
        json_payload = {}
        
        if hasattr(entry, 'payload'):
            if isinstance(entry.payload, str):
                text_payload = entry.payload
            elif isinstance(entry.payload, dict):
                json_payload = entry.payload
        elif hasattr(entry, 'text_payload'):
            text_payload = entry.text_payload
        elif hasattr(entry, 'json_payload'):
            json_payload = dict(entry.json_payload) if entry.json_payload else {}
        
        parsed = {
            'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
            'severity': entry.severity,
            'resource': {
                'type': entry.resource.type,
                'labels': dict(entry.resource.labels) if entry.resource.labels else {}
            },
            'labels': dict(entry.labels) if entry.labels else {},
            'text_payload': text_payload,
            'json_payload': json_payload,
            'http_request': None,
            'trace': entry.trace if hasattr(entry, 'trace') else None,
            'span_id': entry.span_id if hasattr(entry, 'span_id') else None
        }
        
        # Parse HTTP request if present
        if entry.http_request:
            parsed['http_request'] = {
                'method': entry.http_request.get('requestMethod'),
                'url': entry.http_request.get('requestUrl'),
                'status': entry.http_request.get('status'),
                'user_agent': entry.http_request.get('userAgent'),
                'latency': entry.http_request.get('latency')
            }
        
        return parsed
    
    def analyze_oauth_flow(self, logs: List[dict]) -> Dict:
        """Analyze OAuth flow patterns and issues"""
        analysis = {
            'total_logs': len(logs),
            'oauth_sessions': 0,
            'successful_logins': 0,
            'failed_logins': 0,
            'token_issues': [],
            'common_errors': defaultdict(int),
            'flow_breakpoints': [],
            'missing_tokens': 0,
            'configuration_issues': []
        }
        
        # Group logs by trace/session
        for log in logs:
            trace_id = log.get('trace') or self._extract_session_id(log)
            if trace_id:
                self.oauth_sessions[trace_id].append(log)
        
        # Analyze each session
        for session_id, session_logs in self.oauth_sessions.items():
            session_analysis = self._analyze_session(session_logs)
            
            if session_analysis['completed']:
                analysis['successful_logins'] += 1
            elif session_analysis['errors']:
                analysis['failed_logins'] += 1
                self.error_sessions.add(session_id)
                
                # Track error types
                for error in session_analysis['errors']:
                    analysis['common_errors'][error['type']] += 1
                    
            # Check for token issues
            if session_analysis['token_missing']:
                analysis['missing_tokens'] += 1
                analysis['token_issues'].append({
                    'session': session_id,
                    'issue': 'Token not generated or found',
                    'stage': session_analysis['last_stage']
                })
            
            # Track flow breakpoints
            if session_analysis['flow_broken']:
                analysis['flow_breakpoints'].append({
                    'session': session_id,
                    'broke_at': session_analysis['last_stage'],
                    'reason': session_analysis.get('break_reason')
                })
        
        analysis['oauth_sessions'] = len(self.oauth_sessions)
        
        # Check for configuration issues
        analysis['configuration_issues'] = self._check_configuration_issues(logs)
        
        return analysis
    
    def _extract_session_id(self, log: dict) -> Optional[str]:
        """Extract session/trace ID from log"""
        # Try various sources for session ID
        if log.get('trace'):
            return log['trace']
        
        # Check JSON payload
        json_payload = log.get('json_payload', {})
        for field in ['session_id', 'trace_id', 'request_id', 'correlation_id']:
            if field in json_payload:
                return json_payload[field]
        
        # Check labels
        labels = log.get('labels', {})
        for field in ['session_id', 'trace_id', 'request_id']:
            if field in labels:
                return labels[field]
        
        # Try to extract from message
        message = json_payload.get('message', '') or log.get('text_payload', '')
        if message:
            # Look for session patterns
            session_match = re.search(r'session[_-]?id[:\s]+([a-zA-Z0-9-]+)', message, re.I)
            if session_match:
                return session_match.group(1)
        
        return None
    
    def _analyze_session(self, session_logs: List[dict]) -> Dict:
        """Analyze a single OAuth session"""
        analysis = {
            'completed': False,
            'errors': [],
            'token_missing': False,
            'flow_broken': False,
            'last_stage': None,
            'stages_completed': []
        }
        
        # Sort logs by timestamp
        session_logs.sort(key=lambda x: x.get('timestamp', ''))
        
        # Track OAuth flow stages
        stages = {
            'login_initiated': False,
            'google_redirect': False,
            'callback_received': False,
            'code_exchanged': False,
            'token_created': False,
            'token_validated': False
        }
        
        for log in session_logs:
            message = self._get_log_message(log)
            
            # Check each stage
            if re.search(self.oauth_patterns['login_initiated'], message, re.I):
                stages['login_initiated'] = True
                analysis['last_stage'] = 'login_initiated'
                
            if re.search(r'redirect.*google|accounts\.google\.com', message, re.I):
                stages['google_redirect'] = True
                analysis['last_stage'] = 'google_redirect'
                
            if re.search(self.oauth_patterns['callback_received'], message, re.I):
                stages['callback_received'] = True
                analysis['last_stage'] = 'callback_received'
                
            if re.search(self.oauth_patterns['token_exchange'], message, re.I):
                stages['code_exchanged'] = True
                analysis['last_stage'] = 'code_exchanged'
                
            if re.search(self.oauth_patterns['token_created'], message, re.I):
                stages['token_created'] = True
                analysis['last_stage'] = 'token_created'
                
            if re.search(self.oauth_patterns['token_validated'], message, re.I):
                stages['token_validated'] = True
                analysis['last_stage'] = 'token_validated'
            
            # Check for errors
            if re.search(self.oauth_patterns['auth_failed'], message, re.I):
                analysis['errors'].append({
                    'type': 'auth_failed',
                    'message': message[:200]
                })
            
            if re.search(self.oauth_patterns['token_missing'], message, re.I):
                analysis['token_missing'] = True
                analysis['errors'].append({
                    'type': 'token_missing',
                    'message': message[:200]
                })
            
            if re.search(self.oauth_patterns['error_response'], message, re.I):
                error_match = re.search(r'error=([^&\s]+)', message)
                if error_match:
                    analysis['errors'].append({
                        'type': f'oauth_error_{error_match.group(1)}',
                        'message': message[:200]
                    })
        
        # Check if flow completed
        analysis['completed'] = stages['token_created'] or stages['token_validated']
        
        # Check if flow was broken
        if stages['login_initiated'] and not stages['callback_received']:
            analysis['flow_broken'] = True
            analysis['break_reason'] = 'No callback received after login initiation'
        elif stages['callback_received'] and not stages['token_created']:
            analysis['flow_broken'] = True
            analysis['break_reason'] = 'Token not created after callback'
        
        analysis['stages_completed'] = [k for k, v in stages.items() if v]
        
        return analysis
    
    def _get_log_message(self, log: dict) -> str:
        """Extract message from log entry"""
        # Try JSON payload first
        json_payload = log.get('json_payload', {})
        if 'message' in json_payload:
            return str(json_payload['message'])
        
        # Try text payload
        if log.get('text_payload'):
            return str(log['text_payload'])
        
        # Try to construct from JSON payload
        if json_payload:
            return json.dumps(json_payload)
        
        return ''
    
    def _check_configuration_issues(self, logs: List[dict]) -> List[Dict]:
        """Check for OAuth configuration issues"""
        issues = []
        
        # Check for missing client ID/secret
        for log in logs:
            message = self._get_log_message(log).lower()
            
            if 'client_id' in message and ('not set' in message or 'missing' in message or 'not configured' in message):
                issues.append({
                    'type': 'missing_client_id',
                    'severity': 'critical',
                    'message': 'Google Client ID not configured'
                })
            
            if 'client_secret' in message and ('not set' in message or 'missing' in message or 'not configured' in message):
                issues.append({
                    'type': 'missing_client_secret',
                    'severity': 'critical',
                    'message': 'Google Client Secret not configured'
                })
            
            if 'redirect_uri' in message and 'mismatch' in message:
                issues.append({
                    'type': 'redirect_uri_mismatch',
                    'severity': 'high',
                    'message': 'Redirect URI mismatch - check Google Console configuration'
                })
        
        # Deduplicate issues
        seen = set()
        unique_issues = []
        for issue in issues:
            key = (issue['type'], issue['message'])
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)
        
        return unique_issues
    
    def generate_report(self, analysis: Dict) -> None:
        """Generate detailed OAuth audit report"""
        console.print("\n[bold cyan][U+2550][U+2550][U+2550] OAuth Flow Audit Report [U+2550][U+2550][U+2550][/bold cyan]\n")
        
        # Summary Panel
        summary = Panel(
            f"[bold]Total OAuth Logs:[/bold] {analysis['total_logs']}\n"
            f"[bold]OAuth Sessions:[/bold] {analysis['oauth_sessions']}\n"
            f"[bold green]Successful Logins:[/bold green] {analysis['successful_logins']}\n"
            f"[bold red]Failed Logins:[/bold red] {analysis['failed_logins']}\n"
            f"[bold yellow]Missing Tokens:[/bold yellow] {analysis['missing_tokens']}",
            title="[bold]Summary[/bold]",
            border_style="cyan"
        )
        console.print(summary)
        
        # Configuration Issues
        if analysis['configuration_issues']:
            console.print("\n[bold red] WARNING:  Configuration Issues Detected:[/bold red]")
            for issue in analysis['configuration_issues']:
                severity_color = 'red' if issue['severity'] == 'critical' else 'yellow'
                console.print(f"  [{severity_color}][U+2022] {issue['message']}[/{severity_color}]")
        
        # Common Errors
        if analysis['common_errors']:
            console.print("\n[bold]Common Errors:[/bold]")
            error_table = Table(show_header=True, header_style="bold magenta")
            error_table.add_column("Error Type", style="cyan")
            error_table.add_column("Count", justify="right")
            
            for error_type, count in sorted(analysis['common_errors'].items(), key=lambda x: x[1], reverse=True):
                error_table.add_row(error_type.replace('_', ' ').title(), str(count))
            
            console.print(error_table)
        
        # Flow Breakpoints
        if analysis['flow_breakpoints']:
            console.print("\n[bold yellow]Flow Breakpoints:[/bold yellow]")
            for breakpoint in analysis['flow_breakpoints'][:5]:  # Show top 5
                console.print(f"  [U+2022] Session broke at: [yellow]{breakpoint['broke_at']}[/yellow]")
                if breakpoint.get('reason'):
                    console.print(f"    Reason: {breakpoint['reason']}")
        
        # Token Issues
        if analysis['token_issues']:
            console.print("\n[bold red]Token Generation Issues:[/bold red]")
            for issue in analysis['token_issues'][:5]:  # Show top 5
                console.print(f"  [U+2022] {issue['issue']} at stage: [yellow]{issue['stage']}[/yellow]")
        
        # Recommendations
        self._print_recommendations(analysis)
    
    def _print_recommendations(self, analysis: Dict) -> None:
        """Print recommendations based on analysis"""
        console.print("\n[bold green][U+1F4CB] Recommendations:[/bold green]")
        
        recommendations = []
        
        # Check for configuration issues
        for issue in analysis['configuration_issues']:
            if issue['type'] == 'missing_client_id':
                recommendations.append("1. Set GOOGLE_CLIENT_ID environment variable in GCP")
            elif issue['type'] == 'missing_client_secret':
                recommendations.append("2. Set GOOGLE_CLIENT_SECRET environment variable in GCP")
            elif issue['type'] == 'redirect_uri_mismatch':
                recommendations.append("3. Update redirect URIs in Google Cloud Console to match deployment URLs")
        
        # Check for token issues
        if analysis['missing_tokens'] > 0:
            recommendations.append("4. Review token generation logic in auth service")
            recommendations.append("5. Check JWT_SECRET_KEY is properly set in all services")
        
        # Check for flow breakpoints
        if analysis['flow_breakpoints']:
            most_common_break = max(set([b['broke_at'] for b in analysis['flow_breakpoints']]), 
                                   key=[b['broke_at'] for b in analysis['flow_breakpoints']].count)
            recommendations.append(f"6. Investigate why flow commonly breaks at: {most_common_break}")
        
        # Check success rate
        total_sessions = analysis['successful_logins'] + analysis['failed_logins']
        if total_sessions > 0:
            success_rate = (analysis['successful_logins'] / total_sessions) * 100
            if success_rate < 50:
                recommendations.append("7. Critical: Less than 50% success rate - review entire OAuth implementation")
        
        if recommendations:
            for rec in recommendations:
                console.print(f"  [green][U+2713][/green] {rec}")
        else:
            console.print("  [green][U+2713][/green] No critical issues detected")
    
    def export_session_details(self, output_file: str) -> None:
        """Export detailed session information for debugging"""
        console.print(f"\n[yellow]Exporting session details to {output_file}...[/yellow]")
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'project_id': self.project_id,
            'error_sessions': list(self.error_sessions),
            'session_details': {}
        }
        
        # Export error sessions with full details
        for session_id in self.error_sessions:
            if session_id in self.oauth_sessions:
                session_logs = self.oauth_sessions[session_id]
                export_data['session_details'][session_id] = {
                    'log_count': len(session_logs),
                    'logs': [
                        {
                            'timestamp': log.get('timestamp'),
                            'message': self._get_log_message(log)[:500],
                            'severity': log.get('severity'),
                            'http_request': log.get('http_request')
                        }
                        for log in sorted(session_logs, key=lambda x: x.get('timestamp', ''))
                    ]
                }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        console.print(f"[green][U+2713] Session details exported to {output_file}[/green]")


@click.command()
@click.option('--project', '-p', default='netra-staging', help='GCP project ID')
@click.option('--hours', '-h', default=24, help='Hours to look back')
@click.option('--export', '-e', help='Export session details to file')
def main(project: str, hours: int, export: Optional[str]):
    """Audit OAuth logs in GCP for debugging token issues"""
    
    console.print(f"[bold blue]Starting OAuth GCP Log Audit[/bold blue]")
    console.print(f"Project: [cyan]{project}[/cyan]")
    console.print(f"Time range: Last [cyan]{hours}[/cyan] hours\n")
    
    # Set up GCP credentials if needed
    if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
        cred_path = os.path.expanduser('~/.config/gcloud/application_default_credentials.json')
        if os.path.exists(cred_path):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = cred_path
        else:
            console.print("[yellow] WARNING:  No GCP credentials found. Run 'gcloud auth application-default login'[/yellow]")
    
    try:
        # Initialize analyzer
        analyzer = OAuthLogAnalyzer(project, hours)
        
        # Fetch logs
        logs = analyzer.fetch_oauth_logs()
        
        if not logs:
            console.print("[yellow]No OAuth logs found in the specified time range[/yellow]")
            return
        
        # Analyze logs
        analysis = analyzer.analyze_oauth_flow(logs)
        
        # Generate report
        analyzer.generate_report(analysis)
        
        # Export if requested
        if export:
            analyzer.export_session_details(export)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise


if __name__ == '__main__':
    main()
