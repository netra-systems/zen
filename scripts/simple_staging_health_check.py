#!/usr/bin/env python3
"""
Simple GCP Staging Health Check
Quick HTTP-based health check to identify critical staging issues
without requiring Google Cloud SDK dependencies.
"""

import requests
import json
import time
from datetime import datetime
from urllib.parse import urljoin


class SimpleStagingHealthCheck:
    def __init__(self):
        self.services = {
            "auth": {
                "name": "Auth Service",
                "base_url": "https://netra-auth-service-701982941522.us-central1.run.app",
                "critical_endpoints": ["/health", "/auth/health"]
            },
            "backend": {
                "name": "Backend Service", 
                "base_url": "https://netra-backend-staging-701982941522.us-central1.run.app",
                "critical_endpoints": ["/health", "/health/ready", "/health/database"]
            },
            "frontend": {
                "name": "Frontend Service",
                "base_url": "https://netra-frontend-staging-701982941522.us-central1.run.app",
                "critical_endpoints": ["/", "/api/health"]
            }
        }
        self.issues = []
        
    def check_service_health(self, service_key, service_config):
        """Check health of a single service"""
        service_name = service_config["name"]
        base_url = service_config["base_url"]
        endpoints = service_config["critical_endpoints"]
        
        print(f"\n--- Checking {service_name} ---")
        service_issues = []
        
        for endpoint in endpoints:
            url = urljoin(base_url, endpoint)
            print(f"Testing: {url}")
            
            try:
                start_time = time.time()
                response = requests.get(url, timeout=10)
                response_time = time.time() - start_time
                
                print(f"  Status: {response.status_code} ({response_time:.2f}s)")
                
                if response.status_code >= 500:
                    issue = {
                        "severity": "CRITICAL",
                        "service": service_name,
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "response_time": response_time,
                        "error": f"HTTP {response.status_code} Server Error",
                        "content_preview": response.text[:200] if response.text else ""
                    }
                    service_issues.append(issue)
                    print(f"     ALERT:  CRITICAL: HTTP {response.status_code}")
                    
                elif response.status_code == 404:
                    issue = {
                        "severity": "HIGH",
                        "service": service_name,
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "response_time": response_time,
                        "error": "Endpoint not found (404)",
                        "content_preview": response.text[:200] if response.text else ""
                    }
                    service_issues.append(issue)
                    print(f"     WARNING: [U+FE0F]  HIGH: Endpoint not found")
                    
                elif response_time > 5:
                    issue = {
                        "severity": "MEDIUM",
                        "service": service_name,
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "response_time": response_time,
                        "error": f"Slow response ({response_time:.2f}s)",
                        "content_preview": response.text[:200] if response.text else ""
                    }
                    service_issues.append(issue)
                    print(f"     WARNING: [U+FE0F]  MEDIUM: Slow response")
                    
                elif response.status_code == 200:
                    print(f"     PASS:  OK")
                    
            except requests.exceptions.Timeout:
                issue = {
                    "severity": "CRITICAL",
                    "service": service_name,
                    "endpoint": endpoint,
                    "status_code": None,
                    "response_time": 10.0,
                    "error": "Request timeout (10s)",
                    "content_preview": ""
                }
                service_issues.append(issue)
                print(f"     ALERT:  CRITICAL: Timeout")
                
            except requests.exceptions.ConnectionError:
                issue = {
                    "severity": "CRITICAL",
                    "service": service_name,
                    "endpoint": endpoint,
                    "status_code": None,
                    "response_time": None,
                    "error": "Connection failed",
                    "content_preview": ""
                }
                service_issues.append(issue)
                print(f"     ALERT:  CRITICAL: Connection failed")
                
            except Exception as e:
                issue = {
                    "severity": "HIGH", 
                    "service": service_name,
                    "endpoint": endpoint,
                    "status_code": None,
                    "response_time": None,
                    "error": f"Unexpected error: {str(e)}",
                    "content_preview": ""
                }
                service_issues.append(issue)
                print(f"     WARNING: [U+FE0F]  HIGH: {str(e)}")
                
        return service_issues
    
    def run_health_check(self):
        """Run comprehensive health check"""
        print("=== GCP Staging Health Check ===")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        all_issues = []
        
        for service_key, service_config in self.services.items():
            service_issues = self.check_service_health(service_key, service_config)
            all_issues.extend(service_issues)
            
        return self.analyze_issues(all_issues)
    
    def analyze_issues(self, all_issues):
        """Analyze and prioritize issues"""
        print(f"\n=== ISSUE ANALYSIS ===")
        
        if not all_issues:
            print(" PASS:  No critical issues detected!")
            return {"status": "healthy", "issues": []}
            
        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        sorted_issues = sorted(all_issues, key=lambda x: severity_order.get(x["severity"], 4))
        
        print(f"Total issues found: {len(all_issues)}")
        
        # Count by severity
        severity_counts = {}
        for issue in all_issues:
            severity = issue["severity"]
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
        for severity, count in severity_counts.items():
            print(f"  {severity}: {count}")
            
        # Identify most critical issue
        most_critical = sorted_issues[0]
        print(f"\n FIRE:  MOST CRITICAL ISSUE:")
        print(f"  Service: {most_critical['service']}")
        print(f"  Endpoint: {most_critical['endpoint']}")
        print(f"  Error: {most_critical['error']}")
        print(f"  Severity: {most_critical['severity']}")
        
        if most_critical.get("content_preview"):
            print(f"  Response preview: {most_critical['content_preview']}")
            
        return {
            "status": "issues_detected",
            "most_critical": most_critical,
            "all_issues": sorted_issues,
            "summary": {
                "total_issues": len(all_issues),
                "by_severity": severity_counts
            }
        }


def main():
    checker = SimpleStagingHealthCheck()
    results = checker.run_health_check()
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"staging_health_check_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
        
    print(f"\n[U+1F4C4] Results saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    main()