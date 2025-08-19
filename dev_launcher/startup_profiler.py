"""
Startup profiler for precise timing analysis and bottleneck identification.

Profiles each startup phase, identifies performance bottlenecks automatically,
generates actionable performance reports, and stores metrics for historical analysis.
"""

import time
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timezone
from statistics import mean, median

logger = logging.getLogger(__name__)


@dataclass
class TimingMetric:
    """Individual timing measurement."""
    name: str
    start_time: float
    end_time: float
    duration: float
    success: bool
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PhaseProfile:
    """Performance profile for a startup phase."""
    phase_name: str
    total_duration: float
    step_count: int
    success_rate: float
    slowest_steps: List[Tuple[str, float]]
    bottlenecks: List[str]
    cache_hits: int
    cache_misses: int


@dataclass
class StartupProfile:
    """Complete startup performance profile."""
    timestamp: str
    total_duration: float
    target_met: bool
    phase_profiles: Dict[str, PhaseProfile]
    critical_path: List[str]
    recommendations: List[str]
    historical_comparison: Optional[Dict[str, float]] = None


class StartupProfiler:
    """
    Startup profiler for timing analysis and bottleneck identification.
    
    Provides precise timing measurements, automatic bottleneck detection,
    performance report generation, and historical metrics storage.
    """
    
    def __init__(self, project_root: Path, target_time: float = 10.0):
        """Initialize profiler with target time and storage location."""
        self.project_root = project_root
        self.target_time = target_time
        self.metrics_dir = project_root / ".dev_launcher_cache" / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_metrics: List[TimingMetric] = []
        self.phase_timers: Dict[str, float] = {}
        self.step_timers: Dict[str, float] = {}
        self.startup_start_time = 0.0
        self.cache_stats = {"hits": 0, "misses": 0}
    
    def start_profiling(self):
        """Start profiling a new startup sequence."""
        self.startup_start_time = time.time()
        self.current_metrics.clear()
        self.phase_timers.clear()
        self.step_timers.clear()
        self.cache_stats = {"hits": 0, "misses": 0}
        logger.debug("Started startup profiling")
    
    def start_phase_timer(self, phase_name: str):
        """Start timing a startup phase."""
        self.phase_timers[f"{phase_name}_start"] = time.time()
        logger.debug(f"Started timing phase: {phase_name}")
    
    def end_phase_timer(self, phase_name: str, success: bool = True, 
                       error: Optional[str] = None):
        """End timing a startup phase."""
        end_time = time.time()
        start_key = f"{phase_name}_start"
        
        if start_key not in self.phase_timers:
            logger.error(f"No start timer found for phase: {phase_name}")
            return
        
        start_time = self.phase_timers[start_key]
        duration = end_time - start_time
        
        metric = TimingMetric(
            name=f"phase_{phase_name}",
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            success=success,
            error=error
        )
        
        self.current_metrics.append(metric)
        logger.debug(f"Phase {phase_name} took {duration:.3f}s")
    
    def start_step_timer(self, step_name: str):
        """Start timing a startup step."""
        self.step_timers[f"{step_name}_start"] = time.time()
    
    def end_step_timer(self, step_name: str, success: bool = True, 
                      cached: bool = False, error: Optional[str] = None):
        """End timing a startup step."""
        end_time = time.time()
        start_key = f"{step_name}_start"
        
        if start_key not in self.step_timers:
            logger.warning(f"No start timer found for step: {step_name}")
            return
        
        start_time = self.step_timers[start_key]
        duration = end_time - start_time
        
        if cached:
            self.cache_stats["hits"] += 1
        else:
            self.cache_stats["misses"] += 1
        
        metric = TimingMetric(
            name=f"step_{step_name}",
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            success=success,
            error=error,
            metadata={"cached": cached}
        )
        
        self.current_metrics.append(metric)
    
    def record_timing(self, name: str, duration: float, success: bool = True, 
                     metadata: Optional[Dict[str, Any]] = None):
        """Record a manual timing measurement."""
        current_time = time.time()
        metric = TimingMetric(
            name=name,
            start_time=current_time - duration,
            end_time=current_time,
            duration=duration,
            success=success,
            metadata=metadata or {}
        )
        self.current_metrics.append(metric)
    
    def _identify_bottlenecks(self, metrics: List[TimingMetric]) -> List[str]:
        """Identify performance bottlenecks from timing data."""
        if not metrics:
            return []
        durations = [m.duration for m in metrics if m.success]
        if not durations:
            return []
        threshold = mean(durations) * 1.5
        return [f"{m.name} ({m.duration:.3f}s)" for m in metrics 
                if m.duration > threshold and m.success]
    
    def _generate_recommendations(self, profile: StartupProfile) -> List[str]:
        """Generate performance recommendations based on profile."""
        recommendations = []
        if not profile.target_met:
            slow_phases = [n for n, p in profile.phase_profiles.items() if p.total_duration > 3.0]
            if slow_phases:
                recommendations.append(f"Focus on optimizing phases: {', '.join(slow_phases)}")
        return recommendations or ["Performance is within targets"]
    
    def _calculate_critical_path(self, metrics: List[TimingMetric]) -> List[str]:
        """Calculate the critical path through startup phases."""
        phase_metrics = [m for m in metrics if m.name.startswith("phase_")]
        phase_metrics.sort(key=lambda m: m.duration, reverse=True)
        return [m.name.replace("phase_", "") for m in phase_metrics[:3]]
    
    def _create_phase_profiles(self, metrics: List[TimingMetric]) -> Dict[str, PhaseProfile]:
        """Create performance profiles for each phase."""
        phase_metrics = {m.name.replace("phase_", ""): m for m in metrics if m.name.startswith("phase_")}
        step_metrics = {m.name.replace("step_", ""): m for m in metrics if m.name.startswith("step_")}
        
        profiles = {}
        for phase_name, phase_metric in phase_metrics.items():
            related_steps = [(n, m) for n, m in step_metrics.items() if phase_name.lower() in n.lower()]
            profiles[phase_name] = self._create_single_phase_profile(phase_name, phase_metric, related_steps)
        return profiles
    
    def _create_single_phase_profile(self, name: str, metric: TimingMetric, steps: List) -> PhaseProfile:
        """Create profile for a single phase."""
        step_count = len(steps)
        success_rate = sum(1 for _, m in steps if m.success) / step_count if step_count > 0 else 1.0
        slowest = sorted([(n, m.duration) for n, m in steps], key=lambda x: x[1], reverse=True)[:3]
        bottlenecks = self._identify_bottlenecks([m for _, m in steps])
        cache_hits = sum(1 for _, m in steps if m.metadata and m.metadata.get("cached", False))
        return PhaseProfile(name, metric.duration, step_count, success_rate, slowest, bottlenecks, cache_hits, step_count - cache_hits)
    
    def generate_profile(self) -> StartupProfile:
        """Generate complete startup performance profile."""
        total_duration = time.time() - self.startup_start_time
        target_met = total_duration < self.target_time
        
        phase_profiles = self._create_phase_profiles(self.current_metrics)
        critical_path = self._calculate_critical_path(self.current_metrics)
        
        profile = StartupProfile(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_duration=total_duration,
            target_met=target_met,
            phase_profiles=phase_profiles,
            critical_path=critical_path,
            recommendations=[]
        )
        
        profile.recommendations = self._generate_recommendations(profile)
        profile.historical_comparison = self._get_historical_comparison(total_duration)
        
        return profile
    
    def _get_historical_comparison(self, current_duration: float) -> Dict[str, float]:
        """Compare current performance to historical averages."""
        try:
            history_file = self.metrics_dir / "startup_history.json"
            if not history_file.exists():
                return {"trend": 0.0, "percentile": 50.0}
            with open(history_file, 'r') as f:
                history = json.load(f)
            recent_durations = [entry["duration"] for entry in history[-10:]]
            if not recent_durations:
                return {"trend": 0.0, "percentile": 50.0}
            return self._calculate_trend_and_percentile(current_duration, recent_durations, history)
        except Exception as e:
            logger.error(f"Failed to get historical comparison: {e}")
            return {"trend": 0.0, "percentile": 50.0}
    
    def _calculate_trend_and_percentile(self, current: float, recent: List[float], history: List) -> Dict[str, float]:
        """Calculate trend and percentile from historical data."""
        avg_duration = mean(recent)
        trend = (current - avg_duration) / avg_duration * 100
        all_durations = [entry["duration"] for entry in history] + [current]
        all_durations.sort()
        percentile = (all_durations.index(current) / len(all_durations)) * 100
        return {"trend": trend, "percentile": percentile}
    
    def save_profile(self, profile: StartupProfile):
        """Save performance profile to storage."""
        try:
            profile_file = self.metrics_dir / f"profile_{int(time.time())}.json"
            with open(profile_file, 'w') as f:
                json.dump(asdict(profile), f, indent=2)
            self._update_history(profile)
            logger.debug(f"Saved performance profile to {profile_file}")
        except Exception as e:
            logger.error(f"Failed to save performance profile: {e}")
    
    def _update_history(self, profile: StartupProfile):
        """Update startup duration history."""
        try:
            history_file = self.metrics_dir / "startup_history.json"
            history = []
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
            history.append({"timestamp": profile.timestamp, "duration": profile.total_duration, "target_met": profile.target_met})
            with open(history_file, 'w') as f:
                json.dump(history[-100:], f, indent=2)  # Keep last 100
        except Exception as e:
            logger.error(f"Failed to update startup history: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get quick performance summary."""
        total_duration = time.time() - self.startup_start_time
        
        return {
            "total_duration": total_duration,
            "target_met": total_duration < self.target_time,
            "metrics_collected": len(self.current_metrics),
            "cache_hit_rate": self.cache_stats["hits"] / 
                            (self.cache_stats["hits"] + self.cache_stats["misses"])
                            if (self.cache_stats["hits"] + self.cache_stats["misses"]) > 0 else 0.0
        }