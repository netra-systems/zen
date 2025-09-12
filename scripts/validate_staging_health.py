#!/usr/bin/env python3
"""
Staging Health Validation Script
Comprehensive health checking for staging environment deployment
"""

import asyncio
import aiohttp
import time
import json
import sys
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import subprocess
import psutil

@dataclass
class HealthCheck:
    name: str
    status: str
    response_time: float
    details: Dict[str, Any]
    critical: bool = False

class StagingHealthValidator:
    """Validates staging environment health after deployment."""
    
    def __init__(self):
        self.services = {
            "backend": "http://localhost:8000",
            "auth": "http://localhost:8081", 
            "frontend": "http://localhost:3000"
        }
        self.databases = {
            "postgres": {"host": "localhost", "port": 5434},
            "redis": {"host": "localhost", "port": 6381},
            "clickhouse": {"host": "localhost", "port": 8125}
        }
        self.results = []
        
    async def check_service_health(self, name: str, url: str) -> HealthCheck:
        """Check individual service health."""
        try:
            start_time = time.time()
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                health_url = f"{url}/health"
                async with session.get(health_url) as response:
                    response_time = time.time() - start_time
                    response_data = await response.text()
                    
                    if response.status == 200:
                        try:
                            details = json.loads(response_data)
                        except:
                            details = {"response": response_data}
                            
                        return HealthCheck(
                            name=name,
                            status="healthy",
                            response_time=response_time,
                            details=details,
                            critical=True
                        )
                    else:
                        return HealthCheck(
                            name=name,
                            status="unhealthy",
                            response_time=response_time,
                            details={
                                "status_code": response.status,
                                "response": response_data
                            },
                            critical=True
                        )
                        
        except Exception as e:
            return HealthCheck(
                name=name,
                status="error",
                response_time=0,
                details={"error": str(e)},
                critical=True
            )
    
    async def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check."""
        print("[U+1F3E5] Starting Comprehensive Staging Health Check")
        print("=" * 60)
        
        self.results = []
        
        # Check service health
        print("\n SEARCH:  Checking Service Health...")
        for name, url in self.services.items():
            print(f"   Checking {name}...")
            result = await self.check_service_health(name, url)
            self.results.append(result)
            print(f"   {name}: {result.status} ({result.response_time:.3f}s)")
        
        return self.generate_summary()
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate health check summary."""
        total_checks = len(self.results)
        healthy_checks = sum(1 for r in self.results if r.status == "healthy")
        critical_failures = sum(1 for r in self.results if r.status in ["unhealthy", "error"] and r.critical)
        
        overall_health = "healthy" if critical_failures == 0 else "unhealthy"
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "overall_health": overall_health,
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "critical_failures": critical_failures,
            "success_rate": (healthy_checks / total_checks) * 100 if total_checks > 0 else 0,
            "details": [
                {
                    "name": r.name,
                    "status": r.status,
                    "response_time": r.response_time,
                    "critical": r.critical,
                    "details": r.details
                }
                for r in self.results
            ]
        }
        
        return summary
    
    def print_summary(self, summary: Dict[str, Any]):
        """Print health check summary."""
        print("\n" + "=" * 60)
        print("STAGING HEALTH CHECK SUMMARY")
        print("=" * 60)
        
        status_icon = " PASS: " if summary["overall_health"] == "healthy" else " FAIL: "
        print(f"{status_icon} Overall Health: {summary['overall_health'].upper()}")
        print(f" CHART:  Success Rate: {summary['success_rate']:.1f}%")
        print(f" PASS:  Healthy Checks: {summary['healthy_checks']}/{summary['total_checks']}")
        print(f" ALERT:  Critical Failures: {summary['critical_failures']}")
        
        if summary["critical_failures"] > 0:
            print(f"\n ALERT:  CRITICAL ISSUES DETECTED:")
            for detail in summary["details"]:
                if detail["status"] in ["unhealthy", "error"] and detail["critical"]:
                    print(f"    FAIL:  {detail['name']}: {detail['status']}")
                    if "error" in detail["details"]:
                        print(f"      Error: {detail['details']['error']}")
        
        print(f"\n[U+1F4C5] Timestamp: {summary['timestamp']}")
        
        return 0 if summary["overall_health"] == "healthy" else 1

async def main():
    """Main entry point."""
    validator = StagingHealthValidator()
    summary = await validator.run_comprehensive_health_check()
    exit_code = validator.print_summary(summary)
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())