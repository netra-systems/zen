#!/usr/bin/env python3
"""
Progress Tracker Module - Real-time test execution progress tracking
Provides comprehensive progress monitoring with persistence and recovery support
"""

import asyncio
import json
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Callable, Any
from threading import Lock


class ProgressStatus(Enum):
    """Progress status for categories and overall runs"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class ProgressEvent(Enum):
    """Progress tracking events"""
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"
    CATEGORY_STARTED = "category_started"
    CATEGORY_COMPLETED = "category_completed"
    CATEGORY_FAILED = "category_failed"
    CATEGORY_SKIPPED = "category_skipped"
    TEST_STARTED = "test_started"
    TEST_COMPLETED = "test_completed"
    TEST_FAILED = "test_failed"
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"


@dataclass
class CategoryProgress:
    """Progress tracking for individual test categories"""
    name: str
    status: ProgressStatus = ProgressStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: timedelta = field(default_factory=lambda: timedelta(0))
    
    # Test execution details
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    
    # Progress indicators
    progress_percentage: float = 0.0
    estimated_remaining: timedelta = field(default_factory=lambda: timedelta(0))
    
    # Output and results
    output_log: List[str] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Resource usage (if available)
    peak_memory_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    # Retry and recovery
    retry_count: int = 0
    max_retries: int = 0
    
    # Metadata
    phase: int = 0
    parallel_group: Optional[str] = None
    worker_id: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """Initialize computed properties"""
        if isinstance(self.tags, (list, tuple)):
            self.tags = set(self.tags)
    
    @property
    def is_complete(self) -> bool:
        """Check if category is complete (success or failure)"""
        return self.status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED, 
                              ProgressStatus.SKIPPED, ProgressStatus.CANCELLED]
    
    @property
    def is_successful(self) -> bool:
        """Check if category completed successfully"""
        return self.status == ProgressStatus.COMPLETED
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate for tests in this category"""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests
    
    @property
    def execution_time(self) -> timedelta:
        """Get actual execution time"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return datetime.now() - self.start_time
        return timedelta(0)
    
    def start(self, phase: int = 0, parallel_group: Optional[str] = None, 
             worker_id: Optional[str] = None):
        """Mark category as started"""
        self.status = ProgressStatus.RUNNING
        self.start_time = datetime.now()
        self.phase = phase
        self.parallel_group = parallel_group
        self.worker_id = worker_id
    
    def complete(self, success: bool = True):
        """Mark category as completed"""
        self.status = ProgressStatus.COMPLETED if success else ProgressStatus.FAILED
        self.end_time = datetime.now()
        self.progress_percentage = 100.0
        self.estimated_remaining = timedelta(0)
    
    def skip(self, reason: str = ""):
        """Mark category as skipped"""
        self.status = ProgressStatus.SKIPPED
        self.end_time = datetime.now()
        self.progress_percentage = 100.0
        if reason:
            self.warnings.append(f"Skipped: {reason}")
    
    def cancel(self, reason: str = ""):
        """Mark category as cancelled"""
        self.status = ProgressStatus.CANCELLED
        self.end_time = datetime.now()
        if reason:
            self.error_messages.append(f"Cancelled: {reason}")
    
    def update_test_counts(self, total: int = None, passed: int = None, 
                          failed: int = None, skipped: int = None, error: int = None):
        """Update test execution counts"""
        if total is not None:
            self.total_tests = total
        if passed is not None:
            self.passed_tests = passed
        if failed is not None:
            self.failed_tests = failed
        if skipped is not None:
            self.skipped_tests = skipped
        if error is not None:
            self.error_tests = error
        
        # Update progress percentage
        if self.total_tests > 0:
            completed_tests = self.passed_tests + self.failed_tests + self.skipped_tests + self.error_tests
            self.progress_percentage = min(100.0, (completed_tests / self.total_tests) * 100.0)
    
    def add_log_entry(self, message: str, level: str = "INFO"):
        """Add log entry with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.output_log.append(f"[{timestamp}] {level}: {message}")
        
        if level in ["ERROR", "CRITICAL"]:
            self.error_messages.append(message)
        elif level == "WARNING":
            self.warnings.append(message)
    
    def update_resource_usage(self, memory_mb: float = None, cpu_percent: float = None):
        """Update resource usage statistics"""
        if memory_mb is not None:
            self.peak_memory_mb = max(self.peak_memory_mb, memory_mb)
        if cpu_percent is not None:
            self.cpu_usage_percent = cpu_percent
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration.total_seconds(),
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "error_tests": self.error_tests,
            "progress_percentage": self.progress_percentage,
            "estimated_remaining": self.estimated_remaining.total_seconds(),
            "output_log": self.output_log[-50:],  # Keep last 50 entries
            "error_messages": self.error_messages,
            "warnings": self.warnings,
            "peak_memory_mb": self.peak_memory_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "phase": self.phase,
            "parallel_group": self.parallel_group,
            "worker_id": self.worker_id,
            "tags": list(self.tags),
            "success_rate": self.success_rate,
            "execution_time": self.execution_time.total_seconds()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CategoryProgress':
        """Create from dictionary"""
        progress = cls(
            name=data["name"],
            status=ProgressStatus(data.get("status", "pending")),
            duration=timedelta(seconds=data.get("duration", 0)),
            total_tests=data.get("total_tests", 0),
            passed_tests=data.get("passed_tests", 0),
            failed_tests=data.get("failed_tests", 0),
            skipped_tests=data.get("skipped_tests", 0),
            error_tests=data.get("error_tests", 0),
            progress_percentage=data.get("progress_percentage", 0.0),
            estimated_remaining=timedelta(seconds=data.get("estimated_remaining", 0)),
            output_log=data.get("output_log", []),
            error_messages=data.get("error_messages", []),
            warnings=data.get("warnings", []),
            peak_memory_mb=data.get("peak_memory_mb", 0.0),
            cpu_usage_percent=data.get("cpu_usage_percent", 0.0),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 0),
            phase=data.get("phase", 0),
            parallel_group=data.get("parallel_group"),
            worker_id=data.get("worker_id"),
            tags=set(data.get("tags", []))
        )
        
        if data.get("start_time"):
            progress.start_time = datetime.fromisoformat(data["start_time"])
        if data.get("end_time"):
            progress.end_time = datetime.fromisoformat(data["end_time"])
        
        return progress


