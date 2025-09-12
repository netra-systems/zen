"""
Progress indicator for clean startup feedback.

Implements single-line progress updates with phase tracking
and ETA calculation for development launcher.
"""

import sys
import time
from typing import List, Optional, Tuple

try:
    from dev_launcher.progress_core import Phase, PhaseStatus, ProgressCalculator, SpinnerAnimation
except ImportError:
    from progress_core import Phase, PhaseStatus, ProgressCalculator, SpinnerAnimation


class ProgressIndicator:
    """
    Single-line progress indicator for development startup.
    
    Features:
    - Phase-based progress tracking
    - ETA calculation based on historical data
    - Spinner animation for long operations
    - Clean single-line updates
    """
    
    def __init__(self, phases: List[Tuple[str, str, float]] = None):
        """
        Initialize progress indicator.
        
        Args:
            phases: List of (name, description, estimated_duration) tuples
        """
        self.phases = self._create_phases(phases or self._default_phases())
        self.current_phase_idx = 0
        self.start_time = None
        self.spinner = SpinnerAnimation()
        self.last_update = 0
        self.update_interval = 0.1  # 100ms updates
        
    def start(self) -> None:
        """Start progress tracking."""
        self.start_time = time.time()
        self._clear_line()
        self._update_display()
        
    def next_phase(self, skip_current: bool = False) -> bool:
        """
        Move to next phase.
        
        Args:
            skip_current: Skip current phase as already cached
            
        Returns:
            True if there are more phases, False if complete
        """
        if self.current_phase_idx < len(self.phases):
            current = self.phases[self.current_phase_idx]
            
            if skip_current:
                current.status = PhaseStatus.SKIPPED
            else:
                current.end_time = time.time()
                current.status = PhaseStatus.COMPLETED
                
            self.current_phase_idx += 1
            
        if self.current_phase_idx < len(self.phases):
            next_phase = self.phases[self.current_phase_idx]
            next_phase.status = PhaseStatus.RUNNING
            next_phase.start_time = time.time()
            self._update_display()
            return True
            
        return False
    
    def fail_current_phase(self, error: str = "") -> None:
        """Mark current phase as failed."""
        if self.current_phase_idx < len(self.phases):
            current = self.phases[self.current_phase_idx]
            current.status = PhaseStatus.FAILED
            current.end_time = time.time()
            self._update_display()
    
    def update_progress(self, message: Optional[str] = None) -> None:
        """
        Update progress display.
        
        Args:
            message: Optional status message
        """
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
            
        self.last_update = current_time
        self._update_display(message)
    
    def complete(self) -> None:
        """Mark progress as complete."""
        # Complete any remaining phase
        if self.current_phase_idx < len(self.phases):
            current = self.phases[self.current_phase_idx]
            current.status = PhaseStatus.COMPLETED
            current.end_time = time.time()
            
        total_duration = time.time() - (self.start_time or time.time())
        self._clear_line()
        print(f"\n[U+1F680] System Ready ({total_duration:.1f}s)")
        self._show_service_urls()
    
    def _create_phases(self, phase_data: List[Tuple[str, str, float]]) -> List[Phase]:
        """Create phase objects from data."""
        return [
            Phase(name=name, description=desc, estimated_duration=duration)
            for name, desc, duration in phase_data
        ]
    
    def _default_phases(self) -> List[Tuple[str, str, float]]:
        """Get default startup phases."""
        return [
            ("INIT", "Checking environment and dependencies", 2.0),
            ("CACHE", "Loading cached configurations", 1.0),
            ("DEPS", "Installing/validating dependencies", 3.0),
            ("SERVICES", "Starting backend, auth and frontend", 8.0),
            ("HEALTH", "Waiting for services to be ready", 2.0)
        ]
    
    def _update_display(self, message: Optional[str] = None) -> None:
        """Update the progress display."""
        if self.current_phase_idx >= len(self.phases):
            return
            
        current = self.phases[self.current_phase_idx]
        progress_pct = ProgressCalculator.calculate_progress(
            self.phases, self.current_phase_idx
        )
        eta = ProgressCalculator.calculate_eta(self.start_time, progress_pct)
        spinner = self._get_spinner_char(current.status)
        
        # Build progress bar
        bar = ProgressCalculator.build_progress_bar(progress_pct)
        
        # Build status line
        status_parts = [
            f"{spinner} {current.name}:",
            current.description[:30] if len(current.description) > 30 else current.description,
            f"[{bar}]",
            f"{progress_pct:.0f}%"
        ]
        
        if eta > 0:
            status_parts.append(f"ETA: {eta:.0f}s")
            
        if message:
            status_parts.append(f"| {message[:20]}")
            
        status_line = " ".join(status_parts)
        
        # Update display
        self._clear_line()
        sys.stdout.write(status_line)
        sys.stdout.flush()
    
    def _get_spinner_char(self, status: PhaseStatus) -> str:
        """Get character for phase status."""
        if status == PhaseStatus.RUNNING:
            return self.spinner.next_frame()
        elif status == PhaseStatus.COMPLETED:
            return " PASS: "
        elif status == PhaseStatus.FAILED:
            return " FAIL: "
        elif status == PhaseStatus.SKIPPED:
            return "[U+23ED][U+FE0F]"
        else:
            return "[U+23F3]"
    
    def _clear_line(self) -> None:
        """Clear current terminal line."""
        sys.stdout.write("\r" + " " * 120 + "\r")
        sys.stdout.flush()
    
    def _show_service_urls(self) -> None:
        """Show service URLs after completion."""
        urls = [
            ("Frontend", "http://localhost:3000"),
            ("Backend", "http://localhost:8000"),
            ("API Docs", "http://localhost:8000/docs")
        ]
        
        for name, url in urls:
            print(f"   {name:<10} {url}")


class QuietProgressIndicator:
    """
    Minimal progress indicator for silent mode.
    
    Shows only essential status updates without animation.
    """
    
    def __init__(self):
        """Initialize quiet indicator."""
        self.start_time = None
        
    def start(self) -> None:
        """Start silent progress."""
        self.start_time = time.time()
        print(" LIGHTNING:  Starting Netra Apex...")
        
    def next_phase(self, skip_current: bool = False) -> bool:
        """Silent phase transition."""
        return True
        
    def fail_current_phase(self, error: str = "") -> None:
        """Show failure in silent mode."""
        print(f" FAIL:  Startup failed: {error}")
        
    def update_progress(self, message: Optional[str] = None) -> None:
        """No updates in silent mode."""
        pass
        
    def complete(self) -> None:
        """Show completion in silent mode."""
        if self.start_time:
            duration = time.time() - self.start_time
            print(f"[U+1F680] Ready ({duration:.1f}s)")


class ProgressFactory:
    """Factory for creating appropriate progress indicators."""
    
    @staticmethod
    def create(mode: str = "standard") -> ProgressIndicator:
        """
        Create progress indicator based on mode.
        
        Args:
            mode: Progress mode (silent, minimal, standard, verbose)
            
        Returns:
            Appropriate progress indicator instance
        """
        if mode.lower() == "silent":
            return QuietProgressIndicator()
        else:
            return ProgressIndicator()