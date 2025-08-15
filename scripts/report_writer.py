#!/usr/bin/env python
"""
Report Writer for Enhanced Test Reporter
Handles file operations and persistence with 8-line function limit
"""

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

from .report_types import ReportDirectoriesExtended, HistoricalData


class ReportDirectoryManager:
    """Manages report directory structure"""
    
    def __init__(self, reports_dir: Path):
        self.directories = self._create_directory_structure(reports_dir)
        self._ensure_directories_exist()
    
    def _create_directory_structure(self, reports_dir: Path) -> ReportDirectoriesExtended:
        """Create directory structure object"""
        return ReportDirectoriesExtended(
            reports_dir=reports_dir,
            latest_dir=reports_dir / "latest",
            history_dir=reports_dir / "history",
            metrics_dir=reports_dir / "metrics",
            analysis_dir=reports_dir / "analysis"
        )
    
    def _ensure_directories_exist(self) -> None:
        """Ensure all directories exist"""
        self.directories.reports_dir.mkdir(exist_ok=True)
        self.directories.latest_dir.mkdir(exist_ok=True)
        self.directories.history_dir.mkdir(exist_ok=True)
        self.directories.metrics_dir.mkdir(exist_ok=True)
        self.directories.analysis_dir.mkdir(exist_ok=True)
    
    def get_latest_report_path(self, level: str) -> Path:
        """Get path for latest report file"""
        return self.directories.latest_dir / f"{level}_report.md"
    
    def get_metrics_path(self, level: str) -> Path:
        """Get path for metrics file"""
        return self.directories.metrics_dir / f"{level}_metrics.json"
    
    def get_history_path(self) -> Path:
        """Get path for historical data file"""
        return self.directories.metrics_dir / "test_history.json"


class ReportFileWriter:
    """Writes report files to disk"""
    
    def __init__(self, directory_manager: ReportDirectoryManager):
        self.dir_manager = directory_manager
    
    def write_latest_report(self, level: str, content: str) -> Path:
        """Write latest report to disk"""
        file_path = self.dir_manager.get_latest_report_path(level)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    
    def write_metrics_json(self, level: str, metrics_data: Dict) -> Path:
        """Write metrics JSON to disk"""
        file_path = self.dir_manager.get_metrics_path(level)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(metrics_data, f, indent=2, default=str)
        return file_path
    
    def write_historical_data(self, historical_data: HistoricalData) -> Path:
        """Write historical data to disk"""
        file_path = self.dir_manager.get_history_path()
        converted_data = self._convert_for_json(historical_data)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, indent=2, default=str)
        return file_path
    
    def _convert_for_json(self, data: HistoricalData) -> Dict:
        """Convert defaultdict to regular dict for JSON"""
        return {
            "runs": data["runs"],
            "flaky_tests": dict(data.get("flaky_tests", {})),
            "failure_patterns": dict(data.get("failure_patterns", {})),
            "performance_trends": data.get("performance_trends", [])
        }


class HistoricalDataUpdater:
    """Updates historical test data"""
    
    def __init__(self, file_writer: ReportFileWriter):
        self.file_writer = file_writer
    
    def update_historical_runs(self, historical_data: HistoricalData, 
                              level: str, metrics: Dict, results: Dict) -> None:
        """Update historical runs with new data"""
        new_run = self._create_run_record(level, metrics, results)
        historical_data['runs'].append(new_run)
        self._trim_historical_runs(historical_data)
    
    def _create_run_record(self, level: str, metrics: Dict, results: Dict) -> Dict:
        """Create historical run record"""
        return {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "total": metrics.get('total_tests', 0),
            "passed": metrics.get('passed', 0),
            "failed": metrics.get('failed', 0),
            "coverage": metrics.get('coverage'),
            "duration": results.get('duration', 0)
        }
    
    def _trim_historical_runs(self, historical_data: HistoricalData) -> None:
        """Keep only last 100 runs"""
        if len(historical_data['runs']) > 100:
            historical_data['runs'] = historical_data['runs'][-100:]


class ReportCleanupManager:
    """Manages cleanup of old reports"""
    
    def __init__(self, directory_manager: ReportDirectoryManager):
        self.dir_manager = directory_manager
    
    def cleanup_old_reports(self, keep_days: int = 30) -> None:
        """Clean up old reports and organize directory"""
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        self._clean_history_files(cutoff_date)
        self._move_misplaced_files()
        self._delete_old_json_files()
        self._print_cleanup_complete()
    
    def _clean_history_files(self, cutoff_date: datetime) -> None:
        """Clean up old history files"""
        for file in self.dir_manager.directories.history_dir.glob("*.md"):
            if self._is_file_old(file, cutoff_date):
                file.unlink()
                self._print_deleted(file.name)
    
    def _move_misplaced_files(self) -> None:
        """Move misplaced files to history directory"""
        for file in self.dir_manager.directories.reports_dir.glob("test_report_*.md"):
            archive_path = self.dir_manager.directories.history_dir / file.name
            shutil.move(str(file), str(archive_path))
            self._print_archived(file.name)
    
    def _delete_old_json_files(self) -> None:
        """Delete old JSON files from root directory"""
        for file in self.dir_manager.directories.reports_dir.glob("test_report_*.json"):
            file.unlink()
            self._print_deleted_json(file.name)
    
    def _is_file_old(self, file: Path, cutoff_date: datetime) -> bool:
        """Check if file is older than cutoff date"""
        try:
            timestamp_str = file.stem.split('_')[-2] + '_' + file.stem.split('_')[-1]
            file_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            return file_date < cutoff_date
        except:
            return False


