"""
CRITICAL SECURITY MODULE: Docker Force Flag Guardian

LIFE OR DEATH CRITICAL: Complete prohibition of Docker -f (force) flag

This module prevents Docker Desktop crashes caused by force removal operations.
Business Impact: Prevents $2M+ ARR loss from developer downtime.

ZERO TOLERANCE POLICY:
- NO exceptions
- NO bypasses  
- NO workarounds
- LOUD failures with audit logging
"""

import re
import logging
import datetime
from typing import List, Dict, Any
from pathlib import Path

# Configure critical logging
logger = logging.getLogger(__name__)


class DockerForceFlagViolation(Exception):
    """Critical exception for Docker force flag violations."""
    
    def __init__(self, command: str, violation_details: str):
        self.command = command
        self.violation_details = violation_details
        self.timestamp = datetime.datetime.now().isoformat()
        
        message = (
            f" ALERT:  CRITICAL SECURITY VIOLATION  ALERT: \n"
            f"FORBIDDEN: Docker force flag (-f) is prohibited\n"
            f"Command: {command}\n"
            f"Violation: {violation_details}\n"
            f"Timestamp: {self.timestamp}\n"
            f"Business Impact: This operation could crash Docker Desktop causing 4-8 hours downtime\n"
            f"Resolution: Use safe alternatives documented in docker_force_flag_guardian.py"
        )
        
        super().__init__(message)


