"""
Core progress tracking components.

Phase and animation classes for progress indicators.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PhaseStatus(Enum):
    """Phase execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Phase:
    """Single startup phase."""
    name: str
    description: str
    estimated_duration: float
    status: PhaseStatus = PhaseStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Get phase duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class SpinnerAnimation:
    """Simple spinner for long operations."""
    
    FRAMES = ['[U+280B]', '[U+2819]', '[U+2839]', '[U+2838]', '[U+283C]', '[U+2834]', '[U+2826]', '[U+2827]', '[U+2807]', '[U+280F]']
    
    def __init__(self):
        """Initialize spinner."""
        self.frame = 0
        
    def next_frame(self) -> str:
        """Get next spinner frame."""
        frame = self.FRAMES[self.frame]
        self.frame = (self.frame + 1) % len(self.FRAMES)
        return frame


class ProgressCalculator:
    """Helper class for progress calculations."""
    
    @staticmethod
    def calculate_progress(phases, current_idx: int) -> float:
        """Calculate overall progress percentage."""
        total_weight = sum(p.estimated_duration for p in phases)
        completed_weight = 0
        
        for i, phase in enumerate(phases):
            if phase.status == PhaseStatus.COMPLETED:
                completed_weight += phase.estimated_duration
            elif phase.status == PhaseStatus.SKIPPED:
                completed_weight += phase.estimated_duration
            elif phase.status == PhaseStatus.RUNNING and i == current_idx:
                # Estimate progress within current phase
                if phase.start_time:
                    elapsed = time.time() - phase.start_time
                    phase_progress = min(elapsed / phase.estimated_duration, 1.0)
                    completed_weight += phase.estimated_duration * phase_progress
                    
        return (completed_weight / total_weight) * 100 if total_weight > 0 else 0
    
    @staticmethod
    def calculate_eta(start_time: Optional[float], progress: float) -> float:
        """Calculate estimated time to completion."""
        if not start_time:
            return 0
            
        elapsed = time.time() - start_time
        
        if progress <= 0:
            return 0
            
        total_estimated = (elapsed / progress) * 100
        return max(0, total_estimated - elapsed)
    
    @staticmethod
    def build_progress_bar(percentage: float, width: int = 20) -> str:
        """Build visual progress bar."""
        filled = int((percentage / width) * width)
        bar = "[U+2588]" * filled + "[U+2591]" * (width - filled)
        return bar