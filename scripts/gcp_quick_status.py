#!/usr/bin/env python3
"""
Quick GCP Health Status Check

Business Value: Provides instant health status check for all GCP services.
Used for rapid status verification during deployments and troubleshooting.
"""

import asyncio
import time
from datetime import datetime

import aiohttp
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

async def quick_health_check():
    """Perform quick health check on all services."""
    services = [
        {
            "name": "Auth Service",
            "url": "https://netra-auth-service-701982941522.us-central1.run.app/health"
        },
        {
            "name": "Backend Service", 
            "url": "https://netra-backend-staging-701982941522.us-central1.run.app/health"
        },
        {
            "name": "Frontend Service",
            "url": "https://netra-frontend-staging-701982941522.us-central1.run.app/"
        }
    ]
    
    print(f"{Fore.CYAN}=== Quick GCP Health Status ==={Style.RESET_ALL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        results = []
        for service in services:
            start_time = time.time()
            try:
                async with session.get(service["url"], timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response_time = time.time() - start_time
                    
                    # Special handling for frontend
                    if "frontend" in service["name"].lower():
                        content = await response.text()
                        if response.status == 200 and "404" not in content:
                            status = "HEALTHY"
                            color = Fore.GREEN
                            icon = "[OK]"
                        else:
                            status = "DEGRADED"
                            color = Fore.YELLOW  
                            icon = "[WARN]"
                    else:
                        if response.status == 200:
                            status = "HEALTHY"
                            color = Fore.GREEN
                            icon = "[OK]"
                        else:
                            status = "CRITICAL"
                            color = Fore.RED
                            icon = "[FAIL]"
                    
                    results.append({
                        "name": service["name"],
                        "status": status,
                        "response_time": response_time,
                        "status_code": response.status
                    })
                    
                    print(f"{color}{icon} {service['name']:<20} - {status} ({response.status}, {response_time:.2f}s){Style.RESET_ALL}")
                    
            except Exception as e:
                results.append({
                    "name": service["name"],
                    "status": "CRITICAL",
                    "error": str(e)
                })
                print(f"{Fore.RED}[FAIL] {service['name']:<20} - CRITICAL ({str(e)}){Style.RESET_ALL}")
    
    # Summary
    healthy = len([r for r in results if r["status"] == "HEALTHY"])
    total = len(results)
    
    print("\n" + "=" * 50)
    if healthy == total:
        print(f"{Fore.GREEN}Overall Status: ALL SYSTEMS HEALTHY ({healthy}/{total}){Style.RESET_ALL}")
    elif healthy > 0:
        print(f"{Fore.YELLOW}Overall Status: PARTIAL HEALTH ({healthy}/{total}){Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Overall Status: SYSTEM CRITICAL ({healthy}/{total}){Style.RESET_ALL}")

if __name__ == "__main__":
    asyncio.run(quick_health_check())