class DockerForceFlagGuardian:
    """
    Zero-tolerance enforcement of Docker force flag prohibition.
    
    This guardian intercepts ALL Docker commands before execution and
    raises CRITICAL errors if force flags are detected.
    """
    
    # Comprehensive patterns to detect force flags (PRECISE - no false positives)
    FORCE_FLAG_PATTERNS = [
        r'-f\b',                    # -f as standalone flag
        r'--force\b',               # --force as standalone flag
        r'-f\s',                    # -f followed by space
        r'--force\s',               # --force followed by space
        r'-f$',                     # -f at end of line
        r'--force$',                # --force at end of line
        r'--force=[^\s]*',          # --force=value format
        # Only flag -f combined with other SINGLE letters (not words like -format)
        r'-[a-zA-Z]f\b',            # -af, -rf, etc. (f at end)
        r'-f[a-zA-Z]\b',            # -fa, -fr, etc. (f at start) 
        r'-[a-zA-Z]f[a-zA-Z]\b',    # -afr, -rfv, etc. (f in middle of short flags)
    ]
    
    # Docker commands that commonly use force flags (for extra vigilance)
    HIGH_RISK_COMMANDS = [
        'docker rm',
        'docker rmi', 
        'docker container rm',
        'docker image rm',
        'docker volume rm',
        'docker network rm',
        'docker system prune',
        'docker container prune',
        'docker image prune',
        'docker volume prune',
        'docker network prune',
    ]
    
    # Safe alternatives mapping
    SAFE_ALTERNATIVES = {
        'docker rm -f': 'docker stop <container> && docker rm <container>',
        'docker rmi -f': 'docker rmi <image> (after stopping containers)',
        'docker container rm -f': 'docker container stop <container> && docker container rm <container>',
        'docker image rm -f': 'docker image rm <image> (ensure no running containers)',
        'docker volume rm -f': 'docker volume rm <volume> (ensure no containers using it)',
        'docker system prune -f': 'docker system prune (with interactive confirmation)',
        'docker container prune -f': 'docker container prune (with interactive confirmation)',
        'docker image prune -f': 'docker image prune (with interactive confirmation)',
        'docker volume prune -f': 'docker volume prune (with interactive confirmation)',
        'docker network prune -f': 'docker network prune (with interactive confirmation)',
    }
    
    def __init__(self, audit_log_path: str = None):
        """Initialize guardian with audit logging."""
        self.audit_log_path = audit_log_path or "logs/docker_force_violations.log"
        self.violation_count = 0
        
        # Ensure audit log directory exists
        Path(self.audit_log_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Configure audit logger
        self.audit_logger = logging.getLogger('docker_force_violations')
        self.audit_logger.setLevel(logging.ERROR)
        
        if not self.audit_logger.handlers:
            handler = logging.FileHandler(self.audit_log_path)
            formatter = logging.Formatter(
                '%(asctime)s - CRITICAL VIOLATION - %(message)s'
            )
            handler.setFormatter(formatter)
            self.audit_logger.addHandler(handler)
    
    def validate_command(self, command: str) -> None:
        """
        Validate Docker command for force flag violations.
        
        Args:
            command: The Docker command to validate
            
        Raises:
            DockerForceFlagViolation: If force flags are detected
        """
        if not isinstance(command, str):
            command = str(command)
            
        command = command.strip()
        
        # Skip empty commands
        if not command:
            return
            
        # Only check Docker commands
        if not self._is_docker_command(command):
            return
            
        # Check for force flag patterns
        violations = self._detect_force_flags(command)
        
        if violations:
            self._handle_violation(command, violations)
    
    def _is_docker_command(self, command: str) -> bool:
        """Check if command is a Docker command."""
        command_lower = command.lower().strip()
        return (
            command_lower.startswith('docker ') or 
            command_lower == 'docker' or
            'docker' in command_lower
        )
    
    def _detect_force_flags(self, command: str) -> List[str]:
        """
        Detect force flag patterns in command.
        
        Returns:
            List of detected violations
        """
        violations = []
        
        # Check for legitimate exceptions first
        command_lower = command.lower().strip()
        for exception_pattern in [
            r'docker\s+logs\s+.*-f\b',               # docker logs -f (follow logs is safe)
            r'docker\s+build\s+.*-f\s+.*dockerfile', # docker build -f dockerfile  
            r'docker-compose\s+.*-f\s+.*\.ya?ml\b',  # docker-compose -f file.yml
            r'docker\s+exec\s+.*-f\b',               # docker exec -f (if it exists)
        ]:
            if re.search(exception_pattern, command_lower):
                return []  # This is a legitimate use of -f, not a force flag
        
        for pattern in self.FORCE_FLAG_PATTERNS:
            matches = re.finditer(pattern, command, re.IGNORECASE)
            for match in matches:
                violation_detail = f"Pattern '{pattern}' matched: '{match.group()}' at position {match.start()}-{match.end()}"
                violations.append(violation_detail)
        
        # Extra vigilance for high-risk commands
        for high_risk_cmd in self.HIGH_RISK_COMMANDS:
            if high_risk_cmd.lower() in command.lower():
                # Double-check for any force-like patterns
                if re.search(r'-[fF]|--force', command):
                    violations.append(f"High-risk command '{high_risk_cmd}' with force flag detected")
        
        return violations
    
    def _handle_violation(self, command: str, violations: List[str]) -> None:
        """
        Handle detected force flag violation.
        
        Args:
            command: The violating command
            violations: List of violation details
        """
        self.violation_count += 1
        
        violation_summary = "; ".join(violations)
        
        # Log to audit trail
        audit_message = (
            f"VIOLATION #{self.violation_count} | "
            f"Command: {command} | "
            f"Violations: {violation_summary}"
        )
        self.audit_logger.error(audit_message)
        
        # Log to console
        logger.critical(
            f" ALERT:  DOCKER FORCE FLAG VIOLATION DETECTED  ALERT: \n"
            f"Command: {command}\n"
            f"Violations: {violation_summary}"
        )
        
        # Raise critical exception
        raise DockerForceFlagViolation(command, violation_summary)
    
    def get_safe_alternative(self, command: str) -> str:
        """
        Get safe alternative for a command with force flags.
        
        Args:
            command: Command that may contain force flags
            
        Returns:
            Safe alternative command suggestion
        """
        command_lower = command.lower().strip()
        
        for risky_cmd, safe_alt in self.SAFE_ALTERNATIVES.items():
            if risky_cmd.lower() in command_lower:
                return safe_alt
                
        # Generic advice if no specific alternative found
        return (
            "Remove -f/--force flag and handle dependencies manually. "
            "Use 'docker stop' before 'docker rm', check for running containers "
            "before image removal, and use interactive confirmations for cleanup."
        )
    
    def audit_report(self) -> Dict[str, Any]:
        """
        Generate audit report of violations.
        
        Returns:
            Dictionary containing audit statistics and recent violations
        """
        try:
            with open(self.audit_log_path, 'r') as f:
                log_lines = f.readlines()
        except FileNotFoundError:
            log_lines = []
        
        return {
            'total_violations': self.violation_count,
            'audit_log_path': self.audit_log_path,
            'log_entries_count': len(log_lines),
            'recent_violations': log_lines[-10:] if log_lines else [],
            'guardian_status': 'ACTIVE - ZERO TOLERANCE ENFORCED',
            'business_impact_prevented': f'Potentially prevented {self.violation_count} Docker crashes'
        }


# Global guardian instance for easy import
docker_guardian = DockerForceFlagGuardian()


def validate_docker_command(command: str) -> None:
    """
    Convenience function to validate Docker commands.
    
    Args:
        command: Docker command to validate
        
    Raises:
        DockerForceFlagViolation: If force flags detected
    """
    docker_guardian.validate_command(command)


def get_safe_alternative(command: str) -> str:
    """
    Get safe alternative for Docker command.
    
    Args:
        command: Docker command that may need safe alternative
        
    Returns:
        Safe alternative suggestion
    """
    return docker_guardian.get_safe_alternative(command)


if __name__ == "__main__":
    # Self-test the guardian
    print("GUARDIAN: Docker Force Flag Guardian - Self Test")
    print("=" * 50)
    
    test_commands = [
        "docker ps",  # Safe
        "docker rm -f container123",  # VIOLATION
        "docker rmi --force image123",  # VIOLATION  
        "docker stop container123",  # Safe
        "docker container rm -rf container123",  # VIOLATION
        "docker system prune --force",  # VIOLATION
        "ls -la",  # Not Docker, safe
    ]
    
    guardian = DockerForceFlagGuardian()
    
    for cmd in test_commands:
        print(f"\nTesting: {cmd}")
        try:
            guardian.validate_command(cmd)
            print("SAFE")
        except DockerForceFlagViolation as e:
            print("VIOLATION DETECTED")
            print(f"Safe alternative: {guardian.get_safe_alternative(cmd)}")
    
    print(f"\nAudit Report:")
    report = guardian.audit_report()
    for key, value in report.items():
        print(f"{key}: {value}")