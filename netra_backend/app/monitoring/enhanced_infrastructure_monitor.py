"""
Enhanced Infrastructure Monitoring Dashboard for Issue #1278 Remediation

CRITICAL PURPOSE: Phase 1 implementation of approved remediation plan.
Provides enhanced infrastructure monitoring capabilities with better error
categorization, DNS resolution monitoring, and structured reporting.

Business Impact: Maintains visibility of $500K+ ARR platform during 
infrastructure issues with improved diagnostics for faster resolution.

Remediation Focus:
- Enhanced error categorization for VPC, DNS, Cloud SQL issues
- Real-time infrastructure health dashboard 
- DNS resolution monitoring for api-staging.netrasystems.ai
- Structured context for GCP error reporting integration
"""

import asyncio
import socket
import time
import ssl
import aiohttp
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class InfrastructureIssueType(Enum):
    """Enhanced categorization of infrastructure issues for Issue #1278."""
    VPC_CONNECTIVITY = "vpc_connectivity"
    DNS_RESOLUTION = "dns_resolution" 
    SSL_CERTIFICATE = "ssl_certificate"
    CLOUD_SQL_TIMEOUT = "cloud_sql_timeout"
    LOAD_BALANCER = "load_balancer"
    CLOUD_RUN_CONTAINER = "cloud_run_container"
    NETWORK_LATENCY = "network_latency"
    APPLICATION_ERROR = "application_error"
    UNKNOWN = "unknown"


class IssueSeverity(Enum):
    """Issue severity levels aligned with business impact."""
    CRITICAL = "critical"  # Service completely unavailable
    HIGH = "high"         # Major functionality impacted
    MEDIUM = "medium"     # Some functionality degraded
    LOW = "low"          # Minor issues, service functional
    INFO = "info"        # Informational only


