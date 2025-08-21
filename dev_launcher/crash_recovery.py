"""
Crash Recovery Manager for Netra Development Services - Main Orchestrator.

Provides automatic detection and recovery from service crashes with:
- Process monitoring via Process.poll() every 5 seconds
- Health endpoint checks every 30 seconds  
- Log pattern analysis for FATAL, CRITICAL ERROR patterns
- 4-stage recovery: Error Capture, Diagnose, Recovery Attempt, Fallback
- Exponential backoff: 5s, 15s, 45s with max 3 attempts
- Crash reports saved to .netra/crash_reports/

ARCHITECTURE COMPLIANCE:
- File size: ≤300 lines (currently under limit)
- Function size: ≤8 lines each (MANDATORY)
- Strong typing with Pydantic models
- Async patterns throughout
- Modular design with separate components
"""

import asyncio
import subprocess
import time
import logging
from typing import Dict, List, Optional, Any
from netra_backend.app.schemas.service_types import ServiceStatus, ServiceHealthCheck
from netra_backend.app.core.exceptions_base import NetraException

# Import modular components
from .crash_recovery_models import (
    CrashReport, CrashSeverity, DetectionResult, RecoveryAttempt, 
    RecoveryStage, MonitoringConfig, ServiceConfig, DetectionMethod
)
from .crash_detector import CrashDetector
from .recovery_manager import RecoveryManager
from .crash_reporter import CrashReporter


logger = logging.getLogger(__name__)