@dataclass
class TestRunProgress:
    """Overall test run progress tracking"""
    run_id: str
    start_time: datetime
    status: ProgressStatus = ProgressStatus.RUNNING
    end_time: Optional[datetime] = None
    
    # Categories and phases
    categories: Dict[str, CategoryProgress] = field(default_factory=dict)
    total_categories: int = 0
    completed_categories: int = 0
    current_phase: int = 0
    total_phases: int = 0
    
    # Overall test statistics
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    
    # Progress and timing
    overall_progress: float = 0.0
    estimated_total_duration: timedelta = field(default_factory=lambda: timedelta(0))
    estimated_remaining: timedelta = field(default_factory=lambda: timedelta(0))
    
    # Configuration and metadata
    test_level: str = ""
    service_filter: Optional[str] = None
    parallel_workers: int = 1
    fail_fast_enabled: bool = False
    real_llm_enabled: bool = False
    environment: str = "local"
    
    # Resource tracking
    peak_memory_mb: float = 0.0
    average_cpu_percent: float = 0.0
    
    # Recovery and resumption
    resumable: bool = True
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def execution_duration(self) -> timedelta:
        """Get current execution duration"""
        end = self.end_time or datetime.now()
        return end - self.start_time
    
    @property
    def success_rate(self) -> float:
        """Calculate overall success rate"""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests
    
    @property
    def is_complete(self) -> bool:
        """Check if run is complete"""
        return self.status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED, 
                              ProgressStatus.CANCELLED]
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage based on categories"""
        if self.total_categories == 0:
            return 0.0
        return (self.completed_categories / self.total_categories) * 100.0
    
    def update_overall_progress(self):
        """Update overall progress based on category progress"""
        if not self.categories:
            return
        
        total_progress = sum(cat.progress_percentage for cat in self.categories.values())
        self.overall_progress = total_progress / len(self.categories)
        
        # Update test counts
        self.total_tests = sum(cat.total_tests for cat in self.categories.values())
        self.passed_tests = sum(cat.passed_tests for cat in self.categories.values())
        self.failed_tests = sum(cat.failed_tests for cat in self.categories.values())
        self.skipped_tests = sum(cat.skipped_tests for cat in self.categories.values())
        self.error_tests = sum(cat.error_tests for cat in self.categories.values())
        
        # Update completed categories count
        self.completed_categories = sum(1 for cat in self.categories.values() if cat.is_complete)
        
        # Update resource usage
        if self.categories:
            self.peak_memory_mb = max(cat.peak_memory_mb for cat in self.categories.values())
            active_categories = [cat for cat in self.categories.values() 
                               if cat.status == ProgressStatus.RUNNING]
            if active_categories:
                self.average_cpu_percent = sum(cat.cpu_usage_percent for cat in active_categories) / len(active_categories)
    
    def complete(self, success: bool = True):
        """Mark run as completed"""
        self.status = ProgressStatus.COMPLETED if success else ProgressStatus.FAILED
        self.end_time = datetime.now()
        self.overall_progress = 100.0
        self.estimated_remaining = timedelta(0)
        self.update_overall_progress()
    
    def cancel(self, reason: str = ""):
        """Cancel the run"""
        self.status = ProgressStatus.CANCELLED
        self.end_time = datetime.now()
        
        # Cancel all running categories
        for category in self.categories.values():
            if category.status == ProgressStatus.RUNNING:
                category.cancel(reason)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.value,
            "categories": {name: cat.to_dict() for name, cat in self.categories.items()},
            "total_categories": self.total_categories,
            "completed_categories": self.completed_categories,
            "current_phase": self.current_phase,
            "total_phases": self.total_phases,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "error_tests": self.error_tests,
            "overall_progress": self.overall_progress,
            "estimated_total_duration": self.estimated_total_duration.total_seconds(),
            "estimated_remaining": self.estimated_remaining.total_seconds(),
            "test_level": self.test_level,
            "service_filter": self.service_filter,
            "parallel_workers": self.parallel_workers,
            "fail_fast_enabled": self.fail_fast_enabled,
            "real_llm_enabled": self.real_llm_enabled,
            "environment": self.environment,
            "peak_memory_mb": self.peak_memory_mb,
            "average_cpu_percent": self.average_cpu_percent,
            "execution_duration": self.execution_duration.total_seconds(),
            "success_rate": self.success_rate,
            "completion_percentage": self.completion_percentage,
            "resumable": self.resumable,
            "checkpoint_data": self.checkpoint_data
        }


class ProgressTracker:
    """Enhanced progress tracker with real-time updates and persistence"""
    
    def __init__(self, project_root: Path, enable_persistence: bool = True,
                 auto_save_interval: int = 30):
        self.project_root = project_root
        self.reports_dir = project_root / "test_reports"
        self.progress_dir = self.reports_dir / "progress"
        self.enable_persistence = enable_persistence
        self.auto_save_interval = auto_save_interval
        
        # Current state
        self.current_run: Optional[TestRunProgress] = None
        self._lock = Lock()
        self._observers: List[Callable[[ProgressEvent, Dict], None]] = []
        
        # Auto-save thread
        self._auto_save_thread: Optional[threading.Thread] = None
        self._auto_save_stop_event = threading.Event()
        
        # Ensure directories exist
        self.progress_dir.mkdir(parents=True, exist_ok=True)
    
    def start_run(self, run_id: str, categories: List[str], test_level: str = "",
                  parallel_workers: int = 1, fail_fast: bool = False, 
                  real_llm: bool = False, environment: str = "local") -> TestRunProgress:
        """Start a new test run"""
        with self._lock:
            self.current_run = TestRunProgress(
                run_id=run_id,
                start_time=datetime.now(),
                total_categories=len(categories),
                test_level=test_level,
                parallel_workers=parallel_workers,
                fail_fast_enabled=fail_fast,
                real_llm_enabled=real_llm,
                environment=environment
            )
            
            # Initialize category progress
            for category_name in categories:
                self.current_run.categories[category_name] = CategoryProgress(name=category_name)
            
            # Start auto-save if persistence is enabled
            if self.enable_persistence and not self._auto_save_thread:
                self._start_auto_save()
            
            self._notify_observers(ProgressEvent.RUN_STARTED, {
                "run_id": run_id,
                "categories": categories,
                "test_level": test_level
            })
            
            return self.current_run
    
    def start_category(self, category_name: str, phase: int = 0, 
                      parallel_group: Optional[str] = None, 
                      worker_id: Optional[str] = None) -> bool:
        """Start execution of a category"""
        if not self.current_run or category_name not in self.current_run.categories:
            return False
        
        with self._lock:
            category = self.current_run.categories[category_name]
            category.start(phase, parallel_group, worker_id)
            
            # Update current phase
            self.current_run.current_phase = max(self.current_run.current_phase, phase)
            
            self._notify_observers(ProgressEvent.CATEGORY_STARTED, {
                "category_name": category_name,
                "phase": phase,
                "worker_id": worker_id
            })
            
            return True
    
    def complete_category(self, category_name: str, success: bool = True,
                         test_counts: Optional[Dict[str, int]] = None,
                         resource_usage: Optional[Dict[str, float]] = None,
                         output_lines: Optional[List[str]] = None) -> bool:
        """Complete execution of a category"""
        if not self.current_run or category_name not in self.current_run.categories:
            return False
        
        with self._lock:
            category = self.current_run.categories[category_name]
            category.complete(success)
            
            # Update test counts if provided
            if test_counts:
                category.update_test_counts(**test_counts)
            
            # Update resource usage if provided
            if resource_usage:
                category.update_resource_usage(**resource_usage)
            
            # Add output lines if provided
            if output_lines:
                for line in output_lines[-20:]:  # Keep last 20 lines
                    category.add_log_entry(line.strip())
            
            # Update overall progress
            self.current_run.update_overall_progress()
            
            event_type = ProgressEvent.CATEGORY_COMPLETED if success else ProgressEvent.CATEGORY_FAILED
            self._notify_observers(event_type, {
                "category_name": category_name,
                "success": success,
                "test_counts": test_counts or {},
                "duration": category.execution_time.total_seconds()
            })
            
            return True
    
    def skip_category(self, category_name: str, reason: str = "") -> bool:
        """Skip execution of a category"""
        if not self.current_run or category_name not in self.current_run.categories:
            return False
        
        with self._lock:
            category = self.current_run.categories[category_name]
            category.skip(reason)
            
            self.current_run.update_overall_progress()
            
            self._notify_observers(ProgressEvent.CATEGORY_SKIPPED, {
                "category_name": category_name,
                "reason": reason
            })
            
            return True
    
    def update_category_progress(self, category_name: str, progress_percent: float = None,
                               test_counts: Optional[Dict[str, int]] = None,
                               log_message: str = None, level: str = "INFO",
                               resource_usage: Optional[Dict[str, float]] = None) -> bool:
        """Update category progress during execution"""
        if not self.current_run or category_name not in self.current_run.categories:
            return False
        
        with self._lock:
            category = self.current_run.categories[category_name]
            
            if progress_percent is not None:
                category.progress_percentage = min(100.0, progress_percent)
            
            if test_counts:
                category.update_test_counts(**test_counts)
            
            if log_message:
                category.add_log_entry(log_message, level)
            
            if resource_usage:
                category.update_resource_usage(**resource_usage)
            
            # Update overall progress
            self.current_run.update_overall_progress()
            
            return True
    
    def complete_run(self, success: bool = True) -> bool:
        """Complete the current test run"""
        if not self.current_run:
            return False
        
        with self._lock:
            self.current_run.complete(success)
            
            # Stop auto-save
            self._stop_auto_save()
            
            # Final save
            if self.enable_persistence:
                self._save_progress()
            
            event_type = ProgressEvent.RUN_COMPLETED if success else ProgressEvent.RUN_FAILED
            self._notify_observers(event_type, {
                "run_id": self.current_run.run_id,
                "success": success,
                "duration": self.current_run.execution_duration.total_seconds(),
                "total_tests": self.current_run.total_tests,
                "success_rate": self.current_run.success_rate
            })
            
            return True
    
    def cancel_run(self, reason: str = "") -> bool:
        """Cancel the current test run"""
        if not self.current_run:
            return False
        
        with self._lock:
            self.current_run.cancel(reason)
            
            # Stop auto-save
            self._stop_auto_save()
            
            # Final save
            if self.enable_persistence:
                self._save_progress()
            
            self._notify_observers(ProgressEvent.RUN_CANCELLED, {
                "run_id": self.current_run.run_id,
                "reason": reason
            })
            
            return True
    
    def get_current_progress(self) -> Optional[Dict]:
        """Get current progress snapshot"""
        if not self.current_run:
            return None
        
        with self._lock:
            return self.current_run.to_dict()
    
    def get_category_progress(self, category_name: str) -> Optional[Dict]:
        """Get progress for specific category"""
        if not self.current_run or category_name not in self.current_run.categories:
            return None
        
        with self._lock:
            return self.current_run.categories[category_name].to_dict()
    
    def add_observer(self, callback: Callable[[ProgressEvent, Dict], None]):
        """Add progress observer callback"""
        self._observers.append(callback)
    
    def remove_observer(self, callback: Callable[[ProgressEvent, Dict], None]):
        """Remove progress observer callback"""
        if callback in self._observers:
            self._observers.remove(callback)
    
    def _notify_observers(self, event: ProgressEvent, data: Dict):
        """Notify all observers of progress event"""
        for observer in self._observers:
            try:
                observer(event, data)
            except Exception as e:
                # Log error but don't break other observers
                print(f"Error in progress observer: {e}")
    
    def _start_auto_save(self):
        """Start auto-save thread"""
        self._auto_save_stop_event.clear()
        self._auto_save_thread = threading.Thread(target=self._auto_save_worker)
        self._auto_save_thread.daemon = True
        self._auto_save_thread.start()
    
    def _stop_auto_save(self):
        """Stop auto-save thread"""
        self._auto_save_stop_event.set()
        if self._auto_save_thread and self._auto_save_thread.is_alive():
            self._auto_save_thread.join(timeout=5)
        self._auto_save_thread = None
    
    def _auto_save_worker(self):
        """Auto-save worker thread"""
        while not self._auto_save_stop_event.wait(self.auto_save_interval):
            if self.current_run and not self.current_run.is_complete:
                self._save_progress()
    
    def _save_progress(self):
        """Save current progress to file"""
        if not self.current_run or not self.enable_persistence:
            return
        
        try:
            progress_file = self.progress_dir / f"progress_{self.current_run.run_id}.json"
            with open(progress_file, 'w') as f:
                json.dump(self.current_run.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving progress: {e}")
    
    def load_progress(self, run_id: str) -> Optional[TestRunProgress]:
        """Load progress from file"""
        if not self.enable_persistence:
            return None
        
        progress_file = self.progress_dir / f"progress_{run_id}.json"
        if not progress_file.exists():
            return None
        
        try:
            with open(progress_file) as f:
                data = json.load(f)
            
            run_progress = TestRunProgress(
                run_id=data["run_id"],
                start_time=datetime.fromisoformat(data["start_time"]),
                status=ProgressStatus(data["status"]),
                total_categories=data["total_categories"],
                current_phase=data.get("current_phase", 0),
                total_phases=data.get("total_phases", 0),
                test_level=data.get("test_level", ""),
                service_filter=data.get("service_filter"),
                parallel_workers=data.get("parallel_workers", 1),
                fail_fast_enabled=data.get("fail_fast_enabled", False),
                real_llm_enabled=data.get("real_llm_enabled", False),
                environment=data.get("environment", "local"),
                resumable=data.get("resumable", True),
                checkpoint_data=data.get("checkpoint_data", {})
            )
            
            if data.get("end_time"):
                run_progress.end_time = datetime.fromisoformat(data["end_time"])
            
            # Load category progress
            for cat_name, cat_data in data.get("categories", {}).items():
                run_progress.categories[cat_name] = CategoryProgress.from_dict(cat_data)
            
            return run_progress
            
        except Exception as e:
            print(f"Error loading progress: {e}")
            return None
    
    def list_saved_runs(self) -> List[Dict[str, str]]:
        """List all saved progress files"""
        if not self.enable_persistence:
            return []
        
        runs = []
        for progress_file in self.progress_dir.glob("progress_*.json"):
            try:
                with open(progress_file) as f:
                    data = json.load(f)
                
                runs.append({
                    "run_id": data.get("run_id", "unknown"),
                    "start_time": data.get("start_time", ""),
                    "status": data.get("status", "unknown"),
                    "test_level": data.get("test_level", ""),
                    "total_categories": data.get("total_categories", 0),
                    "file_path": str(progress_file)
                })
                
            except Exception:
                continue
        
        return sorted(runs, key=lambda x: x["start_time"], reverse=True)
    
    def cleanup_old_progress(self, days: int = 7):
        """Clean up progress files older than specified days"""
        if not self.enable_persistence:
            return
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        for progress_file in self.progress_dir.glob("progress_*.json"):
            try:
                file_time = datetime.fromtimestamp(progress_file.stat().st_mtime)
                if file_time < cutoff_time:
                    progress_file.unlink()
            except Exception:
                continue
    
    def export_run_summary(self, run_id: str = None, output_path: Path = None) -> Optional[Path]:
        """Export run summary to JSON file"""
        run_progress = self.current_run
        if run_id:
            run_progress = self.load_progress(run_id)
        
        if not run_progress:
            return None
        
        if not output_path:
            output_path = self.reports_dir / f"summary_{run_progress.run_id}.json"
        
        summary = {
            "run_summary": run_progress.to_dict(),
            "export_time": datetime.now().isoformat(),
            "categories_summary": [
                {
                    "name": cat.name,
                    "status": cat.status.value,
                    "duration": cat.execution_time.total_seconds(),
                    "test_counts": {
                        "total": cat.total_tests,
                        "passed": cat.passed_tests,
                        "failed": cat.failed_tests,
                        "skipped": cat.skipped_tests,
                        "error": cat.error_tests
                    },
                    "success_rate": cat.success_rate,
                    "phase": cat.phase
                }
                for cat in run_progress.categories.values()
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return output_path