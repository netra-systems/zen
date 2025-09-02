"""
Standalone Environment Lock Manager - SSOT for Environment Locking

Extracted and enhanced from UnifiedDockerManager to provide cross-platform
environment locking functionality to prevent concurrent usage of development
and test environments.

Key Features:
- Cross-platform file-based locking (Windows and Unix)
- Timeout-based lock acquisition
- Support for multiple environment types (dev, test, staging, production)
- Lock metadata tracking (who, when, why)
- Automatic cleanup of stale locks
- Thread-safe operations
- Force release capabilities for admin operations

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Development Velocity, Risk Reduction
2. Business Goal: Prevent environment conflicts, enable reliable parallel development
3. Value Impact: Eliminates 2-4 hours/week of environment conflict resolution
4. Revenue Impact: Protects development velocity and CI/CD reliability
"""

import json
import logging
import os
import time
import threading
import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from enum import Enum
from datetime import datetime, timedelta
from contextlib import contextmanager
import socket

# Cross-platform imports
if os.name != 'nt':
    import fcntl
else:
    fcntl = None
    
if os.name == 'nt':
    import msvcrt
else:
    msvcrt = None


class EnvironmentType(Enum):
    """Supported environment types for locking."""
    DEV = "dev"
    TEST = "test" 
    STAGING = "staging"
    PRODUCTION = "production"


class LockStatus(Enum):
    """Lock status states."""
    AVAILABLE = "available"
    LOCKED = "locked"
    STALE = "stale"
    ERROR = "error"


@dataclass
class LockMetadata:
    """Metadata associated with an environment lock."""
    environment: str
    holder_id: str  # Process ID or identifier of lock holder
    hostname: str  # Machine holding the lock
    acquired_at: datetime
    purpose: str  # Why the lock was acquired
    timeout: int  # Lock timeout in seconds
    pid: int  # Process ID
    
    def __post_init__(self):
        """Ensure datetime serialization."""
        if isinstance(self.acquired_at, str):
            self.acquired_at = datetime.fromisoformat(self.acquired_at)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "environment": self.environment,
            "holder_id": self.holder_id,
            "hostname": self.hostname,
            "acquired_at": self.acquired_at.isoformat(),
            "purpose": self.purpose,
            "timeout": self.timeout,
            "pid": self.pid
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LockMetadata':
        """Create from dictionary."""
        return cls(
            environment=data["environment"],
            holder_id=data["holder_id"],
            hostname=data["hostname"],
            acquired_at=datetime.fromisoformat(data["acquired_at"]),
            purpose=data["purpose"],
            timeout=data["timeout"],
            pid=data["pid"]
        )
    
    def is_stale(self, stale_threshold: int = 300) -> bool:
        """Check if lock is stale based on timeout and age."""
        now = datetime.now()
        age = (now - self.acquired_at).total_seconds()
        
        # Lock is stale if it's older than its timeout + stale threshold
        return age > (self.timeout + stale_threshold)


class EnvironmentLockError(Exception):
    """Base exception for environment locking errors."""
    pass


class LockAcquisitionTimeout(EnvironmentLockError):
    """Raised when lock acquisition times out."""
    pass


class LockNotHeldError(EnvironmentLockError):
    """Raised when trying to release a lock not held by current process."""
    pass


