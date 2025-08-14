#!/usr/bin/env python
"""
Report Generators - Generate test reports in different formats
Contains markdown, JSON, and text report generation functions
"""

import json
from datetime import datetime
from typing import Dict


def status_badge(status) -> str:
    """Convert status to markdown badge."""
    if status == "passed" or status is True:
        return "[PASSED]"
    elif status == "failed" or status is False:
        return "[FAILED]"
    elif status == "timeout":
        return "[TIMEOUT]"
    elif status == "skipped":
        return "[SKIPPED]"
    else:
        return "[PENDING]"


def calculate_total_counts(results: Dict) -> Dict:
    """Calculate total test counts across all components."""
    backend_counts = results["backend"]["test_counts"]
    frontend_counts = results["frontend"]["test_counts"]
    e2e_counts = results.get("e2e", {}).get("test_counts", {
        "total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0
    })
    
    return {
        "total": backend_counts["total"] + frontend_counts["total"] + e2e_counts["total"],
        "passed": backend_counts["passed"] + frontend_counts["passed"] + e2e_counts["passed"],
        "failed": backend_counts["failed"] + frontend_counts["failed"] + e2e_counts["failed"],
        "skipped": backend_counts["skipped"] + frontend_counts["skipped"] + e2e_counts["skipped"],
        "errors": backend_counts["errors"] + frontend_counts["errors"] + e2e_counts["errors"]
    }


def calculate_overall_coverage(results: Dict) -> float:
    """Calculate overall coverage from backend and frontend results."""
    backend_coverage = results["backend"]["coverage"]
    frontend_coverage = results["frontend"]["coverage"]
    
    if backend_coverage is not None and frontend_coverage is not None:
        return (backend_coverage + frontend_coverage) / 2
    elif backend_coverage is not None:
        return backend_coverage
    elif frontend_coverage is not None:
        return frontend_coverage
    else:
        return None


def generate_markdown_report(results: Dict, level: str, config: Dict, exit_code: int) -> str:
    """Generate markdown report following spec structure."""
    total_counts = calculate_total_counts(results)
    overall_coverage = calculate_overall_coverage(results)
    backend_counts = results["backend"]["test_counts"]
    frontend_counts = results["frontend"]["test_counts"]
    e2e_counts = results.get("e2e", {}).get("test_counts", {
        "total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0
    })
    
    overall_passed = (
        results["backend"]["status"] in ["passed", "skipped"] and 
        results["frontend"]["status"] in ["passed", "skipped"]
    )
    
    md_content = f"""# Netra AI Platform - Test Report

**Generated:** {datetime.now().isoformat()}  
**Test Level:** {level} - {config['description']}  
**Purpose:** {config['purpose']}

## Test Summary

**Total Tests:** {total_counts['total']}  
**Passed:** {total_counts['passed']}  
**Failed:** {total_counts['failed']}  
**Skipped:** {total_counts['skipped']}  
**Errors:** {total_counts['errors']}  
**Overall Status:** {status_badge(overall_passed)}

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | {backend_counts['total']} | {backend_counts['passed']} | {backend_counts['failed']} | {backend_counts['skipped']} | {backend_counts['errors']} | {results['backend']['duration']:.2f}s | {status_badge(results['backend']['status'])} |
| Frontend  | {frontend_counts['total']} | {frontend_counts['passed']} | {frontend_counts['failed']} | {frontend_counts['skipped']} | {frontend_counts['errors']} | {results['frontend']['duration']:.2f}s | {status_badge(results['frontend']['status'])} |"""
    
    # Add E2E row if E2E tests were run
    if results.get("e2e", {}).get("status") != "pending":
        md_content += f"""
| E2E       | {e2e_counts['total']} | {e2e_counts['passed']} | {e2e_counts['failed']} | {e2e_counts['skipped']} | {e2e_counts['errors']} | {results['e2e']['duration']:.2f}s | {status_badge(results['e2e']['status'])} |"""
    
    md_content += "\n"
    
    # Add coverage summary if applicable
    if config.get('run_coverage', False) and overall_coverage is not None:
        md_content += f"""
## Coverage Summary

**Overall Coverage:** {overall_coverage:.1f}%
"""
        if results["backend"]["coverage"] is not None:
            md_content += f"**Backend Coverage:** {results['backend']['coverage']:.1f}%  \n"
        if results["frontend"]["coverage"] is not None:
            md_content += f"**Frontend Coverage:** {results['frontend']['coverage']:.1f}%  \n"
    
    md_content += f"""
## Environment and Configuration

- **Test Level:** {level}
- **Description:** {config['description']}
- **Purpose:** {config['purpose']}
- **Timeout:** {config.get('timeout', 300)}s
- **Coverage Enabled:** {'Yes' if config.get('run_coverage', False) else 'No'}
- **Total Duration:** {results['backend']['duration'] + results['frontend']['duration']:.2f}s
- **Exit Code:** {exit_code}

### Backend Configuration
```
{' '.join(config.get('backend_args', []))}
```

### Frontend Configuration
```
{' '.join(config.get('frontend_args', []))}
```

## Test Output

### Backend Output
```
{results['backend']['output'][:10000]}{'...(truncated)' if len(results['backend']['output']) > 10000 else ''}
```

### Frontend Output
```
{results['frontend']['output'][:10000]}{'...(truncated)' if len(results['frontend']['output']) > 10000 else ''}
```"""
    
    # Add E2E output if E2E tests were run
    if results.get("e2e", {}).get("status") != "pending":
        md_content += f"""

### E2E Output
```
{results['e2e']['output'][:10000]}{'...(truncated)' if len(results['e2e']['output']) > 10000 else ''}
```"""
    
    # Add error summary if there were failures
    if total_counts['failed'] > 0 or total_counts['errors'] > 0:
        md_content += """

## Error Summary

"""
        # Extract error details from output
        if backend_counts['failed'] > 0 or backend_counts['errors'] > 0:
            md_content += "### Backend Errors\n"
            # Extract FAILED lines from output
            for line in results['backend']['output'].split('\n'):
                if 'FAILED' in line or 'ERROR' in line:
                    md_content += f"- {line.strip()}\n"
            md_content += "\n"
        
        if frontend_counts['failed'] > 0 or frontend_counts['errors'] > 0:
            md_content += "### Frontend Errors\n"
            for line in results['frontend']['output'].split('\n'):
                if 'FAILED' in line or 'ERROR' in line or 'FAIL' in line:
                    md_content += f"- {line.strip()}\n"
            md_content += "\n"
    
    md_content += """
---
*Generated by Netra AI Unified Test Runner v3.0*
"""
    
    return md_content


