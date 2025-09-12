#!/usr/bin/env python3
"""
Comprehensive GCP Staging Logs Analysis Script
Analyzes logs from all three deployed services to identify issues using Five Whys methodology.
"""

import json
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Any
import re


class StagingLogAnalyzer:
    """Analyzes GCP staging logs for all services."""
    
    def __init__(self):
        self.project_id = "netra-staging"
        self.services = [
            "netra-backend-staging",
            "netra-auth-service", 
            "netra-frontend-staging"
        ]
        
    def fetch_logs(self, service_name: str, filters: str = "", limit: int = 50) -> List[Dict]:
        """Fetch logs from a specific service."""
        base_filter = f'resource.type="cloud_run_revision" AND resource.labels.service_name="{service_name}"'
        
        if filters:
            full_filter = f'{base_filter} AND ({filters})'
        else:
            full_filter = base_filter
            
        cmd = [
            "gcloud", "logging", "read",
            full_filter,
            "--project", self.project_id,
            "--limit", str(limit),
            "--format", "json",
            "--freshness", "6h"
        ]
            
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout) if result.stdout.strip() else []
        except subprocess.CalledProcessError as e:
            print(f"Error fetching logs for {service_name}: {e}")
            return []
    
    def test_health_endpoints(self) -> Dict[str, str]:
        """Test health endpoints for all services."""
        endpoints = {
            "netra-backend-staging": "https://netra-backend-staging-701982941522.us-central1.run.app/health",
            "netra-auth-service": "https://netra-auth-service-701982941522.us-central1.run.app/health",
            "netra-frontend-staging": "https://netra-frontend-staging-701982941522.us-central1.run.app/"
        }
        
        results = {}
        for service, url in endpoints.items():
            try:
                result = subprocess.run([
                    "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url
                ], capture_output=True, text=True, timeout=10)
                
                status_code = result.stdout.strip()
                results[service] = "healthy" if status_code == "200" else f"unhealthy ({status_code})"
            except Exception as e:
                results[service] = f"error: {str(e)}"
        
        return results
    
    def clean_ansi_codes(self, text: str) -> str:
        """Remove ANSI color codes from text."""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def classify_issue(self, message: str) -> tuple:
        """Classify the issue type and severity."""
        message_lower = message.lower()
        clean_msg = self.clean_ansi_codes(message_lower)
        
        # Critical issues
        if "secret_key must be at least 32 characters" in clean_msg:
            return "CONFIGURATION_ERROR", "CRITICAL"
        
        # High severity
        if "exception" in clean_msg and "startup" in clean_msg:
            return "STARTUP_FAILURE", "HIGH"
        elif "database" in clean_msg and ("connection refused" in clean_msg or "timeout" in clean_msg):
            return "DATABASE_CONNECTION", "HIGH"
            
        # Medium severity  
        if "clickhouse" in clean_msg and "connection failed" in clean_msg:
            return "CLICKHOUSE_CONNECTION", "MEDIUM"
        elif "timeout" in clean_msg and ("clickhouse" in clean_msg or "redis" in clean_msg):
            return "EXTERNAL_SERVICE_TIMEOUT", "MEDIUM"
        elif "http" in clean_msg and ("4" in clean_msg or "5" in clean_msg) and "error" in clean_msg:
            return "HTTP_ERROR", "MEDIUM"
            
        # Low severity
        if "error while closing socket" in clean_msg and "bad file descriptor" in clean_msg:
            return "GRACEFUL_SHUTDOWN", "LOW"
        elif "retrying" in clean_msg and "timeout" in clean_msg:
            return "CONNECTION_RETRY", "LOW"
        elif "graceful degradation" in clean_msg:
            return "EXPECTED_DEGRADATION", "LOW"
        elif "warning" in clean_msg:
            return "WARNING", "LOW"
            
        return "UNKNOWN", "MEDIUM"
    
    def generate_five_whys(self, message: str, issue_type: str) -> List[str]:
        """Generate Five Whys analysis for the issue."""
        five_whys_mapping = {
            "CONFIGURATION_ERROR": [
                "Why 1: SECRET_KEY configuration is too short (less than 32 characters)",
                "Why 2: The secret key in GCP Secret Manager was not properly generated/updated",
                "Why 3: The deployment process didn't validate secret requirements before deployment",
                "Why 4: Secret validation is missing from the startup checks",
                "Why 5: Root cause: Insufficient validation of security configuration during deployment pipeline"
            ],
            "CLICKHOUSE_CONNECTION": [
                "Why 1: ClickHouse service is not responding at clickhouse.staging.netrasystems.ai:8443",
                "Why 2: ClickHouse infrastructure is not deployed in staging environment",
                "Why 3: Staging environment is configured to use optional ClickHouse (graceful degradation)",
                "Why 4: ClickHouse infrastructure provisioning was not included in staging deployment",
                "Why 5: Root cause: Staging environment designed to work without ClickHouse for cost optimization"
            ],
            "EXTERNAL_SERVICE_TIMEOUT": [
                "Why 1: Connection to external service times out after configured timeout period",
                "Why 2: External service (ClickHouse/Redis) is not running or unreachable",
                "Why 3: Network configuration or firewall blocking connections",
                "Why 4: External service infrastructure not provisioned in staging",
                "Why 5: Root cause: Optional dependencies not set up in staging environment for cost reasons"
            ],
            "HTTP_ERROR": [
                "Why 1: HTTP request returns 4xx or 5xx status code",
                "Why 2: Requested resource not found or server error occurred",
                "Why 3: Application routing or resource deployment issue", 
                "Why 4: Configuration mismatch between services",
                "Why 5: Root cause: Service integration or deployment configuration error"
            ],
            "DATABASE_CONNECTION": [
                "Why 1: Database connection attempt fails",
                "Why 2: Database service unavailable or network issue",
                "Why 3: Connection string or credentials incorrect",
                "Why 4: Database infrastructure not properly configured",
                "Why 5: Root cause: Database deployment or configuration issue"
            ],
            "GRACEFUL_SHUTDOWN": [
                "Why 1: Socket closing errors during service shutdown",
                "Why 2: Normal graceful shutdown process in Cloud Run",
                "Why 3: SIGTERM signal received during deployment",
                "Why 4: Cloud Run instance lifecycle management",
                "Why 5: Root cause: Expected behavior during deployments (not an error)"
            ],
            "CONNECTION_RETRY": [
                "Why 1: Connection retries are being attempted due to failures",
                "Why 2: Initial connection attempts fail consistently", 
                "Why 3: Target service endpoint is unreachable or overloaded",
                "Why 4: Network reliability or service availability issue",
                "Why 5: Root cause: Dependent service not available or misconfigured"
            ],
            "EXPECTED_DEGRADATION": [
                "Why 1: System is operating in degraded mode for optional services",
                "Why 2: Non-critical dependencies (ClickHouse) are not available",
                "Why 3: Staging environment configured without full infrastructure stack",
                "Why 4: Cost optimization strategy excludes non-essential services in staging", 
                "Why 5: Root cause: Intentional architecture design for cost-effective staging"
            ]
        }
        
        return five_whys_mapping.get(issue_type, [
            "Why 1: Unknown error pattern detected",
            "Why 2: Error classification needs improvement for this pattern",
            "Why 3: Insufficient monitoring and logging for this scenario",
            "Why 4: Error handling patterns need enhancement",
            "Why 5: Root cause: Need better error analysis and handling framework"
        ])
    
    def analyze_service_logs(self, service_name: str) -> Dict[str, Any]:
        """Analyze logs for a specific service."""
        print(f"Analyzing {service_name}...")
        
        # Fetch different types of logs
        error_logs = self.fetch_logs(service_name, 'severity>=ERROR OR textPayload:"ERROR"', 30)
        warning_logs = self.fetch_logs(service_name, 'textPayload:"WARNING"', 30) 
        failure_logs = self.fetch_logs(service_name, 'textPayload:"failed" OR textPayload:"timeout" OR textPayload:"exception"', 20)
        
        issues = []
        
        # Process all logs
        all_logs = error_logs + warning_logs + failure_logs
        processed_messages = set()  # Avoid duplicates
        
        for log in all_logs:
            text_payload = log.get("textPayload", "")
            if not text_payload or len(text_payload) < 20:
                continue
                
            clean_message = self.clean_ansi_codes(text_payload)
            
            # Skip duplicates
            message_key = clean_message[:100]  # First 100 chars as key
            if message_key in processed_messages:
                continue
            processed_messages.add(message_key)
            
            issue_type, severity = self.classify_issue(clean_message)
            
            # Skip normal shutdown messages
            if issue_type == "GRACEFUL_SHUTDOWN":
                continue
                
            issues.append({
                "timestamp": log.get("timestamp", ""),
                "service": service_name,
                "type": issue_type,
                "severity": severity,
                "message": clean_message[:300],  # Truncate for readability
                "five_whys": self.generate_five_whys(clean_message, issue_type)
            })
        
        return {
            "service": service_name,
            "issues": issues,
            "total_logs_analyzed": len(all_logs),
            "unique_issues": len(issues)
        }
    
    def generate_report(self) -> str:
        """Generate comprehensive analysis report."""
        print("Starting GCP Staging Logs Analysis using Five Whys Methodology...")
        
        # Test health endpoints first
        health_status = self.test_health_endpoints()
        
        # Analyze each service
        all_issues = []
        service_summaries = []
        
        for service in self.services:
            analysis = self.analyze_service_logs(service)
            service_summaries.append(analysis)
            all_issues.extend(analysis["issues"])
        
        # Generate report
        report = []
        report.append("# GCP Staging Environment Audit Report")
        report.append("## Using Five Whys Root Cause Analysis Methodology")
        report.append(f"**Analysis Time:** {datetime.now().isoformat()}")
        report.append(f"**Services Analyzed:** {len(self.services)}")
        report.append("")
        
        # Executive Summary
        total_issues = len(all_issues)
        critical_issues = len([i for i in all_issues if i['severity'] == 'CRITICAL'])
        high_issues = len([i for i in all_issues if i['severity'] == 'HIGH'])
        medium_issues = len([i for i in all_issues if i['severity'] == 'MEDIUM'])
        low_issues = len([i for i in all_issues if i['severity'] == 'LOW'])
        
        report.append("##  CHART:  Executive Summary")
        report.append(f"- **Total Issues Found:** {total_issues}")
        report.append(f"- **Critical Issues:** {critical_issues}")
        report.append(f"- **High Priority Issues:** {high_issues}")
        report.append(f"- **Medium Priority Issues:** {medium_issues}")
        report.append(f"- **Low Priority Issues:** {low_issues}")
        report.append("")
        
        # Service Health Status
        report.append("## [U+1F3E5] Service Health Status")
        for service in self.services:
            status = health_status.get(service, "unknown")
            emoji = " PASS: " if "healthy" in status else " FAIL: "
            report.append(f"- **{service}:** {emoji} {status}")
        report.append("")
        
        # Issues by Severity  
        if all_issues:
            report.append("##  ALERT:  Issues Found (Five Whys Analysis)")
            
            # Group by severity
            issues_by_severity = {}
            for issue in all_issues:
                severity = issue['severity']
                if severity not in issues_by_severity:
                    issues_by_severity[severity] = []
                issues_by_severity[severity].append(issue)
            
            # Report by severity (Critical first)
            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                if severity not in issues_by_severity:
                    continue
                    
                issues = issues_by_severity[severity]
                emoji = {"CRITICAL": " FIRE: ", "HIGH": " WARNING: [U+FE0F]", "MEDIUM": " LIGHTNING: ", "LOW": "[U+2139][U+FE0F]"}[severity]
                
                report.append(f"### {emoji} {severity} Priority Issues ({len(issues)} found)")
                
                for i, issue in enumerate(issues, 1):
                    report.append(f"#### Issue #{i}: {issue['type']} - {issue['service']}")
                    report.append(f"**Timestamp:** {issue['timestamp']}")
                    report.append("")
                    report.append("**Error Message:**")
                    report.append("```")
                    report.append(issue['message'])
                    report.append("```")
                    report.append("")
                    report.append("**Five Whys Root Cause Analysis:**")
                    for why in issue['five_whys']:
                        report.append(f"- {why}")
                    report.append("")
        else:
            report.append("##  PASS:  No Issues Found")
            report.append("All services are operating within normal parameters.")
            report.append("")
        
        # Recommendations
        report.append("##  IDEA:  Recommendations")
        
        if critical_issues > 0:
            report.append("###  FIRE:  Critical Actions Required:")
            report.append("- **Immediate:** Fix SECRET_KEY configuration in GCP Secret Manager")
            report.append("- **Immediate:** Validate all security configurations before deployment")
            report.append("- **Short-term:** Add configuration validation to CI/CD pipeline")
        
        if medium_issues > 0:
            report.append("###  LIGHTNING:  Medium Priority Actions:")
            if any("CLICKHOUSE" in i['type'] for i in all_issues):
                report.append("- **Document:** ClickHouse graceful degradation as expected staging behavior")
                report.append("- **Monitor:** Ensure no non-graceful ClickHouse failures occur")
            report.append("- **Implement:** Better error classification and alerting")
            report.append("- **Create:** Health check monitoring with SLO/SLA definitions")
        
        if low_issues > 0:
            report.append("### [U+2139][U+FE0F] Low Priority Improvements:")
            report.append("- **Enhance:** Structured logging with correlation IDs")
            report.append("- **Document:** Expected graceful degradation patterns")
            report.append("- **Improve:** Error message clarity and actionability")
        
        report.append("### [U+1F4CB] General Recommendations:")
        report.append("- **Create:** Runbooks for identified issue patterns")
        report.append("- **Implement:** Proactive monitoring and alerting")
        report.append("- **Establish:** Regular staging environment health checks")
        report.append("- **Document:** Staging vs production architectural differences")
        
        # Save detailed results
        results = {
            "timestamp": datetime.now().isoformat(),
            "health_status": health_status,
            "service_summaries": service_summaries,
            "total_issues": total_issues,
            "issues_by_severity": {
                "critical": critical_issues,
                "high": high_issues, 
                "medium": medium_issues,
                "low": low_issues
            },
            "all_issues": all_issues
        }
        
        with open("staging_logs.json", "w") as f:
            json.dump(results, f, indent=2)
        
        return "\n".join(report)


def main():
    """Main execution function."""
    analyzer = StagingLogAnalyzer()
    report = analyzer.generate_report()
    
    print("\n" + "="*80)
    print(report)
    print("="*80)
    
    print(f"\nDetailed analysis saved to: staging_logs.json")


if __name__ == "__main__":
    main()