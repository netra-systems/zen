#!/usr/bin/env python3
"""
Automated Load Balancer Compliance Validation Script
===================================================

CRITICAL AUTOMATION: Prevents regression to direct Cloud Run URLs
Business Value: Platform/Internal - Deployment Resilience

This script is designed to be run in CI/CD pipelines to ensure that no
direct Cloud Run URLs are introduced into the codebase, which would cause
staging deployment failures and break the entire development workflow.

USAGE:
  python scripts/validate_load_balancer_compliance.py
  
EXIT CODES:
  0 - All compliance checks pass
  1 - Compliance violations detected 
  2 - Script execution error

CLAUDE.md COMPLIANCE:
- SSOT enforcement for load balancer endpoints
- Zero tolerance for direct Cloud Run URLs
- Atomic validation with immediate feedback
- CI/CD pipeline integration ready
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from tests.mission_critical.test_load_balancer_endpoint_compliance import (
    LoadBalancerComplianceValidator,
    LoadBalancerConnectivityValidator
)


class ComplianceReportGenerator:
    """Generates comprehensive compliance reports for CI/CD and monitoring"""
    
    def __init__(self):
        self.report_dir = project_root / "reports" / "compliance"
        self.report_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_json_report(self, 
                           compliance_results: Dict,
                           connectivity_results: Dict,
                           violations: List) -> Path:
        """Generate machine-readable JSON compliance report"""
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "compliance_check": {
                "status": "PASS" if compliance_results['is_compliant'] else "FAIL",
                "scanned_files": compliance_results['scanned_files'],
                "violation_files": compliance_results['violation_files'],
                "total_violations": compliance_results['total_violations'],
                "violations": [
                    {
                        "file": v.file_path,
                        "line": v.line_number,
                        "url": v.violation_text,
                        "type": v.violation_type,
                        "severity": v.severity
                    } for v in violations
                ]
            },
            "connectivity_check": {
                "status": "PASS" if connectivity_results.get('all_accessible', False) else "PARTIAL",
                "total_services": connectivity_results['total_services'],
                "accessible_services": connectivity_results['accessible_services'],
                "accessibility_rate": connectivity_results['accessibility_rate'],
                "service_results": connectivity_results['results']
            },
            "required_urls": {
                "backend": "https://api.staging.netrasystems.ai",
                "auth": "https://auth.staging.netrasystems.ai", 
                "frontend": "https://app.staging.netrasystems.ai",
                "websocket": "wss://api.staging.netrasystems.ai/ws"
            },
            "overall_status": "PASS" if compliance_results['is_compliant'] else "FAIL"
        }
        
        report_file = self.report_dir / f"load_balancer_compliance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"JSON compliance report saved: {report_file}")
        return report_file
    
    def generate_markdown_report(self,
                               compliance_results: Dict,
                               connectivity_results: Dict,
                               violations: List) -> Path:
        """Generate human-readable markdown compliance report"""
        
        report_lines = []
        report_lines.append("# Load Balancer Endpoint Compliance Report")
        report_lines.append("")
        report_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Compliance Status
        status_emoji = " PASS: " if compliance_results['is_compliant'] else " FAIL: "
        report_lines.append(f"## Overall Status: {status_emoji} {'COMPLIANT' if compliance_results['is_compliant'] else 'NON-COMPLIANT'}")
        report_lines.append("")
        
        # Executive Summary
        report_lines.append("## Executive Summary")
        report_lines.append("")
        report_lines.append(f"- **Files Scanned:** {compliance_results['scanned_files']}")
        report_lines.append(f"- **Files with Violations:** {compliance_results['violation_files']}")
        report_lines.append(f"- **Total Violations:** {compliance_results['total_violations']}")
        report_lines.append("")
        
        # Required URLs
        report_lines.append("## Required Load Balancer URLs")
        report_lines.append("")
        report_lines.append("| Service | URL |")
        report_lines.append("|---------|-----|")
        report_lines.append("| Backend | https://api.staging.netrasystems.ai |")
        report_lines.append("| Auth | https://auth.staging.netrasystems.ai |")
        report_lines.append("| Frontend | https://app.staging.netrasystems.ai |") 
        report_lines.append("| WebSocket | wss://api.staging.netrasystems.ai/ws |")
        report_lines.append("")
        
        # Violations Details
        if violations:
            report_lines.append("##  FAIL:  Violations Found")
            report_lines.append("")
            report_lines.append("| File | Line | Violation | Severity |")
            report_lines.append("|------|------|-----------|----------|")
            
            for violation in violations:
                report_lines.append(f"| {violation.file_path} | {violation.line_number} | `{violation.violation_text}` | {violation.severity} |")
            
            report_lines.append("")
            report_lines.append("### [U+1F527] Remediation")
            report_lines.append("")
            report_lines.append("Run the migration script to fix violations:")
            report_lines.append("```bash")
            report_lines.append("python scripts/migrate_cloud_run_urls.py --execute")
            report_lines.append("```")
        else:
            report_lines.append("##  PASS:  No Violations Found")
            report_lines.append("")
            report_lines.append("All endpoints are correctly using load balancer URLs.")
        
        report_lines.append("")
        
        # Connectivity Results
        report_lines.append("## Connectivity Status")
        report_lines.append("")
        report_lines.append("| Service | URL | Status | Response Time |")
        report_lines.append("|---------|-----|--------|---------------|")
        
        for service, result in connectivity_results['results'].items():
            status_emoji = " PASS: " if result['accessible'] else " FAIL: "
            response_time = f"{result.get('response_time', 0):.0f}ms" if result.get('response_time') else "N/A"
            report_lines.append(f"| {service.title()} | {result['url']} | {status_emoji} | {response_time} |")
        
        report_lines.append("")
        
        # Footer
        report_lines.append("---")
        report_lines.append("")
        report_lines.append("*This report was generated automatically by the load balancer compliance validation system.*")
        
        report_content = "\n".join(report_lines)
        
        report_file = self.report_dir / f"load_balancer_compliance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        logger.info(f"Markdown compliance report saved: {report_file}")
        return report_file


async def main():
    """Main validation function"""
    logger.info(" SEARCH:  Starting Load Balancer Endpoint Compliance Validation...")
    logger.info("=" * 60)
    
    exit_code = 0
    
    try:
        # Step 1: Codebase Compliance Scan
        logger.info("[U+1F4C1] Scanning codebase for Cloud Run URL violations...")
        compliance_validator = LoadBalancerComplianceValidator()
        compliance_results = compliance_validator.scan_codebase()
        
        if compliance_results['is_compliant']:
            logger.info(" PASS:  Codebase compliance: PASSED")
        else:
            logger.error(" FAIL:  Codebase compliance: FAILED")
            logger.error(f"Found {compliance_results['total_violations']} violations in {compliance_results['violation_files']} files")
            exit_code = 1
        
        # Step 2: Connectivity Test
        logger.info("[U+1F310] Testing load balancer endpoint connectivity...")
        connectivity_validator = LoadBalancerConnectivityValidator()
        connectivity_results = await connectivity_validator.test_load_balancer_connectivity()
        
        if connectivity_results['all_accessible']:
            logger.info(" PASS:  Connectivity test: PASSED")
        else:
            logger.warning(f" WARNING: [U+FE0F]  Connectivity test: PARTIAL ({connectivity_results['accessible_services']}/{connectivity_results['total_services']} accessible)")
            # Don't fail on connectivity issues as they may be environment-specific
        
        # Step 3: Generate Reports
        logger.info(" CHART:  Generating compliance reports...")
        report_generator = ComplianceReportGenerator()
        
        json_report = report_generator.generate_json_report(
            compliance_results, 
            connectivity_results,
            compliance_validator.violations
        )
        
        markdown_report = report_generator.generate_markdown_report(
            compliance_results,
            connectivity_results, 
            compliance_validator.violations
        )
        
        # Step 4: Summary
        logger.info("=" * 60)
        logger.info("[U+1F4CB] COMPLIANCE VALIDATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Files Scanned: {compliance_results['scanned_files']}")
        logger.info(f"Violations Found: {compliance_results['total_violations']}")
        logger.info(f"Services Tested: {connectivity_results['total_services']}")
        logger.info(f"Services Accessible: {connectivity_results['accessible_services']}")
        logger.info(f"JSON Report: {json_report}")
        logger.info(f"Markdown Report: {markdown_report}")
        
        if exit_code == 0:
            logger.info(" CELEBRATION:  VALIDATION PASSED: Load balancer compliance verified!")
        else:
            logger.error("[U+1F4A5] VALIDATION FAILED: Compliance violations detected!")
            logger.error("Run migration script: python scripts/migrate_cloud_run_urls.py --execute")
    
    except Exception as e:
        logger.error(f"[U+1F4A5] Script execution error: {e}")
        exit_code = 2
    
    logger.info("=" * 60)
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())