def generate_json_report(results: Dict, level: str, config: Dict, exit_code: int, staging_mode: bool = False) -> Dict:
    """Generate JSON report for CI/CD integration."""
    import os
    
    timestamp = datetime.now().isoformat()
    duration = results["overall"]["end_time"] - results["overall"]["start_time"]
    total_counts = calculate_total_counts(results)
    
    backend_counts = results["backend"]["test_counts"]
    frontend_counts = results["frontend"]["test_counts"]
    e2e_counts = results.get("e2e", {}).get("test_counts", {"total": 0, "passed": 0, "failed": 0})
    
    return {
        "timestamp": timestamp,
        "level": level,
        "status": "passed" if exit_code == 0 else "failed",
        "exit_code": exit_code,
        "duration": duration,
        "environment": {
            "staging": staging_mode,
            "staging_url": os.getenv("STAGING_URL", ""),
            "staging_api_url": os.getenv("STAGING_API_URL", ""),
            "pr_number": os.getenv("PR_NUMBER", ""),
            "pr_branch": os.getenv("PR_BRANCH", ""),
        },
        "summary": {
            "total": total_counts["total"],
            "passed": total_counts["passed"],
            "failed": total_counts["failed"],
            "skipped": total_counts["skipped"],
            "errors": total_counts["errors"],
            "duration": duration,
        },
        "components": {
            "backend": {
                "status": results["backend"]["status"],
                "duration": results["backend"]["duration"],
                "tests": backend_counts,
                "coverage": results["backend"]["coverage"],
            },
            "frontend": {
                "status": results["frontend"]["status"],
                "duration": results["frontend"]["duration"],
                "tests": frontend_counts,
                "coverage": results["frontend"]["coverage"],
            },
            "e2e": {
                "status": results.get("e2e", {}).get("status", "skipped"),
                "duration": results.get("e2e", {}).get("duration", 0),
                "tests": e2e_counts,
            }
        },
        "configuration": {
            "level": level,
            "description": config.get("description", ""),
            "purpose": config.get("purpose", ""),
            "timeout": config.get("timeout", 300),
            "coverage_enabled": config.get("run_coverage", False),
        }
    }


def generate_text_report(results: Dict, level: str, config: Dict, exit_code: int, staging_mode: bool = False) -> str:
    """Generate plain text report."""
    import os
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    duration = results["overall"]["end_time"] - results["overall"]["start_time"]
    total_counts = calculate_total_counts(results)
    backend_counts = results["backend"]["test_counts"]
    frontend_counts = results["frontend"]["test_counts"]
    
    report = []
    report.append("=" * 80)
    report.append("NETRA AI PLATFORM - TEST REPORT")
    report.append("=" * 80)
    report.append(f"Timestamp: {timestamp}")
    report.append(f"Test Level: {level}")
    report.append(f"Status: {'PASSED' if exit_code == 0 else 'FAILED'}")
    report.append(f"Duration: {duration:.2f}s")
    
    if staging_mode:
        report.append("\nSTAGING ENVIRONMENT:")
        report.append(f"  Frontend: {os.getenv('STAGING_URL', 'N/A')}")
        report.append(f"  API: {os.getenv('STAGING_API_URL', 'N/A')}")
        report.append(f"  PR Number: {os.getenv('PR_NUMBER', 'N/A')}")
    
    report.append("\nTEST SUMMARY:")
    report.append(f"  Total: {total_counts['total']}")
    report.append(f"  Passed: {total_counts['passed']}")
    report.append(f"  Failed: {total_counts['failed']}")
    
    report.append("\nCOMPONENT RESULTS:")
    report.append(f"  Backend: {results['backend']['status'].upper()}")
    report.append(f"    Tests: {backend_counts['total']} total, {backend_counts['passed']} passed, {backend_counts['failed']} failed")
    if results["backend"]["coverage"]:
        report.append(f"    Coverage: {results['backend']['coverage']:.1f}%")
    
    report.append(f"  Frontend: {results['frontend']['status'].upper()}")
    report.append(f"    Tests: {frontend_counts['total']} total, {frontend_counts['passed']} passed, {frontend_counts['failed']} failed")
    if results["frontend"]["coverage"]:
        report.append(f"    Coverage: {results['frontend']['coverage']:.1f}%")
    
    report.append("=" * 80)
    
    return "\n".join(report)