"""
Crash Reporter for generating and saving detailed crash reports.

Generates actionable crash reports with:
- Detailed crash analysis and diagnosis
- Recovery attempt history
- Actionable suggestions for resolution
- Structured JSON reports saved to .netra/crash_reports/

ARCHITECTURE COMPLIANCE:
- File size: ≤300 lines (currently under limit)
- Function size: ≤8 lines each (MANDATORY)
- Strong typing throughout
- Async patterns for all I/O operations
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .crash_recovery_models import CrashReport, CrashSeverity, DetectionMethod

logger = logging.getLogger(__name__)


class CrashReporter:
    """Generates and saves crash reports with actionable suggestions."""
    
    def __init__(self, reports_dir: Path = Path(".netra/crash_reports")):
        """Initialize crash reporter with reports directory."""
        self.reports_dir = reports_dir
        self._ensure_reports_directory()
    
    def _ensure_reports_directory(self):
        """Create reports directory if it doesn't exist."""
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Crash reports directory: {self.reports_dir}")
    
    async def generate_suggestions(self, report: CrashReport) -> List[str]:
        """Generate actionable suggestions based on crash analysis."""
        suggestions = []
        
        # Add detection-specific suggestions
        suggestions.extend(self._get_detection_suggestions(report))
        
        # Add diagnosis-specific suggestions
        suggestions.extend(self._get_diagnosis_suggestions(report))
        
        # Add recovery-specific suggestions
        suggestions.extend(self._get_recovery_suggestions(report))
        
        # Add general suggestions if no specific ones found
        if not suggestions:
            suggestions.extend(self._get_general_suggestions())
        
        return suggestions
    
    def _get_detection_suggestions(self, report: CrashReport) -> List[str]:
        """Get suggestions based on detection methods that found crashes."""
        suggestions = []
        
        crashed_methods = [r.method for r in report.detection_results if r.is_crashed]
        
        if DetectionMethod.PROCESS_MONITORING in crashed_methods:
            suggestions.append("Process crashed - check for resource exhaustion or unhandled exceptions")
        
        if DetectionMethod.HEALTH_ENDPOINT in crashed_methods:
            suggestions.append("Health endpoint failing - verify service startup and network connectivity")
        
        if DetectionMethod.LOG_ANALYSIS in crashed_methods:
            suggestions.append("Fatal errors in logs - review application logs for specific error patterns")
        
        return suggestions
    
    def _get_diagnosis_suggestions(self, report: CrashReport) -> List[str]:
        """Get suggestions based on system diagnosis results."""
        suggestions = []
        diagnosis = report.diagnosis
        
        if diagnosis.port_conflicts:
            suggestions.append(
                f"Port conflicts on {diagnosis.port_conflicts} - kill competing processes or change ports"
            )
        
        if diagnosis.memory_issues:
            suggestions.append("Memory issues detected - increase available memory or reduce usage")
        
        if diagnosis.zombie_processes:
            suggestions.append(f"Zombie processes found: {diagnosis.zombie_processes} - system cleanup needed")
        
        if diagnosis.config_issues:
            suggestions.append(f"Configuration errors: {diagnosis.config_issues}")
        
        return suggestions
    
    def _get_recovery_suggestions(self, report: CrashReport) -> List[str]:
        """Get suggestions based on recovery attempt outcomes."""
        suggestions = []
        
        if not report.recovery_attempts:
            suggestions.append("No recovery attempts made - try manual service restart")
            return suggestions
        
        failed_attempts = [a for a in report.recovery_attempts if not a.success]
        if len(failed_attempts) == len(report.recovery_attempts):
            suggestions.append("All recovery attempts failed - manual intervention required")
            suggestions.append("Consider checking service dependencies and system resources")
        
        successful_attempts = [a for a in report.recovery_attempts if a.success]
        if successful_attempts and not report.resolved:
            suggestions.append("Recovery actions completed but service still unstable")
        
        return suggestions
    
    def _get_general_suggestions(self) -> List[str]:
        """Get general troubleshooting suggestions."""
        return [
            "Check service logs for detailed error information",
            "Verify system resources (CPU, memory, disk space)",
            "Ensure all dependencies are running and accessible",
            "Review recent configuration changes",
            "Consider restarting the development environment"
        ]
    
    async def assess_crash_severity(self, report: CrashReport) -> CrashSeverity:
        """Assess crash severity based on multiple factors."""
        severity_score = 0
        
        # Score based on detection methods
        severity_score += len([r for r in report.detection_results if r.is_crashed])
        
        # Score based on diagnosis issues
        if report.diagnosis.memory_issues:
            severity_score += 2
        severity_score += len(report.diagnosis.port_conflicts)
        severity_score += len(report.diagnosis.config_issues)
        
        # Score based on recovery failures
        failed_recoveries = len([a for a in report.recovery_attempts if not a.success])
        severity_score += failed_recoveries
        
        return self._score_to_severity(severity_score)
    
    def _score_to_severity(self, score: int) -> CrashSeverity:
        """Convert severity score to enum value."""
        if score >= 6:
            return CrashSeverity.CRITICAL
        elif score >= 4:
            return CrashSeverity.HIGH
        elif score >= 2:
            return CrashSeverity.MEDIUM
        else:
            return CrashSeverity.LOW
    
    async def save_report(self, report: CrashReport) -> Path:
        """Save crash report to disk with suggestions."""
        # Update severity and suggestions
        report.severity = await self.assess_crash_severity(report)
        report.suggestions = await self.generate_suggestions(report)
        
        # Generate filename
        filename = self._generate_filename(report)
        file_path = self.reports_dir / filename
        
        # Save report as JSON
        await self._write_report_file(file_path, report)
        
        logger.info(f"Crash report saved: {file_path}")
        return file_path
    
    def _generate_filename(self, report: CrashReport) -> str:
        """Generate unique filename for crash report."""
        timestamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
        return f"{report.service_name}_{report.crash_id}_{timestamp}.json"
    
    async def _write_report_file(self, file_path: Path, report: CrashReport):
        """Write crash report to JSON file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report.model_dump(), f, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save crash report to {file_path}: {e}")
            raise
    
    async def load_report(self, file_path: Path) -> CrashReport:
        """Load crash report from disk."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return CrashReport(**data)
        except Exception as e:
            logger.error(f"Failed to load crash report from {file_path}: {e}")
            raise
    
    async def list_reports(self, service_name: str = None) -> List[Path]:
        """List all crash reports, optionally filtered by service."""
        pattern = f"{service_name}_*.json" if service_name else "*.json"
        return list(self.reports_dir.glob(pattern))
    
    async def get_crash_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get summary of crashes in the last N days."""
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_reports = []
        
        for report_file in await self.list_reports():
            try:
                report = await self.load_report(report_file)
                if report.timestamp >= cutoff_date:
                    recent_reports.append(report)
            except Exception:
                continue
        
        return self._build_crash_summary(recent_reports, days)
    
    def _build_crash_summary(self, reports: List[CrashReport], days: int) -> Dict[str, Any]:
        """Build summary statistics from crash reports."""
        total_crashes = len(reports)
        resolved_crashes = len([r for r in reports if r.resolved])
        services_affected = len(set(r.service_name for r in reports))
        
        severity_counts = {}
        for severity in CrashSeverity:
            severity_counts[severity.value] = len([r for r in reports if r.severity == severity])
        
        return {
            "period_days": days,
            "total_crashes": total_crashes,
            "resolved_crashes": resolved_crashes,
            "unresolved_crashes": total_crashes - resolved_crashes,
            "services_affected": services_affected,
            "severity_breakdown": severity_counts,
            "resolution_rate": (resolved_crashes / total_crashes * 100) if total_crashes > 0 else 0
        }
    
    async def cleanup_old_reports(self, days: int = 30):
        """Clean up crash reports older than specified days."""
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        for report_file in await self.list_reports():
            try:
                if report_file.stat().st_mtime < cutoff_date.timestamp():
                    report_file.unlink()
                    cleaned_count += 1
            except Exception as e:
                logger.warning(f"Failed to cleanup report {report_file}: {e}")
        
        logger.info(f"Cleaned up {cleaned_count} old crash reports")
        return cleaned_count