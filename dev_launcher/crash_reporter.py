"""
Crash reporting system for dev launcher.

This module handles reporting and persistence of crash reports,
including logging, file storage, and optional external reporting.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

from dev_launcher.crash_recovery_models import CrashReport


logger = logging.getLogger(__name__)


class CrashReporter:
    """
    Handles crash report generation, storage, and optional external reporting.
    
    Provides functionality for:
    - Saving crash reports to disk
    - Formatting reports for different outputs
    - Managing report retention
    """
    
    def __init__(self, report_dir: Optional[str] = None):
        """
        Initialize crash reporter.
        
        Args:
            report_dir: Directory to save crash reports (default: logs/crashes)
        """
        self.logger = logging.getLogger(__name__)
        self.report_dir = Path(report_dir or "dev_launcher/logs/crashes")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
    async def save_report(self, crash_report: CrashReport) -> str:
        """
        Save crash report to disk.
        
        Args:
            crash_report: The crash report to save
            
        Returns:
            Path to the saved report file
        """
        try:
            # Generate filename with timestamp
            timestamp = int(crash_report.crash_time)
            filename = f"crash_report_{crash_report.service_name}_{timestamp}.json"
            file_path = self.report_dir / filename
            
            # Convert crash report to dictionary
            report_data = self._serialize_crash_report(crash_report)
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, default=str)
                
            self.logger.info(f"Crash report saved to: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save crash report for {crash_report.service_name}: {e}")
            return ""
            
    def _serialize_crash_report(self, crash_report: CrashReport) -> dict:
        """Convert crash report to serializable dictionary."""
        return {
            "service_name": crash_report.service_name,
            "severity": crash_report.severity.value,
            "crash_time": crash_report.crash_time,
            "crash_time_readable": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(crash_report.crash_time)),
            "detection_results": [
                {
                    "method": result.method.value,
                    "is_crashed": result.is_crashed,
                    "error_message": result.error_message,
                    "details": result.details,
                    "timestamp": result.timestamp
                }
                for result in crash_report.detection_results
            ],
            "last_logs": crash_report.last_logs,
            "diagnosis": crash_report.diagnosis,
            "recovery_attempts": [
                {
                    "attempt_number": attempt.attempt_number,
                    "stage": attempt.stage.value,
                    "start_time": attempt.start_time,
                    "end_time": attempt.end_time,
                    "duration": attempt.duration,
                    "success": attempt.success,
                    "actions_taken": attempt.actions_taken,
                    "error_message": attempt.error_message,
                    "stage_results": attempt.stage_results
                }
                for attempt in crash_report.recovery_attempts
            ],
            "recovery_successful": crash_report.recovery_successful,
            "total_recovery_time": crash_report.total_recovery_time,
            "total_attempts": crash_report.total_attempts,
            "current_stage": crash_report.current_stage.value if crash_report.current_stage else None,
            "system_state": crash_report.system_state,
            "environment_info": crash_report.environment_info
        }
        
    async def load_report(self, file_path: str) -> Optional[CrashReport]:
        """Load crash report from file (for analysis/debugging)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Basic reconstruction (could be enhanced)
            from dev_launcher.crash_recovery_models import (
                CrashSeverity, DetectionMethod, DetectionResult, RecoveryStage, RecoveryAttempt
            )
            
            crash_report = CrashReport(
                service_name=data["service_name"],
                severity=CrashSeverity(data["severity"]),
                crash_time=data["crash_time"]
            )
            
            # Reconstruct detection results
            for result_data in data.get("detection_results", []):
                result = DetectionResult(
                    method=DetectionMethod(result_data["method"]),
                    is_crashed=result_data["is_crashed"],
                    error_message=result_data["error_message"],
                    details=result_data["details"],
                    timestamp=result_data["timestamp"]
                )
                crash_report.detection_results.append(result)
                
            crash_report.last_logs = data.get("last_logs", [])
            crash_report.diagnosis = data.get("diagnosis", {})
            crash_report.recovery_successful = data.get("recovery_successful", False)
            crash_report.total_recovery_time = data.get("total_recovery_time")
            crash_report.system_state = data.get("system_state", {})
            crash_report.environment_info = data.get("environment_info", {})
            
            return crash_report
            
        except Exception as e:
            self.logger.error(f"Failed to load crash report from {file_path}: {e}")
            return None
            
    def cleanup_old_reports(self, max_age_hours: int = 24):
        """Remove old crash reports."""
        try:
            current_time = time.time()
            cutoff_time = current_time - (max_age_hours * 3600)
            
            removed_count = 0
            for report_file in self.report_dir.glob("crash_report_*.json"):
                if report_file.stat().st_mtime < cutoff_time:
                    report_file.unlink()
                    removed_count += 1
                    
            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} old crash reports")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old crash reports: {e}")
            
    def get_recent_reports(self, service_name: Optional[str] = None, 
                          max_count: int = 10) -> list:
        """Get list of recent crash report files."""
        try:
            pattern = f"crash_report_{service_name}_*.json" if service_name else "crash_report_*.json"
            report_files = list(self.report_dir.glob(pattern))
            
            # Sort by modification time (newest first)
            report_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            return [str(f) for f in report_files[:max_count]]
            
        except Exception as e:
            self.logger.error(f"Failed to get recent reports: {e}")
            return []