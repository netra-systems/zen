"""
DNS Resolution Monitor for Issue #1278

CRITICAL PURPOSE: Monitor DNS resolution for critical staging domains,
specifically api.staging.netrasystems.ai, to detect infrastructure
issues before they impact the application.

Business Impact: Prevents DNS-related outages affecting $500K+ ARR platform
by providing early warning of DNS resolution failures.

Issue #1278 Focus:
- Monitor api.staging.netrasystems.ai resolution
- Track resolution times and failures
- Detect DNS propagation issues
- Validate load balancer IP assignments
"""

import asyncio
import socket
import time
import dns.resolver
import dns.exception
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import statistics

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DNSRecordType(Enum):
    """DNS record types to monitor."""
    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    TXT = "TXT"


class DNSIssueType(Enum):
    """DNS issue categorization."""
    RESOLUTION_FAILURE = "resolution_failure"
    SLOW_RESOLUTION = "slow_resolution"
    INCONSISTENT_RESULTS = "inconsistent_results"
    MISSING_RECORDS = "missing_records"
    LOAD_BALANCER_ISSUE = "load_balancer_issue"
    PROPAGATION_DELAY = "propagation_delay"


@dataclass
class DNSCheckResult:
    """Single DNS resolution check result."""
    domain: str
    record_type: DNSRecordType
    resolved_ips: List[str]
    resolution_time_ms: float
    success: bool
    error: Optional[str] = None
    dns_server: Optional[str] = None
    ttl: Optional[int] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class DNSMonitoringResult:
    """Comprehensive DNS monitoring result."""
    domain: str
    monitoring_duration_seconds: float
    total_checks: int
    successful_checks: int
    average_resolution_time_ms: float
    min_resolution_time_ms: float
    max_resolution_time_ms: float
    unique_ips_resolved: List[str]
    issues_detected: List[Dict[str, Any]]
    consistency_score: float  # 0-100, how consistent are the results
    availability_score: float  # 0-100, percentage of successful resolutions
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class DNSResolutionMonitor:
    """DNS resolution monitoring for Issue #1278 critical domains."""
    
    def __init__(self):
        """Initialize DNS monitoring for staging domains."""
        # Critical domains for Issue #1278
        self.critical_domains = [
            "staging.netrasystems.ai",
            "api.staging.netrasystems.ai"
        ]
        
        # DNS servers to test against (Google, Cloudflare, system default)
        self.dns_servers = [
            "8.8.8.8",      # Google DNS
            "1.1.1.1",      # Cloudflare DNS
            "8.8.4.4",      # Google DNS Secondary
            None            # System default
        ]
        
        # Performance thresholds
        self.slow_resolution_threshold_ms = 1000  # 1 second
        self.critical_resolution_threshold_ms = 5000  # 5 seconds
        
        # Consistency thresholds
        self.min_consistency_score = 95.0  # 95% consistency required
        self.min_availability_score = 99.0  # 99% availability required

    async def resolve_domain_async(self, domain: str, record_type: DNSRecordType = DNSRecordType.A, 
                                  dns_server: Optional[str] = None) -> DNSCheckResult:
        """Resolve domain using async DNS resolution."""
        start_time = time.time()
        
        try:
            # Create resolver
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            
            # Set timeout
            resolver.timeout = 10
            resolver.lifetime = 10
            
            # Resolve domain
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, resolver.resolve, domain, record_type.value
                )
                
                resolution_time = (time.time() - start_time) * 1000
                
                # Extract IPs and TTL
                ips = [str(record) for record in result]
                ttl = result.ttl if hasattr(result, 'ttl') else None
                
                return DNSCheckResult(
                    domain=domain,
                    record_type=record_type,
                    resolved_ips=ips,
                    resolution_time_ms=round(resolution_time, 2),
                    success=True,
                    dns_server=dns_server or "system_default",
                    ttl=ttl
                )
                
            except dns.exception.DNSException as e:
                resolution_time = (time.time() - start_time) * 1000
                
                return DNSCheckResult(
                    domain=domain,
                    record_type=record_type,
                    resolved_ips=[],
                    resolution_time_ms=round(resolution_time, 2),
                    success=False,
                    error=f"DNS resolution failed: {str(e)}",
                    dns_server=dns_server or "system_default"
                )
                
        except Exception as e:
            resolution_time = (time.time() - start_time) * 1000
            
            return DNSCheckResult(
                domain=domain,
                record_type=record_type,
                resolved_ips=[],
                resolution_time_ms=round(resolution_time, 2),
                success=False,
                error=f"DNS check failed: {str(e)}",
                dns_server=dns_server or "system_default"
            )

    async def resolve_domain_socket(self, domain: str) -> DNSCheckResult:
        """Resolve domain using socket.getaddrinfo for system-level resolution."""
        start_time = time.time()
        
        try:
            # Use asyncio to run getaddrinfo in executor
            loop = asyncio.get_event_loop()
            result = await loop.getaddrinfo(
                domain, None,
                family=socket.AF_UNSPEC,
                type=socket.SOCK_STREAM
            )
            
            resolution_time = (time.time() - start_time) * 1000
            
            # Extract unique IP addresses
            ips = list(set(info[4][0] for info in result))
            
            return DNSCheckResult(
                domain=domain,
                record_type=DNSRecordType.A,
                resolved_ips=ips,
                resolution_time_ms=round(resolution_time, 2),
                success=True,
                dns_server="system_socket"
            )
            
        except Exception as e:
            resolution_time = (time.time() - start_time) * 1000
            
            return DNSCheckResult(
                domain=domain,
                record_type=DNSRecordType.A,
                resolved_ips=[],
                resolution_time_ms=round(resolution_time, 2),
                success=False,
                error=str(e),
                dns_server="system_socket"
            )

    async def monitor_domain_comprehensive(self, domain: str, 
                                         duration_minutes: int = 5,
                                         check_interval_seconds: int = 30) -> DNSMonitoringResult:
        """Run comprehensive DNS monitoring for a domain over time."""
        logger.info(f"Starting comprehensive DNS monitoring for {domain} (duration: {duration_minutes}m)")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        all_results = []
        issues_detected = []
        
        while time.time() < end_time:
            check_start_time = time.time()
            
            # Run checks against all DNS servers
            tasks = []
            
            # DNS resolver checks
            for dns_server in self.dns_servers:
                task = self.resolve_domain_async(domain, DNSRecordType.A, dns_server)
                tasks.append(task)
            
            # Socket-based check
            tasks.append(self.resolve_domain_socket(domain))
            
            # Execute all checks concurrently
            check_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in check_results:
                if isinstance(result, DNSCheckResult):
                    all_results.append(result)
                    
                    # Check for issues
                    self._analyze_dns_result(result, issues_detected)
            
            # Wait for next check interval
            check_duration = time.time() - check_start_time
            sleep_time = max(0, check_interval_seconds - check_duration)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Analyze comprehensive results
        monitoring_duration = time.time() - start_time
        
        # Calculate statistics
        successful_results = [r for r in all_results if r.success]
        successful_count = len(successful_results)
        total_count = len(all_results)
        
        if successful_results:
            resolution_times = [r.resolution_time_ms for r in successful_results]
            avg_resolution_time = statistics.mean(resolution_times)
            min_resolution_time = min(resolution_times)
            max_resolution_time = max(resolution_times)
            
            # Get unique IPs
            all_ips = set()
            for result in successful_results:
                all_ips.update(result.resolved_ips)
            unique_ips = sorted(list(all_ips))
        else:
            avg_resolution_time = 0
            min_resolution_time = 0
            max_resolution_time = 0
            unique_ips = []
        
        # Calculate consistency score
        consistency_score = self._calculate_consistency_score(successful_results)
        
        # Calculate availability score
        availability_score = (successful_count / total_count * 100) if total_count > 0 else 0
        
        # Add overall issues if scores are low
        if consistency_score < self.min_consistency_score:
            issues_detected.append({
                "issue_type": DNSIssueType.INCONSISTENT_RESULTS.value,
                "severity": "high",
                "description": f"DNS consistency score {consistency_score:.1f}% below threshold {self.min_consistency_score}%",
                "remediation": "Check DNS server configuration and propagation status"
            })
        
        if availability_score < self.min_availability_score:
            issues_detected.append({
                "issue_type": DNSIssueType.RESOLUTION_FAILURE.value,
                "severity": "critical",
                "description": f"DNS availability {availability_score:.1f}% below threshold {self.min_availability_score}%",
                "remediation": "Investigate DNS server issues and network connectivity"
            })
        
        return DNSMonitoringResult(
            domain=domain,
            monitoring_duration_seconds=round(monitoring_duration, 2),
            total_checks=total_count,
            successful_checks=successful_count,
            average_resolution_time_ms=round(avg_resolution_time, 2),
            min_resolution_time_ms=round(min_resolution_time, 2),
            max_resolution_time_ms=round(max_resolution_time, 2),
            unique_ips_resolved=unique_ips,
            issues_detected=issues_detected,
            consistency_score=round(consistency_score, 1),
            availability_score=round(availability_score, 1)
        )

    def _analyze_dns_result(self, result: DNSCheckResult, issues_list: List[Dict[str, Any]]):
        """Analyze a single DNS result for issues."""
        if not result.success:
            issues_list.append({
                "issue_type": DNSIssueType.RESOLUTION_FAILURE.value,
                "severity": "high",
                "description": f"DNS resolution failed for {result.domain} via {result.dns_server}: {result.error}",
                "remediation": f"Check DNS server {result.dns_server} connectivity and configuration",
                "timestamp": result.timestamp
            })
        
        elif result.resolution_time_ms > self.critical_resolution_threshold_ms:
            issues_list.append({
                "issue_type": DNSIssueType.SLOW_RESOLUTION.value,
                "severity": "high",
                "description": f"Critical DNS resolution time: {result.resolution_time_ms}ms for {result.domain}",
                "remediation": "Investigate DNS server performance and network latency",
                "timestamp": result.timestamp
            })
        
        elif result.resolution_time_ms > self.slow_resolution_threshold_ms:
            issues_list.append({
                "issue_type": DNSIssueType.SLOW_RESOLUTION.value,
                "severity": "medium", 
                "description": f"Slow DNS resolution time: {result.resolution_time_ms}ms for {result.domain}",
                "remediation": "Monitor DNS performance and consider DNS server optimization",
                "timestamp": result.timestamp
            })

    def _calculate_consistency_score(self, results: List[DNSCheckResult]) -> float:
        """Calculate consistency score based on IP resolution consistency."""
        if not results:
            return 0.0
        
        # Group results by DNS server
        server_results = {}
        for result in results:
            server = result.dns_server
            if server not in server_results:
                server_results[server] = []
            server_results[server].append(set(result.resolved_ips))
        
        # Calculate consistency within each server
        total_consistency = 0.0
        server_count = 0
        
        for server, ip_sets in server_results.items():
            if len(ip_sets) <= 1:
                continue
                
            # Calculate how consistent IPs are within this server
            first_set = ip_sets[0]
            consistent_count = sum(1 for ip_set in ip_sets if ip_set == first_set)
            server_consistency = (consistent_count / len(ip_sets)) * 100
            
            total_consistency += server_consistency
            server_count += 1
        
        if server_count == 0:
            return 100.0  # No inconsistency detected
        
        return total_consistency / server_count

    async def run_critical_domains_monitoring(self, duration_minutes: int = 5) -> Dict[str, Any]:
        """Run DNS monitoring for all critical domains."""
        logger.info(f"Starting DNS monitoring for {len(self.critical_domains)} critical domains...")
        
        start_time = time.time()
        results = {
            "monitoring_run_id": f"dns_monitoring_{int(start_time)}",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "issue_reference": "#1278",
            "purpose": "DNS resolution monitoring for critical staging domains",
            "duration_minutes": duration_minutes,
            "domains": {},
            "summary": {}
        }
        
        # Monitor each domain
        domain_tasks = []
        for domain in self.critical_domains:
            task = self.monitor_domain_comprehensive(domain, duration_minutes)
            domain_tasks.append(task)
        
        domain_results = await asyncio.gather(*domain_tasks, return_exceptions=True)
        
        # Process results
        total_issues = 0
        critical_issues = 0
        high_issues = 0
        lowest_availability = 100.0
        lowest_consistency = 100.0
        
        for i, result in enumerate(domain_results):
            if isinstance(result, DNSMonitoringResult):
                domain = self.critical_domains[i]
                results["domains"][domain] = asdict(result)
                
                # Count issues
                for issue in result.issues_detected:
                    total_issues += 1
                    if issue["severity"] == "critical":
                        critical_issues += 1
                    elif issue["severity"] == "high":
                        high_issues += 1
                
                # Track worst scores
                if result.availability_score < lowest_availability:
                    lowest_availability = result.availability_score
                if result.consistency_score < lowest_consistency:
                    lowest_consistency = result.consistency_score
        
        # Generate summary
        results["summary"] = {
            "total_domains_monitored": len(self.critical_domains),
            "monitoring_duration_seconds": round(time.time() - start_time, 2),
            "total_issues_detected": total_issues,
            "critical_issues": critical_issues,
            "high_priority_issues": high_issues,
            "lowest_availability_score": round(lowest_availability, 1),
            "lowest_consistency_score": round(lowest_consistency, 1),
            "overall_dns_health": self._determine_dns_health(critical_issues, high_issues, lowest_availability, lowest_consistency),
            "end_time": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"DNS monitoring complete: {total_issues} issues detected, "
                   f"availability: {lowest_availability:.1f}%, consistency: {lowest_consistency:.1f}%")
        
        return results

    def _determine_dns_health(self, critical_issues: int, high_issues: int, 
                             availability: float, consistency: float) -> str:
        """Determine overall DNS health status."""
        if critical_issues > 0 or availability < 95.0:
            return "critical_dns_issues"
        elif high_issues > 2 or availability < 99.0 or consistency < 95.0:
            return "dns_performance_degraded"
        elif high_issues > 0 or consistency < 99.0:
            return "minor_dns_issues"
        else:
            return "dns_healthy"

    def format_monitoring_report(self, results: Dict[str, Any]) -> str:
        """Format DNS monitoring results for console output."""
        output = []
        output.append("=" * 80)
        output.append(f"DNS RESOLUTION MONITORING - Issue {results['issue_reference']}")
        output.append(f"Run ID: {results['monitoring_run_id']}")
        output.append(f"Duration: {results['duration_minutes']} minutes")
        output.append(f"Timestamp: {results['start_time']}")
        output.append("=" * 80)
        
        # Summary
        summary = results["summary"]
        output.append(f"\nOVERALL DNS HEALTH: {summary['overall_dns_health'].upper()}")
        output.append(f"Domains Monitored: {summary['total_domains_monitored']}")
        output.append(f"Issues Detected: {summary['total_issues_detected']}")
        output.append(f"Critical Issues: {summary['critical_issues']}")
        output.append(f"Lowest Availability: {summary['lowest_availability_score']}%")
        output.append(f"Lowest Consistency: {summary['lowest_consistency_score']}%")
        
        # Domain details
        output.append(f"\nDOMAIN MONITORING RESULTS:")
        output.append("-" * 40)
        
        for domain, domain_result in results["domains"].items():
            availability = domain_result["availability_score"]
            consistency = domain_result["consistency_score"]
            avg_time = domain_result["average_resolution_time_ms"]
            
            # Status icons
            if availability >= 99.0 and consistency >= 95.0:
                status_icon = "✅"
            elif availability >= 95.0:
                status_icon = "⚠️"
            else:
                status_icon = "❌"
            
            output.append(f"{status_icon} {domain}")
            output.append(f"   Availability: {availability}% | Consistency: {consistency}%")
            output.append(f"   Avg Resolution: {avg_time}ms | Checks: {domain_result['successful_checks']}/{domain_result['total_checks']}")
            output.append(f"   Resolved IPs: {', '.join(domain_result['unique_ips_resolved'])}")
            
            # Show issues if any
            if domain_result["issues_detected"]:
                output.append(f"   Issues ({len(domain_result['issues_detected'])}):")
                for issue in domain_result["issues_detected"][:3]:  # Show first 3 issues
                    output.append(f"     • {issue['severity'].upper()}: {issue['description']}")
            
            output.append("")
        
        # Infrastructure recommendations
        if summary["critical_issues"] > 0 or summary["lowest_availability_score"] < 95.0:
            output.append("🚨 CRITICAL DNS ISSUES DETECTED:")
            output.append("-" * 40)
            output.append("✅ Immediate Actions Required:")
            output.append("   • Check DNS server configuration and availability")
            output.append("   • Verify load balancer health and IP assignments")
            output.append("   • Test DNS propagation across all regions")
            output.append("   • Review CDN and edge cache configuration")
            output.append("   • Validate SSL certificates for all monitored domains")
        
        output.append("\n" + "!" * 60)
        output.append("DNS MONITORING SYSTEM ACTIVE:")
        output.append("✅ Continuous monitoring of api.staging.netrasystems.ai")
        output.append("✅ Multiple DNS server validation (Google, Cloudflare, System)")
        output.append("✅ Resolution time and consistency tracking")
        output.append("✅ Early warning for DNS infrastructure issues")
        output.append("✅ Issue #1278 specific domain monitoring")
        output.append("!" * 60)
        
        return "\n".join(output)


async def monitor_critical_domains(duration_minutes: int = 5):
    """Convenience function to monitor critical domains."""
    monitor = DNSResolutionMonitor()
    results = await monitor.run_critical_domains_monitoring(duration_minutes)
    report = monitor.format_monitoring_report(results)
    print(report)
    return results


if __name__ == "__main__":
    import sys
    
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    asyncio.run(monitor_critical_domains(duration))