class UnifiedReporterIntegration:
    """Integrates with unified reporter system"""
    
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.unified_reporter = self._try_import_unified_reporter()
    
    def _try_import_unified_reporter(self):
        """Try to import unified reporter"""
        try:
            from test_framework.unified_reporter import UnifiedReporter
            return UnifiedReporter
        except ImportError:
            return None
    
    def generate_unified_report(self, results: Dict, level: str, exit_code: int) -> None:
        """Generate unified report if available"""
        if not self.unified_reporter:
            return
        
        try:
            unified = self.unified_reporter(self.reports_dir)
            unified_results = self._convert_results_format(results)
            unified.generate_unified_report(unified_results, level, exit_code)
        except Exception as e:
            self._print_unified_warning(str(e))
    
    def _convert_results_format(self, results: Dict) -> Dict:
        """Convert results to unified reporter format"""
        return {
            "backend": results.get("backend", {}),
            "frontend": results.get("frontend", {}),
            "e2e": results.get("e2e", {})
        }
    
    def _print_unified_warning(self, error: str) -> None:
        """Print warning about unified reporter failure"""
        print(f"[WARNING] Unified reporter failed: {error}")


class ReportOutputManager:
    """Manages report output and console display"""
    
    def __init__(self):
        pass
    
    def print_save_confirmation(self, latest_file: Path, metrics_file: Path, 
                               history_dir: Path) -> None:
        """Print save confirmation to console"""
        try:
            self._print_unicode_confirmation(latest_file, metrics_file, history_dir)
        except UnicodeEncodeError:
            self._print_fallback_confirmation(latest_file, metrics_file, history_dir)
    
    def _print_unicode_confirmation(self, latest_file: Path, metrics_file: Path, 
                                   history_dir: Path) -> None:
        """Print confirmation with Unicode characters"""
        print(f"\n📊 Report saved:")
        print(f"  📄 Latest: {latest_file}")
        print(f"  📈 Metrics: {metrics_file}")
        print(f"  📁 History: {history_dir}")
    
    def _print_fallback_confirmation(self, latest_file: Path, metrics_file: Path, 
                                    history_dir: Path) -> None:
        """Print fallback confirmation without Unicode"""
        print(f"\n[REPORT] Report saved:")
        print(f"  [LATEST] {latest_file}")
        print(f"  [METRICS] {metrics_file}")
        print(f"  [HISTORY] {history_dir}")
    
    def _print_deleted(self, filename: str) -> None:
        """Print deleted file message"""
        try:
            print(f"  🗑️ Deleted old report: {filename}")
        except UnicodeEncodeError:
            print(f"  [DELETED] {filename}")
    
    def _print_archived(self, filename: str) -> None:
        """Print archived file message"""
        try:
            print(f"  📦 Archived: {filename}")
        except UnicodeEncodeError:
            print(f"  [ARCHIVED] {filename}")
    
    def _print_deleted_json(self, filename: str) -> None:
        """Print deleted JSON file message"""
        try:
            print(f"  🗑️ Deleted old JSON: {filename}")
        except UnicodeEncodeError:
            print(f"  [DELETED] {filename}")
    
    def _print_cleanup_complete(self) -> None:
        """Print cleanup complete message"""
        try:
            print("✅ Cleanup complete!")
        except UnicodeEncodeError:
            print("[COMPLETE] Cleanup finished!")


class ReportSaveOrchestrator:
    """Orchestrates the complete report saving process"""
    
    def __init__(self, reports_dir: Path):
        self.dir_manager = ReportDirectoryManager(reports_dir)
        self.file_writer = ReportFileWriter(self.dir_manager)
        self.historical_updater = HistoricalDataUpdater(self.file_writer)
        self.unified_integration = UnifiedReporterIntegration(reports_dir)
        self.output_manager = ReportOutputManager()
    
    def save_complete_report(self, level: str, report_content: str, 
                            results: Dict, metrics: Dict, historical_data: HistoricalData) -> None:
        """Save complete report with all components"""
        # Save main report files
        latest_file = self.file_writer.write_latest_report(level, report_content)
        metrics_file = self._save_metrics_data(level, metrics, results)
        
        # Update historical data
        self.historical_updater.update_historical_runs(historical_data, level, metrics, results)
        self.file_writer.write_historical_data(historical_data)
        # Generate unified report and print confirmation
        exit_code = 0 if metrics.get("failed", 0) == 0 else 1
        self.unified_integration.generate_unified_report(results, level, exit_code)
        self.output_manager.print_save_confirmation(
            latest_file, metrics_file, self.dir_manager.directories.history_dir
        )
    
    def _save_metrics_data(self, level: str, metrics: Dict, results: Dict) -> Path:
        """Save metrics data with timestamp"""
        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "level": level, "metrics": metrics, "results": results
        }
        return self.file_writer.write_metrics_json(level, metrics_data)