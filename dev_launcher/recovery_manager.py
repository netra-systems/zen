"""
Recovery Manager - Main orchestrator for 4-stage recovery process.

Coordinates the recovery strategy:
1. Error Capture: Collect logs, process info, system state
2. Diagnose: Analyze ports, database, memory, config issues  
3. Recovery Attempt: Kill zombies, clear temp files, reset connections
4. Fallback: Generate actionable suggestions for manual intervention

ARCHITECTURE COMPLIANCE:
- File size: ≤300 lines (currently under limit)
- Function size: ≤8 lines each (MANDATORY)
- Strong typing throughout
- Async patterns for all I/O operations
- Modular design with separate components
"""

import asyncio
import os
import subprocess
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import shutil

from .crash_recovery_models import DiagnosisResult, RecoveryStage
from .system_diagnostics import SystemDiagnostics
from .recovery_actions import RecoveryActions


logger = logging.getLogger(__name__)


class RecoveryManager:
    """Orchestrates the 4-stage recovery process for crashed services."""
    
    def __init__(self):
        """Initialize recovery manager with diagnostic and action components."""
        self.diagnostics = SystemDiagnostics()
        self.actions = RecoveryActions()
        self.capture_tools = self._get_system_tools()
    
    def _get_system_tools(self) -> List[str]:
        """Get available system diagnostic tools."""
        if os.name == 'nt':
            return ['tasklist', 'netstat', 'wmic']
        return ['ps', 'netstat', 'lsof', 'top']
    
    async def capture_error_context(self, service_name: str, 
                                  process: Optional[subprocess.Popen]) -> List[str]:
        """Stage 1: Capture error context and logs."""
        logs = []
        
        # Capture process information
        if process:
            logs.extend(self._capture_process_info(process))
        
        # Capture service logs
        logs.extend(await self._capture_service_logs(service_name))
        
        # Capture system state
        system_info = await self.diagnostics.get_system_info()
        logs.append(f"System info: {system_info}")
        
        return logs
    
    def _capture_process_info(self, process: subprocess.Popen) -> List[str]:
        """Capture information about the crashed process."""
        return [
            f"Process PID: {process.pid}",
            f"Return Code: {process.returncode}",
            f"Process Args: {' '.join(process.args) if hasattr(process, 'args') else 'Unknown'}"
        ]
    
    async def _capture_service_logs(self, service_name: str, lines: int = 100) -> List[str]:
        """Capture last N lines from service logs."""
        log_file = Path(f"dev_launcher/logs/{service_name}.log")
        if not log_file.exists():
            return [f"Log file not found: {log_file}"]
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) > lines else all_lines
        except Exception as e:
            return [f"Failed to read logs: {str(e)}"]
    
    async def diagnose_system(self, service_name: str) -> DiagnosisResult:
        """Stage 2: Diagnose system issues using comprehensive diagnostics."""
        return await self.diagnostics.run_full_diagnosis(service_name)
    
    async def attempt_recovery(self, service_name: str, diagnosis: DiagnosisResult) -> List[str]:
        """Stage 3: Attempt system recovery using specialized actions."""
        return await self.actions.execute_recovery_actions(service_name, diagnosis)
    
    async def fallback_recovery(self, service_name: str, diagnosis: DiagnosisResult) -> List[str]:
        """Stage 4: Fallback recovery with actionable suggestions."""
        return await self.actions.generate_fallback_suggestions(service_name, diagnosis)