class EnvironmentLock:
    """
    Cross-platform environment locking system.
    
    Provides file-based locking to prevent concurrent usage of environments
    like dev/test/staging across processes and machines.
    
    Example Usage:
        # Basic usage with context manager
        with EnvironmentLock() as lock:
            lock.acquire_dev(timeout=60, purpose="Running integration tests")
            # Do work that requires exclusive dev environment access
        
        # Manual lock management
        lock = EnvironmentLock()
        try:
            lock.acquire_test(timeout=30, purpose="E2E test suite")
            # Run tests
        finally:
            lock.release_all()
        
        # Check lock status
        status = lock.check_lock_status("dev")
        if status.status == LockStatus.AVAILABLE:
            print("Dev environment is available")
    """
    
    def __init__(self, 
                 lock_dir: Optional[Path] = None,
                 stale_threshold: int = 300,
                 cleanup_interval: int = 60):
        """
        Initialize environment lock manager.
        
        Args:
            lock_dir: Directory to store lock files (defaults to platform-specific temp)
            stale_threshold: Seconds after which locks are considered stale
            cleanup_interval: Seconds between automatic stale lock cleanup
        """
        # Lock directory setup - cross-platform
        if lock_dir is None:
            if os.name != 'nt':
                self.lock_dir = Path("/tmp/netra_env_locks")
            else:
                temp_dir = os.environ.get('TEMP', '.')
                self.lock_dir = Path(temp_dir) / "netra_env_locks"
        else:
            self.lock_dir = lock_dir
            
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        
        self.stale_threshold = stale_threshold
        self.cleanup_interval = cleanup_interval
        
        # Current process identification
        self.holder_id = self._generate_holder_id()
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        
        # Track locks held by this instance
        self._held_locks: Set[str] = set()
        self._lock = threading.RLock()  # Thread safety
        
        # Setup logging
        self.logger = logging.getLogger(f"EnvironmentLock.{self.holder_id}")
        
        # Metadata file for tracking all locks
        self.metadata_file = self.lock_dir / "lock_metadata.json"
        
        # Last cleanup time
        self._last_cleanup = datetime.now()
        
        self.logger.info(f"Initialized EnvironmentLock: holder_id={self.holder_id}, "
                        f"lock_dir={self.lock_dir}")
    
    def _generate_holder_id(self) -> str:
        """Generate unique identifier for this lock holder."""
        # Combine hostname, PID, and timestamp for uniqueness
        unique_str = f"{socket.gethostname()}_{os.getpid()}_{int(time.time())}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:12]
    
    def acquire_dev(self, timeout: int = 60, purpose: str = "Development work") -> bool:
        """Acquire development environment lock."""
        return self.acquire(EnvironmentType.DEV.value, timeout, purpose)
    
    def acquire_test(self, timeout: int = 60, purpose: str = "Testing") -> bool:
        """Acquire test environment lock."""
        return self.acquire(EnvironmentType.TEST.value, timeout, purpose)
    
    def acquire_staging(self, timeout: int = 60, purpose: str = "Staging deployment") -> bool:
        """Acquire staging environment lock."""
        return self.acquire(EnvironmentType.STAGING.value, timeout, purpose)
    
    def acquire_production(self, timeout: int = 60, purpose: str = "Production deployment") -> bool:
        """Acquire production environment lock."""
        return self.acquire(EnvironmentType.PRODUCTION.value, timeout, purpose)
    
    def acquire(self, env_name: str, timeout: int = 60, purpose: str = "Environment access") -> bool:
        """
        Acquire lock for specified environment.
        
        Args:
            env_name: Name of environment to lock
            timeout: Maximum seconds to wait for lock
            purpose: Human-readable purpose for the lock
            
        Returns:
            True if lock acquired successfully
            
        Raises:
            LockAcquisitionTimeout: If lock cannot be acquired within timeout
        """
        with self._lock:
            # Clean up stale locks periodically
            self._cleanup_stale_locks_if_needed()
            
            lock_file = self.lock_dir / f"{env_name}.lock"
            
            self.logger.info(f"Attempting to acquire {env_name} environment lock "
                           f"(timeout={timeout}s, purpose='{purpose}')")
            
            # Try to acquire the file lock
            acquired = self._acquire_file_lock(env_name, timeout)
            
            if acquired:
                # Store metadata
                metadata = LockMetadata(
                    environment=env_name,
                    holder_id=self.holder_id,
                    hostname=self.hostname,
                    acquired_at=datetime.now(),
                    purpose=purpose,
                    timeout=timeout,
                    pid=self.pid
                )
                
                self._store_lock_metadata(metadata)
                self._held_locks.add(env_name)
                
                self.logger.info(f"Successfully acquired {env_name} environment lock")
                return True
            else:
                error_msg = f"Failed to acquire {env_name} environment lock within {timeout} seconds"
                self.logger.error(error_msg)
                raise LockAcquisitionTimeout(error_msg)
    
    @contextmanager
    def _file_lock(self, env_name: str, timeout: int = 30):
        """
        Cross-platform file locking mechanism.
        
        Args:
            env_name: Environment name for lock file
            timeout: Maximum time to wait for lock
        """
        lock_file = self.lock_dir / f"{env_name}.lock"
        lock_file.touch(exist_ok=True)
        
        start_time = time.time()
        locked = False
        
        with open(lock_file, 'r+') as f:
            while time.time() - start_time < timeout:
                try:
                    if os.name == 'nt':
                        # Windows locking
                        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        # Unix locking
                        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except (IOError, OSError):
                    time.sleep(0.1)
            
            if not locked:
                raise TimeoutError(f"Could not acquire file lock {env_name} within {timeout} seconds")
            
            try:
                yield
            finally:
                if os.name == 'nt':
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(f, fcntl.LOCK_UN)
    
    def _acquire_file_lock(self, env_name: str, timeout: int) -> bool:
        """Acquire file lock with timeout."""
        try:
            with self._file_lock(env_name, timeout):
                # Lock acquired successfully
                return True
        except TimeoutError:
            return False
    
    def _store_lock_metadata(self, metadata: LockMetadata):
        """Store lock metadata to persistent storage."""
        try:
            # Load existing metadata
            all_metadata = self._load_all_metadata()
            
            # Update with new metadata
            all_metadata[metadata.environment] = metadata.to_dict()
            
            # Write back to file
            with open(self.metadata_file, 'w') as f:
                json.dump(all_metadata, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to store lock metadata: {e}")
    
    def _load_all_metadata(self) -> Dict[str, Any]:
        """Load all lock metadata from persistent storage."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load lock metadata: {e}")
        
        return {}
    
    def release_all(self) -> List[str]:
        """
        Release all locks held by this instance.
        
        Returns:
            List of environment names that were released
        """
        with self._lock:
            released = []
            
            for env_name in list(self._held_locks):
                if self._release_lock(env_name):
                    released.append(env_name)
            
            self.logger.info(f"Released {len(released)} environment locks: {released}")
            return released
    
    def release(self, env_name: str) -> bool:
        """
        Release lock for specific environment.
        
        Args:
            env_name: Name of environment to release
            
        Returns:
            True if successfully released
            
        Raises:
            LockNotHeldError: If lock is not held by current process
        """
        with self._lock:
            if env_name not in self._held_locks:
                raise LockNotHeldError(f"Lock for {env_name} is not held by this process")
            
            return self._release_lock(env_name)
    
    def _release_lock(self, env_name: str) -> bool:
        """Internal method to release a lock."""
        try:
            # Remove from metadata
            all_metadata = self._load_all_metadata()
            
            if env_name in all_metadata:
                # Verify we own this lock
                metadata = LockMetadata.from_dict(all_metadata[env_name])
                if metadata.holder_id != self.holder_id:
                    self.logger.warning(f"Attempting to release lock held by different process: "
                                      f"current={self.holder_id}, owner={metadata.holder_id}")
                    return False
                
                # Remove metadata
                del all_metadata[env_name]
                
                # Write back
                with open(self.metadata_file, 'w') as f:
                    json.dump(all_metadata, f, indent=2)
            
            # Remove lock file
            lock_file = self.lock_dir / f"{env_name}.lock"
            if lock_file.exists():
                lock_file.unlink()
            
            # Remove from held locks
            self._held_locks.discard(env_name)
            
            self.logger.info(f"Successfully released {env_name} environment lock")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to release {env_name} lock: {e}")
            return False
    
    def check_lock_status(self, env_name: str) -> 'LockStatusInfo':
        """
        Check status of environment lock.
        
        Args:
            env_name: Name of environment to check
            
        Returns:
            LockStatusInfo with current status and metadata
        """
        try:
            lock_file = self.lock_dir / f"{env_name}.lock"
            
            if not lock_file.exists():
                return LockStatusInfo(
                    environment=env_name,
                    status=LockStatus.AVAILABLE,
                    metadata=None
                )
            
            # Load metadata
            all_metadata = self._load_all_metadata()
            
            if env_name not in all_metadata:
                # Lock file exists but no metadata - could be stale
                return LockStatusInfo(
                    environment=env_name,
                    status=LockStatus.STALE,
                    metadata=None
                )
            
            metadata = LockMetadata.from_dict(all_metadata[env_name])
            
            # Check if stale
            if metadata.is_stale(self.stale_threshold):
                return LockStatusInfo(
                    environment=env_name,
                    status=LockStatus.STALE,
                    metadata=metadata
                )
            
            # Check if we can actually acquire the lock (test if process is alive)
            try:
                with self._file_lock(env_name, timeout=0.1):
                    # If we can acquire it, the previous holder is gone
                    return LockStatusInfo(
                        environment=env_name,
                        status=LockStatus.STALE,
                        metadata=metadata
                    )
            except TimeoutError:
                # Lock is actively held
                return LockStatusInfo(
                    environment=env_name,
                    status=LockStatus.LOCKED,
                    metadata=metadata
                )
                
        except Exception as e:
            self.logger.error(f"Failed to check lock status for {env_name}: {e}")
            return LockStatusInfo(
                environment=env_name,
                status=LockStatus.ERROR,
                metadata=None,
                error_message=str(e)
            )
    
    def force_release(self, env_name: str, reason: str = "Administrative override") -> bool:
        """
        Force release a lock (admin function).
        
        Args:
            env_name: Environment to force release
            reason: Reason for force release (for logging)
            
        Returns:
            True if successfully force released
        """
        with self._lock:
            self.logger.warning(f"Force releasing {env_name} environment lock. Reason: {reason}")
            
            try:
                # Remove lock file
                lock_file = self.lock_dir / f"{env_name}.lock"
                if lock_file.exists():
                    lock_file.unlink()
                
                # Remove metadata
                all_metadata = self._load_all_metadata()
                if env_name in all_metadata:
                    del all_metadata[env_name]
                    
                    with open(self.metadata_file, 'w') as f:
                        json.dump(all_metadata, f, indent=2)
                
                # Remove from held locks (in case we held it)
                self._held_locks.discard(env_name)
                
                self.logger.info(f"Successfully force released {env_name} environment lock")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to force release {env_name} lock: {e}")
                return False
    
    def list_all_locks(self) -> List['LockStatusInfo']:
        """List status of all environment locks."""
        locks = []
        
        # Check all known environments
        for env_type in EnvironmentType:
            status = self.check_lock_status(env_type.value)
            locks.append(status)
        
        # Check for any additional lock files
        for lock_file in self.lock_dir.glob("*.lock"):
            env_name = lock_file.stem
            if env_name not in [env.value for env in EnvironmentType]:
                status = self.check_lock_status(env_name)
                locks.append(status)
        
        return locks
    
    def cleanup_stale_locks(self, force: bool = False) -> List[str]:
        """
        Clean up stale locks.
        
        Args:
            force: If True, clean up all locks regardless of staleness
            
        Returns:
            List of environments that had stale locks cleaned up
        """
        cleaned = []
        
        try:
            all_metadata = self._load_all_metadata()
            
            for env_name, metadata_dict in list(all_metadata.items()):
                metadata = LockMetadata.from_dict(metadata_dict)
                
                should_clean = force or metadata.is_stale(self.stale_threshold)
                
                if should_clean:
                    # Try to verify the lock is actually stale by testing acquisition
                    try:
                        with self._file_lock(env_name, timeout=0.1):
                            # We can acquire it, so it's stale
                            self.force_release(env_name, "Stale lock cleanup")
                            cleaned.append(env_name)
                    except TimeoutError:
                        # Still actively held, skip unless force
                        if force:
                            self.force_release(env_name, "Force cleanup requested")
                            cleaned.append(env_name)
        
        except Exception as e:
            self.logger.error(f"Failed to cleanup stale locks: {e}")
        
        if cleaned:
            self.logger.info(f"Cleaned up {len(cleaned)} stale locks: {cleaned}")
        
        return cleaned
    
    def _cleanup_stale_locks_if_needed(self):
        """Clean up stale locks if cleanup interval has elapsed."""
        now = datetime.now()
        if (now - self._last_cleanup).total_seconds() > self.cleanup_interval:
            self.cleanup_stale_locks()
            self._last_cleanup = now
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - release all held locks."""
        self.release_all()


@dataclass
class LockStatusInfo:
    """Information about the status of an environment lock."""
    environment: str
    status: LockStatus
    metadata: Optional[LockMetadata] = None
    error_message: Optional[str] = None
    
    def __str__(self) -> str:
        """Human readable string representation."""
        if self.status == LockStatus.AVAILABLE:
            return f"{self.environment}: Available"
        elif self.status == LockStatus.LOCKED and self.metadata:
            return (f"{self.environment}: Locked by {self.metadata.hostname} "
                   f"(PID: {self.metadata.pid}) at {self.metadata.acquired_at.strftime('%H:%M:%S')} "
                   f"for '{self.metadata.purpose}'")
        elif self.status == LockStatus.STALE and self.metadata:
            return (f"{self.environment}: Stale lock from {self.metadata.hostname} "
                   f"(acquired {self.metadata.acquired_at.strftime('%H:%M:%S')})")
        elif self.status == LockStatus.ERROR:
            return f"{self.environment}: Error - {self.error_message}"
        else:
            return f"{self.environment}: {self.status.value}"


# Example usage and utility functions
def main():
    """Example usage of EnvironmentLock."""
    logging.basicConfig(level=logging.INFO)
    
    # Example 1: Context manager usage
    print("Example 1: Context manager usage")
    with EnvironmentLock() as lock:
        try:
            lock.acquire_dev(timeout=10, purpose="Example development work")
            print("[OK] Acquired dev environment lock")
            
            # Simulate some work
            time.sleep(2)
            
            # Check status of test environment
            test_status = lock.check_lock_status("test")
            print(f"Test environment status: {test_status}")
            
        except LockAcquisitionTimeout as e:
            print(f"[ERROR] Failed to acquire lock: {e}")
    
    print("[OK] Locks automatically released by context manager\n")
    
    # Example 2: Manual lock management
    print("Example 2: Manual lock management")
    lock = EnvironmentLock()
    
    try:
        lock.acquire_test(timeout=5, purpose="Running test suite")
        print("[OK] Acquired test environment lock")
        
        # List all locks
        all_locks = lock.list_all_locks()
        print("\nCurrent lock status:")
        for lock_info in all_locks:
            print(f"  {lock_info}")
        
    except LockAcquisitionTimeout as e:
        print(f"[ERROR] Failed to acquire test lock: {e}")
    finally:
        released = lock.release_all()
        print(f"[OK] Released locks: {released}")
    
    # Example 3: Cleanup demonstration
    print("\nExample 3: Cleanup demonstration")
    cleaned = lock.cleanup_stale_locks(force=True)
    print(f"Cleaned up locks: {cleaned}")


if __name__ == "__main__":
    main()