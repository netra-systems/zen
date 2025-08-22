#!/usr/bin/env python
"""
Report Manager - Manages saving, archiving, and displaying test reports
Handles file operations and report history management
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict

from test_framework.comprehensive_reporter import ComprehensiveTestReporter
from .report_generators import (
    calculate_total_counts,
    generate_markdown_report,
    status_badge,
)


def save_test_report(results: Dict, level: str, config: Dict, exit_code: int, reports_dir: Path, staging_mode: bool = False):
    """Save test report using comprehensive reporting system."""
    # Use comprehensive reporter as the single source of truth
    comprehensive = ComprehensiveTestReporter(reports_dir)
    comprehensive.generate_comprehensive_report(results=results, level=level, config=config, exit_code=exit_code)
    
    print(f"\n[REPORT] Test results saved to: {reports_dir / 'test_results.json'}")


def print_summary(results: Dict):
    """Print final test summary with test counts."""
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    # Calculate totals
    total_counts = calculate_total_counts(results)
    backend_counts = results["backend"]["test_counts"]
    frontend_counts = results["frontend"]["test_counts"]
    e2e_counts = results.get("e2e", {}).get("test_counts", {
        "total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0
    })
    
    total_duration = (
        results["backend"]["duration"] + 
        results["frontend"]["duration"] + 
        results.get("e2e", {}).get("duration", 0)
    )
    
    overall_passed = (
        results["backend"]["status"] in ["passed", "skipped"] and 
        results["frontend"]["status"] in ["passed", "skipped"] and
        (results.get("e2e", {}).get("status", "skipped") in ["passed", "skipped", "pending"])
    )
    
    # Print test counts
    print(f"Total Tests: {total_counts['total']}")
    print(f"  Passed:    {total_counts['passed']}")
    print(f"  Failed:    {total_counts['failed']}")
    print(f"  Skipped:   {total_counts['skipped']}")
    print(f"  Errors:    {total_counts['errors']}")
    print(f"{'='*60}")
    
    # Print component status
    print(f"Backend:  {status_badge(results['backend']['status'])} ({backend_counts['total']} tests, {results['backend']['duration']:.2f}s)")
    print(f"Frontend: {status_badge(results['frontend']['status'])} ({frontend_counts['total']} tests, {results['frontend']['duration']:.2f}s)")
    if results.get("e2e", {}).get("status") != "pending":
        print(f"E2E:      {status_badge(results['e2e']['status'])} ({e2e_counts['total']} tests, {results['e2e']['duration']:.2f}s)")
    print(f"Overall:  {status_badge(overall_passed)} ({total_duration:.2f}s)")
    
    # Print coverage if available
    if results["backend"]["coverage"] is not None or results["frontend"]["coverage"] is not None:
        print(f"{'='*60}")
        print("COVERAGE:")
        if results["backend"]["coverage"] is not None:
            print(f"  Backend:  {results['backend']['coverage']:.1f}%")
        if results["frontend"]["coverage"] is not None:
            print(f"  Frontend: {results['frontend']['coverage']:.1f}%")
    
    print(f"{'='*60}")


def cleanup_old_reports(reports_dir: Path, keep_days: int = 30):
    """Clean up old reports in the history directory."""
    history_dir = reports_dir / "history"
    if not history_dir.exists():
        return
    
    cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
    
    for report_file in history_dir.glob("*.md"):
        if report_file.stat().st_mtime < cutoff_time:
            report_file.unlink()
            print(f"[CLEANUP] Removed old report: {report_file.name}")


def list_available_reports(reports_dir: Path) -> Dict[str, list]:
    """List all available reports."""
    reports = {
        "latest": [],
        "history": []
    }
    
    # Find latest reports
    for report_file in reports_dir.glob("latest_*.md"):
        reports["latest"].append({
            "file": report_file.name,
            "level": report_file.name.replace("latest_", "").replace("_report.md", ""),
            "modified": datetime.fromtimestamp(report_file.stat().st_mtime)
        })
    
    # Find history reports
    history_dir = reports_dir / "history"
    if history_dir.exists():
        for report_file in history_dir.glob("*.md"):
            reports["history"].append({
                "file": report_file.name,
                "modified": datetime.fromtimestamp(report_file.stat().st_mtime)
            })
    
    # Sort by modification time
    reports["latest"].sort(key=lambda x: x["modified"], reverse=True)
    reports["history"].sort(key=lambda x: x["modified"], reverse=True)
    
    return reports


def get_report_metrics(reports_dir: Path) -> Dict:
    """Get metrics about test reports."""
    reports = list_available_reports(reports_dir)
    
    return {
        "latest_count": len(reports["latest"]),
        "history_count": len(reports["history"]),
        "total_reports": len(reports["latest"]) + len(reports["history"]),
        "last_run": reports["latest"][0]["modified"] if reports["latest"] else None
    }


class ReportArchiver:
    """Manages archiving and organizing test reports."""
    
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.history_dir = reports_dir / "history"
        self.history_dir.mkdir(exist_ok=True)
    
    def get_archived_reports(self, level: str = None) -> list:
        """Get list of archived reports, optionally filtered by level."""
        archived = []
        
        for report_file in self.history_dir.glob("*.md"):
            if level and f"_{level}_" not in report_file.name:
                continue
            
            archived.append({
                "path": report_file,
                "name": report_file.name,
                "modified": datetime.fromtimestamp(report_file.stat().st_mtime),
                "size": report_file.stat().st_size
            })
        
        return sorted(archived, key=lambda x: x["modified"], reverse=True)
    
    def purge_old_archives(self, keep_days: int = 30) -> int:
        """Remove archived reports older than specified days."""
        cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
        purged_count = 0
        
        for report_file in self.history_dir.glob("*.md"):
            if report_file.stat().st_mtime < cutoff_time:
                report_file.unlink()
                purged_count += 1
        
        return purged_count