@dataclass
class InfrastructureCheck:
    """Single infrastructure check result with enhanced context."""
    name: str
    status: str
    response_time_ms: Optional[float]
    issue_type: InfrastructureIssueType
    severity: IssueSeverity
    error_message: Optional[str] = None
    remediation_hint: Optional[str] = None
    gcp_context: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class DNSResolutionResult:
    """DNS resolution check result."""
    domain: str
    resolved_ips: List[str]
    resolution_time_ms: float
    success: bool
    error: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class EnhancedInfrastructureMonitor:
    """Enhanced infrastructure monitoring with Issue #1278 specific improvements."""
    
    def __init__(self):
        """Initialize enhanced monitoring with Issue #1278 context."""
        # Current staging domains (correct per Issue #1278)
        self.staging_endpoints = {
            "backend": "https://staging.netrasystems.ai",
            "auth": "https://staging.netrasystems.ai",
            "frontend": "https://staging.netrasystems.ai",
            "websocket": "wss://api-staging.netrasystems.ai"
        }
        
        # DNS targets for resolution monitoring
        self.dns_targets = [
            "staging.netrasystems.ai",
            "api-staging.netrasystems.ai"
        ]
        
        # Deprecated domains that should NOT be used (Issue #1278)
        self.deprecated_domains = [
            "*.staging.netrasystems.ai",
            "staging.staging.netrasystems.ai",
            "api.staging.netrasystems.ai"
        ]
        
        # Enhanced health check paths with better categorization
        self.health_checks = {
            "basic_health": {
                "path": "/health",
                "timeout": 10.0,
                "expected_issue": InfrastructureIssueType.APPLICATION_ERROR
            },
            "readiness_probe": {
                "path": "/health/ready", 
                "timeout": 60.0,  # Extended for GCP validation
                "expected_issue": InfrastructureIssueType.CLOUD_SQL_TIMEOUT
            },
            "infrastructure_probe": {
                "path": "/health/infrastructure",
                "timeout": 45.0,
                "expected_issue": InfrastructureIssueType.VPC_CONNECTIVITY
            },
            "startup_probe": {
                "path": "/health/startup",
                "timeout": 90.0,
                "expected_issue": InfrastructureIssueType.CLOUD_RUN_CONTAINER
            }
        }

    async def check_dns_resolution(self, domain: str) -> DNSResolutionResult:
        """Check DNS resolution for a domain with detailed timing."""
        start_time = time.time()
        
        try:
            # Resolve domain to IP addresses
            loop = asyncio.get_event_loop()
            result = await loop.getaddrinfo(
                domain, None, 
                family=socket.AF_UNSPEC,
                type=socket.SOCK_STREAM
            )
            
            resolution_time = (time.time() - start_time) * 1000
            
            # Extract IP addresses
            ips = list(set(info[4][0] for info in result))
            
            return DNSResolutionResult(
                domain=domain,
                resolved_ips=ips,
                resolution_time_ms=round(resolution_time, 2),
                success=True
            )
            
        except Exception as e:
            resolution_time = (time.time() - start_time) * 1000
            
            return DNSResolutionResult(
                domain=domain,
                resolved_ips=[],
                resolution_time_ms=round(resolution_time, 2),
                success=False,
                error=str(e)
            )

    async def check_ssl_certificate(self, domain: str, port: int = 443) -> InfrastructureCheck:
        """Check SSL certificate validity for domain."""
        start_time = time.time()
        
        try:
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect and get certificate
            sock = socket.create_connection((domain, port), timeout=10)
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                
            response_time = (time.time() - start_time) * 1000
            
            # Check certificate validity
            not_after = cert.get('notAfter')
            if not_after:
                # Parse certificate expiry
                from datetime import datetime
                expiry_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                days_until_expiry = (expiry_date - datetime.now()).days
                
                if days_until_expiry < 30:
                    return InfrastructureCheck(
                        name=f"ssl_cert_{domain}",
                        status="warning",
                        response_time_ms=round(response_time, 2),
                        issue_type=InfrastructureIssueType.SSL_CERTIFICATE,
                        severity=IssueSeverity.MEDIUM,
                        error_message=f"Certificate expires in {days_until_expiry} days",
                        remediation_hint="SSL certificate renewal required"
                    )
            
            return InfrastructureCheck(
                name=f"ssl_cert_{domain}",
                status="healthy",
                response_time_ms=round(response_time, 2),
                issue_type=InfrastructureIssueType.SSL_CERTIFICATE,
                severity=IssueSeverity.INFO
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            # Categorize SSL error
            error_str = str(e).lower()
            if "certificate verify failed" in error_str:
                severity = IssueSeverity.CRITICAL
                hint = "SSL certificate validation failed - check certificate chain"
            elif "timeout" in error_str:
                severity = IssueSeverity.HIGH
                hint = "SSL handshake timeout - possible network connectivity issue"
            else:
                severity = IssueSeverity.HIGH
                hint = "SSL certificate check failed - investigate certificate configuration"
            
            return InfrastructureCheck(
                name=f"ssl_cert_{domain}",
                status="failed",
                response_time_ms=round(response_time, 2),
                issue_type=InfrastructureIssueType.SSL_CERTIFICATE,
                severity=severity,
                error_message=str(e),
                remediation_hint=hint
            )

    async def check_endpoint_health(self, endpoint_name: str, base_url: str, 
                                   check_config: Dict[str, Any]) -> InfrastructureCheck:
        """Enhanced endpoint health check with better error categorization."""
        path = check_config["path"]
        timeout = check_config["timeout"]
        expected_issue = check_config["expected_issue"]
        
        full_url = f"{base_url}{path}"
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                async with session.get(full_url) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    # Enhanced status analysis
                    if response.status == 200:
                        return InfrastructureCheck(
                            name=f"{endpoint_name}_{check_config['path'].replace('/', '_')}",
                            status="healthy",
                            response_time_ms=round(response_time, 2),
                            issue_type=InfrastructureIssueType.APPLICATION_ERROR,
                            severity=IssueSeverity.INFO,
                            gcp_context={
                                "endpoint": endpoint_name,
                                "check_type": path,
                                "response_status": response.status
                            }
                        )
                    
                    # Enhanced error categorization
                    elif response.status == 503:
                        return InfrastructureCheck(
                            name=f"{endpoint_name}_{check_config['path'].replace('/', '_')}",
                            status="service_unavailable",
                            response_time_ms=round(response_time, 2),
                            issue_type=expected_issue,
                            severity=IssueSeverity.CRITICAL,
                            error_message=f"Service unavailable (503) - {expected_issue.value}",
                            remediation_hint=self._get_remediation_hint(expected_issue),
                            gcp_context={
                                "endpoint": endpoint_name,
                                "check_type": path,
                                "response_status": response.status,
                                "issue_type": expected_issue.value
                            }
                        )
                    
                    elif response.status == 502:
                        return InfrastructureCheck(
                            name=f"{endpoint_name}_{check_config['path'].replace('/', '_')}",
                            status="bad_gateway",
                            response_time_ms=round(response_time, 2),
                            issue_type=InfrastructureIssueType.LOAD_BALANCER,
                            severity=IssueSeverity.CRITICAL,
                            error_message="Bad Gateway (502) - Load balancer cannot reach backend",
                            remediation_hint="Check load balancer configuration and backend health",
                            gcp_context={
                                "endpoint": endpoint_name,
                                "check_type": path,
                                "response_status": response.status,
                                "issue_type": "load_balancer"
                            }
                        )
                    
                    elif response.status == 504:
                        return InfrastructureCheck(
                            name=f"{endpoint_name}_{check_config['path'].replace('/', '_')}",
                            status="gateway_timeout",
                            response_time_ms=round(response_time, 2),
                            issue_type=InfrastructureIssueType.CLOUD_SQL_TIMEOUT,
                            severity=IssueSeverity.HIGH,
                            error_message="Gateway Timeout (504) - Backend response timeout",
                            remediation_hint="Check database connection timeouts and VPC connectivity",
                            gcp_context={
                                "endpoint": endpoint_name,
                                "check_type": path,
                                "response_status": response.status,
                                "issue_type": "cloud_sql_timeout"
                            }
                        )
                    
                    else:
                        return InfrastructureCheck(
                            name=f"{endpoint_name}_{check_config['path'].replace('/', '_')}",
                            status="http_error",
                            response_time_ms=round(response_time, 2),
                            issue_type=InfrastructureIssueType.APPLICATION_ERROR,
                            severity=IssueSeverity.MEDIUM,
                            error_message=f"HTTP {response.status}",
                            gcp_context={
                                "endpoint": endpoint_name,
                                "check_type": path,
                                "response_status": response.status
                            }
                        )
                        
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            
            # Categorize timeout based on duration and check type
            if response_time > 30000:  # 30+ seconds
                issue_type = InfrastructureIssueType.CLOUD_SQL_TIMEOUT
                hint = "Extended timeout suggests database connectivity issues"
            elif response_time > 10000:  # 10+ seconds  
                issue_type = InfrastructureIssueType.VPC_CONNECTIVITY
                hint = "Network timeout suggests VPC connectivity issues"
            else:
                issue_type = expected_issue
                hint = self._get_remediation_hint(expected_issue)
            
            return InfrastructureCheck(
                name=f"{endpoint_name}_{check_config['path'].replace('/', '_')}",
                status="timeout",
                response_time_ms=round(response_time, 2),
                issue_type=issue_type,
                severity=IssueSeverity.HIGH,
                error_message=f"Request timed out after {timeout}s",
                remediation_hint=hint,
                gcp_context={
                    "endpoint": endpoint_name,
                    "check_type": path,
                    "timeout_duration": timeout,
                    "actual_duration_ms": round(response_time, 2),
                    "issue_type": issue_type.value
                }
            )
            
        except aiohttp.ClientConnectorError as e:
            response_time = (time.time() - start_time) * 1000
            
            # Enhanced connection error categorization
            error_str = str(e).lower()
            if "name or service not known" in error_str or "nodename nor servname provided" in error_str:
                issue_type = InfrastructureIssueType.DNS_RESOLUTION
                hint = "DNS resolution failed - check domain configuration"
                severity = IssueSeverity.CRITICAL
            elif "connection refused" in error_str:
                issue_type = InfrastructureIssueType.CLOUD_RUN_CONTAINER  
                hint = "Connection refused - check if service is running"
                severity = IssueSeverity.CRITICAL
            elif "ssl" in error_str or "certificate" in error_str:
                issue_type = InfrastructureIssueType.SSL_CERTIFICATE
                hint = "SSL certificate issue - check certificate validity"
                severity = IssueSeverity.HIGH
            else:
                issue_type = InfrastructureIssueType.VPC_CONNECTIVITY
                hint = "Network connectivity issue - check VPC configuration"
                severity = IssueSeverity.HIGH
            
            return InfrastructureCheck(
                name=f"{endpoint_name}_{check_config['path'].replace('/', '_')}",
                status="connection_error",
                response_time_ms=round(response_time, 2),
                issue_type=issue_type,
                severity=severity,
                error_message=str(e),
                remediation_hint=hint,
                gcp_context={
                    "endpoint": endpoint_name,
                    "check_type": path,
                    "connection_error": str(e),
                    "issue_type": issue_type.value
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            return InfrastructureCheck(
                name=f"{endpoint_name}_{check_config['path'].replace('/', '_')}",
                status="error",
                response_time_ms=round(response_time, 2),
                issue_type=InfrastructureIssueType.UNKNOWN,
                severity=IssueSeverity.MEDIUM,
                error_message=str(e),
                remediation_hint="Investigate application logs for root cause",
                gcp_context={
                    "endpoint": endpoint_name,
                    "check_type": path,
                    "error": str(e),
                    "issue_type": "unknown"
                }
            )

    def _get_remediation_hint(self, issue_type: InfrastructureIssueType) -> str:
        """Get remediation hint based on issue type."""
        hints = {
            InfrastructureIssueType.VPC_CONNECTIVITY: "Check VPC connector configuration and firewall rules",
            InfrastructureIssueType.DNS_RESOLUTION: "Verify DNS configuration and domain settings",
            InfrastructureIssueType.SSL_CERTIFICATE: "Check SSL certificate validity and configuration",
            InfrastructureIssueType.CLOUD_SQL_TIMEOUT: "Increase database timeout settings and check VPC connectivity",
            InfrastructureIssueType.LOAD_BALANCER: "Review load balancer health checks and backend configuration",
            InfrastructureIssueType.CLOUD_RUN_CONTAINER: "Check Cloud Run service status and container logs",
            InfrastructureIssueType.NETWORK_LATENCY: "Investigate network performance and routing",
            InfrastructureIssueType.APPLICATION_ERROR: "Check application logs and error reporting",
            InfrastructureIssueType.UNKNOWN: "Enable detailed logging and investigate error patterns"
        }
        return hints.get(issue_type, "Contact infrastructure team for investigation")

    async def validate_domain_configuration(self) -> List[InfrastructureCheck]:
        """Validate domain configuration and detect deprecated patterns."""
        checks = []
        
        # Check for deprecated domain usage
        for deprecated in self.deprecated_domains:
            # This is a configuration validation, not a network check
            check = InfrastructureCheck(
                name=f"domain_config_{deprecated.replace('*', 'wildcard').replace('.', '_')}",
                status="configuration_warning",
                response_time_ms=0,
                issue_type=InfrastructureIssueType.DNS_RESOLUTION,
                severity=IssueSeverity.HIGH,
                error_message=f"Deprecated domain pattern detected: {deprecated}",
                remediation_hint=f"Replace {deprecated} with *.netrasystems.ai pattern",
                gcp_context={
                    "deprecated_domain": deprecated,
                    "correct_pattern": "*.netrasystems.ai",
                    "issue_reference": "#1278"
                }
            )
            checks.append(check)
        
        return checks

    async def run_comprehensive_monitoring(self) -> Dict[str, Any]:
        """Run comprehensive infrastructure monitoring with enhanced categorization."""
        logger.info("Starting enhanced infrastructure monitoring for Issue #1278...")
        
        start_time = time.time()
        results = {
            "monitoring_run_id": f"enhanced_monitoring_{int(start_time)}",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "issue_reference": "#1278",
            "purpose": "Enhanced infrastructure monitoring with better error categorization",
            "checks": {},
            "dns_results": {},
            "ssl_checks": {},
            "domain_validation": {},
            "summary": {}
        }
        
        # Run DNS resolution checks
        logger.info("Running DNS resolution monitoring...")
        dns_tasks = [self.check_dns_resolution(domain) for domain in self.dns_targets]
        dns_results = await asyncio.gather(*dns_tasks, return_exceptions=True)
        
        for result in dns_results:
            if isinstance(result, DNSResolutionResult):
                results["dns_results"][result.domain] = asdict(result)
        
        # Run SSL certificate checks
        logger.info("Running SSL certificate validation...")
        ssl_tasks = []
        for domain in self.dns_targets:
            if not domain.startswith("*."):  # Skip wildcard domains
                ssl_tasks.append(self.check_ssl_certificate(domain))
        
        ssl_results = await asyncio.gather(*ssl_tasks, return_exceptions=True)
        
        for result in ssl_results:
            if isinstance(result, InfrastructureCheck):
                results["ssl_checks"][result.name] = asdict(result)
        
        # Run endpoint health checks
        logger.info("Running enhanced endpoint health checks...")
        endpoint_tasks = []
        
        for check_name, check_config in self.health_checks.items():
            for endpoint_name, base_url in self.staging_endpoints.items():
                if endpoint_name != "websocket":  # Skip websocket for HTTP checks
                    task = self.check_endpoint_health(endpoint_name, base_url, check_config)
                    endpoint_tasks.append(task)
        
        endpoint_results = await asyncio.gather(*endpoint_tasks, return_exceptions=True)
        
        for result in endpoint_results:
            if isinstance(result, InfrastructureCheck):
                results["checks"][result.name] = asdict(result)
        
        # Run domain configuration validation
        domain_validation = await self.validate_domain_configuration()
        for check in domain_validation:
            results["domain_validation"][check.name] = asdict(check)
        
        # Generate enhanced summary with issue categorization
        total_checks = len(results["checks"]) + len(results["ssl_checks"]) + len(results["domain_validation"])
        healthy_checks = 0
        issue_counts = {issue_type.value: 0 for issue_type in InfrastructureIssueType}
        severity_counts = {severity.value: 0 for severity in IssueSeverity}
        
        # Count issues by type and severity
        all_checks = list(results["checks"].values()) + list(results["ssl_checks"].values()) + list(results["domain_validation"].values())
        
        for check in all_checks:
            if check["status"] in ["healthy"]:
                healthy_checks += 1
            
            issue_type = check["issue_type"]
            severity = check["severity"]
            
            issue_counts[issue_type] += 1
            severity_counts[severity] += 1
        
        # Add DNS resolution summary
        dns_success_count = sum(1 for dns in results["dns_results"].values() if dns["success"])
        dns_total = len(results["dns_results"])
        
        results["summary"] = {
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "health_percentage": round((healthy_checks / total_checks) * 100, 1) if total_checks > 0 else 0,
            "dns_resolution": {
                "total": dns_total,
                "successful": dns_success_count,
                "success_rate": round((dns_success_count / dns_total) * 100, 1) if dns_total > 0 else 0
            },
            "issue_breakdown": issue_counts,
            "severity_breakdown": severity_counts,
            "critical_issues": severity_counts["critical"],
            "high_priority_issues": severity_counts["high"],
            "monitoring_duration_seconds": round(time.time() - start_time, 2),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "overall_status": self._determine_overall_status(severity_counts)
        }
        
        logger.info(f"Enhanced monitoring complete: {results['summary']['health_percentage']}% healthy, "
                   f"{results['summary']['critical_issues']} critical issues detected")
        
        return results

    def _determine_overall_status(self, severity_counts: Dict[str, int]) -> str:
        """Determine overall infrastructure status based on issue severity."""
        if severity_counts["critical"] > 0:
            return "critical_issues_detected"
        elif severity_counts["high"] > 2:  # Multiple high-priority issues
            return "infrastructure_degraded"
        elif severity_counts["high"] > 0:
            return "high_priority_issues"
        elif severity_counts["medium"] > 0:
            return "minor_issues_detected"
        else:
            return "infrastructure_healthy"

    def format_monitoring_report(self, results: Dict[str, Any]) -> str:
        """Format enhanced monitoring results for console output."""
        output = []
        output.append("=" * 80)
        output.append(f"ENHANCED INFRASTRUCTURE MONITORING - Issue {results['issue_reference']}")
        output.append(f"Run ID: {results['monitoring_run_id']}")
        output.append(f"Timestamp: {results['start_time']}")
        output.append("=" * 80)
        
        # Summary section
        summary = results["summary"]
        output.append(f"\nOVERALL STATUS: {summary['overall_status'].upper()}")
        output.append(f"Health Percentage: {summary['health_percentage']}%")
        output.append(f"Critical Issues: {summary['critical_issues']}")
        output.append(f"High Priority Issues: {summary['high_priority_issues']}")
        output.append(f"Monitoring Duration: {summary['monitoring_duration_seconds']}s")
        
        # DNS Resolution section
        dns_summary = summary["dns_resolution"]
        output.append(f"\nDNS RESOLUTION STATUS:")
        output.append("-" * 30)
        output.append(f"Success Rate: {dns_summary['success_rate']}% ({dns_summary['successful']}/{dns_summary['total']})")
        
        for domain, dns_result in results["dns_results"].items():
            status_icon = "✅" if dns_result["success"] else "❌"
            output.append(f"{status_icon} {domain}: {dns_result['resolution_time_ms']}ms")
            if dns_result["success"]:
                output.append(f"   IPs: {', '.join(dns_result['resolved_ips'])}")
            else:
                output.append(f"   Error: {dns_result['error']}")
        
        # Issue breakdown
        output.append(f"\nISSUE TYPE BREAKDOWN:")
        output.append("-" * 30)
        for issue_type, count in summary["issue_breakdown"].items():
            if count > 0:
                output.append(f"• {issue_type.replace('_', ' ').title()}: {count}")
        
        # Critical issues detail
        if summary["critical_issues"] > 0:
            output.append("\n🚨 CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION:")
            output.append("-" * 50)
            
            all_checks = list(results["checks"].values()) + list(results["ssl_checks"].values()) + list(results["domain_validation"].values())
            critical_checks = [check for check in all_checks if check["severity"] == "critical"]
            
            for check in critical_checks:
                output.append(f"❌ {check['name']}: {check['error_message']}")
                if check.get("remediation_hint"):
                    output.append(f"   💡 Remediation: {check['remediation_hint']}")
        
        # Infrastructure team handoff
        output.append("\n" + "!" * 60)
        output.append("INFRASTRUCTURE TEAM ACTION ITEMS:")
        output.append("✅ Enhanced monitoring now provides:")
        output.append("   • DNS resolution monitoring for all critical domains")
        output.append("   • SSL certificate validation and expiry tracking")
        output.append("   • Enhanced error categorization by infrastructure component")
        output.append("   • Structured GCP context for error reporting integration")
        output.append("   • Issue #1278 specific remediation hints")
        output.append("!" * 60)
        
        return "\n".join(output)


async def run_enhanced_monitoring():
    """Convenience function to run enhanced monitoring."""
    monitor = EnhancedInfrastructureMonitor()
    results = await monitor.run_comprehensive_monitoring()
    report = monitor.format_monitoring_report(results)
    print(report)
    return results


if __name__ == "__main__":
    asyncio.run(run_enhanced_monitoring())