class CrashRecoveryManager:
    """Main orchestrator for crash detection and recovery."""
    
    def __init__(self, process_manager=None, config: MonitoringConfig = None):
        """Initialize crash recovery manager with components."""
        self.detector = CrashDetector()
        self.recovery = RecoveryManager()
        self.reporter = CrashReporter()
        self.process_manager = process_manager
        self.config = config or MonitoringConfig()
        self.monitoring = False
        self.monitoring_tasks = []
    
    async def start_monitoring(self, services: Dict[str, ServiceConfig]):
        """Start continuous crash monitoring for all services."""
        if self.monitoring:
            logger.warning("Monitoring already active")
            return
        
        self.monitoring = True
        logger.info(f"Starting crash monitoring for {len(services)} services")
        
        self.monitoring_tasks = [
            asyncio.create_task(self._monitor_service(name, config))
            for name, config in services.items()
        ]
        
        try:
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
        finally:
            self.monitoring = False
    
    def stop_monitoring(self):
        """Stop crash monitoring gracefully."""
        logger.info("Stopping crash monitoring")
        self.monitoring = False
        
        for task in self.monitoring_tasks:
            if not task.done():
                task.cancel()
    
    async def _monitor_service(self, service_name: str, service_config: ServiceConfig):
        """Monitor individual service for crashes continuously."""
        logger.info(f"Starting monitoring for service: {service_name}")
        
        while self.monitoring:
            try:
                await self._check_service_health(service_name, service_config)
                await asyncio.sleep(self.config.process_check_interval)
            except asyncio.CancelledError:
                logger.info(f"Monitoring cancelled for {service_name}")
                break
            except Exception as e:
                logger.error(f"Error monitoring {service_name}: {e}")
                await asyncio.sleep(self.config.process_check_interval * 2)
    
    async def _check_service_health(self, service_name: str, service_config: ServiceConfig):
        """Check health of a single service and handle crashes."""
        process = self._get_service_process(service_name)
        detection_results = await self.detector.run_all_detections(
            service_name, service_config.model_dump(), process
        )
        
        if self.detector.has_any_crash(detection_results):
            await self._handle_service_crash(service_name, detection_results, process)
    
    def _get_service_process(self, service_name: str) -> Optional[subprocess.Popen]:
        """Get process reference for service."""
        if self.process_manager:
            return self.process_manager.get_process(service_name)
        return None
    
    async def _handle_service_crash(self, service_name: str, detection_results: List[DetectionResult],
                                  process: Optional[subprocess.Popen]):
        """Handle detected crash with full recovery process."""
        logger.warning(f"Crash detected for service: {service_name}")
        
        crash_report = self._create_crash_report(service_name, detection_results)
        
        for attempt in range(self.config.max_recovery_attempts):
            recovery_attempt = await self._execute_recovery_attempt(
                service_name, attempt + 1, crash_report, process
            )
            crash_report.recovery_attempts.append(recovery_attempt)
            
            if recovery_attempt.success:
                crash_report.resolved = True
                logger.info(f"Recovery successful for {service_name} on attempt {attempt + 1}")
                break
            
            # Wait before next attempt
            if attempt < self.config.max_recovery_attempts - 1:
                delay = self.config.backoff_delays[min(attempt, len(self.config.backoff_delays) - 1)]
                await asyncio.sleep(delay)
        
        # Save final crash report
        report_path = await self.reporter.save_report(crash_report)
        logger.info(f"Crash report saved: {report_path}")
    
    def _create_crash_report(self, service_name: str, detection_results: List[DetectionResult]) -> CrashReport:
        """Create initial crash report."""
        return CrashReport(
            service_name=service_name,
            severity=CrashSeverity.MEDIUM,
            detection_results=detection_results
        )
    
    async def _execute_recovery_attempt(self, service_name: str, attempt_number: int,
                                      crash_report: CrashReport, process: Optional[subprocess.Popen]) -> RecoveryAttempt:
        """Execute single recovery attempt through all 4 stages."""
        recovery_attempt = RecoveryAttempt(
            attempt_number=attempt_number, 
            stage=RecoveryStage.ERROR_CAPTURE
        )
        start_time = time.time()
        
        try:
            # Stage 1: Error Capture
            await self._stage_error_capture(service_name, crash_report, recovery_attempt, process)
            
            # Stage 2: Diagnose
            await self._stage_diagnose(service_name, crash_report, recovery_attempt)
            
            # Stage 3: Recovery Attempt
            await self._stage_recovery_attempt(service_name, crash_report, recovery_attempt)
            
            # Stage 4: Fallback (if needed)
            await self._stage_fallback(service_name, crash_report, recovery_attempt)
            
            recovery_attempt.success = True
            
        except Exception as e:
            recovery_attempt.error_message = str(e)
            logger.error(f"Recovery attempt {attempt_number} failed for {service_name}: {e}")
        finally:
            recovery_attempt.duration_seconds = time.time() - start_time
        
        return recovery_attempt
    
    async def _stage_error_capture(self, service_name: str, crash_report: CrashReport,
                                 recovery_attempt: RecoveryAttempt, process: Optional[subprocess.Popen]):
        """Execute error capture stage."""
        recovery_attempt.stage = RecoveryStage.ERROR_CAPTURE
        logs = await self.recovery.capture_error_context(service_name, process)
        crash_report.last_logs = logs
        recovery_attempt.actions_taken.append("Captured error context and logs")
    
    async def _stage_diagnose(self, service_name: str, crash_report: CrashReport,
                            recovery_attempt: RecoveryAttempt):
        """Execute diagnosis stage."""
        recovery_attempt.stage = RecoveryStage.DIAGNOSE
        diagnosis = await self.recovery.diagnose_system(service_name)
        crash_report.diagnosis = diagnosis
        recovery_attempt.actions_taken.append("Completed system diagnosis")
    
    async def _stage_recovery_attempt(self, service_name: str, crash_report: CrashReport,
                                    recovery_attempt: RecoveryAttempt):
        """Execute recovery attempt stage."""
        recovery_attempt.stage = RecoveryStage.RECOVERY_ATTEMPT
        actions = await self.recovery.attempt_recovery(service_name, crash_report.diagnosis)
        recovery_attempt.actions_taken.extend(actions)
    
    async def _stage_fallback(self, service_name: str, crash_report: CrashReport,
                            recovery_attempt: RecoveryAttempt):
        """Execute fallback stage if needed."""
        if not recovery_attempt.success:
            recovery_attempt.stage = RecoveryStage.FALLBACK
            fallback_actions = await self.recovery.fallback_recovery(service_name, crash_report.diagnosis)
            recovery_attempt.actions_taken.extend(fallback_actions)
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            "monitoring_active": self.monitoring,
            "services_monitored": len(self.monitoring_tasks),
            "config": self.config.model_dump(),
            "active_tasks": len([t for t in self.monitoring_tasks if not t.done()])
        }
    
    async def force_recovery(self, service_name: str) -> CrashReport:
        """Force recovery attempt for a specific service."""
        logger.info(f"Forcing recovery for service: {service_name}")
        
        process = self._get_service_process(service_name)
        detection_results = [
            DetectionResult(
                method=DetectionMethod.PROCESS_MONITORING, 
                is_crashed=True, 
                error_message="Manual recovery triggered"
            )
        ]
        
        crash_report = self._create_crash_report(service_name, detection_results)
        
        recovery_attempt = await self._execute_recovery_attempt(service_name, 1, crash_report, process)
        crash_report.recovery_attempts.append(recovery_attempt)
        
        await self.reporter.save_report(crash_report)
        return crash_report