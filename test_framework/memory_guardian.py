"""
Memory Guardian - Pre-flight memory checks and monitoring for Docker test environments

This module prevents OOM kills by checking available memory before starting Docker services
and provides memory monitoring during test execution.

Business Value: Platform/Internal - Test Infrastructure Stability
Prevents test failures due to insufficient memory, improving development velocity.
"""

import os
import sys
import psutil
import logging
from typing import Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TestProfile(Enum):
    """Test execution profiles with memory requirements."""
    MINIMAL = "minimal"      # Unit tests only
    STANDARD = "standard"    # Integration tests
    FULL = "full"           # E2E tests with all services
    PERFORMANCE = "performance"  # Performance testing


@dataclass
class MemoryRequirements:
    """Memory requirements for different test profiles."""
    profile: TestProfile
    postgres_mb: int
    redis_mb: int
    backend_mb: int
    auth_mb: int
    frontend_mb: int
    clickhouse_mb: int = 0
    overhead_mb: int = 512  # OS and test runner overhead
    
    @property
    def total_mb(self) -> int:
        """Calculate total memory required."""
        return (
            self.postgres_mb + 
            self.redis_mb + 
            self.backend_mb + 
            self.auth_mb + 
            self.frontend_mb + 
            self.clickhouse_mb + 
            self.overhead_mb
        )
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary for reporting."""
        return {
            "profile": self.profile.value,
            "postgres_mb": self.postgres_mb,
            "redis_mb": self.redis_mb,
            "backend_mb": self.backend_mb,
            "auth_mb": self.auth_mb,
            "frontend_mb": self.frontend_mb,
            "clickhouse_mb": self.clickhouse_mb,
            "overhead_mb": self.overhead_mb,
            "total_mb": self.total_mb
        }


# Memory profiles optimized after OOM analysis
MEMORY_PROFILES = {
    TestProfile.MINIMAL: MemoryRequirements(
        profile=TestProfile.MINIMAL,
        postgres_mb=256,
        redis_mb=128,
        backend_mb=512,
        auth_mb=256,
        frontend_mb=0,  # No frontend for unit tests
        clickhouse_mb=0,
        overhead_mb=256
    ),
    TestProfile.STANDARD: MemoryRequirements(
        profile=TestProfile.STANDARD,
        postgres_mb=256,
        redis_mb=256,
        backend_mb=1024,
        auth_mb=512,
        frontend_mb=512,
        clickhouse_mb=512,
        overhead_mb=512
    ),
    TestProfile.FULL: MemoryRequirements(
        profile=TestProfile.FULL,
        postgres_mb=512,
        redis_mb=512,
        backend_mb=2048,
        auth_mb=1024,
        frontend_mb=512,
        clickhouse_mb=1024,
        overhead_mb=1024
    ),
    TestProfile.PERFORMANCE: MemoryRequirements(
        profile=TestProfile.PERFORMANCE,
        postgres_mb=1024,
        redis_mb=512,
        backend_mb=4096,
        auth_mb=2048,
        frontend_mb=1024,
        clickhouse_mb=2048,
        overhead_mb=2048
    )
}


class MemoryGuardian:
    """
    Guardian that prevents OOM kills by checking memory before Docker operations.
    
    Features:
    - Pre-flight memory checks before starting services
    - Dynamic profile selection based on available memory
    - Memory pressure monitoring during tests
    - Recommendations for memory optimization
    """
    
    def __init__(self, profile: Optional[TestProfile] = None):
        """
        Initialize MemoryGuardian.
        
        Args:
            profile: Test profile to use, or None to auto-detect
        """
        self.profile = profile
        self.memory_requirements = None
        if profile:
            self.memory_requirements = MEMORY_PROFILES.get(profile)
    
    def get_system_memory(self) -> Tuple[int, int, float]:
        """
        Get current system memory status.
        
        Returns:
            Tuple of (total_mb, available_mb, percent_used)
        """
        mem = psutil.virtual_memory()
        total_mb = mem.total / (1024 * 1024)
        available_mb = mem.available / (1024 * 1024)
        percent_used = mem.percent
        
        return int(total_mb), int(available_mb), percent_used
    
    def check_memory_available(self, required_mb: int, safety_factor: float = 1.2) -> Tuple[bool, str]:
        """
        Check if sufficient memory is available.
        
        Args:
            required_mb: Memory required in MB
            safety_factor: Safety multiplier (default 1.2 = 20% buffer)
            
        Returns:
            Tuple of (is_available, message)
        """
        total_mb, available_mb, percent_used = self.get_system_memory()
        required_with_buffer = int(required_mb * safety_factor)
        
        if available_mb >= required_with_buffer:
            return True, f"Memory check passed: {available_mb}MB available, {required_with_buffer}MB required"
        
        shortage_mb = required_with_buffer - available_mb
        return False, (
            f"Insufficient memory: {available_mb}MB available, "
            f"{required_with_buffer}MB required (shortage: {shortage_mb}MB). "
            f"System memory usage: {percent_used:.1f}%"
        )
    
    def pre_flight_check(self, profile: Optional[TestProfile] = None) -> Tuple[bool, Dict]:
        """
        Perform pre-flight memory check before starting Docker services.
        
        Args:
            profile: Test profile to check, uses instance profile if not provided
            
        Returns:
            Tuple of (can_proceed, details_dict)
        """
        test_profile = profile or self.profile or TestProfile.STANDARD
        requirements = MEMORY_PROFILES[test_profile]
        
        total_mb, available_mb, percent_used = self.get_system_memory()
        can_proceed, message = self.check_memory_available(requirements.total_mb)
        
        details = {
            "profile": test_profile.value,
            "system_total_mb": total_mb,
            "system_available_mb": available_mb,
            "system_percent_used": percent_used,
            "required_mb": requirements.total_mb,
            "can_proceed": can_proceed,
            "message": message,
            "requirements": requirements.to_dict()
        }
        
        if not can_proceed:
            # Suggest alternative profiles
            details["alternatives"] = self._suggest_alternatives(available_mb)
        
        return can_proceed, details
    
    def _suggest_alternatives(self, available_mb: int) -> list:
        """
        Suggest alternative test profiles based on available memory.
        
        Args:
            available_mb: Available memory in MB
            
        Returns:
            List of alternative profile suggestions
        """
        alternatives = []
        safety_factor = 1.2
        
        for profile, requirements in MEMORY_PROFILES.items():
            required_with_buffer = int(requirements.total_mb * safety_factor)
            if available_mb >= required_with_buffer:
                alternatives.append({
                    "profile": profile.value,
                    "required_mb": requirements.total_mb,
                    "description": self._get_profile_description(profile)
                })
        
        return alternatives
    
    def _get_profile_description(self, profile: TestProfile) -> str:
        """Get human-readable description of test profile."""
        descriptions = {
            TestProfile.MINIMAL: "Unit tests only, minimal services",
            TestProfile.STANDARD: "Integration tests with core services",
            TestProfile.FULL: "Full E2E tests with all services",
            TestProfile.PERFORMANCE: "Performance testing with high resources"
        }
        return descriptions.get(profile, "Unknown profile")
    
    def monitor_memory_pressure(self) -> Dict:
        """
        Monitor current memory pressure and provide recommendations.
        
        Returns:
            Dictionary with memory status and recommendations
        """
        total_mb, available_mb, percent_used = self.get_system_memory()
        
        status = {
            "total_mb": total_mb,
            "available_mb": available_mb,
            "percent_used": percent_used,
            "pressure_level": self._get_pressure_level(percent_used),
            "recommendations": []
        }
        
        # Add recommendations based on pressure level
        if percent_used > 90:
            status["recommendations"].extend([
                "CRITICAL: System memory usage above 90%",
                "Stop non-essential services immediately",
                "Consider restarting Docker services",
                "Run 'docker system prune' to free space"
            ])
        elif percent_used > 80:
            status["recommendations"].extend([
                "WARNING: High memory usage detected",
                "Monitor closely for OOM conditions",
                "Consider using MINIMAL test profile",
                "Close unnecessary applications"
            ])
        elif percent_used > 70:
            status["recommendations"].append(
                "Memory usage elevated but manageable"
            )
        
        return status
    
    def _get_pressure_level(self, percent_used: float) -> str:
        """Categorize memory pressure level."""
        if percent_used > 90:
            return "CRITICAL"
        elif percent_used > 80:
            return "HIGH"
        elif percent_used > 70:
            return "MODERATE"
        else:
            return "LOW"
    
    def get_docker_memory_config(self, profile: Optional[TestProfile] = None) -> Dict[str, str]:
        """
        Get Docker memory configuration for the specified profile.
        
        Args:
            profile: Test profile to use
            
        Returns:
            Dictionary of service: memory_limit pairs
        """
        test_profile = profile or self.profile or TestProfile.STANDARD
        requirements = MEMORY_PROFILES[test_profile]
        
        return {
            "postgres": f"{requirements.postgres_mb}M",
            "redis": f"{requirements.redis_mb}M",
            "backend": f"{requirements.backend_mb}M",
            "auth": f"{requirements.auth_mb}M",
            "frontend": f"{requirements.frontend_mb}M" if requirements.frontend_mb > 0 else "0",
            "clickhouse": f"{requirements.clickhouse_mb}M" if requirements.clickhouse_mb > 0 else "0"
        }


def perform_pre_flight_check(profile: TestProfile = TestProfile.STANDARD) -> bool:
    """
    Convenience function to perform pre-flight memory check.
    
    Args:
        profile: Test profile to check
        
    Returns:
        True if memory check passes, raises MemoryError otherwise
    """
    guardian = MemoryGuardian(profile)
    can_proceed, details = guardian.pre_flight_check()
    
    if not can_proceed:
        logger.error(f"Memory pre-flight check failed: {details['message']}")
        
        # Log alternatives if available
        if details.get("alternatives"):
            logger.info("Alternative profiles that could work:")
            for alt in details["alternatives"]:
                logger.info(f"  - {alt['profile']}: {alt['description']} ({alt['required_mb']}MB)")
        
        raise MemoryError(
            f"Insufficient memory for {profile.value} profile. "
            f"Available: {details['system_available_mb']}MB, "
            f"Required: {details['required_mb']}MB"
        )
    
    logger.info(f"Memory pre-flight check passed: {details['message']}")
    return True


def get_recommended_profile() -> TestProfile:
    """
    Get recommended test profile based on available memory.
    
    Returns:
        Recommended TestProfile
    """
    guardian = MemoryGuardian()
    _, available_mb, _ = guardian.get_system_memory()
    
    # Work backwards from most to least demanding
    for profile in [TestProfile.PERFORMANCE, TestProfile.FULL, 
                   TestProfile.STANDARD, TestProfile.MINIMAL]:
        requirements = MEMORY_PROFILES[profile]
        required_with_buffer = int(requirements.total_mb * 1.2)
        
        if available_mb >= required_with_buffer:
            logger.info(f"Recommended profile: {profile.value} "
                       f"(available: {available_mb}MB, required: {requirements.total_mb}MB)")
            return profile
    
    # If even minimal doesn't fit, return it anyway with warning
    logger.warning(f"Insufficient memory even for MINIMAL profile "
                  f"(available: {available_mb}MB)")
    return TestProfile.MINIMAL


if __name__ == "__main__":
    # Example usage and testing
    print("=== Docker Memory Guardian ===\n")
    
    guardian = MemoryGuardian()
    
    # Check system memory
    total, available, percent = guardian.get_system_memory()
    print(f"System Memory:")
    print(f"  Total: {total:,} MB")
    print(f"  Available: {available:,} MB")
    print(f"  Used: {percent:.1f}%\n")
    
    # Test each profile
    for profile in TestProfile:
        can_proceed, details = guardian.pre_flight_check(profile)
        print(f"{profile.value.upper()} Profile:")
        print(f"  Required: {details['requirements']['total_mb']:,} MB")
        print(f"  Can proceed: {can_proceed}")
        print(f"  {details['message']}\n")
    
    # Get recommendation
    recommended = get_recommended_profile()
    print(f"Recommended profile: {recommended.value}")
    
    # Monitor current pressure
    status = guardian.monitor_memory_pressure()
    print(f"\nMemory Pressure: {status['pressure_level']}")
    if status['recommendations']:
        print("Recommendations:")
        for rec in status['recommendations']:
            print(f"  - {rec}")